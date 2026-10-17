"""The FF Agent integration."""

from __future__ import annotations

from contextlib import suppress

# Aliased: "webhook" would clash with the submodule .webhook of this package.
from homeassistant.components import webhook as ha_webhook
from homeassistant.const import CONF_WEBHOOK_ID, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.typing import ConfigType

from .alarm import AlarmManager
from .const import (
    CONF_CLOUDHOOK,
    CONF_REPLY_HOST,
    CONF_REPLY_ID,
    CONF_RESET_MINUTES,
    DEFAULT_RESET_MINUTES,
    DOMAIN,
    ISSUE_TOKEN_REJECTED,
    WEBHOOK_ALLOWED_METHODS,
)
from .models import FFAgentConfigEntry, FFAgentData
from .reply import ReplyClient
from .services import async_setup_services
from .webhook import async_build_handler

# The integration is set up through config entries only.
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.EVENT,
    Platform.SENSOR,
]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the actions once; they work on the entry that is named in the call."""
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: FFAgentConfigEntry) -> bool:
    """Set up FF Agent from a config entry."""
    alarm = AlarmManager(
        hass,
        entry.entry_id,
        entry.options.get(CONF_RESET_MINUTES, DEFAULT_RESET_MINUTES),
    )
    reply = ReplyClient(
        hass, entry.entry_id, entry.data[CONF_REPLY_HOST], entry.data[CONF_REPLY_ID]
    )
    entry.runtime_data = FFAgentData(alarm=alarm, reply=reply)
    entry.async_on_unload(alarm.async_shutdown)

    # FF Agent calls from the internet, so the webhook must not be local only. GET and
    # POST are exactly the methods a generic webhook in FF Agent offers.
    webhook_id = entry.data[CONF_WEBHOOK_ID]
    ha_webhook.async_register(
        hass,
        DOMAIN,
        entry.title,
        webhook_id,
        async_build_handler(entry),
        local_only=False,
        allowed_methods=list(WEBHOOK_ALLOWED_METHODS),
    )
    entry.async_on_unload(lambda: ha_webhook.async_unregister(hass, webhook_id))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: FFAgentConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: FFAgentConfigEntry) -> None:
    """Clean up after a removed config entry: repair issue and cloudhook."""
    ir.async_delete_issue(
        hass, DOMAIN, ISSUE_TOKEN_REJECTED.format(entry_id=entry.entry_id)
    )

    if entry.data.get(CONF_CLOUDHOOK) and "cloud" in hass.config.components:
        # Lazy import: the cloud integration is only an optional (after) dependency.
        from homeassistant.components import cloud

        with suppress(cloud.CloudNotAvailable, ValueError):
            await cloud.async_delete_cloudhook(hass, entry.data[CONF_WEBHOOK_ID])
