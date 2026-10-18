"""Reload and restart in the ntfy mode must not cause a false alarm.

Gap tests from the QA of the plan 261017-alarmquelle-ntfy: the matrix names the restore
placeholder and the freshness window, these tests walk through whole restart sequences.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.const import ATTR_RESTORED, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .common import async_setup_entry, fire_ntfy
from .const import NTFY_ENTITY_ID

if TYPE_CHECKING:
    from freezegun.api import FrozenDateTimeFactory
    from pytest_homeassistant_custom_component.common import MockConfigEntry

NOW = "2026-10-17 12:00:00+00:00"


async def test_reload_of_the_entry_with_a_fresh_message_is_no_alarm(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, ntfy_entry: MockConfigEntry
) -> None:
    """The message of 5 s ago is known to the entity; a reload must not count it."""
    freezer.move_to(NOW)
    fire_ntfy(hass, dt_util.utcnow() - timedelta(seconds=5))
    await async_setup_entry(hass, ntfy_entry)
    assert ntfy_entry.runtime_data.alarm.alarms_total == 0

    assert await hass.config_entries.async_reload(ntfy_entry.entry_id)
    await hass.async_block_till_done()

    assert ntfy_entry.runtime_data.alarm.alarms_total == 0
    assert ntfy_entry.runtime_data.alarm.active is False

    # A real new message after the reload is still an alarm.
    freezer.tick(timedelta(seconds=20))
    fire_ntfy(hass)
    await hass.async_block_till_done()
    assert ntfy_entry.runtime_data.alarm.alarms_total == 1


async def test_restart_of_home_assistant_is_no_alarm_but_the_next_message_is(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, ntfy_entry: MockConfigEntry
) -> None:
    """Start: no state yet, then the placeholder, then the restored fresh value."""
    freezer.move_to(NOW)
    await async_setup_entry(hass, ntfy_entry)
    assert hass.states.get(NTFY_ENTITY_ID) is None

    hass.states.async_set(NTFY_ENTITY_ID, STATE_UNAVAILABLE, {ATTR_RESTORED: True})
    restored = fire_ntfy(hass, dt_util.utcnow() - timedelta(seconds=3))
    await hass.async_block_till_done()
    assert ntfy_entry.runtime_data.alarm.alarms_total == 0

    # The ntfy connection drops and returns with the same value: still no alarm.
    hass.states.async_set(NTFY_ENTITY_ID, STATE_UNAVAILABLE)
    fire_ntfy(hass, restored)
    await hass.async_block_till_done()
    assert ntfy_entry.runtime_data.alarm.alarms_total == 0

    freezer.tick(timedelta(seconds=40))
    fire_ntfy(hass)
    await hass.async_block_till_done()
    assert ntfy_entry.runtime_data.alarm.alarms_total == 1
