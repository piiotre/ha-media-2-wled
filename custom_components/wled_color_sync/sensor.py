"""Sensors exposing the extracted palette and individual numbered palette colors (1-12)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .color_extractor import rgb_to_hex
from .engine import WledColorSyncEngine
from .entity import WledColorSyncEntity


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback) -> None:
    engine: WledColorSyncEngine = entry.runtime_data
    entities: list[SensorEntity] = [PaletteSensor(engine, "dominant_color")]
    for i in range(1, 13):
        entities.append(PaletteColorSensor(engine, f"color_{i}", index=i - 1))
    async_add_entities(entities)


class PaletteSensor(WledColorSyncEntity, SensorEntity):
    """Main dominant color sensor; attributes contain the full palette."""

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
            "palette_size": len(palette),
            **self.engine.device_info_extra,
        }


class PaletteColorSensor(WledColorSyncEntity, SensorEntity):
    """Sensor for an individual color (1-12) in the extracted palette."""

    _attr_icon = "mdi:palette-swatch-outline"

    def __init__(self, engine: WledColorSyncEngine, key: str, index: int) -> None:
        super().__init__(engine, key)
        self.index = index

    @property
    def native_value(self) -> str | None:
        palette = self.engine.palette
        if self.index < len(palette):
            return rgb_to_hex(palette[self.index])
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        palette = self.engine.palette
        if self.index < len(palette):
            rgb = palette[self.index]
            return {
                "rgb_color": list(rgb),
                "r": rgb[0],
                "g": rgb[1],
                "b": rgb[2],
                "color_index": self.index + 1,
            }
        return {"color_index": self.index + 1}
