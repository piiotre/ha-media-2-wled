"""Switch to enable/disable color sync streaming."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .entity import WledColorSyncEntity


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities([SyncSwitch(entry.runtime_data, "sync")])


class SyncSwitch(WledColorSyncEntity, SwitchEntity, RestoreEntity):
    """Turns streaming to WLED on/off."""

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is not None and last.state == "off":
            await self.engine.async_set_enabled(False)

    @property
    def is_on(self) -> bool:
        return self.engine.enabled

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"streaming": self.engine.enabled and self.engine.source_active}

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.engine.async_set_enabled(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.engine.async_set_enabled(False)
