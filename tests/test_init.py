"""Tests for setting up, unloading and removing the FF Agent integration."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from homeassistant.components import webhook
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ff_agent.const import (
    DOMAIN,
    ISSUE_TOKEN_REJECTED,
    WEBHOOK_ALLOWED_METHODS,
)
from custom_components.ff_agent.models import FFAgentData

from .common import CloudNotAvailable, patch_cloud
from .const import WEBHOOK_ID


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def _dummy_handler(hass: HomeAssistant, webhook_id: str, request: object) -> None:
    """Do nothing; only used to probe whether a webhook ID is taken."""


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


async def test_setup_creates_runtime_data(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Setting up an entry stores fresh runtime data with empty counters."""
    await _setup(hass, mock_config_entry)

    assert isinstance(mock_config_entry.runtime_data, FFAgentData)
    stats = mock_config_entry.runtime_data.webhook_stats
    assert (stats.calls_total, stats.rejected_total, stats.last_call) == (0, 0, None)


async def test_setup_registers_the_webhook(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """The webhook is open to the internet and accepts exactly GET and POST."""
    with patch(
        "homeassistant.components.webhook.async_register", wraps=webhook.async_register
    ) as register:
        await _setup(hass, mock_config_entry)

    register.assert_called_once()
    args, kwargs = register.call_args
    assert args[:4] == (hass, DOMAIN, mock_config_entry.title, WEBHOOK_ID)
    assert kwargs == {
        "local_only": False,
        "allowed_methods": list(WEBHOOK_ALLOWED_METHODS),
    }
    assert WEBHOOK_ALLOWED_METHODS == ("GET", "POST")


async def test_unload_unregisters_the_webhook(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """After unloading the webhook ID is free again."""
    await _setup(hass, mock_config_entry)
    with pytest.raises(ValueError):
        webhook.async_register(hass, DOMAIN, "Other", WEBHOOK_ID, _dummy_handler)

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    webhook.async_register(hass, DOMAIN, "Other", WEBHOOK_ID, _dummy_handler)
    webhook.async_unregister(hass, WEBHOOK_ID)


async def test_remove_entry_deletes_the_repair_issue(
    hass: HomeAssistant, token_entry: MockConfigEntry
) -> None:
    """A stale hint about a rejected call does not outlive its entry."""
    await _setup(hass, token_entry)
    issue_id = ISSUE_TOKEN_REJECTED.format(entry_id=token_entry.entry_id)
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key="webhook_token_rejected",
        translation_placeholders={"title": token_entry.title},
    )
    registry = ir.async_get(hass)
    assert registry.async_get_issue(DOMAIN, issue_id) is not None

    await hass.config_entries.async_remove(token_entry.entry_id)

    assert registry.async_get_issue(DOMAIN, issue_id) is None
