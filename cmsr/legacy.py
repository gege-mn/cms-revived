from __future__ import annotations

from dataclasses import dataclass
from functools import cache

from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.ttLib import TTFont

from .config import CUTS, Cut

KEYS = "".join(chr(code) for code in range(0x20, 0x7F))


@dataclass
class LegacyFont:
    """One 1998 cut, addressed the way it was typed: by keyboard key."""

    cut: Cut
    ttf: TTFont

    @classmethod
    @cache
    def open(cls, cut_id: str) -> LegacyFont:
        cut = CUTS[cut_id]
        return cls(cut, TTFont(cut.legacy_path))

    @property
    def units_per_em(self) -> int:
        return self.ttf["head"].unitsPerEm

    def glyph_name(self, key: str) -> str:
        name = self.ttf.getBestCmap().get(ord(key))
        if name is None:
            raise KeyError(f"{self.cut.id} has no glyph on key {key!r}")
        return name

    def advance(self, glyph_name: str) -> int:
        return self.ttf["hmtx"][glyph_name][0]

    def keyed_glyphs(self) -> dict[str, str]:
        cmap = self.ttf.getBestCmap()
        return {key: cmap[ord(key)] for key in KEYS if ord(key) in cmap}

    def contours(self, glyph_name: str) -> list[list[tuple[str, tuple]]]:
        """The glyph's outline as one recording per contour, in drawing order."""

        recording = DecomposingRecordingPen(self.ttf.getGlyphSet())
        self.ttf.getGlyphSet()[glyph_name].draw(recording)
        found: list[list[tuple[str, tuple]]] = [[]]
        for operator, arguments in recording.value:
            found[-1].append((operator, arguments))
            if operator in ("closePath", "endPath"):
                found.append([])
        return [contour for contour in found if contour]

    def tip(self, glyph_name: str) -> float:
        """Where the glyph's first stroke reaches lowest along the run: a tooth's tip."""

        points = [point for _, arguments in self.contours(glyph_name)[0] for point in arguments if point is not None]
        return min(points, key=lambda point: point[1])[0] if points else 0
