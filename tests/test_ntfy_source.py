"""Tests for the alarm source ntfy: the search, the listener and the setup.

The ntfy integration is never loaded. Its config entry with the topic subentry, the
registry entry of its event entity and the states of that entity are simulated with
placeholder values.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from http import HTTPStatus
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from homeassistant.components import webhook
from homeassistant.config_entries import ConfigEntryState, ConfigSubentryDataWithId
from homeassistant.const import ATTR_RESTORED, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.util import dt as dt_util
from homeassistant.util.aiohttp import MockRequest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ff_agent.const import (
    CONF_NTFY_ENTITY_UUID,
    DOMAIN,
    ISSUE_NTFY_ENTITY_MISSING,
)
from custom_components.ff_agent.models import NtfySubscription
from custom_components.ff_agent.ntfy_source import (
    NtfyAlarmSource,
    async_describe_entity,
    async_find_subscription_by_topic,
    async_generate_topic,
    ntfy_publish_url,
)

from .common import (
    add_ntfy_entity,
    add_ntfy_entry,
    async_setup_entry,
    fire_ntfy,
)
from .const import (
    ACCEPT_URL,
    NTFY_ENTITY_ID,
    NTFY_SUBENTRY_ID,
    NTFY_TOPIC,
    OTHER_NTFY_ENTITY_ID,
    OTHER_NTFY_SUBENTRY_ID,
    OTHER_NTFY_TOPIC,
    OWN_NTFY_SERVER,
    WEBHOOK_ID,
)

if TYPE_CHECKING:
    from freezegun.api import FrozenDateTimeFactory
    from pytest_homeassistant_custom_component.test_util.aiohttp import (
        AiohttpClientMocker,
    )

NOW = "2026-10-17 12:00:00+00:00"


def _alarm_state(hass: HomeAssistant, entry: MockConfigEntry) -> str:
    entity_id = er.async_get(hass).async_get_entity_id(
        "binary_sensor", DOMAIN, f"{entry.entry_id}_alarm"
    )
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    return state.state


def _issue(hass: HomeAssistant, entry: MockConfigEntry) -> ir.IssueEntry | None:
    issue_id = ISSUE_NTFY_ENTITY_MISSING.format(entry_id=entry.entry_id)
    return ir.async_get(hass).async_get_issue(DOMAIN, issue_id)


async def _setup_with_uuid(
    hass: HomeAssistant, entry: MockConfigEntry, uuid: str | None
) -> None:
    """Set up the entry with another stored registry UUID."""
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        entry, data={**entry.data, CONF_NTFY_ENTITY_UUID: uuid}
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def _source(entry: MockConfigEntry) -> NtfyAlarmSource:
    source = entry.runtime_data.source
    assert source is not None
    return source


@pytest.fixture
def frozen(freezer: FrozenDateTimeFactory) -> FrozenDateTimeFactory:
    """Freeze the time at a fixed placeholder moment."""
    freezer.move_to(NOW)
    return freezer


# --- The search -----------------------


async def test_find_subscription_by_topic(
    hass: HomeAssistant, ntfy_entity: er.RegistryEntry
) -> None:
    """Topic -> subentry -> registry entry of the event entity."""
    assert async_find_subscription_by_topic(hass, NTFY_TOPIC) == NtfySubscription(
        entity_id=NTFY_ENTITY_ID,
        entity_uuid=ntfy_entity.id,
        topic=NTFY_TOPIC,
        server="https://ntfy.sh/",
    )


async def test_find_subscription_among_several_topics(hass: HomeAssistant) -> None:
    """With two subscriptions the one of the topic is found."""
    ntfy_entry = add_ntfy_entry(
        hass,
        {NTFY_SUBENTRY_ID: NTFY_TOPIC, OTHER_NTFY_SUBENTRY_ID: OTHER_NTFY_TOPIC},
        url=OWN_NTFY_SERVER,
    )
    add_ntfy_entity(hass, ntfy_entry)
    other = add_ntfy_entity(
        hass, ntfy_entry, OTHER_NTFY_SUBENTRY_ID, OTHER_NTFY_ENTITY_ID
    )

    found = async_find_subscription_by_topic(hass, OTHER_NTFY_TOPIC)

    assert found is not None
    assert (found.entity_id, found.entity_uuid) == (OTHER_NTFY_ENTITY_ID, other.id)
    assert (found.topic, found.server) == (OTHER_NTFY_TOPIC, OWN_NTFY_SERVER)


async def test_find_without_ntfy_entry(hass: HomeAssistant) -> None:
    """Without the ntfy integration nothing is found."""
    assert async_find_subscription_by_topic(hass, NTFY_TOPIC) is None


@pytest.mark.usefixtures("ntfy_entity")
async def test_find_another_topic(hass: HomeAssistant) -> None:
    """A topic nobody subscribed to is not found."""
    assert async_find_subscription_by_topic(hass, OTHER_NTFY_TOPIC) is None


async def test_find_ignores_other_subentry_types(hass: HomeAssistant) -> None:
    """Only subentries of the type "topic" count."""
    ntfy_entry = MockConfigEntry(
        domain="ntfy",
        data={"url": "https://ntfy.sh/"},
        subentries_data=[
            ConfigSubentryDataWithId(
                data={"topic": NTFY_TOPIC},
                subentry_id=NTFY_SUBENTRY_ID,
                subentry_type="other",
                title="FF Agent Alarm",
                unique_id=NTFY_TOPIC,
            )
        ],
    )
    ntfy_entry.add_to_hass(hass)
    add_ntfy_entity(hass, ntfy_entry)

    assert async_find_subscription_by_topic(hass, NTFY_TOPIC) is None
    # The entity itself is fine, only its topic cannot be read.
    found = async_describe_entity(hass, NTFY_ENTITY_ID)
    assert found is not None
    assert found.topic is None


async def test_find_subscription_without_event_entity(hass: HomeAssistant) -> None:
    """A subscription whose entity is not registered (yet) is not found."""
    add_ntfy_entry(hass)

    assert async_find_subscription_by_topic(hass, NTFY_TOPIC) is None


async def test_find_ignores_a_disabled_entity(
    hass: HomeAssistant, ntfy_entity: er.RegistryEntry
) -> None:
    """A disabled entity receives nothing, so it does not count as found."""
    er.async_get(hass).async_update_entity(
        ntfy_entity.entity_id, disabled_by=er.RegistryEntryDisabler.USER
    )

    assert async_find_subscription_by_topic(hass, NTFY_TOPIC) is None


async def test_describe_by_entity_id_and_by_uuid(
    hass: HomeAssistant, ntfy_entity: er.RegistryEntry
) -> None:
    """The entity can be named by its entity ID or by its registry UUID."""
    by_id = async_describe_entity(hass, NTFY_ENTITY_ID)
    by_uuid = async_describe_entity(hass, ntfy_entity.id)

    assert by_id == by_uuid
    assert by_id is not None
    assert (by_id.topic, by_id.server) == (NTFY_TOPIC, "https://ntfy.sh/")


async def test_describe_without_subentry(hass: HomeAssistant) -> None:
    """A missing subentry gives no topic, but no error either."""
    ntfy_entry = add_ntfy_entry(hass)
    registry_entry = er.async_get(hass).async_get_or_create(
        "event",
        "ntfy",
        "no-subentry",
        config_entry=ntfy_entry,
        suggested_object_id="ff_agent_alarm",
    )

    found = async_describe_entity(hass, registry_entry.id)

    assert found is not None
    assert found.topic is None
    assert found.server == "https://ntfy.sh/"


async def test_describe_without_config_entry(hass: HomeAssistant) -> None:
    """An ntfy entity without config entry gives neither topic nor server."""
    registry_entry = er.async_get(hass).async_get_or_create(
        "event", "ntfy", "orphan", suggested_object_id="ff_agent_alarm"
    )

    found = async_describe_entity(hass, registry_entry.id)

    assert found == NtfySubscription(
        entity_id=NTFY_ENTITY_ID,
        entity_uuid=registry_entry.id,
        topic=None,
        server=None,
    )


async def test_describe_with_unreadable_values(hass: HomeAssistant) -> None:
    """Values of an unexpected type are treated as unreadable."""
    ntfy_entry = MockConfigEntry(domain="ntfy", data={"url": 42})
    ntfy_entry.add_to_hass(hass)
    registry_entry = er.async_get(hass).async_get_or_create(
        "event", "ntfy", "odd", config_entry=ntfy_entry
    )

    found = async_describe_entity(hass, registry_entry.id)

    assert found is not None
    assert (found.topic, found.server) == (None, None)


@pytest.mark.parametrize(
    ("domain", "platform"),
    [("event", "demo"), ("sensor", "ntfy")],
    ids=["other platform", "other domain"],
)
async def test_describe_refuses_foreign_entities(
    hass: HomeAssistant, domain: str, platform: str
) -> None:
    """Only event entities of the integration ntfy are accepted."""
    registry_entry = er.async_get(hass).async_get_or_create(domain, platform, "x")

    assert async_describe_entity(hass, registry_entry.id) is None
    assert async_describe_entity(hass, registry_entry.entity_id) is None


@pytest.mark.parametrize(
    "value", ["0123456789abcdef0123456789abcdef", "event.does_not_exist", ""]
)
async def test_describe_unknown_entities(hass: HomeAssistant, value: str) -> None:
    """An unknown UUID or entity ID gives None, not an error."""
    assert async_describe_entity(hass, value) is None


@pytest.mark.parametrize(
    ("server", "expected"),
    [
        ("https://ntfy.sh/", f"https://ntfy.sh/{NTFY_TOPIC}/trigger"),
        ("https://ntfy.sh", f"https://ntfy.sh/{NTFY_TOPIC}/trigger"),
        (OWN_NTFY_SERVER, f"https://ntfy.example.com/{NTFY_TOPIC}/trigger"),
        (None, f"https://ntfy.sh/{NTFY_TOPIC}/trigger"),
    ],
)
def test_publish_url(server: str | None, expected: str) -> None:
    """GET on /<topic>/trigger, with or without a trailing slash of the server."""
    assert ntfy_publish_url(server, NTFY_TOPIC) == expected


def test_generated_topics_are_random_hex() -> None:
    """32 lower case hex characters (128 bits), no telling prefix, never the same."""
    topics = {async_generate_topic() for _ in range(20)}

    assert len(topics) == 20
    for topic in topics:
        assert len(topic) == 32
        assert set(topic) <= set("0123456789abcdef")


# --- The listener -----------------------


async def test_fresh_message_is_an_alarm(
    hass: HomeAssistant, frozen: FrozenDateTimeFactory, ntfy_entry: MockConfigEntry
) -> None:
    """A new and fresh timestamp after a known one is exactly one alarm."""
    fire_ntfy(hass, dt_util.utcnow() - timedelta(hours=1))
    await async_setup_entry(hass, ntfy_entry)
    assert _alarm_state(hass, ntfy_entry) == "off"

    timestamp = fire_ntfy(hass)
    await hass.async_block_till_done()

    alarm = ntfy_entry.runtime_data.alarm
    assert (alarm.alarms_total, alarm.last_alarm) == (1, timestamp)
    assert _alarm_state(hass, ntfy_entry) == "on"
    event_id = er.async_get(hass).async_get_entity_id(
        "event", DOMAIN, f"{ntfy_entry.entry_id}_alarm"
    )
    assert event_id is not None
    event_state = hass.states.get(event_id)
    assert event_state is not None
    assert event_state.state == timestamp.isoformat(timespec="milliseconds")
    source = _source(ntfy_entry)
    assert (source.events_total, source.accepted_total) == (1, 1)
    # Webhook calls are a different thing; none came in.
    assert alarm.calls_total == 0


async def test_added_entity_restores_an_old_value(
    hass: HomeAssistant, frozen: FrozenDateTimeFactory, ntfy_entry: MockConfigEntry
) -> None:
    """The first state of an entity that was just added is its restored value."""
    await async_setup_entry(hass, ntfy_entry)

    old = fire_ntfy(hass, dt_util.utcnow() - timedelta(seconds=5))
    await hass.async_block_till_done()
    # The same value again, only another attribute: already seen.
    fire_ntfy(hass, old, {"id": "other"})
    await hass.async_block_till_done()

    source = _source(ntfy_entry)
    assert ntfy_entry.runtime_data.alarm.alarms_total == 0
    assert source.ignored_restored_total == 1
    assert source.ignored_duplicate_total == 1


@pytest.mark.parametrize("age", [timedelta(hours=2), timedelta(seconds=1)])
async def test_value_after_the_restore_placeholder_is_no_alarm(
    hass: HomeAssistant,
    frozen: FrozenDateTimeFactory,
    ntfy_entry: MockConfigEntry,
    age: timedelta,
) -> None:
    """After the placeholder of the registry the value is the restored one."""
    await async_setup_entry(hass, ntfy_entry)
    hass.states.async_set(NTFY_ENTITY_ID, STATE_UNAVAILABLE, {ATTR_RESTORED: True})
    await hass.async_block_till_done()

    timestamp = fire_ntfy(hass, dt_util.utcnow() - age)
    await hass.async_block_till_done()

    source = _source(ntfy_entry)
    assert ntfy_entry.runtime_data.alarm.alarms_total == 0
    assert source.ignored_restored_total == 1
    # The value counts as seen: coming back with it later is no alarm either.
    hass.states.async_set(NTFY_ENTITY_ID, STATE_UNAVAILABLE)
    fire_ntfy(hass, timestamp)
    await hass.async_block_till_done()
    assert ntfy_entry.runtime_data.alarm.alarms_total == 0


async def test_back_from_unavailable_with_the_same_value(
    hass: HomeAssistant, frozen: FrozenDateTimeFactory, ntfy_entry: MockConfigEntry
) -> None:
    """A lost connection restores the old timestamp: no alarm."""
    timestamp = fire_ntfy(hass)
    await async_setup_entry(hass, ntfy_entry)

    hass.states.async_set(NTFY_ENTITY_ID, STATE_UNAVAILABLE)
    fire_ntfy(hass, timestamp)
    await hass.async_block_till_done()

    source = _source(ntfy_entry)
    assert ntfy_entry.runtime_data.alarm.alarms_total == 0
    assert source.ignored_duplicate_total == 1


async def test_new_message_directly_after_unavailable(
    hass: HomeAssistant, frozen: FrozenDateTimeFactory, ntfy_entry: MockConfigEntry
) -> None:
    """A message right after a reconnect goes from unavailable to the new value."""
    first = fire_ntfy(hass, dt_util.utcnow() - timedelta(minutes=5))
    await async_setup_entry(hass, ntfy_entry)
    hass.states.async_set(NTFY_ENTITY_ID, STATE_UNAVAILABLE)
    await hass.async_block_till_done()

    frozen.tick(timedelta(seconds=10))
    second = fire_ntfy(hass)
    await hass.async_block_till_done()

    assert second != first
    alarm = ntfy_entry.runtime_data.alarm
    assert (alarm.alarms_total, alarm.last_alarm) == (1, second)


async def test_first_message_of_a_new_subscription(
    hass: HomeAssistant, frozen: FrozenDateTimeFactory, ntfy_entry: MockConfigEntry
) -> None:
    """A new subscription is unknown; its first message is an alarm."""
    hass.states.async_set(NTFY_ENTITY_ID, STATE_UNKNOWN)
    await async_setup_entry(hass, ntfy_entry)

    fire_ntfy(hass)
    await hass.async_block_till_done()

    assert ntfy_entry.runtime_data.alarm.alarms_total == 1


async def test_old_unseen_value_after_unavailable_is_stale(
    hass: HomeAssistant, frozen: FrozenDateTimeFactory, ntfy_entry: MockConfigEntry
) -> None:
    """An old value the listener has never seen is not an alarm."""
    hass.states.async_set(NTFY_ENTITY_ID, STATE_UNAVAILABLE)
    await async_setup_entry(hass, ntfy_entry)

    fire_ntfy(hass, dt_util.utcnow() - timedelta(seconds=61))
    await hass.async_block_till_done()

    source = _source(ntfy_entry)
    assert ntfy_entry.runtime_data.alarm.alarms_total == 0
    assert source.ignored_stale_total == 1


async def test_unseen_value_within_the_window_is_an_alarm(
    hass: HomeAssistant, frozen: FrozenDateTimeFactory, ntfy_entry: MockConfigEntry
) -> None:
    """The documented rest risk: an unseen value younger than 60 s counts."""
    hass.states.async_set(NTFY_ENTITY_ID, STATE_UNAVAILABLE)
    await async_setup_entry(hass, ntfy_entry)

    fire_ntfy(hass, dt_util.utcnow() - timedelta(seconds=30))
    await hass.async_block_till_done()

    assert ntfy_entry.runtime_data.alarm.alarms_total == 1


async def test_attribute_change_is_no_alarm(
    hass: HomeAssistant, frozen: FrozenDateTimeFactory, ntfy_entry: MockConfigEntry
) -> None:
    """Only a new timestamp is a message; changed attributes are not."""
    timestamp = fire_ntfy(hass)
    await async_setup_entry(hass, ntfy_entry)

    fire_ntfy(hass, timestamp, {"priority": 5})
    await hass.async_block_till_done()

    assert ntfy_entry.runtime_data.alarm.alarms_total == 0
    assert _source(ntfy_entry).ignored_duplicate_total == 1


@pytest.mark.parametrize("value", ["abc", "2026-10-17T12:00:00"])
async def test_invalid_state_is_ignored(
    hass: HomeAssistant,
    frozen: FrozenDateTimeFactory,
    ntfy_entry: MockConfigEntry,
    value: str,
) -> None:
    """A state that is no timestamp with time zone is ignored without an error."""
    fire_ntfy(hass, dt_util.utcnow() - timedelta(hours=1))
    await async_setup_entry(hass, ntfy_entry)

    hass.states.async_set(NTFY_ENTITY_ID, value)
    await hass.async_block_till_done()

    source = _source(ntfy_entry)
    assert ntfy_entry.runtime_data.alarm.alarms_total == 0
    assert (source.events_total, source.accepted_total) == (1, 0)


async def test_invalid_state_at_the_start(
    hass: HomeAssistant, frozen: FrozenDateTimeFactory, ntfy_entry: MockConfigEntry
) -> None:
    """An invalid current state gives no base value; the next message counts."""
    hass.states.async_set(NTFY_ENTITY_ID, "abc")
    await async_setup_entry(hass, ntfy_entry)

    fire_ntfy(hass)
    await hass.async_block_till_done()

    assert ntfy_entry.runtime_data.alarm.alarms_total == 1


async def test_timestamp_in_the_future_is_fresh(
    hass: HomeAssistant, frozen: FrozenDateTimeFactory, ntfy_entry: MockConfigEntry
) -> None:
    """Like in the alarm manager, a timestamp ahead of the clock counts as fresh."""
    fire_ntfy(hass, dt_util.utcnow() - timedelta(hours=1))
    await async_setup_entry(hass, ntfy_entry)

    fire_ntfy(hass, dt_util.utcnow() + timedelta(minutes=5))
    await hass.async_block_till_done()

    assert ntfy_entry.runtime_data.alarm.alarms_total == 1


async def test_two_messages_within_the_dedup_window(
    hass: HomeAssistant, frozen: FrozenDateTimeFactory, ntfy_entry: MockConfigEntry
) -> None:
    """Two webhooks of FF Agent on the same topic: one alarm, one repetition."""
    fire_ntfy(hass, dt_util.utcnow() - timedelta(hours=1))
    await async_setup_entry(hass, ntfy_entry)

    fire_ntfy(hass)
    frozen.tick(timedelta(seconds=20))
    fire_ntfy(hass)
    await hass.async_block_till_done()

    alarm = ntfy_entry.runtime_data.alarm
    assert (alarm.alarms_total, alarm.deduplicated_total) == (1, 1)
    assert _source(ntfy_entry).accepted_total == 2


async def test_same_state_written_again_is_no_alarm(
    hass: HomeAssistant, frozen: FrozenDateTimeFactory, ntfy_entry: MockConfigEntry
) -> None:
    """The current state at the start is the base value."""
    timestamp = fire_ntfy(hass)
    state = hass.states.get(NTFY_ENTITY_ID)
    assert state is not None
    await async_setup_entry(hass, ntfy_entry)

    hass.states.async_set(
        NTFY_ENTITY_ID, state.state, state.attributes, force_update=True
    )
    await hass.async_block_till_done()

    assert ntfy_entry.runtime_data.alarm.alarms_total == 0
    assert ntfy_entry.runtime_data.alarm.last_alarm is None
    assert _source(ntfy_entry).ignored_duplicate_total == 1
    assert state.state == timestamp.isoformat(timespec="milliseconds")


async def test_shape_of_the_message_is_kept_without_values(
    hass: HomeAssistant, frozen: FrozenDateTimeFactory, ntfy_entry: MockConfigEntry
) -> None:
    """Only lengths and counts are kept, never the text."""
    fire_ntfy(hass, dt_util.utcnow() - timedelta(hours=1))
    await async_setup_entry(hass, ntfy_entry)

    fire_ntfy(
        hass,
        dt_util.utcnow() - timedelta(seconds=2),
        {"message": "Text-Placeholder", "title": "Title-Placeholder", "tags": ["a"]},
    )
    await hass.async_block_till_done()

    shape = _source(ntfy_entry).last_event
    assert shape is not None
    assert shape.as_diagnostics() == {
        "received_at": "2026-10-17T11:59:58+00:00",
        "age_seconds": 2.0,
        "message_length": 16,
        "has_title": True,
        "tags_count": 1,
    }


async def test_unexpected_attribute_types_give_an_empty_shape(
    hass: HomeAssistant, frozen: FrozenDateTimeFactory, ntfy_entry: MockConfigEntry
) -> None:
    """A message as number, a title that is no text and no tags: no error."""
    fire_ntfy(hass, dt_util.utcnow() - timedelta(hours=1))
    await async_setup_entry(hass, ntfy_entry)

    timestamp = dt_util.utcnow()
    hass.states.async_set(
        NTFY_ENTITY_ID,
        timestamp.isoformat(timespec="milliseconds"),
        {"message": 42, "title": 7},
    )
    await hass.async_block_till_done()

    shape = _source(ntfy_entry).last_event
    assert shape is not None
    assert (shape.message_length, shape.has_title, shape.tags_count) == (
        None,
        False,
        None,
    )
    assert ntfy_entry.runtime_data.alarm.alarms_total == 1


async def test_no_alarm_after_unload(
    hass: HomeAssistant, frozen: FrozenDateTimeFactory, ntfy_entry: MockConfigEntry
) -> None:
    """After unloading no listener is left."""
    fire_ntfy(hass, dt_util.utcnow() - timedelta(hours=1))
    await async_setup_entry(hass, ntfy_entry)
    source = _source(ntfy_entry)
    alarm = ntfy_entry.runtime_data.alarm
    assert source.running

    assert await hass.config_entries.async_unload(ntfy_entry.entry_id)
    await hass.async_block_till_done()
    fire_ntfy(hass)
    await hass.async_block_till_done()

    assert not source.running
    assert source.events_total == 0
    assert alarm.alarms_total == 0
    # Stopping twice is no error.
    source.async_stop()


# --- Setup, registry changes and the repair issue -----------------------


async def test_ntfy_mode_registers_no_webhook(
    hass: HomeAssistant, ntfy_entry: MockConfigEntry
) -> None:
    """An entry has exactly one entrance: in ntfy mode the webhook stays closed."""
    with patch(
        "homeassistant.components.webhook.async_register", wraps=webhook.async_register
    ) as register:
        await async_setup_entry(hass, ntfy_entry)

    register.assert_not_called()
    request = MockRequest(b"", "test", method="POST")
    response = await webhook.async_handle_webhook(hass, WEBHOOK_ID, request)
    await hass.async_block_till_done()
    assert response.status == HTTPStatus.OK
    assert ntfy_entry.runtime_data.alarm.calls_total == 0
    assert ntfy_entry.runtime_data.alarm.alarms_total == 0
    assert _issue(hass, ntfy_entry) is None


async def test_removed_entity_creates_the_repair_issue(
    hass: HomeAssistant, frozen: FrozenDateTimeFactory, ntfy_entry: MockConfigEntry
) -> None:
    """Removing the ntfy entity stops the listener and tells the user."""
    await async_setup_entry(hass, ntfy_entry)
    source = _source(ntfy_entry)

    er.async_get(hass).async_remove(NTFY_ENTITY_ID)
    await hass.async_block_till_done()

    issue = _issue(hass, ntfy_entry)
    assert issue is not None
    assert issue.translation_key == "ntfy_entity_missing"
    assert issue.severity is ir.IssueSeverity.ERROR
    assert not issue.is_fixable
    assert issue.translation_placeholders == {"title": ntfy_entry.title}
    assert not source.running
    fire_ntfy(hass, dt_util.utcnow() - timedelta(hours=1))
    fire_ntfy(hass)
    await hass.async_block_till_done()
    assert ntfy_entry.runtime_data.alarm.alarms_total == 0
    assert ntfy_entry.state is ConfigEntryState.LOADED


async def test_renamed_entity_reloads_and_keeps_working(
    hass: HomeAssistant, frozen: FrozenDateTimeFactory, ntfy_entry: MockConfigEntry
) -> None:
    """A new entity ID reloads the entry, which then listens to the new ID."""
    fire_ntfy(hass, dt_util.utcnow() - timedelta(hours=1))
    await async_setup_entry(hass, ntfy_entry)
    old_alarm = ntfy_entry.runtime_data.alarm

    er.async_get(hass).async_update_entity(
        NTFY_ENTITY_ID, new_entity_id=OTHER_NTFY_ENTITY_ID
    )
    await hass.async_block_till_done()

    assert ntfy_entry.state is ConfigEntryState.LOADED
    assert ntfy_entry.runtime_data.alarm is not old_alarm
    old = dt_util.utcnow() - timedelta(hours=1)
    fire_ntfy(hass, old, entity_id=OTHER_NTFY_ENTITY_ID)
    await hass.async_block_till_done()
    fire_ntfy(hass, entity_id=OTHER_NTFY_ENTITY_ID)
    await hass.async_block_till_done()
    assert ntfy_entry.runtime_data.alarm.alarms_total == 1


async def test_other_registry_updates_do_not_reload(
    hass: HomeAssistant, ntfy_entry: MockConfigEntry
) -> None:
    """The ntfy entity changes its capabilities with every message: no reload."""
    await async_setup_entry(hass, ntfy_entry)
    alarm = ntfy_entry.runtime_data.alarm

    er.async_get(hass).async_update_entity(
        NTFY_ENTITY_ID, capabilities={"event_types": ["triggered"]}
    )
    await hass.async_block_till_done()

    assert ntfy_entry.runtime_data.alarm is alarm


async def test_disabled_entity_reloads_and_creates_the_issue(
    hass: HomeAssistant, ntfy_entry: MockConfigEntry
) -> None:
    """Disabling the ntfy entity reloads the entry, which then reports it."""
    await async_setup_entry(hass, ntfy_entry)
    assert _issue(hass, ntfy_entry) is None

    er.async_get(hass).async_update_entity(
        NTFY_ENTITY_ID, disabled_by=er.RegistryEntryDisabler.USER
    )
    await hass.async_block_till_done()

    assert ntfy_entry.state is ConfigEntryState.LOADED
    assert ntfy_entry.runtime_data.source is None
    assert _issue(hass, ntfy_entry) is not None

    # Enabled again: the reload removes the issue.
    er.async_get(hass).async_update_entity(NTFY_ENTITY_ID, disabled_by=None)
    await hass.async_block_till_done()
    assert ntfy_entry.runtime_data.source is not None
    assert _issue(hass, ntfy_entry) is None


@pytest.mark.parametrize("case", ["unknown uuid", "other platform", "no uuid"])
async def test_setup_without_a_valid_entity(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    ntfy_entry: MockConfigEntry,
    case: str,
) -> None:
    """The setup works and the buttons work; the repair issue tells the user."""
    uuid: str | None = "0123456789abcdef0123456789abcdef"
    if case == "other platform":
        uuid = er.async_get(hass).async_get_or_create("event", "demo", "x").id
    elif case == "no uuid":
        uuid = None
    aioclient_mock.get(ACCEPT_URL)

    await _setup_with_uuid(hass, ntfy_entry, uuid)

    assert ntfy_entry.state is ConfigEntryState.LOADED
    assert ntfy_entry.runtime_data.source is None
    assert _issue(hass, ntfy_entry) is not None
    button = er.async_get(hass).async_get_entity_id(
        "button", DOMAIN, f"{ntfy_entry.entry_id}_accept"
    )
    await hass.services.async_call(
        "button", "press", {"entity_id": button}, blocking=True
    )
    assert aioclient_mock.call_count == 1


async def test_setup_with_a_valid_entity_removes_the_issue(
    hass: HomeAssistant, ntfy_entry: MockConfigEntry
) -> None:
    """Once the entry has a valid entity again, the issue disappears."""
    uuid = ntfy_entry.data[CONF_NTFY_ENTITY_UUID]
    await _setup_with_uuid(hass, ntfy_entry, "missing")
    assert _issue(hass, ntfy_entry) is not None

    assert await hass.config_entries.async_unload(ntfy_entry.entry_id)
    hass.config_entries.async_update_entry(
        ntfy_entry, data={**ntfy_entry.data, CONF_NTFY_ENTITY_UUID: uuid}
    )
    assert await hass.config_entries.async_setup(ntfy_entry.entry_id)
    await hass.async_block_till_done()

    assert _issue(hass, ntfy_entry) is None
    assert ntfy_entry.runtime_data.source is not None


async def test_removing_the_entry_removes_the_issue(
    hass: HomeAssistant, ntfy_entry: MockConfigEntry
) -> None:
    """The hint does not outlive its entry."""
    await _setup_with_uuid(hass, ntfy_entry, "missing")
    assert _issue(hass, ntfy_entry) is not None

    await hass.config_entries.async_remove(ntfy_entry.entry_id)

    assert _issue(hass, ntfy_entry) is None


async def test_webhook_mode_removes_a_leftover_ntfy_issue(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Back on the webhook, the hint about the ntfy entity is obsolete."""
    mock_config_entry.add_to_hass(hass)
    issue_id = ISSUE_NTFY_ENTITY_MISSING.format(entry_id=mock_config_entry.entry_id)
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        severity=ir.IssueSeverity.ERROR,
        translation_key="ntfy_entity_missing",
        translation_placeholders={"title": mock_config_entry.title},
    )

    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None


async def test_listener_logs_neither_topic_nor_entity_id(
    hass: HomeAssistant,
    frozen: FrozenDateTimeFactory,
    ntfy_entry: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Only the reason is logged, never the topic or the entity ID."""
    caplog.set_level(logging.DEBUG, logger="custom_components.ff_agent")
    await async_setup_entry(hass, ntfy_entry)
    hass.states.async_set(NTFY_ENTITY_ID, STATE_UNAVAILABLE, {ATTR_RESTORED: True})
    fire_ntfy(hass, dt_util.utcnow() - timedelta(hours=1))
    hass.states.async_set(NTFY_ENTITY_ID, STATE_UNAVAILABLE)
    fire_ntfy(hass, dt_util.utcnow() - timedelta(hours=2))
    fire_ntfy(hass)
    hass.states.async_set(NTFY_ENTITY_ID, "abc")
    await hass.async_block_till_done()

    ours = "\n".join(
        record.getMessage()
        for record in caplog.records
        if record.name.startswith("custom_components.ff_agent")
    )
    for message in (
        "ntfy event ignored: no timestamp",
        "ntfy event ignored: restored",
        "ntfy event ignored: stale",
        "ntfy event accepted",
        "Alarm recognized",
    ):
        assert message in ours
    assert NTFY_TOPIC not in ours
    assert NTFY_ENTITY_ID not in ours
