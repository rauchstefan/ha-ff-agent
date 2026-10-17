"""Helpers shared by the tests."""

from __future__ import annotations

import sys
from collections.abc import Generator
from contextlib import contextmanager
from types import ModuleType
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant import components
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import CLOUDHOOK_URL

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
