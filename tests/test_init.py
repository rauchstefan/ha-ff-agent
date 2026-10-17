"""Tests for setting up, unloading and removing the FF Agent integration."""

from __future__ import annotations

from typing import Any

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ff_agent.const import (
    CONF_CLOUDHOOK,
    CONF_CLOUDHOOK_URL,
    DOMAIN,
)

from .common import CloudNotAvailable, patch_cloud
from .const import CLOUDHOOK_URL, WEBHOOK_ID


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_setup_and_unload_entry(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """A config entry can be set up and unloaded again."""
    await _setup(hass, mock_config_entry)
    assert mock_config_entry.state is ConfigEntryState.LOADED

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED


async def test_unload_removes_no_entry(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Unloading keeps the entry registered, only its state changes."""
    await _setup(hass, mock_config_entry)

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert hass.config_entries.async_entries(DOMAIN) == [mock_config_entry]


async def test_reload_entry(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """A loaded entry can be reloaded and ends up loaded again."""
    await _setup(hass, mock_config_entry)

    await hass.config_entries.async_reload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED


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


async def test_remove_entry_deletes_cloudhook(
    hass: HomeAssistant, cloudhook_entry: MockConfigEntry
) -> None:
    """Removing an entry with a cloudhook deletes the cloudhook."""
    await _setup(hass, cloudhook_entry)

    with patch_cloud(hass) as cloud_mocks:
        await hass.config_entries.async_remove(cloudhook_entry.entry_id)

    cloud_mocks["delete"].assert_awaited_once_with(hass, WEBHOOK_ID)
    assert hass.config_entries.async_entries(DOMAIN) == []


async def test_remove_entry_without_cloudhook(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Without a cloudhook nothing is deleted."""
    await _setup(hass, mock_config_entry)

    with patch_cloud(hass) as cloud_mocks:
        await hass.config_entries.async_remove(mock_config_entry.entry_id)

    cloud_mocks["delete"].assert_not_called()
    assert hass.config_entries.async_entries(DOMAIN) == []


async def test_remove_entry_without_cloud_integration(
    hass: HomeAssistant, cloudhook_entry: MockConfigEntry
) -> None:
    """A cloudhook entry is removed cleanly even if cloud is not loaded."""
    await _setup(hass, cloudhook_entry)
    assert "cloud" not in hass.config.components

    await hass.config_entries.async_remove(cloudhook_entry.entry_id)

    assert hass.config_entries.async_entries(DOMAIN) == []


@pytest.mark.parametrize("error", [CloudNotAvailable, ValueError])
async def test_remove_entry_ignores_cloudhook_errors(
    hass: HomeAssistant, cloudhook_entry: MockConfigEntry, error: type[Exception]
) -> None:
    """A failing cloudhook deletion does not block removing the entry."""
    await _setup(hass, cloudhook_entry)

    with patch_cloud(hass) as cloud_mocks:
        cloud_mocks["delete"].side_effect = error
        await hass.config_entries.async_remove(cloudhook_entry.entry_id)

    cloud_mocks["delete"].assert_awaited_once_with(hass, WEBHOOK_ID)
    assert hass.config_entries.async_entries(DOMAIN) == []
