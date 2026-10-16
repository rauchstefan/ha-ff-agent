"""Tests for the FF Agent config flow."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ff_agent.const import DOMAIN


async def test_user_flow_shows_form(hass: HomeAssistant) -> None:
    """The user step shows a confirmation form without input fields."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_user_flow_creates_entry(hass: HomeAssistant) -> None:
    """Confirming the form creates a config entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "FF Agent"
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1


async def test_second_flow_aborts_single_instance(hass: HomeAssistant) -> None:
    """A second setup attempt is aborted because only one instance is allowed."""
    MockConfigEntry(domain=DOMAIN, title="FF Agent").add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_abort_does_not_create_second_entry(hass: HomeAssistant) -> None:
    """After the abort exactly the original entry exists."""
    existing = MockConfigEntry(domain=DOMAIN, title="FF Agent")
    existing.add_to_hass(hass)

    await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert hass.config_entries.async_entries(DOMAIN) == [existing]


async def test_created_entry_is_set_up(hass: HomeAssistant) -> None:
    """The entry created by the flow is loaded and has empty data."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={}
    )
    await hass.async_block_till_done()

    entry = result["result"]
    assert entry.data == {}
    assert entry.state is config_entries.ConfigEntryState.LOADED
