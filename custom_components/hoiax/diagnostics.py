"""Diagnostics support for Høiax Connected."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .const import Param
from .coordinator import HoiaxConfigEntry

TO_REDACT = {
    CONF_USERNAME,
    CONF_PASSWORD,
    "serial_number",
    "device_id",
    "title",
    "unique_id",
}
REDACT_POINTS = {Param.SERIAL_NUMBER, Param.MODEL_ID}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: HoiaxConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry (credentials and serials removed)."""
    coordinator = entry.runtime_data
    devices = []
    for index, device in enumerate(coordinator.data.values()):
        data = asdict(device)
        data["device_id"] = f"device_{index}"
        for parameter_id in REDACT_POINTS:
            if parameter_id in data["points"]:
                data["points"][parameter_id]["value"] = "**REDACTED**"
                data["points"][parameter_id]["text"] = "**REDACTED**"
        devices.append(async_redact_data(data, TO_REDACT - {"device_id"}))
    return {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "devices": devices,
    }
