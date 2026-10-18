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

# Where the alarm comes from (ADR 0003). Exactly one source is active per entry.
CONF_ALARM_SOURCE: Final = "alarm_source"
SOURCE_WEBHOOK: Final = "webhook"
SOURCE_NTFY: Final = "ntfy"
ALARM_SOURCES: Final = (SOURCE_WEBHOOK, SOURCE_NTFY)  # choice in the reconfigure flow

# Menus of the config flow. The options are step IDs, the order is the display order
# (menus have no preselection, so the recommended option comes first).
MENU_ALARM_SOURCE: Final = ["cloud", "no_cloud"]
MENU_NO_CLOUD: Final = ["ntfy", "cloud", "own_address"]
MENU_CLOUD_SETUP: Final = ["cloud", "ntfy", "webhook_anyway"]
MENU_CLOUD_NOT_CONNECTED: Final = ["cloud", "ntfy"]
MENU_NTFY: Final = ["ntfy_find", "cloud"]

CONF_NTFY_ENTITY_UUID: Final = "ntfy_entity_uuid"  # registry UUID, secret
CONF_NTFY_TOPIC: Final = "ntfy_topic"  # secret
CONF_NTFY_SERVER: Final = "ntfy_server"  # only shown, not secret
CONF_NTFY_ENTITY: Final = "ntfy_entity"  # flow field only (entity ID), never stored
NTFY_PUBLISH_URL: Final = "ntfy_publish_url"  # placeholder, contains the topic

# Keys of the core integration ntfy. Not imported: homeassistant.components.ntfy
# imports aiontfy. Guarded by tests/test_ntfy_contract.py.
NTFY_DOMAIN: Final = "ntfy"
NTFY_SUBENTRY_TYPE: Final = "topic"
NTFY_CONF_TOPIC: Final = "topic"
NTFY_CONF_URL: Final = "url"
NTFY_DEFAULT_SERVER: Final = "https://ntfy.sh/"
NTFY_TOPIC_BYTES: Final = 16  # secrets.token_hex -> 32 characters, 128 bits
# A timestamp of the ntfy entity older than this is a restored value, not an alarm.
NTFY_MAX_EVENT_AGE_SECONDS: Final = 60

ISSUE_NTFY_ENTITY_MISSING: Final = "ntfy_entity_missing_{entry_id}"

# My Home Assistant links. Translations must not contain URLs (hassfest), so they are
# passed as description placeholders.
MY_CLOUD_URL: Final = "https://my.home-assistant.io/redirect/cloud/"
MY_NETWORK_URL: Final = "https://my.home-assistant.io/redirect/network/"
MY_NTFY_SETUP_URL: Final = (
    "https://my.home-assistant.io/redirect/config_flow_start/?domain=ntfy"
)
MY_NTFY_INTEGRATION_URL: Final = (
    "https://my.home-assistant.io/redirect/integration/?domain=ntfy"
)

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

# Device of a config entry. The manufacturer is neutral on purpose: this is an
# unofficial community project and must not name the vendor or operator of FF Agent.
MANUFACTURER: Final = "ha-ff-agent (inoffiziell)"
MODEL: Final = "FF Agent"

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
    CONF_NTFY_TOPIC,
    CONF_NTFY_ENTITY_UUID,
    CONF_NTFY_ENTITY,
    NTFY_PUBLISH_URL,
    # The entity ID of the ntfy entity contains the topic if it has no display name.
    "entity_id",
}
