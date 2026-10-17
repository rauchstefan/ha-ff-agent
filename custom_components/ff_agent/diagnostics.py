"""Diagnostics for the FF Agent integration.

Secrets (reply ID, webhook ID, cloudhook URL, token), the title and the location
entity are redacted. Of the last webhook call only the shape is available.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .const import CONF_REQUIRE_TOKEN, TO_REDACT, WEBHOOK_ALLOWED_METHODS
from .models import FFAgentConfigEntry, WebhookStats
from .webhook_url import async_get_webhook_url


def _stats(stats: WebhookStats | None) -> dict[str, Any] | None:
    """Return the counters and the shape of the last call."""
    if stats is None:
        return None
    return {
        "calls_total": stats.calls_total,
        "rejected_total": stats.rejected_total,
        "last_call": stats.last_call.as_diagnostics() if stats.last_call else None,
    }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: FFAgentConfigEntry
) -> dict[str, Any]:
    """Return the redacted diagnostics of a config entry."""
    # Only the kind of the URL is reported, never the URL itself.
    _, url_kind = async_get_webhook_url(hass, entry)
    # Not loaded (e.g. disabled or failed): there is no runtime data.
    runtime_data = getattr(entry, "runtime_data", None)
    stats = runtime_data.webhook_stats if runtime_data else None

    return {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "webhook": {
            "url_kind": str(url_kind),
            "allowed_methods": list(WEBHOOK_ALLOWED_METHODS),
            "require_token": entry.options.get(CONF_REQUIRE_TOKEN, False),
        },
        "stats": _stats(stats),
    }
