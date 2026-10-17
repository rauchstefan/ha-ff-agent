"""Tests of the reply client: the HTTP request, its errors and the repeat guard.

Every HTTP request goes to the mock of the HTTP client; nothing reaches ff-agent.com.
"""

from __future__ import annotations

import asyncio
import logging
import traceback
from collections.abc import Callable
from datetime import timedelta
from typing import TYPE_CHECKING, Any
from unittest.mock import Mock, patch

import aiohttp
import pytest
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ff_agent.const import (
    DEFAULT_REPLY_HOST,
    MAX_CONTENT_TYPE_CHARS,
    REPLY_REPEAT_GUARD_SECONDS,
    REPLY_TIMEOUT_SECONDS,
    SIGNAL_REPLY,
)
from custom_components.ff_agent.models import ReplyAction, ReplyResult
from custom_components.ff_agent.reply import (
    ReplyClient,
    ReplyConnectionError,
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
    REJECT_URL,
    REPLY_ID,
)

if TYPE_CHECKING:
    from freezegun.api import FrozenDateTimeFactory
    from pytest_homeassistant_custom_component.test_util.aiohttp import (
        AiohttpClientMocker,
    )

ENTRY_ID = "test-entry-id"
LOCATION = (LATITUDE, LONGITUDE)


def _client(hass: HomeAssistant) -> ReplyClient:
    return ReplyClient(hass, ENTRY_ID, DEFAULT_REPLY_HOST, REPLY_ID)


def _request(aioclient_mock: AiohttpClientMocker, index: int = -1) -> Any:
    """Return the URL of a request (a yarl URL) and check that it was a GET."""
    method, url, _data, _headers = aioclient_mock.mock_calls[index]
    assert method == "GET"
    return url


def _log_text(caplog: pytest.LogCaptureFixture) -> str:
    """Return the log messages of this integration."""
    return "\n".join(
        record.getMessage()
        for record in caplog.records
        if record.name.startswith("custom_components.ff_agent")
    )


def _collect_results(hass: HomeAssistant) -> list[ReplyResult]:
    """Collect the results the client sends to the entities."""
    results: list[ReplyResult] = []

    @callback
    def _collect(result: ReplyResult) -> None:
        results.append(result)

    async_dispatcher_connect(hass, SIGNAL_REPLY.format(entry_id=ENTRY_ID), _collect)
    return results


# --- The request ----------------------------------------------------------------


async def test_accept_is_a_get_with_transport_and_location(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """The acceptance is a GET to the accept path, with transport, lat and lng."""
    aioclient_mock.get(ACCEPT_URL)

    result = await _client(hass).async_send(
        ReplyAction.ACCEPT, transport="CAR", location=LOCATION
    )

    assert aioclient_mock.call_count == 1
    url = _request(aioclient_mock)
    assert url.scheme == "https"
    assert url.host == DEFAULT_REPLY_HOST
    assert url.path == f"/app2/missionreplies/{REPLY_ID}/accept"
    # The coordinates have six decimals and a decimal point.
    assert dict(url.query) == {
        "transport": "CAR",
        "lat": "1.234500",
        "lng": "6.789000",
    }
    assert result.success is True
    assert result.status == 200
    assert result.action is ReplyAction.ACCEPT
    assert result.skipped is False
    assert result.error_type is None


@pytest.mark.parametrize(
    ("transport", "location", "expected"),
    [
        (None, None, {}),
        ("CAR", None, {"transport": "CAR"}),
        (None, LOCATION, {"lat": "1.234500", "lng": "6.789000"}),
    ],
)
async def test_accept_sends_only_what_is_given(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    transport: str | None,
    location: tuple[float, float] | None,
    expected: dict[str, str],
) -> None:
    """Transport and location are optional; without them there is no query."""
    aioclient_mock.get(ACCEPT_URL)

    await _client(hass).async_send(
        ReplyAction.ACCEPT, transport=transport, location=location
    )

    assert dict(_request(aioclient_mock).query) == expected


async def test_reject_is_a_get_without_a_query(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A rejection never sends a transport or a location, even if it is given."""
    aioclient_mock.get(REJECT_URL)

    result = await _client(hass).async_send(
        ReplyAction.REJECT, transport="CAR", location=LOCATION
    )

    url = _request(aioclient_mock)
    assert url.path == f"/app2/missionreplies/{REPLY_ID}/reject"
    assert url.query_string == ""
    assert result.success is True
    assert result.action is ReplyAction.REJECT


async def test_request_has_a_timeout_of_ten_seconds(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """The request is limited by the total timeout of the constant."""
    aioclient_mock.get(ACCEPT_URL)

    with patch(
        "custom_components.ff_agent.reply.aiohttp.ClientTimeout",
        wraps=aiohttp.ClientTimeout,
    ) as timeout:
        await _client(hass).async_send(ReplyAction.ACCEPT)

    timeout.assert_called_once_with(total=REPLY_TIMEOUT_SECONDS)
    assert REPLY_TIMEOUT_SECONDS == 10


@pytest.mark.parametrize("status", [200, 201, 204, 299])
async def test_every_2xx_is_a_success(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, status: int
) -> None:
    """Success is any status from 200 to 299; the body does not matter."""
    aioclient_mock.get(ACCEPT_URL, status=status, text="whatever")

    result = await _client(hass).async_send(ReplyAction.ACCEPT)

    assert result.success is True
    assert result.status == status


async def test_the_body_is_neither_used_nor_logged(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The content type is kept, cut to its limit; the body is not in the result."""
    caplog.set_level(logging.DEBUG)
    aioclient_mock.get(
        ACCEPT_URL,
        text="BODY-PLACEHOLDER",
        headers={"Content-Type": "t" * (MAX_CONTENT_TYPE_CHARS + 50)},
    )

    result = await _client(hass).async_send(ReplyAction.ACCEPT)

    assert result.content_type == "t" * MAX_CONTENT_TYPE_CHARS
    assert "BODY-PLACEHOLDER" not in repr(result)
    assert "BODY-PLACEHOLDER" not in caplog.text


async def test_a_missing_content_type_is_none(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Without a Content-Type header there is no content type in the result."""
    aioclient_mock.get(ACCEPT_URL)

    result = await _client(hass).async_send(ReplyAction.ACCEPT)

    assert result.content_type is None


# --- Errors ---------------------------------------------------------------------


@pytest.mark.parametrize("status", [301, 400, 404, 500, 503])
async def test_a_status_outside_of_2xx_raises_http_error(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    status: int,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The status is raised and stored, nothing else about the answer."""
    caplog.set_level(logging.DEBUG)
    aioclient_mock.get(ACCEPT_URL, status=status)
    client = _client(hass)

    with pytest.raises(ReplyHttpError) as error:
        await client.async_send(ReplyAction.ACCEPT)

    assert error.value.status == status
    assert REPLY_ID not in str(error.value)
    result = client.last_result
    assert result is not None
    assert (result.success, result.status, result.error_type) == (False, status, None)
    assert f"HTTP status {status}" in _log_text(caplog)
    counters = (client.attempts_total, client.succeeded_total, client.failed_total)
    assert counters == (1, 0, 1)


def _timeout() -> BaseException:
    return TimeoutError()


def _client_error() -> BaseException:
    return aiohttp.ClientError()


def _connection_error() -> BaseException:
    # The text of real aiohttp errors contains the URL.
    return aiohttp.ClientConnectionError(f"Cannot connect to {ACCEPT_URL}")


def _disconnected() -> BaseException:
    return aiohttp.ServerDisconnectedError(f"Server {ACCEPT_URL} disconnected")


def _response_error() -> BaseException:
    return aiohttp.ClientResponseError(
        Mock(real_url=ACCEPT_URL), (), status=500, message="Too many redirects"
    )


@pytest.mark.parametrize(
    ("factory", "name"),
    [
        (_timeout, "TimeoutError"),
        (_client_error, "ClientError"),
        (_connection_error, "ClientConnectionError"),
        (_disconnected, "ServerDisconnectedError"),
        (_response_error, "ClientResponseError"),
    ],
)
async def test_a_connection_problem_raises_an_error_without_the_url(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    caplog: pytest.LogCaptureFixture,
    factory: Callable[[], BaseException],
    name: str,
) -> None:
    """Only the class name is kept; no text, cause or context carries the URL."""
    caplog.set_level(logging.DEBUG)
    aioclient_mock.get(ACCEPT_URL, exc=factory())
    client = _client(hass)

    with pytest.raises(ReplyConnectionError) as error:
        await client.async_send(ReplyAction.ACCEPT, transport="CAR", location=LOCATION)

    assert error.value.error_type == name
    assert error.value.__cause__ is None
    assert error.value.__context__ is None
    assert error.value.__suppress_context__ is True
    rendered = "".join(traceback.format_exception(error.value))
    assert REPLY_ID not in rendered
    assert REPLY_ID not in str(error.value)
    assert REPLY_ID not in caplog.text
    assert name in _log_text(caplog)
    result = client.last_result
    assert result is not None
    assert (result.success, result.status, result.error_type) == (False, None, name)


async def test_a_failure_does_not_block_the_next_try(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """The repeat guard only follows a success."""
    aioclient_mock.get(ACCEPT_URL, status=500)
    client = _client(hass)
    with pytest.raises(ReplyHttpError):
        await client.async_send(ReplyAction.ACCEPT)

    aioclient_mock.clear_requests()
    aioclient_mock.get(ACCEPT_URL)
    result = await client.async_send(ReplyAction.ACCEPT)

    assert result.success is True
    assert aioclient_mock.call_count == 1
    counters = (client.attempts_total, client.succeeded_total, client.failed_total)
    assert counters == (2, 1, 1)


# --- Repeat guard ---------------------------------------------------------------


async def test_the_same_reply_twice_is_sent_once(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A second acceptance right after the first one makes no request."""
    aioclient_mock.get(ACCEPT_URL)
    client = _client(hass)
    results = _collect_results(hass)

    first = await client.async_send(ReplyAction.ACCEPT)
    second = await client.async_send(ReplyAction.ACCEPT)
    await hass.async_block_till_done()

    assert aioclient_mock.call_count == 1
    assert (first.skipped, second.skipped) == (False, True)
    assert second.success is True
    # The skipped reply is not a result: the sensor keeps the first one.
    assert client.last_result is first
    assert results == [first]
    assert (client.attempts_total, client.skipped_total) == (1, 1)


async def test_two_simultaneous_presses_send_one_request(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """The lock serializes a double click; the second reply is then skipped."""
    aioclient_mock.get(ACCEPT_URL)
    client = _client(hass)

    results = await asyncio.gather(
        client.async_send(ReplyAction.ACCEPT), client.async_send(ReplyAction.ACCEPT)
    )

    assert aioclient_mock.call_count == 1
    assert sorted(result.skipped for result in results) == [False, True]


async def test_accept_then_reject_sends_both(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A different reply is not a repetition."""
    aioclient_mock.get(ACCEPT_URL)
    aioclient_mock.get(REJECT_URL)
    client = _client(hass)

    await client.async_send(ReplyAction.ACCEPT)
    await client.async_send(ReplyAction.REJECT)

    assert aioclient_mock.call_count == 2
    first = _request(aioclient_mock, 0)
    second = _request(aioclient_mock, 1)
    assert first.path.endswith("/accept")
    assert second.path.endswith("/reject")


@pytest.mark.parametrize(
    ("first", "second"),
    [
        (ReplyAction.ACCEPT, ReplyAction.REJECT),
        (ReplyAction.REJECT, ReplyAction.ACCEPT),
    ],
)
async def test_only_the_last_success_counts_for_the_guard(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    first: ReplyAction,
    second: ReplyAction,
) -> None:
    """First, second, first within the window sends three requests.

    FF Agent holds the second reply by then, so the third one must not be skipped.
    """
    aioclient_mock.get(ACCEPT_URL)
    aioclient_mock.get(REJECT_URL)
    client = _client(hass)

    results = [
        await client.async_send(first),
        await client.async_send(second),
        await client.async_send(first),
        # Now the last success is `first` again: a fourth call is a repetition.
        await client.async_send(first),
    ]

    assert [result.skipped for result in results] == [False, False, False, True]
    assert aioclient_mock.call_count == 3
    paths = [_request(aioclient_mock, i).path for i in range(3)]
    assert [path.rsplit("/", 1)[1] for path in paths] == [
        first.value,
        second.value,
        first.value,
    ]
    assert client.skipped_total == 1


async def test_the_guard_expires_after_eleven_seconds(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Within ten seconds the second acceptance is skipped, after eleven it is sent."""
    aioclient_mock.get(ACCEPT_URL)
    client = _client(hass)
    await client.async_send(ReplyAction.ACCEPT)

    freezer.tick(timedelta(seconds=REPLY_REPEAT_GUARD_SECONDS - 1))
    assert (await client.async_send(ReplyAction.ACCEPT)).skipped is True
    assert aioclient_mock.call_count == 1

    freezer.tick(timedelta(seconds=2))
    assert (await client.async_send(ReplyAction.ACCEPT)).skipped is False
    assert aioclient_mock.call_count == 2


async def test_a_clock_that_jumps_back_does_not_block(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    """A negative time difference is not a repetition."""
    aioclient_mock.get(ACCEPT_URL)
    client = _client(hass)
    await client.async_send(ReplyAction.ACCEPT)

    freezer.tick(timedelta(seconds=-30))
    result = await client.async_send(ReplyAction.ACCEPT)

    assert result.skipped is False
    assert aioclient_mock.call_count == 2


async def test_results_are_dispatched_for_success_and_failure(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """The entities hear about every real attempt."""
    aioclient_mock.get(ACCEPT_URL, status=500)
    aioclient_mock.get(REJECT_URL)
    client = _client(hass)
    results = _collect_results(hass)

    with pytest.raises(ReplyHttpError):
        await client.async_send(ReplyAction.ACCEPT)
    await client.async_send(ReplyAction.REJECT)
    await hass.async_block_till_done()

    assert [(r.action, r.success) for r in results] == [
        (ReplyAction.ACCEPT, False),
        (ReplyAction.REJECT, True),
    ]


# --- Location of an entity ------------------------------------------------------


async def test_resolve_location_reads_the_attributes(hass: HomeAssistant) -> None:
    """Latitude and longitude of the state are returned as floats."""
    hass.states.async_set(
        LOCATION_ENTITY, "home", {"latitude": LATITUDE, "longitude": LONGITUDE}
    )

    assert resolve_location(hass, LOCATION_ENTITY) == LOCATION


@pytest.mark.parametrize(
    "attributes",
    [
        {},
        {"latitude": LATITUDE},
        {"longitude": LONGITUDE},
        {"latitude": None, "longitude": None},
        {"latitude": "north", "longitude": "east"},
        {"latitude": 90.5, "longitude": LONGITUDE},
        {"latitude": LATITUDE, "longitude": -180.5},
        {"latitude": float("nan"), "longitude": LONGITUDE},
        {"latitude": LATITUDE, "longitude": float("inf")},
    ],
)
async def test_resolve_location_without_usable_coordinates(
    hass: HomeAssistant,
    attributes: dict[str, Any],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Missing, unparsable or impossible coordinates give None and a quiet log."""
    caplog.set_level(logging.DEBUG)
    hass.states.async_set(LOCATION_ENTITY, "not_home", attributes)

    assert resolve_location(hass, LOCATION_ENTITY) is None

    log = _log_text(caplog)
    assert "Location entity" in log
    assert LOCATION_ENTITY not in log
    assert str(LATITUDE) not in log
    assert str(LONGITUDE) not in log


async def test_resolve_location_of_a_missing_entity(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    """An entity that does not exist gives None; its name is not logged."""
    caplog.set_level(logging.DEBUG)

    assert resolve_location(hass, LOCATION_ENTITY) is None

    assert "Location entity not found" in _log_text(caplog)
    assert LOCATION_ENTITY not in _log_text(caplog)


# --- async_send_reply: values from the options and error mapping ------------------


async def test_options_provide_the_default_transport_and_the_location(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    location_entry: MockConfigEntry,
) -> None:
    """Without explicit values an acceptance uses the options of the entry."""
    aioclient_mock.get(ACCEPT_URL)
    hass.states.async_set(
        LOCATION_ENTITY, "home", {"latitude": LATITUDE, "longitude": LONGITUDE}
    )
    await async_setup_entry(hass, location_entry)

    await async_send_reply(hass, location_entry, ReplyAction.ACCEPT)

    assert dict(_request(aioclient_mock).query) == {
        "transport": "CAR",
        "lat": "1.234500",
        "lng": "6.789000",
    }


async def test_without_the_option_no_location_is_sent(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """The default is to send no location, even if a person entity exists."""
    aioclient_mock.get(ACCEPT_URL)
    hass.states.async_set(
        LOCATION_ENTITY, "home", {"latitude": LATITUDE, "longitude": LONGITUDE}
    )
    await async_setup_entry(hass, mock_config_entry)

    await async_send_reply(hass, mock_config_entry, ReplyAction.ACCEPT)

    assert dict(_request(aioclient_mock).query) == {"transport": "CAR"}


async def test_an_entity_without_coordinates_sends_no_location(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    location_entry: MockConfigEntry,
) -> None:
    """The acceptance still works if the location entity has no position."""
    aioclient_mock.get(ACCEPT_URL)
    hass.states.async_set(LOCATION_ENTITY, "unknown", {})
    await async_setup_entry(hass, location_entry)

    result = await async_send_reply(hass, location_entry, ReplyAction.ACCEPT)

    assert result.success is True
    assert dict(_request(aioclient_mock).query) == {"transport": "CAR"}


async def test_explicit_values_win_over_the_options(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    location_entry: MockConfigEntry,
) -> None:
    """An explicit location replaces the one of the entity."""
    aioclient_mock.get(ACCEPT_URL)
    hass.states.async_set(
        LOCATION_ENTITY, "home", {"latitude": LATITUDE, "longitude": LONGITUDE}
    )
    await async_setup_entry(hass, location_entry)

    await async_send_reply(
        hass,
        location_entry,
        ReplyAction.ACCEPT,
        transport="car",
        location=(10.0, 20.5),
    )

    assert dict(_request(aioclient_mock).query) == {
        "transport": "CAR",
        "lat": "10.000000",
        "lng": "20.500000",
    }


async def test_a_rejection_ignores_transport_and_location(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    location_entry: MockConfigEntry,
) -> None:
    """The options do not leak into a rejection."""
    aioclient_mock.get(REJECT_URL)
    hass.states.async_set(
        LOCATION_ENTITY, "home", {"latitude": LATITUDE, "longitude": LONGITUDE}
    )
    await async_setup_entry(hass, location_entry)

    await async_send_reply(
        hass, location_entry, ReplyAction.REJECT, transport="CAR", location=LOCATION
    )

    assert _request(aioclient_mock).query_string == ""


async def test_an_unknown_default_transport_falls_back_to_car(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Only verified transports are sent, also if an option holds another value."""
    aioclient_mock.get(ACCEPT_URL)
    await async_setup_entry(hass, mock_config_entry)
    hass.config_entries.async_update_entry(
        mock_config_entry,
        options={**mock_config_entry.options, "default_transport": "BIKE"},
    )

    await async_send_reply(hass, mock_config_entry, ReplyAction.ACCEPT)

    assert dict(_request(aioclient_mock).query) == {"transport": "CAR"}


async def test_an_unknown_explicit_transport_is_refused_before_any_request(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """An explicit transport that is not verified raises a validation error."""
    await async_setup_entry(hass, mock_config_entry)

    with pytest.raises(ServiceValidationError) as error:
        await async_send_reply(
            hass, mock_config_entry, ReplyAction.ACCEPT, transport="BIKE"
        )

    assert error.value.translation_key == "invalid_transport"
    assert error.value.translation_placeholders == {"transport": "BIKE"}
    assert aioclient_mock.call_count == 0


async def test_errors_are_translated_and_carry_no_url(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """HTTP and connection errors become translated errors of Home Assistant."""
    await async_setup_entry(hass, mock_config_entry)

    aioclient_mock.get(ACCEPT_URL, status=404)
    with pytest.raises(HomeAssistantError) as http_error:
        await async_send_reply(hass, mock_config_entry, ReplyAction.ACCEPT)
    assert http_error.value.translation_domain == "ff_agent"
    assert http_error.value.translation_key == "reply_http_error"
    assert http_error.value.translation_placeholders == {"status": "404"}

    aioclient_mock.clear_requests()
    aioclient_mock.get(ACCEPT_URL, exc=_connection_error())
    with pytest.raises(HomeAssistantError) as connection_error:
        await async_send_reply(hass, mock_config_entry, ReplyAction.ACCEPT)
    assert connection_error.value.translation_domain == "ff_agent"
    assert connection_error.value.translation_key == "reply_connection_error"
    assert connection_error.value.translation_placeholders is None

    for error in (http_error.value, connection_error.value):
        assert error.__cause__ is None
        assert error.__suppress_context__ is True
        assert REPLY_ID not in str(error)
        assert REPLY_ID not in "".join(traceback.format_exception(error))
