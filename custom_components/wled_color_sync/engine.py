"""Sync engine: watches a media source, extracts colors and streams effects to WLED."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import logging
from typing import Any

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.core import valid_entity_id
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.network import NoURLAvailableError, get_url

from . import effects
from .color_extractor import FALLBACK_PALETTE, extract_palette
from .const import (
    ACTIVE_MEDIA_STATES,
    CONF_BRIGHTNESS_BOOST,
    CONF_FPS,
    CONF_GAP_SIZE,
    CONF_HOST,
    CONF_NUM_LEDS,
    CONF_PALETTE_SIZE,
    CONF_PORT,
    CONF_PROTOCOL,
    CONF_SATURATION_BOOST,
    CONF_SOURCE_ENTITY,
    CONF_STOP_WHEN_IDLE,
    CONF_TRANSITION,
    DEFAULT_BRIGHTNESS,
    DEFAULT_BRIGHTNESS_BOOST,
    DEFAULT_EFFECT,
    DEFAULT_FPS,
    DEFAULT_GAP_SIZE,
    DEFAULT_PALETTE_SIZE,
    DEFAULT_PORTS,
    DEFAULT_PROTOCOL,
    DEFAULT_SATURATION_BOOST,
    DEFAULT_SPEED,
    DEFAULT_STOP_WHEN_IDLE,
    DEFAULT_TRANSITION,
    REALTIME_TIMEOUT,
    STATIC_EFFECTS,
)
from .udp_sender import UdpSender

_LOGGER = logging.getLogger(__name__)

RGB = tuple[int, int, int]
STATIC_KEEPALIVE = 0.5  # seconds between packets for non-animated effects


async def async_fetch_image(hass: HomeAssistant, source: str) -> bytes | None:
    """Fetch image bytes from an entity, HA-relative URL, absolute URL or local file."""
    if not source:
        return None

    # Entity id -> its picture
    if valid_entity_id(source):
        state = hass.states.get(source)
        if state is None:
            _LOGGER.warning("Source entity %s not found", source)
            return None
        source = state.attributes.get("entity_picture_local") or state.attributes.get(
            "entity_picture"
        )
        if not source:
            _LOGGER.debug("Entity has no picture right now")
            return None

    # HA relative URL (/api/media_player_proxy/..., /api/image_proxy/..., /local/...)
    if source.startswith(("/api/", "/local/")):
        try:
            base = get_url(hass, allow_external=False)
        except NoURLAvailableError:
            base = f"http://127.0.0.1:{hass.http.server_port}"
        source = base.rstrip("/") + source

    if source.startswith(("http://", "https://")):
        session = async_get_clientsession(hass)
        try:
            async with session.get(source, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    _LOGGER.warning("Fetching image failed (HTTP %s): %s", resp.status, source)
                    return None
                return await resp.read()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.warning("Error fetching image %s: %s", source, err)
            return None

    # Local file - must be in allowlist_external_dirs
    path = source.removeprefix("file://")
    if not hass.config.is_allowed_path(path):
        _LOGGER.error(
            "Path %s is not allowed; add its folder to allowlist_external_dirs", path
        )
        return None

    def _read() -> bytes:
        with open(path, "rb") as file:
            return file.read()

    try:
        return await hass.async_add_executor_job(_read)
    except OSError as err:
        _LOGGER.error("Cannot read %s: %s", path, err)
        return None


class WledColorSyncEngine:
    """Per-device runtime."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, num_leds: int) -> None:
        self.hass = hass
        self.entry = entry
        cfg = {**entry.data, **entry.options}

        self.host: str = cfg[CONF_HOST]
        self.protocol: str = cfg.get(CONF_PROTOCOL, DEFAULT_PROTOCOL)
        self.port: int = cfg.get(CONF_PORT) or DEFAULT_PORTS[self.protocol]
        self.num_leds = num_leds
        self.source_entity: str | None = cfg.get(CONF_SOURCE_ENTITY) or None
        self.palette_size: int = int(cfg.get(CONF_PALETTE_SIZE, DEFAULT_PALETTE_SIZE))
        self.gap_size: int = int(cfg.get(CONF_GAP_SIZE, DEFAULT_GAP_SIZE))
        self.saturation_boost: float = cfg.get(CONF_SATURATION_BOOST, DEFAULT_SATURATION_BOOST)
        self.brightness_boost: float = cfg.get(CONF_BRIGHTNESS_BOOST, DEFAULT_BRIGHTNESS_BOOST)
        self.fps: int = int(cfg.get(CONF_FPS, DEFAULT_FPS))
        self.transition: float = float(cfg.get(CONF_TRANSITION, DEFAULT_TRANSITION))
        self.stop_when_idle: bool = cfg.get(CONF_STOP_WHEN_IDLE, DEFAULT_STOP_WHEN_IDLE)

        # Runtime state (controlled by entities)
        self.enabled = True
        self.effect = DEFAULT_EFFECT
        self.brightness = DEFAULT_BRIGHTNESS
        self.speed = DEFAULT_SPEED

        self.palette: list[RGB] = list(FALLBACK_PALETTE)
        self.current_source: str | None = None
        self.source_active = True

        self._sender = UdpSender(self.host, self.port, self.protocol, REALTIME_TIMEOUT)
        self._task: asyncio.Task | None = None
        self._unsub_state: Callable[[], None] | None = None
        self._listeners: list[Callable[[], None]] = []
        self._last_frame: list[RGB] | None = None
        self._transition_from: list[RGB] | None = None
        self._transition_start = 0.0
        self._dirty = True
        self._last_picture: str | None = None
        self._process_lock = asyncio.Lock()

    # ----------------------------------------------------------------- lifecycle
    async def async_start(self) -> None:
        await self._sender.async_connect()
        if self.source_entity:
            self._unsub_state = async_track_state_change_event(
                self.hass, [self.source_entity], self._handle_source_event
            )
            state = self.hass.states.get(self.source_entity)
            self._update_source_active(state.state if state else None)
            self.hass.async_create_task(self.async_process_source(self.source_entity))
        self._ensure_loop()

    async def async_stop(self) -> None:
        if self._unsub_state:
            self._unsub_state()
            self._unsub_state = None
        await self._cancel_loop()
        self._sender.close()

    # ----------------------------------------------------------------- listeners
    @callback
    def add_listener(self, update_callback: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(update_callback)

        @callback
        def remove() -> None:
            self._listeners.remove(update_callback)

        return remove

    @callback
    def _notify(self) -> None:
        for listener in list(self._listeners):
            listener()

    # ----------------------------------------------------------------- controls
    async def async_set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        if enabled:
            self._dirty = True
            self._ensure_loop()
        else:
            await self._cancel_loop()
        self._notify()

    @callback
    def set_effect(self, effect: str) -> None:
        self._start_transition()
        self.effect = effect
        self._notify()

    @callback
    def set_brightness(self, brightness: int) -> None:
        self.brightness = int(brightness)
        self._dirty = True
        self._notify()

    @callback
    def set_speed(self, speed: int) -> None:
        self.speed = int(speed)
        self._notify()

    @callback
    def set_palette_size(self, palette_size: int) -> None:
        self.palette_size = max(1, min(12, int(palette_size)))
        if self.source_entity:
            self.hass.async_create_task(self.async_process_source(self.source_entity))
        self._notify()

    @callback
    def set_gap_size(self, gap_size: int) -> None:
        self.gap_size = max(0, min(20, int(gap_size)))
        self._dirty = True
        self._notify()

    # ----------------------------------------------------------------- source handling
    @callback
    def _handle_source_event(self, event: Event[EventStateChangedData]) -> None:
        new_state = event.data["new_state"]
        if new_state is None:
            return
        self._update_source_active(new_state.state)
        picture = new_state.attributes.get("entity_picture_local") or new_state.attributes.get(
            "entity_picture"
        )
        if picture != self._last_picture:
            self.hass.async_create_task(self.async_process_source(self.source_entity))
        self._notify()

    @callback
    def _update_source_active(self, state: str | None) -> None:
        if not self.stop_when_idle or not self.source_entity:
            self.source_active = True
            return
        if self.source_entity.startswith("media_player."):
            was_active = self.source_active
            self.source_active = state in ACTIVE_MEDIA_STATES
            if self.source_active and not was_active:
                self._dirty = True
        else:
            self.source_active = state not in (None, "unavailable", "unknown")

    async def async_process_source(self, source: str | None) -> list[RGB]:
        """Fetch an image, extract its palette and transition to it."""
        if not source:
            return self.palette
        async with self._process_lock:
            if valid_entity_id(source):
                state = self.hass.states.get(source)
                if state:
                    self._last_picture = state.attributes.get(
                        "entity_picture_local"
                    ) or state.attributes.get("entity_picture")
            image = await async_fetch_image(self.hass, source)
            if image is None:
                return self.palette
            palette = await self.hass.async_add_executor_job(
                extract_palette,
                image,
                self.palette_size,
                self.saturation_boost,
                self.brightness_boost,
            )
            self.apply_palette(palette, source)
            return palette

    @callback
    def apply_palette(self, palette: list[RGB], source: str | None = None) -> None:
        if palette == self.palette:
            return
        _LOGGER.debug("New palette for %s: %s", self.host, palette)
        self._start_transition()
        self.palette = palette
        self.current_source = source
        self._notify()

    @callback
    def _start_transition(self) -> None:
        if self._last_frame is not None and self.transition > 0:
            self._transition_from = self._last_frame
            self._transition_start = self.hass.loop.time()
        self._dirty = True

    # ----------------------------------------------------------------- render loop
    def _ensure_loop(self) -> None:
        if self.enabled and (self._task is None or self._task.done()):
            self._task = self.entry.async_create_background_task(
                self.hass, self._run_loop(), f"wled_color_sync {self.host}"
            )

    async def _cancel_loop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _run_loop(self) -> None:
        loop = self.hass.loop
        start = loop.time()
        last_send = 0.0
        interval = 1 / max(1, self.fps)
        while True:
            now = loop.time()
            try:
                if self.source_active and self.num_leds > 0:
                    frame = effects.render(
                        self.effect,
                        self.palette,
                        self.num_leds,
                        now - start,
                        self.speed / 50,
                        self.gap_size,
                    )
                    transitioning = False
                    if self._transition_from is not None:
                        progress = (now - self._transition_start) / self.transition
                        if progress >= 1:
                            self._transition_from = None
                        else:
                            transitioning = True
                            frame = effects.blend_frames(self._transition_from, frame, progress)
                    self._last_frame = frame

                    animated = self.effect not in STATIC_EFFECTS or transitioning
                    if animated or self._dirty or now - last_send >= STATIC_KEEPALIVE:
                        if not self._sender.connected:
                            await self._sender.async_connect()
                        self._sender.send(frame, self.brightness)
                        last_send = now
                        self._dirty = False
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Error in WLED color sync loop")
                await asyncio.sleep(1)
            await asyncio.sleep(max(0.001, interval - (loop.time() - now)))

    # ----------------------------------------------------------------- info
    @property
    def device_info_extra(self) -> dict[str, Any]:
        return {
            "host": self.host,
            "port": self.port,
            "protocol": self.protocol,
            "num_leds": self.num_leds,
            "palette_size": self.palette_size,
            "gap_size": self.gap_size,
        }
