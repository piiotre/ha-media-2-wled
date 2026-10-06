"""Color extraction engine for media images.

This module is intentionally free of Home Assistant imports so it can be
unit-tested standalone.
"""

from __future__ import annotations

import colorsys
import io
import logging

from PIL import Image, ImageDraw

_LOGGER = logging.getLogger(__name__)

RGB = tuple[int, int, int]
FALLBACK_PALETTE: list[RGB] = [(255, 255, 255)]


def extract_palette(
    image_bytes: bytes,
    palette_size: int = 5,
    saturation_boost: float = 1.3,
    brightness_boost: float = 1.0,
) -> list[RGB]:
    """Extract the most prominent, LED-friendly colors from an image.

    Blocking (CPU bound) - run in an executor from async code.
    Returns a list of RGB tuples ordered by prominence.
    """
    if not image_bytes:
        return list(FALLBACK_PALETTE)

    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            img = img.convert("RGB")
            img.thumbnail((128, 128), Image.Resampling.LANCZOS)
            # Over-quantize, then score & de-duplicate down to palette_size
            quantized = img.quantize(
                colors=max(8, palette_size * 3), method=Image.Quantize.MEDIANCUT
            )
            palette = quantized.getpalette() or []
            color_counts = quantized.getcolors() or []
    except Exception as err:  # noqa: BLE001
        _LOGGER.error("Failed to decode image for color extraction: %s", err)
        return list(FALLBACK_PALETTE)

    if not color_counts or not palette:
        return list(FALLBACK_PALETTE)

    candidates: list[tuple[float, RGB]] = []
    for count, index in color_counts:
        r, g, b = palette[index * 3 : index * 3 + 3]
        _, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        # Favour colorful, reasonably bright colors over large dark/grey areas
        # (e.g. black album-art backgrounds), while still respecting area.
        score = count * (0.2 + s) * (0.15 + v)
        if v < 0.08:
            score *= 0.05  # near-black is useless on LEDs
        candidates.append((score, (r, g, b)))

    candidates.sort(key=lambda item: item[0], reverse=True)

    selected: list[RGB] = []
    for _, color in candidates:
        if all(_distance(color, other) > 45 for other in selected):
            selected.append(color)
        if len(selected) >= palette_size:
            break

    if not selected:
        return list(FALLBACK_PALETTE)

    return [enhance_color(c, saturation_boost, brightness_boost) for c in selected]


def generate_palette_image(
    palette: list[RGB],
    swatch_width: int = 32,
    height: int = 32,
) -> bytes:
    """Generate a PNG image showing the detected palette colors left to right.

    Height: 32px
    Width: 32px * palette_size
    """
    if not palette:
        palette = list(FALLBACK_PALETTE)
    width = max(1, len(palette) * swatch_width)
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)
    for idx, color in enumerate(palette):
        x1 = idx * swatch_width
        x2 = (idx + 1) * swatch_width
        draw.rectangle([x1, 0, x2, height], fill=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def enhance_color(
    color: RGB, saturation_boost: float = 1.3, brightness_boost: float = 1.0
) -> RGB:
    """Boost saturation / brightness of a color for richer LED output."""
    r, g, b = color
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    s = min(1.0, s * saturation_boost)
    # LEDs look washed out / invisible at low values: normalise toward full value
    v = min(1.0, max(0.35, v * brightness_boost))
    nr, ng, nb = colorsys.hsv_to_rgb(h, s, v)
    return (round(nr * 255), round(ng * 255), round(nb * 255))


def rgb_to_hex(color: RGB) -> str:
    """Convert an RGB tuple to a #rrggbb string."""
    return "#{:02x}{:02x}{:02x}".format(*color)


def _distance(a: RGB, b: RGB) -> float:
    """Weighted (redmean) RGB distance - cheap approximation of perceived difference."""
    rmean = (a[0] + b[0]) / 2
    dr, dg, db = a[0] - b[0], a[1] - b[1], a[2] - b[2]
    return (
        (2 + rmean / 256) * dr * dr + 4 * dg * dg + (2 + (255 - rmean) / 256) * db * db
    ) ** 0.5
