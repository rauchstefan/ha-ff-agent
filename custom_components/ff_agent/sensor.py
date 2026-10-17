"""Sensors "last alarm" and "last reply" of the FF Agent integration."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    REPLY_OPTIONS,
    REPLY_STATE_ACCEPTED,
    REPLY_STATE_FAILED,
    REPLY_STATE_REJECTED,
    SIGNAL_ALARM,
    SIGNAL_REPLY,
)
from .entity import FFAgentEntity
from .models import AlarmEvent, FFAgentConfigEntry, ReplyAction, ReplyResult

# The value only changes through a dispatcher signal, so nothing is ever updated in
# parallel.
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FFAgentConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensors of a config entry."""
    async_add_entities([LastAlarmSensor(entry), LastReplySensor(entry)])


class LastAlarmSensor(FFAgentEntity, RestoreSensor):
    """The time of the last alarm. Has no attributes.

    The value survives a restart of Home Assistant. It is shown only; the alarm
    manager does not take it over, so the deduplication window stays volatile.
    """

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, entry: FFAgentConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(entry, "last_alarm")

    async def async_added_to_hass(self) -> None:
        """Restore the last alarm and follow the alarm signal of the manager."""
        await super().async_added_to_hass()

        if self._manager.last_alarm is not None:
            # An alarm arrived before this entity was added: that one is newer.
            self._attr_native_value = self._manager.last_alarm
        elif (restored := await self._async_restored_alarm()) is not None:
            self._attr_native_value = restored

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_ALARM.format(entry_id=self._entry_id),
                self._handle_alarm,
            )
        )

    async def _async_restored_alarm(self) -> datetime | None:
        """Return the restored time of the last alarm, if there is a valid one.

        A time without a time zone is ignored: it cannot be a timestamp.
        """
        data = await self.async_get_last_sensor_data()
        if (
            data is not None
            and isinstance(data.native_value, datetime)
            and data.native_value.tzinfo is not None
        ):
            return data.native_value
        return None

    @callback
    def _handle_alarm(self, alarm: AlarmEvent) -> None:
        """Show the time of the new alarm."""
        self._attr_native_value = alarm.received_at
        self.async_write_ha_state()


class LastReplySensor(FFAgentEntity, SensorEntity):
    """The result of the last reply: accepted, rejected or failed.

    "accepted" and "rejected" mean that FF Agent answered with an HTTP status 2xx, not
    that it recorded the reply (assumption A7). A reply that was skipped by the repeat
    guard does not change the value. The sensor has no attributes and is not restored:
    after a restart nothing is known about the last reply.
    """

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = list(REPLY_OPTIONS)

    def __init__(self, entry: FFAgentConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(entry, "last_reply")

    async def async_added_to_hass(self) -> None:
        """Follow the reply signal of the reply client."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_REPLY.format(entry_id=self._entry_id),
                self._handle_reply,
            )
        )

    @callback
    def _handle_reply(self, result: ReplyResult) -> None:
        """Show the result of a reply."""
        if not result.success:
            self._attr_native_value = REPLY_STATE_FAILED
        elif result.action is ReplyAction.ACCEPT:
            self._attr_native_value = REPLY_STATE_ACCEPTED
        else:
            self._attr_native_value = REPLY_STATE_REJECTED
        self.async_write_ha_state()
