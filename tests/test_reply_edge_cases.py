"""Edge cases of the reply path: redirects, odd answers, odd input, races.

Every HTTP request goes to the mock of the HTTP client; nothing reaches ff-agent.com.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ff_agent.const import (
    DEFAULT_REPLY_HOST,
    DOMAIN,
    REPLY_REPEAT_GUARD_SECONDS,
    REPLY_TIMEOUT_SECONDS,
)
from custom_components.ff_agent.models import ReplyAction
from custom_components.ff_agent.reply import (
    ReplyClient,
    ReplyHttpError,
    async_send_reply,
    resolve_location,
)

from .common import async_setup_entry
from .const import (
    ACCEPT_URL,
    LATITUDE,
    LOCATION_ENTITY,
    LONGITUDE,
    OTHER_ACCEPT_URL,
    OTHER_REPLY_ID,
    REPLY_ID,
)

if TYPE_CHECKING:
    from freezegun.api import FrozenDateTimeFactory
    from pytest_homeassistant_custom_component.test_util.aiohttp import (
        AiohttpClientMocker,
    )

ENTRY_ID = "test-entry-id"


def _client(hass: HomeAssistant) -> ReplyClient:
    return ReplyClient(hass, ENTRY_ID, DEFAULT_REPLY_HOST, REPLY_ID)


def _entity_id(
    hass: HomeAssistant, entry: MockConfigEntry, platform: str, key: str
) -> str:
    entity_id = er.async_get(hass).async_get_entity_id(
        platform, DOMAIN, f"{entry.entry_id}_{key}"
    )
    assert entity_id is not None
    return entity_id


def _press(hass: HomeAssistant, entry: MockConfigEntry, key: str) -> Any:
    return hass.services.async_call(
        "button",
        "press",
        {ATTR_ENTITY_ID: _entity_id(hass, entry, "button", key)},
        blocking=True,
    )


def _last_reply(hass: HomeAssistant, entry: MockConfigEntry) -> str:
    state = hass.states.get(_entity_id(hass, entry, "sensor", "last_reply"))
    assert state is not None
    return state.state


# --- Redirects (they are followed to any host) -----------------------------------


async def test_redirects_are_followed(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Documents the behaviour: the request is made with allow_redirects=True.

    The plan prescribes this. aiohttp then follows a Location header to any host,
    also to another one and also to plain http. The secret ID is only part of the
    first URL, so it reaches another host only if the answer repeats it in the
    Location header. The target of a redirect is not checked by the integration.
    The mock of the HTTP client does not follow redirects, so only the flag can be
    checked here.
    """
    aioclient_mock.get(ACCEPT_URL)
    session = async_get_clientsession(hass)

    with patch.object(session, "_request", wraps=session._request) as spy:
        await _client(hass).async_send(ReplyAction.ACCEPT)

    assert spy.call_count == 1
    assert spy.call_args.kwargs["allow_redirects"] is True
    assert spy.call_args.kwargs["timeout"].total == REPLY_TIMEOUT_SECONDS


async def test_an_unfollowed_redirect_status_is_a_failure(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A 3xx that arrives at the client (no Location, loop) is not a success."""
    aioclient_mock.get(ACCEPT_URL, status=302, headers={"Location": "/elsewhere"})

    with pytest.raises(ReplyHttpError) as error:
        await _client(hass).async_send(ReplyAction.ACCEPT)

    assert error.value.status == 302


# --- A 200 answer that did not record the reply (A7) ------------------------------


async def test_a_200_html_page_counts_as_success(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Assumption A7: FF Agent answers 200 with a page even without an active mission.

    The integration cannot tell, so it reports success. The body is never evaluated.
    """
    caplog.set_level(logging.DEBUG)
    aioclient_mock.get(
        ACCEPT_URL,
        text="<html><body>Kein aktiver Einsatz</body></html>",
        headers={"Content-Type": "text/html"},
    )
    await async_setup_entry(hass, mock_config_entry)

    await _press(hass, mock_config_entry, "accept")

    assert _last_reply(hass, mock_config_entry) == "accepted"
    assert "Kein aktiver Einsatz" not in caplog.text


# --- Transport spelling ----------------------------------------------------------


@pytest.mark.parametrize("transport", ["CAR", "Car", " car", "car ", ""])
async def test_transport_must_match_exactly(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
    transport: str,
) -> None:
    """Only the exact lower case spelling is accepted; there is no normalization."""
    await async_setup_entry(hass, mock_config_entry)

    with pytest.raises(ServiceValidationError) as error:
        await async_send_reply(
            hass, mock_config_entry, ReplyAction.ACCEPT, transport=transport
        )

    assert error.value.translation_key == "invalid_transport"
    assert aioclient_mock.call_count == 0


@pytest.mark.parametrize(
    "option", ["car", "CAR", "Car", " car", "", "bike", None, 5, ["car"]]
)
async def test_every_default_transport_option_sends_car(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
    option: object,
) -> None:
    """The option "car", the old value "CAR" and anything else all send CAR."""
    aioclient_mock.get(ACCEPT_URL)
    await async_setup_entry(hass, mock_config_entry)
    hass.config_entries.async_update_entry(
        mock_config_entry,
        options={**mock_config_entry.options, "default_transport": option},
    )

    await async_send_reply(hass, mock_config_entry, ReplyAction.ACCEPT)

    assert dict(aioclient_mock.mock_calls[-1][1].query) == {"transport": "CAR"}


# --- Coordinates as strings -------------------------------------------------------


async def test_the_action_accepts_coordinates_as_strings(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """The validators of Home Assistant turn numeric strings into floats."""
    aioclient_mock.get(ACCEPT_URL)
    await async_setup_entry(hass, mock_config_entry)

    await hass.services.async_call(
        DOMAIN,
        "accept",
        {
            "config_entry_id": mock_config_entry.entry_id,
            "latitude": "1.2345",
            "longitude": "6.789",
        },
        blocking=True,
    )

    query = dict(aioclient_mock.mock_calls[-1][1].query)
    assert query["lat"] == "1.234500"
    assert query["lng"] == "6.789000"


async def test_state_attributes_as_strings_are_used(hass: HomeAssistant) -> None:
    """Some trackers store the coordinates as text."""
    hass.states.async_set(
        LOCATION_ENTITY, "home", {"latitude": "1.2345", "longitude": " 6.789 "}
    )

    assert resolve_location(hass, LOCATION_ENTITY) == (LATITUDE, LONGITUDE)


@pytest.mark.parametrize(
    "attributes",
    [
        {"latitude": "1,2345", "longitude": "6,789"},
        {"latitude": "", "longitude": ""},
        {"latitude": "nan", "longitude": "6.789"},
        {"latitude": [1.0], "longitude": [2.0]},
    ],
)
async def test_state_attributes_as_odd_strings_give_no_location(
    hass: HomeAssistant, attributes: dict[str, Any]
) -> None:
    """Decimal commas, empty text, NaN and wrong types do not raise."""
    hass.states.async_set(LOCATION_ENTITY, "home", attributes)

    assert resolve_location(hass, LOCATION_ENTITY) is None


# --- Boundaries ---------------------------------------------------------------------


async def test_the_repeat_guard_ends_exactly_at_its_limit(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Just before the limit a repetition is skipped, at the limit it is sent."""
    aioclient_mock.get(ACCEPT_URL)
    client = _client(hass)
    await client.async_send(ReplyAction.ACCEPT)

    freezer.tick(timedelta(seconds=REPLY_REPEAT_GUARD_SECONDS, microseconds=-1))
    assert (await client.async_send(ReplyAction.ACCEPT)).skipped is True

    freezer.tick(timedelta(microseconds=1))
    assert (await client.async_send(ReplyAction.ACCEPT)).skipped is False
    assert aioclient_mock.call_count == 2


# --- Two people at the same time ----------------------------------------------------


async def test_two_entries_pressed_at_the_same_time_use_their_own_ids(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
    other_entry: MockConfigEntry,
) -> None:
    """Both presses are sent, each to its own URL, and each sensor shows its result."""
    aioclient_mock.get(ACCEPT_URL)
    aioclient_mock.get(OTHER_ACCEPT_URL, status=404)
    await async_setup_entry(hass, mock_config_entry)
    await async_setup_entry(hass, other_entry)

    results = await asyncio.gather(
        _press(hass, mock_config_entry, "accept"),
        _press(hass, other_entry, "accept"),
        return_exceptions=True,
    )

    assert aioclient_mock.call_count == 2
    paths = sorted(call[1].path for call in aioclient_mock.mock_calls)
    assert paths == sorted(
        [
            f"/app2/missionreplies/{REPLY_ID}/accept",
            f"/app2/missionreplies/{OTHER_REPLY_ID}/accept",
        ]
    )
    # The failure of one person does not touch the other one.
    assert results[0] is None
    assert isinstance(results[1], Exception)
    assert _last_reply(hass, mock_config_entry) == "accepted"
    assert _last_reply(hass, other_entry) == "failed"


# --- Unload while a reply is on its way ---------------------------------------------


async def test_a_reply_in_flight_while_the_entry_unloads_and_reloads(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """The reply still ends cleanly; the reloaded entry starts without a result."""
    aioclient_mock.get(ACCEPT_URL)
    await async_setup_entry(hass, mock_config_entry)
    old_client = mock_config_entry.runtime_data.reply

    started = asyncio.Event()
    release = asyncio.Event()
    session = async_get_clientsession(hass)
    original = session._request

    async def _slow(*args: Any, **kwargs: Any) -> Any:
        started.set()
        await release.wait()
        return await original(*args, **kwargs)

    with patch.object(session, "_request", _slow):
        task = hass.async_create_task(
            async_send_reply(hass, mock_config_entry, ReplyAction.ACCEPT)
        )
        await started.wait()
        assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
        assert mock_config_entry.state is ConfigEntryState.NOT_LOADED
        release.set()
        result = await task

    await hass.async_block_till_done()
    assert result.success is True
    assert old_client.last_result is result

    # A reload creates a new client: no result, and the repeat guard starts again.
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    new_client = mock_config_entry.runtime_data.reply
    assert new_client is not old_client
    assert new_client.last_result is None
    assert _last_reply(hass, mock_config_entry) == "unknown"
