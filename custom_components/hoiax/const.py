"""Constants for the Høiax Connected integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "hoiax"
MANUFACTURER: Final = "Høiax"

API_BASE_URL: Final = "https://internalapi.myuplink.com"
TOKEN_URL: Final = f"{API_BASE_URL}/oauth/token"
# Same public client the myUplink web app uses, so users only need their
# normal myUplink e-mail and password (no developer app registration).
CLIENT_ID: Final = "My-Uplink-Web"

CONF_SCAN_INTERVAL: Final = "scan_interval"
DEFAULT_SCAN_INTERVAL: Final = 60
MIN_SCAN_INTERVAL: Final = 30
MAX_SCAN_INTERVAL: Final = 600

# myUplink needs a few seconds before a written value is reflected on reads.
REFRESH_DELAY_AFTER_WRITE: Final = timedelta(seconds=5)


class Param:
    """myUplink parameter ids used by Høiax Connected water heaters."""

    AMBIENT_TEMPERATURE: Final = "100"
    INLET_TEMPERATURE: Final = "101"
    DEFAULT_ECO_SETPOINT: Final = "102"
    BOOST_SETPOINT: Final = "200"
    BOOST_DURATION: Final = "201"
    VACATION_SETPOINT: Final = "300"
    VACATION_DURATION: Final = "301"
    ENERGY_STORED: Final = "302"
    ENERGY_TOTAL: Final = "303"
    ESTIMATED_POWER: Final = "400"
    FILL_LEVEL: Final = "404"
    CURRENT_PROGRAM: Final = "406"
    PROGRAM: Final = "500"
    PROGRAM_TIMEOUT: Final = "501"
    ELEMENT_2_POWER: Final = "503"
    ELEMENT_1_POWER: Final = "504"
    ELEMENT_2_ON: Final = "505"
    ELEMENT_1_ON: Final = "506"
    ELEMENT_2_RUNTIME: Final = "507"
    ELEMENT_1_RUNTIME: Final = "508"
    HOURS_SINCE_LEGIONELLA: Final = "509"
    LEGIONELLA_INTERVAL: Final = "511"
    MAX_WATER_FLOW: Final = "512"
    MODEL_ID: Final = "513"
    HOURS_TO_LEGIONELLA: Final = "514"
    HYSTERESIS: Final = "516"
    POWER_LEVEL: Final = "517"
    SERIAL_NUMBER: Final = "518"
    TANK_VOLUME: Final = "526"
    SETPOINT: Final = "527"
    TEMPERATURE: Final = "528"
    TOTAL_RUNTIME: Final = "531"


# Program (parameter 500 / 406) values -> stable keys used as HA options.
PROGRAMS: Final[dict[str, str]] = {
    "0": "test",
    "1": "off",
    "2": "sleep",
    "3": "eco",
    "4": "normal",
    "5": "express",
    "6": "smart",
    "7": "schedule",
    "8": "external",
    "9": "legionella",
    "10": "vacation",
    "11": "boost",
}
PROGRAM_VALUES: Final[dict[str, str]] = {key: value for value, key in PROGRAMS.items()}

PROGRAM_EXTERNAL: Final = "8"
PROGRAM_VACATION: Final = "10"

# Power level (parameter 517) value 0 means heating elements off.
POWER_OFF: Final = "0"
