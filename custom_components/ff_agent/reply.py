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
from datetime import datetime, timedelta
from http import HTTPStatus

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
    DEFAULT_TRANSPORT,
    DOMAIN,
    LEGACY_TRANSPORTS,
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
    ``default_transport``, the location from the entity ``location_entity``. Without
    that option no location is sent. Explicit values win. A refusal contains no
    address and is translated.
    """
    api_transport: str | None = None
    if action is ReplyAction.ACCEPT:
        if transport is None:
            configured = entry.options.get(CONF_DEFAULT_TRANSPORT)
            transport = configured_transport(configured)
        elif transport not in TRANSPORTS:
            # Only verified values are sent (A9).
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="invalid_transport",
                translation_placeholders={"transport": transport},
            )
        api_transport = TRANSPORT_API_VALUES[transport]
        entity_id = entry.options.get(CONF_LOCATION_ENTITY)
        if location is None and entity_id:
            location = resolve_location(hass, entity_id)
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
