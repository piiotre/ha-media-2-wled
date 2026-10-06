"""Effect selector."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import EFFECTS
from .entity import WledColorSyncEntity


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities([EffectSelect(entry.runtime_data, "effect")])


class EffectSelect(WledColorSyncEntity, SelectEntity, RestoreEntity):
    """Selects the effect used to render the extracted palette."""

    _attr_options = EFFECTS

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is not None and last.state in EFFECTS:
            self.engine.effect = last.state

    @property
    def current_option(self) -> str:
        return self.engine.effect

    async def async_select_option(self, option: str) -> None:
        self.engine.set_effect(option)
