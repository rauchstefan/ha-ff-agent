"""Constants for the FF Agent integration."""

from __future__ import annotations

from typing import Final

from homeassistant.const import CONF_WEBHOOK_ID

DOMAIN: Final = "ff_agent"
NAME: Final = "FF Agent"

CONF_REPLY_ID: Final = "reply_id"
CONF_REPLY_HOST: Final = "reply_host"
CONF_CLOUDHOOK: Final = "cloudhook"  # bool
CONF_CLOUDHOOK_URL: Final = "cloudhook_url"  # str | None, secret
CONF_HEADER_TOKEN: Final = "header_token"  # str, secret, always generated
# CONF_WEBHOOK_ID and CONF_NAME come from homeassistant.const

CONF_REPLY_URL: Final = "reply_url"  # flow field only, never stored
CONF_REGENERATE_WEBHOOK: Final = "regenerate_webhook"  # flow field only

CONF_RESET_MINUTES: Final = "reset_minutes"
CONF_DEFAULT_TRANSPORT: Final = "default_transport"
CONF_LOCATION_ENTITY: Final = "location_entity"
CONF_REQUIRE_TOKEN: Final = "require_token"  # bool, default False (ADR 0002, 5.)

TOKEN_HEADER: Final = "X-FF-Agent-Token"
ISSUE_TOKEN_REJECTED: Final = "webhook_token_rejected_{entry_id}"

DEFAULT_RESET_MINUTES: Final = 30
MIN_RESET_MINUTES: Final = 1
MAX_RESET_MINUTES: Final = 1440
DEFAULT_TRANSPORT: Final = "car"
# The transports of the actions and the options are lower case, because translation
# keys must be (hassfest). FF Agent gets the upper case value. The three values are
# the ones the FF Agent web UI names for the optional parameter (research 3.7, A9).
TRANSPORT_API_VALUES: Final = {"car": "CAR", "feet": "FEET", "bicycle": "BICYCLE"}
TRANSPORTS: Final = tuple(TRANSPORT_API_VALUES)
# Entries from the first version stored the value for FF Agent as default transport.
LEGACY_TRANSPORTS: Final = {api: key for key, api in TRANSPORT_API_VALUES.items()}

# Calls within this time after the last recognized alarm are only counted (A3).
DEDUP_SECONDS: Final = 30

# Reply to FF Agent: GET <host>/app2/missionreplies/<reply_id>/<accept|reject> (A6).
REPLY_PATH: Final = "/app2/missionreplies/{reply_id}/{action}"
REPLY_TIMEOUT_SECONDS: Final = 10
# The same reply right after a success is not sent a second time (double click).
REPLY_REPEAT_GUARD_SECONDS: Final = 10

# Values of the sensor "last reply".
REPLY_STATE_ACCEPTED: Final = "accepted"
REPLY_STATE_REJECTED: Final = "rejected"
REPLY_STATE_FAILED: Final = "failed"
REPLY_OPTIONS: Final = (REPLY_STATE_ACCEPTED, REPLY_STATE_REJECTED, REPLY_STATE_FAILED)

# Actions of the integration.
SERVICE_ACCEPT: Final = "accept"
SERVICE_REJECT: Final = "reject"
ATTR_TRANSPORT: Final = "transport"

# Dispatcher signals of the alarm manager, one pair per config entry.
SIGNAL_ALARM: Final = "ff_agent_alarm_{entry_id}"  # payload AlarmEvent
SIGNAL_ALARM_STATE: Final = "ff_agent_alarm_state_{entry_id}"
# Dispatcher signal of the reply client, one per config entry.
SIGNAL_REPLY: Final = "ff_agent_reply_{entry_id}"  # payload ReplyResult

# The event type of the event entity "alarm".
EVENT_TYPE_ALARM: Final = "alarm"

# Device of a config entry.
MANUFACTURER: Final = "mackoy consulting"
MODEL: Final = "FF Agent"
CONFIGURATION_URL: Final = "https://www.ff-agent.com"

# Analysis of an incoming webhook call: only the shape is kept, never a value.
# A body longer than MAX_BODY_ANALYSIS_CHARS is cut before it is parsed, so a large
# JSON body is recorded as "text" (a cut-off JSON document cannot be parsed).
MAX_BODY_ANALYSIS_CHARS: Final = 65536
MAX_SHAPE_DEPTH: Final = 5
MAX_SHAPE_KEYS: Final = 50
MAX_NAME_CHARS: Final = 64  # longest header name, query key or body key that is kept
MAX_USER_AGENT_CHARS: Final = 120
MAX_CONTENT_TYPE_CHARS: Final = 100  # media type only, without parameters

DEFAULT_REPLY_HOST: Final = "www.ff-agent.com"
WEBHOOK_ALLOWED_METHODS: Final = ("GET", "POST")  # exactly what FF Agent offers [G]

TO_REDACT: Final = {
    CONF_REPLY_ID,
    CONF_WEBHOOK_ID,
    CONF_CLOUDHOOK_URL,
    "webhook_url",
    CONF_HEADER_TOKEN,
    "unique_id",
    "title",
    CONF_LOCATION_ENTITY,
}
