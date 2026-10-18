"""Tests for the alarm manager: deduplication, reset timer and signals."""

from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass, field
from datetime import timedelta

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.ff_agent.alarm import AlarmManager, clamp_reset_minutes
from custom_components.ff_agent.const import (
    DEDUP_SECONDS,
    DEFAULT_RESET_MINUTES,
    MAX_RESET_MINUTES,
    MIN_RESET_MINUTES,
    SIGNAL_ALARM,
    SIGNAL_ALARM_STATE,
)
from custom_components.ff_agent.models import AlarmEvent, WebhookCall

ENTRY_ID = "test-entry-id"
RESET_MINUTES = 30


@dataclass
class Signals:
    """What the alarm manager sent through the dispatcher."""

    alarms: list[AlarmEvent] = field(default_factory=list)
    states: int = 0


def _call() -> WebhookCall:
    """Return a call that was received now (the frozen time)."""
    return WebhookCall(
        received_at=dt_util.utcnow(),
        method="POST",
        content_type=None,
        body_length=0,
        header_names=(),
        user_agent=None,
        query_keys=(),
        body_kind="empty",
        body_shape=None,
    )


async def _advance(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, delta: timedelta
) -> None:
    """Let time pass and fire the timers that are due."""
    freezer.tick(delta)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


@pytest.fixture
def manager(hass: HomeAssistant) -> Generator[AlarmManager]:
    """Return a manager with the default reset time, shut down after the test."""
    alarm_manager = AlarmManager(hass, ENTRY_ID, RESET_MINUTES)
    yield alarm_manager
    alarm_manager.async_shutdown()


@pytest.fixture
def signals(hass: HomeAssistant) -> Generator[Signals]:
    """Record the dispatcher signals of the manager."""
    recorded = Signals()

    @callback
    def _on_alarm(event: AlarmEvent) -> None:
        recorded.alarms.append(event)

    @callback
    def _on_state() -> None:
        recorded.states += 1

    unsubscribe = [
        async_dispatcher_connect(
            hass, SIGNAL_ALARM.format(entry_id=ENTRY_ID), _on_alarm
        ),
        async_dispatcher_connect(
            hass, SIGNAL_ALARM_STATE.format(entry_id=ENTRY_ID), _on_state
        ),
    ]
    yield recorded
    for remove in unsubscribe:
        remove()


async def test_first_call_activates_and_dispatches(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    manager: AlarmManager,
    signals: Signals,
) -> None:
    """The first call is an alarm: active, counted, and both signals are sent."""
    call = _call()

    manager.async_handle_call(call)
    await hass.async_block_till_done()

    assert manager.active is True
    assert manager.last_alarm == call.received_at
    assert manager.active_until == call.received_at + timedelta(minutes=RESET_MINUTES)
    assert manager.last_call is call
    assert (manager.calls_total, manager.alarms_total) == (1, 1)
    assert (manager.deduplicated_total, manager.rejected_total) == (0, 0)
    assert signals.alarms == [AlarmEvent(call.received_at)]
    assert signals.states == 1


async def test_second_call_after_10_seconds_is_deduplicated(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    manager: AlarmManager,
    signals: Signals,
) -> None:
    """A repetition is only counted: no new alarm, no signal, the timer runs on."""
    first = _call()
    manager.async_handle_call(first)
    active_until = manager.active_until
    await _advance(hass, freezer, timedelta(seconds=10))

    second = _call()
    manager.async_handle_call(second)
    await hass.async_block_till_done()

    assert (manager.calls_total, manager.alarms_total) == (2, 1)
    assert manager.deduplicated_total == 1
    assert manager.last_call is second
    assert manager.last_alarm == first.received_at
    assert manager.active_until == active_until
    assert signals.alarms == [AlarmEvent(first.received_at)]
    assert signals.states == 1


@pytest.mark.parametrize(
    ("delay_seconds", "alarms", "deduplicated"),
    [
        (0, 1, 1),
        (10, 1, 1),
        (DEDUP_SECONDS - 1, 1, 1),
        (DEDUP_SECONDS, 2, 0),
        (DEDUP_SECONDS + 1, 2, 0),
    ],
)
async def test_dedup_window_is_30_seconds(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    manager: AlarmManager,
    delay_seconds: int,
    alarms: int,
    deduplicated: int,
) -> None:
    """Less than 30 seconds after the last alarm is a repetition, 30 seconds is not."""
    manager.async_handle_call(_call())
    await _advance(hass, freezer, timedelta(seconds=delay_seconds))

    manager.async_handle_call(_call())

    assert (manager.alarms_total, manager.deduplicated_total) == (alarms, deduplicated)
    assert manager.calls_total == 2


async def test_call_after_31_seconds_is_a_new_alarm_and_restarts_the_timer(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    manager: AlarmManager,
    signals: Signals,
) -> None:
    """A later call starts a new alarm; the reset time counts from that one."""
    first = _call()
    manager.async_handle_call(first)
    await _advance(hass, freezer, timedelta(seconds=31))

    second = _call()
    manager.async_handle_call(second)
    await hass.async_block_till_done()

    assert manager.alarms_total == 2
    assert manager.last_alarm == second.received_at
    assert manager.active_until == second.received_at + timedelta(minutes=30)
    assert signals.alarms == [
        AlarmEvent(first.received_at),
        AlarmEvent(second.received_at),
    ]
    assert signals.states == 2

    # The first timer would be over now (30 minutes after the first alarm). The new
    # alarm restarted it, so the state stays on ...
    await _advance(hass, freezer, timedelta(minutes=29, seconds=40))
    assert manager.active is True
    # ... until 30 minutes after the second alarm.
    await _advance(hass, freezer, timedelta(seconds=30))
    assert manager.active is False


async def test_active_ends_after_the_reset_time(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    manager: AlarmManager,
    signals: Signals,
) -> None:
    """After the reset time the state is off again and only the state signal is sent."""
    call = _call()
    manager.async_handle_call(call)
    await hass.async_block_till_done()

    await _advance(hass, freezer, timedelta(minutes=29))
    assert manager.active is True
    assert manager.active_until is not None

    await _advance(hass, freezer, timedelta(minutes=1, seconds=1))
    assert manager.active is False
    assert manager.active_until is None
    # The time of the last alarm stays: it is not part of "active".
    assert manager.last_alarm == call.received_at
    assert signals.states == 2
    assert len(signals.alarms) == 1


async def test_shutdown_cancels_the_timer(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, manager: AlarmManager
) -> None:
    """After the shutdown the reset timer does nothing any more."""
    manager.async_handle_call(_call())

    manager.async_shutdown()
    await _advance(hass, freezer, timedelta(minutes=31))

    # Nobody reset the state, so the timer really did not run.
    assert manager.active is True


async def test_shutdown_without_a_timer_does_nothing(manager: AlarmManager) -> None:
    """Shutting down twice, or before any alarm, is harmless."""
    manager.async_shutdown()
    manager.async_shutdown()

    assert manager.active is False


async def test_call_during_shutdown_is_ignored(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    manager: AlarmManager,
    signals: Signals,
) -> None:
    """A call that was in flight while the entry unloaded starts no timer."""
    manager.async_shutdown()

    manager.async_handle_call(_call())
    await hass.async_block_till_done()

    assert manager.calls_total == 0
    assert manager.active is False
    assert signals.alarms == []
    assert signals.states == 0
    # No lingering timer: nothing happens, however long we wait.
    await _advance(hass, freezer, timedelta(minutes=31))
    assert signals.states == 0


async def test_rejected_calls_are_counted(manager: AlarmManager) -> None:
    """A rejected call changes only its own counter."""
    manager.async_handle_rejected()
    manager.async_handle_rejected()

    assert manager.rejected_total == 2
    assert (manager.calls_total, manager.alarms_total) == (0, 0)
    assert manager.active is False


async def test_default_reset_time(hass: HomeAssistant) -> None:
    """Without a value the reset time is the default of 30 minutes."""
    assert DEFAULT_RESET_MINUTES == 30
    assert AlarmManager(hass, ENTRY_ID).reset_minutes == DEFAULT_RESET_MINUTES


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (15, 15),
        (MIN_RESET_MINUTES, MIN_RESET_MINUTES),
        (MAX_RESET_MINUTES, MAX_RESET_MINUTES),
        (0, MIN_RESET_MINUTES),
        (-5, MIN_RESET_MINUTES),
        (MAX_RESET_MINUTES + 1, MAX_RESET_MINUTES),
    ],
)
async def test_reset_time_is_limited(
    hass: HomeAssistant, value: float, expected: float
) -> None:
    """A value outside the range the options allow is brought into that range."""
    assert clamp_reset_minutes(value) == expected
    assert AlarmManager(hass, ENTRY_ID, value).reset_minutes == expected


async def test_call_after_the_clock_jumped_back_is_a_new_alarm(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    manager: AlarmManager,
    signals: Signals,
) -> None:
    """A negative time difference is no repetition: the call starts a new alarm."""
    first = _call()
    manager.async_handle_call(first)
    freezer.tick(timedelta(hours=-1))

    second = _call()
    manager.async_handle_call(second)
    await hass.async_block_till_done()

    assert second.received_at < first.received_at
    assert (manager.alarms_total, manager.deduplicated_total) == (2, 0)
    assert manager.last_alarm == second.received_at
    assert signals.alarms == [
        AlarmEvent(first.received_at),
        AlarmEvent(second.received_at),
    ]


# --- Alarms of any source (ntfy) -----------------------


async def test_handle_alarm_returns_whether_it_is_new(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    manager: AlarmManager,
    signals: Signals,
) -> None:
    """A new alarm returns True, a repetition False; no webhook call is counted."""
    now = dt_util.utcnow()

    assert manager.async_handle_alarm(now) is True
    assert manager.async_handle_alarm(now + timedelta(seconds=5)) is False
    await hass.async_block_till_done()

    assert (manager.alarms_total, manager.deduplicated_total) == (1, 1)
    assert (manager.calls_total, manager.last_call) == (0, None)
    assert manager.active
    assert manager.last_alarm == now
    assert [event.received_at for event in signals.alarms] == [now]


async def test_handle_alarm_after_shutdown_does_nothing(
    hass: HomeAssistant, manager: AlarmManager, signals: Signals
) -> None:
    """After the shutdown no alarm is recognized and no timer starts."""
    manager.async_shutdown()

    assert manager.async_handle_alarm(dt_util.utcnow()) is False
    await hass.async_block_till_done()

    assert manager.alarms_total == 0
    assert not manager.active
    assert signals.alarms == []
