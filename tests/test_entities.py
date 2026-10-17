"""End-to-end tests of the alarm entities: a call arrives, the entities follow."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest
from homeassistant.components import webhook
from homeassistant.components.sensor import SensorExtraStoredData
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from homeassistant.util.aiohttp import MockRequest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    async_mock_service,
    mock_restore_cache_with_extra_data,
)

from custom_components.ff_agent.const import (
    CONF_RESET_MINUTES,
    DOMAIN,
    EVENT_TYPE_ALARM,
    TOKEN_HEADER,
)

from .const import HEADER_TOKEN, REPLY_ID, WEBHOOK_ID

if TYPE_CHECKING:
    from freezegun.api import FrozenDateTimeFactory
    from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

PATH = f"/api/webhook/{WEBHOOK_ID}"
# Values that must never show up anywhere. They are invented.
BODY_VALUE = "STICHWORT-PLATZHALTER"
QUERY_VALUE = "query-value-placeholder"


async def _load(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Set up an entry that is already known to Home Assistant."""
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    await _load(hass, entry)


def _entity_id(
    hass: HomeAssistant, entry: MockConfigEntry, platform: str, key: str
) -> str:
    """Return the entity ID of an entity of the entry, looked up by its unique ID."""
    entity_id = er.async_get(hass).async_get_entity_id(
        platform, DOMAIN, f"{entry.entry_id}_{key}"
    )
    assert entity_id is not None
    return entity_id


def _entity_ids(hass: HomeAssistant, entry: MockConfigEntry) -> dict[str, str]:
    """Return the entity IDs of the three alarm entities."""
    return {
        "binary_sensor": _entity_id(hass, entry, "binary_sensor", "alarm"),
        "event": _entity_id(hass, entry, "event", "alarm"),
        "sensor": _entity_id(hass, entry, "sensor", "last_alarm"),
    }


def _state(hass: HomeAssistant, entity_id: str) -> State:
    state = hass.states.get(entity_id)
    assert state is not None
    return state


def _post() -> MockRequest:
    """Return a call as it arrives through a cloudhook."""
    return MockRequest(b"", "test", method="POST")


async def _call_webhook(hass: HomeAssistant) -> None:
    response = await webhook.async_handle_webhook(hass, WEBHOOK_ID, _post())
    assert response.status == HTTPStatus.OK
    await hass.async_block_till_done()


def _log_text(caplog: pytest.LogCaptureFixture) -> str:
    """Return the log messages of this integration."""
    return "\n".join(
        record.getMessage()
        for record in caplog.records
        if record.name.startswith("custom_components.ff_agent")
    )


# --- Entities and device --------------------------------------------------------


async def test_entities_exist_before_the_first_alarm(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """After the setup the binary sensor is off and event and sensor have no value."""
    await _setup(hass, mock_config_entry)

    ids = _entity_ids(hass, mock_config_entry)
    assert _state(hass, ids["binary_sensor"]).state == "off"
    assert _state(hass, ids["event"]).state == "unknown"
    assert _state(hass, ids["sensor"]).state == "unknown"


NAMES = {
    "en": [
        "FF Agent Test Alarm active",
        "FF Agent Test Alarm",
        "FF Agent Test Last alarm",
    ],
    "de": [
        "FF Agent Test Alarm aktiv",
        "FF Agent Test Alarm",
        "FF Agent Test Letzter Alarm",
    ],
}


@pytest.mark.parametrize("language", sorted(NAMES))
async def test_entity_names_are_translated(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    language: str,
) -> None:
    """The names come from the translations and start with the device name."""
    hass.config.language = language
    await _setup(hass, mock_config_entry)

    ids = _entity_ids(hass, mock_config_entry)
    friendly_names = [
        _state(hass, ids[platform]).attributes["friendly_name"]
        for platform in ("binary_sensor", "event", "sensor")
    ]
    assert friendly_names == NAMES[language]


async def test_entities_belong_to_one_service_device(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """All entities share a device of type service that is named like the entry."""
    await _setup(hass, mock_config_entry)

    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, mock_config_entry.entry_id), mock_config_entry.entry_id
    )
    assert device is not None
    assert device.entry_type is dr.DeviceEntryType.SERVICE
    assert device.name == mock_config_entry.title
    assert device.manufacturer == "mackoy consulting"
    assert device.model == "FF Agent"
    assert device.configuration_url == "https://www.ff-agent.com"

    registry = er.async_get(hass)
    for entity_id in _entity_ids(hass, mock_config_entry).values():
        entry = registry.async_get(entity_id)
        assert entry is not None
        assert entry.device_id == device.id
        assert entry.has_entity_name is True
        assert entry.translation_key in ("alarm", "last_alarm")


async def test_unique_ids_contain_the_entry_id_but_no_secret(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """The unique IDs are stable: entry ID and key, never the reply ID."""
    await _setup(hass, mock_config_entry)

    registry = er.async_get(hass)
    entries = er.async_entries_for_config_entry(registry, mock_config_entry.entry_id)
    assert {entry.unique_id for entry in entries} == {
        f"{mock_config_entry.entry_id}_alarm",
        f"{mock_config_entry.entry_id}_last_alarm",
    }
    assert len(entries) == 3
    for entry in entries:
        for secret in (REPLY_ID, WEBHOOK_ID, HEADER_TOKEN):
            assert secret not in entry.unique_id
            assert secret not in entry.entity_id


# --- A call arrives -------------------------------------------------------------


async def test_call_switches_all_entities(
    hass: HomeAssistant,
    hass_client_no_auth: ClientSessionGenerator,
    mock_config_entry: MockConfigEntry,
) -> None:
    """A POST makes the binary sensor on, triggers the event and sets the sensor."""
    await _setup(hass, mock_config_entry)
    client = await hass_client_no_auth()

    response = await client.post(PATH)
    await hass.async_block_till_done()

    assert response.status == HTTPStatus.OK
    ids = _entity_ids(hass, mock_config_entry)
    alarm = mock_config_entry.runtime_data.alarm
    assert alarm.last_alarm is not None

    assert _state(hass, ids["binary_sensor"]).state == "on"

    event = _state(hass, ids["event"])
    assert event.attributes["event_type"] == EVENT_TYPE_ALARM
    event_time = dt_util.parse_datetime(event.state)
    assert event_time is not None
    assert abs(event_time - alarm.last_alarm) < timedelta(seconds=5)

    last_alarm = _state(hass, ids["sensor"])
    # The state of a timestamp sensor is rounded down to full seconds.
    expected = alarm.last_alarm.replace(microsecond=0)
    assert dt_util.parse_datetime(last_alarm.state) == expected


async def test_entities_have_no_content_attributes(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """The state attributes hold no mission data, not even after a call."""
    await _setup(hass, mock_config_entry)
    await _call_webhook(hass)

    ids = _entity_ids(hass, mock_config_entry)
    assert set(_state(hass, ids["binary_sensor"]).attributes) == {"friendly_name"}
    assert set(_state(hass, ids["event"]).attributes) == {
        "friendly_name",
        "event_type",
        "event_types",
    }
    assert _state(hass, ids["event"]).attributes["event_types"] == [EVENT_TYPE_ALARM]
    assert set(_state(hass, ids["sensor"]).attributes) == {
        "friendly_name",
        "device_class",
    }
    assert _state(hass, ids["sensor"]).attributes["device_class"] == "timestamp"


async def test_repeated_call_changes_nothing(
    hass: HomeAssistant,
    hass_client_no_auth: ClientSessionGenerator,
    mock_config_entry: MockConfigEntry,
) -> None:
    """A second call right after the first is counted but triggers no second event."""
    await _setup(hass, mock_config_entry)
    client = await hass_client_no_auth()
    ids = _entity_ids(hass, mock_config_entry)

    assert (await client.post(PATH)).status == HTTPStatus.OK
    await hass.async_block_till_done()
    event_state = _state(hass, ids["event"]).state
    sensor_state = _state(hass, ids["sensor"]).state

    assert (await client.post(PATH)).status == HTTPStatus.OK
    await hass.async_block_till_done()

    alarm = mock_config_entry.runtime_data.alarm
    counters = (alarm.calls_total, alarm.alarms_total, alarm.deduplicated_total)
    assert counters == (2, 1, 1)
    assert _state(hass, ids["event"]).state == event_state
    assert _state(hass, ids["sensor"]).state == sensor_state
    assert _state(hass, ids["binary_sensor"]).state == "on"


async def test_new_alarm_after_the_window_triggers_the_event_again(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    mock_config_entry: MockConfigEntry,
) -> None:
    """A call 31 seconds later is a new alarm: the event and the sensor move on."""
    await _setup(hass, mock_config_entry)
    ids = _entity_ids(hass, mock_config_entry)

    await _call_webhook(hass)
    first_event = _state(hass, ids["event"]).state
    first_alarm = _state(hass, ids["sensor"]).state

    freezer.tick(timedelta(seconds=31))
    async_fire_time_changed(hass)
    await _call_webhook(hass)

    assert _state(hass, ids["event"]).state != first_event
    assert _state(hass, ids["sensor"]).state != first_alarm
    assert mock_config_entry.runtime_data.alarm.alarms_total == 2


async def test_binary_sensor_goes_off_after_the_reset_time(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    mock_config_entry: MockConfigEntry,
) -> None:
    """After 31 minutes the binary sensor is off, the last alarm stays."""
    await _setup(hass, mock_config_entry)
    ids = _entity_ids(hass, mock_config_entry)
    await _call_webhook(hass)
    last_alarm = _state(hass, ids["sensor"]).state

    freezer.tick(timedelta(minutes=29))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert _state(hass, ids["binary_sensor"]).state == "on"

    freezer.tick(timedelta(minutes=2))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert _state(hass, ids["binary_sensor"]).state == "off"
    assert _state(hass, ids["sensor"]).state == last_alarm


async def test_reset_time_comes_from_the_options(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    mock_config_entry: MockConfigEntry,
    entry_data: dict[str, Any],
    entry_options: dict[str, Any],
) -> None:
    """The option reset_minutes decides when the binary sensor goes off."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=mock_config_entry.title,
        unique_id=mock_config_entry.unique_id,
        data=entry_data,
        options={**entry_options, CONF_RESET_MINUTES: 5},
    )
    await _setup(hass, entry)
    ids = _entity_ids(hass, entry)
    await _call_webhook(hass)
    assert _state(hass, ids["binary_sensor"]).state == "on"

    freezer.tick(timedelta(minutes=6))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert _state(hass, ids["binary_sensor"]).state == "off"


async def test_unload_cancels_the_timer_and_removes_the_entities(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Unloading stops the reset timer; the entities are no longer available."""
    await _setup(hass, mock_config_entry)
    ids = _entity_ids(hass, mock_config_entry)
    await _call_webhook(hass)
    alarm = mock_config_entry.runtime_data.alarm

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    freezer.tick(timedelta(minutes=31))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    # The timer was cancelled: it did not reset the manager.
    assert alarm.active is True
    for entity_id in ids.values():
        assert _state(hass, entity_id).state == "unavailable"


# --- Restore --------------------------------------------------------------------


def _register_last_alarm_sensor(hass: HomeAssistant, entry: MockConfigEntry) -> str:
    """Create the registry entry of the sensor, so its entity ID is known."""
    entry.add_to_hass(hass)
    sensor = er.async_get(hass).async_get_or_create(
        Platform.SENSOR,
        DOMAIN,
        f"{entry.entry_id}_last_alarm",
        config_entry=entry,
        suggested_object_id="ff_agent_test_last_alarm",
    )
    return sensor.entity_id


async def test_last_alarm_is_restored_but_the_alarm_is_not_active(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """After a restart the sensor shows the last alarm, the binary sensor is off."""
    restored_at = datetime(2026, 10, 1, 8, 30, tzinfo=UTC)
    entity_id = _register_last_alarm_sensor(hass, mock_config_entry)
    mock_restore_cache_with_extra_data(
        hass,
        (
            (
                State(entity_id, restored_at.isoformat()),
                SensorExtraStoredData(restored_at, None).as_dict(),
            ),
        ),
    )

    await _load(hass, mock_config_entry)

    ids = _entity_ids(hass, mock_config_entry)
    assert ids["sensor"] == entity_id
    assert _state(hass, entity_id).state == restored_at.isoformat()
    assert _state(hass, ids["binary_sensor"]).state == "off"
    # Only the display is restored: the manager and its window start empty ...
    alarm = mock_config_entry.runtime_data.alarm
    assert alarm.last_alarm is None
    # ... so even a call right after the restart is a new alarm.
    await _call_webhook(hass)
    assert (alarm.alarms_total, alarm.deduplicated_total) == (1, 0)
    assert _state(hass, ids["binary_sensor"]).state == "on"
    assert _state(hass, entity_id).state != restored_at.isoformat()


async def test_invalid_restored_value_is_ignored(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """A stored value that is no time leaves the sensor without a value."""
    entity_id = _register_last_alarm_sensor(hass, mock_config_entry)
    mock_restore_cache_with_extra_data(
        hass,
        (
            (
                State(entity_id, "garbage"),
                {"native_value": "garbage", "native_unit_of_measurement": None},
            ),
        ),
    )

    await _load(hass, mock_config_entry)

    assert _state(hass, entity_id).state == "unknown"


async def test_sensor_shows_an_alarm_that_came_before_it_was_added(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """The webhook is open before the platforms are set up; an early alarm counts."""
    entity_id = _register_last_alarm_sensor(hass, mock_config_entry)
    restored_at = datetime(2026, 10, 1, 8, 30, tzinfo=UTC)
    mock_restore_cache_with_extra_data(
        hass,
        (
            (
                State(entity_id, restored_at.isoformat()),
                SensorExtraStoredData(restored_at, None).as_dict(),
            ),
        ),
    )
    with patch("custom_components.ff_agent.PLATFORMS", []):
        await _load(hass, mock_config_entry)
    await _call_webhook(hass)
    alarm = mock_config_entry.runtime_data.alarm
    assert alarm.last_alarm is not None

    await hass.config_entries.async_forward_entry_setups(
        mock_config_entry, [Platform.SENSOR]
    )
    await hass.async_block_till_done()

    # The alarm is newer than what was stored.
    expected = alarm.last_alarm.replace(microsecond=0)
    assert dt_util.parse_datetime(_state(hass, entity_id).state) == expected


# --- Automation -----------------------------------------------------------------


async def _setup_automation(
    hass: HomeAssistant, event_entity_id: str, *, with_filters: bool = True
) -> list:
    """Create the example automation: when the event triggers, call a service.

    The filters not_from and not_to "unavailable" are mandatory in the example of the
    documentation (see the reload tests below).
    """
    calls = async_mock_service(hass, "test", "light_on")
    trigger = {"trigger": "state", "entity_id": event_entity_id}
    if with_filters:
        trigger |= {"not_from": "unavailable", "not_to": "unavailable"}
    assert await async_setup_component(
        hass,
        "automation",
        {
            "automation": {
                "alias": "Alarm: light on",
                "triggers": [trigger],
                "actions": [{"action": "test.light_on"}],
            }
        },
    )
    await hass.async_block_till_done()
    return calls


async def test_event_entity_triggers_an_automation_once_per_alarm(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    mock_config_entry: MockConfigEntry,
) -> None:
    """The documented example: the event entity starts an automation for each alarm.

    The filters not_from and not_to "unavailable" belong to the example and are
    mandatory, see test_reloading_without_the_filters_triggers_the_automation.
    """
    await _setup(hass, mock_config_entry)
    calls = await _setup_automation(
        hass, _entity_id(hass, mock_config_entry, "event", "alarm")
    )

    await _call_webhook(hass)
    assert len(calls) == 1

    # A repetition within 30 seconds does not trigger again ...
    freezer.tick(timedelta(seconds=10))
    await _call_webhook(hass)
    assert len(calls) == 1

    # ... a later alarm does.
    freezer.tick(timedelta(seconds=30))
    async_fire_time_changed(hass)
    await _call_webhook(hass)
    assert len(calls) == 2


async def test_reloading_the_entry_does_not_trigger_the_automation(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Reloading restores the event state; that must not look like an alarm."""
    await _setup(hass, mock_config_entry)
    calls = await _setup_automation(
        hass, _entity_id(hass, mock_config_entry, "event", "alarm")
    )
    await _call_webhook(hass)
    assert len(calls) == 1

    assert await hass.config_entries.async_reload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert len(calls) == 1


# --- Privacy --------------------------------------------------------------------


async def test_alarm_flow_logs_no_secret_and_no_content(
    hass: HomeAssistant,
    hass_client_no_auth: ClientSessionGenerator,
    token_entry: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Neither IDs, token nor values of the call reach the log of the integration."""
    caplog.set_level(logging.DEBUG)
    await _setup(hass, token_entry)
    client = await hass_client_no_auth()

    response = await client.post(
        PATH,
        params={"keyword": QUERY_VALUE},
        json={"keyword": BODY_VALUE},
        headers={TOKEN_HEADER: HEADER_TOKEN},
    )
    await hass.async_block_till_done()
    assert response.status == HTTPStatus.OK
    assert token_entry.runtime_data.alarm.alarms_total == 1

    log = _log_text(caplog)
    assert "Alarm recognized" in log
    for secret in (REPLY_ID, WEBHOOK_ID, HEADER_TOKEN, BODY_VALUE, QUERY_VALUE):
        assert secret not in log


async def test_reloading_without_the_filters_triggers_the_automation(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Why the example needs its filters: without them a reload looks like an alarm.

    On a reload the event entity goes to unavailable and comes back, and both changes
    start a plain state trigger.
    """
    await _setup(hass, mock_config_entry)
    calls = await _setup_automation(
        hass, _entity_id(hass, mock_config_entry, "event", "alarm"), with_filters=False
    )
    await _call_webhook(hass)
    assert len(calls) == 1

    assert await hass.config_entries.async_reload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert len(calls) > 1


async def test_restored_time_without_a_time_zone_is_ignored(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """A stored time without a time zone cannot be a timestamp and is not shown."""
    entity_id = _register_last_alarm_sensor(hass, mock_config_entry)
    naive = datetime(2026, 10, 1, 8, 30)
    mock_restore_cache_with_extra_data(
        hass,
        (
            (
                State(entity_id, naive.isoformat()),
                SensorExtraStoredData(naive, None).as_dict(),
            ),
        ),
    )

    await _load(hass, mock_config_entry)

    assert _state(hass, entity_id).state == "unknown"
