"""Select entities (program and power level) for Høiax Connected."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import PROGRAM_VALUES, PROGRAMS, Param
from .coordinator import HoiaxConfigEntry, HoiaxCoordinator
from .entity import HoiaxPointEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HoiaxConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up select entities."""
    coordinator = entry.runtime_data
    entities: list[SelectEntity] = []
    for device_id, device in coordinator.data.items():
        program = device.points.get(Param.PROGRAM)
        if program and program.writable and program.options:
            entities.append(HoiaxProgramSelect(coordinator, device_id))
        power = device.points.get(Param.POWER_LEVEL)
        if power and power.writable and power.options:
            entities.append(HoiaxPowerSelect(coordinator, device_id))
    async_add_entities(entities)


class HoiaxProgramSelect(HoiaxPointEntity, SelectEntity):
    """Operating program (Eco, Normal, Schedule, External, Vacation, Boost)."""

    _attr_translation_key = "program"

    def __init__(self, coordinator: HoiaxCoordinator, device_id: str) -> None:
        """Initialise the select."""
        super().__init__(coordinator, device_id, Param.PROGRAM, "program")

    @property
    def options(self) -> list[str]:
        """Programs the heater accepts."""
        point = self.point(Param.PROGRAM)
        if point is None:
            return []
        return [PROGRAMS[value] for value in point.options if value in PROGRAMS]

    @property
    def current_option(self) -> str | None:
        """Return the selected program."""
        point = self.point(Param.PROGRAM)
        return PROGRAMS.get(point.enum_key or "") if point else None

    async def async_select_option(self, option: str) -> None:
        """Change program."""
        await self.coordinator.async_write(
            self._device_id, {Param.PROGRAM: int(PROGRAM_VALUES[option])}
        )


class HoiaxPowerSelect(HoiaxPointEntity, SelectEntity):
    """Maximum heating power (which heating elements may be used)."""

    _attr_translation_key = "power_level"

    def __init__(self, coordinator: HoiaxCoordinator, device_id: str) -> None:
        """Initialise the select."""
        super().__init__(coordinator, device_id, Param.POWER_LEVEL, "power_level")

    @property
    def options(self) -> list[str]:
        """Power steps reported by the heater, e.g. Off / 700W / 1300W / 2000W."""
        point = self.point(Param.POWER_LEVEL)
        return list(point.options.values()) if point else []

    @property
    def current_option(self) -> str | None:
        """Return the current power step."""
        point = self.point(Param.POWER_LEVEL)
        if point is None:
            return None
        return point.options.get(point.enum_key or "")

    async def async_select_option(self, option: str) -> None:
        """Change the power step."""
        point = self.point(Param.POWER_LEVEL)
        assert point is not None
        value = next(key for key, text in point.options.items() if text == option)
        await self.coordinator.async_write(self._device_id, {Param.POWER_LEVEL: int(value)})
