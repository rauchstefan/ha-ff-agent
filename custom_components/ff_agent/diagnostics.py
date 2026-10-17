"""Diagnostics for the FF Agent integration.

Secrets (reply ID, webhook ID, cloudhook URL, token), the title and the location
entity are redacted. Of the last webhook call only the shape is available.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .alarm import AlarmManager
from .const import (
    CONF_REQUIRE_TOKEN,
    DEDUP_SECONDS,
    TO_REDACT,
    WEBHOOK_ALLOWED_METHODS,
)
from .models import FFAgentConfigEntry
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


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: FFAgentConfigEntry
) -> dict[str, Any]:
    """Return the redacted diagnostics of a config entry."""
    # Only the kind of the URL is reported, never the URL itself.
    _, url_kind = async_get_webhook_url(hass, entry)
    # Not loaded (e.g. disabled or failed): there is no runtime data.
    runtime_data = getattr(entry, "runtime_data", None)
    alarm = runtime_data.alarm if runtime_data else None

    return {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "webhook": {
            "url_kind": str(url_kind),
            "allowed_methods": list(WEBHOOK_ALLOWED_METHODS),
            "require_token": entry.options.get(CONF_REQUIRE_TOKEN, False),
        },
        "stats": _stats(alarm),
        "alarm": _alarm(alarm),
    }
