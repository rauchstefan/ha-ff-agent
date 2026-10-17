"""Config flow for the FF Agent integration."""

from __future__ import annotations

import logging
import secrets
from typing import Any

import voluptuous as vol
from homeassistant.components import webhook
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_NAME, CONF_WEBHOOK_ID
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CONF_CLOUDHOOK,
    CONF_CLOUDHOOK_URL,
    CONF_DEFAULT_TRANSPORT,
    CONF_HEADER_TOKEN,
    CONF_REPLY_HOST,
    CONF_REPLY_ID,
    CONF_REPLY_URL,
    CONF_REQUIRE_TOKEN,
    CONF_RESET_MINUTES,
    DEFAULT_RESET_MINUTES,
    DEFAULT_TRANSPORT,
    DOMAIN,
    NAME,
)
from .reply_url import InvalidReplyUrl, parse_reply_input, reply_unique_id
from .webhook_url import CloudhookUnavailable, async_create_webhook_url

_LOGGER = logging.getLogger(__name__)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME, default=NAME): str,
        vol.Required(CONF_REPLY_URL): TextSelector(
            TextSelectorConfig(type=TextSelectorType.TEXT)
        ),
    }
)


class FFAgentConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow for FF Agent.

    One config entry stands for one person. The flow makes no request to FF Agent,
    because every test call would be a real mission reply.
    """

    VERSION = 1

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
                try:
                    url, url_kind, cloudhook = await async_create_webhook_url(
                        self.hass, webhook_id
                    )
                except CloudhookUnavailable:
                    errors["base"] = "cloud_not_connected"
                except Exception as err:
                    # Only the type is logged: the message may contain the URL.
                    _LOGGER.error(
                        "Unexpected error while creating the webhook URL: %s",
                        type(err).__name__,
                    )
                    errors["base"] = "unknown"
                else:
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
