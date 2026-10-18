"""Config flow, reconfigure flow and options flow for the FF Agent integration.

The config flow first asks for the reply URL, then how the alarm reaches Home
Assistant (ADR 0003): through Home Assistant Cloud or an own internet address (a
webhook), or through the free service ntfy. Each path is a guide with numbered steps,
and the user can switch between the paths at any time.
"""

from __future__ import annotations

import logging
import secrets
from typing import Any

import voluptuous as vol
from homeassistant.components import webhook
from homeassistant.config_entries import (
    SOURCE_RECONFIGURE,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_NAME, CONF_WEBHOOK_ID
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.selector import (
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .alarm import clamp_reset_minutes
from .const import (
    ALARM_SOURCES,
    CONF_ALARM_SOURCE,
    CONF_CLOUDHOOK,
    CONF_CLOUDHOOK_URL,
    CONF_DEFAULT_TRANSPORT,
    CONF_HEADER_TOKEN,
    CONF_LOCATION_ENTITY,
    CONF_NTFY_ENTITY,
    CONF_NTFY_ENTITY_UUID,
    CONF_NTFY_SERVER,
    CONF_NTFY_TOPIC,
    CONF_REGENERATE_WEBHOOK,
    CONF_REPLY_HOST,
    CONF_REPLY_ID,
    CONF_REPLY_URL,
    CONF_REQUIRE_TOKEN,
    CONF_RESET_MINUTES,
    DEFAULT_RESET_MINUTES,
    DEFAULT_TRANSPORT,
    DOMAIN,
    ISSUE_NTFY_ENTITY_MISSING,
    ISSUE_TOKEN_REJECTED,
    MAX_RESET_MINUTES,
    MENU_ALARM_SOURCE,
    MENU_CLOUD_NOT_CONNECTED,
    MENU_CLOUD_SETUP,
    MENU_NO_CLOUD,
    MENU_NTFY,
    MIN_RESET_MINUTES,
    MY_CLOUD_URL,
    MY_NETWORK_URL,
    MY_NTFY_INTEGRATION_URL,
    MY_NTFY_SETUP_URL,
    NAME,
    NTFY_CONF_URL,
    NTFY_DEFAULT_SERVER,
    NTFY_DOMAIN,
    NTFY_PUBLISH_URL,
    SOURCE_NTFY,
    SOURCE_WEBHOOK,
    TOKEN_HEADER,
    TRANSPORTS,
)
from .models import NtfySubscription
from .ntfy_source import (
    async_describe_entity,
    async_find_subscription_by_topic,
    async_generate_topic,
    ntfy_publish_url,
)
from .reply import configured_transport
from .reply_url import InvalidReplyUrl, parse_reply_input, reply_unique_id
from .webhook_url import (
    CloudhookUnavailable,
    Reachability,
    UrlKind,
    async_create_webhook_url,
    async_delete_cloudhook,
    async_get_webhook_url,
    async_local_webhook_url,
    async_probe_reachability,
)

_LOGGER = logging.getLogger(__name__)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME, default=NAME): str,
        vol.Required(CONF_REPLY_URL): TextSelector(
            TextSelectorConfig(type=TextSelectorType.TEXT)
        ),
    }
)

# A number box in the UI; the value arrives as float and is stored as int.
RESET_MINUTES_VALIDATOR = vol.All(
    NumberSelector(
        NumberSelectorConfig(
            min=MIN_RESET_MINUTES,
            max=MAX_RESET_MINUTES,
            step=1,
            mode=NumberSelectorMode.BOX,
            unit_of_measurement="min",
        )
    ),
    vol.Coerce(int),
    vol.Range(min=MIN_RESET_MINUTES, max=MAX_RESET_MINUTES),
)

TRANSPORT_SELECTOR = SelectSelector(
    SelectSelectorConfig(options=list(TRANSPORTS), translation_key="transport")
)

LOCATION_SELECTOR = EntitySelector(
    EntitySelectorConfig(domain=["person", "device_tracker"])
)

ALARM_SOURCE_SELECTOR = SelectSelector(
    SelectSelectorConfig(options=list(ALARM_SOURCES), translation_key="alarm_source")
)

# The UI only offers event entities of ntfy; the flow checks the choice again.
NTFY_ENTITY_SELECTOR = EntitySelector(
    EntitySelectorConfig(integration=NTFY_DOMAIN, domain="event")
)

# Kinds of a webhook URL that FF Agent cannot reach from the internet.
UNREACHABLE_KINDS = (UrlKind.INTERNAL, UrlKind.PATH_ONLY)

# Shown instead of the ntfy entity when the entry has none.
NO_VALUE = "–"

# Closing text when the chosen ntfy entity differs from the address the guide showed.
NTFY_OTHER_ADDRESS = "ntfy_other_address"


def _link_placeholders() -> dict[str, str]:
    """Return the My Home Assistant links that the texts use as placeholders."""
    return {
        "cloud_url": MY_CLOUD_URL,
        "network_url": MY_NETWORK_URL,
        "ntfy_setup_url": MY_NTFY_SETUP_URL,
        "ntfy_integration_url": MY_NTFY_INTEGRATION_URL,
    }


def _default_options() -> dict[str, Any]:
    """Return the options of a new entry."""
    return {
        CONF_RESET_MINUTES: DEFAULT_RESET_MINUTES,
        CONF_DEFAULT_TRANSPORT: DEFAULT_TRANSPORT,
        CONF_REQUIRE_TOKEN: False,
    }


def _reconfigure_schema(current_source: str) -> vol.Schema:
    """Return the reconfigure form; the alarm source starts with the current one.

    The reply URL is optional: an empty field means "unchanged". The stored reply URL
    is a secret and is never shown, so the field is never pre-filled.
    """
    return vol.Schema(
        {
            vol.Optional(CONF_REPLY_URL): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT)
            ),
            vol.Required(
                CONF_ALARM_SOURCE, default=current_source
            ): ALARM_SOURCE_SELECTOR,
            vol.Optional(CONF_REGENERATE_WEBHOOK, default=False): BooleanSelector(),
        }
    )


class FFAgentConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow for FF Agent.

    One config entry stands for one person. The flow makes no request to FF Agent,
    because every test call would be a real mission reply. The steps of the alarm
    paths are shared by the config flow and the reconfigure flow; only the closing
    step differs (``self.source``).
    """

    VERSION = 1
    MINOR_VERSION = 2

    def __init__(self) -> None:
        """Initialize the state of the flow."""
        self._name = NAME
        self._reply_data: dict[str, Any] = {}  # reply ID and host of a new entry
        self._reply_updates: dict[str, Any] = {}  # reconfigure: changed reply data
        self._unique_id: str | None = None  # reconfigure: unique ID after the change
        self._webhook_id = ""
        self._header_token = ""
        self._regenerate = False
        self._ntfy_topic: str | None = None
        # The URL for FF Agent that the ntfy guide showed last (a secret, never logged).
        self._shown_ntfy_url: str | None = None
        self._cloud_attempts = 0  # unsuccessful checks in the cloud path

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> FFAgentOptionsFlow:
        """Return the options flow; it reloads the entry when the options change."""
        return FFAgentOptionsFlow()

    @property
    def _reconfiguring(self) -> bool:
        """Return whether the flow changes an existing entry."""
        return self.source == SOURCE_RECONFIGURE

    # --- Setup and the first question -----------------------

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the name and the reply URL; the duplicate check comes first."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                target = parse_reply_input(user_input[CONF_REPLY_URL])
            except InvalidReplyUrl:
                errors[CONF_REPLY_URL] = "invalid_reply_url"
            else:
                await self.async_set_unique_id(reply_unique_id(target.reply_id))
                self._abort_if_unique_id_configured()

                self._name = user_input[CONF_NAME].strip() or NAME
                self._reply_data = {
                    CONF_REPLY_ID: target.reply_id,
                    CONF_REPLY_HOST: target.host,
                }
                # Both are created for every entry, also in ntfy mode: a later switch
                # to the webhook then needs no special case.
                self._webhook_id = webhook.async_generate_id()
                self._header_token = secrets.token_urlsafe(32)
                return await self.async_step_alarm_source()

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(USER_SCHEMA, user_input),
            errors=errors,
        )

    async def async_step_alarm_source(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask whether the user has Home Assistant Cloud.

        A detected subscription only changes the text (a second step ID), never the
        choice: nothing happens until the user picks an option.
        """
        if async_probe_reachability(self.hass) is Reachability.CLOUD:
            return await self.async_step_alarm_source_cloud()
        return self._async_show_menu("alarm_source", MENU_ALARM_SOURCE)

    async def async_step_alarm_source_cloud(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask the same question with the text for a detected subscription."""
        return self._async_show_menu("alarm_source_cloud", MENU_ALARM_SOURCE)

    async def async_step_no_cloud(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Point to ntfy as the free alternative; cloud and own address stay open."""
        return self._async_show_menu("no_cloud", MENU_NO_CLOUD)

    @callback
    def _async_show_menu(
        self, step_id: str, menu_options: list[str]
    ) -> ConfigFlowResult:
        """Show a menu whose text may use the My Home Assistant links."""
        return self.async_show_menu(
            step_id=step_id,
            menu_options=menu_options,
            description_placeholders=_link_placeholders(),
        )

    # --- The cloud path (webhook) -----------------------

    async def async_step_own_address(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Use an own internet address: the cloud path detects it anyway."""
        return await self.async_step_cloud()

    async def async_step_cloud(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Create the webhook URL if Home Assistant is reachable, else guide."""
        if async_probe_reachability(self.hass) is Reachability.NONE:
            self._cloud_attempts += 1
            if self._cloud_attempts > 1:
                # The second unsuccessful check shows what to look at.
                return await self.async_step_cloud_setup_retry()
            return await self.async_step_cloud_setup()

        try:
            url, kind, cloudhook = await async_create_webhook_url(
                self.hass, self._webhook_id
            )
        except CloudhookUnavailable:
            return await self.async_step_cloud_not_connected()
        except Exception as err:
            # Only the type is logged: the message may contain the URL.
            _LOGGER.error(
                "Unexpected error while creating the webhook URL: %s",
                type(err).__name__,
            )
            return self.async_abort(reason="unknown")
        return await self._async_finish_webhook(url, kind, cloudhook)

    async def async_step_cloud_setup(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Guide through setting up Home Assistant Cloud, without a dead end."""
        return self._async_show_menu("cloud_setup", MENU_CLOUD_SETUP)

    async def async_step_cloud_setup_retry(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Still not reachable: show what to check."""
        return self._async_show_menu("cloud_setup_retry", MENU_CLOUD_SETUP)

    async def async_step_cloud_not_connected(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """The subscription is active, but the cloud is not connected."""
        return self._async_show_menu("cloud_not_connected", MENU_CLOUD_NOT_CONNECTED)

    async def async_step_webhook_anyway(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Save with a local address: replies work, alarms can be added later."""
        url, kind = async_local_webhook_url(self.hass, self._webhook_id)
        return await self._async_finish_webhook(url, kind, False)

    async def _async_finish_webhook(
        self, url: str, kind: UrlKind, cloudhook: bool
    ) -> ConfigFlowResult:
        """Create the entry, or update it in the reconfigure flow."""
        webhook_data = {
            CONF_ALARM_SOURCE: SOURCE_WEBHOOK,
            CONF_WEBHOOK_ID: self._webhook_id,
            CONF_CLOUDHOOK: cloudhook,
            CONF_CLOUDHOOK_URL: url if cloudhook else None,
            CONF_HEADER_TOKEN: self._header_token,
        }
        if not self._reconfiguring:
            return self.async_create_entry(
                title=self._name,
                data={
                    **self._reply_data,
                    **webhook_data,
                    CONF_NTFY_ENTITY_UUID: None,
                    CONF_NTFY_TOPIC: None,
                    CONF_NTFY_SERVER: None,
                },
                options=_default_options(),
                description=kind,
                description_placeholders={**_link_placeholders(), "webhook_url": url},
            )

        entry = self._get_reconfigure_entry()
        data = {**entry.data, **self._reply_updates, **webhook_data}
        if data == dict(entry.data) and self._unique_id == entry.unique_id:
            # Nothing changed: no reload (which would reset a running alarm).
            return self.async_abort(reason="reconfigure_successful")

        old_webhook_id = entry.data[CONF_WEBHOOK_ID]
        had_cloudhook = bool(entry.data.get(CONF_CLOUDHOOK))
        new_token = entry.data[CONF_HEADER_TOKEN] != self._header_token
        self._async_update(entry, data)
        if new_token:
            # The new token makes the hint about a rejected call obsolete.
            self._async_delete_issue(ISSUE_TOKEN_REJECTED, entry)
        self._async_delete_issue(ISSUE_NTFY_ENTITY_MISSING, entry)
        # A cloudhook that the entry does not use anymore is deleted. The new access
        # was created first, so a failure here leaves a working entry.
        if had_cloudhook and (old_webhook_id != self._webhook_id or not cloudhook):
            await self._async_delete_old_cloudhook(old_webhook_id)

        # This dialog is the only place that shows the new access. An address that
        # FF Agent cannot reach gets the text of "continue anyway".
        reason = "reconfigure_successful_new_webhook"
        if kind in UNREACHABLE_KINDS:
            reason = "reconfigure_successful_local"
        return self.async_abort(
            reason=reason,
            description_placeholders={
                **_link_placeholders(),
                "webhook_url": url,
                "token_header": TOKEN_HEADER,
                "token": self._header_token,
            },
        )

    # --- The ntfy path -----------------------

    async def async_step_ntfy(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the guide for ntfy with the topic and the URL for FF Agent."""
        return self.async_show_menu(
            step_id="ntfy",
            menu_options=MENU_NTFY,
            description_placeholders=self._ntfy_placeholders(),
        )

    async def async_step_ntfy_find(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Find the ntfy entity of the topic; without a hit ask for it."""
        errors: dict[str, str] = {}
        if (subscription := self._async_search(errors)) is not None:
            return await self._async_finish_ntfy(subscription)
        return self._async_show_ntfy_select(errors, None)

    async def async_step_ntfy_select(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Search again (empty field) or check the entity the user chose."""
        errors: dict[str, str] = {}
        chosen: str | None = None
        if user_input is not None:
            if chosen := user_input.get(CONF_NTFY_ENTITY):
                subscription = async_describe_entity(self.hass, chosen)
                if subscription is None:
                    errors[CONF_NTFY_ENTITY] = "ntfy_entity_invalid"
                elif self._ntfy_entity_in_use(subscription.entity_uuid):
                    errors["base"] = "ntfy_entity_in_use"
                else:
                    return await self._async_finish_ntfy(subscription)
            elif (subscription := self._async_search(errors)) is not None:
                return await self._async_finish_ntfy(subscription)
        return self._async_show_ntfy_select(errors, chosen)

    @callback
    def _async_show_ntfy_select(
        self, errors: dict[str, str], chosen: str | None
    ) -> ConfigFlowResult:
        """Show the form to choose the ntfy entity."""
        suggested = chosen or self._current_ntfy_entity_id()
        key = vol.Optional(
            CONF_NTFY_ENTITY,
            description={"suggested_value": suggested} if suggested else None,
        )
        return self.async_show_form(
            step_id="ntfy_select",
            data_schema=vol.Schema({key: NTFY_ENTITY_SELECTOR}),
            errors=errors,
            description_placeholders=self._ntfy_placeholders(),
        )

    @callback
    def _async_search(self, errors: dict[str, str]) -> NtfySubscription | None:
        """Search the entity by the topic; on failure fill ``errors``."""
        if not self.hass.config_entries.async_entries(NTFY_DOMAIN):
            errors["base"] = "ntfy_not_set_up"
            return None
        subscription = async_find_subscription_by_topic(self.hass, self._topic)
        if subscription is None:
            errors["base"] = "ntfy_entity_not_found"
            return None
        if self._ntfy_entity_in_use(subscription.entity_uuid):
            errors["base"] = "ntfy_entity_in_use"
            return None
        return subscription

    async def _async_finish_ntfy(
        self, subscription: NtfySubscription
    ) -> ConfigFlowResult:
        """Create the entry, or update it in the reconfigure flow.

        The chosen entity is the source of truth: its topic and server win over the
        generated topic. If its topic cannot be read, no URL is shown at all, because
        the generated topic would be a wrong one.
        """
        topic = subscription.topic
        server = subscription.server or NTFY_DEFAULT_SERVER
        ntfy_data = {
            CONF_ALARM_SOURCE: SOURCE_NTFY,
            CONF_NTFY_ENTITY_UUID: subscription.entity_uuid,
            CONF_NTFY_TOPIC: topic,
            CONF_NTFY_SERVER: server,
            # Dormant in ntfy mode, kept for a later switch back to the webhook.
            CONF_WEBHOOK_ID: self._webhook_id,
            CONF_HEADER_TOKEN: self._header_token,
            # No cloudhook in ntfy mode: an entry has exactly one open entrance.
            CONF_CLOUDHOOK: False,
            CONF_CLOUDHOOK_URL: None,
        }
        placeholders = _link_placeholders()
        if not topic:
            text = "ntfy_topic_unknown"
        elif (url := ntfy_publish_url(server, topic)) == self._shown_ntfy_url:
            # Short text: the guide showed exactly this URL, so it is not repeated.
            text = SOURCE_NTFY
        else:
            text = NTFY_OTHER_ADDRESS
            placeholders[NTFY_PUBLISH_URL] = url
        if not self._reconfiguring:
            return self.async_create_entry(
                title=self._name,
                data={**self._reply_data, **ntfy_data},
                options=_default_options(),
                description=text,
                description_placeholders=placeholders,
            )

        entry = self._get_reconfigure_entry()
        data = {**entry.data, **self._reply_updates, **ntfy_data}
        if data == dict(entry.data) and self._unique_id == entry.unique_id:
            # Nothing changed: no reload (which would reset a running alarm).
            return self.async_abort(reason="reconfigure_successful")

        old_webhook_id = entry.data[CONF_WEBHOOK_ID]
        had_cloudhook = bool(entry.data.get(CONF_CLOUDHOOK))
        self._async_update(entry, data)
        self._async_delete_issue(ISSUE_TOKEN_REJECTED, entry)
        self._async_delete_issue(ISSUE_NTFY_ENTITY_MISSING, entry)
        if had_cloudhook:
            await self._async_delete_old_cloudhook(old_webhook_id)
        return self.async_abort(
            reason=f"reconfigure_successful_{text}",
            description_placeholders=placeholders,
        )

    @property
    def _topic(self) -> str:
        """Return the topic of the flow, created once when the guide is first shown.

        The reconfigure flow keeps the stored topic unless a new one is wanted.
        """
        if self._ntfy_topic is None:
            self._ntfy_topic = self._stored_ntfy_topic() or async_generate_topic()
        return self._ntfy_topic

    @callback
    def _stored_ntfy_topic(self) -> str | None:
        """Return the topic to keep in the reconfigure flow, if any."""
        if not self._reconfiguring or self._regenerate:
            return None
        data = self._get_reconfigure_entry().data
        if data.get(CONF_ALARM_SOURCE) != SOURCE_NTFY:
            return None
        return data.get(CONF_NTFY_TOPIC)

    @callback
    def _current_ntfy_entity_id(self) -> str | None:
        """Return the entity ID of the ntfy entity (reconfigure only)."""
        if not self._reconfiguring:
            return None
        data = self._get_reconfigure_entry().data
        uuid = data.get(CONF_NTFY_ENTITY_UUID)
        if data.get(CONF_ALARM_SOURCE) != SOURCE_NTFY or not uuid:
            return None
        return er.async_resolve_entity_id(er.async_get(self.hass), uuid)

    @callback
    def _ntfy_placeholders(self) -> dict[str, str]:
        """Return topic, URL for FF Agent and links for the ntfy texts.

        Only the steps "ntfy" and "ntfy_select" call this, and both show the URL. It is
        remembered, so the closing dialog can tell whether the chosen entity changes it.
        """
        topic = self._topic
        ntfy_entries = self.hass.config_entries.async_entries(NTFY_DOMAIN)
        server = NTFY_DEFAULT_SERVER
        if len(ntfy_entries) == 1:
            url = ntfy_entries[0].data.get(NTFY_CONF_URL)
            if isinstance(url, str) and url:
                server = url
        self._shown_ntfy_url = ntfy_publish_url(server, topic)
        return {
            **_link_placeholders(),
            "ntfy_topic": topic,
            NTFY_PUBLISH_URL: self._shown_ntfy_url,
        }

    @callback
    def _ntfy_entity_in_use(self, entity_uuid: str) -> bool:
        """Return whether another FF Agent entry uses the ntfy entity.

        Otherwise a second person would get the same alarms.
        """
        own = self._get_reconfigure_entry().entry_id if self._reconfiguring else None
        return any(
            entry.entry_id != own
            and entry.data.get(CONF_ALARM_SOURCE) == SOURCE_NTFY
            and entry.data.get(CONF_NTFY_ENTITY_UUID) == entity_uuid
            for entry in self._async_current_entries(include_ignore=False)
        )

    # --- Shared helpers of the reconfigure flow -----------------------

    @callback
    def _async_update(self, entry: ConfigEntry, data: dict[str, Any]) -> None:
        """Store the new data and schedule the reload of the entry."""
        self.hass.config_entries.async_update_entry(
            entry, unique_id=self._unique_id, data=data
        )
        # From here on the new data is valid. The reload is scheduled first, so
        # nothing below can keep the entry from running with it.
        self.hass.config_entries.async_schedule_reload(entry.entry_id)

    @callback
    def _async_delete_issue(self, issue: str, entry: ConfigEntry) -> None:
        """Delete a repair issue of the entry."""
        ir.async_delete_issue(self.hass, DOMAIN, issue.format(entry_id=entry.entry_id))

    async def _async_delete_old_cloudhook(self, webhook_id: str) -> None:
        """Delete a cloudhook the entry does not use anymore; errors are harmless."""
        try:
            await async_delete_cloudhook(self.hass, webhook_id)
        except Exception as err:
            # A leftover cloudhook is harmless (nobody knows its URL anymore, or it
            # points at a webhook that is not registered in ntfy mode). Only the type
            # is logged: the message may contain the URL.
            _LOGGER.warning(
                "Could not delete the old cloudhook: %s", type(err).__name__
            )

    # --- Reconfigure -----------------------

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the reply URL, the alarm source and/or the secret address.

        The stored reply URL is never shown. An empty field leaves it as it is. A new
        reply URL may change the unique ID; if another entry already has that ID, the
        flow aborts. The path to the alarm source is the same as in the config flow,
        without the first question: the field "alarm source" replaces it.
        """
        entry = self._get_reconfigure_entry()
        current_source = entry.data.get(CONF_ALARM_SOURCE, SOURCE_WEBHOOK)
        errors: dict[str, str] = {}

        if user_input is not None:
            reply_input = (user_input.get(CONF_REPLY_URL) or "").strip()
            updates: dict[str, Any] = {}
            unique_id = entry.unique_id
            if reply_input:
                try:
                    target = parse_reply_input(reply_input)
                except InvalidReplyUrl:
                    errors[CONF_REPLY_URL] = "invalid_reply_url"
                else:
                    updates = {
                        CONF_REPLY_ID: target.reply_id,
                        CONF_REPLY_HOST: target.host,
                    }
                    unique_id = reply_unique_id(target.reply_id)

            if not errors and unique_id != entry.unique_id:
                other = self.hass.config_entries.async_entry_for_domain_unique_id(
                    DOMAIN, unique_id
                )
                if other is not None and other.entry_id != entry.entry_id:
                    return self.async_abort(reason="already_configured")

            if not errors:
                return await self._async_reconfigure_source(
                    entry,
                    updates,
                    unique_id,
                    user_input.get(CONF_ALARM_SOURCE, current_source),
                    bool(user_input.get(CONF_REGENERATE_WEBHOOK)),
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                _reconfigure_schema(current_source), user_input
            ),
            errors=errors,
        )

    async def _async_reconfigure_source(
        self,
        entry: ConfigEntry,
        updates: dict[str, Any],
        unique_id: str | None,
        target_source: str,
        regenerate: bool,
    ) -> ConfigFlowResult:
        """Go on with the path of the chosen alarm source."""
        current_source = entry.data.get(CONF_ALARM_SOURCE, SOURCE_WEBHOOK)
        self._reply_updates = updates
        self._unique_id = unique_id
        self._regenerate = regenerate
        self._webhook_id = entry.data[CONF_WEBHOOK_ID]
        self._header_token = entry.data[CONF_HEADER_TOKEN]

        if regenerate:
            # A new secret address renews the webhook values, also the dormant ones
            # of an ntfy entry.
            self._webhook_id = webhook.async_generate_id()
            self._header_token = secrets.token_urlsafe(32)

        if target_source == SOURCE_NTFY:
            uuid = entry.data.get(CONF_NTFY_ENTITY_UUID)
            valid = uuid is not None and async_describe_entity(self.hass, uuid)
            if current_source != SOURCE_NTFY or regenerate or not valid:
                # With "regenerate" the guide shows a new topic.
                return await self.async_step_ntfy()
            # ntfy stays as it is: only the reply URL may have changed.
        elif (
            current_source == SOURCE_NTFY
            or regenerate
            or async_get_webhook_url(self.hass, entry)[1] in UNREACHABLE_KINDS
        ):
            return await self.async_step_cloud()

        if updates.items() <= entry.data.items():
            # Nothing changed: no update and no reload (which would reset the
            # running alarm).
            return self.async_abort(reason="reconfigure_successful")
        return self.async_update_reload_and_abort(
            entry, unique_id=unique_id, data_updates=updates
        )


class FFAgentOptionsFlow(OptionsFlowWithReload):
    """Options of one entry. Saving reloads the entry and resets a running alarm."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show and save the options. The form also shows the webhook access."""
        if self.config_entry.data.get(CONF_ALARM_SOURCE) == SOURCE_NTFY:
            return await self.async_step_ntfy()

        if user_input is not None:
            # The options are replaced as a whole. A cleared location entity is missing
            # from the input, so no location is sent afterwards.
            return self.async_create_entry(data=user_input)

        entry = self.config_entry
        # URL and token are secrets. They are shown here on purpose and never logged.
        url, url_kind = async_get_webhook_url(self.hass, entry)
        return self.async_show_form(
            step_id="init",
            data_schema=self._schema(with_token=True),
            description_placeholders={
                "webhook_url": url,
                "url_kind": url_kind.value,
                "token_header": TOKEN_HEADER,
                "token": entry.data[CONF_HEADER_TOKEN],
                "cloud_url": MY_CLOUD_URL,
            },
        )

    async def async_step_ntfy(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show and save the options in ntfy mode: there is no additional token."""
        options = self.config_entry.options
        if user_input is not None:
            # The token option is kept, so it applies again after a switch back to
            # the webhook.
            return self.async_create_entry(
                data={
                    **user_input,
                    CONF_REQUIRE_TOKEN: bool(options.get(CONF_REQUIRE_TOKEN, False)),
                }
            )

        data = self.config_entry.data
        uuid = data.get(CONF_NTFY_ENTITY_UUID)
        entity_id = (
            er.async_resolve_entity_id(er.async_get(self.hass), uuid) if uuid else None
        )
        publish_url = NO_VALUE
        if topic := data.get(CONF_NTFY_TOPIC):
            publish_url = ntfy_publish_url(data.get(CONF_NTFY_SERVER), topic)
        # Topic and entity ID are secrets. They are shown here on purpose.
        return self.async_show_form(
            step_id="ntfy",
            data_schema=self._schema(with_token=False),
            description_placeholders={
                "ntfy_entity": entity_id or NO_VALUE,
                NTFY_PUBLISH_URL: publish_url,
            },
        )

    @callback
    def _schema(self, *, with_token: bool) -> vol.Schema:
        """Return the options form with the current values."""
        options = self.config_entry.options
        reset_minutes = int(
            clamp_reset_minutes(options.get(CONF_RESET_MINUTES, DEFAULT_RESET_MINUTES))
        )
        # "suggested_value" instead of "default": a default would come back when the
        # field is cleared, so the location could never be removed.
        location = options.get(CONF_LOCATION_ENTITY)
        location_key = vol.Optional(
            CONF_LOCATION_ENTITY,
            description={"suggested_value": location} if location else None,
        )
        schema: dict[Any, Any] = {
            vol.Required(
                CONF_RESET_MINUTES, default=reset_minutes
            ): RESET_MINUTES_VALIDATOR,
            vol.Required(
                CONF_DEFAULT_TRANSPORT,
                default=configured_transport(options.get(CONF_DEFAULT_TRANSPORT)),
            ): TRANSPORT_SELECTOR,
            location_key: LOCATION_SELECTOR,
        }
        if with_token:
            # The token switch comes first, as it always did.
            schema = {
                vol.Required(
                    CONF_REQUIRE_TOKEN, default=bool(options.get(CONF_REQUIRE_TOKEN))
                ): BooleanSelector(),
                **schema,
            }
        return vol.Schema(schema)
