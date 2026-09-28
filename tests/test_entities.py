"""Entity and setup tests."""

from __future__ import annotations

import json

from homeassistant.components.water_heater import (
    ATTR_OPERATION_MODE,
    DOMAIN as WATER_HEATER_DOMAIN,
    SERVICE_SET_OPERATION_MODE,
    SERVICE_SET_TEMPERATURE,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_ENTITY_ID, ATTR_TEMPERATURE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.hoiax.diagnostics import async_get_config_entry_diagnostics

from .conftest import mock_cloud

WATER_HEATER = "water_heater.hoiax_connected_200"


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_setup_creates_entities(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, config_entry: MockConfigEntry
) -> None:
    """All main entities are created with sensible states."""
    mock_cloud(aioclient_mock)
    await _setup(hass, config_entry)
    assert config_entry.state is ConfigEntryState.LOADED

    state = hass.states.get(WATER_HEATER)
    assert state is not None
    assert state.state == "external"
    assert state.attributes["current_temperature"] == 54.2
    assert state.attributes["temperature"] == 60
    assert state.attributes["min_temp"] == 20
    assert state.attributes["max_temp"] == 85
    assert "off" in state.attributes["operation_list"]

    assert hass.states.get("sensor.hoiax_connected_200_water_temperature").state == "54.2"
    assert hass.states.get("sensor.hoiax_connected_200_power").state == "1910.0"
    energy = hass.states.get("sensor.hoiax_connected_200_energy_consumption")
    assert energy.state == "30.4"
    assert energy.attributes["state_class"] == "total_increasing"
    assert hass.states.get("sensor.hoiax_connected_200_hot_water_level").state == "100.0"
    assert hass.states.get("sensor.hoiax_connected_200_active_program").state == "external"
    assert hass.states.get("select.hoiax_connected_200_program").state == "external"
    assert hass.states.get("select.hoiax_connected_200_max_power").state == "2000W"
    assert hass.states.get("binary_sensor.hoiax_connected_200_heating_element_1").state == "on"
    assert hass.states.get("number.hoiax_connected_200_boost_temperature").state == "80.0"

    registry = er.async_get(hass)
    ambient = registry.async_get("number.hoiax_connected_200_ambient_temperature")
    assert ambient is not None and ambient.disabled_by is not None


async def test_set_temperature_and_mode(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, config_entry: MockConfigEntry
) -> None:
    """Writes go to myUplink with the right parameter ids."""
    mock_cloud(aioclient_mock)
    await _setup(hass, config_entry)

    await hass.services.async_call(
        WATER_HEATER_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {ATTR_ENTITY_ID: WATER_HEATER, ATTR_TEMPERATURE: 65},
        blocking=True,
    )
    patches = [call for call in aioclient_mock.mock_calls if call[0] == "PATCH"]
    assert patches[-1][2] == {"527": 65}
    assert hass.states.get(WATER_HEATER).attributes["temperature"] == 65

    await hass.services.async_call(
        WATER_HEATER_DOMAIN,
        SERVICE_SET_OPERATION_MODE,
        {ATTR_ENTITY_ID: WATER_HEATER, ATTR_OPERATION_MODE: "off"},
        blocking=True,
    )
    patches = [call for call in aioclient_mock.mock_calls if call[0] == "PATCH"]
    assert patches[-1][2] == {"517": 0}
    assert hass.states.get(WATER_HEATER).state == "off"

    await hass.services.async_call(
        WATER_HEATER_DOMAIN,
        SERVICE_SET_OPERATION_MODE,
        {ATTR_ENTITY_ID: WATER_HEATER, ATTR_OPERATION_MODE: "eco"},
        blocking=True,
    )
    patches = [call for call in aioclient_mock.mock_calls if call[0] == "PATCH"]
    assert patches[-1][2] == {"500": 3, "517": 3}
    assert hass.states.get(WATER_HEATER).state == "eco"


async def test_auth_failure_starts_reauth(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, config_entry: MockConfigEntry
) -> None:
    """A rejected password puts the entry in reauth instead of failing silently."""
    mock_cloud(aioclient_mock, login_ok=False)
    config_entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress()
    assert any(flow["context"]["source"] == "reauth" for flow in flows)


async def test_diagnostics_redacts_secrets(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, config_entry: MockConfigEntry
) -> None:
    """Diagnostics never contain the password, e-mail or serial number."""
    mock_cloud(aioclient_mock)
    await _setup(hass, config_entry)
    diag = await async_get_config_entry_diagnostics(hass, config_entry)
    dumped = json.dumps(diag, default=str)
    assert "secret" not in dumped
    assert "user@example.com" not in dumped
    assert "12345678" not in dumped
    assert diag["devices"][0]["points"]["528"]["value"] == 54.2
