"""Binary sensor "alarm active" of the FF Agent integration."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import SIGNAL_ALARM_STATE
from .entity import FFAgentEntity
from .models import FFAgentConfigEntry

# The state only changes through a dispatcher signal, so nothing is ever updated in
# parallel.
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FFAgentConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the binary sensor of a config entry."""
    async_add_entities([AlarmBinarySensor(entry)])


class AlarmBinarySensor(FFAgentEntity, BinarySensorEntity):
    """On from an alarm until the reset time is over. Has no attributes."""

    def __init__(self, entry: FFAgentConfigEntry) -> None:
        """Initialize the binary sensor."""
        super().__init__(entry, "alarm")

    @property
    def is_on(self) -> bool:
        """Return True while an alarm is active."""
        return self._manager.active

    async def async_added_to_hass(self) -> None:
        """Follow the state signal of the alarm manager."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_ALARM_STATE.format(entry_id=self._entry_id),
                self.async_write_ha_state,
            )
        )
