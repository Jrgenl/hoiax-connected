"""Number (settings) entities for Høiax Connected."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import EntityCategory, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import Param
from .coordinator import HoiaxConfigEntry, HoiaxCoordinator
from .entity import HoiaxPointEntity

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class HoiaxNumberDescription(NumberEntityDescription):
    """Describes a writable Høiax setting."""

    parameter_id: str


NUMBERS: tuple[HoiaxNumberDescription, ...] = (
    HoiaxNumberDescription(
        key="boost_setpoint",
        translation_key="boost_setpoint",
        parameter_id=Param.BOOST_SETPOINT,
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=60,
        native_max_value=85,
        entity_category=EntityCategory.CONFIG,
    ),
    HoiaxNumberDescription(
        key="boost_duration",
        translation_key="boost_duration",
        parameter_id=Param.BOOST_DURATION,
        device_class=NumberDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.DAYS,
        native_min_value=1,
        native_max_value=14,
        entity_category=EntityCategory.CONFIG,
    ),
    HoiaxNumberDescription(
        key="vacation_setpoint",
        translation_key="vacation_setpoint",
        parameter_id=Param.VACATION_SETPOINT,
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=35,
        native_max_value=65,
        entity_category=EntityCategory.CONFIG,
    ),
    HoiaxNumberDescription(
        key="vacation_duration",
        translation_key="vacation_duration",
        parameter_id=Param.VACATION_DURATION,
        device_class=NumberDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.DAYS,
        native_min_value=4,
        native_max_value=35,
        entity_category=EntityCategory.CONFIG,
    ),
    HoiaxNumberDescription(
        key="hysteresis",
        translation_key="hysteresis",
        parameter_id=Param.HYSTERESIS,
        device_class=NumberDeviceClass.TEMPERATURE_DELTA,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=3,
        native_max_value=10,
        entity_category=EntityCategory.CONFIG,
    ),
    HoiaxNumberDescription(
        key="legionella_interval",
        translation_key="legionella_interval",
        parameter_id=Param.LEGIONELLA_INTERVAL,
        device_class=NumberDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.WEEKS,
        native_min_value=2,
        native_max_value=8,
        entity_category=EntityCategory.CONFIG,
    ),
    HoiaxNumberDescription(
        key="ambient_temperature",
        translation_key="ambient_temperature",
        parameter_id=Param.AMBIENT_TEMPERATURE,
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=10,
        native_max_value=35,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
    HoiaxNumberDescription(
        key="inlet_temperature",
        translation_key="inlet_temperature",
        parameter_id=Param.INLET_TEMPERATURE,
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=4,
        native_max_value=20,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
    HoiaxNumberDescription(
        key="max_water_flow",
        translation_key="max_water_flow",
        parameter_id=Param.MAX_WATER_FLOW,
        native_unit_of_measurement="L/min",
        native_min_value=5,
        native_max_value=40,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HoiaxConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up number entities for writable parameters."""
    coordinator = entry.runtime_data
    async_add_entities(
        HoiaxNumber(coordinator, device_id, description)
        for device_id, device in coordinator.data.items()
        for description in NUMBERS
        if (point := device.points.get(description.parameter_id)) and point.writable
    )


class HoiaxNumber(HoiaxPointEntity, NumberEntity):
    """A writable numeric Høiax setting."""

    entity_description: HoiaxNumberDescription
    _attr_mode = NumberMode.BOX
    _attr_native_step = 1

    def __init__(
        self,
        coordinator: HoiaxCoordinator,
        device_id: str,
        description: HoiaxNumberDescription,
    ) -> None:
        """Initialise the number entity."""
        super().__init__(coordinator, device_id, description.parameter_id, description.key)
        self.entity_description = description

    @property
    def native_min_value(self) -> float:
        """Use the limits reported by the heater when present."""
        point = self.point(self._parameter_id)
        if point and point.min_value is not None:
            return point.min_value
        return super().native_min_value

    @property
    def native_max_value(self) -> float:
        """Use the limits reported by the heater when present."""
        point = self.point(self._parameter_id)
        if point and point.max_value is not None:
            return point.max_value
        return super().native_max_value

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        point = self.point(self._parameter_id)
        if point is None or point.value is None:
            return None
        try:
            return float(point.value)
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        """Write a new value."""
        await self.coordinator.async_write(self._device_id, {self._parameter_id: round(value)})
