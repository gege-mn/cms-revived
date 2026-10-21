from __future__ import annotations

from dataclasses import dataclass
from functools import cache

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
