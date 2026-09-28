"""Binary sensors for Høiax Connected."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import Param
from .coordinator import HoiaxConfigEntry, HoiaxCoordinator
from .entity import HoiaxPointEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class HoiaxBinarySensorDescription(BinarySensorEntityDescription):
    """Describes a Høiax binary sensor."""

    parameter_id: str


BINARY_SENSORS: tuple[HoiaxBinarySensorDescription, ...] = (
    HoiaxBinarySensorDescription(
        key="element_1",
        translation_key="element_1",
        parameter_id=Param.ELEMENT_1_ON,
        device_class=BinarySensorDeviceClass.RUNNING,
    ),
    HoiaxBinarySensorDescription(
        key="element_2",
        translation_key="element_2",
        parameter_id=Param.ELEMENT_2_ON,
        device_class=BinarySensorDeviceClass.RUNNING,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HoiaxConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up binary sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        HoiaxBinarySensor(coordinator, device_id, description)
        for device_id, device in coordinator.data.items()
        for description in BINARY_SENSORS
        if description.parameter_id in device.points
    )


class HoiaxBinarySensor(HoiaxPointEntity, BinarySensorEntity):
    """Heating element on/off."""

    entity_description: HoiaxBinarySensorDescription

    def __init__(
        self,
        coordinator: HoiaxCoordinator,
        device_id: str,
        description: HoiaxBinarySensorDescription,
    ) -> None:
        """Initialise the binary sensor."""
        super().__init__(coordinator, device_id, description.parameter_id, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return True when the heating element is on."""
        point = self.point(self._parameter_id)
        if point is None or point.value is None:
            return None
        return point.enum_key not in (None, "0")
