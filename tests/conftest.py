"""Shared fixtures for the FF Agent tests."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

import pytest
from homeassistant.const import CONF_WEBHOOK_ID
from homeassistant.core import HomeAssistant
from homeassistant.core_config import async_process_ha_core_config
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ff_agent.const import (
    CONF_CLOUDHOOK,
    CONF_CLOUDHOOK_URL,
    CONF_DEFAULT_TRANSPORT,
    CONF_HEADER_TOKEN,
    CONF_REPLY_HOST,
    CONF_REPLY_ID,
    CONF_REQUIRE_TOKEN,
    CONF_RESET_MINUTES,
    DEFAULT_REPLY_HOST,
    DEFAULT_RESET_MINUTES,
    DEFAULT_TRANSPORT,
    DOMAIN,
)
from custom_components.ff_agent.reply_url import reply_unique_id

from .common import patch_cloud
from .const import CLOUDHOOK_URL, EXTERNAL_URL, HEADER_TOKEN, REPLY_ID, WEBHOOK_ID


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> Generator[None]:
    """Enable loading of custom integrations in every test."""
    yield


@pytest.fixture
async def external_url(hass: HomeAssistant) -> str:
    """Give Home Assistant an external URL."""
    await async_process_ha_core_config(hass, {"external_url": EXTERNAL_URL})
    return EXTERNAL_URL


@pytest.fixture
def cloud(hass: HomeAssistant) -> Generator[dict[str, Any]]:
    """Cloud with an active subscription that is connected."""
    with patch_cloud(hass) as mocks:
        yield mocks


@pytest.fixture
def entry_data() -> dict[str, Any]:
    """Config entry data of an entry without cloudhook."""
    return {
        CONF_REPLY_ID: REPLY_ID,
        CONF_REPLY_HOST: DEFAULT_REPLY_HOST,
        CONF_WEBHOOK_ID: WEBHOOK_ID,
        CONF_CLOUDHOOK: False,
        CONF_CLOUDHOOK_URL: None,
        CONF_HEADER_TOKEN: HEADER_TOKEN,
    }


@pytest.fixture
def entry_options() -> dict[str, Any]:
    """Default options of a freshly created entry."""
    return {
        CONF_RESET_MINUTES: DEFAULT_RESET_MINUTES,
        CONF_DEFAULT_TRANSPORT: DEFAULT_TRANSPORT,
        CONF_REQUIRE_TOKEN: False,
    }


@pytest.fixture
def mock_config_entry(
    entry_data: dict[str, Any], entry_options: dict[str, Any]
) -> MockConfigEntry:
    """Return a config entry for one placeholder person."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="FF Agent Test",
        unique_id=reply_unique_id(REPLY_ID),
        data=entry_data,
        options=entry_options,
    )


@pytest.fixture
def cloudhook_entry(
    mock_config_entry: MockConfigEntry, entry_data: dict[str, Any]
) -> MockConfigEntry:
    """Return a config entry that uses a cloudhook."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=mock_config_entry.title,
        unique_id=mock_config_entry.unique_id,
        data={**entry_data, CONF_CLOUDHOOK: True, CONF_CLOUDHOOK_URL: CLOUDHOOK_URL},
        options=dict(mock_config_entry.options),
    )


@pytest.fixture
def token_entry(
    mock_config_entry: MockConfigEntry, entry_data: dict[str, Any]
) -> MockConfigEntry:
    """Return a config entry that requires the additional token."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=mock_config_entry.title,
        unique_id=mock_config_entry.unique_id,
        data=entry_data,
        options={**mock_config_entry.options, CONF_REQUIRE_TOKEN: True},
    )
