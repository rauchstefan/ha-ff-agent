"""Tests for the FF Agent config flow."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_NAME, CONF_WEBHOOK_ID
from homeassistant.core import HomeAssistant
from homeassistant.core_config import async_process_ha_core_config
from homeassistant.data_entry_flow import FlowResult, FlowResultType
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.ff_agent.const import (
    CONF_ALARM_SOURCE,
    CONF_CLOUDHOOK,
    CONF_CLOUDHOOK_URL,
    CONF_DEFAULT_TRANSPORT,
    CONF_HEADER_TOKEN,
    CONF_NTFY_ENTITY,
    CONF_NTFY_ENTITY_UUID,
    CONF_NTFY_SERVER,
    CONF_NTFY_TOPIC,
    CONF_REPLY_HOST,
    CONF_REPLY_ID,
    CONF_REPLY_URL,
    CONF_REQUIRE_TOKEN,
    CONF_RESET_MINUTES,
    DEFAULT_REPLY_HOST,
    DOMAIN,
    MY_CLOUD_URL,
    MY_NETWORK_URL,
    MY_NTFY_INTEGRATION_URL,
    MY_NTFY_SETUP_URL,
    NAME,
)
from custom_components.ff_agent.reply_url import reply_unique_id
from custom_components.ff_agent.webhook_url import UrlKind

from .common import add_ntfy_entity, add_ntfy_entry, patch_cloud
from .const import (
    CLOUDHOOK_URL,
    EXTERNAL_URL,
    INTERNAL_URL,
    NTFY_ENTITY_ID,
    OTHER_NTFY_ENTITY_ID,
    OTHER_NTFY_SUBENTRY_ID,
    OTHER_NTFY_TOPIC,
    OTHER_REPLY_ID,
    OTHER_REPLY_URL,
    OWN_NTFY_SERVER,
    REPLY_ID,
    REPLY_URL,
)

PATH = "/api/webhook/test-webhook-id-placeholder"
MISSION_PATH = "/app2/missionreplies"
TRANSLATIONS = Path(__file__).parents[1] / "custom_components/ff_agent/translations"
LINKS = {
    "cloud_url": MY_CLOUD_URL,
    "network_url": MY_NETWORK_URL,
    "ntfy_setup_url": MY_NTFY_SETUP_URL,
    "ntfy_integration_url": MY_NTFY_INTEGRATION_URL,
}
TOPIC = re.compile(r"^[0-9a-f]{32}$")


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


async def _choose(hass: HomeAssistant, flow_id: str, option: str) -> FlowResult:
    """Choose an option of a menu."""
    result = await hass.config_entries.flow.async_configure(
        flow_id, {"next_step_id": option}
    )
    await hass.async_block_till_done()
    return result


async def _configure(
    hass: HomeAssistant, flow_id: str, values: dict[str, Any]
) -> FlowResult:
    result = await hass.config_entries.flow.async_configure(flow_id, values)
    await hass.async_block_till_done()
    return result


async def _to_menu(hass: HomeAssistant, name: str = "Test Person") -> FlowResult:
    """Start the flow and enter the reply URL; return the first question."""
    result = await _start_flow(hass)
    return await _submit(hass, result["flow_id"], name=name)


async def _create_with_cloud_path(
    hass: HomeAssistant, name: str = "Test Person", reply_url: str = REPLY_URL
) -> FlowResult:
    """Run the flow with the answer "yes, Home Assistant Cloud"."""
    result = await _start_flow(hass)
    result = await _submit(hass, result["flow_id"], reply_url, name)
    return await _choose(hass, result["flow_id"], "cloud")


async def _to_ntfy_guide(hass: HomeAssistant) -> FlowResult:
    """Run the flow up to the guide for ntfy."""
    result = await _to_menu(hass)
    result = await _choose(hass, result["flow_id"], "no_cloud")
    return await _choose(hass, result["flow_id"], "ntfy")


def _subscribe(hass: HomeAssistant, topic: str) -> er.RegistryEntry:
    """Simulate the subscription of the topic in the ntfy integration."""
    ntfy_entry = add_ntfy_entry(hass, {"subentry-flow": topic})
    return add_ntfy_entity(hass, ntfy_entry, "subentry-flow")


def _text(language: str, result: FlowResult) -> str:
    """Return the translated description of a flow result."""
    texts = json.loads((TRANSLATIONS / f"{language}.json").read_text("utf-8"))
    config = texts["config"]
    if result["type"] is FlowResultType.CREATE_ENTRY:
        return config["create_entry"][result["description"]]
    if result["type"] is FlowResultType.ABORT:
        return config["abort"][result["reason"]]
    return config["step"][result["step_id"]]["description"]


def _assert_placeholders(result: FlowResult) -> None:
    """Every placeholder of the text is delivered by the flow."""
    given = set(result.get("description_placeholders") or {})
    for language in ("en", "de"):
        needed = set(re.findall(r"\{(\w+)\}", _text(language, result)))
        assert needed <= given, (result.get("step_id"), needed - given)


# --- The user step -----------------------


async def test_user_flow_shows_form(hass: HomeAssistant) -> None:
    """The user step asks for a name and the reply URL."""
    result = await _start_flow(hass)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}
    assert set(result["data_schema"].schema) == {CONF_NAME, CONF_REPLY_URL}


async def test_first_question_without_cloud(hass: HomeAssistant) -> None:
    """After the reply URL comes the question about Home Assistant Cloud."""
    result = await _to_menu(hass)

    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "alarm_source"
    assert result["menu_options"] == ["cloud", "no_cloud"]
    _assert_placeholders(result)
    assert hass.config_entries.async_entries(DOMAIN) == []


async def test_first_question_with_cloud_only_changes_the_text(
    hass: HomeAssistant,
) -> None:
    """A detected subscription changes the text, but nothing is created yet."""
    with patch_cloud(hass) as cloud_mocks:
        result = await _to_menu(hass)

    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "alarm_source_cloud"
    assert result["menu_options"] == ["cloud", "no_cloud"]
    cloud_mocks["get_or_create"].assert_not_called()
    assert hass.config_entries.async_entries(DOMAIN) == []


# --- The cloud path -----------------------


@pytest.mark.usefixtures("external_url")
async def test_user_flow_creates_entry_with_external_url(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    """A valid reply URL creates an entry that points at the external URL."""
    caplog.set_level(logging.DEBUG)
    result = await _create_with_cloud_path(hass)

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Test Person"
    assert result["description"] == "external"
    entry: ConfigEntry = result["result"]
    webhook_id = entry.data[CONF_WEBHOOK_ID]
    webhook_url = f"{EXTERNAL_URL}/api/webhook/{webhook_id}"
    assert result["description_placeholders"] == {**LINKS, "webhook_url": webhook_url}
    _assert_placeholders(result)

    assert entry.unique_id == reply_unique_id(REPLY_ID)
    assert (entry.version, entry.minor_version) == (1, 2)
    assert entry.data == {
        CONF_REPLY_ID: REPLY_ID,
        CONF_REPLY_HOST: DEFAULT_REPLY_HOST,
        CONF_ALARM_SOURCE: "webhook",
        CONF_WEBHOOK_ID: webhook_id,
        CONF_CLOUDHOOK: False,
        CONF_CLOUDHOOK_URL: None,
        CONF_HEADER_TOKEN: entry.data[CONF_HEADER_TOKEN],
        CONF_NTFY_ENTITY_UUID: None,
        CONF_NTFY_TOPIC: None,
        CONF_NTFY_SERVER: None,
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


@pytest.mark.usefixtures("external_url")
async def test_user_flow_never_stores_the_full_url(hass: HomeAssistant) -> None:
    """Only the UUID and the host are stored, not the URL the user pasted."""
    result = await _create_with_cloud_path(hass)

    entry: ConfigEntry = result["result"]
    assert CONF_REPLY_URL not in entry.data
    assert "missionreplies" not in str(entry.data)
    assert "transport=CAR" not in str(entry.data)


async def test_user_flow_with_cloud(hass: HomeAssistant) -> None:
    """With an active cloud subscription "yes" creates and stores a cloudhook."""
    with patch_cloud(hass) as cloud_mocks:
        result = await _create_with_cloud_path(hass)

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["description"] == "cloud"
    assert result["description_placeholders"] == {
        **LINKS,
        "webhook_url": CLOUDHOOK_URL,
    }
    entry: ConfigEntry = result["result"]
    assert entry.data[CONF_CLOUDHOOK] is True
    assert entry.data[CONF_CLOUDHOOK_URL] == CLOUDHOOK_URL
    assert entry.data[CONF_ALARM_SOURCE] == "webhook"
    assert entry.data[CONF_NTFY_TOPIC] is None
    cloud_mocks["get_or_create"].assert_awaited_once_with(
        hass, entry.data[CONF_WEBHOOK_ID]
    )


@pytest.mark.usefixtures("external_url")
async def test_yes_without_subscription_but_with_external_url(
    hass: HomeAssistant,
) -> None:
    """The answer yes also finds an external URL when there is no subscription."""
    with patch_cloud(hass, subscription=False) as cloud_mocks:
        result = await _create_with_cloud_path(hass)

    assert result["description"] == "external"
    cloud_mocks["get_or_create"].assert_not_called()


async def test_unreachable_shows_the_cloud_guide_then_the_checklist(
    hass: HomeAssistant,
) -> None:
    """No dead end: a guide, then a checklist, and an external URL then works."""
    result = await _create_with_cloud_path(hass)

    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "cloud_setup"
    assert result["menu_options"] == ["cloud", "ntfy", "webhook_anyway"]
    _assert_placeholders(result)

    result = await _choose(hass, result["flow_id"], "cloud")
    assert result["step_id"] == "cloud_setup_retry"
    assert result["menu_options"] == ["cloud", "ntfy", "webhook_anyway"]
    _assert_placeholders(result)
    result = await _choose(hass, result["flow_id"], "cloud")
    assert result["step_id"] == "cloud_setup_retry"

    await async_process_ha_core_config(hass, {"external_url": EXTERNAL_URL})
    result = await _choose(hass, result["flow_id"], "cloud")

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["description"] == "external"


async def test_continue_anyway_with_an_internal_url(hass: HomeAssistant) -> None:
    """Continue anyway saves the entry with the internal address."""
    await async_process_ha_core_config(hass, {"internal_url": INTERNAL_URL})
    result = await _create_with_cloud_path(hass)
    assert result["step_id"] == "cloud_setup"

    result = await _choose(hass, result["flow_id"], "webhook_anyway")

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["description"] == "internal"
    assert result["description_placeholders"]["webhook_url"].startswith(INTERNAL_URL)
    _assert_placeholders(result)
    assert result["result"].data[CONF_ALARM_SOURCE] == "webhook"


async def test_continue_anyway_with_the_path_only(hass: HomeAssistant) -> None:
    """Without any URL the dialog gets the bare path.

    The flow itself starts the http integration, which makes an internal URL
    available, so the URL helper is stubbed here.
    """
    result = await _create_with_cloud_path(hass)
    with patch(
        "custom_components.ff_agent.config_flow.async_local_webhook_url",
        return_value=(PATH, UrlKind.PATH_ONLY),
    ):
        result = await _choose(hass, result["flow_id"], "webhook_anyway")

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["description"] == "path_only"
    assert result["description_placeholders"] == {**LINKS, "webhook_url": PATH}
    _assert_placeholders(result)


async def test_cloud_not_connected_then_recovery(hass: HomeAssistant) -> None:
    """A disconnected cloud shows its own menu and "try again" succeeds."""
    with patch_cloud(hass, connected=False) as cloud_mocks:
        result = await _create_with_cloud_path(hass)

    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "cloud_not_connected"
    assert result["menu_options"] == ["cloud", "ntfy"]
    _assert_placeholders(result)
    cloud_mocks["get_or_create"].assert_not_called()
    assert hass.config_entries.async_entries(DOMAIN) == []

    with patch_cloud(hass):
        result = await _choose(hass, result["flow_id"], "cloud")

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["description"] == "cloud"


async def test_cloud_not_connected_offers_ntfy(hass: HomeAssistant) -> None:
    """The way to ntfy is open from the menu of a disconnected cloud."""
    with patch_cloud(hass, connected=False):
        result = await _create_with_cloud_path(hass)
        result = await _choose(hass, result["flow_id"], "ntfy")

    assert result["step_id"] == "ntfy"


@pytest.mark.parametrize("error", [TimeoutError, ValueError])
async def test_known_cloudhook_errors_count_as_not_connected(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture, error: type[Exception]
) -> None:
    """A failing cloudhook leads to the menu; the message is not logged."""
    caplog.set_level(logging.DEBUG)
    with patch_cloud(hass) as cloud_mocks:
        cloud_mocks["get_or_create"].side_effect = error(REPLY_URL)
        result = await _create_with_cloud_path(hass)

    assert result["step_id"] == "cloud_not_connected"
    assert hass.config_entries.async_entries(DOMAIN) == []
    assert REPLY_URL not in caplog.text
    assert REPLY_ID not in caplog.text

    with patch_cloud(hass):
        result = await _choose(hass, result["flow_id"], "cloud")

    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_unexpected_error_aborts_and_logs_only_the_type(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    """An unexpected error ends the flow; only its type reaches the log."""
    caplog.set_level(logging.DEBUG)
    with patch_cloud(hass) as cloud_mocks:
        cloud_mocks["get_or_create"].side_effect = RuntimeError(REPLY_URL)
        result = await _create_with_cloud_path(hass)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "unknown"
    assert hass.config_entries.async_entries(DOMAIN) == []
    assert "RuntimeError" in caplog.text
    assert REPLY_URL not in caplog.text
    assert REPLY_ID not in caplog.text


async def test_cloud_error_leaks_no_secret(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    """A disconnected cloud neither logs nor shows the UUID or a webhook URL."""
    caplog.set_level(logging.DEBUG)
    with patch_cloud(hass, connected=False):
        result = await _create_with_cloud_path(hass)

    assert result["step_id"] == "cloud_not_connected"
    assert REPLY_ID not in caplog.text
    assert CLOUDHOOK_URL not in caplog.text
    assert REPLY_ID not in str(result["description_placeholders"])


async def test_created_entry_is_not_logged_on_cloud_path(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    """With a cloudhook neither the cloudhook URL nor the secrets reach the log."""
    caplog.set_level(logging.DEBUG)
    with patch_cloud(hass):
        result = await _create_with_cloud_path(hass)

    entry: ConfigEntry = result["result"]
    for secret in (
        REPLY_ID,
        CLOUDHOOK_URL,
        entry.data[CONF_WEBHOOK_ID],
        entry.data[CONF_HEADER_TOKEN],
    ):
        assert secret not in caplog.text


# --- "No" and the own address -----------------------


async def test_no_cloud_points_to_ntfy(hass: HomeAssistant) -> None:
    """The answer no leads to ntfy; cloud and own address stay open."""
    result = await _to_menu(hass)

    result = await _choose(hass, result["flow_id"], "no_cloud")

    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "no_cloud"
    assert result["menu_options"] == ["ntfy", "cloud", "own_address"]
    _assert_placeholders(result)


@pytest.mark.parametrize("option", ["cloud", "own_address"])
@pytest.mark.usefixtures("external_url")
async def test_no_cloud_then_cloud_or_own_address(
    hass: HomeAssistant, option: str
) -> None:
    """Both options run the cloud path, which detects the external URL."""
    result = await _to_menu(hass)
    result = await _choose(hass, result["flow_id"], "no_cloud")

    result = await _choose(hass, result["flow_id"], option)

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["description"] == "external"


async def test_own_address_without_an_address_shows_the_guide(
    hass: HomeAssistant,
) -> None:
    """Without an address the own-address option ends in the cloud guide."""
    result = await _to_menu(hass)
    result = await _choose(hass, result["flow_id"], "no_cloud")

    result = await _choose(hass, result["flow_id"], "own_address")

    assert result["step_id"] == "cloud_setup"


# --- The ntfy path -----------------------


async def test_ntfy_guide_shows_topic_and_url(hass: HomeAssistant) -> None:
    """The guide shows a new random topic and the URL for FF Agent (GET)."""
    result = await _to_ntfy_guide(hass)

    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "ntfy"
    assert result["menu_options"] == ["ntfy_find", "cloud"]
    placeholders = result["description_placeholders"]
    topic = placeholders["ntfy_topic"]
    assert TOPIC.match(topic)
    assert placeholders["ntfy_publish_url"] == f"https://ntfy.sh/{topic}/trigger"
    _assert_placeholders(result)


async def test_ntfy_guide_uses_the_server_of_the_only_ntfy_entry(
    hass: HomeAssistant,
) -> None:
    """With exactly one ntfy entry its server is used for the URL."""
    add_ntfy_entry(hass, {}, url=OWN_NTFY_SERVER)

    result = await _to_ntfy_guide(hass)

    topic = result["description_placeholders"]["ntfy_topic"]
    assert result["description_placeholders"]["ntfy_publish_url"] == (
        f"https://ntfy.example.com/{topic}/trigger"
    )


async def test_ntfy_guide_with_two_ntfy_entries_uses_ntfy_sh(
    hass: HomeAssistant,
) -> None:
    """With several ntfy entries the default server is shown."""
    add_ntfy_entry(hass, {}, url=OWN_NTFY_SERVER)
    add_ntfy_entry(hass, {}, url="https://ntfy.example.org/")

    result = await _to_ntfy_guide(hass)

    url = result["description_placeholders"]["ntfy_publish_url"]
    assert url.startswith("https://ntfy.sh/")


async def test_topic_stays_when_switching_paths(hass: HomeAssistant) -> None:
    """ntfy -> cloud -> guide -> ntfy keeps the topic of the flow."""
    result = await _to_ntfy_guide(hass)
    topic = result["description_placeholders"]["ntfy_topic"]

    result = await _choose(hass, result["flow_id"], "cloud")
    assert result["step_id"] == "cloud_setup"
    result = await _choose(hass, result["flow_id"], "ntfy")

    assert result["step_id"] == "ntfy"
    assert result["description_placeholders"]["ntfy_topic"] == topic


async def test_switching_both_ways_in_one_flow(hass: HomeAssistant) -> None:
    """no_cloud -> ntfy -> cloud -> cloud_setup -> ntfy -> find -> entry."""
    with patch_cloud(hass, subscription=False) as cloud_mocks:
        result = await _to_ntfy_guide(hass)
        result = await _choose(hass, result["flow_id"], "cloud")
        assert result["step_id"] == "cloud_setup"
        result = await _choose(hass, result["flow_id"], "ntfy")
        topic = result["description_placeholders"]["ntfy_topic"]
        registry_entry = _subscribe(hass, topic)

        result = await _choose(hass, result["flow_id"], "ntfy_find")

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].data[CONF_NTFY_ENTITY_UUID] == registry_entry.id
    cloud_mocks["get_or_create"].assert_not_called()


async def test_ntfy_find_creates_the_entry(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    """The subscription is found by the topic; no cloudhook is created."""
    caplog.set_level(logging.DEBUG)
    with patch_cloud(hass) as cloud_mocks:
        result = await _to_menu(hass)
        result = await _choose(hass, result["flow_id"], "no_cloud")
        result = await _choose(hass, result["flow_id"], "ntfy")
        topic = result["description_placeholders"]["ntfy_topic"]
        registry_entry = _subscribe(hass, topic)

        result = await _choose(hass, result["flow_id"], "ntfy_find")

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["description"] == "ntfy"
    publish_url = f"https://ntfy.sh/{topic}/trigger"
    assert result["description_placeholders"] == {
        **LINKS,
        "ntfy_publish_url": publish_url,
    }
    _assert_placeholders(result)
    entry: ConfigEntry = result["result"]
    assert entry.data == {
        CONF_REPLY_ID: REPLY_ID,
        CONF_REPLY_HOST: DEFAULT_REPLY_HOST,
        CONF_ALARM_SOURCE: "ntfy",
        CONF_WEBHOOK_ID: entry.data[CONF_WEBHOOK_ID],
        CONF_CLOUDHOOK: False,
        CONF_CLOUDHOOK_URL: None,
        CONF_HEADER_TOKEN: entry.data[CONF_HEADER_TOKEN],
        CONF_NTFY_ENTITY_UUID: registry_entry.id,
        CONF_NTFY_TOPIC: topic,
        CONF_NTFY_SERVER: "https://ntfy.sh/",
    }
    assert len(entry.data[CONF_HEADER_TOKEN]) >= 40
    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data.source is not None
    cloud_mocks["get_or_create"].assert_not_called()
    for secret in (topic, NTFY_ENTITY_ID, registry_entry.id, REPLY_ID):
        assert secret not in caplog.text


async def test_ntfy_find_without_the_ntfy_integration(hass: HomeAssistant) -> None:
    """Without ntfy the form asks to set it up first."""
    result = await _to_ntfy_guide(hass)

    result = await _choose(hass, result["flow_id"], "ntfy_find")

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "ntfy_select"
    assert result["errors"] == {"base": "ntfy_not_set_up"}
    _assert_placeholders(result)


async def test_ntfy_select_searches_again_with_an_empty_field(
    hass: HomeAssistant,
) -> None:
    """Not found yet: an empty submit searches again, with the same topic."""
    add_ntfy_entry(hass, {OTHER_NTFY_SUBENTRY_ID: OTHER_NTFY_TOPIC})
    result = await _to_ntfy_guide(hass)
    topic = result["description_placeholders"]["ntfy_topic"]

    result = await _choose(hass, result["flow_id"], "ntfy_find")
    assert result["errors"] == {"base": "ntfy_entity_not_found"}
    assert result["description_placeholders"]["ntfy_topic"] == topic

    result = await _configure(hass, result["flow_id"], {})
    assert result["step_id"] == "ntfy_select"
    assert result["errors"] == {"base": "ntfy_entity_not_found"}
    assert result["description_placeholders"]["ntfy_topic"] == topic

    registry_entry = _subscribe(hass, topic)
    result = await _configure(hass, result["flow_id"], {})

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].data[CONF_NTFY_ENTITY_UUID] == registry_entry.id
    assert result["result"].data[CONF_NTFY_TOPIC] == topic


async def test_ntfy_select_takes_an_existing_subscription(
    hass: HomeAssistant,
) -> None:
    """A chosen entity wins: its topic and server are stored and shown."""
    ntfy_entry = add_ntfy_entry(
        hass, {OTHER_NTFY_SUBENTRY_ID: OTHER_NTFY_TOPIC}, url=OWN_NTFY_SERVER
    )
    registry_entry = add_ntfy_entity(
        hass, ntfy_entry, OTHER_NTFY_SUBENTRY_ID, OTHER_NTFY_ENTITY_ID
    )
    result = await _to_ntfy_guide(hass)
    result = await _choose(hass, result["flow_id"], "ntfy_find")

    result = await _configure(
        hass, result["flow_id"], {CONF_NTFY_ENTITY: OTHER_NTFY_ENTITY_ID}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    data = result["result"].data
    assert data[CONF_NTFY_ENTITY_UUID] == registry_entry.id
    assert data[CONF_NTFY_TOPIC] == OTHER_NTFY_TOPIC
    assert data[CONF_NTFY_SERVER] == OWN_NTFY_SERVER
    assert result["description_placeholders"]["ntfy_publish_url"] == (
        f"https://ntfy.example.com/{OTHER_NTFY_TOPIC}/trigger"
    )


async def test_ntfy_select_refuses_foreign_entities(hass: HomeAssistant) -> None:
    """Only event entities of ntfy are accepted."""
    add_ntfy_entry(hass, {})
    er.async_get(hass).async_get_or_create(
        "event", "demo", "x", suggested_object_id="other"
    )
    result = await _to_ntfy_guide(hass)
    result = await _choose(hass, result["flow_id"], "ntfy_find")

    result = await _configure(
        hass, result["flow_id"], {CONF_NTFY_ENTITY: "event.other"}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_NTFY_ENTITY: "ntfy_entity_invalid"}
    _assert_placeholders(result)


async def test_ntfy_entity_in_use_by_another_person(
    hass: HomeAssistant, ntfy_entry: MockConfigEntry
) -> None:
    """One ntfy entity belongs to one entry; both ways refuse a second one."""
    ntfy_entry.add_to_hass(hass)
    result = await _start_flow(hass)
    result = await _submit(hass, result["flow_id"], OTHER_REPLY_URL)
    result = await _choose(hass, result["flow_id"], "no_cloud")
    result = await _choose(hass, result["flow_id"], "ntfy")

    result = await _choose(hass, result["flow_id"], "ntfy_find")
    # The flow has its own topic, so the search finds nothing; then the user picks
    # the entity of the other person.
    assert result["errors"] == {"base": "ntfy_entity_not_found"}
    result = await _configure(
        hass, result["flow_id"], {CONF_NTFY_ENTITY: NTFY_ENTITY_ID}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "ntfy_entity_in_use"}
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1


async def test_ntfy_entity_in_use_found_by_the_topic(hass: HomeAssistant) -> None:
    """The search does not take an entity another entry already uses."""
    result = await _to_ntfy_guide(hass)
    topic = result["description_placeholders"]["ntfy_topic"]
    registry_entry = _subscribe(hass, topic)
    other = MockConfigEntry(
        domain=DOMAIN,
        minor_version=2,
        unique_id=reply_unique_id(OTHER_REPLY_ID),
        data={
            CONF_ALARM_SOURCE: "ntfy",
            CONF_NTFY_ENTITY_UUID: registry_entry.id,
        },
    )
    other.add_to_hass(hass)

    result = await _choose(hass, result["flow_id"], "ntfy_find")

    assert result["step_id"] == "ntfy_select"
    assert result["errors"] == {"base": "ntfy_entity_in_use"}


async def test_ntfy_entity_of_a_webhook_entry_is_free(hass: HomeAssistant) -> None:
    """An entry that went back to the webhook does not hold its old ntfy entity."""
    result = await _to_ntfy_guide(hass)
    topic = result["description_placeholders"]["ntfy_topic"]
    registry_entry = _subscribe(hass, topic)
    MockConfigEntry(
        domain=DOMAIN,
        minor_version=2,
        unique_id=reply_unique_id(OTHER_REPLY_ID),
        data={
            CONF_ALARM_SOURCE: "webhook",
            CONF_NTFY_ENTITY_UUID: registry_entry.id,
        },
    ).add_to_hass(hass)

    result = await _choose(hass, result["flow_id"], "ntfy_find")

    assert result["type"] is FlowResultType.CREATE_ENTRY


# --- Persons, tokens and secrets -----------------------


@pytest.mark.usefixtures("external_url")
@pytest.mark.parametrize(
    "value",
    ["", "not a url", "https://example.com/app2/missionreplies/x/accept"],
)
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
    assert result["step_id"] == "alarm_source"
    result = await _choose(hass, result["flow_id"], "cloud")

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1


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
    """The same person cannot be added twice, before the alarm path is set up."""
    mock_config_entry.add_to_hass(hass)

    result = await _start_flow(hass)
    result = await _submit(hass, result["flow_id"], reply_url)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert hass.config_entries.async_entries(DOMAIN) == [mock_config_entry]


@pytest.mark.usefixtures("external_url")
async def test_user_flow_two_persons_give_two_entries(hass: HomeAssistant) -> None:
    """Different persons coexist, each with its own webhook and token."""
    first = await _create_with_cloud_path(hass, reply_url=REPLY_URL)
    second = await _create_with_cloud_path(hass, reply_url=OTHER_REPLY_URL)

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


@pytest.mark.usefixtures("external_url")
async def test_user_flow_header_token_and_options(hass: HomeAssistant) -> None:
    """Every entry gets a long random token and the token check starts disabled."""
    result = await _create_with_cloud_path(hass)

    entry: ConfigEntry = result["result"]
    assert len(entry.data[CONF_HEADER_TOKEN]) >= 40
    assert entry.options[CONF_REQUIRE_TOKEN] is False


async def test_user_flow_makes_no_request_to_ff_agent(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Setting up never calls FF Agent, a call would be a real mission reply."""
    result = await _create_with_cloud_path(hass)
    await _choose(hass, result["flow_id"], "webhook_anyway")

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


@pytest.mark.usefixtures("external_url")
@pytest.mark.parametrize("name", ["", "   ", "\t\n"])
async def test_blank_name_falls_back_to_the_default(
    hass: HomeAssistant, name: str
) -> None:
    """An empty or whitespace-only name gives the entry the default title."""
    result = await _create_with_cloud_path(hass, name=name)

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == NAME


@pytest.mark.usefixtures("external_url")
async def test_name_is_stripped(hass: HomeAssistant) -> None:
    """Surrounding whitespace is removed from the title."""
    result = await _create_with_cloud_path(hass, name="  Test Person  ")

    assert result["title"] == "Test Person"


async def test_reply_url_field_is_plain_text(hass: HomeAssistant) -> None:
    """The field also takes a bare UUID, so it must not be a URL input."""
    result = await _start_flow(hass)

    (marker,) = (key for key in result["data_schema"].schema if key == CONF_REPLY_URL)
    assert result["data_schema"].schema[marker].config["type"] == "text"


async def test_second_flow_for_same_person_is_already_in_progress(
    hass: HomeAssistant,
) -> None:
    """A flow that is still open blocks a second one for the same person."""
    first = await _to_menu(hass)
    assert first["type"] is FlowResultType.MENU

    second = await _start_flow(hass)
    second = await _submit(hass, second["flow_id"])

    assert second["type"] is FlowResultType.ABORT
    assert second["reason"] == "already_in_progress"


def test_every_step_text_has_its_placeholders_in_the_flow() -> None:
    """Steps whose texts use links are covered by the tests above; this checks
    that no text asks for a placeholder the flow never delivers."""
    delivered = {
        *LINKS,
        "webhook_url",
        "token_header",
        "token",
        "ntfy_topic",
        "ntfy_publish_url",
    }
    for language in ("en", "de"):
        texts = json.loads((TRANSLATIONS / f"{language}.json").read_text("utf-8"))
        config = json.dumps(texts["config"])
        assert set(re.findall(r"\{(\w+)\}", config)) <= delivered
