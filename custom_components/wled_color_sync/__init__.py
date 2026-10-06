"""WLED Media Color Sync - extract colors from media images and stream them to WLED over UDP."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import ConfigEntryNotReady, ServiceValidationError
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .color_extractor import extract_palette, rgb_to_hex
from .const import (
    ATTR_CONFIG_ENTRY_ID,
    ATTR_PALETTE_SIZE,
    ATTR_SOURCE,
    CONF_HOST,
    CONF_NUM_LEDS,
    DEFAULT_PALETTE_SIZE,
    DOMAIN,
    PLATFORMS,
    SERVICE_EXTRACT_COLORS,
    SERVICE_SYNC_IMAGE,
)
from .engine import WledColorSyncEngine, async_fetch_image
from .wled_api import async_get_led_count

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

WledColorSyncConfigEntry = ConfigEntry[WledColorSyncEngine]

SYNC_IMAGE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required(ATTR_SOURCE): cv.string,
    }
)
EXTRACT_COLORS_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_SOURCE): cv.string,
        vol.Optional(ATTR_PALETTE_SIZE, default=DEFAULT_PALETTE_SIZE): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=12)
        ),
    }
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register services."""

    async def _sync_image(call: ServiceCall) -> ServiceResponse:
        entry = hass.config_entries.async_get_entry(call.data[ATTR_CONFIG_ENTRY_ID])
        if entry is None or entry.domain != DOMAIN or entry.state is not ConfigEntryState.LOADED:
            raise ServiceValidationError("Unknown or not loaded WLED Color Sync entry")
        engine: WledColorSyncEngine = entry.runtime_data
        palette = await engine.async_process_source(call.data[ATTR_SOURCE])
        return {
            "colors": [rgb_to_hex(c) for c in palette],
            "rgb": [list(c) for c in palette],
        }

    async def _extract_colors(call: ServiceCall) -> ServiceResponse:
        image = await async_fetch_image(hass, call.data[ATTR_SOURCE])
        if image is None:
            raise ServiceValidationError(f"Could not load image from {call.data[ATTR_SOURCE]}")
        palette = await hass.async_add_executor_job(
            extract_palette, image, call.data[ATTR_PALETTE_SIZE]
        )
        return {
            "colors": [rgb_to_hex(c) for c in palette],
            "rgb": [list(c) for c in palette],
        }

    hass.services.async_register(
        DOMAIN,
        SERVICE_SYNC_IMAGE,
        _sync_image,
        schema=SYNC_IMAGE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_EXTRACT_COLORS,
        _extract_colors,
        schema=EXTRACT_COLORS_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: WledColorSyncConfigEntry) -> bool:
    """Set up a WLED device from a config entry."""
    cfg = {**entry.data, **entry.options}
    num_leds = int(cfg.get(CONF_NUM_LEDS) or 0)
    if num_leds <= 0:
        num_leds = await async_get_led_count(hass, cfg[CONF_HOST]) or 0
        if num_leds <= 0:
            raise ConfigEntryNotReady(
                f"Could not auto-detect LED count from {cfg[CONF_HOST]}; "
                "is WLED online? (or set the LED count manually in options)"
            )

    engine = WledColorSyncEngine(hass, entry, num_leds)
    entry.runtime_data = engine
    await engine.async_start()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: WledColorSyncConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.async_stop()
    return unloaded


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
