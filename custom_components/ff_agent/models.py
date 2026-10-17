"""Data models of the FF Agent integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Literal

from homeassistant.config_entries import ConfigEntry

if TYPE_CHECKING:
    from .alarm import AlarmManager
    from .reply import ReplyClient

type BodyKind = Literal["empty", "json", "form", "text", "binary"]


@dataclass(frozen=True, slots=True)
class WebhookCall:
    """The shape of one incoming webhook call.

    Contains no values of the call (no header values, query values or body values),
    only names, types and lengths. That keeps mission data out of memory, logs and
    diagnostics even if FF Agent sends some.
    """

    received_at: datetime
    method: str
    content_type: str | None  # media type only, no parameters
    # Characters for a text body; for "binary" the bytes from the Content-Length header.
    body_length: int
    header_names: tuple[str, ...]  # sorted, lower case
    user_agent: str | None
    query_keys: tuple[str, ...]
    body_kind: BodyKind
    body_shape: Any

    def as_diagnostics(self) -> dict[str, Any]:
        """Return the call as JSON-serializable data for the diagnostics."""
        return {
            "received_at": self.received_at.isoformat(),
            "method": self.method,
            "content_type": self.content_type,
            "body_length": self.body_length,
            "header_names": list(self.header_names),
            "user_agent": self.user_agent,
            "query_keys": list(self.query_keys),
            "body_kind": self.body_kind,
            "body_shape": self.body_shape,
        }


@dataclass(frozen=True, slots=True)
class AlarmEvent:
    """A recognized alarm: a webhook call that was not a duplicate.

    It carries no mission data. A later ``details`` field is the extension point for
    mission details (see docs/architektur.md).
    """

    received_at: datetime


class ReplyAction(StrEnum):
    """The two replies to a mission; the value is the last part of the reply URL."""

    ACCEPT = "accept"
    REJECT = "reject"


@dataclass(frozen=True, slots=True)
class ReplyResult:
    """The outcome of one reply.

    Contains no URL and no reply ID: only what is needed to tell the user and the
    diagnostics what happened.
    """

    action: ReplyAction
    at: datetime
    success: bool
    status: int | None = None  # HTTP status, None if there was no response
    content_type: str | None = None  # media type of the response
    error_type: str | None = None  # class name of a connection error, never its text
    # True if the reply was not sent because the same reply had just succeeded.
    skipped: bool = False

    def as_diagnostics(self) -> dict[str, Any]:
        """Return the result as JSON-serializable data for the diagnostics."""
        return {
            "action": str(self.action),
            "at": self.at.isoformat(),
            "success": self.success,
            "status": self.status,
            "content_type": self.content_type,
            "error_type": self.error_type,
        }


@dataclass(slots=True)
class FFAgentData:
    """Runtime data of a config entry."""

    alarm: AlarmManager
    reply: ReplyClient


type FFAgentConfigEntry = ConfigEntry[FFAgentData]
