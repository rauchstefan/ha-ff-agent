"""Tests for the migration of config entries (1.1 -> 1.2, ADR 0003)."""

from __future__ import annotations

import logging
from typing import Any
from unittest.mock import patch

import pytest
from homeassistant.components import webhook
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_WEBHOOK_ID
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ff_agent import async_migrate_entry
from custom_components.ff_agent.const import (
    CONF_ALARM_SOURCE,
    CONF_CLOUDHOOK,
    CONF_CLOUDHOOK_URL,
    CONF_HEADER_TOKEN,
    CONF_NTFY_ENTITY_UUID,
    CONF_NTFY_SERVER,
    CONF_NTFY_TOPIC,
    CONF_REPLY_HOST,
    CONF_REPLY_ID,
    DOMAIN,
    SOURCE_NTFY,
)
from custom_components.ff_agent.reply_url import reply_unique_id

from .const import HEADER_TOKEN, NTFY_TOPIC, REPLY_ID, WEBHOOK_ID

# The data of an entry created by version 0.1.0 (config entry version 1.1).
OLD_DATA: dict[str, Any] = {
    CONF_REPLY_ID: REPLY_ID,
    CONF_REPLY_HOST: "www.ff-agent.com",
    CONF_WEBHOOK_ID: WEBHOOK_ID,
    CONF_CLOUDHOOK: False,
    CONF_CLOUDHOOK_URL: None,
    CONF_HEADER_TOKEN: HEADER_TOKEN,
}


def _entry(
    data: dict[str, Any], version: int = 1, minor_version: int = 1
) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="FF Agent Test",
        unique_id=reply_unique_id(REPLY_ID),
        data=data,
        options={"reset_minutes": 30, "default_transport": "car"},
        version=version,
        minor_version=minor_version,
    )


async def test_entry_of_version_1_1_becomes_a_webhook_entry(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    """The alarm source and the empty ntfy keys are added, nothing else changes."""
    caplog.set_level(logging.DEBUG, logger="custom_components.ff_agent")
    entry = _entry(dict(OLD_DATA))
    entry.add_to_hass(hass)
    with patch(
        "homeassistant.components.webhook.async_register", wraps=webhook.async_register
    ) as register:
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert (entry.version, entry.minor_version) == (1, 2)
    assert dict(entry.data) == {
        **OLD_DATA,
        CONF_ALARM_SOURCE: "webhook",
        CONF_NTFY_ENTITY_UUID: None,
        CONF_NTFY_TOPIC: None,
        CONF_NTFY_SERVER: None,
    }
    assert dict(entry.options) == {"reset_minutes": 30, "default_transport": "car"}
    register.assert_called_once()
    assert register.call_args.args[3] == WEBHOOK_ID
    # Only the versions are logged, no data.
    for secret in (REPLY_ID, WEBHOOK_ID, HEADER_TOKEN):
        assert secret not in caplog.text


async def test_existing_values_win(hass: HomeAssistant) -> None:
    """A value that is already there is not overwritten by the defaults."""
    data = {**OLD_DATA, CONF_ALARM_SOURCE: SOURCE_NTFY, CONF_NTFY_TOPIC: NTFY_TOPIC}
    entry = _entry(data)
    entry.add_to_hass(hass)

    assert await async_migrate_entry(hass, entry)

    assert entry.minor_version == 2
    assert entry.data[CONF_ALARM_SOURCE] == SOURCE_NTFY
    assert entry.data[CONF_NTFY_TOPIC] == NTFY_TOPIC
    assert entry.data[CONF_NTFY_ENTITY_UUID] is None


async def test_entry_of_version_1_2_stays_as_it_is(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """A current entry is not touched."""
    mock_config_entry.add_to_hass(hass)
    data = dict(mock_config_entry.data)

    assert await async_migrate_entry(hass, mock_config_entry)

    assert dict(mock_config_entry.data) == data
    assert mock_config_entry.minor_version == 2


async def test_future_minor_version_is_accepted(
    hass: HomeAssistant, entry_data: dict[str, Any]
) -> None:
    """A higher minor version (downgrade of the integration) loads without change."""
    entry = _entry(entry_data, minor_version=3)
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert entry.minor_version == 3
    assert dict(entry.data) == entry_data


async def test_future_major_version_is_refused(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    """An entry of a future major version cannot be loaded."""
    entry = _entry(dict(OLD_DATA), version=2)
    entry.add_to_hass(hass)

    assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.MIGRATION_ERROR
    # The integration itself refuses it as well, if Home Assistant asks.
    assert not await async_migrate_entry(hass, entry)
    assert "version 2.1" in caplog.text
    assert dict(entry.data) == OLD_DATA
