"""Tests for setting up and unloading the FF Agent integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ff_agent.const import DOMAIN


async def test_setup_and_unload_entry(hass: HomeAssistant) -> None:
    """A config entry can be set up and unloaded again."""
    entry = MockConfigEntry(domain=DOMAIN, title="FF Agent")
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_unload_removes_no_entry(hass: HomeAssistant) -> None:
    """Unloading keeps the entry registered, only its state changes."""
    entry = MockConfigEntry(domain=DOMAIN, title="FF Agent")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.config_entries.async_entries(DOMAIN) == [entry]


async def test_reload_entry(hass: HomeAssistant) -> None:
    """A loaded entry can be reloaded and ends up loaded again."""
    entry = MockConfigEntry(domain=DOMAIN, title="FF Agent")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
