"""Config flow, reconfigure flow and options flow for the FF Agent integration."""

from __future__ import annotations

import logging
import secrets
from typing import Any

import voluptuous as vol
from homeassistant.components import webhook
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_NAME, CONF_WEBHOOK_ID
from homeassistant.core import HomeAssistant, callback
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
    CONF_CLOUDHOOK,
    CONF_CLOUDHOOK_URL,
    CONF_DEFAULT_TRANSPORT,
    CONF_HEADER_TOKEN,
    CONF_LOCATION_ENTITY,
    CONF_REGENERATE_WEBHOOK,
    CONF_REPLY_HOST,
    CONF_REPLY_ID,
    CONF_REPLY_URL,
    CONF_REQUIRE_TOKEN,
    CONF_RESET_MINUTES,
    DEFAULT_RESET_MINUTES,
    DEFAULT_TRANSPORT,
    DOMAIN,
    ISSUE_TOKEN_REJECTED,
    MAX_RESET_MINUTES,
    MIN_RESET_MINUTES,
    NAME,
    TOKEN_HEADER,
    TRANSPORTS,
)
from .reply import configured_transport
from .reply_url import InvalidReplyUrl, parse_reply_input, reply_unique_id
from .webhook_url import (
    CloudhookUnavailable,
    UrlKind,
    async_create_webhook_url,
    async_delete_cloudhook,
    async_get_webhook_url,
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

# Both fields are optional: an empty reply URL means "unchanged". The stored reply URL
# is a secret and is never shown, so the field is never pre-filled.
RECONFIGURE_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_REPLY_URL): TextSelector(
            TextSelectorConfig(type=TextSelectorType.TEXT)
        ),
        vol.Optional(CONF_REGENERATE_WEBHOOK, default=False): BooleanSelector(),
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


async def _async_create_url(
    hass: HomeAssistant, webhook_id: str, errors: dict[str, str]
) -> tuple[str, UrlKind, bool] | None:
    """Create the URL of a webhook; on failure fill ``errors`` and return None."""
    try:
        return await async_create_webhook_url(hass, webhook_id)
    except CloudhookUnavailable:
        errors["base"] = "cloud_not_connected"
    except Exception as err:
        # Only the type is logged: the message may contain the URL.
        _LOGGER.error(
            "Unexpected error while creating the webhook URL: %s", type(err).__name__
        )
        errors["base"] = "unknown"
    return None


class FFAgentConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow for FF Agent.

    One config entry stands for one person. The flow makes no request to FF Agent,
    because every test call would be a real mission reply.
    """

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> FFAgentOptionsFlow:
        """Return the options flow; it reloads the entry when the options change."""
        return FFAgentOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step started by the user."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                target = parse_reply_input(user_input[CONF_REPLY_URL])
            except InvalidReplyUrl:
                errors[CONF_REPLY_URL] = "invalid_reply_url"
            else:
                await self.async_set_unique_id(reply_unique_id(target.reply_id))
                self._abort_if_unique_id_configured()

                webhook_id = webhook.async_generate_id()
                if created := await _async_create_url(self.hass, webhook_id, errors):
                    url, url_kind, cloudhook = created
                    return self.async_create_entry(
                        title=user_input[CONF_NAME].strip() or NAME,
                        data={
                            CONF_REPLY_ID: target.reply_id,
                            CONF_REPLY_HOST: target.host,
                            CONF_WEBHOOK_ID: webhook_id,
                            CONF_CLOUDHOOK: cloudhook,
                            CONF_CLOUDHOOK_URL: url if cloudhook else None,
                            CONF_HEADER_TOKEN: secrets.token_urlsafe(32),
                        },
                        options={
                            CONF_RESET_MINUTES: DEFAULT_RESET_MINUTES,
                            CONF_DEFAULT_TRANSPORT: DEFAULT_TRANSPORT,
                            CONF_REQUIRE_TOKEN: False,
                        },
                        description=url_kind,
                        description_placeholders={"webhook_url": url},
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(USER_SCHEMA, user_input),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the mission reply URL and/or create a new webhook access.

        The stored reply URL is never shown. An empty field leaves it as it is. A new
        reply URL may change the unique ID; if another entry already has that ID, the
        flow aborts. A new webhook access (new webhook ID and token, a new cloudhook
        if the cloud is used) is shown once in the closing dialog.
        """
        entry = self._get_reconfigure_entry()
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
                if user_input.get(CONF_REGENERATE_WEBHOOK):
                    if result := await self._async_regenerate(
                        entry, updates, unique_id, errors
                    ):
                        return result
                elif updates.items() <= entry.data.items():
                    # Nothing changed: no update and no reload (which would reset the
                    # running alarm).
                    return self.async_abort(reason="reconfigure_successful")
                else:
                    return self.async_update_reload_and_abort(
                        entry, unique_id=unique_id, data_updates=updates
                    )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                RECONFIGURE_SCHEMA, user_input
            ),
            errors=errors,
        )

    async def _async_regenerate(
        self,
        entry: ConfigEntry,
        updates: dict[str, Any],
        unique_id: str | None,
        errors: dict[str, str],
    ) -> ConfigFlowResult | None:
        """Replace webhook ID and token. On failure fill ``errors`` and return None.

        The new access is created first and the old cloudhook is deleted afterwards,
        so a failure leaves the old access intact. A failing deletion of the old
        cloudhook does not fail the flow.
        """
        webhook_id = webhook.async_generate_id()
        token = secrets.token_urlsafe(32)
        created = await _async_create_url(self.hass, webhook_id, errors)
        if created is None:
            return None
        url, _kind, cloudhook = created

        old_webhook_id = entry.data[CONF_WEBHOOK_ID]
        had_cloudhook = bool(entry.data.get(CONF_CLOUDHOOK))
        self.hass.config_entries.async_update_entry(
            entry,
            unique_id=unique_id,
            data={
                **entry.data,
                **updates,
                CONF_WEBHOOK_ID: webhook_id,
                CONF_CLOUDHOOK: cloudhook,
                CONF_CLOUDHOOK_URL: url if cloudhook else None,
                CONF_HEADER_TOKEN: token,
            },
        )
        # From here on the new access is the valid one. The reload is scheduled first,
        # so nothing below can keep the entry from running with it.
        self.hass.config_entries.async_schedule_reload(entry.entry_id)
        # The new token makes the hint about a call that was rejected obsolete.
        ir.async_delete_issue(
            self.hass, DOMAIN, ISSUE_TOKEN_REJECTED.format(entry_id=entry.entry_id)
        )
        if had_cloudhook:
            try:
                await async_delete_cloudhook(self.hass, old_webhook_id)
            except Exception as err:
                # A leftover cloudhook is harmless (nobody knows its URL anymore).
                # Only the type is logged: the message may contain the URL.
                _LOGGER.warning(
                    "Could not delete the old cloudhook: %s", type(err).__name__
                )

        # This dialog is the only place that shows the new access.
        return self.async_abort(
            reason="reconfigure_successful_new_webhook",
            description_placeholders={
                "webhook_url": url,
                "token_header": TOKEN_HEADER,
                "token": token,
            },
        )


class FFAgentOptionsFlow(OptionsFlowWithReload):
    """Options of one entry. Saving reloads the entry and resets a running alarm."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show and save the options. The form also shows the webhook access."""
        if user_input is not None:
            # The options are replaced as a whole. A cleared location entity is missing
            # from the input, so no location is sent afterwards.
            return self.async_create_entry(data=user_input)

        entry = self.config_entry
        options = entry.options
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
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_REQUIRE_TOKEN, default=bool(options.get(CONF_REQUIRE_TOKEN))
                ): BooleanSelector(),
                vol.Required(
                    CONF_RESET_MINUTES, default=reset_minutes
                ): RESET_MINUTES_VALIDATOR,
                vol.Required(
                    CONF_DEFAULT_TRANSPORT,
                    default=configured_transport(options.get(CONF_DEFAULT_TRANSPORT)),
                ): TRANSPORT_SELECTOR,
                location_key: LOCATION_SELECTOR,
            }
        )

        # URL and token are secrets. They are shown here on purpose and never logged.
        url, url_kind = async_get_webhook_url(self.hass, entry)
        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            description_placeholders={
                "webhook_url": url,
                "url_kind": url_kind.value,
                "token_header": TOKEN_HEADER,
                "token": entry.data[CONF_HEADER_TOKEN],
            },
        )
