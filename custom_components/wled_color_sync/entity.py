"""Base entity for WLED Media Color Sync."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, MANUFACTURER
from .engine import WledColorSyncEngine


class WledColorSyncEntity(Entity):
    """Common entity wiring: device info + engine update listener."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, engine: WledColorSyncEngine, key: str) -> None:
        self.engine = engine
        entry = engine.entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer=MANUFACTURER,
            model=f"UDP {engine.protocol.upper()} · {engine.num_leds} LEDs",
            configuration_url=f"http://{engine.host}",
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self.engine.add_listener(self.async_write_ha_state))
