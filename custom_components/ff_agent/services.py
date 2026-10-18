"""Actions of the FF Agent integration.

ff_agent.accept and ff_agent.reject reply to FF Agent; ff_agent.reset_alarm only
switches "alarm active" off in Home Assistant.
"""

from __future__ import annotations

import voluptuous as vol
from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import service

from .const import (
    ATTR_TRANSPORT,
    DOMAIN,
    SERVICE_ACCEPT,
    SERVICE_REJECT,
    SERVICE_RESET_ALARM,
    TRANSPORTS,
)
from .models import ReplyAction
from .reply import async_send_reply

# The entry is named explicitly: one entry is one person, and a reply is personal.
ATTR_CONFIG_ENTRY_ID = "config_entry_id"

ACCEPT_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Optional(ATTR_TRANSPORT): vol.In(TRANSPORTS),
        vol.Inclusive(ATTR_LATITUDE, "location"): cv.latitude,
        vol.Inclusive(ATTR_LONGITUDE, "location"): cv.longitude,
    }
)
REJECT_SCHEMA = vol.Schema({vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string})
RESET_ALARM_SCHEMA = vol.Schema({vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string})


async def _async_accept(call: ServiceCall) -> None:
    """Accept the current mission for the person of the given entry."""
    entry = service.async_get_config_entry(
        call.hass, DOMAIN, call.data[ATTR_CONFIG_ENTRY_ID]
    )
    location = None
    if ATTR_LATITUDE in call.data:
        location = (call.data[ATTR_LATITUDE], call.data[ATTR_LONGITUDE])
    await async_send_reply(
        call.hass,
        entry,
        ReplyAction.ACCEPT,
        transport=call.data.get(ATTR_TRANSPORT),
        location=location,
    )


async def _async_reject(call: ServiceCall) -> None:
    """Decline the current mission for the person of the given entry."""
    entry = service.async_get_config_entry(
        call.hass, DOMAIN, call.data[ATTR_CONFIG_ENTRY_ID]
    )
    await async_send_reply(call.hass, entry, ReplyAction.REJECT)


async def _async_reset_alarm(call: ServiceCall) -> None:
    """Switch "alarm active" of the given entry off. Nothing is sent to FF Agent."""
    entry = service.async_get_config_entry(
        call.hass, DOMAIN, call.data[ATTR_CONFIG_ENTRY_ID]
    )
    entry.runtime_data.alarm.async_reset()


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the actions. They are available even if no entry is loaded."""
    hass.services.async_register(
        DOMAIN,
        SERVICE_ACCEPT,
        _async_accept,
        schema=ACCEPT_SCHEMA,
        supports_response=SupportsResponse.NONE,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REJECT,
        _async_reject,
        schema=REJECT_SCHEMA,
        supports_response=SupportsResponse.NONE,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RESET_ALARM,
        _async_reset_alarm,
        schema=RESET_ALARM_SCHEMA,
        supports_response=SupportsResponse.NONE,
    )
