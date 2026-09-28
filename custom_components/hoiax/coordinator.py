"""Data update coordinator for Høiax Connected."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import HoiaxApiClient, HoiaxAuthError, HoiaxDevice, HoiaxError
from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    REFRESH_DELAY_AFTER_WRITE,
)

_LOGGER = logging.getLogger(__name__)

type HoiaxConfigEntry = ConfigEntry[HoiaxCoordinator]


class HoiaxCoordinator(DataUpdateCoordinator[dict[str, HoiaxDevice]]):
    """Polls all Høiax water heaters on a myUplink account."""

    config_entry: HoiaxConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: HoiaxConfigEntry, client: HoiaxApiClient
    ) -> None:
        """Initialise the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(
                seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
        )
        self.client = client
        self._devices: dict[str, HoiaxDevice] = {}
        self._cancel_delayed_refresh: Any = None

    async def _async_setup(self) -> None:
        """Discover devices once when the integration starts."""
        try:
            devices = await self.client.async_get_devices()
        except HoiaxAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except HoiaxError as err:
            raise UpdateFailed(f"Could not list devices: {err}") from err
        self._devices = {device.device_id: device for device in devices}

    async def _async_update_data(self) -> dict[str, HoiaxDevice]:
        results = await asyncio.gather(
            *(self.client.async_get_points(dev_id) for dev_id in self._devices),
            return_exceptions=True,
        )
        errors: list[BaseException] = []
        for device, result in zip(self._devices.values(), results, strict=True):
            if isinstance(result, HoiaxAuthError):
                raise ConfigEntryAuthFailed(str(result)) from result
            if isinstance(result, BaseException):
                # One offline tank should not make the others unavailable.
                _LOGGER.debug("Could not update %s: %s", device.device_id, result)
                if not isinstance(result, HoiaxError):
                    raise result
                errors.append(result)
                device.points = {}
                continue
            device.points = result
        if errors and len(errors) == len(self._devices):
            raise UpdateFailed(str(errors[0]))
        return dict(self._devices)

    async def async_write(self, device_id: str, values: dict[str, Any]) -> None:
        """Write values, update state optimistically and refresh shortly after."""
        try:
            await self.client.async_set_points(device_id, values)
        except HoiaxAuthError as err:
            self.config_entry.async_start_reauth(self.hass)
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="auth_failed"
            ) from err
        except HoiaxError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="write_failed",
                translation_placeholders={"error": str(err)},
            ) from err

        device = self._devices.get(device_id)
        if device is not None:
            for parameter_id, value in values.items():
                if (point := device.points.get(parameter_id)) is not None:
                    point.value = value
                    point.text = point.options.get(str(value), point.text)
            self.async_set_updated_data(dict(self._devices))

        if self._cancel_delayed_refresh:
            self._cancel_delayed_refresh()
        self._cancel_delayed_refresh = async_call_later(
            self.hass, REFRESH_DELAY_AFTER_WRITE, self._delayed_refresh
        )

    async def _delayed_refresh(self, _now: Any) -> None:
        self._cancel_delayed_refresh = None
        await self.async_request_refresh()

    async def async_shutdown(self) -> None:
        """Cancel pending timers."""
        if self._cancel_delayed_refresh:
            self._cancel_delayed_refresh()
            self._cancel_delayed_refresh = None
        await super().async_shutdown()
