"""Shared fixtures for the FF Agent tests."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

import pytest
from homeassistant.const import CONF_WEBHOOK_ID
from homeassistant.core import HomeAssistant
from homeassistant.core_config import async_process_ha_core_config
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ff_agent.const import (
    CONF_ALARM_SOURCE,
    CONF_CLOUDHOOK,
    CONF_CLOUDHOOK_URL,
    CONF_DEFAULT_TRANSPORT,
    CONF_HEADER_TOKEN,
    CONF_LOCATION_ENTITY,
    CONF_LOCATION_LATITUDE,
    CONF_LOCATION_LONGITUDE,
    CONF_LOCATION_SOURCE,
    CONF_NTFY_ENTITY_UUID,
    CONF_NTFY_SERVER,
    CONF_NTFY_TOPIC,
    CONF_REPLY_HOST,
    CONF_REPLY_ID,
    CONF_REQUIRE_TOKEN,
    CONF_RESET_MINUTES,
    DEFAULT_REPLY_HOST,
    DEFAULT_RESET_MINUTES,
    DEFAULT_TRANSPORT,
    DOMAIN,
    LOCATION_SOURCE_ENTITY,
    LOCATION_SOURCE_HOME,
    LOCATION_SOURCE_MANUAL,
    LOCATION_SOURCE_NONE,
    SOURCE_NTFY,
    SOURCE_WEBHOOK,
)
from custom_components.ff_agent.reply_url import reply_unique_id

from .common import add_ntfy_entity, add_ntfy_entry, patch_cloud
from .const import (
    CLOUDHOOK_URL,
    EXTERNAL_URL,
    HEADER_TOKEN,
    LOCATION_ENTITY,
    MANUAL_LATITUDE,
    MANUAL_LONGITUDE,
    NTFY_SERVER,
    NTFY_TOPIC,
    OTHER_REPLY_ID,
    OTHER_WEBHOOK_ID,
    REPLY_ID,
    WEBHOOK_ID,
)


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
        CONF_ALARM_SOURCE: SOURCE_WEBHOOK,
        CONF_NTFY_ENTITY_UUID: None,
        CONF_NTFY_TOPIC: None,
        CONF_NTFY_SERVER: None,
    }


@pytest.fixture
def entry_options() -> dict[str, Any]:
    """Default options of a freshly created entry."""
    return {
        CONF_RESET_MINUTES: DEFAULT_RESET_MINUTES,
        CONF_DEFAULT_TRANSPORT: DEFAULT_TRANSPORT,
        CONF_REQUIRE_TOKEN: False,
        CONF_LOCATION_SOURCE: LOCATION_SOURCE_NONE,
    }


@pytest.fixture
def mock_config_entry(
    entry_data: dict[str, Any], entry_options: dict[str, Any]
) -> MockConfigEntry:
    """Return a config entry for one placeholder person."""
    return MockConfigEntry(
        domain=DOMAIN,
        minor_version=2,
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
        minor_version=2,
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
        minor_version=2,
        title=mock_config_entry.title,
        unique_id=mock_config_entry.unique_id,
        data=entry_data,
        options={**mock_config_entry.options, CONF_REQUIRE_TOKEN: True},
    )


def _entry_with_options(
    mock_config_entry: MockConfigEntry,
    entry_data: dict[str, Any],
    extra: dict[str, Any],
) -> MockConfigEntry:
    """Return the standard entry with additional options."""
    return MockConfigEntry(
        domain=DOMAIN,
        minor_version=2,
        title=mock_config_entry.title,
        unique_id=mock_config_entry.unique_id,
        data=entry_data,
        options={**mock_config_entry.options, **extra},
    )


@pytest.fixture
def location_entry(
    mock_config_entry: MockConfigEntry, entry_data: dict[str, Any]
) -> MockConfigEntry:
    """Return a config entry whose acceptance sends the location of an entity."""
    return _entry_with_options(
        mock_config_entry,
        entry_data,
        {
            CONF_LOCATION_SOURCE: LOCATION_SOURCE_ENTITY,
            CONF_LOCATION_ENTITY: LOCATION_ENTITY,
        },
    )


@pytest.fixture
def legacy_location_entry(
    mock_config_entry: MockConfigEntry, entry_data: dict[str, Any]
) -> MockConfigEntry:
    """Return an entry from before the location source: only the location entity."""
    options = {
        key: value
        for key, value in mock_config_entry.options.items()
        if key != CONF_LOCATION_SOURCE
    }
    return MockConfigEntry(
        domain=DOMAIN,
        minor_version=2,
        title=mock_config_entry.title,
        unique_id=mock_config_entry.unique_id,
        data=entry_data,
        options={**options, CONF_LOCATION_ENTITY: LOCATION_ENTITY},
    )


@pytest.fixture
def home_location_entry(
    mock_config_entry: MockConfigEntry, entry_data: dict[str, Any]
) -> MockConfigEntry:
    """Return a config entry whose acceptance sends the home position of HA."""
    return _entry_with_options(
        mock_config_entry, entry_data, {CONF_LOCATION_SOURCE: LOCATION_SOURCE_HOME}
    )


@pytest.fixture
def manual_location_entry(
    mock_config_entry: MockConfigEntry, entry_data: dict[str, Any]
) -> MockConfigEntry:
    """Return a config entry whose acceptance sends stored coordinates."""
    return _entry_with_options(
        mock_config_entry,
        entry_data,
        {
            CONF_LOCATION_SOURCE: LOCATION_SOURCE_MANUAL,
            CONF_LOCATION_LATITUDE: MANUAL_LATITUDE,
            CONF_LOCATION_LONGITUDE: MANUAL_LONGITUDE,
        },
    )


@pytest.fixture
def other_entry(
    mock_config_entry: MockConfigEntry, entry_data: dict[str, Any]
) -> MockConfigEntry:
    """Return the config entry of a second person (other reply ID, other webhook)."""
    return MockConfigEntry(
        domain=DOMAIN,
        minor_version=2,
        title="FF Agent Other",
        unique_id=reply_unique_id(OTHER_REPLY_ID),
        data={
            **entry_data,
            CONF_REPLY_ID: OTHER_REPLY_ID,
            CONF_WEBHOOK_ID: OTHER_WEBHOOK_ID,
            CONF_HEADER_TOKEN: HEADER_TOKEN + "-other",
        },
        options=dict(mock_config_entry.options),
    )


@pytest.fixture
def ntfy_config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Return a config entry of the ntfy integration with one topic (not set up)."""
    return add_ntfy_entry(hass)


@pytest.fixture
def ntfy_entity(
    hass: HomeAssistant, ntfy_config_entry: MockConfigEntry
) -> er.RegistryEntry:
    """Return the registry entry of the ntfy event entity of the topic."""
    return add_ntfy_entity(hass, ntfy_config_entry)


@pytest.fixture
def ntfy_entry(
    entry_data: dict[str, Any],
    entry_options: dict[str, Any],
    ntfy_entity: er.RegistryEntry,
) -> MockConfigEntry:
    """Return a config entry that receives the alarm through ntfy."""
    return MockConfigEntry(
        domain=DOMAIN,
        minor_version=2,
        title="FF Agent Test",
        unique_id=reply_unique_id(REPLY_ID),
        data={
            **entry_data,
            CONF_ALARM_SOURCE: SOURCE_NTFY,
            CONF_NTFY_ENTITY_UUID: ntfy_entity.id,
            CONF_NTFY_TOPIC: NTFY_TOPIC,
            CONF_NTFY_SERVER: NTFY_SERVER,
        },
        options=entry_options,
    )
