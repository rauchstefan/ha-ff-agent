"""The reply client of the FF Agent integration: accept or decline a mission.

A reply is a GET request to the personal reply URL of the person. The ID in that URL is
the only credential, so it is a secret. Therefore nothing here may log or raise
anything that contains the URL, the ID or the query:

- aiohttp exceptions contain the URL. Only the name of their class is kept, and the
  errors raised from here are raised without the original exception (``from None``),
  so no traceback can show it either.
- The response body is neither read nor logged. Success means an HTTP status 2xx; FF
  Agent may answer 200 even if it did not record the reply (assumption A7).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from datetime import datetime, timedelta
from http import HTTPStatus
from typing import Any

import aiohttp
from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.util import dt as dt_util

from .const import (
    CONF_DEFAULT_TRANSPORT,
    CONF_LOCATION_ENTITY,
    CONF_LOCATION_LATITUDE,
    CONF_LOCATION_LONGITUDE,
    CONF_LOCATION_SOURCE,
    DEFAULT_TRANSPORT,
    DOMAIN,
    LEGACY_TRANSPORTS,
    LOCATION_SOURCE_ENTITY,
    LOCATION_SOURCE_HOME,
    LOCATION_SOURCE_MANUAL,
    LOCATION_SOURCE_NONE,
    LOCATION_SOURCES,
    MAX_CONTENT_TYPE_CHARS,
    REPLY_PATH,
    REPLY_REPEAT_GUARD_SECONDS,
    REPLY_TIMEOUT_SECONDS,
    SIGNAL_REPLY,
    TRANSPORT_API_VALUES,
    TRANSPORTS,
)
from .models import FFAgentConfigEntry, ReplyAction, ReplyResult

_LOGGER = logging.getLogger(__name__)

ZERO = timedelta(0)
REPEAT_GUARD = timedelta(seconds=REPLY_REPEAT_GUARD_SECONDS)

type Location = tuple[float, float]  # latitude, longitude


class ReplyError(Exception):
    """A reply could not be delivered. The text never contains the URL."""


class ReplyConnectionError(ReplyError):
    """There was no response: timeout, no connection, or another client error."""

    def __init__(self, error_type: str) -> None:
        """Keep only the class name of the underlying error."""
        super().__init__(f"No response from FF Agent ({error_type})")
        self.error_type = error_type


class ReplyHttpError(ReplyError):
    """FF Agent answered with a status outside of 2xx."""

    def __init__(self, status: int) -> None:
        """Keep the HTTP status."""
        super().__init__(f"FF Agent answered with HTTP status {status}")
        self.status = status


class ReplyClient:
    """Sends the replies of one config entry (one person).

    One request at a time: the lock makes a double click wait for the first request,
    and the repeat guard then skips the second one.
    """

    def __init__(
        self, hass: HomeAssistant, entry_id: str, host: str, reply_id: str
    ) -> None:
        """Initialize the client with the checked host and the reply ID."""
        self._hass = hass
        self._signal = SIGNAL_REPLY.format(entry_id=entry_id)
        self._host = host
        self._reply_id = reply_id
        self._lock = asyncio.Lock()
        # Only the last success counts: after accept, reject, accept the third reply
        # is not a repetition, because FF Agent holds the rejection by then.
        self._last_success: tuple[ReplyAction, datetime] | None = None

        self.last_result: ReplyResult | None = None
        # Counters for the diagnostics. Only real requests count as attempts.
        self.attempts_total = 0
        self.succeeded_total = 0
        self.failed_total = 0
        self.skipped_total = 0

    def _url(self, action: ReplyAction) -> str:
        """Return the URL of a reply. It is a secret and must never be logged."""
        return f"https://{self._host}" + REPLY_PATH.format(
            reply_id=self._reply_id, action=action.value
        )

    async def async_send(
        self,
        action: ReplyAction,
        *,
        transport: str | None = None,
        location: Location | None = None,
    ) -> ReplyResult:
        """Send a reply and return the result.

        The transport and the location are only sent with an acceptance. The same
        reply right after the last successful one is skipped without a request; a
        different reply in between (accept, reject, accept) makes it a new reply.

        Raises ReplyConnectionError if there was no response and ReplyHttpError if the
        status is not 2xx. The result is stored in both cases.
        """
        async with self._lock:
            started = dt_util.utcnow()
            last = self._last_success
            # A repetition is the same action as the last success, within the window.
            # A negative difference means the clock jumped back: not a repetition.
            if (
                last is not None
                and last[0] is action
                and ZERO <= started - last[1] < REPEAT_GUARD
            ):
                self.skipped_total += 1
                _LOGGER.debug("Reply %s skipped: it was just sent", action.value)
                return ReplyResult(action, started, success=True, skipped=True)

            params: dict[str, str] = {}
            if action is ReplyAction.ACCEPT:
                if transport is not None:
                    params["transport"] = transport
                if location is not None:
                    params["lat"] = f"{location[0]:.6f}"
                    params["lng"] = f"{location[1]:.6f}"

            _LOGGER.debug("Sending reply %s", action.value)
            status: int | None = None
            content_type: str | None = None
            error_type: str | None = None
            try:
                session = async_get_clientsession(self._hass)
                async with session.get(
                    self._url(action),
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=REPLY_TIMEOUT_SECONDS),
                    # To be checked after the first real test (A6): whether FF Agent
                    # redirects at all, and to which host (TODO 261017-reply-redirects).
                    allow_redirects=True,
                ) as response:
                    # The body is not read, evaluated or logged.
                    status = response.status
                    content_type = response.content_type
            except (TimeoutError, aiohttp.ClientError) as err:
                # The text of the error contains the URL: keep the class name only.
                error_type = type(err).__name__

            success = (
                error_type is None
                and status is not None
                and HTTPStatus.OK <= status < HTTPStatus.MULTIPLE_CHOICES
            )
            media = content_type[:MAX_CONTENT_TYPE_CHARS] if content_type else None
            result = ReplyResult(
                action,
                dt_util.utcnow(),
                success=success,
                status=status,
                content_type=media,
                error_type=error_type,
            )
            self._record(result)

            # Raised outside of the except block above and without a cause, so that
            # neither a traceback nor a log record can contain the URL.
            if error_type is not None:
                _LOGGER.warning("Reply %s: %s", action.value, error_type)
                raise ReplyConnectionError(error_type) from None
            if not success:
                _LOGGER.warning("Reply %s: HTTP status %s", action.value, status)
                raise ReplyHttpError(status or 0) from None
            _LOGGER.debug("Reply %s sent: HTTP status %s", action.value, status)
            return result

    def _record(self, result: ReplyResult) -> None:
        """Count the result, remember it and tell the entities."""
        self.attempts_total += 1
        if result.success:
            self.succeeded_total += 1
            self._last_success = (result.action, result.at)
        else:
            self.failed_total += 1
        self.last_result = result
        async_dispatcher_send(self._hass, self._signal, result)


def resolve_location(hass: HomeAssistant, entity_id: str) -> Location | None:
    """Return the coordinates of an entity (person, device tracker) or None.

    The log never contains the entity or the coordinates: where a person is, is
    private.
    """
    state = hass.states.get(entity_id)
    if state is None:
        _LOGGER.debug("Location entity not found, replying without location")
        return None
    try:
        latitude = float(state.attributes[ATTR_LATITUDE])
        longitude = float(state.attributes[ATTR_LONGITUDE])
    except KeyError, TypeError, ValueError:
        _LOGGER.debug("Location entity has no coordinates, replying without them")
        return None
    # NaN and infinity fail these comparisons as well.
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        _LOGGER.debug("Location entity has invalid coordinates, not using them")
        return None
    return latitude, longitude


def valid_latitude(value: object) -> bool:
    """Return whether the value is a latitude (NaN and infinity are not)."""
    try:
        return -90 <= float(value) <= 90
    except TypeError, ValueError, OverflowError:
        return False


def valid_longitude(value: object) -> bool:
    """Return whether the value is a longitude (NaN and infinity are not)."""
    try:
        return -180 <= float(value) <= 180
    except TypeError, ValueError, OverflowError:
        return False


def home_position(hass: HomeAssistant) -> Location | None:
    """Return the home position of Home Assistant or None if it is not set.

    Home Assistant starts with 0, 0 until the user sets the position.
    """
    latitude = hass.config.latitude
    longitude = hass.config.longitude
    usable = valid_latitude(latitude) and valid_longitude(longitude)
    if not usable or (latitude, longitude) == (0, 0):
        return None
    return float(latitude), float(longitude)


def resolve_home_location(hass: HomeAssistant) -> Location | None:
    """Return the home position for an acceptance or None (send no location).

    Read from the core configuration every time, so a change of the home position
    applies to the next acceptance. The log never contains the coordinates.
    """
    location = home_position(hass)
    if location is None:
        _LOGGER.debug("Home position is not set, replying without location")
    return location


def resolve_manual_location(options: Mapping[str, Any]) -> Location | None:
    """Return the coordinates stored in the options or None if they are unusable.

    The log never contains the coordinates.
    """
    latitude = options.get(CONF_LOCATION_LATITUDE)
    longitude = options.get(CONF_LOCATION_LONGITUDE)
    if not (valid_latitude(latitude) and valid_longitude(longitude)):
        _LOGGER.debug("Manual location is missing or invalid, replying without it")
        return None
    return float(latitude), float(longitude)


def configured_location_source(options: Mapping[str, Any]) -> str:
    """Return the location source of the options.

    Options from before the source existed have none: a location entity means the
    source "entity", otherwise there is no location. Unknown values are treated the
    same way.
    """
    value = options.get(CONF_LOCATION_SOURCE)
    if isinstance(value, str) and value in LOCATION_SOURCES:
        return value
    if options.get(CONF_LOCATION_ENTITY):
        return LOCATION_SOURCE_ENTITY
    return LOCATION_SOURCE_NONE


def resolve_configured_location(
    hass: HomeAssistant, options: Mapping[str, Any]
) -> Location | None:
    """Return the location of the configured source or None (send no location)."""
    source = configured_location_source(options)
    if source == LOCATION_SOURCE_HOME:
        return resolve_home_location(hass)
    if source == LOCATION_SOURCE_MANUAL:
        return resolve_manual_location(options)
    if source == LOCATION_SOURCE_ENTITY:
        if entity_id := options.get(CONF_LOCATION_ENTITY):
            return resolve_location(hass, entity_id)
        _LOGGER.debug("No location entity chosen, replying without location")
    return None


def configured_transport(value: object) -> str:
    """Return the transport of the option; unknown values give the default."""
    if isinstance(value, str):
        if value in TRANSPORT_API_VALUES:
            return value
        if value in LEGACY_TRANSPORTS:
            return LEGACY_TRANSPORTS[value]
    return DEFAULT_TRANSPORT


async def async_send_reply(
    hass: HomeAssistant,
    entry: FFAgentConfigEntry,
    action: ReplyAction,
    transport: str | None = None,
    location: Location | None = None,
) -> ReplyResult:
    """Send a reply for an entry; the common path of the buttons and the actions.

    Missing values come from the options of the entry: the transport from
    ``default_transport``, the location from the source ``location_source`` (none,
    home position, manual coordinates or a location entity). Without a usable
    location none is sent. Explicit values win. A refusal contains no address and is
    translated.
    """
    api_transport: str | None = None
    if action is ReplyAction.ACCEPT:
        if transport is None:
            configured = entry.options.get(CONF_DEFAULT_TRANSPORT)
            transport = configured_transport(configured)
        elif transport not in TRANSPORTS:
            # Only the values named by FF Agent are sent (A9).
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="invalid_transport",
                translation_placeholders={"transport": transport},
            )
        api_transport = TRANSPORT_API_VALUES[transport]
        if location is None:
            location = resolve_configured_location(hass, entry.options)
    else:
        location = None

    try:
        return await entry.runtime_data.reply.async_send(
            action, transport=api_transport, location=location
        )
    except ReplyConnectionError:
        raise HomeAssistantError(
            translation_domain=DOMAIN, translation_key="reply_connection_error"
        ) from None
    except ReplyHttpError as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="reply_http_error",
            translation_placeholders={"status": str(err.status)},
        ) from None
