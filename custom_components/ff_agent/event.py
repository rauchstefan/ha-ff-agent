"""Event entity "alarm" of the FF Agent integration."""

from __future__ import annotations

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import EVENT_TYPE_ALARM, SIGNAL_ALARM
from .entity import FFAgentEntity
from .models import AlarmEvent, FFAgentConfigEntry

# The event is triggered by a dispatcher signal, so nothing is ever updated in parallel.
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FFAgentConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the event entity of a config entry."""
    async_add_entities([AlarmEventEntity(entry)])


class AlarmEventEntity(FFAgentEntity, EventEntity):
    """Triggers once for every new alarm, after the deduplication.

    This is the primary trigger for automations. The event has no attributes: mission
    data would be stored in core.restore_state, and there is none anyway.
    """

    _attr_event_types = [EVENT_TYPE_ALARM]

    def __init__(self, entry: FFAgentConfigEntry) -> None:
        """Initialize the event entity."""
        super().__init__(entry, "alarm")

    async def async_added_to_hass(self) -> None:
        """Follow the alarm signal of the alarm manager."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_ALARM.format(entry_id=self._entry_id),
                self._handle_alarm,
            )
        )

    @callback
    def _handle_alarm(self, _alarm: AlarmEvent) -> None:
        """Trigger the event. The state is not written by the trigger itself."""
        self._trigger_event(EVENT_TYPE_ALARM)
        self.async_write_ha_state()
