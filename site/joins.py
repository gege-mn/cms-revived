"""Before and after of a join: CMs as typed in 1998 against the rework, cropped to where the ink changed.

Both come from the legacy-keyed companion: with its features off it is dEgi's 1998 font, with
them on it draws as the Unicode build.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from pathlib import Path

import pathops
import uharfbuzz as hb
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

OFF = {"liga": False, "calt": False}


@cache
def _font(path: Path) -> tuple[TTFont, hb.Font]:
    return TTFont(path), hb.Font(hb.Face(hb.Blob.from_file_path(str(path))))


def ink(path: Path, text: str, features: dict[str, bool]) -> pathops.Path:
    ttf, font = _font(path)
    glyphs = ttf.getGlyphSet()
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(font, buf, features)
    out = pathops.Path()
    x = 0
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        rec = DecomposingRecordingPen(glyphs)
        glyphs[ttf.getGlyphName(info.codepoint)].draw(rec)
        piece = pathops.Path()
        rec.replay(TransformPen(piece.getPen(), (1, 0, 0, 1, x + pos.x_offset, pos.y_offset)))
        try:
            piece.simplify()
        except pathops.PathOpsError:
            pass
        out = pathops.op(out, piece, pathops.PathOp.UNION)
        x += pos.x_advance
    return out


def _d(path: pathops.Path) -> str:
    pen = SVGPathPen(None)
    path.draw(pen)
    return pen.getCommands()


@dataclass
class Join:
    before: pathops.Path
    after: pathops.Path
    upem: int

    @classmethod
    def of(cls, companion: Path, keys: str) -> Join:
        return cls(ink(companion, keys, OFF), ink(companion, keys, {}), _font(companion)[0]["head"].unitsPerEm)

    def crop(self, at: float | None = None, size_em: float = 0.8) -> tuple[float, float, float, float]:
        """Square font-unit box (xmin, ymin, xmax, ymax) on the join.

        `at` is how far down the word the join sits, 0 to 1. Without it the box goes where 1998's
        ink falls apart: the start of the first piece that does not touch the rest.
        """
        x0, y0, x1, y1 = self.after.bounds
        if at is not None:
            cx = x0 + (x1 - x0) * at
        else:
            contours = list(self.before.contours)
            biggest = max(contours, key=lambda c: abs(c.area))
            loose = max(
                (c for c in contours if c is not biggest and c.clockwise == biggest.clockwise),
                key=lambda c: abs(c.area),
            )
            a, b = pathops.Path(), pathops.Path()
            biggest.draw(a.getPen())
            loose.draw(b.getPen())
            # The gap sits where the loose piece ends nearest the rest of the word.
            cx = b.bounds[2] if b.bounds[0] < a.bounds[0] else b.bounds[0]
        cy = (y0 + y1) / 2
        side = size_em * self.upem
        return cx - side / 2, cy - side / 2, cx + side / 2, cy + side / 2

    def svg(self, which: str, box: tuple[float, float, float, float], label: str) -> str:
        # Vertical Mongolian is the horizontal line turned a quarter clockwise: font x runs down,
        # font y runs right. matrix(0 1 1 0) swaps them.
        x0, y0, x1, y1 = box
        path = self.before if which == "before" else self.after
        return (
            f'<svg viewBox="{y0:.0f} {x0:.0f} {y1 - y0:.0f} {x1 - x0:.0f}" role="img" aria-label="{label}">'
            f'<g transform="matrix(0 1 1 0 0 0)"><path d="{_d(path)}" fill="currentColor"/></g></svg>'
        )

    def whole(self, box: tuple[float, float, float, float], label: str) -> str:
        bx0, by0, bx1, by1 = box
        pad = self.upem * 0.06
        x0, y0, x1, y1 = self.after.bounds
        x0, y0, x1, y1 = min(x0, bx0) - pad, min(y0, by0) - pad, max(x1, bx1) + pad, max(y1, by1) + pad
        return (
            f'<svg viewBox="{y0:.0f} {x0:.0f} {y1 - y0:.0f} {x1 - x0:.0f}" role="img" aria-label="{label}">'
            f'<g transform="matrix(0 1 1 0 0 0)"><path d="{_d(self.after)}" fill="currentColor"/></g>'
            f'<rect class="lens" x="{by0:.0f}" y="{bx0:.0f}" width="{by1 - by0:.0f}" height="{bx1 - bx0:.0f}" rx="{self.upem * 0.08:.0f}"/>'
            "</svg>"
        )
