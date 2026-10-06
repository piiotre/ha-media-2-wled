"""LED frame renderers for palette-driven effects.

Stateless (time-based) so frames can be produced at any FPS.
Free of Home Assistant imports so it can be tested standalone.
"""

from __future__ import annotations

import math

RGB = tuple[int, int, int]


def lerp(a: RGB, b: RGB, t: float) -> RGB:
    """Linear interpolation between two colors."""
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def blend_frames(a: list[RGB], b: list[RGB], t: float) -> list[RGB]:
    """Crossfade two frames (used for transitions between palettes)."""
    if len(a) != len(b):
        return b
    return [lerp(x, y, t) for x, y in zip(a, b)]


def _smooth(t: float) -> float:
    return t * t * (3 - 2 * t)


def _scale(c: RGB, f: float) -> RGB:
    return (int(c[0] * f), int(c[1] * f), int(c[2] * f))


def _palette_at(palette: list[RGB], pos: float, cyclic: bool) -> RGB:
    """Sample a palette at a fractional position."""
    n = len(palette)
    if n == 1:
        return palette[0]
    if cyclic:
        pos %= n
        i = int(pos)
        return lerp(palette[i], palette[(i + 1) % n], _smooth(pos - i))
    pos = max(0.0, min(n - 1, pos))
    i = min(int(pos), n - 2)
    return lerp(palette[i], palette[i + 1], pos - i)


def _hash(i: int, j: int) -> int:
    return ((i * 2654435761) ^ (j * 40503) ^ 0x9E3779B9) & 0xFFFFFFFF


def render(
    effect: str, palette: list[RGB], num_leds: int, t: float, speed: float = 1.0
) -> list[RGB]:
    """Render a frame.

    effect:  effect name (see const.EFFECTS)
    palette: extracted colors, most prominent first
    t:       seconds since start
    speed:   multiplier (1.0 = normal)
    """
    if num_leds <= 0:
        return []
    if not palette:
        palette = [(255, 255, 255)]
    n = len(palette)

    if effect == "solid":
        return [palette[0]] * num_leds

    if effect == "gradient":
        if num_leds == 1:
            return [palette[0]]
        return [
            _palette_at(palette, i / (num_leds - 1) * (n - 1), cyclic=False)
            for i in range(num_leds)
        ]

    if effect == "segments":
        return [palette[min(n - 1, i * n // num_leds)] for i in range(num_leds)]

    if effect == "ambient":
        # Whole strip slowly drifts through the palette with a gentle swell
        color = _palette_at(palette, t * speed * 0.15, cyclic=True)
        swell = 0.85 + 0.15 * math.sin(t * speed * 0.8)
        return [_scale(color, swell)] * num_leds

    if effect == "breathe":
        # Breathe on one color, switch to the next palette color at the bottom
        period = 4.0 / max(speed, 0.05)
        cycle = int(t / period)
        phase = (t % period) / period
        level = 0.08 + 0.92 * (0.5 - 0.5 * math.cos(phase * 2 * math.pi))
        return [_scale(palette[cycle % n], level)] * num_leds

    if effect == "chase":
        # Cyclic palette gradient scrolling along the strip
        span = max(1, num_leds / 2)  # palette repeats twice along the strip
        offset = t * speed * 1.5
        return [
            _palette_at(palette, (i / span) * n - offset, cyclic=True)
            for i in range(num_leds)
        ]

    if effect == "twinkle":
        # Each LED fades in/out independently with a palette color per cycle
        base = _scale(palette[0], 0.12)
        frame = []
        for i in range(num_leds):
            rate = 0.25 + (_hash(i, 7) % 1000) / 1000 * 0.5
            pos = t * speed * rate + (_hash(i, 3) % 1000) / 1000
            cycle = int(pos)
            phase = pos - cycle
            level = max(0.0, math.sin(phase * math.pi)) ** 2
            color = palette[_hash(i, cycle) % n]
            frame.append(lerp(base, color, level))
        return frame

    # Unknown effect - fall back to solid
    return [palette[0]] * num_leds
