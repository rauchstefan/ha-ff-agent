"""Base entity of the FF Agent integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import Entity

from .alarm import AlarmManager
from .const import DOMAIN, MANUFACTURER, MODEL
from .models import FFAgentConfigEntry


class FFAgentEntity(Entity):
    """An entity of one config entry (one person), belonging to the service device.

    The unique ID is built from the entry ID and the key. It never contains the reply
    ID, so it stays the same if the person renews that ID.
    """

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, entry: FFAgentConfigEntry, key: str) -> None:
        """Initialize the entity; the key is also its translation key."""
        self._entry_id = entry.entry_id
        self._manager: AlarmManager = entry.runtime_data.alarm
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer=MANUFACTURER,
            model=MODEL,
            entry_type=DeviceEntryType.SERVICE,
            # An explicit None clears the link of devices created by earlier versions;
            # leaving the field out would keep the stored value.
            configuration_url=None,
        )
