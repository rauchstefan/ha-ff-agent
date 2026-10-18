"""The FF Agent integration."""

from __future__ import annotations

import logging

# Aliased: "webhook" would clash with the submodule .webhook of this package.
from homeassistant.components import webhook as ha_webhook
from homeassistant.const import CONF_WEBHOOK_ID, Platform
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.event import async_track_entity_registry_updated_event
from homeassistant.helpers.typing import ConfigType

from .alarm import AlarmManager
from .const import (
    CONF_ALARM_SOURCE,
    CONF_CLOUDHOOK,
    CONF_NTFY_ENTITY_UUID,
    CONF_NTFY_SERVER,
    CONF_NTFY_TOPIC,
    CONF_REPLY_HOST,
    CONF_REPLY_ID,
    CONF_REQUIRE_TOKEN,
    CONF_RESET_MINUTES,
    DEFAULT_RESET_MINUTES,
    DOMAIN,
    ISSUE_NTFY_ENTITY_MISSING,
    ISSUE_TOKEN_REJECTED,
    SOURCE_NTFY,
    SOURCE_WEBHOOK,
    WEBHOOK_ALLOWED_METHODS,
)
from .models import FFAgentConfigEntry, FFAgentData, NtfySubscription
from .ntfy_source import (
    NtfyAlarmSource,
    async_describe_entity,
    async_find_subscription_by_topic,
)
from .reply import ReplyClient
from .services import async_setup_services
from .webhook import async_build_handler
from .webhook_url import async_delete_cloudhook

_LOGGER = logging.getLogger(__name__)

# The integration is set up through config entries only.
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.EVENT,
    Platform.SENSOR,
]

# Registry changes of the ntfy entity that need a reload: a new entity ID or a
# change of "disabled". Others (e.g. the capabilities, which the ntfy entity changes
# with every message) are ignored.
NTFY_RELOAD_CHANGES = frozenset({"entity_id", "disabled_by"})


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the actions once; they work on the entry that is named in the call."""
    async_setup_services(hass)
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: FFAgentConfigEntry) -> bool:
    """Migrate an entry to the current version. Only versions are logged."""
    if entry.version > 1:
        # A downgrade from a future major version.
        _LOGGER.error(
            "Cannot migrate a config entry of version %s.%s",
            entry.version,
            entry.minor_version,
        )
        return False

    if entry.minor_version < 2:
        # 1.1 -> 1.2: the alarm source (ADR 0003). Existing entries use the webhook.
        hass.config_entries.async_update_entry(
            entry,
            data={
                CONF_ALARM_SOURCE: SOURCE_WEBHOOK,
                CONF_NTFY_ENTITY_UUID: None,
                CONF_NTFY_TOPIC: None,
                CONF_NTFY_SERVER: None,
                **entry.data,  # existing values win
            },
            minor_version=2,
        )
        _LOGGER.debug("Migrated a config entry to version 1.2")
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

    source = entry.data.get(CONF_ALARM_SOURCE, SOURCE_WEBHOOK)
    # The hint about a rejected call only makes sense while the webhook is used and
    # the token is required. Switching either off (which reloads the entry) must not
    # leave it behind.
    if source != SOURCE_WEBHOOK or not entry.options.get(CONF_REQUIRE_TOKEN):
        ir.async_delete_issue(
            hass, DOMAIN, ISSUE_TOKEN_REJECTED.format(entry_id=entry.entry_id)
        )

    if source == SOURCE_NTFY:
        # No webhook in ntfy mode: an entry has exactly one open entrance.
        _async_setup_ntfy(hass, entry, alarm)
    else:
        ir.async_delete_issue(
            hass, DOMAIN, ISSUE_NTFY_ENTITY_MISSING.format(entry_id=entry.entry_id)
        )
        # FF Agent calls from the internet, so the webhook must not be local only.
        # GET and POST are exactly the methods a generic webhook in FF Agent offers.
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


@callback
def _async_create_ntfy_issue(hass: HomeAssistant, entry: FFAgentConfigEntry) -> None:
    """Tell the user that the ntfy entity of the entry is missing."""
    ir.async_create_issue(
        hass,
        DOMAIN,
        ISSUE_NTFY_ENTITY_MISSING.format(entry_id=entry.entry_id),
        is_fixable=False,
        is_persistent=False,
        severity=ir.IssueSeverity.ERROR,
        translation_key="ntfy_entity_missing",
        translation_placeholders={"title": entry.title},
    )


@callback
def _async_adopt_subscription(
    hass: HomeAssistant, entry: FFAgentConfigEntry
) -> NtfySubscription | None:
    """Find the subscription of the stored topic and store its entity.

    Subscribing to the topic again creates a new subentry and a new entity, so the
    stored registry UUID is lost. The topic is the same, so the entry finds the new
    entity by it. An entity that another entry uses is not taken.
    """
    topic = entry.data.get(CONF_NTFY_TOPIC)
    if not topic:
        return None
    subscription = async_find_subscription_by_topic(hass, topic)
    if subscription is None or any(
        other.entry_id != entry.entry_id
        and other.data.get(CONF_ALARM_SOURCE) == SOURCE_NTFY
        and other.data.get(CONF_NTFY_ENTITY_UUID) == subscription.entity_uuid
        for other in hass.config_entries.async_entries(DOMAIN)
    ):
        return None
    hass.config_entries.async_update_entry(
        entry,
        data={
            **entry.data,
            CONF_NTFY_ENTITY_UUID: subscription.entity_uuid,
            CONF_NTFY_SERVER: subscription.server or entry.data.get(CONF_NTFY_SERVER),
        },
    )
    _LOGGER.debug("Adopted a new ntfy subscription of the stored topic")
    return subscription


@callback
def _async_watch_for_subscription(
    hass: HomeAssistant, entry: FFAgentConfigEntry
) -> None:
    """Wait for a new entity that subscribes to the stored topic, then reload."""

    @callback
    def _async_registry_created(
        event: Event[er.EventEntityRegistryUpdatedData],
    ) -> None:
        """Adopt a new ntfy entity of the topic and reload the entry."""
        if event.data["action"] != "create":
            return
        if _async_adopt_subscription(hass, entry) is not None:
            hass.config_entries.async_schedule_reload(entry.entry_id)

    entry.async_on_unload(
        hass.bus.async_listen(
            er.EVENT_ENTITY_REGISTRY_UPDATED, _async_registry_created
        )
    )


@callback
def _async_setup_ntfy(
    hass: HomeAssistant, entry: FFAgentConfigEntry, alarm: AlarmManager
) -> None:
    """Listen to the ntfy event entity of the entry.

    A missing, foreign or disabled entity does not fail the setup: replies keep
    working, and a repair issue tells the user what to do.
    """
    uuid = entry.data.get(CONF_NTFY_ENTITY_UUID)
    subscription = async_describe_entity(hass, uuid) if uuid else None
    if subscription is None:
        # A new subscription of the same topic has a new entity: adopt it.
        subscription = _async_adopt_subscription(hass, entry)
        if subscription is not None:
            uuid = subscription.entity_uuid

    registry = er.async_get(hass)
    entity_id = er.async_resolve_entity_id(registry, uuid) if uuid else None
    registry_entry = registry.async_get(entity_id) if entity_id else None

    if registry_entry is not None:

        @callback
        def _async_registry_updated(
            event: Event[er.EventEntityRegistryUpdatedData],
        ) -> None:
            """Follow a removal, a rename or a change of "disabled" of the entity."""
            data = event.data
            if data["action"] == "remove":
                _async_create_ntfy_issue(hass, entry)
                if entry.runtime_data.source is not None:
                    entry.runtime_data.source.async_stop()
                _async_watch_for_subscription(hass, entry)
            elif data["action"] == "update":
                if NTFY_RELOAD_CHANGES.intersection(data["changes"]):
                    hass.config_entries.async_schedule_reload(entry.entry_id)

        entry.async_on_unload(
            async_track_entity_registry_updated_event(
                hass, [registry_entry.entity_id], _async_registry_updated
            )
        )

    if subscription is None:
        _async_create_ntfy_issue(hass, entry)
        _async_watch_for_subscription(hass, entry)
        return

    ir.async_delete_issue(
        hass, DOMAIN, ISSUE_NTFY_ENTITY_MISSING.format(entry_id=entry.entry_id)
    )
    source = NtfyAlarmSource(hass, alarm, subscription.entity_id)
    source.async_start()
    entry.async_on_unload(source.async_stop)
    entry.runtime_data.source = source


async def async_unload_entry(hass: HomeAssistant, entry: FFAgentConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: FFAgentConfigEntry) -> None:
    """Clean up after a removed config entry: repair issues and cloudhook."""
    for issue in (ISSUE_TOKEN_REJECTED, ISSUE_NTFY_ENTITY_MISSING):
        ir.async_delete_issue(hass, DOMAIN, issue.format(entry_id=entry.entry_id))

    if entry.data.get(CONF_CLOUDHOOK):
        await async_delete_cloudhook(hass, entry.data[CONF_WEBHOOK_ID])
