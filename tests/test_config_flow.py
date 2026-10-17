"""Tests for the FF Agent config flow."""

from __future__ import annotations

import logging
from unittest.mock import patch

import pytest
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_NAME, CONF_WEBHOOK_ID
from homeassistant.core import HomeAssistant
from homeassistant.core_config import async_process_ha_core_config
from homeassistant.data_entry_flow import FlowResult, FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.ff_agent.const import (
    CONF_CLOUDHOOK,
    CONF_CLOUDHOOK_URL,
    CONF_DEFAULT_TRANSPORT,
    CONF_HEADER_TOKEN,
    CONF_REPLY_HOST,
    CONF_REPLY_ID,
    CONF_REPLY_URL,
    CONF_REQUIRE_TOKEN,
    CONF_RESET_MINUTES,
    DEFAULT_REPLY_HOST,
    DOMAIN,
    NAME,
)
from custom_components.ff_agent.reply_url import reply_unique_id
from custom_components.ff_agent.webhook_url import UrlKind

from .common import patch_cloud
from .const import (
    CLOUDHOOK_URL,
    EXTERNAL_URL,
    INTERNAL_URL,
    OTHER_REPLY_ID,
    OTHER_REPLY_URL,
    REPLY_ID,
    REPLY_URL,
)

PATH = "/api/webhook/test-webhook-id-placeholder"
MISSION_PATH = "/app2/missionreplies"


async def _start_flow(hass: HomeAssistant) -> FlowResult:
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


async def _submit(
    hass: HomeAssistant,
    flow_id: str,
    reply_url: str = REPLY_URL,
    name: str = "Test Person",
) -> FlowResult:
    result = await hass.config_entries.flow.async_configure(
        flow_id, {CONF_NAME: name, CONF_REPLY_URL: reply_url}
    )
    await hass.async_block_till_done()
    return result


async def test_user_flow_shows_form(hass: HomeAssistant) -> None:
    """The user step asks for a name and the reply URL."""
    result = await _start_flow(hass)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}
    assert set(result["data_schema"].schema) == {CONF_NAME, CONF_REPLY_URL}


@pytest.mark.usefixtures("external_url")
async def test_user_flow_creates_entry_with_external_url(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    """A valid reply URL creates an entry that points at the external URL."""
    caplog.set_level(logging.DEBUG)
    result = await _start_flow(hass)
    result = await _submit(hass, result["flow_id"])

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Test Person"
    assert result["description"] == "external"
    entry: ConfigEntry = result["result"]
    webhook_id = entry.data[CONF_WEBHOOK_ID]
    webhook_url = f"{EXTERNAL_URL}/api/webhook/{webhook_id}"
    assert result["description_placeholders"] == {"webhook_url": webhook_url}

    assert entry.unique_id == reply_unique_id(REPLY_ID)
    assert entry.data == {
        CONF_REPLY_ID: REPLY_ID,
        CONF_REPLY_HOST: DEFAULT_REPLY_HOST,
        CONF_WEBHOOK_ID: webhook_id,
        CONF_CLOUDHOOK: False,
        CONF_CLOUDHOOK_URL: None,
        CONF_HEADER_TOKEN: entry.data[CONF_HEADER_TOKEN],
    }
    assert entry.options == {
        CONF_RESET_MINUTES: 30,
        CONF_DEFAULT_TRANSPORT: "car",
        CONF_REQUIRE_TOKEN: False,
    }
    assert entry.state is ConfigEntryState.LOADED

    # No secret ends up in the log, not even at DEBUG level.
    for secret in (
        REPLY_ID,
        REPLY_URL,
        webhook_id,
        webhook_url,
        entry.data[CONF_HEADER_TOKEN],
    ):
        assert secret not in caplog.text


async def test_user_flow_never_stores_the_full_url(hass: HomeAssistant) -> None:
    """Only the UUID and the host are stored, not the URL the user pasted."""
    result = await _start_flow(hass)
    result = await _submit(hass, result["flow_id"])

    entry: ConfigEntry = result["result"]
    assert CONF_REPLY_URL not in entry.data
    assert "missionreplies" not in str(entry.data)
    assert "transport=CAR" not in str(entry.data)


async def test_user_flow_with_cloud(hass: HomeAssistant) -> None:
    """With an active cloud subscription a cloudhook is created and stored."""
    result = await _start_flow(hass)
    with patch_cloud(hass) as cloud_mocks:
        result = await _submit(hass, result["flow_id"])

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["description"] == "cloud"
    assert result["description_placeholders"] == {"webhook_url": CLOUDHOOK_URL}
    entry: ConfigEntry = result["result"]
    assert entry.data[CONF_CLOUDHOOK] is True
    assert entry.data[CONF_CLOUDHOOK_URL] == CLOUDHOOK_URL
    cloud_mocks["get_or_create"].assert_awaited_once_with(
        hass, entry.data[CONF_WEBHOOK_ID]
    )


async def test_user_flow_internal_url(hass: HomeAssistant) -> None:
    """Only an internal URL is reported as such."""
    await async_process_ha_core_config(hass, {"internal_url": INTERNAL_URL})
    result = await _start_flow(hass)
    result = await _submit(hass, result["flow_id"])

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["description"] == "internal"
    assert result["description_placeholders"]["webhook_url"].startswith(INTERNAL_URL)


async def test_user_flow_path_only(hass: HomeAssistant) -> None:
    """Without any URL the dialog gets the bare path.

    The flow itself starts the http integration, which makes an internal URL
    available, so the URL helper is stubbed here.
    """
    result = await _start_flow(hass)
    with patch(
        "custom_components.ff_agent.config_flow.async_create_webhook_url",
        return_value=(PATH, UrlKind.PATH_ONLY, False),
    ):
        result = await _submit(hass, result["flow_id"])

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["description"] == "path_only"
    assert result["description_placeholders"] == {"webhook_url": PATH}


@pytest.mark.parametrize(
    "value",
    ["", "not a url", "https://example.com/app2/missionreplies/x/accept"],
)
@pytest.mark.usefixtures("external_url")
async def test_user_flow_invalid_url_then_recovery(
    hass: HomeAssistant, value: str
) -> None:
    """An invalid input shows an error at the field and can be corrected."""
    result = await _start_flow(hass)
    result = await _submit(hass, result["flow_id"], value)

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_REPLY_URL: "invalid_reply_url"}
    assert hass.config_entries.async_entries(DOMAIN) == []

    result = await _submit(hass, result["flow_id"])

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1


async def test_user_flow_cloud_not_connected_then_recovery(
    hass: HomeAssistant,
) -> None:
    """A disconnected cloud shows a base error and a retry succeeds."""
    result = await _start_flow(hass)
    with patch_cloud(hass, connected=False) as cloud_mocks:
        result = await _submit(hass, result["flow_id"])

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cloud_not_connected"}
    cloud_mocks["get_or_create"].assert_not_called()
    assert hass.config_entries.async_entries(DOMAIN) == []

    with patch_cloud(hass):
        result = await _submit(hass, result["flow_id"])

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["description"] == "cloud"


@pytest.mark.parametrize(
    "reply_url",
    [
        REPLY_URL,
        REPLY_ID,
        REPLY_ID.upper(),
        f"https://free.ff-agent.com/app2/missionreplies/{REPLY_ID}/reject",
    ],
)
async def test_user_flow_same_person_is_aborted(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, reply_url: str
) -> None:
    """The same person cannot be added twice, however the URL is written."""
    mock_config_entry.add_to_hass(hass)

    result = await _start_flow(hass)
    result = await _submit(hass, result["flow_id"], reply_url)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert hass.config_entries.async_entries(DOMAIN) == [mock_config_entry]


@pytest.mark.usefixtures("external_url")
async def test_user_flow_two_persons_give_two_entries(hass: HomeAssistant) -> None:
    """Different persons coexist, each with its own webhook and token."""
    first = await _start_flow(hass)
    first = await _submit(hass, first["flow_id"], REPLY_URL)
    second = await _start_flow(hass)
    second = await _submit(hass, second["flow_id"], OTHER_REPLY_URL)

    assert first["type"] is FlowResultType.CREATE_ENTRY
    assert second["type"] is FlowResultType.CREATE_ENTRY
    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 2
    assert {entry.data[CONF_REPLY_ID] for entry in entries} == {
        REPLY_ID,
        OTHER_REPLY_ID,
    }
    assert len({entry.unique_id for entry in entries}) == 2
    assert len({entry.data[CONF_WEBHOOK_ID] for entry in entries}) == 2
    assert len({entry.data[CONF_HEADER_TOKEN] for entry in entries}) == 2


async def test_user_flow_header_token_and_options(hass: HomeAssistant) -> None:
    """Every entry gets a long random token and the token check starts disabled."""
    result = await _start_flow(hass)
    result = await _submit(hass, result["flow_id"])

    entry: ConfigEntry = result["result"]
    assert len(entry.data[CONF_HEADER_TOKEN]) >= 40
    assert entry.options[CONF_REQUIRE_TOKEN] is False


async def test_user_flow_makes_no_request_to_ff_agent(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Setting up never calls FF Agent, a call would be a real mission reply."""
    result = await _start_flow(hass)
    await _submit(hass, result["flow_id"])

    assert aioclient_mock.call_count == 0


async def test_duplicate_person_does_not_create_a_cloudhook(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """A rejected duplicate leaves no orphaned cloudhook behind."""
    mock_config_entry.add_to_hass(hass)

    result = await _start_flow(hass)
    with patch_cloud(hass) as cloud_mocks:
        result = await _submit(hass, result["flow_id"], REPLY_ID.upper())

    assert result["type"] is FlowResultType.ABORT
    cloud_mocks["get_or_create"].assert_not_called()


@pytest.mark.parametrize(
    "value",
    [
        f"https://ff-agent.com.evil.example{MISSION_PATH}/{REPLY_ID}/accept",
        f"http://www.ff-agent.com{MISSION_PATH}/{REPLY_ID}/accept",
    ],
)
async def test_error_paths_leak_no_secret(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture, value: str
) -> None:
    """Errors and logs of failed attempts contain neither the UUID nor the URL."""
    caplog.set_level(logging.DEBUG)
    result = await _start_flow(hass)
    result = await _submit(hass, result["flow_id"], value)

    assert result["errors"] == {CONF_REPLY_URL: "invalid_reply_url"}
    assert REPLY_ID not in str(result["errors"])
    assert "http" not in str(result["errors"])
    assert REPLY_ID not in caplog.text
    assert value not in caplog.text


async def test_cloud_error_leaks_no_secret(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    """A disconnected cloud neither logs nor shows the UUID or a webhook URL."""
    caplog.set_level(logging.DEBUG)
    result = await _start_flow(hass)
    with patch_cloud(hass, connected=False):
        result = await _submit(hass, result["flow_id"])

    assert result["errors"] == {"base": "cloud_not_connected"}
    assert REPLY_ID not in caplog.text
    assert CLOUDHOOK_URL not in caplog.text
    assert REPLY_ID not in str(result["errors"])


async def test_created_entry_is_not_logged_on_cloud_path(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    """With a cloudhook neither the cloudhook URL nor the secrets reach the log."""
    caplog.set_level(logging.DEBUG)
    result = await _start_flow(hass)
    with patch_cloud(hass):
        result = await _submit(hass, result["flow_id"])

    entry: ConfigEntry = result["result"]
    for secret in (
        REPLY_ID,
        CLOUDHOOK_URL,
        entry.data[CONF_WEBHOOK_ID],
        entry.data[CONF_HEADER_TOKEN],
    ):
        assert secret not in caplog.text


@pytest.mark.parametrize("name", ["", "   ", "\t\n"])
async def test_blank_name_falls_back_to_the_default(
    hass: HomeAssistant, name: str
) -> None:
    """An empty or whitespace-only name gives the entry the default title."""
    result = await _start_flow(hass)
    result = await _submit(hass, result["flow_id"], name=name)

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == NAME


async def test_name_is_stripped(hass: HomeAssistant) -> None:
    """Surrounding whitespace is removed from the title."""
    result = await _start_flow(hass)
    result = await _submit(hass, result["flow_id"], name="  Test Person  ")

    assert result["title"] == "Test Person"


async def test_reply_url_field_is_plain_text(hass: HomeAssistant) -> None:
    """The field also takes a bare UUID, so it must not be a URL input."""
    result = await _start_flow(hass)

    (marker,) = (key for key in result["data_schema"].schema if key == CONF_REPLY_URL)
    assert result["data_schema"].schema[marker].config["type"] == "text"


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (TimeoutError(REPLY_URL), "cloud_not_connected"),
        (ValueError(REPLY_URL), "cloud_not_connected"),
        (RuntimeError(REPLY_URL), "unknown"),
    ],
)
async def test_cloudhook_errors_then_recovery(
    hass: HomeAssistant,
    caplog: pytest.LogCaptureFixture,
    error: Exception,
    expected: str,
) -> None:
    """Failures while creating the cloudhook show a form error and can be retried.

    The exception message carries the secret URL; it must not reach the log.
    """
    caplog.set_level(logging.DEBUG)
    result = await _start_flow(hass)
    with patch_cloud(hass) as cloud_mocks:
        cloud_mocks["get_or_create"].side_effect = error
        result = await _submit(hass, result["flow_id"])

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": expected}
    assert hass.config_entries.async_entries(DOMAIN) == []
    assert REPLY_URL not in caplog.text
    assert REPLY_ID not in caplog.text
    if expected == "unknown":
        assert "RuntimeError" in caplog.text

    with patch_cloud(hass):
        result = await _submit(hass, result["flow_id"])

    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_second_flow_for_same_person_is_already_in_progress(
    hass: HomeAssistant,
) -> None:
    """A flow that is still open blocks a second one for the same person."""
    first = await _start_flow(hass)
    with patch_cloud(hass, connected=False):
        first = await _submit(hass, first["flow_id"])
    assert first["type"] is FlowResultType.FORM

    second = await _start_flow(hass)
    second = await _submit(hass, second["flow_id"])

    assert second["type"] is FlowResultType.ABORT
    assert second["reason"] == "already_in_progress"
