"""Scenario tests of the alarm logic: clock jumps, several people, reload, removal."""

from __future__ import annotations

import json
from collections.abc import Generator
from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from functools import partial
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

import pytest
from homeassistant.components import webhook
from homeassistant.components.sensor import SensorExtraStoredData
from homeassistant.const import CONF_WEBHOOK_ID
from homeassistant.core import HomeAssistant, State, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.util import dt as dt_util
from homeassistant.util.aiohttp import MockRequest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    mock_restore_cache_with_extra_data,
)

from custom_components.ff_agent.alarm import AlarmManager
from custom_components.ff_agent.const import (
    CONF_RESET_MINUTES,
    DEDUP_SECONDS,
    DOMAIN,
    SIGNAL_ALARM,
    SIGNAL_ALARM_STATE,
)
from custom_components.ff_agent.models import WebhookCall
from custom_components.ff_agent.reply_url import reply_unique_id

from .const import OTHER_REPLY_ID, REPLY_ID, WEBHOOK_ID

if TYPE_CHECKING:
    from freezegun.api import FrozenDateTimeFactory
    from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

OTHER_WEBHOOK_ID = "test-webhook-id-placeholder-other"
ENTRY_ID = "test-entry-id"
BODY_VALUE = "STICHWORT-PLATZHALTER"
QUERY_VALUE = "query-value-placeholder"
HEADER_VALUE = "header-value-placeholder"


def _call() -> WebhookCall:
    """Return a call that was received now (the frozen time)."""
    return WebhookCall(
        received_at=dt_util.utcnow(),
        method="POST",
        content_type=None,
        body_length=0,
        header_names=(),
        user_agent=None,
        query_keys=(),
        body_kind="empty",
        body_shape=None,
    )


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def _entity_id(
    hass: HomeAssistant, entry: MockConfigEntry, platform: str, key: str
) -> str:
    entity_id = er.async_get(hass).async_get_entity_id(
        platform, DOMAIN, f"{entry.entry_id}_{key}"
    )
    assert entity_id is not None
    return entity_id


def _state(hass: HomeAssistant, entity_id: str) -> State:
    state = hass.states.get(entity_id)
    assert state is not None
    return state


def _ids(hass: HomeAssistant, entry: MockConfigEntry) -> list[str]:
    """Return binary sensor, event and sensor of the entry."""
    return [
        _entity_id(hass, entry, platform, key)
        for platform, key in (
            ("binary_sensor", "alarm"),
            ("event", "alarm"),
            ("sensor", "last_alarm"),
        )
    ]


async def _call_webhook(hass: HomeAssistant, webhook_id: str = WEBHOOK_ID) -> None:
    request = MockRequest(b"", "test", method="POST")
    response = await webhook.async_handle_webhook(hass, webhook_id, request)
    assert response.status == HTTPStatus.OK
    await hass.async_block_till_done()


async def _tick(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, delta: timedelta
) -> None:
    freezer.tick(delta)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


@pytest.fixture
def manager(hass: HomeAssistant) -> Generator[AlarmManager]:
    """Return a manager with a reset time of 30 minutes."""
    alarm_manager = AlarmManager(hass, ENTRY_ID, 30)
    yield alarm_manager
    alarm_manager.async_shutdown()


@pytest.fixture
def other_entry(
    mock_config_entry: MockConfigEntry, entry_data: dict[str, Any]
) -> MockConfigEntry:
    """Return the entry of a second person."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="FF Agent Other",
        unique_id=reply_unique_id(OTHER_REPLY_ID),
        data={
            **entry_data,
            "reply_id": OTHER_REPLY_ID,
            CONF_WEBHOOK_ID: OTHER_WEBHOOK_ID,
        },
        options=dict(mock_config_entry.options),
    )


# --- Deduplication at the limit, with jumps of the clock ----------------------------


async def test_dedup_limit_to_the_microsecond(
    freezer: FrozenDateTimeFactory, manager: AlarmManager
) -> None:
    """One microsecond before the limit is a repetition, at the limit a new alarm."""
    manager.async_handle_call(_call())

    freezer.tick(timedelta(seconds=DEDUP_SECONDS, microseconds=-1))
    manager.async_handle_call(_call())
    assert (manager.alarms_total, manager.deduplicated_total) == (1, 1)

    # The window counts from the last alarm, not from the last repetition.
    freezer.tick(timedelta(microseconds=1))
    manager.async_handle_call(_call())
    assert (manager.alarms_total, manager.deduplicated_total) == (2, 1)


async def test_jump_forward_in_time_gives_a_new_alarm(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, manager: AlarmManager
) -> None:
    """After a jump of the clock (e.g. time sync) the next call is a new alarm."""
    manager.async_handle_call(_call())

    freezer.move_to(dt_util.utcnow() + timedelta(hours=7))
    new_call = _call()
    manager.async_handle_call(new_call)

    assert manager.alarms_total == 2
    assert manager.last_alarm == new_call.received_at
    assert manager.active_until == new_call.received_at + timedelta(minutes=30)


async def test_jump_over_the_reset_time_switches_off_and_next_call_starts_again(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, manager: AlarmManager
) -> None:
    """A jump past the reset time ends the alarm; a later call starts a new one."""
    manager.async_handle_call(_call())

    await _tick(hass, freezer, timedelta(hours=7))
    assert manager.active is False

    manager.async_handle_call(_call())
    assert manager.active is True
    assert manager.alarms_total == 2


async def test_dedup_with_a_time_zone_other_than_utc(
    freezer: FrozenDateTimeFactory, manager: AlarmManager
) -> None:
    """The comparison works on instants, whatever offset the timestamps carry."""
    first = _call()
    manager.async_handle_call(first)
    freezer.tick(timedelta(seconds=10))
    later = _call()
    offset = timezone(timedelta(hours=-5))
    local = replace(later, received_at=later.received_at.astimezone(offset))

    manager.async_handle_call(local)

    assert (manager.alarms_total, manager.deduplicated_total) == (1, 1)


# --- Two people are independent -----------------------------------------------------


async def test_two_entries_are_independent(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    mock_config_entry: MockConfigEntry,
    other_entry: MockConfigEntry,
) -> None:
    """An alarm of person A changes nothing at person B, signals are separate."""
    await _setup(hass, mock_config_entry)
    await _setup(hass, other_entry)
    seen: list[tuple[str, str]] = []

    @callback
    def _on_alarm(which: str, _event: object) -> None:
        seen.append((which, "alarm"))

    @callback
    def _on_state(which: str) -> None:
        seen.append((which, "state"))

    removers = []
    for entry, which in ((mock_config_entry, "a"), (other_entry, "b")):
        removers.append(
            async_dispatcher_connect(
                hass,
                SIGNAL_ALARM.format(entry_id=entry.entry_id),
                partial(_on_alarm, which),
            )
        )
        removers.append(
            async_dispatcher_connect(
                hass,
                SIGNAL_ALARM_STATE.format(entry_id=entry.entry_id),
                partial(_on_state, which),
            )
        )

    await _call_webhook(hass, WEBHOOK_ID)

    alarm_a = mock_config_entry.runtime_data.alarm
    alarm_b = other_entry.runtime_data.alarm
    assert alarm_a is not alarm_b
    assert (alarm_a.calls_total, alarm_a.alarms_total, alarm_a.active) == (1, 1, True)
    assert (alarm_b.calls_total, alarm_b.alarms_total, alarm_b.active) == (0, 0, False)
    assert alarm_b.last_alarm is None
    assert alarm_b.last_call is None
    assert sorted(seen) == [("a", "alarm"), ("a", "state")]
    ids_a = _ids(hass, mock_config_entry)
    ids_b = _ids(hass, other_entry)
    assert _state(hass, ids_a[0]).state == "on"
    assert _state(hass, ids_b[0]).state == "off"
    assert _state(hass, ids_b[1]).state == "unknown"
    assert _state(hass, ids_b[2]).state == "unknown"

    # B is not inside the deduplication window of A: its first call is an alarm.
    freezer.tick(timedelta(seconds=5))
    await _call_webhook(hass, OTHER_WEBHOOK_ID)
    assert (alarm_b.alarms_total, alarm_b.deduplicated_total) == (1, 0)
    assert alarm_a.alarms_total == 1

    # A's timer ends A only.
    await _tick(hass, freezer, timedelta(minutes=29, seconds=58))
    assert alarm_a.active is False
    assert alarm_b.active is True

    for remove in removers:
        remove()


# --- Reload with a changed reset time -----------------------------------------------


async def test_reload_with_changed_reset_time(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    mock_config_entry: MockConfigEntry,
) -> None:
    """After a reload the new reset time counts and the old timer is gone."""
    await _setup(hass, mock_config_entry)
    old_alarm = mock_config_entry.runtime_data.alarm
    await _call_webhook(hass)
    await _tick(hass, freezer, timedelta(minutes=2))

    hass.config_entries.async_update_entry(
        mock_config_entry,
        options={**mock_config_entry.options, CONF_RESET_MINUTES: 5},
    )
    assert await hass.config_entries.async_reload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    new_alarm = mock_config_entry.runtime_data.alarm
    assert new_alarm is not old_alarm
    assert new_alarm.reset_minutes == 5
    binary_sensor = _entity_id(hass, mock_config_entry, "binary_sensor", "alarm")

    await _call_webhook(hass)
    assert _state(hass, binary_sensor).state == "on"
    await _tick(hass, freezer, timedelta(minutes=4))
    assert _state(hass, binary_sensor).state == "on"
    await _tick(hass, freezer, timedelta(minutes=2))
    assert _state(hass, binary_sensor).state == "off"

    # The timer of the old manager (30 minutes) was cancelled by the unload.
    await _tick(hass, freezer, timedelta(minutes=30))
    assert old_alarm.active is True


# --- Restore with a time zone -------------------------------------------------------


async def test_restore_with_a_time_zone_offset(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """A stored time with an offset is shown as the same instant."""
    restored_at = datetime(2026, 10, 1, 8, 30, tzinfo=timezone(timedelta(hours=2)))
    mock_config_entry.add_to_hass(hass)
    registry_entry = er.async_get(hass).async_get_or_create(
        "sensor",
        DOMAIN,
        f"{mock_config_entry.entry_id}_last_alarm",
        config_entry=mock_config_entry,
        suggested_object_id="ff_agent_test_last_alarm",
    )
    entity_id = registry_entry.entity_id
    mock_restore_cache_with_extra_data(
        hass,
        (
            (
                State(entity_id, restored_at.isoformat()),
                SensorExtraStoredData(restored_at, None).as_dict(),
            ),
        ),
    )

    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    shown = dt_util.parse_datetime(_state(hass, entity_id).state)
    assert shown == restored_at
    assert shown == datetime(2026, 10, 1, 6, 30, tzinfo=UTC)


# --- Recorder ---------------------------------------------------------------------


async def test_recorded_states_carry_no_content(
    hass: HomeAssistant,
    hass_client_no_auth: ClientSessionGenerator,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Event, binary sensor and sensor hold no value of the call, not even hidden."""
    await _setup(hass, mock_config_entry)
    client = await hass_client_no_auth()

    response = await client.post(
        f"/api/webhook/{WEBHOOK_ID}",
        params={"keyword": QUERY_VALUE},
        json={"keyword": BODY_VALUE},
        headers={"X-Mission": HEADER_VALUE},
    )
    await hass.async_block_till_done()
    assert response.status == HTTPStatus.OK

    states = [
        _state(hass, _entity_id(hass, mock_config_entry, platform, key))
        for platform, key in (
            ("binary_sensor", "alarm"),
            ("event", "alarm"),
            ("sensor", "last_alarm"),
        )
    ]
    dumped = json.dumps([state.as_dict() for state in states], default=str)
    for value in (BODY_VALUE, QUERY_VALUE, HEADER_VALUE, REPLY_ID, WEBHOOK_ID):
        assert value not in dumped
    assert states[1].attributes["event_types"] == ["alarm"]
    assert set(states[1].attributes) == {"friendly_name", "event_type", "event_types"}
    assert set(states[0].attributes) == {"friendly_name"}


# --- Removal of the entry ---------------------------------------------------------


async def test_removing_the_entry_removes_entities_device_and_timer(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    mock_config_entry: MockConfigEntry,
) -> None:
    """After the removal no entity, device or timer of the entry is left."""
    await _setup(hass, mock_config_entry)
    entry_id = mock_config_entry.entry_id
    entity_ids = [
        _entity_id(hass, mock_config_entry, platform, key)
        for platform, key in (
            ("binary_sensor", "alarm"),
            ("event", "alarm"),
            ("sensor", "last_alarm"),
        )
    ]
    await _call_webhook(hass)
    alarm = mock_config_entry.runtime_data.alarm
    states_after_removal = 0

    @callback
    def _count() -> None:
        nonlocal states_after_removal
        states_after_removal += 1

    remove = async_dispatcher_connect(
        hass, SIGNAL_ALARM_STATE.format(entry_id=entry_id), _count
    )

    assert await hass.config_entries.async_remove(entry_id)
    await hass.async_block_till_done()

    registry = er.async_get(hass)
    assert er.async_entries_for_config_entry(registry, entry_id) == []
    for entity_id in entity_ids:
        assert registry.async_get(entity_id) is None
        assert hass.states.get(entity_id) is None
    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, entry_id), entry_id
    )
    assert device is None

    # The reset timer is gone: nothing fires, and a late call is ignored.
    await _tick(hass, freezer, timedelta(minutes=31))
    assert states_after_removal == 0
    assert alarm.active is True
    alarm.async_handle_call(_call())
    assert alarm.calls_total == 1
    remove()
