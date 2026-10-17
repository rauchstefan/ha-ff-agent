"""Tests for the webhook that FF Agent calls.

The tests send calls through the real HTTP view of Home Assistant (a plain
``web.Request``) and through ``webhook.async_handle_webhook`` with a ``MockRequest``,
which is what a call through a Nabu Casa cloudhook looks like.
"""

from __future__ import annotations

import json
import logging
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

import pytest
from homeassistant.components import webhook
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.util.aiohttp import MockRequest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ff_agent.const import (
    DOMAIN,
    ISSUE_TOKEN_REJECTED,
    MAX_CONTENT_TYPE_CHARS,
    MAX_NAME_CHARS,
    MAX_SHAPE_KEYS,
    MAX_USER_AGENT_CHARS,
    TOKEN_HEADER,
)
from custom_components.ff_agent.models import WebhookCall, WebhookStats
from custom_components.ff_agent.webhook import async_capture_call

from .const import HEADER_TOKEN, REPLY_ID, WEBHOOK_ID

if TYPE_CHECKING:
    from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

PATH = f"/api/webhook/{WEBHOOK_ID}"
JSON = {"Content-Type": "application/json"}
# Values that must never show up anywhere. They are invented.
BODY_VALUE = "STICHWORT-PLATZHALTER"
QUERY_VALUE = "query-value-placeholder"
HEADER_VALUE = "header-value-placeholder"


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> WebhookStats:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry.runtime_data.webhook_stats


def _issue(hass: HomeAssistant, entry: MockConfigEntry) -> ir.IssueEntry | None:
    issue_id = ISSUE_TOKEN_REJECTED.format(entry_id=entry.entry_id)
    return ir.async_get(hass).async_get_issue(DOMAIN, issue_id)


def _log_text(caplog: pytest.LogCaptureFixture) -> str:
    """Return the log messages for which this integration is responsible.

    These are all records of the integration and every warning or error of any
    logger. Left out are the DEBUG and INFO records of Home Assistant itself and of
    the test HTTP server: they print the request path and with it the webhook ID
    ("Handling webhook POST payload for ..."), and that is not under our control.
    """
    return "\n".join(
        record.getMessage()
        for record in caplog.records
        if record.name.startswith("custom_components.ff_agent")
        or record.levelno >= logging.WARNING
    )


def _mock_request(
    content: bytes = b"",
    headers: dict[str, str] | None = None,
    query_string: str | None = None,
) -> MockRequest:
    return MockRequest(
        content, "test", method="POST", headers=headers, query_string=query_string
    )


class UnreadableRequest(MockRequest):
    """A request whose body cannot be read."""

    def __init__(self, error: Exception, headers: dict[str, str] | None = None):
        super().__init__(b"", "test", method="POST", headers=headers)
        self._error = error

    async def text(self) -> str:
        """Raise the error instead of returning the body."""
        raise self._error


# --- Calls through the HTTP view ------------------------------------------------


async def test_get_is_accepted_and_counted(
    hass: HomeAssistant,
    hass_client_no_auth: ClientSessionGenerator,
    mock_config_entry: MockConfigEntry,
) -> None:
    """A GET call with a query gets 200 and only its query keys are recorded."""
    stats = await _setup(hass, mock_config_entry)
    client = await hass_client_no_auth()

    response = await client.get(PATH, params={"a": "1"})

    assert response.status == HTTPStatus.OK
    assert (stats.calls_total, stats.rejected_total) == (1, 0)
    call = stats.last_call
    assert call is not None
    assert call.method == "GET"
    assert call.query_keys == ("a",)
    assert call.body_kind == "empty"
    assert call.body_length == 0


async def test_post_is_accepted_and_counted(
    hass: HomeAssistant,
    hass_client_no_auth: ClientSessionGenerator,
    mock_config_entry: MockConfigEntry,
) -> None:
    """A POST call without any body gets 200, every call is counted."""
    stats = await _setup(hass, mock_config_entry)
    client = await hass_client_no_auth()

    assert (await client.post(PATH)).status == HTTPStatus.OK
    assert (await client.post(PATH)).status == HTTPStatus.OK

    assert stats.calls_total == 2
    assert stats.last_call is not None
    assert stats.last_call.method == "POST"
    assert stats.last_call.query_keys == ()
    assert stats.last_call.received_at is not None


async def test_head_is_answered_without_counting(
    hass: HomeAssistant,
    hass_client_no_auth: ClientSessionGenerator,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Home Assistant answers HEAD itself, the handler does not run."""
    stats = await _setup(hass, mock_config_entry)
    client = await hass_client_no_auth()

    response = await client.head(PATH)

    assert response.status == HTTPStatus.OK
    assert stats.calls_total == 0


async def test_unsupported_method_is_rejected(
    hass: HomeAssistant,
    hass_client_no_auth: ClientSessionGenerator,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Only GET and POST are registered, so PUT gets 405."""
    stats = await _setup(hass, mock_config_entry)
    client = await hass_client_no_auth()

    response = await client.put(PATH)

    assert response.status == HTTPStatus.METHOD_NOT_ALLOWED
    assert stats.calls_total == 0


async def test_json_body_keeps_only_the_shape(
    hass: HomeAssistant,
    hass_client_no_auth: ClientSessionGenerator,
    mock_config_entry: MockConfigEntry,
) -> None:
    """The JSON body is reduced to keys and types, the values are dropped."""
    stats = await _setup(hass, mock_config_entry)
    client = await hass_client_no_auth()

    response = await client.post(PATH, json={"keyword": "B3", "lat": 1.2345})

    assert response.status == HTTPStatus.OK
    call = stats.last_call
    assert call is not None
    assert call.body_kind == "json"
    assert call.body_shape == {"keyword": "str(2)", "lat": "float"}
    assert call.content_type == "application/json"
    assert call.body_length == len('{"keyword": "B3", "lat": 1.2345}')


async def test_form_body_keeps_only_the_keys(
    hass: HomeAssistant,
    hass_client_no_auth: ClientSessionGenerator,
    mock_config_entry: MockConfigEntry,
) -> None:
    """A form body is reduced to the sorted list of its keys."""
    stats = await _setup(hass, mock_config_entry)
    client = await hass_client_no_auth()

    response = await client.post(PATH, data={"b": "2", "a": "1", "c": ""})

    assert response.status == HTTPStatus.OK
    call = stats.last_call
    assert call is not None
    assert (call.body_kind, call.body_shape) == ("form", ["a", "b", "c"])


async def test_invalid_json_counts_as_text(
    hass: HomeAssistant,
    hass_client_no_auth: ClientSessionGenerator,
    mock_config_entry: MockConfigEntry,
) -> None:
    """A body that claims to be JSON but is not still gets 200."""
    stats = await _setup(hass, mock_config_entry)
    client = await hass_client_no_auth()

    response = await client.post(PATH, data="{not json", headers=JSON)

    assert response.status == HTTPStatus.OK
    call = stats.last_call
    assert call is not None
    assert (call.body_kind, call.body_shape) == ("text", None)


async def test_invalid_utf8_counts_as_binary(
    hass: HomeAssistant,
    hass_client_no_auth: ClientSessionGenerator,
    mock_config_entry: MockConfigEntry,
) -> None:
    """A body that is no text gets 200; its length comes from Content-Length."""
    stats = await _setup(hass, mock_config_entry)
    client = await hass_client_no_auth()

    response = await client.post(PATH, data=b"\xff\xfe\xfd")

    assert response.status == HTTPStatus.OK
    call = stats.last_call
    assert call is not None
    assert (call.body_kind, call.body_shape, call.body_length) == ("binary", None, 3)


async def test_plain_text_body(
    hass: HomeAssistant,
    hass_client_no_auth: ClientSessionGenerator,
    mock_config_entry: MockConfigEntry,
) -> None:
    """A plain text body is only measured."""
    stats = await _setup(hass, mock_config_entry)
    client = await hass_client_no_auth()

    response = await client.post(PATH, data="alarm")

    assert response.status == HTTPStatus.OK
    call = stats.last_call
    assert call is not None
    assert (call.body_kind, call.body_shape, call.body_length) == ("text", None, 5)


async def test_header_names_and_clipped_user_agent(
    hass: HomeAssistant,
    hass_client_no_auth: ClientSessionGenerator,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Header names are recorded in lower case, values are not."""
    stats = await _setup(hass, mock_config_entry)
    client = await hass_client_no_auth()

    await client.post(
        PATH, headers={"User-Agent": "u" * 200, "X-Other-Header": HEADER_VALUE}
    )

    call = stats.last_call
    assert call is not None
    assert "x-other-header" in call.header_names
    assert "user-agent" in call.header_names
    assert list(call.header_names) == sorted(call.header_names)
    assert call.user_agent == "u" * MAX_USER_AGENT_CHARS
    assert HEADER_VALUE not in json.dumps(call.as_diagnostics())


# --- Additional token -----------------------------------------------------------


async def test_without_token_option_no_header_is_needed(
    hass: HomeAssistant,
    hass_client_no_auth: ClientSessionGenerator,
    mock_config_entry: MockConfigEntry,
) -> None:
    """By default the token is not checked."""
    stats = await _setup(hass, mock_config_entry)
    client = await hass_client_no_auth()

    response = await client.post(PATH, headers={TOKEN_HEADER: "wrong"})

    assert response.status == HTTPStatus.OK
    assert (stats.calls_total, stats.rejected_total) == (1, 0)
    assert _issue(hass, mock_config_entry) is None


async def test_missing_token_is_rejected_with_a_repair_issue(
    hass: HomeAssistant,
    hass_client_no_auth: ClientSessionGenerator,
    token_entry: MockConfigEntry,
) -> None:
    """Without the header the call gets 401, is counted and a repair issue appears."""
    stats = await _setup(hass, token_entry)
    client = await hass_client_no_auth()

    response = await client.post(PATH, json={"keyword": "B3"})

    assert response.status == HTTPStatus.UNAUTHORIZED
    assert (stats.calls_total, stats.rejected_total) == (0, 1)
    assert stats.last_call is None
    issue = _issue(hass, token_entry)
    assert issue is not None
    assert issue.translation_key == "webhook_token_rejected"
    assert issue.severity is ir.IssueSeverity.WARNING
    assert issue.is_fixable is False
    assert issue.is_persistent is True
    assert issue.translation_placeholders == {"title": token_entry.title}


async def test_wrong_token_is_rejected(
    hass: HomeAssistant,
    hass_client_no_auth: ClientSessionGenerator,
    token_entry: MockConfigEntry,
) -> None:
    """A wrong token, also one with non-ASCII characters, gets 401."""
    stats = await _setup(hass, token_entry)
    client = await hass_client_no_auth()

    for value in ("wrong", HEADER_TOKEN[:-1], HEADER_TOKEN + "x", "tökën"):
        response = await client.post(PATH, headers={TOKEN_HEADER: value})
        assert response.status == HTTPStatus.UNAUTHORIZED

    assert (stats.calls_total, stats.rejected_total) == (0, 4)


async def test_valid_token_is_accepted_and_clears_the_issue(
    hass: HomeAssistant,
    hass_client_no_auth: ClientSessionGenerator,
    token_entry: MockConfigEntry,
) -> None:
    """The header name is case-insensitive; a good call removes the repair issue."""
    stats = await _setup(hass, token_entry)
    client = await hass_client_no_auth()

    assert (await client.post(PATH)).status == HTTPStatus.UNAUTHORIZED
    assert _issue(hass, token_entry) is not None

    response = await client.post(PATH, headers={TOKEN_HEADER.lower(): HEADER_TOKEN})

    assert response.status == HTTPStatus.OK
    assert (stats.calls_total, stats.rejected_total) == (1, 1)
    assert _issue(hass, token_entry) is None
    call = stats.last_call
    assert call is not None
    # The header is recorded by name only, never with its value.
    assert TOKEN_HEADER.lower() in call.header_names
    assert HEADER_TOKEN not in json.dumps(call.as_diagnostics())


# --- Calls through a cloudhook (MockRequest) ------------------------------------


async def test_cloudhook_call_is_handled_without_read(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """A MockRequest has no read(); the handler works with text() only."""
    stats = await _setup(hass, mock_config_entry)

    response = await webhook.async_handle_webhook(
        hass,
        WEBHOOK_ID,
        MockRequest(
            content=b'{"a":1}',
            mock_source="test",
            method="POST",
            headers=JSON,
        ),
    )

    assert response.status == HTTPStatus.OK
    call = stats.last_call
    assert call is not None
    assert (call.body_kind, call.body_shape) == ("json", {"a": "int"})
    assert stats.calls_total == 1


async def test_cloudhook_call_with_token_header(
    hass: HomeAssistant, token_entry: MockConfigEntry
) -> None:
    """The token header of a cloudhook call is accepted; without it the call is not."""
    stats = await _setup(hass, token_entry)

    accepted = await webhook.async_handle_webhook(
        hass, WEBHOOK_ID, _mock_request(headers={TOKEN_HEADER: HEADER_TOKEN})
    )
    rejected = await webhook.async_handle_webhook(hass, WEBHOOK_ID, _mock_request())
    # A value that is not even valid text (a lone surrogate) is simply wrong.
    garbage = await webhook.async_handle_webhook(
        hass, WEBHOOK_ID, _mock_request(headers={TOKEN_HEADER: "\ud800"})
    )

    assert accepted.status == HTTPStatus.OK
    assert rejected.status == HTTPStatus.UNAUTHORIZED
    assert garbage.status == HTTPStatus.UNAUTHORIZED
    assert (stats.calls_total, stats.rejected_total) == (1, 2)
    assert stats.last_call is not None
    assert TOKEN_HEADER.lower() in stats.last_call.header_names


async def test_call_after_unload_has_no_effect(
    hass: HomeAssistant,
    hass_client_no_auth: ClientSessionGenerator,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Once the entry is unloaded, the webhook no longer counts anything."""
    stats = await _setup(hass, mock_config_entry)
    client = await hass_client_no_auth()
    assert (await client.post(PATH)).status == HTTPStatus.OK
    assert stats.calls_total == 1

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    response = await client.post(PATH)

    # Home Assistant answers 200 for unknown webhooks so that nothing leaks.
    assert response.status == HTTPStatus.OK
    assert stats.calls_total == 1


# --- Shape of a call ------------------------------------------------------------


async def test_shape_of_nested_json() -> None:
    """Scalars become type names, lists a length and the type of the first item."""
    body = {
        "s": "abc",
        "i": 1,
        "f": 1.5,
        "b": True,
        "n": None,
        "l": [1, 2, 3],
        "e": [],
        "d": {"x": "y"},
    }

    call = await async_capture_call(
        _mock_request(json.dumps(body).encode(), headers=JSON)
    )

    assert call.body_shape == {
        "s": "str(3)",
        "i": "int",
        "f": "float",
        "b": "bool",
        "n": "null",
        "l": ["list(3)", "int"],
        "e": ["list(0)"],
        "d": {"x": "str(1)"},
    }


async def test_shape_is_limited_in_depth_keys_and_name_length() -> None:
    """Deep, wide or oddly named bodies stay small."""
    deep: Any = 1
    for _ in range(8):
        deep = {"a": deep}
    wide = {f"key{index:03d}": index for index in range(MAX_SHAPE_KEYS + 10)}
    long_name = {"k" * (MAX_NAME_CHARS + 30): 1}

    deep_call = await async_capture_call(
        _mock_request(json.dumps(deep).encode(), headers=JSON)
    )
    wide_call = await async_capture_call(
        _mock_request(json.dumps(wide).encode(), headers=JSON)
    )
    long_call = await async_capture_call(
        _mock_request(json.dumps(long_name).encode(), headers=JSON)
    )

    assert deep_call.body_shape == {"a": {"a": {"a": {"a": {"a": "..."}}}}}
    assert len(wide_call.body_shape) == MAX_SHAPE_KEYS
    assert list(long_call.body_shape) == ["k" * MAX_NAME_CHARS]


@pytest.mark.parametrize(
    ("content", "headers", "kind", "shape"),
    [
        (b"", None, "empty", None),
        (b"  \n", None, "empty", None),
        (b'{"a": 1}', None, "json", {"a": "int"}),
        (b'["x"]', {"Content-Type": "text/plain"}, "json", ["list(1)", "str(1)"]),
        (b'"abc"', JSON, "json", "str(3)"),
        (b"{broken", None, "text", None),
        (b"not json", JSON, "text", None),
        (
            b"b=2&a=1&c=",
            {"Content-Type": "application/x-www-form-urlencoded; charset=utf-8"},
            "form",
            ["a", "b", "c"],
        ),
        (b"b=2&a=1", {"Content-Type": "text/plain"}, "text", None),
    ],
)
async def test_body_kinds(
    content: bytes,
    headers: dict[str, str] | None,
    kind: str,
    shape: Any,
) -> None:
    """The kind of a body is derived from its content and the Content-Type."""
    call = await async_capture_call(_mock_request(content, headers))

    assert (call.body_kind, call.body_shape) == (kind, shape)


async def test_query_keys_of_a_cloudhook_call() -> None:
    """Query keys are unique and sorted; their values are dropped."""
    call = await async_capture_call(
        _mock_request(query_string=f"b={QUERY_VALUE}&a=1&b=2")
    )

    assert call.query_keys == ("a", "b")
    assert QUERY_VALUE not in json.dumps(call.as_diagnostics())


@pytest.mark.parametrize(
    ("length_header", "expected"),
    [("7", 7), ("-5", 0), ("seven", 0), (None, 0)],
)
async def test_binary_length_comes_from_content_length(
    length_header: str | None, expected: int
) -> None:
    """The length of a body that is no text is read from Content-Length."""
    headers = {} if length_header is None else {"Content-Length": length_header}

    call = await async_capture_call(
        UnreadableRequest(UnicodeDecodeError("utf-8", b"", 0, 1, "x"), headers)
    )

    assert (call.body_kind, call.body_length) == ("binary", expected)


async def test_unreadable_body_never_raises(caplog: pytest.LogCaptureFixture) -> None:
    """A body that cannot be read at all is recorded as binary, with the error type."""
    caplog.set_level(logging.DEBUG, logger="custom_components.ff_agent")

    call = await async_capture_call(
        UnreadableRequest(ConnectionResetError("secret-detail"))
    )

    assert isinstance(call, WebhookCall)
    assert call.body_kind == "binary"
    assert "ConnectionResetError" in caplog.text
    # The message of the error may contain anything, so it is not logged.
    assert "secret-detail" not in caplog.text


# --- Privacy --------------------------------------------------------------------


async def test_no_secret_or_value_is_logged_or_kept(
    hass: HomeAssistant,
    hass_client_no_auth: ClientSessionGenerator,
    token_entry: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Neither IDs, the token nor any value of a call ends up in logs or counters.

    Deliberately no unsupported method here: Home Assistant itself logs the webhook
    ID as a warning for those.
    """
    caplog.set_level(logging.DEBUG, logger="custom_components.ff_agent")
    stats = await _setup(hass, token_entry)
    client = await hass_client_no_auth()

    accepted = await client.post(
        PATH,
        params={"secret_key": QUERY_VALUE},
        json={"keyword": BODY_VALUE},
        headers={TOKEN_HEADER: HEADER_TOKEN, "X-Other": HEADER_VALUE},
    )
    rejected = await client.post(
        PATH,
        params={"secret_key": QUERY_VALUE},
        json={"keyword": BODY_VALUE},
        headers={TOKEN_HEADER: HEADER_TOKEN + "x", "X-Other": HEADER_VALUE},
    )
    cloudhook = await webhook.async_handle_webhook(
        hass,
        WEBHOOK_ID,
        _mock_request(
            json.dumps({"keyword": BODY_VALUE}).encode(),
            {**JSON, TOKEN_HEADER: HEADER_TOKEN, "X-Other": HEADER_VALUE},
        ),
    )

    assert accepted.status == HTTPStatus.OK
    assert rejected.status == HTTPStatus.UNAUTHORIZED
    assert cloudhook.status == HTTPStatus.OK

    log = _log_text(caplog)
    # The test is only meaningful if the handler really logged something.
    assert "Received a webhook call" in log
    assert "Rejected a webhook call" in log
    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]

    assert stats.last_call is not None
    kept = json.dumps(stats.last_call.as_diagnostics())
    for secret in (
        WEBHOOK_ID,
        REPLY_ID,
        HEADER_TOKEN,
        BODY_VALUE,
        QUERY_VALUE,
        HEADER_VALUE,
    ):
        assert secret not in log
        assert secret not in kept


def test_handler_only_uses_what_a_mock_request_offers() -> None:
    """MockRequest (cloudhook) has no read(), but everything the handler touches."""
    request = _mock_request()

    assert not hasattr(request, "read")
    for name in ("text", "headers", "query", "method"):
        assert hasattr(request, name)


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ("application/json", "application/json"),
        ("Application/JSON; charset=UTF-8", "application/json"),
        ("text/plain ; boundary=secret-parameter", "text/plain"),
        ("x/" + "y" * 300, ("x/" + "y" * 300)[:MAX_CONTENT_TYPE_CHARS]),
        ("", None),
    ],
)
async def test_content_type_keeps_only_the_clipped_media_type(
    header: str, expected: str | None
) -> None:
    """Parameters are dropped, the media type is lower case and has a maximum length."""
    headers = {"Content-Type": header} if header else None

    call = await async_capture_call(_mock_request(b"x", headers))

    assert call.content_type == expected
    assert "secret-parameter" not in json.dumps(call.as_diagnostics())
