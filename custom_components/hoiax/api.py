"""Minimal async client for the myUplink cloud used by Høiax Connected."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import logging
import time
from typing import Any

import aiohttp

from .const import API_BASE_URL, CLIENT_ID, TOKEN_URL

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=30)
# Renew the access token this many seconds before it actually expires.
TOKEN_EXPIRY_MARGIN = 120


class HoiaxError(Exception):
    """Base error for the Høiax client."""


class HoiaxAuthError(HoiaxError):
    """Credentials were rejected by myUplink."""


class HoiaxConnectionError(HoiaxError):
    """myUplink could not be reached or answered with an error."""


@dataclass(slots=True)
class HoiaxPoint:
    """A single myUplink data point (parameter) on a device."""

    parameter_id: str
    name: str
    value: Any
    text: str | None
    unit: str | None
    writable: bool
    min_value: float | None
    max_value: float | None
    options: dict[str, str]

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> HoiaxPoint:
        """Build a point from the API response.

        ``value`` is already scaled, but ``minValue``/``maxValue`` are raw and
        must be multiplied by ``scaleValue``.
        """
        try:
            scale = float(data.get("scaleValue") or 1)
        except (TypeError, ValueError):
            scale = 1.0

        def _scaled(raw: Any) -> float | None:
            if raw is None:
                return None
            try:
                return round(float(raw) * scale, 3)
            except (TypeError, ValueError):
                return None

        return cls(
            parameter_id=str(data.get("parameterId")),
            name=str(data.get("parameterName") or ""),
            value=data.get("value"),
            text=data.get("strVal"),
            unit=data.get("parameterUnit") or None,
            writable=bool(data.get("writable")),
            min_value=_scaled(data.get("minValue")),
            max_value=_scaled(data.get("maxValue")),
            options={
                str(opt.get("value")): str(opt.get("text")) for opt in data.get("enumValues") or []
            },
        )

    @property
    def enum_key(self) -> str | None:
        """Return the value as an enum key string (e.g. ``"8"``)."""
        if self.value is None:
            return None
        try:
            return str(int(float(self.value)))
        except (TypeError, ValueError):
            return str(self.value)


@dataclass(slots=True)
class HoiaxDevice:
    """A Høiax water heater and its latest data points."""

    device_id: str
    name: str
    model: str | None = None
    serial_number: str | None = None
    firmware: str | None = None
    online: bool = True
    points: dict[str, HoiaxPoint] = field(default_factory=dict)

    def value(self, parameter_id: str) -> Any:
        """Return the value of a point, or None when missing."""
        point = self.points.get(parameter_id)
        return None if point is None else point.value


class HoiaxApiClient:
    """Talks to myUplink with the user's own e-mail and password."""

    def __init__(self, session: aiohttp.ClientSession, username: str, password: str) -> None:
        """Initialise the client."""
        self._session = session
        self._username = username
        self._password = password
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._expires_at = 0.0
        self._token_lock = asyncio.Lock()

    async def async_login(self) -> None:
        """Log in with username/password (also validates credentials)."""
        await self._async_token_request(
            {
                "grant_type": "password",
                "client_id": CLIENT_ID,
                "username": self._username,
                "password": self._password,
            }
        )

    async def _async_token_request(self, form: dict[str, str]) -> None:
        try:
            async with self._session.post(
                TOKEN_URL,
                data=form,
                headers={"Accept": "application/json"},
                timeout=REQUEST_TIMEOUT,
            ) as resp:
                payload = await resp.json(content_type=None)
                status = resp.status
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise HoiaxConnectionError(f"Could not reach myUplink: {err}") from err

        if (
            status in (400, 401)
            and isinstance(payload, dict)
            and payload.get("error") in ("invalid_grant", "invalid_client")
        ):
            raise HoiaxAuthError(payload.get("error_description") or "invalid_grant")
        if status != 200 or not isinstance(payload, dict) or "access_token" not in payload:
            raise HoiaxConnectionError(f"Unexpected login response from myUplink ({status})")

        self._access_token = payload["access_token"]
        self._refresh_token = payload.get("refresh_token") or self._refresh_token
        self._expires_at = time.monotonic() + float(payload.get("expires_in") or 3600)

    async def _async_ensure_token(self, force: bool = False) -> str:
        async with self._token_lock:
            if (
                not force
                and self._access_token
                and time.monotonic() < self._expires_at - TOKEN_EXPIRY_MARGIN
            ):
                return self._access_token
            if self._refresh_token:
                try:
                    await self._async_token_request(
                        {
                            "grant_type": "refresh_token",
                            "client_id": CLIENT_ID,
                            "refresh_token": self._refresh_token,
                        }
                    )
                except HoiaxError:
                    _LOGGER.debug("Refreshing token failed, logging in again")
                    self._refresh_token = None
                else:
                    assert self._access_token
                    return self._access_token
            await self.async_login()
            assert self._access_token
            return self._access_token

    async def _async_request(
        self, method: str, path: str, *, retry_auth: bool = True, **kwargs: Any
    ) -> Any:
        token = await self._async_ensure_token()
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        try:
            async with self._session.request(
                method,
                f"{API_BASE_URL}{path}",
                headers=headers,
                timeout=REQUEST_TIMEOUT,
                **kwargs,
            ) as resp:
                if resp.status == 401 and retry_auth:
                    await self._async_ensure_token(force=True)
                    return await self._async_request(method, path, retry_auth=False, **kwargs)
                if resp.status == 401:
                    raise HoiaxAuthError("myUplink rejected the access token")
                if resp.status == 204:
                    return None
                if resp.status >= 400:
                    body = await resp.text()
                    raise HoiaxConnectionError(
                        f"myUplink returned {resp.status} for {method} {path}: {body[:200]}"
                    )
                return await resp.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise HoiaxConnectionError(f"Error talking to myUplink: {err}") from err

    async def async_get_devices(self) -> list[HoiaxDevice]:
        """Return all devices on the account."""
        devices: dict[str, HoiaxDevice] = {}
        try:
            data = await self._async_request("GET", "/v2/systems/me?itemsPerPage=100")
            for system in (data or {}).get("systems", []):
                for dev in system.get("devices", []):
                    self._add_device(devices, dev, system.get("name"))
        except HoiaxConnectionError:
            _LOGGER.debug("systems/me failed, falling back to groups/me")
        if not devices:
            data = await self._async_request("GET", "/v2/groups/me")
            for group in (data or {}).get("groups", []):
                for dev in group.get("devices", []):
                    self._add_device(devices, dev, group.get("name"))
        return list(devices.values())

    @staticmethod
    def _add_device(
        devices: dict[str, HoiaxDevice], dev: dict[str, Any], fallback_name: str | None
    ) -> None:
        device_id = dev.get("id")
        if not device_id:
            return
        product = dev.get("product") or {}
        devices[device_id] = HoiaxDevice(
            device_id=device_id,
            name=product.get("name") or dev.get("name") or fallback_name or "Høiax",
            model=product.get("name") or dev.get("name"),
            serial_number=product.get("serialNumber") or dev.get("serialNumber"),
            firmware=dev.get("currentFwVersion"),
            online=dev.get("connectionState", "Connected") != "Disconnected",
        )

    async def async_get_points(self, device_id: str) -> dict[str, HoiaxPoint]:
        """Return all data points for a device keyed by parameter id."""
        data = await self._async_request("GET", f"/v2/devices/{device_id}/points")
        if not isinstance(data, list):
            raise HoiaxConnectionError("Unexpected points response from myUplink")
        points = (HoiaxPoint.from_api(item) for item in data if isinstance(item, dict))
        return {point.parameter_id: point for point in points}

    async def async_set_points(self, device_id: str, values: dict[str, Any]) -> None:
        """Write one or more writable parameters."""
        _LOGGER.debug("Writing %s to %s", values, device_id)
        result = await self._async_request("PATCH", f"/v2/devices/{device_id}/points", json=values)
        _LOGGER.debug("Write result: %s", result)
        # The API answers with a status per parameter, e.g. {"527": "modified"}.
        if isinstance(result, dict):
            failed = {
                key: status
                for key, status in result.items()
                if any(word in str(status).lower() for word in ("error", "invalid", "fail"))
            }
            if failed:
                raise HoiaxConnectionError(f"myUplink did not accept {failed}")
