"""Async UDP realtime sender for WLED (DDP, DRGB/DNRGB, DRGBW, WARLS).

Free of Home Assistant imports so it can be tested standalone.
"""

from __future__ import annotations

import asyncio
import logging
import struct

_LOGGER = logging.getLogger(__name__)

RGB = tuple[int, int, int]

DDP_MAX_PIXELS = 480  # 1440 data bytes per packet
DRGB_MAX_PIXELS = 490
DNRGB_MAX_PIXELS = 489
DRGBW_MAX_PIXELS = 367
WARLS_MAX_PIXELS = 255


def build_packets(
    protocol: str, frame: list[RGB], brightness: int = 255, timeout: int = 2
) -> list[bytes]:
    """Build the UDP payload(s) for one frame."""
    scale = max(0, min(255, brightness)) / 255
    if scale < 1:
        frame = [(int(r * scale), int(g * scale), int(b * scale)) for r, g, b in frame]

    if protocol == "ddp":
        return _build_ddp(frame)
    if protocol == "drgb":
        return _build_drgb(frame, timeout)
    if protocol == "drgbw":
        return _build_drgbw(frame, timeout)
    if protocol == "warls":
        return _build_warls(frame, timeout)
    raise ValueError(f"Unknown protocol: {protocol}")


_ddp_seq = 0


def _build_ddp(frame: list[RGB]) -> list[bytes]:
    """DDP: 10 byte header, max 1440 data bytes, PUSH flag on last packet."""
    global _ddp_seq  # noqa: PLW0603
    _ddp_seq = _ddp_seq % 15 + 1
    data = bytes(c for px in frame for c in px)
    chunk_size = DDP_MAX_PIXELS * 3
    packets = []
    for offset in range(0, max(len(data), 1), chunk_size):
        chunk = data[offset : offset + chunk_size]
        last = offset + chunk_size >= len(data)
        flags = 0x40 | (0x01 if last else 0x00)  # version 1 (+ push)
        # flags, sequence, data type (RGB 8-bit), destination id (display), offset, length
        header = struct.pack("!BBBBIH", flags, _ddp_seq, 0x0B, 0x01, offset, len(chunk))
        packets.append(header + chunk)
    return packets


def _build_drgb(frame: list[RGB], timeout: int) -> list[bytes]:
    """DRGB for small strips, DNRGB (with start index) for larger ones."""
    if len(frame) <= DRGB_MAX_PIXELS:
        return [bytes([2, timeout]) + bytes(c for px in frame for c in px)]
    packets = []
    for start in range(0, len(frame), DNRGB_MAX_PIXELS):
        chunk = frame[start : start + DNRGB_MAX_PIXELS]
        header = bytes([4, timeout, (start >> 8) & 0xFF, start & 0xFF])
        packets.append(header + bytes(c for px in chunk for c in px))
    return packets


def _build_drgbw(frame: list[RGB], timeout: int) -> list[bytes]:
    """DRGBW: extracts the common white component into the W channel."""
    if len(frame) > DRGBW_MAX_PIXELS:
        _LOGGER.debug("DRGBW supports %s LEDs max, truncating", DRGBW_MAX_PIXELS)
        frame = frame[:DRGBW_MAX_PIXELS]
    out = bytearray([3, timeout])
    for r, g, b in frame:
        w = min(r, g, b)
        out += bytes((r - w, g - w, b - w, w))
    return [bytes(out)]


def _build_warls(frame: list[RGB], timeout: int) -> list[bytes]:
    """WARLS: index + RGB per LED, max 255 LEDs."""
    if len(frame) > WARLS_MAX_PIXELS:
        _LOGGER.debug("WARLS supports %s LEDs max, truncating", WARLS_MAX_PIXELS)
        frame = frame[:WARLS_MAX_PIXELS]
    out = bytearray([1, timeout])
    for i, (r, g, b) in enumerate(frame):
        out += bytes((i, r, g, b))
    return [bytes(out)]


class _Protocol(asyncio.DatagramProtocol):
    def error_received(self, exc: Exception) -> None:
        _LOGGER.debug("UDP error: %s", exc)


class UdpSender:
    """Non-blocking UDP sender bound to a single WLED device."""

    def __init__(self, host: str, port: int, protocol: str, timeout: int = 2) -> None:
        self.host = host
        self.port = port
        self.protocol = protocol
        self.timeout = timeout
        self._transport: asyncio.DatagramTransport | None = None

    async def async_connect(self) -> None:
        """Create the UDP endpoint (resolves the hostname)."""
        if self._transport is not None:
            return
        loop = asyncio.get_running_loop()
        try:
            self._transport, _ = await loop.create_datagram_endpoint(
                _Protocol, remote_addr=(self.host, self.port)
            )
        except OSError as err:
            _LOGGER.warning("Cannot open UDP socket to %s:%s: %s", self.host, self.port, err)
            self._transport = None

    def send(self, frame: list[RGB], brightness: int = 255) -> None:
        """Send a frame (fire and forget)."""
        if self._transport is None or self._transport.is_closing():
            return
        for packet in build_packets(self.protocol, frame, brightness, self.timeout):
            self._transport.sendto(packet)

    @property
    def connected(self) -> bool:
        return self._transport is not None and not self._transport.is_closing()

    def close(self) -> None:
        if self._transport is not None:
            self._transport.close()
            self._transport = None
