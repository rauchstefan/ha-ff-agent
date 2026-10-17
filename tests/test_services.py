"""Tests of the actions ff_agent.accept and ff_agent.reject."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import pytest
import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ff_agent.const import DOMAIN

from .common import async_setup_entry
from .const import (
    ACCEPT_URL,
    LATITUDE,
    LOCATION_ENTITY,
    LONGITUDE,
    OTHER_ACCEPT_URL,
    OTHER_REPLY_ID,
    REJECT_URL,
    REPLY_ID,
)

if TYPE_CHECKING:
    from pytest_homeassistant_custom_component.test_util.aiohttp import (
        AiohttpClientMocker,
    )


POSITION = {"latitude": 11.5, "longitude": 12.5}


async def _call(hass: HomeAssistant, service: str, data: dict[str, Any]) -> None:
    await hass.services.async_call(DOMAIN, service, data, blocking=True)


# --- Registration ---------------------------------------------------------------


async def test_actions_exist_even_without_an_entry(hass: HomeAssistant) -> None:
    """The actions are registered once by async_setup, not by an entry."""
    assert await async_setup_component(hass, DOMAIN, {})

    assert hass.services.has_service(DOMAIN, "accept")
    assert hass.services.has_service(DOMAIN, "reject")


async def test_actions_are_registered_when_an_entry_is_set_up(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Setting up an entry sets up the integration and with it the actions."""
    await async_setup_entry(hass, mock_config_entry)

    assert hass.services.has_service(DOMAIN, "accept")
    assert hass.services.has_service(DOMAIN, "reject")


# --- Accept ---------------------------------------------------------------------


async def test_accept_uses_the_default_transport(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Without fields the acceptance carries the default transport and no location."""
    aioclient_mock.get(ACCEPT_URL)
    await async_setup_entry(hass, mock_config_entry)

    await _call(hass, "accept", {"config_entry_id": mock_config_entry.entry_id})

    assert aioclient_mock.call_count == 1
    method, url, _data, _headers = aioclient_mock.mock_calls[0]
    assert method == "GET"
    assert url.path == f"/app2/missionreplies/{REPLY_ID}/accept"
    assert dict(url.query) == {"transport": "CAR"}


async def test_accept_with_transport_and_coordinates(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """The fields are passed on: transport, latitude as lat, longitude as lng."""
    aioclient_mock.get(ACCEPT_URL)
    await async_setup_entry(hass, mock_config_entry)

    await _call(
        hass,
        "accept",
        {
            "config_entry_id": mock_config_entry.entry_id,
            "transport": "car",
            "latitude": LATITUDE,
            "longitude": LONGITUDE,
        },
    )

    url = aioclient_mock.mock_calls[0][1]
    assert dict(url.query) == {
        "transport": "CAR",
        "lat": "1.234500",
        "lng": "6.789000",
    }


async def test_accept_coordinates_win_over_the_location_entity(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    location_entry: MockConfigEntry,
) -> None:
    """Coordinates in the call replace the position of the location entity."""
    aioclient_mock.get(ACCEPT_URL)
    hass.states.async_set(LOCATION_ENTITY, "home", POSITION)
    await async_setup_entry(hass, location_entry)

    await _call(
        hass,
        "accept",
        {
            "config_entry_id": location_entry.entry_id,
            "latitude": LATITUDE,
            "longitude": LONGITUDE,
        },
    )

    url = aioclient_mock.mock_calls[0][1]
    assert dict(url.query) == {
        "transport": "CAR",
        "lat": "1.234500",
        "lng": "6.789000",
    }


async def test_accept_without_coordinates_uses_the_location_entity(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    location_entry: MockConfigEntry,
) -> None:
    """Without coordinates in the call the option decides."""
    aioclient_mock.get(ACCEPT_URL)
    hass.states.async_set(LOCATION_ENTITY, "home", POSITION)
    await async_setup_entry(hass, location_entry)

    await _call(hass, "accept", {"config_entry_id": location_entry.entry_id})

    url = aioclient_mock.mock_calls[0][1]
    assert dict(url.query) == {
        "transport": "CAR",
        "lat": "11.500000",
        "lng": "12.500000",
    }


# --- Reject ---------------------------------------------------------------------


async def test_reject_sends_the_rejection(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """The rejection is a GET to the reject path without a query."""
    aioclient_mock.get(REJECT_URL)
    await async_setup_entry(hass, mock_config_entry)

    await _call(hass, "reject", {"config_entry_id": mock_config_entry.entry_id})

    assert aioclient_mock.call_count == 1
    method, url, _data, _headers = aioclient_mock.mock_calls[0]
    assert method == "GET"
    assert url.path == f"/app2/missionreplies/{REPLY_ID}/reject"
    assert url.query_string == ""


# --- Several people -------------------------------------------------------------


async def test_the_reply_id_of_the_named_entry_is_used(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
    other_entry: MockConfigEntry,
) -> None:
    """With two people each call goes to the URL of the entry that is named."""
    aioclient_mock.get(ACCEPT_URL)
    aioclient_mock.get(OTHER_ACCEPT_URL)
    await async_setup_entry(hass, mock_config_entry)
    await async_setup_entry(hass, other_entry)

    await _call(hass, "accept", {"config_entry_id": other_entry.entry_id})
    assert aioclient_mock.call_count == 1
    assert OTHER_REPLY_ID in aioclient_mock.mock_calls[-1][1].path
    assert REPLY_ID not in aioclient_mock.mock_calls[-1][1].path

    # The repeat guard belongs to the person: the first person can still accept.
    await _call(hass, "accept", {"config_entry_id": mock_config_entry.entry_id})
    assert aioclient_mock.call_count == 2
    assert REPLY_ID in aioclient_mock.mock_calls[-1][1].path
    assert OTHER_REPLY_ID not in aioclient_mock.mock_calls[-1][1].path


# --- Errors ---------------------------------------------------------------------


@pytest.mark.parametrize("service", ["accept", "reject"])
async def test_an_unknown_entry_is_refused(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
    service: str,
) -> None:
    """An entry ID that does not exist raises a validation error, nothing is sent."""
    await async_setup_entry(hass, mock_config_entry)

    with pytest.raises(ServiceValidationError):
        await _call(hass, service, {"config_entry_id": "does-not-exist"})

    assert aioclient_mock.call_count == 0


@pytest.mark.parametrize("service", ["accept", "reject"])
async def test_an_entry_of_another_integration_is_refused(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
    service: str,
) -> None:
    """The ID of an entry of another integration is refused."""
    await async_setup_entry(hass, mock_config_entry)
    foreign = MockConfigEntry(domain="other_integration")
    foreign.add_to_hass(hass)

    with pytest.raises(ServiceValidationError):
        await _call(hass, service, {"config_entry_id": foreign.entry_id})

    assert aioclient_mock.call_count == 0


@pytest.mark.parametrize("service", ["accept", "reject"])
async def test_an_entry_that_is_not_loaded_is_refused(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
    other_entry: MockConfigEntry,
    service: str,
) -> None:
    """A known entry that is not loaded cannot reply."""
    await async_setup_entry(hass, mock_config_entry)
    other_entry.add_to_hass(hass)

    with pytest.raises(ServiceValidationError):
        await _call(hass, service, {"config_entry_id": other_entry.entry_id})

    assert aioclient_mock.call_count == 0


@pytest.mark.parametrize("service", ["accept", "reject"])
async def test_the_entry_is_required(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
    service: str,
) -> None:
    """A call without config_entry_id is refused, even with a single entry."""
    await async_setup_entry(hass, mock_config_entry)

    with pytest.raises(vol.Invalid):
        await _call(hass, service, {})

    assert aioclient_mock.call_count == 0


@pytest.mark.parametrize(
    ("service", "data"),
    [
        # Latitude and longitude only come together.
        ("accept", {"latitude": LATITUDE}),
        ("accept", {"longitude": LONGITUDE}),
        # Out of range.
        ("accept", {"latitude": 90.5, "longitude": LONGITUDE}),
        ("accept", {"latitude": LATITUDE, "longitude": -180.5}),
        # Only verified transports.
        ("accept", {"transport": "BIKE"}),
        ("accept", {"transport": "CAR"}),
        # The rejection has no further fields.
        ("reject", {"transport": "CAR"}),
        ("reject", {"latitude": LATITUDE, "longitude": LONGITUDE}),
    ],
)
async def test_invalid_fields_are_rejected_by_the_schema(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
    service: str,
    data: dict[str, Any],
) -> None:
    """The schema refuses wrong fields before anything is sent."""
    await async_setup_entry(hass, mock_config_entry)

    with pytest.raises(vol.Invalid):
        await _call(
            hass, service, {"config_entry_id": mock_config_entry.entry_id, **data}
        )

    assert aioclient_mock.call_count == 0


@pytest.mark.parametrize(
    ("service", "url", "status", "key"),
    [
        ("accept", ACCEPT_URL, 404, "reply_http_error"),
        ("reject", REJECT_URL, 500, "reply_http_error"),
    ],
)
async def test_an_http_error_is_translated(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
    service: str,
    url: str,
    status: int,
    key: str,
) -> None:
    """A status outside of 2xx is a translated error with the status."""
    caplog.set_level(logging.DEBUG)
    aioclient_mock.get(url, status=status)
    await async_setup_entry(hass, mock_config_entry)

    with pytest.raises(HomeAssistantError) as error:
        await _call(hass, service, {"config_entry_id": mock_config_entry.entry_id})

    assert error.value.translation_key == key
    assert error.value.translation_placeholders == {"status": str(status)}
    assert REPLY_ID not in str(error.value)
    assert REPLY_ID not in caplog.text


async def test_a_connection_error_is_translated(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """A timeout is a translated error without placeholders."""
    aioclient_mock.get(ACCEPT_URL, exc=TimeoutError())
    await async_setup_entry(hass, mock_config_entry)

    with pytest.raises(HomeAssistantError) as error:
        await _call(hass, "accept", {"config_entry_id": mock_config_entry.entry_id})

    assert error.value.translation_key == "reply_connection_error"
