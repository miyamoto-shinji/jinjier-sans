from __future__ import annotations

import math
from dataclasses import dataclass

from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates

from .config import BRAND_PRIMARY_CHARS


@dataclass(frozen=True)
class BrandResult:
    primary_characters: int
    transformed_glyphs: int


def _decompose(font: TTFont, glyph_name: str) -> None:
    glyph = font["glyf"][glyph_name]
    if not glyph.isComposite():
        return
    recording = DecomposingRecordingPen(font.getGlyphSet())
    font.getGlyphSet()[glyph_name].draw(recording)
    pen = TTGlyphPen(None)
    recording.replay(pen)
    font["glyf"][glyph_name] = pen.glyph()


def _profile(character: str) -> tuple[float, float, int]:
    if character.isalpha():
        directions = {"a": 1, "e": -1, "g": 1, "i": -1, "j": 1, "n": -1, "r": 1}
        return 0.0065, 0.010, directions[character]
    if character.isdigit():
        return 0.0035, 0.007, 1 if int(character) % 2 == 0 else -1
    return 0.0025, 0.006, 1


def _transform_simple(font: TTFont, glyph_name: str, character: str, weight: int) -> bool:
    glyph = font["glyf"][glyph_name]
    if glyph.numberOfContours <= 0 or not hasattr(glyph, "coordinates"):
        return False
    coordinates = list(glyph.coordinates)
    if not coordinates:
        return False
    xs = [point[0] for point in coordinates]
    ys = [point[1] for point in coordinates]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    height = max(1, y_max - y_min)
    centre = (x_min + x_max) / 2
    upm = font["head"].unitsPerEm
    curve, warmth, direction = _profile(character)
    heavy_guard = 1.0 - 0.2 * ((weight - 100) / 800)
    amplitude = upm * curve * heavy_guard

    transformed: list[tuple[int, int]] = []
    for x, y in coordinates:
        vertical = (y - y_min) / height
        middle = max(0.0, 1.0 - abs(2.0 * vertical - 1.0))
        flow = math.sin(math.pi * vertical)
        dx = direction * amplitude * flow + (x - centre) * warmth * middle
        transformed.append((round(x + dx), y))
    glyph.coordinates = GlyphCoordinates(transformed)
    glyph.recalcBounds(font["glyf"])
    return True


def apply_brand_glyphs(font: TTFont, weight: int) -> BrandResult:
    """Apply the jinjer organic-flow treatment to the 26 approved glyphs.

    Related OpenType alternates (for example tabular numerals) receive the same
    treatment when their glyph names share the primary glyph prefix. Composite
    targets are decomposed first so interpolation remains deterministic.
    """
    cmap = font.getBestCmap() or {}
    order = font.getGlyphOrder()
    transformed: set[str] = set()
    for character in BRAND_PRIMARY_CHARS:
        primary = cmap.get(ord(character))
        if primary is None:
            raise RuntimeError(f"Brand glyph is missing from cmap: U+{ord(character):04X}")
        candidates = [primary]
        prefix = primary + "."
        candidates.extend(name for name in order if name.startswith(prefix))
        for glyph_name in candidates:
            if glyph_name in transformed:
                continue
            _decompose(font, glyph_name)
            if _transform_simple(font, glyph_name, character, weight):
                transformed.add(glyph_name)
    font["maxp"].recalc(font)
    return BrandResult(len(BRAND_PRIMARY_CHARS), len(transformed))
