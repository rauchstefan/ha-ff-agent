"""Data models of the FF Agent integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal

from homeassistant.config_entries import ConfigEntry

if TYPE_CHECKING:
    from .alarm import AlarmManager

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


@dataclass(slots=True)
class FFAgentData:
    """Runtime data of a config entry."""

    alarm: AlarmManager


type FFAgentConfigEntry = ConfigEntry[FFAgentData]
