"""Tests for the diagnostics of the FF Agent integration."""

from __future__ import annotations

import json
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

import pytest
from homeassistant.components import webhook
from homeassistant.components.diagnostics import REDACTED
from homeassistant.core import HomeAssistant
from homeassistant.core_config import async_process_ha_core_config
from homeassistant.exceptions import HomeAssistantError
from homeassistant.setup import async_setup_component
from homeassistant.util.aiohttp import MockRequest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)

from custom_components.ff_agent.const import TOKEN_HEADER
from custom_components.ff_agent.diagnostics import async_get_config_entry_diagnostics
from custom_components.ff_agent.models import ReplyAction
from custom_components.ff_agent.reply import async_send_reply
from custom_components.ff_agent.reply_url import reply_unique_id

from .const import (
    ACCEPT_URL,
    CLOUDHOOK_URL,
    HEADER_TOKEN,
    INTERNAL_URL,
    LATITUDE,
    LOCATION_ENTITY,
    LONGITUDE,
    REJECT_URL,
    REPLY_ID,
    WEBHOOK_ID,
)

if TYPE_CHECKING:
    from pytest_homeassistant_custom_component.test_util.aiohttp import (
        AiohttpClientMocker,
    )
    from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

BODY_VALUE = "STICHWORT-PLATZHALTER"


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert await async_setup_component(hass, "diagnostics", {})


async def test_diagnostics_are_redacted(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    cloudhook_entry: MockConfigEntry,
) -> None:
    """Neither IDs, URL, token, title nor values of a call are in the diagnostics."""
    await _setup(hass, cloudhook_entry)
    response = await webhook.async_handle_webhook(
        hass,
        WEBHOOK_ID,
        MockRequest(
            content=json.dumps({"keyword": BODY_VALUE}).encode(),
            mock_source="test",
            method="POST",
            headers={"Content-Type": "application/json", TOKEN_HEADER: HEADER_TOKEN},
        ),
    )
    assert response.status == HTTPStatus.OK

    result = await get_diagnostics_for_config_entry(hass, hass_client, cloudhook_entry)

    dumped = json.dumps(result)
    for secret in (
        REPLY_ID,
        reply_unique_id(REPLY_ID),
        WEBHOOK_ID,
        CLOUDHOOK_URL,
        HEADER_TOKEN,
        cloudhook_entry.title,
        BODY_VALUE,
    ):
        assert secret not in dumped
    data = result["entry"]["data"]
    assert data["reply_id"] == REDACTED
    assert data["webhook_id"] == REDACTED
    assert data["cloudhook_url"] == REDACTED
    assert data["header_token"] == REDACTED
    assert result["entry"]["title"] == REDACTED
    assert result["entry"]["unique_id"] == REDACTED


async def test_diagnostics_show_the_shape_of_the_last_call(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    cloudhook_entry: MockConfigEntry,
) -> None:
    """The diagnostics answer the questions of the first real test."""
    await _setup(hass, cloudhook_entry)
    await webhook.async_handle_webhook(
        hass,
        WEBHOOK_ID,
        MockRequest(
            content=json.dumps({"keyword": BODY_VALUE}).encode(),
            mock_source="test",
            method="POST",
            headers={"Content-Type": "application/json", TOKEN_HEADER: HEADER_TOKEN},
            query_string="a=1",
        ),
    )

    result = await get_diagnostics_for_config_entry(hass, hass_client, cloudhook_entry)

    assert result["webhook"] == {
        "url_kind": "cloud",
        "allowed_methods": ["GET", "POST"],
        "require_token": False,
    }
    stats = result["stats"]
    assert (stats["calls_total"], stats["rejected_total"]) == (1, 0)
    last_call = stats["last_call"]
    assert last_call["method"] == "POST"
    assert last_call["query_keys"] == ["a"]
    assert last_call["body_kind"] == "json"
    assert last_call["body_shape"] == {"keyword": "str(21)"}
    assert "x-ff-agent-token" in last_call["header_names"]
    assert last_call["received_at"]

    alarm = result["alarm"]
    assert alarm["active"] is True
    assert alarm["last_alarm"] == last_call["received_at"]
    assert alarm["active_until"]
    assert (alarm["alarms_total"], alarm["deduplicated_total"]) == (1, 0)
    assert alarm["dedup_seconds"] == 30
    assert alarm["reset_minutes"] == 30
    assert BODY_VALUE not in json.dumps(alarm)


async def test_diagnostics_without_any_call(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Before the first call there is no last call; the URL kind is reported."""
    await async_process_ha_core_config(hass, {"internal_url": INTERNAL_URL})
    await _setup(hass, mock_config_entry)

    result = await get_diagnostics_for_config_entry(
        hass, hass_client, mock_config_entry
    )

    assert result["webhook"]["url_kind"] == "internal"
    assert result["webhook"]["require_token"] is False
    assert result["stats"] == {
        "calls_total": 0,
        "rejected_total": 0,
        "last_call": None,
    }
    assert result["alarm"] == {
        "active": False,
        "last_alarm": None,
        "active_until": None,
        "alarms_total": 0,
        "deduplicated_total": 0,
        "dedup_seconds": 30,
        "reset_minutes": 30,
    }


async def test_diagnostics_report_the_token_option_and_rejections(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    token_entry: MockConfigEntry,
) -> None:
    """A rejected call is counted but leaves no last call."""
    await _setup(hass, token_entry)
    response = await webhook.async_handle_webhook(
        hass,
        WEBHOOK_ID,
        MockRequest(content=b"", mock_source="test", method="POST"),
    )
    assert response.status == HTTPStatus.UNAUTHORIZED

    result = await get_diagnostics_for_config_entry(hass, hass_client, token_entry)

    assert result["webhook"]["require_token"] is True
    assert result["stats"] == {
        "calls_total": 0,
        "rejected_total": 1,
        "last_call": None,
    }
    assert result["alarm"]["alarms_total"] == 0
    assert result["alarm"]["active"] is False


@pytest.mark.usefixtures("external_url")
async def test_diagnostics_url_kind_external(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    mock_config_entry: MockConfigEntry,
) -> None:
    """With an external URL the kind is reported, never the URL."""
    await _setup(hass, mock_config_entry)

    result = await get_diagnostics_for_config_entry(
        hass, hass_client, mock_config_entry
    )

    assert result["webhook"]["url_kind"] == "external"
    assert "example.com" not in json.dumps(result)


async def test_diagnostics_of_an_unloaded_entry(
    hass: HomeAssistant, cloudhook_entry: MockConfigEntry
) -> None:
    """Without runtime data the stats are None instead of raising."""
    await _setup(hass, cloudhook_entry)
    assert await hass.config_entries.async_unload(cloudhook_entry.entry_id)
    await hass.async_block_till_done()

    result = await async_get_config_entry_diagnostics(hass, cloudhook_entry)

    assert result["stats"] is None
    assert result["alarm"] is None
    assert result["reply"] is None
    assert result["webhook"]["url_kind"] == "cloud"
    assert result["entry"]["data"]["webhook_id"] == REDACTED


# --- Replies --------------------------------------------------------------------


async def test_diagnostics_without_any_reply(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Before the first reply the counters are zero and there is no result."""
    await _setup(hass, mock_config_entry)

    result = await get_diagnostics_for_config_entry(
        hass, hass_client, mock_config_entry
    )

    assert result["reply"] == {
        "attempts_total": 0,
        "succeeded_total": 0,
        "failed_total": 0,
        "skipped_total": 0,
        "repeat_guard_seconds": 10,
        "last_result": None,
    }


async def test_diagnostics_show_the_outcome_of_the_last_reply(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
    location_entry: MockConfigEntry,
) -> None:
    """A reply shows up with its outcome, but without address or coordinates."""
    aioclient_mock.get(ACCEPT_URL, headers={"Content-Type": "text/html"})
    hass.states.async_set(
        LOCATION_ENTITY, "home", {"latitude": LATITUDE, "longitude": LONGITUDE}
    )
    await _setup(hass, location_entry)
    await async_send_reply(hass, location_entry, ReplyAction.ACCEPT)
    # The second one is skipped by the repeat guard and only counted.
    await async_send_reply(hass, location_entry, ReplyAction.ACCEPT)

    result = await get_diagnostics_for_config_entry(hass, hass_client, location_entry)

    reply = result["reply"]
    assert reply["attempts_total"] == 1
    assert reply["succeeded_total"] == 1
    assert reply["failed_total"] == 0
    assert reply["skipped_total"] == 1
    last = reply["last_result"]
    assert set(last) == {
        "action",
        "at",
        "success",
        "status",
        "content_type",
        "error_type",
    }
    assert last["action"] == "accept"
    assert last["success"] is True
    assert last["status"] == 200
    assert last["content_type"] == "text/html"
    assert last["error_type"] is None
    assert last["at"]
    dumped = json.dumps(result)
    for secret in (REPLY_ID, str(LATITUDE), str(LONGITUDE), LOCATION_ENTITY):
        assert secret not in dumped
    assert result["entry"]["options"]["location_entity"] == REDACTED


@pytest.mark.parametrize(
    ("kwargs", "status", "error_type"),
    [
        ({"status": 404}, 404, None),
        ({"exc": TimeoutError()}, None, "TimeoutError"),
    ],
)
async def test_diagnostics_show_a_failed_reply(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
    kwargs: dict[str, Any],
    status: int | None,
    error_type: str | None,
) -> None:
    """A failed reply shows the status or the error class, never an address."""
    aioclient_mock.get(REJECT_URL, **kwargs)
    await _setup(hass, mock_config_entry)
    with pytest.raises(HomeAssistantError):
        await async_send_reply(hass, mock_config_entry, ReplyAction.REJECT)

    result = await get_diagnostics_for_config_entry(
        hass, hass_client, mock_config_entry
    )

    reply = result["reply"]
    assert (reply["attempts_total"], reply["failed_total"]) == (1, 1)
    last = reply["last_result"]
    assert last["action"] == "reject"
    assert last["success"] is False
    assert last["status"] == status
    assert last["error_type"] == error_type
    assert REPLY_ID not in json.dumps(result)
