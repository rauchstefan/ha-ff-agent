"""Tests for the reconfigure flow of the FF Agent integration."""

from __future__ import annotations

import json
import logging
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest
from homeassistant.components import webhook
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_WEBHOOK_ID
from homeassistant.core import HomeAssistant
from homeassistant.core_config import async_process_ha_core_config
from homeassistant.data_entry_flow import FlowResult, FlowResultType
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.util.aiohttp import MockRequest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ff_agent.const import (
    CONF_ALARM_SOURCE,
    CONF_CLOUDHOOK,
    CONF_CLOUDHOOK_URL,
    CONF_HEADER_TOKEN,
    CONF_NTFY_ENTITY_UUID,
    CONF_NTFY_SERVER,
    CONF_NTFY_TOPIC,
    CONF_REGENERATE_WEBHOOK,
    CONF_REPLY_HOST,
    CONF_REPLY_ID,
    CONF_REPLY_URL,
    DEFAULT_REPLY_HOST,
    DOMAIN,
    ISSUE_NTFY_ENTITY_MISSING,
    ISSUE_TOKEN_REJECTED,
    MY_CLOUD_URL,
    MY_NETWORK_URL,
    MY_NTFY_INTEGRATION_URL,
    MY_NTFY_SETUP_URL,
    TOKEN_HEADER,
)
from custom_components.ff_agent.models import ReplyAction
from custom_components.ff_agent.reply import async_send_reply
from custom_components.ff_agent.reply_url import reply_unique_id

from .common import (
    CloudNotAvailable,
    add_ntfy_entity,
    add_ntfy_entry,
    async_setup_entry,
    patch_cloud,
)
from .const import (
    CLOUDHOOK_URL,
    EXTERNAL_URL,
    HEADER_TOKEN,
    INTERNAL_URL,
    NEW_CLOUDHOOK_URL,
    NTFY_ENTITY_ID,
    NTFY_PUBLISH_URL,
    NTFY_TOPIC,
    OTHER_ACCEPT_URL,
    OTHER_NTFY_ENTITY_ID,
    OTHER_NTFY_SUBENTRY_ID,
    OTHER_REPLY_ID,
    OTHER_REPLY_URL,
    REPLY_ID,
    REPLY_URL,
    WEBHOOK_ID,
)

if TYPE_CHECKING:
    from pytest_homeassistant_custom_component.test_util.aiohttp import (
        AiohttpClientMocker,
    )

TRANSLATIONS = Path(__file__).parents[1] / "custom_components/ff_agent/translations"
LINKS = {
    "cloud_url": MY_CLOUD_URL,
    "network_url": MY_NETWORK_URL,
    "ntfy_setup_url": MY_NTFY_SETUP_URL,
    "ntfy_integration_url": MY_NTFY_INTEGRATION_URL,
}


async def _start(hass: HomeAssistant, entry: MockConfigEntry) -> FlowResult:
    result = await entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"
    return result


async def _submit(
    hass: HomeAssistant, flow_id: str, values: dict[str, Any] | None = None
) -> FlowResult:
    result = await hass.config_entries.flow.async_configure(flow_id, values or {})
    await hass.async_block_till_done()
    return result


async def _choose(hass: HomeAssistant, flow_id: str, option: str) -> FlowResult:
    """Choose an option of a menu."""
    result = await hass.config_entries.flow.async_configure(
        flow_id, {"next_step_id": option}
    )
    await hass.async_block_till_done()
    return result


async def _call_webhook(
    hass: HomeAssistant,
    webhook_id: str = WEBHOOK_ID,
    headers: dict[str, str] | None = None,
) -> int:
    request = MockRequest(b"", "test", method="POST", headers=headers)
    response = await webhook.async_handle_webhook(hass, webhook_id, request)
    await hass.async_block_till_done()
    return response.status


def _requested(aioclient_mock: AiohttpClientMocker) -> tuple[str, str]:
    """Return host and path of the only request that was made."""
    assert aioclient_mock.call_count == 1
    _method, url, _data, _headers = aioclient_mock.mock_calls[0]
    return str(url.host), str(url.path)


# --- The form -----------------------


async def test_form_fields_and_no_secret(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """The stored reply URL is a secret and is never shown or pre-filled."""
    await async_setup_entry(hass, mock_config_entry)

    result = await _start(hass, mock_config_entry)

    schema = result["data_schema"].schema
    fields = {CONF_REPLY_URL, CONF_ALARM_SOURCE, CONF_REGENERATE_WEBHOOK}
    assert {str(key) for key in schema} == fields
    source_key = next(key for key in schema if key == CONF_ALARM_SOURCE)
    assert source_key.default() == "webhook"
    assert schema[source_key].config["options"] == ["webhook", "ntfy"]
    assert schema[source_key].config["translation_key"] == "alarm_source"
    assert REPLY_ID not in str(result)
    for language in ("en", "de"):
        texts = json.loads((TRANSLATIONS / f"{language}.json").read_text("utf-8"))
        step = texts["config"]["step"]["reconfigure"]
        assert set(step["data"]) == fields
        assert set(step["data_description"]) == fields
        assert set(texts["selector"]["alarm_source"]["options"]) == {"webhook", "ntfy"}


# --- Nothing to change -----------------------


@pytest.mark.parametrize(
    "values",
    [
        {},
        {CONF_REPLY_URL: ""},
        {CONF_REPLY_URL: "   "},
        {CONF_REPLY_URL: REPLY_URL},
        {CONF_REPLY_URL: REPLY_ID.upper()},
        {CONF_REPLY_URL: REPLY_ID, CONF_REGENERATE_WEBHOOK: False},
    ],
)
@pytest.mark.usefixtures("external_url")
async def test_nothing_changed_aborts_without_reload(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, values: dict[str, Any]
) -> None:
    """Empty fields or the same URL change nothing and do not reload the entry."""
    await async_setup_entry(hass, mock_config_entry)
    alarm = mock_config_entry.runtime_data.alarm
    data = dict(mock_config_entry.data)
    result = await _start(hass, mock_config_entry)

    result = await _submit(hass, result["flow_id"], values)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert dict(mock_config_entry.data) == data
    assert mock_config_entry.runtime_data.alarm is alarm


# --- A new reply URL -----------------------


@pytest.mark.usefixtures("external_url")
async def test_new_reply_url_updates_data_and_unique_id_but_not_the_webhook(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """The person renewed the UUID: data and unique ID follow, the webhook stays."""
    aioclient_mock.get(OTHER_ACCEPT_URL)
    await async_setup_entry(hass, mock_config_entry)
    old_alarm = mock_config_entry.runtime_data.alarm
    result = await _start(hass, mock_config_entry)

    result = await _submit(hass, result["flow_id"], {CONF_REPLY_URL: OTHER_REPLY_URL})

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert mock_config_entry.unique_id == reply_unique_id(OTHER_REPLY_ID)
    assert mock_config_entry.data[CONF_REPLY_ID] == OTHER_REPLY_ID
    assert mock_config_entry.data[CONF_REPLY_HOST] == DEFAULT_REPLY_HOST
    assert mock_config_entry.data[CONF_WEBHOOK_ID] == WEBHOOK_ID
    assert mock_config_entry.data[CONF_HEADER_TOKEN] == HEADER_TOKEN
    assert CONF_REPLY_URL not in mock_config_entry.data
    # The entry was reloaded and the reply client uses the new UUID.
    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert mock_config_entry.runtime_data.alarm is not old_alarm
    await async_send_reply(hass, mock_config_entry, ReplyAction.ACCEPT)
    assert _requested(aioclient_mock) == (
        DEFAULT_REPLY_HOST,
        f"/app2/missionreplies/{OTHER_REPLY_ID}/accept",
    )


@pytest.mark.usefixtures("external_url")
async def test_new_host_of_the_same_person_keeps_the_unique_id(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """The same UUID on another FF Agent host only changes the host."""
    aioclient_mock.get(
        f"https://free.ff-agent.com/app2/missionreplies/{REPLY_ID}/accept"
    )
    await async_setup_entry(hass, mock_config_entry)
    unique_id = mock_config_entry.unique_id
    result = await _start(hass, mock_config_entry)
    url = f"https://free.ff-agent.com/app2/missionreplies/{REPLY_ID}/reject"

    result = await _submit(hass, result["flow_id"], {CONF_REPLY_URL: url})

    assert result["reason"] == "reconfigure_successful"
    assert mock_config_entry.unique_id == unique_id
    assert mock_config_entry.data[CONF_REPLY_HOST] == "free.ff-agent.com"
    await async_send_reply(hass, mock_config_entry, ReplyAction.ACCEPT)
    assert _requested(aioclient_mock) == (
        "free.ff-agent.com",
        f"/app2/missionreplies/{REPLY_ID}/accept",
    )


async def test_url_of_another_person_aborts_with_already_configured(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    other_entry: MockConfigEntry,
) -> None:
    """The unique ID may change, but not to the one of another entry."""
    other_entry.add_to_hass(hass)
    with patch_cloud(hass) as cloud_mocks:
        await async_setup_entry(hass, mock_config_entry)
        data = dict(mock_config_entry.data)
        result = await _start(hass, mock_config_entry)

        result = await _submit(
            hass,
            result["flow_id"],
            {CONF_REPLY_URL: OTHER_REPLY_URL, CONF_REGENERATE_WEBHOOK: True},
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert dict(mock_config_entry.data) == data
    assert mock_config_entry.unique_id == reply_unique_id(REPLY_ID)
    # Nothing was created or deleted before the abort.
    cloud_mocks["get_or_create"].assert_not_called()
    cloud_mocks["delete"].assert_not_called()


@pytest.mark.parametrize(
    "value",
    [
        "not a url",
        f"http://www.ff-agent.com/app2/missionreplies/{REPLY_ID}/accept",
        f"https://ff-agent.com.evil.example/app2/missionreplies/{REPLY_ID}/accept",
    ],
)
@pytest.mark.usefixtures("external_url")
async def test_invalid_url_shows_an_error_and_can_be_corrected(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
    value: str,
) -> None:
    """A bad URL keeps the form open; a good one then works."""
    caplog.set_level(logging.DEBUG)
    await async_setup_entry(hass, mock_config_entry)
    result = await _start(hass, mock_config_entry)

    result = await _submit(hass, result["flow_id"], {CONF_REPLY_URL: value})

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_REPLY_URL: "invalid_reply_url"}
    assert mock_config_entry.data[CONF_REPLY_ID] == REPLY_ID
    assert value not in caplog.text

    result = await _submit(hass, result["flow_id"], {CONF_REPLY_URL: OTHER_REPLY_URL})

    assert result["reason"] == "reconfigure_successful"
    assert mock_config_entry.data[CONF_REPLY_ID] == OTHER_REPLY_ID


async def test_invalid_url_does_not_create_a_new_access(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """With an invalid URL the new access is not created, even if it is requested."""
    await async_setup_entry(hass, mock_config_entry)
    result = await _start(hass, mock_config_entry)

    with patch_cloud(hass) as cloud_mocks:
        result = await _submit(
            hass,
            result["flow_id"],
            {CONF_REPLY_URL: "nonsense", CONF_REGENERATE_WEBHOOK: True},
        )

    assert result["errors"] == {CONF_REPLY_URL: "invalid_reply_url"}
    cloud_mocks["get_or_create"].assert_not_called()
    assert mock_config_entry.data[CONF_WEBHOOK_ID] == WEBHOOK_ID


# --- A new webhook access -----------------------


@pytest.mark.usefixtures("external_url")
async def test_new_webhook_access_without_cloud(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """New ID and token replace the old ones; the old webhook is gone."""
    await async_setup_entry(hass, mock_config_entry)
    old_alarm = mock_config_entry.runtime_data.alarm
    unique_id = mock_config_entry.unique_id
    result = await _start(hass, mock_config_entry)

    result = await _submit(hass, result["flow_id"], {CONF_REGENERATE_WEBHOOK: True})

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful_new_webhook"
    data = mock_config_entry.data
    new_id = data[CONF_WEBHOOK_ID]
    new_token = data[CONF_HEADER_TOKEN]
    assert new_id != WEBHOOK_ID
    assert new_token != HEADER_TOKEN
    assert len(new_token) >= 40
    assert (data[CONF_CLOUDHOOK], data[CONF_CLOUDHOOK_URL]) == (False, None)
    assert result["description_placeholders"] == {
        **LINKS,
        "webhook_url": f"{EXTERNAL_URL}/api/webhook/{new_id}",
        "token_header": TOKEN_HEADER,
        "token": new_token,
    }
    # The reply and the identity of the entry stay as they are.
    assert data[CONF_REPLY_ID] == REPLY_ID
    assert mock_config_entry.unique_id == unique_id

    # Reloaded: a call to the old ID changes nothing, one to the new ID is an alarm.
    assert mock_config_entry.state is ConfigEntryState.LOADED
    new_alarm = mock_config_entry.runtime_data.alarm
    assert new_alarm is not old_alarm
    assert await _call_webhook(hass, WEBHOOK_ID) == HTTPStatus.OK
    assert (new_alarm.calls_total, new_alarm.active) == (0, False)
    assert await _call_webhook(hass, new_id) == HTTPStatus.OK
    assert (new_alarm.calls_total, new_alarm.active) == (1, True)


@pytest.mark.usefixtures("external_url")
async def test_new_token_replaces_the_old_one(
    hass: HomeAssistant, token_entry: MockConfigEntry
) -> None:
    """With the token required, only the new token is accepted afterwards."""
    await async_setup_entry(hass, token_entry)
    result = await _start(hass, token_entry)

    result = await _submit(hass, result["flow_id"], {CONF_REGENERATE_WEBHOOK: True})

    new_id = token_entry.data[CONF_WEBHOOK_ID]
    new_token = token_entry.data[CONF_HEADER_TOKEN]
    alarm = token_entry.runtime_data.alarm
    old_headers = {TOKEN_HEADER: HEADER_TOKEN}
    assert await _call_webhook(hass, new_id, old_headers) == HTTPStatus.UNAUTHORIZED
    assert alarm.calls_total == 0
    new_headers = {TOKEN_HEADER: new_token}
    assert await _call_webhook(hass, new_id, new_headers) == HTTPStatus.OK
    assert alarm.calls_total == 1


async def test_new_webhook_access_with_cloud_replaces_the_cloudhook(
    hass: HomeAssistant, cloudhook_entry: MockConfigEntry
) -> None:
    """The new cloudhook is created first, then the old one is deleted."""
    order: list[tuple[str, str]] = []

    async def get_or_create(_hass: HomeAssistant, webhook_id: str) -> str:
        order.append(("create", webhook_id))
        return NEW_CLOUDHOOK_URL

    async def delete(_hass: HomeAssistant, webhook_id: str) -> None:
        order.append(("delete", webhook_id))

    with patch_cloud(hass) as cloud_mocks:
        cloud_mocks["get_or_create"].side_effect = get_or_create
        cloud_mocks["delete"].side_effect = delete
        await async_setup_entry(hass, cloudhook_entry)
        result = await _start(hass, cloudhook_entry)

        result = await _submit(hass, result["flow_id"], {CONF_REGENERATE_WEBHOOK: True})

    new_id = cloudhook_entry.data[CONF_WEBHOOK_ID]
    assert new_id != WEBHOOK_ID
    assert order == [("create", new_id), ("delete", WEBHOOK_ID)]
    assert cloudhook_entry.data[CONF_CLOUDHOOK] is True
    assert cloudhook_entry.data[CONF_CLOUDHOOK_URL] == NEW_CLOUDHOOK_URL
    assert result["reason"] == "reconfigure_successful_new_webhook"
    assert result["description_placeholders"]["webhook_url"] == NEW_CLOUDHOOK_URL


async def test_first_cloudhook_when_the_cloud_came_later(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """An entry without cloudhook gets one; there is no old one to delete."""
    await async_setup_entry(hass, mock_config_entry)
    result = await _start(hass, mock_config_entry)

    with patch_cloud(hass) as cloud_mocks:
        result = await _submit(hass, result["flow_id"], {CONF_REGENERATE_WEBHOOK: True})

    new_id = mock_config_entry.data[CONF_WEBHOOK_ID]
    cloud_mocks["get_or_create"].assert_awaited_once_with(hass, new_id)
    cloud_mocks["delete"].assert_not_called()
    assert mock_config_entry.data[CONF_CLOUDHOOK] is True
    assert mock_config_entry.data[CONF_CLOUDHOOK_URL] == CLOUDHOOK_URL
    assert result["description_placeholders"]["webhook_url"] == CLOUDHOOK_URL


@pytest.mark.usefixtures("external_url")
async def test_old_cloudhook_is_deleted_when_the_new_access_is_local(
    hass: HomeAssistant, cloudhook_entry: MockConfigEntry
) -> None:
    """Without a subscription the new access is local; the old cloudhook goes."""
    with patch_cloud(hass, subscription=False) as cloud_mocks:
        await async_setup_entry(hass, cloudhook_entry)
        result = await _start(hass, cloudhook_entry)

        result = await _submit(hass, result["flow_id"], {CONF_REGENERATE_WEBHOOK: True})

    cloud_mocks["get_or_create"].assert_not_called()
    cloud_mocks["delete"].assert_awaited_once_with(hass, WEBHOOK_ID)
    new_id = cloudhook_entry.data[CONF_WEBHOOK_ID]
    assert cloudhook_entry.data[CONF_CLOUDHOOK] is False
    assert cloudhook_entry.data[CONF_CLOUDHOOK_URL] is None
    assert result["description_placeholders"]["webhook_url"] == (
        f"{EXTERNAL_URL}/api/webhook/{new_id}"
    )


@pytest.mark.usefixtures("external_url")
async def test_old_cloudhook_without_the_cloud_integration_is_no_error(
    hass: HomeAssistant, cloudhook_entry: MockConfigEntry
) -> None:
    """If the cloud is not loaded anymore there is nothing to delete."""
    await async_setup_entry(hass, cloudhook_entry)
    result = await _start(hass, cloudhook_entry)

    result = await _submit(hass, result["flow_id"], {CONF_REGENERATE_WEBHOOK: True})

    assert result["reason"] == "reconfigure_successful_new_webhook"
    assert cloudhook_entry.data[CONF_CLOUDHOOK] is False


async def test_cloud_not_connected_keeps_the_old_access_and_can_be_retried(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """The menu leaves the old access intact; "try again" succeeds."""
    await async_setup_entry(hass, mock_config_entry)
    alarm = mock_config_entry.runtime_data.alarm
    data = dict(mock_config_entry.data)
    result = await _start(hass, mock_config_entry)

    with patch_cloud(hass, connected=False) as cloud_mocks:
        result = await _submit(hass, result["flow_id"], {CONF_REGENERATE_WEBHOOK: True})

    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "cloud_not_connected"
    cloud_mocks["get_or_create"].assert_not_called()
    assert dict(mock_config_entry.data) == data
    assert mock_config_entry.runtime_data.alarm is alarm
    assert await _call_webhook(hass) == HTTPStatus.OK
    assert alarm.calls_total == 1

    with patch_cloud(hass) as cloud_mocks:
        result = await _choose(hass, result["flow_id"], "cloud")

    assert result["reason"] == "reconfigure_successful_new_webhook"
    assert mock_config_entry.data[CONF_WEBHOOK_ID] != WEBHOOK_ID
    assert mock_config_entry.data[CONF_CLOUDHOOK_URL] == CLOUDHOOK_URL


@pytest.mark.usefixtures("external_url")
async def test_unexpected_error_aborts_and_logs_no_secret(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Only the type of an unexpected error is logged, never its message."""
    caplog.set_level(logging.DEBUG)
    await async_setup_entry(hass, mock_config_entry)
    data = dict(mock_config_entry.data)
    result = await _start(hass, mock_config_entry)

    with patch(
        "custom_components.ff_agent.config_flow.async_create_webhook_url",
        side_effect=RuntimeError(CLOUDHOOK_URL),
    ):
        result = await _submit(hass, result["flow_id"], {CONF_REGENERATE_WEBHOOK: True})

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "unknown"
    assert dict(mock_config_entry.data) == data
    assert "RuntimeError" in caplog.text
    assert CLOUDHOOK_URL not in caplog.text


async def test_new_reply_url_and_new_webhook_access_in_one_step(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Both changes are applied together and the reply client uses the new UUID."""
    aioclient_mock.get(OTHER_ACCEPT_URL)
    with patch_cloud(hass):
        await async_setup_entry(hass, mock_config_entry)
        result = await _start(hass, mock_config_entry)

        result = await _submit(
            hass,
            result["flow_id"],
            {CONF_REPLY_URL: OTHER_REPLY_URL, CONF_REGENERATE_WEBHOOK: True},
        )

    assert result["reason"] == "reconfigure_successful_new_webhook"
    assert mock_config_entry.unique_id == reply_unique_id(OTHER_REPLY_ID)
    assert mock_config_entry.data[CONF_REPLY_ID] == OTHER_REPLY_ID
    assert mock_config_entry.data[CONF_WEBHOOK_ID] != WEBHOOK_ID
    assert mock_config_entry.state is ConfigEntryState.LOADED
    await async_send_reply(hass, mock_config_entry, ReplyAction.ACCEPT)
    assert _requested(aioclient_mock)[1].endswith(f"{OTHER_REPLY_ID}/accept")


async def test_reconfigure_does_not_log_the_secrets(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Neither UUIDs nor webhook IDs, tokens or cloudhook URLs reach the log."""
    caplog.set_level(logging.DEBUG)
    with patch_cloud(hass):
        await async_setup_entry(hass, mock_config_entry)
        result = await _start(hass, mock_config_entry)
        result = await _submit(
            hass,
            result["flow_id"],
            {CONF_REPLY_URL: OTHER_REPLY_URL, CONF_REGENERATE_WEBHOOK: True},
        )

    secrets = (
        REPLY_ID,
        OTHER_REPLY_ID,
        OTHER_REPLY_URL,
        WEBHOOK_ID,
        HEADER_TOKEN,
        CLOUDHOOK_URL,
        mock_config_entry.data[CONF_WEBHOOK_ID],
        mock_config_entry.data[CONF_HEADER_TOKEN],
    )
    for secret in secrets:
        assert secret not in caplog.text
    assert result["description_placeholders"]["token"] not in caplog.text


# --- QA additions -----------------------


@pytest.mark.usefixtures("external_url")
@pytest.mark.parametrize("error", [CloudNotAvailable, ValueError])
async def test_failing_deletion_of_the_old_cloudhook_does_not_fail_the_flow(
    hass: HomeAssistant, cloudhook_entry: MockConfigEntry, error: type[Exception]
) -> None:
    """The new access counts even if the old cloudhook cannot be deleted."""
    with patch_cloud(hass, subscription=False) as cloud_mocks:
        cloud_mocks["delete"].side_effect = error("placeholder")
        await async_setup_entry(hass, cloudhook_entry)
        result = await _start(hass, cloudhook_entry)

        result = await _submit(hass, result["flow_id"], {CONF_REGENERATE_WEBHOOK: True})

    cloud_mocks["delete"].assert_awaited_once_with(hass, WEBHOOK_ID)
    new_id = cloudhook_entry.data[CONF_WEBHOOK_ID]
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful_new_webhook"
    assert new_id != WEBHOOK_ID
    assert cloudhook_entry.state is ConfigEntryState.LOADED
    assert cloudhook_entry.data[CONF_HEADER_TOKEN] != HEADER_TOKEN
    assert await _call_webhook(hass, WEBHOOK_ID) == HTTPStatus.OK
    assert cloudhook_entry.runtime_data.alarm.calls_total == 0
    assert await _call_webhook(hass, new_id) == HTTPStatus.OK
    assert cloudhook_entry.runtime_data.alarm.calls_total == 1


@pytest.mark.usefixtures("external_url")
async def test_uppercase_uuid_on_another_host_updates_only_the_host(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """The same UUID in capitals on another host: unique ID and UUID stay as stored."""
    await async_setup_entry(hass, mock_config_entry)
    unique_id = mock_config_entry.unique_id
    result = await _start(hass, mock_config_entry)
    url = f"https://free.ff-agent.com/app2/missionreplies/{REPLY_ID.upper()}/accept"

    result = await _submit(hass, result["flow_id"], {CONF_REPLY_URL: url})

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert mock_config_entry.unique_id == unique_id
    assert mock_config_entry.data[CONF_REPLY_ID] == REPLY_ID
    assert mock_config_entry.data[CONF_REPLY_HOST] == "free.ff-agent.com"
    assert mock_config_entry.state is ConfigEntryState.LOADED


@pytest.mark.usefixtures("external_url")
async def test_uuid_that_formerly_belonged_to_the_entry_is_taken_over(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Back to an earlier UUID is a normal change: no other entry holds it."""
    await async_setup_entry(hass, mock_config_entry)
    result = await _start(hass, mock_config_entry)
    await _submit(hass, result["flow_id"], {CONF_REPLY_URL: OTHER_REPLY_URL})
    assert mock_config_entry.unique_id == reply_unique_id(OTHER_REPLY_ID)

    result = await _start(hass, mock_config_entry)
    result = await _submit(hass, result["flow_id"], {CONF_REPLY_URL: REPLY_URL})

    assert result["reason"] == "reconfigure_successful"
    assert mock_config_entry.unique_id == reply_unique_id(REPLY_ID)
    assert mock_config_entry.data[CONF_REPLY_ID] == REPLY_ID


@pytest.mark.usefixtures("external_url")
async def test_unexpected_error_when_deleting_the_old_cloudhook_still_reloads(
    hass: HomeAssistant,
    cloudhook_entry: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Any error of the deletion is only logged (by type); the new access is loaded."""
    caplog.set_level(logging.DEBUG)
    with patch_cloud(hass, subscription=False) as cloud_mocks:
        cloud_mocks["delete"].side_effect = RuntimeError(CLOUDHOOK_URL)
        await async_setup_entry(hass, cloudhook_entry)
        old_alarm = cloudhook_entry.runtime_data.alarm
        result = await _start(hass, cloudhook_entry)

        result = await _submit(hass, result["flow_id"], {CONF_REGENERATE_WEBHOOK: True})

    cloud_mocks["delete"].assert_awaited_once_with(hass, WEBHOOK_ID)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful_new_webhook"
    new_id = cloudhook_entry.data[CONF_WEBHOOK_ID]
    assert new_id != WEBHOOK_ID
    # The reload happened: a new manager, and only the new webhook is registered.
    assert cloudhook_entry.state is ConfigEntryState.LOADED
    new_alarm = cloudhook_entry.runtime_data.alarm
    assert new_alarm is not old_alarm
    assert await _call_webhook(hass, new_id) == HTTPStatus.OK
    assert new_alarm.calls_total == 1
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert any("RuntimeError" in record.getMessage() for record in warnings)
    assert CLOUDHOOK_URL not in caplog.text


@pytest.mark.usefixtures("external_url")
async def test_new_webhook_access_removes_the_repair_issue(
    hass: HomeAssistant, token_entry: MockConfigEntry
) -> None:
    """The token is new, so the hint about a rejected call is obsolete."""
    await async_setup_entry(hass, token_entry)
    assert await _call_webhook(hass) == HTTPStatus.UNAUTHORIZED
    issue_id = ISSUE_TOKEN_REJECTED.format(entry_id=token_entry.entry_id)
    registry = ir.async_get(hass)
    assert registry.async_get_issue(DOMAIN, issue_id) is not None
    result = await _start(hass, token_entry)

    result = await _submit(hass, result["flow_id"], {CONF_REGENERATE_WEBHOOK: True})

    assert result["reason"] == "reconfigure_successful_new_webhook"
    # The token is still required after the reload, so the setup does not remove it.
    assert token_entry.state is ConfigEntryState.LOADED
    assert registry.async_get_issue(DOMAIN, issue_id) is None


@pytest.mark.usefixtures("external_url")
async def test_reply_url_change_keeps_the_repair_issue(
    hass: HomeAssistant, token_entry: MockConfigEntry
) -> None:
    """Without a new token the hint stays: the rejected call is still unexplained."""
    await async_setup_entry(hass, token_entry)
    assert await _call_webhook(hass) == HTTPStatus.UNAUTHORIZED
    issue_id = ISSUE_TOKEN_REJECTED.format(entry_id=token_entry.entry_id)
    result = await _start(hass, token_entry)

    await _submit(hass, result["flow_id"], {CONF_REPLY_URL: OTHER_REPLY_URL})

    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is not None


# --- Switching the alarm source -----------------------


def _subscribe(hass: HomeAssistant, topic: str) -> er.RegistryEntry:
    """Simulate the subscription of the topic in the ntfy integration."""
    ntfy_entry = add_ntfy_entry(hass, {OTHER_NTFY_SUBENTRY_ID: topic})
    return add_ntfy_entity(
        hass, ntfy_entry, OTHER_NTFY_SUBENTRY_ID, OTHER_NTFY_ENTITY_ID
    )


async def test_webhook_to_ntfy(
    hass: HomeAssistant, cloudhook_entry: MockConfigEntry
) -> None:
    """Data switched, cloudhook and token issue gone, webhook closed, reloaded."""
    with patch_cloud(hass) as cloud_mocks:
        await async_setup_entry(hass, cloudhook_entry)
        issue_id = ISSUE_TOKEN_REJECTED.format(entry_id=cloudhook_entry.entry_id)
        ir.async_create_issue(
            hass,
            DOMAIN,
            issue_id,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="webhook_token_rejected",
            translation_placeholders={"title": cloudhook_entry.title},
        )
        old_alarm = cloudhook_entry.runtime_data.alarm
        result = await _start(hass, cloudhook_entry)

        result = await _submit(hass, result["flow_id"], {CONF_ALARM_SOURCE: "ntfy"})
        assert result["type"] is FlowResultType.MENU
        assert result["step_id"] == "ntfy"
        topic = result["description_placeholders"]["ntfy_topic"]
        registry_entry = _subscribe(hass, topic)
        result = await _choose(hass, result["flow_id"], "ntfy_find")

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful_ntfy"
    publish_url = f"https://ntfy.sh/{topic}/trigger"
    assert result["description_placeholders"] == {
        **LINKS,
        "ntfy_publish_url": publish_url,
    }
    data = cloudhook_entry.data
    assert data[CONF_ALARM_SOURCE] == "ntfy"
    assert data[CONF_NTFY_ENTITY_UUID] == registry_entry.id
    assert data[CONF_NTFY_TOPIC] == topic
    assert data[CONF_NTFY_SERVER] == "https://ntfy.sh/"
    assert (data[CONF_CLOUDHOOK], data[CONF_CLOUDHOOK_URL]) == (False, None)
    # The webhook ID and the token stay, dormant, for a later switch back.
    assert data[CONF_WEBHOOK_ID] == WEBHOOK_ID
    assert data[CONF_HEADER_TOKEN] == HEADER_TOKEN
    cloud_mocks["get_or_create"].assert_not_called()
    cloud_mocks["delete"].assert_awaited_once_with(hass, WEBHOOK_ID)
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None
    assert cloudhook_entry.state is ConfigEntryState.LOADED
    assert cloudhook_entry.runtime_data.alarm is not old_alarm
    assert cloudhook_entry.runtime_data.source is not None
    # The webhook is closed: a call does not reach the entry anymore.
    assert await _call_webhook(hass) == HTTPStatus.OK
    assert cloudhook_entry.runtime_data.alarm.calls_total == 0


@pytest.mark.parametrize("regenerate", [False, True])
async def test_ntfy_to_webhook_with_cloud(
    hass: HomeAssistant, ntfy_entry: MockConfigEntry, regenerate: bool
) -> None:
    """Back to the webhook: the stored ID is reused unless a new one is wanted."""
    await async_setup_entry(hass, ntfy_entry)
    issue_id = ISSUE_NTFY_ENTITY_MISSING.format(entry_id=ntfy_entry.entry_id)
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        severity=ir.IssueSeverity.ERROR,
        translation_key="ntfy_entity_missing",
        translation_placeholders={"title": ntfy_entry.title},
    )
    result = await _start(hass, ntfy_entry)
    schema = result["data_schema"].schema
    source_key = next(key for key in schema if key == CONF_ALARM_SOURCE)
    assert source_key.default() == "ntfy"

    with patch_cloud(hass) as cloud_mocks:
        result = await _submit(
            hass,
            result["flow_id"],
            {CONF_ALARM_SOURCE: "webhook", CONF_REGENERATE_WEBHOOK: regenerate},
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful_new_webhook"
    data = ntfy_entry.data
    assert data[CONF_ALARM_SOURCE] == "webhook"
    assert (data[CONF_WEBHOOK_ID] == WEBHOOK_ID) is not regenerate
    assert (data[CONF_HEADER_TOKEN] == HEADER_TOKEN) is not regenerate
    assert data[CONF_CLOUDHOOK] is True
    assert data[CONF_CLOUDHOOK_URL] == CLOUDHOOK_URL
    cloud_mocks["get_or_create"].assert_awaited_once_with(hass, data[CONF_WEBHOOK_ID])
    cloud_mocks["delete"].assert_not_called()
    placeholders = result["description_placeholders"]
    assert placeholders["webhook_url"] == CLOUDHOOK_URL
    assert placeholders["token"] == data[CONF_HEADER_TOKEN]
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None
    assert ntfy_entry.state is ConfigEntryState.LOADED
    assert ntfy_entry.runtime_data.source is None
    assert await _call_webhook(hass, data[CONF_WEBHOOK_ID]) == HTTPStatus.OK
    assert ntfy_entry.runtime_data.alarm.calls_total == 1


async def test_ntfy_to_unreachable_webhook_shows_the_cloud_guide(
    hass: HomeAssistant, ntfy_entry: MockConfigEntry
) -> None:
    """Without the first question, straight into the guide and the checklist."""
    await async_setup_entry(hass, ntfy_entry)
    data = dict(ntfy_entry.data)
    result = await _start(hass, ntfy_entry)

    result = await _submit(hass, result["flow_id"], {CONF_ALARM_SOURCE: "webhook"})
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "cloud_setup"
    result = await _choose(hass, result["flow_id"], "cloud")
    assert result["step_id"] == "cloud_setup_retry"

    # Back to ntfy from the guide: nothing changed.
    result = await _choose(hass, result["flow_id"], "ntfy")
    assert result["step_id"] == "ntfy"
    assert result["description_placeholders"]["ntfy_topic"] == NTFY_TOPIC
    result = await _choose(hass, result["flow_id"], "ntfy_find")

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert dict(ntfy_entry.data) == data


async def test_ntfy_unchanged_does_not_reload(
    hass: HomeAssistant, ntfy_entry: MockConfigEntry
) -> None:
    """Same source, same entity, same topic: no reload."""
    await async_setup_entry(hass, ntfy_entry)
    alarm = ntfy_entry.runtime_data.alarm
    result = await _start(hass, ntfy_entry)

    result = await _submit(hass, result["flow_id"], {})
    assert result["step_id"] == "ntfy"
    placeholders = result["description_placeholders"]
    assert placeholders["ntfy_topic"] == NTFY_TOPIC
    assert placeholders["ntfy_publish_url"] == NTFY_PUBLISH_URL
    result = await _choose(hass, result["flow_id"], "ntfy_find")

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert ntfy_entry.runtime_data.alarm is alarm


async def test_ntfy_new_topic_and_the_current_entity_as_suggestion(
    hass: HomeAssistant, ntfy_entry: MockConfigEntry
) -> None:
    """A new topic is shown; the current entity is offered when it is not found."""
    await async_setup_entry(hass, ntfy_entry)
    result = await _start(hass, ntfy_entry)

    result = await _submit(hass, result["flow_id"], {CONF_REGENERATE_WEBHOOK: True})
    topic = result["description_placeholders"]["ntfy_topic"]
    assert topic != NTFY_TOPIC
    result = await _choose(hass, result["flow_id"], "ntfy_find")
    assert result["step_id"] == "ntfy_select"
    assert result["errors"] == {"base": "ntfy_entity_not_found"}
    key = next(key for key in result["data_schema"].schema if key == "ntfy_entity")
    assert key.description == {"suggested_value": NTFY_ENTITY_ID}

    # The new topic is subscribed: the entry moves to its entity.
    registry_entry = _subscribe(hass, topic)
    result = await _submit(hass, result["flow_id"], {})

    assert result["reason"] == "reconfigure_successful_ntfy"
    assert ntfy_entry.data[CONF_NTFY_TOPIC] == topic
    assert ntfy_entry.data[CONF_NTFY_ENTITY_UUID] == registry_entry.id
    assert ntfy_entry.runtime_data.source is not None


async def test_ntfy_own_entity_is_not_in_use(
    hass: HomeAssistant, ntfy_entry: MockConfigEntry
) -> None:
    """The entry may keep its own entity; that is no conflict with itself."""
    await async_setup_entry(hass, ntfy_entry)
    result = await _start(hass, ntfy_entry)
    result = await _submit(hass, result["flow_id"], {CONF_REGENERATE_WEBHOOK: True})
    result = await _choose(hass, result["flow_id"], "ntfy_find")

    result = await _submit(hass, result["flow_id"], {"ntfy_entity": NTFY_ENTITY_ID})

    # The topic is read from the entity, so nothing changed.
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert ntfy_entry.data[CONF_NTFY_TOPIC] == NTFY_TOPIC


async def test_internal_webhook_gets_a_cloudhook_for_the_same_id(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """After setting up the cloud, saving creates the cloudhook for the old ID."""
    await async_process_ha_core_config(hass, {"internal_url": INTERNAL_URL})
    await async_setup_entry(hass, mock_config_entry)
    result = await _start(hass, mock_config_entry)

    with patch_cloud(hass) as cloud_mocks:
        result = await _submit(hass, result["flow_id"], {})

    assert result["reason"] == "reconfigure_successful_new_webhook"
    cloud_mocks["get_or_create"].assert_awaited_once_with(hass, WEBHOOK_ID)
    cloud_mocks["delete"].assert_not_called()
    assert mock_config_entry.data[CONF_WEBHOOK_ID] == WEBHOOK_ID
    assert mock_config_entry.data[CONF_HEADER_TOKEN] == HEADER_TOKEN
    assert mock_config_entry.data[CONF_CLOUDHOOK_URL] == CLOUDHOOK_URL


async def test_internal_webhook_unchanged_with_continue_anyway(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Still unreachable and continue anyway: nothing changes, no reload."""
    await async_process_ha_core_config(hass, {"internal_url": INTERNAL_URL})
    await async_setup_entry(hass, mock_config_entry)
    alarm = mock_config_entry.runtime_data.alarm
    result = await _start(hass, mock_config_entry)

    result = await _submit(hass, result["flow_id"], {})
    assert result["step_id"] == "cloud_setup"
    result = await _choose(hass, result["flow_id"], "webhook_anyway")

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert mock_config_entry.runtime_data.alarm is alarm


async def test_failing_cloudhook_deletion_on_the_way_to_ntfy(
    hass: HomeAssistant,
    cloudhook_entry: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A cloudhook that cannot be deleted does not stop the switch."""
    with patch_cloud(hass) as cloud_mocks:
        cloud_mocks["delete"].side_effect = RuntimeError(CLOUDHOOK_URL)
        await async_setup_entry(hass, cloudhook_entry)
        result = await _start(hass, cloudhook_entry)
        result = await _submit(hass, result["flow_id"], {CONF_ALARM_SOURCE: "ntfy"})
        _subscribe(hass, result["description_placeholders"]["ntfy_topic"])
        result = await _choose(hass, result["flow_id"], "ntfy_find")

    assert result["reason"] == "reconfigure_successful_ntfy"
    assert cloudhook_entry.data[CONF_ALARM_SOURCE] == "ntfy"
    assert "RuntimeError" in caplog.text
    assert CLOUDHOOK_URL not in caplog.text


async def test_switching_logs_no_topic(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The topic and the entity ID of ntfy never reach the log of the integration.

    Home Assistant itself logs entity IDs (entity registry, platforms) on INFO level.
    """
    caplog.set_level(logging.DEBUG, logger="custom_components.ff_agent")
    await async_setup_entry(hass, mock_config_entry)
    result = await _start(hass, mock_config_entry)
    result = await _submit(hass, result["flow_id"], {CONF_ALARM_SOURCE: "ntfy"})
    topic = result["description_placeholders"]["ntfy_topic"]
    registry_entry = _subscribe(hass, topic)
    result = await _choose(hass, result["flow_id"], "ntfy_find")

    assert result["reason"] == "reconfigure_successful_ntfy"
    ours = "
".join(
        record.getMessage()
        for record in caplog.records
        if record.name.startswith("custom_components.ff_agent")
    )
    for secret in (topic, OTHER_NTFY_ENTITY_ID, registry_entry.id):
        assert secret not in ours
        assert secret not in "
".join(
            record.getMessage()
            for record in caplog.records
            if record.levelno >= logging.WARNING
        )


async def test_webhook_to_ntfy_without_the_ntfy_integration(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Without ntfy the form asks to set it up and suggests no entity."""
    await async_setup_entry(hass, mock_config_entry)
    data = dict(mock_config_entry.data)
    result = await _start(hass, mock_config_entry)
    result = await _submit(hass, result["flow_id"], {CONF_ALARM_SOURCE: "ntfy"})

    result = await _choose(hass, result["flow_id"], "ntfy_find")

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "ntfy_select"
    assert result["errors"] == {"base": "ntfy_not_set_up"}
    key = next(key for key in result["data_schema"].schema if key == "ntfy_entity")
    assert key.description is None
    assert dict(mock_config_entry.data) == data
