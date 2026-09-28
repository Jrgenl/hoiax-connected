"""Sensors for Høiax Connected."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolume,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import PROGRAMS, Param
from .coordinator import HoiaxConfigEntry, HoiaxCoordinator
from .entity import HoiaxPointEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class HoiaxSensorDescription(SensorEntityDescription):
    """Describes a Høiax sensor."""

    parameter_id: str


SENSORS: tuple[HoiaxSensorDescription, ...] = (
    HoiaxSensorDescription(
        key="temperature",
        translation_key="water_temperature",
        parameter_id=Param.TEMPERATURE,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    HoiaxSensorDescription(
        key="power",
        translation_key="power",
        parameter_id=Param.ESTIMATED_POWER,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=0,
    ),
    HoiaxSensorDescription(
        key="energy_total",
        translation_key="energy_total",
        parameter_id=Param.ENERGY_TOTAL,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
    ),
    HoiaxSensorDescription(
        key="energy_stored",
        translation_key="energy_stored",
        parameter_id=Param.ENERGY_STORED,
        device_class=SensorDeviceClass.ENERGY_STORAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
    ),
    HoiaxSensorDescription(
        key="fill_level",
        translation_key="fill_level",
        parameter_id=Param.FILL_LEVEL,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=0,
    ),
    HoiaxSensorDescription(
        key="current_program",
        translation_key="current_program",
        parameter_id=Param.CURRENT_PROGRAM,
        device_class=SensorDeviceClass.ENUM,
        options=list(PROGRAMS.values()),
    ),
    HoiaxSensorDescription(
        key="next_legionella",
        translation_key="next_legionella",
        parameter_id=Param.HOURS_TO_LEGIONELLA,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    HoiaxSensorDescription(
        key="last_legionella",
        translation_key="last_legionella",
        parameter_id=Param.HOURS_SINCE_LEGIONELLA,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    HoiaxSensorDescription(
        key="tank_volume",
        translation_key="tank_volume",
        parameter_id=Param.TANK_VOLUME,
        device_class=SensorDeviceClass.VOLUME_STORAGE,
        native_unit_of_measurement=UnitOfVolume.LITERS,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    HoiaxSensorDescription(
        key="element_1_runtime",
        translation_key="element_1_runtime",
        parameter_id=Param.ELEMENT_1_RUNTIME,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfTime.HOURS,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    HoiaxSensorDescription(
        key="element_2_runtime",
        translation_key="element_2_runtime",
        parameter_id=Param.ELEMENT_2_RUNTIME,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfTime.HOURS,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    HoiaxSensorDescription(
        key="total_runtime",
        translation_key="total_runtime",
        parameter_id=Param.TOTAL_RUNTIME,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfTime.HOURS,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HoiaxConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors for every parameter the heater reports."""
    coordinator = entry.runtime_data
    async_add_entities(
        HoiaxSensor(coordinator, device_id, description)
        for device_id, device in coordinator.data.items()
        for description in SENSORS
        if description.parameter_id in device.points
    )


class HoiaxSensor(HoiaxPointEntity, SensorEntity):
    """A read-only Høiax value."""

    entity_description: HoiaxSensorDescription

    def __init__(
        self,
        coordinator: HoiaxCoordinator,
        device_id: str,
        description: HoiaxSensorDescription,
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, device_id, description.parameter_id, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | str | None:
        """Return the sensor value."""
        point = self.point(self._parameter_id)
        if point is None or point.value is None:
            return None
        if self.entity_description.device_class == SensorDeviceClass.ENUM:
            return PROGRAMS.get(point.enum_key or "")
        try:
            return float(point.value)
        except (TypeError, ValueError):
            return None
