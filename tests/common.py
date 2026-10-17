"""Helpers shared by the tests."""

from __future__ import annotations

import sys
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
from types import ModuleType
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant import components
from homeassistant.config_entries import ConfigSubentryDataWithId
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .const import (
    CLOUDHOOK_URL,
    NTFY_ENTITY_ID,
    NTFY_SERVER,
    NTFY_SUBENTRY_ID,
    NTFY_TOPIC,
)

CLOUD_MODULE = "homeassistant.components.cloud"


class CloudNotAvailable(HomeAssistantError):
    """Stand-in for homeassistant.components.cloud.CloudNotAvailable."""


class CloudNotConnected(CloudNotAvailable):
    """Stand-in for homeassistant.components.cloud.CloudNotConnected."""


@contextmanager
def patch_cloud(
    hass: HomeAssistant,
    *,
    subscription: bool = True,
    connected: bool = True,
    cloudhook_url: str = CLOUDHOOK_URL,
) -> Generator[dict[str, Any]]:
    """Make the cloud integration look loaded.

    The real cloud integration cannot be imported in the test environment (its
    imports reach modules whose requirements are not installed), so a small stand-in
    module with the public helpers FF Agent uses replaces it.
    """
    mocks: dict[str, Any] = {
        "active_subscription": MagicMock(return_value=subscription),
        "is_connected": MagicMock(return_value=connected),
        "get_or_create": AsyncMock(return_value=cloudhook_url),
        "delete": AsyncMock(),
    }
    module = ModuleType(CLOUD_MODULE)
    module.async_active_subscription = mocks["active_subscription"]
    module.async_is_connected = mocks["is_connected"]
    module.async_get_or_create_cloudhook = mocks["get_or_create"]
    module.async_delete_cloudhook = mocks["delete"]
    # Used by the URL helpers of Home Assistant; there is no remote UI in the tests.
    module.async_remote_ui_url = MagicMock(side_effect=CloudNotAvailable)
    module.CloudNotAvailable = CloudNotAvailable
    module.CloudNotConnected = CloudNotConnected

    hass.config.components.add("cloud")
    try:
        with (
            patch.dict(sys.modules, {CLOUD_MODULE: module}),
            patch.object(components, "cloud", module, create=True),
        ):
            yield mocks
    finally:
        hass.config.components.remove("cloud")


async def async_setup_entry(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Add a config entry to Home Assistant and set it up."""
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def add_ntfy_entry(
    hass: HomeAssistant,
    topics: dict[str, str] | None = None,
    url: str = NTFY_SERVER,
) -> MockConfigEntry:
    """Add a config entry of the ntfy integration with one subentry per topic.

    The ntfy integration itself is never set up in the tests: only its config entry,
    its registry entries and its states are simulated.
    """
    if topics is None:
        topics = {NTFY_SUBENTRY_ID: NTFY_TOPIC}
    entry = MockConfigEntry(
        domain="ntfy",
        title="ntfy.sh",
        data={"url": url},
        subentries_data=[
            ConfigSubentryDataWithId(
                data={"topic": topic},
                subentry_id=subentry_id,
                subentry_type="topic",
                title="FF Agent Alarm",
                unique_id=topic,
            )
            for subentry_id, topic in topics.items()
        ],
    )
    entry.add_to_hass(hass)
    return entry


def add_ntfy_entity(
    hass: HomeAssistant,
    ntfy_entry: MockConfigEntry,
    subentry_id: str = NTFY_SUBENTRY_ID,
    entity_id: str = NTFY_ENTITY_ID,
    **kwargs: Any,
) -> er.RegistryEntry:
    """Register the event entity of an ntfy subscription."""
    return er.async_get(hass).async_get_or_create(
        "event",
        "ntfy",
        f"{subentry_id}_subscribe",
        config_entry=ntfy_entry,
        config_subentry_id=subentry_id,
        suggested_object_id=entity_id.split(".", 1)[1],
        **kwargs,
    )


def fire_ntfy(
    hass: HomeAssistant,
    timestamp: datetime | None = None,
    attributes: dict[str, Any] | None = None,
    entity_id: str = NTFY_ENTITY_ID,
) -> datetime:
    """Write a state like the ntfy event entity does for a message (GET /trigger)."""
    timestamp = timestamp or dt_util.utcnow()
    hass.states.async_set(
        entity_id,
        timestamp.isoformat(timespec="milliseconds"),
        {
            "event_type": "triggered",
            "message": "triggered",
            "topic": NTFY_TOPIC,
            **(attributes or {}),
        },
    )
    return timestamp
