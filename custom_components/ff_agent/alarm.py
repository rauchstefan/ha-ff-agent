"""The alarm logic of the FF Agent integration.

The webhook hands every accepted call to the AlarmManager. The manager decides
whether the call is a new alarm or a repetition, keeps the state "alarm active" with
its reset timer and tells the entities through dispatcher signals. All of that is
synchronous and happens in memory only, so the webhook answers FF Agent fast.

Nothing here knows mission data: neither the calls nor the alarms carry any.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from homeassistant.core import CALLBACK_TYPE, HassJob, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_call_later
from homeassistant.util import dt as dt_util

from .const import (
    DEDUP_SECONDS,
    DEFAULT_RESET_MINUTES,
    MAX_RESET_MINUTES,
    MIN_RESET_MINUTES,
    SIGNAL_ALARM,
    SIGNAL_ALARM_STATE,
)
from .models import AlarmEvent, WebhookCall

_LOGGER = logging.getLogger(__name__)

ZERO = timedelta(0)
DEDUP_WINDOW = timedelta(seconds=DEDUP_SECONDS)


def clamp_reset_minutes(value: float) -> float:
    """Return the reset time limited to the range the options allow."""
    return max(MIN_RESET_MINUTES, min(MAX_RESET_MINUTES, value))


class AlarmManager:
    """State and counters of the alarms of one config entry (one person).

    After a restart of Home Assistant the manager starts empty: "alarm active" is off
    and the deduplication window is closed. Only the timestamp of the last alarm is
    restored, by the sensor.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        reset_minutes: float = DEFAULT_RESET_MINUTES,
    ) -> None:
        """Initialize the manager with the reset time in minutes."""
        self._hass = hass
        self._signal_alarm = SIGNAL_ALARM.format(entry_id=entry_id)
        self._signal_state = SIGNAL_ALARM_STATE.format(entry_id=entry_id)
        self._reset = timedelta(minutes=clamp_reset_minutes(reset_minutes))
        self._cancel_reset: CALLBACK_TYPE | None = None
        self._closed = False
        # The timer is irrelevant once Home Assistant stops; unloading cancels it.
        self._reset_job = HassJob(
            self._async_reset, "ff_agent alarm reset", cancel_on_shutdown=True
        )

        self.active = False
        self.last_alarm: datetime | None = None
        self.active_until: datetime | None = None
        self.calls_total = 0
        self.alarms_total = 0
        self.deduplicated_total = 0
        # Rejected calls (missing or wrong token) never become a WebhookCall, but they
        # belong to the same picture, so the manager counts them as well.
        self.rejected_total = 0
        self.last_call: WebhookCall | None = None

    @property
    def reset_minutes(self) -> float:
        """Return the reset time in minutes."""
        return self._reset.total_seconds() / 60

    @callback
    def async_handle_rejected(self) -> None:
        """Count a call that was rejected because of the additional token."""
        self.rejected_total += 1

    @callback
    def async_handle_call(self, call: WebhookCall) -> None:
        """Handle an accepted webhook call: a new alarm or a repetition."""
        if self._closed:
            # A call that was in flight while the entry unloaded: no timer may start.
            return

        self.calls_total += 1
        self.last_call = call
        self.async_handle_alarm(call.received_at)

    @callback
    def async_handle_alarm(self, received_at: datetime) -> bool:
        """Handle an alarm of any source: a new alarm or a repetition.

        Return True for a new alarm, False for a repetition or after the shutdown.
        """
        if self._closed:
            return False

        last = self.last_alarm
        # A negative difference means the clock jumped back: that is a new alarm, not a
        # repetition.
        if last is not None and ZERO <= received_at - last < DEDUP_WINDOW:
            self.deduplicated_total += 1
            _LOGGER.debug("Alarm counted as a repetition of the last alarm")
            return False

        self.last_alarm = received_at
        self.alarms_total += 1
        self.active = True
        self.active_until = dt_util.utcnow() + self._reset
        _LOGGER.debug("Alarm recognized, active for %s minutes", self.reset_minutes)

        # A new alarm restarts the time.
        self._async_cancel_reset()
        self._cancel_reset = async_call_later(
            self._hass, self._reset.total_seconds(), self._reset_job
        )

        async_dispatcher_send(self._hass, self._signal_alarm, AlarmEvent(received_at))
        async_dispatcher_send(self._hass, self._signal_state)
        return True

    @callback
    def _async_reset(self, _now: datetime) -> None:
        """Switch "alarm active" off when the reset time is over."""
        self._cancel_reset = None
        self.active = False
        self.active_until = None
        _LOGGER.debug("Alarm reset after the reset time")
        async_dispatcher_send(self._hass, self._signal_state)

    @callback
    def _async_cancel_reset(self) -> None:
        """Cancel the reset timer, if one is running."""
        if self._cancel_reset is not None:
            self._cancel_reset()
            self._cancel_reset = None

    @callback
    def async_shutdown(self) -> None:
        """Cancel the reset timer when the config entry is unloaded."""
        self._closed = True
        self._async_cancel_reset()
