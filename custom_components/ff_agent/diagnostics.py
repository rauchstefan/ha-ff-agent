"""Diagnostics for the FF Agent integration.

Secrets (reply ID, webhook ID, cloudhook URL, token, ntfy topic, the registry UUID
and the entity ID of the ntfy entity), the title and the location entity are
redacted. Of the last webhook call and the last ntfy message only the shape is
available, of the last reply only the outcome: no address, no coordinates.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .alarm import AlarmManager
from .const import (
    CONF_ALARM_SOURCE,
    CONF_NTFY_ENTITY_UUID,
    CONF_NTFY_SERVER,
    CONF_REQUIRE_TOKEN,
    DEDUP_SECONDS,
    NTFY_DOMAIN,
    REPLY_REPEAT_GUARD_SECONDS,
    SOURCE_NTFY,
    SOURCE_WEBHOOK,
    TO_REDACT,
    WEBHOOK_ALLOWED_METHODS,
)
from .models import FFAgentConfigEntry, FFAgentData
from .reply import ReplyClient
from .webhook_url import async_get_webhook_url


def _stats(alarm: AlarmManager | None) -> dict[str, Any] | None:
    """Return the webhook counters and the shape of the last call."""
    if alarm is None:
        return None
    return {
        "calls_total": alarm.calls_total,
        "rejected_total": alarm.rejected_total,
        "last_call": alarm.last_call.as_diagnostics() if alarm.last_call else None,
    }


def _alarm(alarm: AlarmManager | None) -> dict[str, Any] | None:
    """Return the state and the counters of the alarm logic."""
    if alarm is None:
        return None
    return {
        "active": alarm.active,
        "last_alarm": alarm.last_alarm.isoformat() if alarm.last_alarm else None,
        "active_until": alarm.active_until.isoformat() if alarm.active_until else None,
        "alarms_total": alarm.alarms_total,
        "deduplicated_total": alarm.deduplicated_total,
        "dedup_seconds": DEDUP_SECONDS,
        "reset_minutes": alarm.reset_minutes,
    }


def _reply(reply: ReplyClient | None) -> dict[str, Any] | None:
    """Return the counters and the last result of the replies, never an address."""
    if reply is None:
        return None
    last = reply.last_result
    return {
        "attempts_total": reply.attempts_total,
        "succeeded_total": reply.succeeded_total,
        "failed_total": reply.failed_total,
        "skipped_total": reply.skipped_total,
        "repeat_guard_seconds": REPLY_REPEAT_GUARD_SECONDS,
        "last_result": last.as_diagnostics() if last else None,
    }


def _webhook(hass: HomeAssistant, entry: FFAgentConfigEntry) -> dict[str, Any]:
    """Return the kind of the webhook URL, never the URL itself."""
    _, url_kind = async_get_webhook_url(hass, entry)
    return {
        "url_kind": str(url_kind),
        "allowed_methods": list(WEBHOOK_ALLOWED_METHODS),
        "require_token": entry.options.get(CONF_REQUIRE_TOKEN, False),
    }


def _ntfy(
    hass: HomeAssistant, entry: FFAgentConfigEntry, runtime_data: FFAgentData | None
) -> dict[str, Any]:
    """Return the state of the ntfy entity and the listener, never an identifier."""
    uuid = entry.data.get(CONF_NTFY_ENTITY_UUID)
    registry = er.async_get(hass)
    entity_id = er.async_resolve_entity_id(registry, uuid) if uuid else None
    registry_entry = registry.async_get(entity_id) if entity_id else None

    platform_ok = False
    disabled: bool | None = None
    available: bool | None = None
    if registry_entry is not None:
        platform_ok = (
            registry_entry.platform == NTFY_DOMAIN and registry_entry.domain == "event"
        )
        disabled = registry_entry.disabled
        state = hass.states.get(registry_entry.entity_id)
        available = state is not None and state.state != STATE_UNAVAILABLE

    result: dict[str, Any] = {
        "entity_found": registry_entry is not None,
        "entity_platform_ok": platform_ok,
        "entity_disabled": disabled,
        "entity_available": available,
        "server": entry.data.get(CONF_NTFY_SERVER),
    }
    if runtime_data is not None and runtime_data.source is not None:
        result.update(runtime_data.source.as_diagnostics())
    return result


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: FFAgentConfigEntry
) -> dict[str, Any]:
    """Return the redacted diagnostics of a config entry."""
    source = entry.data.get(CONF_ALARM_SOURCE, SOURCE_WEBHOOK)
    # Not loaded (e.g. disabled or failed): there is no runtime data.
    runtime_data: FFAgentData | None = getattr(entry, "runtime_data", None)
    alarm = runtime_data.alarm if runtime_data else None
    reply = runtime_data.reply if runtime_data else None

    return {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "alarm_source": source,
        "webhook": _webhook(hass, entry) if source == SOURCE_WEBHOOK else None,
        "ntfy": _ntfy(hass, entry, runtime_data) if source == SOURCE_NTFY else None,
        "stats": _stats(alarm),
        "alarm": _alarm(alarm),
        "reply": _reply(reply),
    }
