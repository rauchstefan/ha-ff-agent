"""Tests for the options flow of the FF Agent integration."""

from __future__ import annotations

import asyncio
import json
import logging
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest
import voluptuous as vol
from homeassistant.components import webhook
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult, FlowResultType, InvalidData
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.util.aiohttp import MockRequest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ff_agent import webhook as webhook_module
from custom_components.ff_agent.const import (
    CONF_DEFAULT_TRANSPORT,
    CONF_LOCATION_ENTITY,
    CONF_LOCATION_LATITUDE,
    CONF_LOCATION_LONGITUDE,
    CONF_LOCATION_SOURCE,
    CONF_NTFY_ENTITY_UUID,
    CONF_NTFY_TOPIC,
    CONF_REQUIRE_TOKEN,
    CONF_RESET_MINUTES,
    DOMAIN,
    ISSUE_TOKEN_REJECTED,
    MY_CLOUD_URL,
    TOKEN_HEADER,
)
from custom_components.ff_agent.models import ReplyAction
from custom_components.ff_agent.reply import async_send_reply
from custom_components.ff_agent.webhook_url import UrlKind

from .common import async_setup_entry, patch_cloud
from .const import (
    ACCEPT_URL,
    CLOUDHOOK_URL,
    EXTERNAL_URL,
    HEADER_TOKEN,
    INTERNAL_URL,
    LATITUDE,
    LOCATION_ENTITY,
    LONGITUDE,
    MANUAL_LATITUDE,
    MANUAL_LONGITUDE,
    NTFY_ENTITY_ID,
    NTFY_PUBLISH_URL,
    REPLY_ID,
    WEBHOOK_ID,
)

if TYPE_CHECKING:
    from pytest_homeassistant_custom_component.test_util.aiohttp import (
        AiohttpClientMocker,
    )

TRANSLATIONS = Path(__file__).parents[1] / "custom_components/ff_agent/translations"
PATH = f"/api/webhook/{WEBHOOK_ID}"
POSITION = {"latitude": LATITUDE, "longitude": LONGITUDE}


async def _open(hass: HomeAssistant, entry: MockConfigEntry) -> FlowResult:
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"
    return result


async def _save(
    hass: HomeAssistant, flow_id: str, values: dict[str, Any] | None = None
) -> FlowResult:
    result = await hass.config_entries.options.async_configure(flow_id, values or {})
    await hass.async_block_till_done()
    return result


async def _call_webhook(hass: HomeAssistant, webhook_id: str = WEBHOOK_ID) -> int:
    """Call the webhook like a Nabu Casa cloudhook does; return the status."""
    request = MockRequest(b"", "test", method="POST")
    response = await webhook.async_handle_webhook(hass, webhook_id, request)
    await hass.async_block_till_done()
    return response.status


def _suggested(result: FlowResult) -> dict[str, Any]:
    """Return the suggested values of a form; fields without one are missing."""
    return {
        str(key): key.description["suggested_value"]
        for key in result["data_schema"].schema
        if key.description
    }


def _alarm_state(hass: HomeAssistant, entry: MockConfigEntry) -> str:
    entity_id = er.async_get(hass).async_get_entity_id(
        "binary_sensor", DOMAIN, f"{entry.entry_id}_alarm"
    )
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    return state.state


def _issue(hass: HomeAssistant, entry: MockConfigEntry) -> ir.IssueEntry | None:
    issue_id = ISSUE_TOKEN_REJECTED.format(entry_id=entry.entry_id)
    return ir.async_get(hass).async_get_issue(DOMAIN, issue_id)


# --- The form shows the webhook access -----------------------


@pytest.mark.usefixtures("external_url")
async def test_form_shows_the_external_webhook_url_header_and_token(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """The URL, the header name and the token can be read at any time."""
    await async_setup_entry(hass, mock_config_entry)

    result = await _open(hass, mock_config_entry)

    assert result["description_placeholders"] == {
        "webhook_url": f"{EXTERNAL_URL}/api/webhook/{WEBHOOK_ID}",
        "url_kind": "external",
        "token_header": TOKEN_HEADER,
        "token": HEADER_TOKEN,
        "cloud_url": MY_CLOUD_URL,
    }


async def test_form_shows_the_stored_cloudhook_url(
    hass: HomeAssistant, cloudhook_entry: MockConfigEntry
) -> None:
    """With a cloudhook the stored cloudhook URL is shown, not a local one."""
    await async_setup_entry(hass, cloudhook_entry)

    result = await _open(hass, cloudhook_entry)

    placeholders = result["description_placeholders"]
    assert placeholders["webhook_url"] == CLOUDHOOK_URL
    assert placeholders["url_kind"] == "cloud"


async def test_form_shows_an_internal_url_as_such(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Without an external URL the form says that the address is internal."""
    await async_setup_entry(hass, mock_config_entry)
    with patch(
        "custom_components.ff_agent.config_flow.async_get_webhook_url",
        return_value=(f"{INTERNAL_URL}{PATH}", UrlKind.INTERNAL),
    ):
        result = await _open(hass, mock_config_entry)

    placeholders = result["description_placeholders"]
    assert placeholders["url_kind"] == "internal"
    assert placeholders["webhook_url"] == f"{INTERNAL_URL}{PATH}"


async def test_form_does_not_log_the_secrets(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Showing and saving the form puts neither URL nor token into the log."""
    caplog.set_level(logging.DEBUG)
    await async_setup_entry(hass, mock_config_entry)

    result = await _open(hass, mock_config_entry)
    await _save(hass, result["flow_id"], {CONF_RESET_MINUTES: 7})

    for secret in (HEADER_TOKEN, WEBHOOK_ID, REPLY_ID):
        assert secret not in caplog.text


# --- Defaults and the schema -----------------------


async def test_the_schema_keys_are_translated(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Every field has a label and a description in both languages."""
    await async_setup_entry(hass, mock_config_entry)
    result = await _open(hass, mock_config_entry)

    keys = {str(key) for key in result["data_schema"].schema}

    assert keys == {
        CONF_REQUIRE_TOKEN,
        CONF_RESET_MINUTES,
        CONF_DEFAULT_TRANSPORT,
        CONF_LOCATION_SOURCE,
    }
    for language in ("en", "de"):
        texts = json.loads((TRANSLATIONS / f"{language}.json").read_text("utf-8"))
        step = texts["options"]["step"]["init"]
        assert set(step["data"]) == keys
        assert set(step["data_description"]) == keys


async def test_saving_the_defaults_keeps_the_current_options(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """The fields start with the current values; no location is invented."""
    await async_setup_entry(hass, mock_config_entry)
    alarm = mock_config_entry.runtime_data.alarm
    result = await _open(hass, mock_config_entry)

    saved = await _save(hass, result["flow_id"])

    assert saved["type"] is FlowResultType.CREATE_ENTRY
    assert saved["data"] == {
        CONF_REQUIRE_TOKEN: False,
        CONF_RESET_MINUTES: 30,
        CONF_DEFAULT_TRANSPORT: "car",
        CONF_LOCATION_SOURCE: "none",
    }
    # Nothing changed, so there is no reload and a running alarm stays.
    assert mock_config_entry.runtime_data.alarm is alarm


@pytest.mark.parametrize(
    ("stored", "expected"),
    [("car", "CAR"), ("feet", "FEET"), ("bicycle", "BICYCLE")],
)
async def test_each_transport_can_be_chosen_in_the_form(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
    stored: str,
    expected: str,
) -> None:
    """The form offers all three transports; the next acceptance sends the choice."""
    aioclient_mock.get(ACCEPT_URL)
    await async_setup_entry(hass, mock_config_entry)
    result = await _open(hass, mock_config_entry)
    transport_key = next(
        key for key in result["data_schema"].schema if key == CONF_DEFAULT_TRANSPORT
    )
    assert result["data_schema"].schema[transport_key].config["options"] == [
        "car",
        "feet",
        "bicycle",
    ]

    saved = await _save(hass, result["flow_id"], {CONF_DEFAULT_TRANSPORT: stored})

    assert saved["data"][CONF_DEFAULT_TRANSPORT] == stored
    assert mock_config_entry.options[CONF_DEFAULT_TRANSPORT] == stored
    await async_send_reply(hass, mock_config_entry, ReplyAction.ACCEPT)
    url = aioclient_mock.mock_calls[0][1]
    assert dict(url.query) == {"transport": expected}


@pytest.mark.parametrize(
    ("legacy", "key"), [("CAR", "car"), ("FEET", "feet"), ("BICYCLE", "bicycle")]
)
async def test_a_legacy_transport_is_offered_in_lower_case(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, legacy: str, key: str
) -> None:
    """An option stored as the API value is shown and saved as the lower case key."""
    await async_setup_entry(hass, mock_config_entry)
    hass.config_entries.async_update_entry(
        mock_config_entry,
        options={**mock_config_entry.options, CONF_DEFAULT_TRANSPORT: legacy},
    )
    await hass.async_block_till_done()
    result = await _open(hass, mock_config_entry)

    saved = await _save(hass, result["flow_id"])

    assert saved["data"][CONF_DEFAULT_TRANSPORT] == key
    assert mock_config_entry.options[CONF_DEFAULT_TRANSPORT] == key


@pytest.mark.parametrize(
    "values",
    [
        {CONF_RESET_MINUTES: 0},
        {CONF_RESET_MINUTES: 1441},
        {CONF_RESET_MINUTES: -5},
        {CONF_RESET_MINUTES: "soon"},
        {CONF_DEFAULT_TRANSPORT: "CAR"},
        {CONF_DEFAULT_TRANSPORT: "FEET"},
        {CONF_DEFAULT_TRANSPORT: "BICYCLE"},
        {CONF_DEFAULT_TRANSPORT: "bike"},
        {CONF_DEFAULT_TRANSPORT: "walk"},
        {CONF_LOCATION_SOURCE: "satellite"},
        {CONF_LOCATION_SOURCE: ""},
        # The values of a source are asked in a step of their own.
        {CONF_LOCATION_ENTITY: LOCATION_ENTITY},
        {CONF_LOCATION_LATITUDE: MANUAL_LATITUDE},
    ],
)
async def test_invalid_values_are_refused(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, values: dict[str, Any]
) -> None:
    """Out-of-range numbers, unknown transports and unknown sources are refused."""
    await async_setup_entry(hass, mock_config_entry)
    result = await _open(hass, mock_config_entry)
    options = dict(mock_config_entry.options)

    with pytest.raises(InvalidData):
        await _save(hass, result["flow_id"], values)

    assert dict(mock_config_entry.options) == options


@pytest.mark.parametrize("minutes", [1, 1440])
async def test_the_limits_of_the_reset_time_are_accepted(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, minutes: int
) -> None:
    """The reset time is stored as an integer, also at both limits."""
    await async_setup_entry(hass, mock_config_entry)
    result = await _open(hass, mock_config_entry)

    await _save(hass, result["flow_id"], {CONF_RESET_MINUTES: float(minutes)})

    stored = mock_config_entry.options[CONF_RESET_MINUTES]
    assert stored == minutes
    assert isinstance(stored, int)


@pytest.mark.parametrize("entity_id", ["person.test_person", "device_tracker.phone"])
async def test_person_and_device_tracker_are_accepted(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, entity_id: str
) -> None:
    """The location comes from a person or a device tracker."""
    await async_setup_entry(hass, mock_config_entry)
    result = await _open(hass, mock_config_entry)
    result = await _save(hass, result["flow_id"], {CONF_LOCATION_SOURCE: "entity"})

    await _save(hass, result["flow_id"], {CONF_LOCATION_ENTITY: entity_id})

    assert mock_config_entry.options[CONF_LOCATION_SOURCE] == "entity"
    assert mock_config_entry.options[CONF_LOCATION_ENTITY] == entity_id


# --- Saving reloads the entry -----------------------


async def test_saving_changes_the_options_and_reloads_with_the_new_reset_time(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """The reload creates a new alarm manager that uses the new reset time."""
    await async_setup_entry(hass, mock_config_entry)
    old_alarm = mock_config_entry.runtime_data.alarm
    assert old_alarm.reset_minutes == 30
    result = await _open(hass, mock_config_entry)

    result = await _save(
        hass,
        result["flow_id"],
        {
            CONF_REQUIRE_TOKEN: True,
            CONF_RESET_MINUTES: 5,
            CONF_DEFAULT_TRANSPORT: "car",
            CONF_LOCATION_SOURCE: "entity",
        },
    )
    # Nothing is saved before the last step.
    assert result["type"] is FlowResultType.FORM
    assert mock_config_entry.runtime_data.alarm is old_alarm
    saved = await _save(
        hass, result["flow_id"], {CONF_LOCATION_ENTITY: LOCATION_ENTITY}
    )

    assert saved["type"] is FlowResultType.CREATE_ENTRY
    assert dict(mock_config_entry.options) == {
        CONF_REQUIRE_TOKEN: True,
        CONF_RESET_MINUTES: 5,
        CONF_DEFAULT_TRANSPORT: "car",
        CONF_LOCATION_SOURCE: "entity",
        CONF_LOCATION_ENTITY: LOCATION_ENTITY,
    }
    new_alarm = mock_config_entry.runtime_data.alarm
    assert new_alarm is not old_alarm
    assert new_alarm.reset_minutes == 5


async def test_saving_resets_an_active_alarm(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """The alarm state is volatile: a reload ends a running alarm (by decision)."""
    await async_setup_entry(hass, mock_config_entry)
    assert await _call_webhook(hass) == HTTPStatus.OK
    assert _alarm_state(hass, mock_config_entry) == "on"
    result = await _open(hass, mock_config_entry)

    await _save(hass, result["flow_id"], {CONF_RESET_MINUTES: 10})

    assert _alarm_state(hass, mock_config_entry) == "off"
    # The deduplication window is open again, so the next call is a new alarm.
    assert await _call_webhook(hass) == HTTPStatus.OK
    alarm = mock_config_entry.runtime_data.alarm
    assert (alarm.alarms_total, alarm.deduplicated_total) == (1, 0)
    assert _alarm_state(hass, mock_config_entry) == "on"


# --- The location -----------------------

HOME_QUERY = {"transport": "CAR", "lat": "1.234500", "lng": "6.789000"}
MANUAL_QUERY = {"transport": "CAR", "lat": "12.345600", "lng": "-65.432100"}
NO_LOCATION = {"transport": "CAR"}


def _query(aioclient_mock: AiohttpClientMocker) -> dict[str, str]:
    """Return the query of the only request."""
    assert aioclient_mock.call_count == 1
    method, url, _data, _headers = aioclient_mock.mock_calls[0]
    assert method == "GET"
    return dict(url.query)


async def test_the_source_field_is_a_dropdown_in_the_agreed_order(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """None first, then home, manual, and the entity as the last option."""
    await async_setup_entry(hass, mock_config_entry)
    result = await _open(hass, mock_config_entry)

    schema = result["data_schema"].schema
    key = next(key for key in schema if key == CONF_LOCATION_SOURCE)

    assert isinstance(key, vol.Required)
    assert schema[key].config["options"] == ["none", "home", "manual", "entity"]
    assert schema[key].config["mode"] == "dropdown"
    assert schema[key].config["translation_key"] == "location_source"


@pytest.mark.parametrize(
    ("fixture", "expected"),
    [
        ("mock_config_entry", "none"),
        ("home_location_entry", "home"),
        ("manual_location_entry", "manual"),
        ("location_entry", "entity"),
        # Created before the source existed: it follows from the location entity.
        ("legacy_location_entry", "entity"),
    ],
)
async def test_the_source_field_starts_with_the_source_of_the_entry(
    hass: HomeAssistant,
    request: pytest.FixtureRequest,
    fixture: str,
    expected: str,
) -> None:
    """The dropdown shows what the entry uses now."""
    entry: MockConfigEntry = request.getfixturevalue(fixture)
    await async_setup_entry(hass, entry)

    result = await _open(hass, entry)

    schema = result["data_schema"].schema
    key = next(key for key in schema if key == CONF_LOCATION_SOURCE)
    assert key.default() == expected


async def test_an_old_entry_without_a_location_gets_the_source_none(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Options without source and without entity mean no location."""
    await async_setup_entry(hass, mock_config_entry)
    options = dict(mock_config_entry.options)
    del options[CONF_LOCATION_SOURCE]
    hass.config_entries.async_update_entry(mock_config_entry, options=options)
    result = await _open(hass, mock_config_entry)

    saved = await _save(hass, result["flow_id"])

    assert saved["data"][CONF_LOCATION_SOURCE] == "none"
    assert mock_config_entry.options[CONF_LOCATION_SOURCE] == "none"


async def test_an_old_entry_with_an_entity_is_saved_with_the_source_entity(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    legacy_location_entry: MockConfigEntry,
) -> None:
    """Saving writes the derived source; the entity is asked again and kept."""
    aioclient_mock.get(ACCEPT_URL)
    hass.states.async_set(LOCATION_ENTITY, "home", POSITION)
    await async_setup_entry(hass, legacy_location_entry)
    result = await _open(hass, legacy_location_entry)

    result = await _save(hass, result["flow_id"])

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "location_entity"
    assert _suggested(result) == {CONF_LOCATION_ENTITY: LOCATION_ENTITY}
    await _save(hass, result["flow_id"], {CONF_LOCATION_ENTITY: LOCATION_ENTITY})

    assert legacy_location_entry.options[CONF_LOCATION_SOURCE] == "entity"
    assert legacy_location_entry.options[CONF_LOCATION_ENTITY] == LOCATION_ENTITY
    await async_send_reply(hass, legacy_location_entry, ReplyAction.ACCEPT)
    assert _query(aioclient_mock) == HOME_QUERY


async def test_switching_to_none_removes_every_location_value(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    manual_location_entry: MockConfigEntry,
) -> None:
    """No old coordinates stay behind; the next acceptance sends no location."""
    aioclient_mock.get(ACCEPT_URL)
    await async_setup_entry(hass, manual_location_entry)
    result = await _open(hass, manual_location_entry)

    saved = await _save(hass, result["flow_id"], {CONF_LOCATION_SOURCE: "none"})

    assert saved["type"] is FlowResultType.CREATE_ENTRY
    assert dict(manual_location_entry.options) == {
        CONF_REQUIRE_TOKEN: False,
        CONF_RESET_MINUTES: 30,
        CONF_DEFAULT_TRANSPORT: "car",
        CONF_LOCATION_SOURCE: "none",
    }
    await async_send_reply(hass, manual_location_entry, ReplyAction.ACCEPT)
    assert _query(aioclient_mock) == NO_LOCATION


async def test_switching_from_an_entity_to_none_removes_the_entity(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    location_entry: MockConfigEntry,
) -> None:
    """The entity is gone from the options, so it cannot come back by itself."""
    aioclient_mock.get(ACCEPT_URL)
    hass.states.async_set(LOCATION_ENTITY, "home", POSITION)
    await async_setup_entry(hass, location_entry)
    result = await _open(hass, location_entry)

    await _save(hass, result["flow_id"], {CONF_LOCATION_SOURCE: "none"})

    assert CONF_LOCATION_ENTITY not in location_entry.options
    assert location_entry.options[CONF_LOCATION_SOURCE] == "none"
    await async_send_reply(hass, location_entry, ReplyAction.ACCEPT)
    assert _query(aioclient_mock) == NO_LOCATION


async def test_changing_the_source_keeps_the_other_options(
    hass: HomeAssistant, token_entry: MockConfigEntry
) -> None:
    """Token switch, reset time and transport survive a change of the source."""
    await async_setup_entry(hass, token_entry)
    result = await _open(hass, token_entry)

    await _save(
        hass,
        result["flow_id"],
        {
            CONF_RESET_MINUTES: 5,
            CONF_DEFAULT_TRANSPORT: "feet",
            CONF_LOCATION_SOURCE: "home",
        },
    )

    assert dict(token_entry.options) == {
        CONF_REQUIRE_TOKEN: True,
        CONF_RESET_MINUTES: 5,
        CONF_DEFAULT_TRANSPORT: "feet",
        CONF_LOCATION_SOURCE: "home",
    }


async def test_the_home_source_is_saved_at_once_without_stored_values(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    manual_location_entry: MockConfigEntry,
) -> None:
    """The home position is read when sending; the old coordinates are dropped."""
    aioclient_mock.get(ACCEPT_URL)
    hass.config.latitude = LATITUDE
    hass.config.longitude = LONGITUDE
    await async_setup_entry(hass, manual_location_entry)
    result = await _open(hass, manual_location_entry)

    saved = await _save(hass, result["flow_id"], {CONF_LOCATION_SOURCE: "home"})

    assert saved["type"] is FlowResultType.CREATE_ENTRY
    assert CONF_LOCATION_LATITUDE not in manual_location_entry.options
    assert CONF_LOCATION_LONGITUDE not in manual_location_entry.options
    await async_send_reply(hass, manual_location_entry, ReplyAction.ACCEPT)
    assert _query(aioclient_mock) == HOME_QUERY


async def test_the_manual_source_asks_for_coordinates_and_saves_them(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    location_entry: MockConfigEntry,
) -> None:
    """A second form follows; the home position is suggested; the entity is dropped."""
    aioclient_mock.get(ACCEPT_URL)
    hass.config.latitude = LATITUDE
    hass.config.longitude = LONGITUDE
    await async_setup_entry(hass, location_entry)
    before = dict(location_entry.options)
    result = await _open(hass, location_entry)

    result = await _save(hass, result["flow_id"], {CONF_LOCATION_SOURCE: "manual"})

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "location_manual"
    assert _suggested(result) == {
        CONF_LOCATION_LATITUDE: LATITUDE,
        CONF_LOCATION_LONGITUDE: LONGITUDE,
    }
    # Nothing is saved before the last step.
    assert dict(location_entry.options) == before

    saved = await _save(
        hass,
        result["flow_id"],
        {
            CONF_LOCATION_LATITUDE: MANUAL_LATITUDE,
            CONF_LOCATION_LONGITUDE: MANUAL_LONGITUDE,
        },
    )

    assert saved["type"] is FlowResultType.CREATE_ENTRY
    assert dict(location_entry.options) == {
        CONF_REQUIRE_TOKEN: False,
        CONF_RESET_MINUTES: 30,
        CONF_DEFAULT_TRANSPORT: "car",
        CONF_LOCATION_SOURCE: "manual",
        CONF_LOCATION_LATITUDE: MANUAL_LATITUDE,
        CONF_LOCATION_LONGITUDE: MANUAL_LONGITUDE,
    }
    await async_send_reply(hass, location_entry, ReplyAction.ACCEPT)
    assert _query(aioclient_mock) == MANUAL_QUERY


async def test_the_manual_form_starts_with_the_stored_coordinates(
    hass: HomeAssistant, manual_location_entry: MockConfigEntry
) -> None:
    """The stored values win over the home position."""
    hass.config.latitude = LATITUDE
    hass.config.longitude = LONGITUDE
    await async_setup_entry(hass, manual_location_entry)
    result = await _open(hass, manual_location_entry)

    result = await _save(hass, result["flow_id"])

    assert result["step_id"] == "location_manual"
    assert _suggested(result) == {
        CONF_LOCATION_LATITUDE: MANUAL_LATITUDE,
        CONF_LOCATION_LONGITUDE: MANUAL_LONGITUDE,
    }


async def test_the_manual_form_without_any_position_suggests_nothing(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Neither stored coordinates nor a home position: empty fields."""
    hass.config.latitude = 0
    hass.config.longitude = 0
    await async_setup_entry(hass, mock_config_entry)
    result = await _open(hass, mock_config_entry)

    result = await _save(hass, result["flow_id"], {CONF_LOCATION_SOURCE: "manual"})

    assert result["step_id"] == "location_manual"
    assert _suggested(result) == {}


@pytest.mark.parametrize(
    ("latitude", "longitude", "errors"),
    [
        (91, 6.789, {CONF_LOCATION_LATITUDE: "invalid_latitude"}),
        (float("nan"), 6.789, {CONF_LOCATION_LATITUDE: "invalid_latitude"}),
        (1.2345, -180.5, {CONF_LOCATION_LONGITUDE: "invalid_longitude"}),
        (1.2345, float("inf"), {CONF_LOCATION_LONGITUDE: "invalid_longitude"}),
        (
            -95,
            181,
            {
                CONF_LOCATION_LATITUDE: "invalid_latitude",
                CONF_LOCATION_LONGITUDE: "invalid_longitude",
            },
        ),
    ],
)
async def test_invalid_coordinates_are_an_error_in_the_form(
    hass: HomeAssistant,
    manual_location_entry: MockConfigEntry,
    latitude: float,
    longitude: float,
    errors: dict[str, str],
) -> None:
    """The form shows the error and nothing is saved."""
    await async_setup_entry(hass, manual_location_entry)
    before = dict(manual_location_entry.options)
    result = await _open(hass, manual_location_entry)
    result = await _save(hass, result["flow_id"])

    result = await _save(
        hass,
        result["flow_id"],
        {CONF_LOCATION_LATITUDE: latitude, CONF_LOCATION_LONGITUDE: longitude},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "location_manual"
    assert result["errors"] == errors
    assert dict(manual_location_entry.options) == before

    # A correction saves.
    result = await _save(
        hass,
        result["flow_id"],
        {CONF_LOCATION_LATITUDE: 10.5, CONF_LOCATION_LONGITUDE: -20.25},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert manual_location_entry.options[CONF_LOCATION_LATITUDE] == 10.5
    assert manual_location_entry.options[CONF_LOCATION_LONGITUDE] == -20.25


async def test_the_entity_source_asks_for_the_entity(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    manual_location_entry: MockConfigEntry,
) -> None:
    """The entity is required in its own form; the old coordinates are dropped."""
    aioclient_mock.get(ACCEPT_URL)
    hass.states.async_set(LOCATION_ENTITY, "home", POSITION)
    await async_setup_entry(hass, manual_location_entry)
    result = await _open(hass, manual_location_entry)

    result = await _save(hass, result["flow_id"], {CONF_LOCATION_SOURCE: "entity"})

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "location_entity"
    schema = result["data_schema"].schema
    assert set(schema) == {CONF_LOCATION_ENTITY}
    assert all(isinstance(key, vol.Required) for key in schema)
    assert _suggested(result) == {}
    for values in ({}, {CONF_LOCATION_ENTITY: "light.kitchen"}):
        with pytest.raises(InvalidData):
            await _save(hass, result["flow_id"], values)

    saved = await _save(
        hass, result["flow_id"], {CONF_LOCATION_ENTITY: LOCATION_ENTITY}
    )

    assert saved["type"] is FlowResultType.CREATE_ENTRY
    assert dict(manual_location_entry.options) == {
        CONF_REQUIRE_TOKEN: False,
        CONF_RESET_MINUTES: 30,
        CONF_DEFAULT_TRANSPORT: "car",
        CONF_LOCATION_SOURCE: "entity",
        CONF_LOCATION_ENTITY: LOCATION_ENTITY,
    }
    await async_send_reply(hass, manual_location_entry, ReplyAction.ACCEPT)
    assert _query(aioclient_mock) == HOME_QUERY


async def test_the_entity_form_starts_with_the_stored_entity(
    hass: HomeAssistant, location_entry: MockConfigEntry
) -> None:
    """The current entity is suggested and can be replaced."""
    await async_setup_entry(hass, location_entry)
    result = await _open(hass, location_entry)

    result = await _save(hass, result["flow_id"])

    assert result["step_id"] == "location_entity"
    assert _suggested(result) == {CONF_LOCATION_ENTITY: LOCATION_ENTITY}
    await _save(hass, result["flow_id"], {CONF_LOCATION_ENTITY: "device_tracker.phone"})
    assert location_entry.options[CONF_LOCATION_ENTITY] == "device_tracker.phone"


# --- The additional token -----------------------


async def test_requiring_the_token_makes_the_webhook_reject_calls_without_it(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """After saving, a call without the header gets 401 and one with it passes."""
    await async_setup_entry(hass, mock_config_entry)
    assert await _call_webhook(hass) == HTTPStatus.OK
    result = await _open(hass, mock_config_entry)

    await _save(hass, result["flow_id"], {CONF_REQUIRE_TOKEN: True})

    alarm = mock_config_entry.runtime_data.alarm
    rejected = MockRequest(b"", "test", method="POST")
    response = await webhook.async_handle_webhook(hass, WEBHOOK_ID, rejected)
    assert response.status == HTTPStatus.UNAUTHORIZED
    assert (alarm.calls_total, alarm.rejected_total) == (0, 1)

    accepted = MockRequest(
        b"", "test", method="POST", headers={TOKEN_HEADER: HEADER_TOKEN}
    )
    response = await webhook.async_handle_webhook(hass, WEBHOOK_ID, accepted)
    assert response.status == HTTPStatus.OK
    assert alarm.calls_total == 1


async def test_switching_the_token_requirement_off_removes_the_repair_issue(
    hass: HomeAssistant, token_entry: MockConfigEntry
) -> None:
    """The hint about a rejected call disappears with the requirement."""
    await async_setup_entry(hass, token_entry)
    request = MockRequest(b"", "test", method="POST")
    response = await webhook.async_handle_webhook(hass, WEBHOOK_ID, request)
    assert response.status == HTTPStatus.UNAUTHORIZED
    assert _issue(hass, token_entry) is not None
    result = await _open(hass, token_entry)

    await _save(hass, result["flow_id"], {CONF_REQUIRE_TOKEN: False})

    assert _issue(hass, token_entry) is None
    assert await _call_webhook(hass) == HTTPStatus.OK


async def test_options_of_two_persons_are_independent(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    other_entry: MockConfigEntry,
) -> None:
    """Saving the options of one entry leaves the other one untouched."""
    await async_setup_entry(hass, mock_config_entry)
    await async_setup_entry(hass, other_entry)
    other_alarm = other_entry.runtime_data.alarm
    result = await _open(hass, mock_config_entry)

    await _save(hass, result["flow_id"], {CONF_RESET_MINUTES: 3})

    assert mock_config_entry.options[CONF_RESET_MINUTES] == 3
    assert other_entry.options[CONF_RESET_MINUTES] == 30
    assert other_entry.runtime_data.alarm is other_alarm


async def test_the_form_works_with_the_cloud_loaded(
    hass: HomeAssistant, cloudhook_entry: MockConfigEntry
) -> None:
    """Opening and saving makes no cloud call; the cloudhook stays as it is."""
    with patch_cloud(hass) as cloud_mocks:
        await async_setup_entry(hass, cloudhook_entry)
        result = await _open(hass, cloudhook_entry)
        await _save(hass, result["flow_id"], {CONF_RESET_MINUTES: 12})

    cloud_mocks["get_or_create"].assert_not_called()
    cloud_mocks["delete"].assert_not_called()


# --- QA additions -----------------------


async def test_saving_during_a_running_webhook_call_hands_it_to_the_new_manager(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """A call that waits while the options are saved ends up in the reloaded entry."""
    await async_setup_entry(hass, mock_config_entry)
    old_alarm = mock_config_entry.runtime_data.alarm
    gate = asyncio.Event()
    real_capture = webhook_module.async_capture_call

    async def slow_capture(request: Any) -> Any:
        await gate.wait()
        return await real_capture(request)

    with patch.object(webhook_module, "async_capture_call", slow_capture):
        request = MockRequest(b"", "test", method="POST")
        call = asyncio.create_task(
            webhook.async_handle_webhook(hass, WEBHOOK_ID, request)
        )
        await asyncio.sleep(0)
        result = await _open(hass, mock_config_entry)
        await _save(hass, result["flow_id"], {CONF_RESET_MINUTES: 7})
        new_alarm = mock_config_entry.runtime_data.alarm
        assert new_alarm is not old_alarm

        gate.set()
        response = await call

    await hass.async_block_till_done()
    assert response.status == HTTPStatus.OK
    assert mock_config_entry.options[CONF_RESET_MINUTES] == 7
    assert old_alarm.calls_total == 0
    assert new_alarm.calls_total == 1


async def test_token_requirement_on_then_off_rejects_then_clears_the_issue(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """On: a call without the header gives 401 and the issue. Off: gone after reload."""
    await async_setup_entry(hass, mock_config_entry)
    result = await _open(hass, mock_config_entry)
    await _save(hass, result["flow_id"], {CONF_REQUIRE_TOKEN: True})

    assert await _call_webhook(hass) == HTTPStatus.UNAUTHORIZED
    assert _issue(hass, mock_config_entry) is not None

    result = await _open(hass, mock_config_entry)
    await _save(hass, result["flow_id"], {CONF_REQUIRE_TOKEN: False})

    assert mock_config_entry.options[CONF_REQUIRE_TOKEN] is False
    assert _issue(hass, mock_config_entry) is None
    assert await _call_webhook(hass) == HTTPStatus.OK
    assert _issue(hass, mock_config_entry) is None


async def test_options_flow_of_an_entry_that_is_not_loaded(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """The form and saving work without a running entry (no runtime data)."""
    mock_config_entry.add_to_hass(hass)
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED

    result = await _open(hass, mock_config_entry)
    assert result["description_placeholders"]["token"] == HEADER_TOKEN
    result = await _save(hass, result["flow_id"], {CONF_RESET_MINUTES: 9})

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert mock_config_entry.options[CONF_RESET_MINUTES] == 9


# --- ntfy mode -----------------------


async def _open_ntfy(hass: HomeAssistant, entry: MockConfigEntry) -> FlowResult:
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "ntfy"
    return result


async def test_ntfy_form_has_no_token_switch(
    hass: HomeAssistant, ntfy_entry: MockConfigEntry
) -> None:
    """There is no additional token with ntfy; the form shows entity and URL."""
    await async_setup_entry(hass, ntfy_entry)

    result = await _open_ntfy(hass, ntfy_entry)

    keys = {str(key) for key in result["data_schema"].schema}
    assert keys == {CONF_RESET_MINUTES, CONF_DEFAULT_TRANSPORT, CONF_LOCATION_SOURCE}
    assert result["description_placeholders"] == {
        "ntfy_entity": NTFY_ENTITY_ID,
        "ntfy_publish_url": NTFY_PUBLISH_URL,
    }
    for language in ("en", "de"):
        texts = json.loads((TRANSLATIONS / f"{language}.json").read_text("utf-8"))
        step = texts["options"]["step"]["ntfy"]
        assert set(step["data"]) == keys
        assert set(step["data_description"]) == keys
        for placeholder in ("ntfy_entity", "ntfy_publish_url"):
            assert f"{{{placeholder}}}" in step["description"]


async def test_ntfy_form_keeps_the_token_option(
    hass: HomeAssistant, ntfy_entry: MockConfigEntry
) -> None:
    """A stored token option survives, so it applies again after a switch back."""
    ntfy_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        ntfy_entry, options={**ntfy_entry.options, CONF_REQUIRE_TOKEN: True}
    )
    assert await hass.config_entries.async_setup(ntfy_entry.entry_id)
    await hass.async_block_till_done()
    old_alarm = ntfy_entry.runtime_data.alarm
    result = await _open_ntfy(hass, ntfy_entry)

    saved = await _save(hass, result["flow_id"], {CONF_RESET_MINUTES: 9})

    assert saved["type"] is FlowResultType.CREATE_ENTRY
    assert dict(ntfy_entry.options) == {
        CONF_RESET_MINUTES: 9,
        CONF_DEFAULT_TRANSPORT: "car",
        CONF_REQUIRE_TOKEN: True,
        CONF_LOCATION_SOURCE: "none",
    }
    assert ntfy_entry.runtime_data.alarm is not old_alarm
    assert ntfy_entry.runtime_data.alarm.reset_minutes == 9


async def test_ntfy_form_without_entity_and_topic(
    hass: HomeAssistant, ntfy_entry: MockConfigEntry
) -> None:
    """A missing entity or topic is shown as a dash, not as an error."""
    ntfy_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        ntfy_entry,
        data={**ntfy_entry.data, CONF_NTFY_ENTITY_UUID: None, CONF_NTFY_TOPIC: None},
    )

    result = await _open_ntfy(hass, ntfy_entry)

    assert result["description_placeholders"] == {
        "ntfy_entity": "–",
        "ntfy_publish_url": "–",
    }
    saved = await _save(hass, result["flow_id"])
    assert saved["data"] == {
        CONF_RESET_MINUTES: 30,
        CONF_DEFAULT_TRANSPORT: "car",
        CONF_REQUIRE_TOKEN: False,
        CONF_LOCATION_SOURCE: "none",
    }


async def test_ntfy_form_asks_for_the_location_values_in_a_second_step(
    hass: HomeAssistant, ntfy_entry: MockConfigEntry
) -> None:
    """The follow-up steps work in ntfy mode too; the token option is kept."""
    ntfy_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        ntfy_entry, options={**ntfy_entry.options, CONF_REQUIRE_TOKEN: True}
    )
    assert await hass.config_entries.async_setup(ntfy_entry.entry_id)
    await hass.async_block_till_done()
    result = await _open_ntfy(hass, ntfy_entry)

    result = await _save(hass, result["flow_id"], {CONF_LOCATION_SOURCE: "manual"})

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "location_manual"
    saved = await _save(
        hass,
        result["flow_id"],
        {
            CONF_LOCATION_LATITUDE: MANUAL_LATITUDE,
            CONF_LOCATION_LONGITUDE: MANUAL_LONGITUDE,
        },
    )

    assert saved["type"] is FlowResultType.CREATE_ENTRY
    assert dict(ntfy_entry.options) == {
        CONF_RESET_MINUTES: 30,
        CONF_DEFAULT_TRANSPORT: "car",
        CONF_REQUIRE_TOKEN: True,
        CONF_LOCATION_SOURCE: "manual",
        CONF_LOCATION_LATITUDE: MANUAL_LATITUDE,
        CONF_LOCATION_LONGITUDE: MANUAL_LONGITUDE,
    }
