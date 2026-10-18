"""Tests of the location source: which position an acceptance carries.

The sources are none, the home position of Home Assistant, coordinates typed in by
hand and the location of a person or device tracker. Every HTTP request goes to the
mock of the HTTP client; the positions are invented.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ff_agent.const import (
    CONF_LOCATION_ENTITY,
    CONF_LOCATION_LATITUDE,
    CONF_LOCATION_LONGITUDE,
    CONF_LOCATION_SOURCE,
    LOCATION_SOURCE_ENTITY,
    LOCATION_SOURCE_HOME,
    LOCATION_SOURCE_MANUAL,
    LOCATION_SOURCE_NONE,
)
from custom_components.ff_agent.models import ReplyAction
from custom_components.ff_agent.reply import (
    async_send_reply,
    configured_location_source,
    home_position,
    resolve_configured_location,
    valid_latitude,
    valid_longitude,
)

from .common import async_setup_entry
from .const import (
    ACCEPT_URL,
    LATITUDE,
    LOCATION_ENTITY,
    LONGITUDE,
    MANUAL_LATITUDE,
    MANUAL_LONGITUDE,
    REJECT_URL,
)

if TYPE_CHECKING:
    from pytest_homeassistant_custom_component.test_util.aiohttp import (
        AiohttpClientMocker,
    )

POSITION = {"latitude": LATITUDE, "longitude": LONGITUDE}
HOME_QUERY = {"transport": "CAR", "lat": "1.234500", "lng": "6.789000"}
MANUAL_QUERY = {"transport": "CAR", "lat": "12.345600", "lng": "-65.432100"}
NO_LOCATION = {"transport": "CAR"}


def _query(aioclient_mock: AiohttpClientMocker) -> dict[str, str]:
    """Return the query of the only request."""
    assert aioclient_mock.call_count == 1
    method, url, _data, _headers = aioclient_mock.mock_calls[0]
    assert method == "GET"
    return dict(url.query)


def _log_text(caplog: pytest.LogCaptureFixture) -> str:
    """Return the log messages of this integration."""
    return "\n".join(
        record.getMessage()
        for record in caplog.records
        if record.name.startswith("custom_components.ff_agent")
    )


def _set_home(hass: HomeAssistant, latitude: float, longitude: float) -> None:
    hass.config.latitude = latitude
    hass.config.longitude = longitude


# --- Which source applies ------------------------------------------------------


@pytest.mark.parametrize(
    ("options", "expected"),
    [
        # Options from before the source existed.
        ({}, LOCATION_SOURCE_NONE),
        ({CONF_LOCATION_ENTITY: LOCATION_ENTITY}, LOCATION_SOURCE_ENTITY),
        ({CONF_LOCATION_ENTITY: ""}, LOCATION_SOURCE_NONE),
        ({CONF_LOCATION_ENTITY: None}, LOCATION_SOURCE_NONE),
        # The stored source wins, also over a leftover location entity.
        ({CONF_LOCATION_SOURCE: LOCATION_SOURCE_NONE}, LOCATION_SOURCE_NONE),
        (
            {
                CONF_LOCATION_SOURCE: LOCATION_SOURCE_NONE,
                CONF_LOCATION_ENTITY: LOCATION_ENTITY,
            },
            LOCATION_SOURCE_NONE,
        ),
        ({CONF_LOCATION_SOURCE: LOCATION_SOURCE_HOME}, LOCATION_SOURCE_HOME),
        ({CONF_LOCATION_SOURCE: LOCATION_SOURCE_MANUAL}, LOCATION_SOURCE_MANUAL),
        ({CONF_LOCATION_SOURCE: LOCATION_SOURCE_ENTITY}, LOCATION_SOURCE_ENTITY),
        # Unknown values are treated like a missing one.
        ({CONF_LOCATION_SOURCE: "satellite"}, LOCATION_SOURCE_NONE),
        ({CONF_LOCATION_SOURCE: 7}, LOCATION_SOURCE_NONE),
        (
            {CONF_LOCATION_SOURCE: "satellite", CONF_LOCATION_ENTITY: LOCATION_ENTITY},
            LOCATION_SOURCE_ENTITY,
        ),
    ],
)
def test_the_location_source_of_the_options(
    options: dict[str, Any], expected: str
) -> None:
    """Old options without a source are derived from the location entity."""
    assert configured_location_source(options) == expected


@pytest.mark.parametrize(
    ("value", "latitude", "longitude"),
    [
        (0, True, True),
        (90, True, True),
        (-90, True, True),
        (90.0001, False, True),
        (-90.0001, False, True),
        (180, False, True),
        (-180, False, True),
        (180.0001, False, False),
        (12.5, True, True),
        ("12.5", True, True),
        ("north", False, False),
        (None, False, False),
        ([], False, False),
        (float("nan"), False, False),
        (float("inf"), False, False),
        (float("-inf"), False, False),
        (10**400, False, False),
    ],
)
def test_coordinates_are_checked(value: Any, latitude: bool, longitude: bool) -> None:
    """Latitude and longitude have their own range; NaN and infinity are refused."""
    assert valid_latitude(value) is latitude
    assert valid_longitude(value) is longitude


# --- The home position ---------------------------------------------------------


async def test_the_home_position_is_read_from_the_core_configuration(
    hass: HomeAssistant,
) -> None:
    """The position is read every time, so a change applies to the next reply."""
    options = {CONF_LOCATION_SOURCE: LOCATION_SOURCE_HOME}
    _set_home(hass, LATITUDE, LONGITUDE)
    assert resolve_configured_location(hass, options) == (LATITUDE, LONGITUDE)

    _set_home(hass, MANUAL_LATITUDE, MANUAL_LONGITUDE)
    assert resolve_configured_location(hass, options) == (
        MANUAL_LATITUDE,
        MANUAL_LONGITUDE,
    )


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [(0, 0), (0.0, 0.0), (91, 6.789), (1.2345, 181), (float("nan"), 6.789)],
)
async def test_an_unset_or_invalid_home_position_is_not_used(
    hass: HomeAssistant,
    caplog: pytest.LogCaptureFixture,
    latitude: float,
    longitude: float,
) -> None:
    """0, 0 is what Home Assistant has before the position is set: no location."""
    caplog.set_level(logging.DEBUG)
    _set_home(hass, latitude, longitude)

    location = resolve_configured_location(
        hass, {CONF_LOCATION_SOURCE: LOCATION_SOURCE_HOME}
    )

    assert home_position(hass) is None
    assert location is None
    assert "Home position is not set" in _log_text(caplog)
    assert "6.789" not in _log_text(caplog)


async def test_the_home_source_sends_the_home_position(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    home_location_entry: MockConfigEntry,
) -> None:
    """The acceptance carries the position of Home Assistant; nothing is stored."""
    aioclient_mock.get(ACCEPT_URL)
    _set_home(hass, LATITUDE, LONGITUDE)
    await async_setup_entry(hass, home_location_entry)

    await async_send_reply(hass, home_location_entry, ReplyAction.ACCEPT)

    assert _query(aioclient_mock) == HOME_QUERY
    assert CONF_LOCATION_LATITUDE not in home_location_entry.options
    assert CONF_LOCATION_LONGITUDE not in home_location_entry.options


async def test_the_home_source_without_a_position_still_accepts(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    home_location_entry: MockConfigEntry,
) -> None:
    """Without a home position the acceptance goes out without a location."""
    aioclient_mock.get(ACCEPT_URL)
    _set_home(hass, 0, 0)
    await async_setup_entry(hass, home_location_entry)

    result = await async_send_reply(hass, home_location_entry, ReplyAction.ACCEPT)

    assert result.success is True
    assert _query(aioclient_mock) == NO_LOCATION


# --- Manual coordinates --------------------------------------------------------


async def test_the_manual_source_sends_the_stored_coordinates(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    manual_location_entry: MockConfigEntry,
) -> None:
    """The stored coordinates are sent, not the home position."""
    aioclient_mock.get(ACCEPT_URL)
    _set_home(hass, LATITUDE, LONGITUDE)
    await async_setup_entry(hass, manual_location_entry)

    await async_send_reply(hass, manual_location_entry, ReplyAction.ACCEPT)

    assert _query(aioclient_mock) == MANUAL_QUERY


@pytest.mark.parametrize(
    "options",
    [
        {},
        {CONF_LOCATION_LATITUDE: MANUAL_LATITUDE},
        {CONF_LOCATION_LONGITUDE: MANUAL_LONGITUDE},
        {CONF_LOCATION_LATITUDE: None, CONF_LOCATION_LONGITUDE: None},
        {CONF_LOCATION_LATITUDE: "north", CONF_LOCATION_LONGITUDE: "east"},
        {CONF_LOCATION_LATITUDE: 95, CONF_LOCATION_LONGITUDE: MANUAL_LONGITUDE},
        {CONF_LOCATION_LATITUDE: MANUAL_LATITUDE, CONF_LOCATION_LONGITUDE: 181},
        {
            CONF_LOCATION_LATITUDE: float("nan"),
            CONF_LOCATION_LONGITUDE: MANUAL_LONGITUDE,
        },
    ],
)
async def test_unusable_manual_coordinates_send_no_location(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture, options: dict[str, Any]
) -> None:
    """Missing or impossible coordinates give no location; they are not logged."""
    caplog.set_level(logging.DEBUG)

    location = resolve_configured_location(
        hass, {CONF_LOCATION_SOURCE: LOCATION_SOURCE_MANUAL, **options}
    )

    assert location is None
    assert "Manual location is missing or invalid" in _log_text(caplog)
    for value in (MANUAL_LATITUDE, MANUAL_LONGITUDE):
        assert str(value) not in _log_text(caplog)


# --- The entity (as before) ----------------------------------------------------


async def test_the_entity_source_sends_the_location_of_the_entity(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    location_entry: MockConfigEntry,
) -> None:
    """The live position of the entity is sent, not the home position."""
    aioclient_mock.get(ACCEPT_URL)
    hass.states.async_set(LOCATION_ENTITY, "home", POSITION)
    _set_home(hass, MANUAL_LATITUDE, MANUAL_LONGITUDE)
    await async_setup_entry(hass, location_entry)

    await async_send_reply(hass, location_entry, ReplyAction.ACCEPT)

    assert _query(aioclient_mock) == HOME_QUERY


async def test_an_entry_from_before_the_source_keeps_its_entity(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    legacy_location_entry: MockConfigEntry,
) -> None:
    """Options with a location entity but no source work as the source "entity"."""
    aioclient_mock.get(ACCEPT_URL)
    hass.states.async_set(LOCATION_ENTITY, "home", POSITION)
    await async_setup_entry(hass, legacy_location_entry)
    assert CONF_LOCATION_SOURCE not in legacy_location_entry.options

    await async_send_reply(hass, legacy_location_entry, ReplyAction.ACCEPT)

    assert _query(aioclient_mock) == HOME_QUERY


async def test_the_entity_source_without_an_entity_sends_no_location(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    """A source "entity" without an entity cannot happen in the flow; it is safe."""
    caplog.set_level(logging.DEBUG)

    location = resolve_configured_location(
        hass, {CONF_LOCATION_SOURCE: LOCATION_SOURCE_ENTITY}
    )

    assert location is None
    assert "No location entity chosen" in _log_text(caplog)


# --- None, priority and rejections ---------------------------------------------


async def test_the_source_none_ignores_a_leftover_entity(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """An explicit "none" wins over a location entity that is still stored."""
    aioclient_mock.get(ACCEPT_URL)
    hass.states.async_set(LOCATION_ENTITY, "home", POSITION)
    await async_setup_entry(hass, mock_config_entry)
    hass.config_entries.async_update_entry(
        mock_config_entry,
        options={**mock_config_entry.options, CONF_LOCATION_ENTITY: LOCATION_ENTITY},
    )

    await async_send_reply(hass, mock_config_entry, ReplyAction.ACCEPT)

    assert _query(aioclient_mock) == NO_LOCATION


@pytest.mark.parametrize(
    "fixture", ["home_location_entry", "manual_location_entry", "location_entry"]
)
async def test_explicit_coordinates_win_over_every_source(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    request: pytest.FixtureRequest,
    fixture: str,
) -> None:
    """Coordinates from the action replace the position of the source."""
    entry: MockConfigEntry = request.getfixturevalue(fixture)
    aioclient_mock.get(ACCEPT_URL)
    hass.states.async_set(LOCATION_ENTITY, "home", POSITION)
    _set_home(hass, LATITUDE, LONGITUDE)
    await async_setup_entry(hass, entry)

    await async_send_reply(hass, entry, ReplyAction.ACCEPT, location=(10.0, 20.5))

    assert _query(aioclient_mock) == {
        "transport": "CAR",
        "lat": "10.000000",
        "lng": "20.500000",
    }


@pytest.mark.parametrize(
    "fixture", ["home_location_entry", "manual_location_entry", "location_entry"]
)
async def test_a_rejection_never_sends_a_location(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    request: pytest.FixtureRequest,
    fixture: str,
) -> None:
    """Whatever the source is, a rejection has no query at all."""
    entry: MockConfigEntry = request.getfixturevalue(fixture)
    aioclient_mock.get(REJECT_URL)
    hass.states.async_set(LOCATION_ENTITY, "home", POSITION)
    _set_home(hass, LATITUDE, LONGITUDE)
    await async_setup_entry(hass, entry)

    await async_send_reply(hass, entry, ReplyAction.REJECT)

    assert aioclient_mock.call_count == 1
    assert aioclient_mock.mock_calls[0][1].query_string == ""
