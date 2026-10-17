"""Parser for the personal FF Agent mission reply URL.

The URL (or the bare UUID in it) is a secret. Nothing in this module logs it, and
exception messages never contain the input.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass

from yarl import URL

from .const import DEFAULT_REPLY_HOST

REPLY_DOMAIN = "ff-agent.com"
_PATH_PARTS = ("app2", "missionreplies")
_ACTIONS = ("accept", "reject")
_LDH_HOST = re.compile(r"[a-z0-9-]+(\.[a-z0-9-]+)*")


class InvalidReplyUrl(ValueError):
    """The input is not a valid FF Agent mission reply URL or UUID."""


@dataclass(frozen=True)
class ReplyTarget:
    """Host and normalized reply ID extracted from the user's input."""

    host: str
    reply_id: str


def _parse_uuid(value: str) -> str:
    """Return the normalized, lower-case form of a UUID or raise."""
    try:
        return str(uuid.UUID(value))
    except ValueError:
        raise InvalidReplyUrl from None


def parse_reply_input(value: str) -> ReplyTarget:
    """Extract host and reply ID from a mission reply URL or a bare UUID."""
    value = value.strip()

    try:
        return ReplyTarget(DEFAULT_REPLY_HOST, str(uuid.UUID(value)))
    except ValueError:
        pass

    try:
        url = URL(value)
    except ValueError:
        raise InvalidReplyUrl from None

    host = url.host
    if (
        url.scheme != "https"
        or host is None
        or not host.isascii()
        or _LDH_HOST.fullmatch(host.lower()) is None
        or not (host == REPLY_DOMAIN or host.endswith(f".{REPLY_DOMAIN}"))
        or url.user is not None
        or url.password is not None
        or url.explicit_port not in (None, 443)
    ):
        raise InvalidReplyUrl

    parts = list(url.parts)
    if parts and parts[-1] == "":
        parts.pop()  # a trailing slash is allowed
    if (
        len(parts) != 5
        or parts[0] != "/"
        or tuple(parts[1:3]) != _PATH_PARTS
        or parts[4] not in _ACTIONS
    ):
        raise InvalidReplyUrl

    return ReplyTarget(host, _parse_uuid(parts[3]))


def reply_unique_id(reply_id: str) -> str:
    """Return a non-reversible unique ID for a reply ID (16 hex characters)."""
    return hashlib.sha256(reply_id.encode()).hexdigest()[:16]
