"""Constants for the FF Agent integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "ff_agent"
NAME: Final = "FF Agent"

CONF_REPLY_ID: Final = "reply_id"
CONF_REPLY_HOST: Final = "reply_host"
CONF_CLOUDHOOK: Final = "cloudhook"  # bool
CONF_CLOUDHOOK_URL: Final = "cloudhook_url"  # str | None, secret
CONF_HEADER_TOKEN: Final = "header_token"  # str, secret, always generated
# CONF_WEBHOOK_ID and CONF_NAME come from homeassistant.const

CONF_REPLY_URL: Final = "reply_url"  # flow field only, never stored

CONF_RESET_MINUTES: Final = "reset_minutes"
CONF_DEFAULT_TRANSPORT: Final = "default_transport"
CONF_REQUIRE_TOKEN: Final = "require_token"  # bool, default False (ADR 0002, 5.)

DEFAULT_RESET_MINUTES: Final = 30
DEFAULT_TRANSPORT: Final = "CAR"

DEFAULT_REPLY_HOST: Final = "www.ff-agent.com"
