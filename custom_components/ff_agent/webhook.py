"""Webhook handler of the FF Agent integration.

FF Agent calls the webhook when an alarm is sent. Nothing is assumed about the call:
the handler only records its shape (names, types, lengths), never a value. The
handler must answer fast, because FF Agent aborts after 5 seconds, so it makes no
external call.

Nothing from a call may be logged except its method and its length: neither header
values (the token), nor query values, nor body values.
"""

from __future__ import annotations

import hmac
import logging
from collections.abc import Awaitable, Callable, Iterable
from http import HTTPStatus
from itertools import islice
from typing import Any
from urllib.parse import parse_qs

from aiohttp import hdrs, web
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.util import dt as dt_util
from homeassistant.util.aiohttp import MockRequest
from homeassistant.util.json import json_loads

from .const import (
    CONF_HEADER_TOKEN,
    CONF_REQUIRE_TOKEN,
    DOMAIN,
    ISSUE_TOKEN_REJECTED,
    MAX_BODY_ANALYSIS_CHARS,
    MAX_CONTENT_TYPE_CHARS,
    MAX_NAME_CHARS,
    MAX_SHAPE_DEPTH,
    MAX_SHAPE_KEYS,
    MAX_USER_AGENT_CHARS,
    TOKEN_HEADER,
)
from .models import BodyKind, FFAgentConfigEntry, WebhookCall

_LOGGER = logging.getLogger(__name__)

# A call through a Nabu Casa cloudhook arrives as MockRequest.
type WebhookRequest = web.Request | MockRequest
type Handler = Callable[
    [HomeAssistant, str, WebhookRequest],
    Awaitable[web.Response | None],
]

FORM_CONTENT_TYPE = "application/x-www-form-urlencoded"


def _names(names: Iterable[str]) -> tuple[str, ...]:
    """Return unique, sorted and limited names (header names, keys)."""
    return tuple(sorted({name[:MAX_NAME_CHARS] for name in names})[:MAX_SHAPE_KEYS])


def _shape(obj: object, depth: int = 0) -> Any:
    """Return the shape of parsed JSON: keys and types instead of values."""
    if depth >= MAX_SHAPE_DEPTH:
        return "..."
    if isinstance(obj, dict):
        return {
            str(key)[:MAX_NAME_CHARS]: _shape(value, depth + 1)
            for key, value in islice(obj.items(), MAX_SHAPE_KEYS)
        }
    if isinstance(obj, list):
        label = f"list({len(obj)})"
        return [label, _shape(obj[0], depth + 1)] if obj else [label]
    if obj is None:
        return "null"
    if isinstance(obj, str):
        return f"str({len(obj)})"
    # bool, int and float: the type name is all that is kept.
    return type(obj).__name__


def _analyze_text(text: str, content_type: str | None) -> tuple[BodyKind, Any]:
    """Return the kind and the shape of a text body. Never raises."""
    lowered = (content_type or "").lower()
    analyzed = text[:MAX_BODY_ANALYSIS_CHARS]

    if not analyzed.strip():
        return "empty", None

    if "json" in lowered or analyzed.lstrip().startswith(("{", "[")):
        try:
            return "json", _shape(json_loads(analyzed))
        except Exception:
            # Any parse problem means "text"; the body is not stored anyway.
            return "text", None

    if lowered.split(";")[0].strip() == FORM_CONTENT_TYPE:
        return "form", list(_names(parse_qs(analyzed, keep_blank_values=True)))

    return "text", None


def _media_type(content_type: str | None) -> str | None:
    """Return only the media type of a Content-Type header, lower case and clipped."""
    if not content_type:
        return None
    return content_type.split(";")[0].strip().lower()[:MAX_CONTENT_TYPE_CHARS]


def _header_length(request: WebhookRequest) -> int:
    """Return the Content-Length header as number, 0 if missing or invalid."""
    try:
        return max(int(request.headers.get(hdrs.CONTENT_LENGTH, 0)), 0)
    except ValueError:
        return 0


async def async_capture_call(request: WebhookRequest) -> WebhookCall:
    """Record the shape of a webhook call. Never raises.

    The body is read with ``request.text()``: calls that arrive through a Nabu Casa
    cloudhook are a ``MockRequest``, which has no ``read()``.
    """
    headers = request.headers
    content_type = headers.get(hdrs.CONTENT_TYPE)
    user_agent = headers.get(hdrs.USER_AGENT)

    text: str | None
    try:
        text = await request.text()
    except UnicodeDecodeError:
        text = None
    except Exception as err:
        # Only the type is logged: the message of the error is not under our control.
        _LOGGER.debug("Could not read a webhook body: %s", type(err).__name__)
        text = None

    body_shape: Any = None
    if text is None:
        body_kind: BodyKind = "binary"
        body_length = _header_length(request)
    else:
        body_length = len(text)
        body_kind, body_shape = _analyze_text(text, content_type)

    return WebhookCall(
        received_at=dt_util.utcnow(),
        method=request.method,
        content_type=_media_type(content_type),
        body_length=body_length,
        header_names=_names(name.lower() for name in headers),
        user_agent=user_agent[:MAX_USER_AGENT_CHARS] if user_agent else None,
        query_keys=_names(request.query),
        body_kind=body_kind,
        body_shape=body_shape,
    )


def _token_is_valid(entry: FFAgentConfigEntry, request: WebhookRequest) -> bool:
    """Compare the token header with the stored token in constant time."""
    try:
        presented = request.headers.get(TOKEN_HEADER, "").encode()
    except UnicodeEncodeError:
        # Not even valid text, so certainly not the token.
        return False
    return hmac.compare_digest(presented, entry.data[CONF_HEADER_TOKEN].encode())


def async_build_handler(entry: FFAgentConfigEntry) -> Handler:
    """Return the webhook handler of a config entry."""

    async def async_handle(
        hass: HomeAssistant, webhook_id: str, request: WebhookRequest
    ) -> web.Response | None:
        """Handle a webhook call: 200 (None), or 401 for a missing or wrong token."""
        alarm = entry.runtime_data.alarm
        issue_id = ISSUE_TOKEN_REJECTED.format(entry_id=entry.entry_id)

        if entry.options.get(CONF_REQUIRE_TOKEN) and not _token_is_valid(
            entry, request
        ):
            alarm.async_handle_rejected()
            _LOGGER.debug("Rejected a webhook call: token missing or wrong")
            ir.async_create_issue(
                hass,
                DOMAIN,
                issue_id,
                is_fixable=False,
                is_persistent=True,
                severity=ir.IssueSeverity.WARNING,
                translation_key="webhook_token_rejected",
                translation_placeholders={"title": entry.title},
            )
            return web.Response(status=HTTPStatus.UNAUTHORIZED)

        # Idempotent: removes the hint of an earlier rejected call, if any.
        ir.async_delete_issue(hass, DOMAIN, issue_id)

        call = await async_capture_call(request)
        _LOGGER.debug(
            "Received a webhook call: method=%s, body_length=%d",
            call.method,
            call.body_length,
        )
        # Read the manager only now: during the await above the entry may have been
        # reloaded, and the call belongs to the manager that is current at this point.
        # While the entry is being unloaded there is none, and the call is dropped.
        if (runtime_data := getattr(entry, "runtime_data", None)) is not None:
            runtime_data.alarm.async_handle_call(call)
        return None

    return async_handle
