"""Brightness, speed, palette size, and gap size number entities."""

from __future__ import annotations

from homeassistant.components.number import NumberMode, RestoreNumber
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import WledColorSyncEntity


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback) -> None:
    engine = entry.runtime_data
    async_add_entities(
        [
            BrightnessNumber(engine, "brightness"),
            SpeedNumber(engine, "speed"),
            PaletteSizeNumber(engine, "palette_size"),
            GapSizeNumber(engine, "gap_size"),
        ]
    )


class _EngineNumber(WledColorSyncEntity, RestoreNumber):
    _attr_mode = NumberMode.SLIDER
    _attr_native_step = 1

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_number_data()) is not None and last.native_value is not None:
            self._apply(last.native_value)

    def _apply(self, value: float) -> None:
        raise NotImplementedError

    async def async_set_native_value(self, value: float) -> None:
        self._apply(value)


class BrightnessNumber(_EngineNumber):
    _attr_native_min_value = 0
    _attr_native_max_value = 255
    _attr_icon = "mdi:brightness-6"

    @property
    def native_value(self) -> float:
        return self.engine.brightness

    def _apply(self, value: float) -> None:
        self.engine.set_brightness(int(value))


class SpeedNumber(_EngineNumber):
    _attr_native_min_value = 1
    _attr_native_max_value = 100
    _attr_icon = "mdi:speedometer"

    @property
    def native_value(self) -> float:
        return self.engine.speed

    def _apply(self, value: float) -> None:
        self.engine.set_speed(int(value))


class PaletteSizeNumber(_EngineNumber):
    _attr_native_min_value = 1
    _attr_native_max_value = 12
    _attr_icon = "mdi:palette-swatch"

    @property
    def native_value(self) -> float:
        return self.engine.palette_size

    def _apply(self, value: float) -> None:
        self.engine.set_palette_size(int(value))


class GapSizeNumber(_EngineNumber):
    _attr_native_min_value = 0
    _attr_native_max_value = 20
    _attr_icon = "mdi:arrow-expand-horizontal"

    @property
    def native_value(self) -> float:
        return self.engine.gap_size

    def _apply(self, value: float) -> None:
        self.engine.set_gap_size(int(value))
