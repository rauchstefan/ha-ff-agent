"""Tests of the buttons "accept" and "decline" and of the sensor "last reply"."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING

import aiohttp
import pytest
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, State
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ff_agent import button
from custom_components.ff_agent.const import CONF_DEFAULT_TRANSPORT, DOMAIN

from .common import async_setup_entry
from .const import (
    ACCEPT_URL,
    LATITUDE,
    LOCATION_ENTITY,
    LONGITUDE,
    REJECT_URL,
    REPLY_ID,
    WEBHOOK_ID,
)

if TYPE_CHECKING:
    from freezegun.api import FrozenDateTimeFactory
    from pytest_homeassistant_custom_component.test_util.aiohttp import (
        AiohttpClientMocker,
    )


def _entity_id(
    hass: HomeAssistant, entry: MockConfigEntry, platform: str, key: str
) -> str:
    """Return the entity ID of an entity of the entry, looked up by its unique ID."""
    entity_id = er.async_get(hass).async_get_entity_id(
        platform, DOMAIN, f"{entry.entry_id}_{key}"
    )
    assert entity_id is not None
    return entity_id


def _state(hass: HomeAssistant, entity_id: str) -> State:
    state = hass.states.get(entity_id)
    assert state is not None
    return state


async def _press(hass: HomeAssistant, entry: MockConfigEntry, key: str) -> None:
    """Press one of the buttons of the entry."""
    await hass.services.async_call(
        "button",
        "press",
        {ATTR_ENTITY_ID: _entity_id(hass, entry, "button", key)},
        blocking=True,
    )


def _last_reply(hass: HomeAssistant, entry: MockConfigEntry) -> str:
    """Return the state of the sensor "last reply"."""
    return _state(hass, _entity_id(hass, entry, "sensor", "last_reply")).state


# --- Entities -------------------------------------------------------------------


def test_the_button_platform_does_not_update_in_parallel() -> None:
    """Only one reply at a time (PARALLEL_UPDATES)."""
    assert button.PARALLEL_UPDATES == 1


async def test_buttons_and_sensor_exist_and_belong_to_the_device(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Two buttons and the sensor share the service device of the entry."""
    await async_setup_entry(hass, mock_config_entry)

    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, mock_config_entry.entry_id), mock_config_entry.entry_id
    )
    assert device is not None
    registry = er.async_get(hass)
    for platform, key in (
        ("button", "accept"),
        ("button", "reject"),
        ("sensor", "last_reply"),
    ):
        entity = registry.async_get(_entity_id(hass, mock_config_entry, platform, key))
        assert entity is not None
        assert entity.device_id == device.id
        assert entity.has_entity_name is True
        assert entity.translation_key == key
        for secret in (REPLY_ID, WEBHOOK_ID):
            assert secret not in entity.unique_id
            assert secret not in entity.entity_id


@pytest.mark.parametrize(
    ("language", "names"),
    [
        ("en", ["FF Agent Test Accept", "FF Agent Test Decline"]),
        ("de", ["FF Agent Test Zusagen", "FF Agent Test Absagen"]),
    ],
)
async def test_button_names_are_translated(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    language: str,
    names: list[str],
) -> None:
    """The names of the buttons come from the translations."""
    hass.config.language = language
    await async_setup_entry(hass, mock_config_entry)

    keys = ("accept", "reject")
    ids = [_entity_id(hass, mock_config_entry, "button", key) for key in keys]
    assert [_state(hass, i).attributes["friendly_name"] for i in ids] == names


@pytest.mark.parametrize(
    ("language", "name"),
    [("en", "FF Agent Test Last reply"), ("de", "FF Agent Test Letzte Rückmeldung")],
)
async def test_last_reply_sensor_is_translated(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    language: str,
    name: str,
) -> None:
    """The sensor has a translated name and starts without a value."""
    hass.config.language = language
    await async_setup_entry(hass, mock_config_entry)

    state = _state(hass, _entity_id(hass, mock_config_entry, "sensor", "last_reply"))
    assert state.attributes["friendly_name"] == name
    assert state.state == "unknown"


async def test_last_reply_sensor_is_an_enum_without_attributes(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """The three results are the options; there are no further attributes."""
    await async_setup_entry(hass, mock_config_entry)

    state = _state(hass, _entity_id(hass, mock_config_entry, "sensor", "last_reply"))
    assert state.attributes["device_class"] == "enum"
    assert state.attributes["options"] == ["accepted", "rejected", "failed"]
    assert set(state.attributes) == {"friendly_name", "device_class", "options"}


# --- Pressing -------------------------------------------------------------------


async def test_pressing_accept_sends_the_acceptance_with_the_default_transport(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """The button sends a GET to the accept URL with transport=CAR, no location."""
    aioclient_mock.get(ACCEPT_URL)
    await async_setup_entry(hass, mock_config_entry)
    button_id = _entity_id(hass, mock_config_entry, "button", "accept")
    assert _state(hass, button_id).state == "unknown"

    await _press(hass, mock_config_entry, "accept")

    assert aioclient_mock.call_count == 1
    method, url, _data, _headers = aioclient_mock.mock_calls[0]
    assert method == "GET"
    assert url.path == f"/app2/missionreplies/{REPLY_ID}/accept"
    assert dict(url.query) == {"transport": "CAR"}
    assert _last_reply(hass, mock_config_entry) == "accepted"
    # The state of a button is the time of the press.
    assert _state(hass, button_id).state != "unknown"


@pytest.mark.parametrize(
    ("option", "expected"),
    [("car", "CAR"), ("feet", "FEET"), ("bicycle", "BICYCLE")],
)
async def test_accept_button_sends_the_transport_of_the_option(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
    option: str,
    expected: str,
) -> None:
    """The default transport of the options decides the query of the button."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=mock_config_entry.title,
        unique_id=mock_config_entry.unique_id,
        data=dict(mock_config_entry.data),
        options={**mock_config_entry.options, CONF_DEFAULT_TRANSPORT: option},
    )
    aioclient_mock.get(ACCEPT_URL)
    await async_setup_entry(hass, entry)

    await _press(hass, entry, "accept")

    assert aioclient_mock.call_count == 1
    url = aioclient_mock.mock_calls[0][1]
    assert dict(url.query) == {"transport": expected}


async def test_pressing_reject_sends_the_rejection(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """The button sends a GET to the reject URL without a query."""
    aioclient_mock.get(REJECT_URL)
    await async_setup_entry(hass, mock_config_entry)

    await _press(hass, mock_config_entry, "reject")

    assert aioclient_mock.call_count == 1
    _method, url, _data, _headers = aioclient_mock.mock_calls[0]
    assert url.path == f"/app2/missionreplies/{REPLY_ID}/reject"
    assert url.query_string == ""
    assert _last_reply(hass, mock_config_entry) == "rejected"


async def test_accept_button_sends_the_location_of_the_option(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    location_entry: MockConfigEntry,
) -> None:
    """With a location entity in the options the acceptance carries lat and lng."""
    aioclient_mock.get(ACCEPT_URL)
    hass.states.async_set(
        LOCATION_ENTITY, "home", {"latitude": LATITUDE, "longitude": LONGITUDE}
    )
    await async_setup_entry(hass, location_entry)

    await _press(hass, location_entry, "accept")

    url = aioclient_mock.mock_calls[0][1]
    assert dict(url.query) == {
        "transport": "CAR",
        "lat": "1.234500",
        "lng": "6.789000",
    }


async def test_a_double_press_sends_one_request(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """The second press right after the first one makes no request."""
    aioclient_mock.get(ACCEPT_URL)
    await async_setup_entry(hass, mock_config_entry)

    await _press(hass, mock_config_entry, "accept")
    await _press(hass, mock_config_entry, "accept")

    assert aioclient_mock.call_count == 1
    assert _last_reply(hass, mock_config_entry) == "accepted"


async def test_pressing_again_after_the_guard_sends_again(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """After eleven seconds the same button works again."""
    aioclient_mock.get(ACCEPT_URL)
    await async_setup_entry(hass, mock_config_entry)
    await _press(hass, mock_config_entry, "accept")

    freezer.tick(timedelta(seconds=11))
    await _press(hass, mock_config_entry, "accept")

    assert aioclient_mock.call_count == 2


async def test_accept_then_reject_changes_the_sensor(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Two different replies are both sent; the sensor shows the last one."""
    aioclient_mock.get(ACCEPT_URL)
    aioclient_mock.get(REJECT_URL)
    await async_setup_entry(hass, mock_config_entry)

    await _press(hass, mock_config_entry, "accept")
    assert _last_reply(hass, mock_config_entry) == "accepted"
    await _press(hass, mock_config_entry, "reject")

    assert aioclient_mock.call_count == 2
    assert _last_reply(hass, mock_config_entry) == "rejected"


# --- Errors ---------------------------------------------------------------------


async def test_an_http_error_is_translated_and_the_sensor_fails(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A 404 becomes a translated error with the status; no address is in it."""
    caplog.set_level(logging.DEBUG)
    aioclient_mock.get(ACCEPT_URL, status=404)
    await async_setup_entry(hass, mock_config_entry)

    with pytest.raises(HomeAssistantError) as error:
        await _press(hass, mock_config_entry, "accept")

    assert error.value.translation_domain == DOMAIN
    assert error.value.translation_key == "reply_http_error"
    assert error.value.translation_placeholders == {"status": "404"}
    assert REPLY_ID not in str(error.value)
    assert _last_reply(hass, mock_config_entry) == "failed"
    assert REPLY_ID not in caplog.text


@pytest.mark.parametrize(
    "exception",
    [TimeoutError(), aiohttp.ClientError()],
    ids=["timeout", "client-error"],
)
async def test_a_connection_error_is_translated_and_the_sensor_fails(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
    exception: BaseException,
) -> None:
    """A timeout or a client error becomes a translated error."""
    aioclient_mock.get(REJECT_URL, exc=exception)
    await async_setup_entry(hass, mock_config_entry)

    with pytest.raises(HomeAssistantError) as error:
        await _press(hass, mock_config_entry, "reject")

    assert error.value.translation_key == "reply_connection_error"
    assert _last_reply(hass, mock_config_entry) == "failed"


async def test_a_failure_followed_by_a_success_shows_the_success(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """The sensor follows the last attempt; a failure does not block the next one."""
    aioclient_mock.get(ACCEPT_URL, status=500)
    await async_setup_entry(hass, mock_config_entry)
    with pytest.raises(HomeAssistantError):
        await _press(hass, mock_config_entry, "accept")
    assert _last_reply(hass, mock_config_entry) == "failed"

    aioclient_mock.clear_requests()
    aioclient_mock.get(ACCEPT_URL)
    await _press(hass, mock_config_entry, "accept")

    assert aioclient_mock.call_count == 1
    assert _last_reply(hass, mock_config_entry) == "accepted"


async def test_unloading_makes_the_entities_unavailable(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """After the unload the buttons and the sensor are unavailable."""
    aioclient_mock.get(ACCEPT_URL)
    await async_setup_entry(hass, mock_config_entry)
    ids = [
        _entity_id(hass, mock_config_entry, "button", "accept"),
        _entity_id(hass, mock_config_entry, "button", "reject"),
        _entity_id(hass, mock_config_entry, "sensor", "last_reply"),
    ]

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    for entity_id in ids:
        assert _state(hass, entity_id).state == "unavailable"


@pytest.mark.parametrize(
    ("first", "second", "states"),
    [
        ("accept", "reject", ["accepted", "rejected", "accepted"]),
        ("reject", "accept", ["rejected", "accepted", "rejected"]),
    ],
)
async def test_changing_your_mind_within_ten_seconds_is_sent_every_time(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
    first: str,
    second: str,
    states: list[str],
) -> None:
    """Accept, decline, accept sends three requests and the sensor follows."""
    aioclient_mock.get(ACCEPT_URL)
    aioclient_mock.get(REJECT_URL)
    await async_setup_entry(hass, mock_config_entry)

    seen = []
    for key in (first, second, first):
        await _press(hass, mock_config_entry, key)
        seen.append(_last_reply(hass, mock_config_entry))

    assert aioclient_mock.call_count == 3
    assert seen == states
