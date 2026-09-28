"""Fixtures for Høiax Connected tests."""

from __future__ import annotations

import json
from pathlib import Path

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.hoiax.const import API_BASE_URL, DOMAIN, TOKEN_URL

DEVICE_ID = "HOIAX_aabbccddeeff_00000000-0000-0000-0000-000000000000"
FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading custom integrations in all tests."""
    return


def load_points() -> list[dict]:
    """Return the recorded myUplink points for a Connected 200."""
    return json.loads((FIXTURES / "points.json").read_text(encoding="utf-8"))


def mock_cloud(aioclient_mock: AiohttpClientMocker, *, login_ok: bool = True) -> None:
    """Register fake myUplink responses."""
    if login_ok:
        aioclient_mock.post(
            TOKEN_URL,
            json={"access_token": "token", "expires_in": 3600, "refresh_token": "refresh"},
        )
    else:
        aioclient_mock.post(
            TOKEN_URL,
            status=400,
            json={"error": "invalid_grant", "error_description": "invalid_username_or_password"},
        )
    aioclient_mock.get(
        f"{API_BASE_URL}/v2/systems/me?itemsPerPage=100",
        json={
            "systems": [
                {
                    "name": "Hjemme",
                    "devices": [
                        {
                            "id": DEVICE_ID,
                            "connectionState": "Connected",
                            "currentFwVersion": "1.23",
                            "product": {"name": "Høiax Connected 200", "serialNumber": "123"},
                        }
                    ],
                }
            ]
        },
    )
    aioclient_mock.get(f"{API_BASE_URL}/v2/devices/{DEVICE_ID}/points", json=load_points())
    aioclient_mock.patch(f"{API_BASE_URL}/v2/devices/{DEVICE_ID}/points", json={"527": "modified"})


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """A configured Høiax entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="user@example.com",
        unique_id="user@example.com",
        data={CONF_USERNAME: "user@example.com", CONF_PASSWORD: "secret"},
    )
