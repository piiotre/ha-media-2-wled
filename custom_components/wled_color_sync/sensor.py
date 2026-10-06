"""Sensor exposing the extracted palette."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .color_extractor import rgb_to_hex
from .entity import WledColorSyncEntity


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities([PaletteSensor(entry.runtime_data, "dominant_color")])


class PaletteSensor(WledColorSyncEntity, SensorEntity):
    """State = dominant color hex; attributes = full palette."""

    _attr_icon = "mdi:palette"

    @property
    def native_value(self) -> str:
        return rgb_to_hex(self.engine.palette[0])

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        palette = self.engine.palette
        return {
            "palette": [rgb_to_hex(c) for c in palette],
            "rgb_palette": [list(c) for c in palette],
            "source": self.engine.current_source,
            "source_active": self.engine.source_active,
            "effect": self.engine.effect,
            **self.engine.device_info_extra,
        }
