"""Water heater entity for Høiax Connected."""

from __future__ import annotations

from typing import Any

from homeassistant.components.water_heater import (
    STATE_OFF,
    WaterHeaterEntity,
    WaterHeaterEntityFeature,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    POWER_OFF,
    PROGRAM_VACATION,
    PROGRAM_VALUES,
    PROGRAMS,
    Param,
)
from .coordinator import HoiaxConfigEntry, HoiaxCoordinator
from .entity import HoiaxEntity

PARALLEL_UPDATES = 1

DEFAULT_MIN_TEMP = 20.0
DEFAULT_MAX_TEMP = 85.0
FALLBACK_PROGRAM = "4"  # Normal


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HoiaxConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up one water heater entity per tank."""
    coordinator = entry.runtime_data
    async_add_entities(
        HoiaxWaterHeater(coordinator, device_id)
        for device_id, device in coordinator.data.items()
        if Param.TEMPERATURE in device.points or Param.SETPOINT in device.points
    )


class HoiaxWaterHeater(HoiaxEntity, WaterHeaterEntity):
    """The water heater itself: temperature, setpoint, program and on/off."""

    _attr_name = None
    _attr_translation_key = "water_heater"
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 1

    def __init__(self, coordinator: HoiaxCoordinator, device_id: str) -> None:
        """Initialise the water heater."""
        super().__init__(coordinator, device_id, "water_heater")
        self._last_program = FALLBACK_PROGRAM

    def _program_key(self) -> str | None:
        point = self.point(Param.PROGRAM)
        return point.enum_key if point else None

    def _is_off(self) -> bool:
        point = self.point(Param.POWER_LEVEL)
        return point is not None and point.enum_key == POWER_OFF

    def _max_power_value(self) -> int | None:
        point = self.point(Param.POWER_LEVEL)
        if point is None or not point.options:
            return None
        return max(int(key) for key in point.options)

    @property
    def supported_features(self) -> WaterHeaterEntityFeature:
        """Only advertise what this heater exposes as writable."""
        features = WaterHeaterEntityFeature(0)
        if (point := self.point(Param.SETPOINT)) and point.writable:
            features |= WaterHeaterEntityFeature.TARGET_TEMPERATURE
        if (point := self.point(Param.PROGRAM)) and point.writable:
            features |= WaterHeaterEntityFeature.OPERATION_MODE
            if PROGRAM_VACATION in point.options:
                features |= WaterHeaterEntityFeature.AWAY_MODE
        if (point := self.point(Param.POWER_LEVEL)) and point.writable:
            features |= WaterHeaterEntityFeature.ON_OFF
        return features

    @property
    def current_temperature(self) -> float | None:
        """Measured water temperature."""
        value = self.device.value(Param.TEMPERATURE)
        return None if value is None else float(value)

    @property
    def target_temperature(self) -> float | None:
        """Setpoint."""
        value = self.device.value(Param.SETPOINT)
        return None if value is None else float(value)

    @property
    def min_temp(self) -> float:
        """Lowest allowed setpoint."""
        point = self.point(Param.SETPOINT)
        return point.min_value if point and point.min_value is not None else DEFAULT_MIN_TEMP

    @property
    def max_temp(self) -> float:
        """Highest allowed setpoint."""
        point = self.point(Param.SETPOINT)
        return point.max_value if point and point.max_value is not None else DEFAULT_MAX_TEMP

    @property
    def operation_list(self) -> list[str] | None:
        """Selectable programs, plus off when power can be switched off."""
        point = self.point(Param.PROGRAM)
        if point is None:
            return None
        modes = [PROGRAMS[value] for value in point.options if value in PROGRAMS]
        if WaterHeaterEntityFeature.ON_OFF in self.supported_features:
            modes.append(STATE_OFF)
        return modes

    @property
    def current_operation(self) -> str | None:
        """Current program, or off when the heating elements are disabled."""
        if self._is_off():
            return STATE_OFF
        return PROGRAMS.get(self._program_key() or "")

    @property
    def is_away_mode_on(self) -> bool | None:
        """Vacation program is used as away mode."""
        return self._program_key() == PROGRAM_VACATION

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Handy extras for dashboards and automations."""
        attrs: dict[str, Any] = {}
        for key, param in (
            ("fill_level", Param.FILL_LEVEL),
            ("energy_stored", Param.ENERGY_STORED),
            ("power", Param.ESTIMATED_POWER),
        ):
            if (value := self.device.value(param)) is not None:
                attrs[key] = value
        if (point := self.point(Param.POWER_LEVEL)) is not None:
            attrs["power_level"] = point.options.get(point.enum_key or "", point.text)
        return attrs

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set a new setpoint."""
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is None:
            return
        await self.coordinator.async_write(
            self._device_id, {Param.SETPOINT: round(float(temperature))}
        )

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        """Change program, or switch heating off."""
        if operation_mode == STATE_OFF:
            await self.async_turn_off()
            return
        values: dict[str, Any] = {Param.PROGRAM: int(PROGRAM_VALUES[operation_mode])}
        if self._is_off() and (max_power := self._max_power_value()) is not None:
            values[Param.POWER_LEVEL] = max_power
        await self.coordinator.async_write(self._device_id, values)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Allow full heating power again."""
        if (max_power := self._max_power_value()) is not None:
            await self.coordinator.async_write(self._device_id, {Param.POWER_LEVEL: max_power})

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Switch the heating elements off."""
        await self.coordinator.async_write(self._device_id, {Param.POWER_LEVEL: int(POWER_OFF)})

    async def async_turn_away_mode_on(self) -> None:
        """Start the vacation program."""
        current = self._program_key()
        if current and current != PROGRAM_VACATION:
            self._last_program = current
        await self.coordinator.async_write(self._device_id, {Param.PROGRAM: int(PROGRAM_VACATION)})

    async def async_turn_away_mode_off(self) -> None:
        """Return to the program used before vacation."""
        await self.coordinator.async_write(
            self._device_id, {Param.PROGRAM: int(self._last_program)}
        )
