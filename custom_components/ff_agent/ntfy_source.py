"""The alarm source ntfy (ADR 0003).

FF Agent publishes to an ntfy topic, the core integration ntfy subscribes to it and
shows each message as an event entity. This module finds that entity and listens to
it. It has no ntfy client of its own and makes no network request.

The topic and the entity ID are secrets: whoever knows the topic sees the alarm times
and can send false alarms, and the entity ID contains the topic if the subscription
has no display name. Neither is ever logged.
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta
from typing import Any

from homeassistant.const import ATTR_RESTORED, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import (
    CALLBACK_TYPE,
    Event,
    EventStateChangedData,
    HomeAssistant,
    State,
    callback,
)
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import dt as dt_util

from .alarm import AlarmManager
from .const import (
    NTFY_CONF_TOPIC,
    NTFY_CONF_URL,
    NTFY_DEFAULT_SERVER,
    NTFY_DOMAIN,
    NTFY_MAX_EVENT_AGE_SECONDS,
    NTFY_SUBENTRY_TYPE,
    NTFY_TOPIC_BYTES,
)
from .models import NtfyEventShape, NtfySubscription

_LOGGER = logging.getLogger(__name__)

EVENT_DOMAIN = "event"
MAX_EVENT_AGE = timedelta(seconds=NTFY_MAX_EVENT_AGE_SECONDS)


def async_generate_topic() -> str:
    """Return a new random topic: 32 hex characters, without a telling prefix."""
    return secrets.token_hex(NTFY_TOPIC_BYTES)


def ntfy_publish_url(server: str | None, topic: str) -> str:
    """Return the URL FF Agent calls with GET. It contains the secret topic."""
    return f"{(server or NTFY_DEFAULT_SERVER).rstrip('/')}/{topic}/trigger"


@callback
def async_describe_entity(
    hass: HomeAssistant, entity_id_or_uuid: str
) -> NtfySubscription | None:
    """Return the subscription behind an ntfy event entity.

    None if the entity does not exist, is not an event entity of the integration ntfy
    or is disabled. Topic and server are None if they cannot be read; that is no
    error, because only the entity is needed to receive alarms.
    """
    registry = er.async_get(hass)
    entity_id = er.async_resolve_entity_id(registry, entity_id_or_uuid)
    if entity_id is None:
        return None
    entry = registry.async_get(entity_id)
    if (
        entry is None
        or entry.platform != NTFY_DOMAIN
        or entry.domain != EVENT_DOMAIN
        or entry.disabled
    ):
        return None

    topic: str | None = None
    server: str | None = None
    config_entry = (
        hass.config_entries.async_get_entry(entry.config_entry_id)
        if entry.config_entry_id
        else None
    )
    if config_entry is not None:
        if isinstance(url := config_entry.data.get(NTFY_CONF_URL), str):
            server = url
        subentry = (
            config_entry.subentries.get(entry.config_subentry_id)
            if entry.config_subentry_id
            else None
        )
        if subentry is not None and subentry.subentry_type == NTFY_SUBENTRY_TYPE:
            if isinstance(value := subentry.data.get(NTFY_CONF_TOPIC), str):
                topic = value

    return NtfySubscription(
        entity_id=entry.entity_id, entity_uuid=entry.id, topic=topic, server=server
    )


@callback
def async_find_subscription_by_topic(
    hass: HomeAssistant, topic: str
) -> NtfySubscription | None:
    """Return the enabled ntfy event entity that subscribes to the topic, if any."""
    registry = er.async_get(hass)
    for config_entry in hass.config_entries.async_entries(NTFY_DOMAIN):
        for subentry_id, subentry in config_entry.subentries.items():
            if (
                subentry.subentry_type != NTFY_SUBENTRY_TYPE
                or subentry.data.get(NTFY_CONF_TOPIC) != topic
            ):
                continue
            for entry in er.async_entries_for_config_entry(
                registry, config_entry.entry_id
            ):
                if (
                    entry.config_subentry_id == subentry_id
                    and entry.domain == EVENT_DOMAIN
                    and (found := async_describe_entity(hass, entry.id)) is not None
                ):
                    return found
    return None


def _timestamp(state: State) -> datetime | None:
    """Return the timestamp of an event entity state, None if it has none."""
    if state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
        return None
    timestamp = dt_util.parse_datetime(state.state)
    if timestamp is None or timestamp.tzinfo is None:
        return None
    return timestamp


def _event_shape(state: State, received_at: datetime, age: timedelta) -> NtfyEventShape:
    """Return the shape of an ntfy message: lengths and counts, never a value."""
    message = state.attributes.get("message")
    title = state.attributes.get("title")
    tags = state.attributes.get("tags")
    return NtfyEventShape(
        received_at=received_at,
        age_seconds=round(age.total_seconds(), 3),
        message_length=len(message) if isinstance(message, str) else None,
        has_title=isinstance(title, str) and bool(title),
        tags_count=len(tags) if isinstance(tags, list | tuple) else None,
    )


class NtfyAlarmSource:
    """Turn new messages of an ntfy event entity into alarms (ADR 0003, 3.).

    The entity of another integration switches to unavailable on every restart,
    reload and lost connection and then restores its old timestamp. Only a new and
    fresh timestamp is an alarm. Apart from the search, nothing here knows ntfy: the
    rules only rely on the semantics of an event entity.
    """

    def __init__(
        self, hass: HomeAssistant, alarm: AlarmManager, entity_id: str
    ) -> None:
        """Initialize the listener for one event entity."""
        self._hass = hass
        self._alarm = alarm
        self._entity_id = entity_id
        self._seen: datetime | None = None
        self._unsub: CALLBACK_TYPE | None = None

        self.events_total = 0
        self.accepted_total = 0
        self.ignored_restored_total = 0
        self.ignored_stale_total = 0
        self.ignored_duplicate_total = 0
        self.last_event: NtfyEventShape | None = None

    @property
    def running(self) -> bool:
        """Return whether the listener is active."""
        return self._unsub is not None

    @callback
    def async_start(self) -> None:
        """Take the current state as seen and start listening."""
        if (state := self._hass.states.get(self._entity_id)) is not None:
            self._seen = _timestamp(state)
        self._unsub = async_track_state_change_event(
            self._hass, [self._entity_id], self._async_handle
        )

    @callback
    def async_stop(self) -> None:
        """Stop listening. Calling it twice is no error."""
        if self._unsub is not None:
            self._unsub()
            self._unsub = None

    @callback
    def _async_handle(self, event: Event[EventStateChangedData]) -> None:
        """Apply the rules 1 to 6 of ADR 0003, section 3, in this order."""
        self.events_total += 1
        new_state = event.data["new_state"]
        old_state = event.data["old_state"]

        # Rules 1 and 2: no state, unavailable, unknown or no timestamp.
        if new_state is None or (timestamp := _timestamp(new_state)) is None:
            _LOGGER.debug("ntfy event ignored: no timestamp")
            return

        # Rule 3: the entity was just added (again); its value is the restored one.
        if old_state is None or old_state.attributes.get(ATTR_RESTORED):
            self._seen = timestamp
            self.ignored_restored_total += 1
            _LOGGER.debug("ntfy event ignored: restored")
            return

        # Rule 4: back from unavailable with the old value, or only attributes changed.
        if timestamp == self._seen:
            self.ignored_duplicate_total += 1
            _LOGGER.debug("ntfy event ignored: already seen")
            return

        # Rule 5: an old value that was not seen before. A timestamp in the future
        # counts as fresh, like in the alarm manager.
        self._seen = timestamp
        age = dt_util.utcnow() - timestamp
        if age > MAX_EVENT_AGE:
            self.ignored_stale_total += 1
            _LOGGER.debug("ntfy event ignored: stale")
            return

        # Rule 6: a new alarm. The alarm manager deduplicates repetitions.
        self.accepted_total += 1
        self.last_event = _event_shape(new_state, timestamp, age)
        _LOGGER.debug("ntfy event accepted")
        self._alarm.async_handle_alarm(timestamp)

    def as_diagnostics(self) -> dict[str, Any]:
        """Return counters and the shape of the last accepted message."""
        return {
            "running": self.running,
            "events_total": self.events_total,
            "accepted_total": self.accepted_total,
            "ignored_restored_total": self.ignored_restored_total,
            "ignored_stale_total": self.ignored_stale_total,
            "ignored_duplicate_total": self.ignored_duplicate_total,
            "last_event": self.last_event.as_diagnostics() if self.last_event else None,
        }
