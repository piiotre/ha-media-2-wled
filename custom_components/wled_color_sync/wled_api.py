"""Minimal WLED JSON API helpers (used for LED count auto-detection)."""

from __future__ import annotations

import asyncio
import logging

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)


async def async_get_info(hass: HomeAssistant, host: str) -> dict | None:
    """Return WLED /json/info or None if unreachable."""
    session = async_get_clientsession(hass)
    try:
        async with session.get(
            f"http://{host}/json/info", timeout=aiohttp.ClientTimeout(total=5)
        ) as resp:
            if resp.status != 200:
                return None
            return await resp.json(content_type=None)
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as err:
        _LOGGER.debug("WLED info request to %s failed: %s", host, err)
        return None


async def async_get_led_count(hass: HomeAssistant, host: str) -> int | None:
    """Return the configured LED count of a WLED device."""
    info = await async_get_info(hass, host)
    try:
        return int(info["leds"]["count"]) if info else None
    except (KeyError, TypeError, ValueError):
        return None
