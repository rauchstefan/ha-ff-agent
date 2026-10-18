"""Buttons "accept", "decline" and "reset alarm" of the FF Agent integration."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import SERVICE_ACCEPT, SERVICE_REJECT, SERVICE_RESET_ALARM
from .entity import FFAgentEntity
from .models import FFAgentConfigEntry, ReplyAction
from .reply import async_send_reply

# One reply at a time: a second press waits for the first one (and is then skipped by
# the repeat guard of the reply client).
PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FFAgentConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the buttons of a config entry."""
    async_add_entities(
        [
            ReplyButton(entry, SERVICE_ACCEPT, ReplyAction.ACCEPT),
            ReplyButton(entry, SERVICE_REJECT, ReplyAction.REJECT),
            ResetAlarmButton(entry, SERVICE_RESET_ALARM),
        ]
    )


class ReplyButton(FFAgentEntity, ButtonEntity):
    """Replies to the current mission with the options of the entry.

    An acceptance uses the default transport and the location of the chosen location
    source, if there is one. The state of a button is the time of the last press; it
    holds no information about the result, that is the job of the sensor "last reply".
    """

    def __init__(
        self, entry: FFAgentConfigEntry, key: str, action: ReplyAction
    ) -> None:
        """Initialize the button; the key is also its translation key."""
        super().__init__(entry, key)
        self._entry = entry
        self._action = action

    async def async_press(self) -> None:
        """Send the reply. An error is raised translated and shown by the frontend."""
        await async_send_reply(self.hass, self._entry, self._action)


class ResetAlarmButton(FFAgentEntity, ButtonEntity):
    """Switches "alarm active" off by hand.

    Nothing is sent to FF Agent. Without an active alarm a press does nothing.
    """

    async def async_press(self) -> None:
        """Switch "alarm active" off, if it is on."""
        self._manager.async_reset()
