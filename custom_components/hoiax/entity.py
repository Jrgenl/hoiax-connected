"""Base entity for Høiax Connected."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import HoiaxDevice, HoiaxPoint
from .const import DOMAIN, MANUFACTURER, Param
from .coordinator import HoiaxCoordinator


class HoiaxEntity(CoordinatorEntity[HoiaxCoordinator]):
    """Common base for all Høiax entities (one HA device per water heater)."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: HoiaxCoordinator, device_id: str, key: str) -> None:
        """Initialise the entity."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_{key}"
        device = self.device
        model = device.model or "Connected"
        serial = device.value(Param.SERIAL_NUMBER) or device.serial_number
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            manufacturer=MANUFACTURER,
            name=device.name if device.name.startswith("Høiax") else f"Høiax {device.name}",
            model=model,
            model_id=str(device.value(Param.MODEL_ID) or "") or None,
            serial_number=str(serial) if serial else None,
            sw_version=device.firmware,
            configuration_url="https://myuplink.com",
        )

    @property
    def device(self) -> HoiaxDevice:
        """Return the current device data."""
        return self.coordinator.data[self._device_id]

    def point(self, parameter_id: str) -> HoiaxPoint | None:
        """Return a data point on this device."""
        return self.device.points.get(parameter_id)

    @property
    def available(self) -> bool:
        """Entities are available while the device reports data."""
        return (
            super().available
            and self._device_id in self.coordinator.data
            and bool(self.device.points)
        )


class HoiaxPointEntity(HoiaxEntity):
    """Entity bound to a single myUplink parameter."""

    def __init__(
        self, coordinator: HoiaxCoordinator, device_id: str, parameter_id: str, key: str
    ) -> None:
        """Initialise the entity."""
        super().__init__(coordinator, device_id, key)
        self._parameter_id = parameter_id

    @property
    def available(self) -> bool:
        """Only available while the parameter is reported."""
        return super().available and self._parameter_id in self.device.points
