"""Edge cases of the webhook: limits, odd headers, repeated rejections, reload."""

from __future__ import annotations

import asyncio
import json
import logging
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

import pytest
from homeassistant.components import webhook
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component
from homeassistant.util.aiohttp import MockRequest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)

from custom_components.ff_agent.const import (
    DOMAIN,
    MAX_BODY_ANALYSIS_CHARS,
    MAX_SHAPE_DEPTH,
    TOKEN_HEADER,
)
from custom_components.ff_agent.webhook import async_capture_call

from .const import HEADER_TOKEN, REPLY_ID, WEBHOOK_ID

if TYPE_CHECKING:
    from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

PATH = f"/api/webhook/{WEBHOOK_ID}"
JSON = {"Content-Type": "application/json"}


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def _post(content: bytes = b"", headers: dict[str, str] | None = None) -> MockRequest:
    return MockRequest(content, "test", method="POST", headers=headers)


def _is_registered(hass: HomeAssistant) -> bool:
    """Return whether the webhook ID is taken (HA raises ValueError on a duplicate)."""

    async def _unused(*_: Any) -> None:
        return None

    try:
        webhook.async_register(hass, DOMAIN, "probe", WEBHOOK_ID, _unused)
    except ValueError:
        return True
    webhook.async_unregister(hass, WEBHOOK_ID)
    return False


def _depth(shape: Any) -> int:
    """Return the nesting depth of a shape."""
    if isinstance(shape, dict):
        return 1 + max((_depth(v) for v in shape.values()), default=0)
    if isinstance(shape, list):
        return 1 + max((_depth(v) for v in shape), default=0)
    return 0


# --- Large and odd bodies -------------------------------------------------------


async def test_huge_text_body_is_measured_not_analyzed(
    hass: HomeAssistant,
    hass_client_no_auth: ClientSessionGenerator,
    mock_config_entry: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A body far beyond the analysis limit gets 200 and the full length."""
    await _setup(hass, mock_config_entry)
    client = await hass_client_no_auth()
    size = MAX_BODY_ANALYSIS_CHARS * 8

    response = await client.post(PATH, data="x" * size)

    assert response.status == HTTPStatus.OK
    call = mock_config_entry.runtime_data.alarm.last_call
    assert call is not None
    assert (call.body_kind, call.body_shape, call.body_length) == ("text", None, size)
    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]


async def test_huge_json_body_never_raises(
    hass: HomeAssistant,
    hass_client_no_auth: ClientSessionGenerator,
    mock_config_entry: MockConfigEntry,
) -> None:
    """A JSON body cut at the limit is invalid JSON: counted as text, still 200."""
    await _setup(hass, mock_config_entry)
    client = await hass_client_no_auth()
    body = json.dumps({"items": list(range(MAX_BODY_ANALYSIS_CHARS))})
    assert len(body) > MAX_BODY_ANALYSIS_CHARS

    response = await client.post(PATH, data=body, headers=JSON)

    assert response.status == HTTPStatus.OK
    call = mock_config_entry.runtime_data.alarm.last_call
    assert call is not None
    assert call.body_kind == "text"
    assert call.body_length == len(body)


async def test_extremely_nested_json_never_raises() -> None:
    """Nesting far beyond the parser limits ends as text or a depth-limited shape."""
    nested = b"[" * 20000 + b"]" * 20000
    assert len(nested) < MAX_BODY_ANALYSIS_CHARS

    call = await async_capture_call(_post(nested, JSON))

    assert call.body_kind in ("text", "json")
    assert _depth(call.body_shape) <= MAX_SHAPE_DEPTH + 1


async def test_nested_json_is_cut_at_the_depth_limit() -> None:
    """Moderately nested JSON is parsed, but the shape stays within the depth limit."""
    deep: Any = 1
    for _ in range(40):
        deep = [deep]

    call = await async_capture_call(_post(json.dumps(deep).encode(), JSON))

    assert call.body_kind == "json"
    assert _depth(call.body_shape) <= MAX_SHAPE_DEPTH + 1
    assert "..." in json.dumps(call.body_shape)


async def test_json_list_as_root_keeps_only_the_first_item_shape() -> None:
    """A list as the root is described by its length and the shape of its first item."""
    body = [{"keyword": "B3"}, {"other": 1}]

    call = await async_capture_call(_post(json.dumps(body).encode(), JSON))

    assert call.body_kind == "json"
    assert call.body_shape == ["list(2)", {"keyword": "str(2)"}]


async def test_many_headers_are_limited() -> None:
    """Hundreds of different header names stay a bounded list."""
    headers = {f"X-Header-{index:04d}": "v" for index in range(300)}

    call = await async_capture_call(_post(headers=headers))

    assert 0 < len(call.header_names) <= 50
    assert list(call.header_names) == sorted(call.header_names)


# --- Token header ---------------------------------------------------------------


async def test_upper_case_token_header_name_is_accepted(
    hass: HomeAssistant,
    hass_client_no_auth: ClientSessionGenerator,
    token_entry: MockConfigEntry,
) -> None:
    """Header names are case-insensitive, for a real request and a cloudhook call."""
    await _setup(hass, token_entry)
    client = await hass_client_no_auth()
    stats = token_entry.runtime_data.alarm

    http = await client.post(PATH, headers={TOKEN_HEADER.upper(): HEADER_TOKEN})
    cloud = await webhook.async_handle_webhook(
        hass, WEBHOOK_ID, _post(headers={TOKEN_HEADER.upper(): HEADER_TOKEN})
    )

    assert http.status == HTTPStatus.OK
    assert cloud.status == HTTPStatus.OK
    assert (stats.calls_total, stats.rejected_total) == (2, 0)


async def test_empty_token_header_is_rejected(
    hass: HomeAssistant,
    hass_client_no_auth: ClientSessionGenerator,
    token_entry: MockConfigEntry,
) -> None:
    """An empty token header is as wrong as a missing one."""
    await _setup(hass, token_entry)
    client = await hass_client_no_auth()
    stats = token_entry.runtime_data.alarm

    http = await client.post(PATH, headers={TOKEN_HEADER: ""})
    cloud = await webhook.async_handle_webhook(
        hass, WEBHOOK_ID, _post(headers={TOKEN_HEADER: ""})
    )

    assert http.status == HTTPStatus.UNAUTHORIZED
    assert cloud.status == HTTPStatus.UNAUTHORIZED
    assert (stats.calls_total, stats.rejected_total) == (0, 2)


async def test_token_with_surrounding_whitespace_is_rejected(
    hass: HomeAssistant, token_entry: MockConfigEntry
) -> None:
    """The comparison is exact: no trimming, no prefix match."""
    await _setup(hass, token_entry)

    for value in (f" {HEADER_TOKEN}", f"{HEADER_TOKEN}\n", HEADER_TOKEN.upper()):
        response = await webhook.async_handle_webhook(
            hass, WEBHOOK_ID, _post(headers={TOKEN_HEADER: value})
        )
        assert response.status == HTTPStatus.UNAUTHORIZED


async def test_repeated_rejections_keep_a_single_issue(
    hass: HomeAssistant,
    hass_client_no_auth: ClientSessionGenerator,
    token_entry: MockConfigEntry,
) -> None:
    """Many rejected calls are all counted but leave exactly one repair issue."""
    await _setup(hass, token_entry)
    client = await hass_client_no_auth()
    registry = ir.async_get(hass)

    for _ in range(3):
        assert (await client.post(PATH)).status == HTTPStatus.UNAUTHORIZED
    await webhook.async_handle_webhook(hass, WEBHOOK_ID, _post())

    own = [key for key in registry.issues if key[0] == DOMAIN]
    assert len(own) == 1
    assert token_entry.runtime_data.alarm.rejected_total == 4

    good = await client.post(PATH, headers={TOKEN_HEADER: HEADER_TOKEN})
    assert good.status == HTTPStatus.OK
    assert not [key for key in registry.issues if key[0] == DOMAIN]


async def test_rejected_call_does_not_read_the_body(
    hass: HomeAssistant, token_entry: MockConfigEntry
) -> None:
    """A rejected call is discarded before the body is analyzed."""
    await _setup(hass, token_entry)

    response = await webhook.async_handle_webhook(
        hass, WEBHOOK_ID, _post(b'{"keyword": "B3"}', JSON)
    )

    assert response.status == HTTPStatus.UNAUTHORIZED
    assert token_entry.runtime_data.alarm.last_call is None


# --- Unload and reload ----------------------------------------------------------


async def test_reload_registers_the_webhook_again(
    hass: HomeAssistant,
    hass_client_no_auth: ClientSessionGenerator,
    mock_config_entry: MockConfigEntry,
) -> None:
    """After a reload the webhook is registered once and counts into the new data."""
    await _setup(hass, mock_config_entry)
    client = await hass_client_no_auth()
    assert (await client.post(PATH)).status == HTTPStatus.OK
    first = mock_config_entry.runtime_data

    for _ in range(2):
        # A double registration would raise ValueError during the setup.
        assert await hass.config_entries.async_reload(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        assert _is_registered(hass)

    second = mock_config_entry.runtime_data
    assert second is not first
    assert second.alarm.calls_total == 0
    assert (await client.post(PATH)).status == HTTPStatus.OK
    assert second.alarm.calls_total == 1
    assert first.alarm.calls_total == 1


async def test_unload_removes_the_registration(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Unloading unregisters the webhook, so a setup can register it again."""
    await _setup(hass, mock_config_entry)
    assert _is_registered(hass)

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert not _is_registered(hass)


# --- Diagnostics ----------------------------------------------------------------


def _strings(data: Any) -> list[str]:
    """Return every string in nested data, keys included."""
    if isinstance(data, dict):
        return [s for k, v in data.items() for s in [*_strings(k), *_strings(v)]]
    if isinstance(data, (list, tuple)):
        return [s for item in data for s in _strings(item)]
    return [data] if isinstance(data, str) else []


async def test_diagnostics_hold_no_secret_even_if_a_call_carries_them(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    token_entry: MockConfigEntry,
) -> None:
    """Secrets sent as values (body, query, header) do not reach the diagnostics."""
    await _setup(hass, token_entry)

    assert await async_setup_component(hass, "diagnostics", {})
    secrets = (WEBHOOK_ID, REPLY_ID, HEADER_TOKEN, token_entry.title)
    body = {
        "a": HEADER_TOKEN,
        "nested": {"b": [WEBHOOK_ID, {"c": REPLY_ID}]},
        "list": [token_entry.title],
    }
    response = await webhook.async_handle_webhook(
        hass,
        WEBHOOK_ID,
        MockRequest(
            json.dumps(body).encode(),
            "test",
            method="POST",
            headers={**JSON, TOKEN_HEADER: HEADER_TOKEN, "X-Echo": WEBHOOK_ID},
            query_string=f"q={REPLY_ID}",
        ),
    )
    assert response.status == HTTPStatus.OK

    result = await get_diagnostics_for_config_entry(hass, hass_client, token_entry)

    texts = _strings(result)
    for secret in secrets:
        assert not [t for t in texts if secret in t], secret
    assert result["stats"]["last_call"]["body_shape"] == {
        "a": f"str({len(HEADER_TOKEN)})",
        "nested": {"b": ["list(2)", f"str({len(WEBHOOK_ID)})"]},
        "list": ["list(1)", f"str({len(token_entry.title)})"],
    }


# --- A call that is in flight while the entry reloads ---------------------------


class SlowRequest(MockRequest):
    """A request whose body only arrives when the gate is opened."""

    def __init__(self, gate: asyncio.Event) -> None:
        super().__init__(b"", "test", method="POST")
        self._gate = gate

    async def text(self) -> str:
        """Wait for the gate, then return an empty body."""
        await self._gate.wait()
        return ""


async def test_call_in_flight_during_a_reload_goes_to_the_new_manager(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """The manager is read after the body: the call lands in the current one."""
    await _setup(hass, mock_config_entry)
    old = mock_config_entry.runtime_data.alarm
    gate = asyncio.Event()
    task = hass.async_create_task(
        webhook.async_handle_webhook(hass, WEBHOOK_ID, SlowRequest(gate))
    )
    await asyncio.sleep(0)

    assert await hass.config_entries.async_reload(mock_config_entry.entry_id)
    new = mock_config_entry.runtime_data.alarm
    gate.set()
    response = await task
    await hass.async_block_till_done()

    assert response.status == HTTPStatus.OK
    assert new is not old
    assert (old.calls_total, old.active) == (0, False)
    assert (new.calls_total, new.alarms_total, new.active) == (1, 1, True)


async def test_call_in_flight_while_the_entry_unloads_is_dropped(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Without a manager the call is answered with 200 and has no effect."""
    await _setup(hass, mock_config_entry)
    old = mock_config_entry.runtime_data.alarm
    gate = asyncio.Event()
    task = hass.async_create_task(
        webhook.async_handle_webhook(hass, WEBHOOK_ID, SlowRequest(gate))
    )
    await asyncio.sleep(0)

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    gate.set()
    response = await task
    await hass.async_block_till_done()

    assert response.status == HTTPStatus.OK
    assert (old.calls_total, old.active) == (0, False)
