"""Image entity exposing the detected palette as a PNG picture."""

from __future__ import annotations

from typing import Any

from homeassistant.components.image import ImageEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .color_extractor import generate_palette_image
from .engine import WledColorSyncEngine
from .entity import WledColorSyncEntity


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback) -> None:
    engine: WledColorSyncEngine = entry.runtime_data
    async_add_entities([PaletteImageEntity(engine, "palette_image", hass)])


class PaletteImageEntity(WledColorSyncEntity, ImageEntity):
    """Image entity providing a 32x(32*palette_size) PNG palette picture."""

    _attr_icon = "mdi:image-palette"

    def __init__(self, engine: WledColorSyncEngine, key: str, hass: HomeAssistant) -> None:
        WledColorSyncEntity.__init__(self, engine, key)
        ImageEntity.__init__(self, hass)
        self._last_palette: list[tuple[int, int, int]] | None = None
        self._cached_image: bytes | None = None

    async def async_image(self) -> bytes | None:
        """Return the bytes of the palette PNG picture."""
        palette = self.engine.palette
        if self._cached_image is None or palette != self._last_palette:
            self._cached_image = await self.hass.async_add_executor_job(
                generate_palette_image, palette, 32, 32
            )
            self._last_palette = list(palette)
        return self._cached_image

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._attr_image_last_updated = dt_util.utcnow()
        self.async_on_remove(self.engine.add_listener(self._handle_engine_update))

    @callback
    def _handle_engine_update(self) -> None:
        """Update last_updated timestamp whenever the palette changes."""
        if self.engine.palette != self._last_palette:
            self._attr_image_last_updated = dt_util.utcnow()
            self._cached_image = None
            self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        palette = self.engine.palette
        return {
            "palette_size": len(palette),
            "width_px": len(palette) * 32,
            "height_px": 32,
            "source": self.engine.current_source,
        }
