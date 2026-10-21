"""Goldens: words checked against how the 1998 font typed them.

A golden is a Unicode word and the CMs keys a typist would use for it. It passes when the
built font, shaping the word, puts exactly the same 1998 outlines in exactly the same
places as the 1998 font typing the keys. Only a human can say what the keys are, so a
golden is `pending` until confirmed; a confirmed one that fails is a mapping to fix.
"""

from __future__ import annotations

import hashlib
import json
import tomllib
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Literal

import uharfbuzz as hb
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib import TTFont

from .config import ROOT
from .legacy import LegacyFont

GOLDENS_FILE = ROOT / "mapping" / "goldens.toml"
PLACEHOLDER = "□"
LIFTED = "·"
TRIMMED = "✂"
DRAWN = "✎"

HEADER = """\
# Goldens: words and the CMs keys that type them, checked against every build.
#
# status  pending  keys proposed, waiting for a human eye
#         ok       confirmed: the build must draw the word exactly as these keys did
#         fixed    differs from CMs on purpose: the build must keep drawing the snapshot
#
# The goldens page (/goldens in the editor) rewrites this file.
"""

Status = Literal["pending", "ok", "fixed"]


@dataclass
class Golden:
    text: str
    latin: str
    keys: str = ""
    status: Status = "pending"
    note: str = ""
    snapshot: dict[str, str] = field(default_factory=dict)  # per cut: each draws its own outlines


@dataclass
class Result:
    produced: str
    passed: bool
    signature: str
    suggestion: dict[str, str] | None = None  # {piece: keys} that would explain the typed keys


def load(path: Path = GOLDENS_FILE) -> list[Golden]:
    if not path.exists():
        return []
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    found = []
    for fields in raw.get("golden", []):
        if isinstance(fields.get("snapshot"), str):
            fields["snapshot"] = {}  # an early single snapshot; re-pinned on the next "differs on purpose"
        found.append(Golden(**fields))
    return found


def save(goldens: list[Golden], path: Path = GOLDENS_FILE) -> None:
    string = lambda value: json.dumps(value, ensure_ascii=False)  # noqa: E731
    lines = [HEADER]
    for golden in goldens:
        lines += ["[[golden]]", f"latin = {string(golden.latin)}", f"text = {string(golden.text)}"]
        lines += [f"keys = {string(golden.keys)}", f"status = {string(golden.status)}"]
        if golden.note:
            lines.append(f"note = {string(golden.note)}")
        if golden.snapshot:
            pins = ", ".join(f"{cut} = {string(value)}" for cut, value in sorted(golden.snapshot.items()))
            lines.append(f"snapshot = {{ {pins} }}")
        lines.append("")
    temporary = path.with_suffix(".toml.tmp")
    temporary.write_text("\n".join(lines), encoding="utf-8")
    temporary.replace(path)


def check(golden: Golden, font_path: Path, legacy: LegacyFont) -> Result:
    built = _built_leaves(font_path, golden.text)
    keys_by_glyph = {name: key for key, name in legacy.keyed_glyphs().items()}
    gaps = _gaps(font_path, golden.text)
    produced = ""
    for name, x, _ in built:
        while gaps and gaps[0] < x:
            produced += " "
            gaps.pop(0)
        produced += _typed(name, keys_by_glyph)
    signature = _signature(built, font_path)
    if golden.status == "fixed":
        return Result(produced, signature == golden.snapshot.get(legacy.cut.id), signature)
    passed = _same(built, _legacy_leaves(legacy, golden.keys))
    return Result(produced, passed, signature, None if passed else _suggest(built, produced, golden.keys))


def _typed(name: str, keys_by_glyph: dict[str, str]) -> str:
    if name in keys_by_glyph:
        return keys_by_glyph[name]
    base, trimmed, sides = name.partition(".trim")
    if trimmed and base in keys_by_glyph:
        return TRIMMED * (sides in ("_start", "_both")) + keys_by_glyph[base] + TRIMMED * (sides in ("", "_both"))
    if name.startswith("cmsr."):
        return DRAWN
    return LIFTED if name.startswith("cms.") else PLACEHOLDER


def _suggest(built: list[tuple[str, float, float]], produced: str, typed: str) -> dict[str, str] | None:
    """With one unmapped piece in the word, the typed keys around it say what it is."""

    holes = [name for name, _, _ in built if name.startswith("_")]
    if len(holes) != 1 or produced.count(PLACEHOLDER) != 1:
        return None
    before, after = produced.split(PLACEHOLDER)
    if not (typed.startswith(before) and typed.endswith(after)) or len(typed) <= len(before) + len(after):
        return None
    return {holes[0][1:]: typed[len(before) : len(typed) - len(after)]}


def _signature(leaves: list[tuple[str, float, float]], path: Path) -> str:
    """A short fingerprint of what the font draws, for a golden that differs on purpose."""

    if not leaves:
        return ""
    _, ttf = _font(path, path.stat().st_mtime_ns)
    glyph_set = ttf.getGlyphSet()

    def mark(name: str) -> str:
        # A hand drawing can be redrawn under the same name; dEgi's outlines never change.
        if not name.startswith("cmsr."):
            return name
        recording = RecordingPen()
        glyph_set[name].draw(recording)
        return f"{name}#{hashlib.sha1(repr(recording.value).encode()).hexdigest()[:8]}"

    x0 = leaves[0][1]
    text = ";".join(f"{mark(name)}@{round(x - x0)},{round(y)}" for name, x, y in leaves)
    return hashlib.sha1(text.encode()).hexdigest()[:12]


def _same(a: list[tuple[str, float, float]], b: list[tuple[str, float, float]]) -> bool:
    if [name for name, _, _ in a] != [name for name, _, _ in b] or not a:
        return False
    ax, bx = a[0][1], b[0][1]
    return all(abs((x1 - ax) - (x2 - bx)) <= 1 and abs(y1 - y2) <= 1 for (_, x1, y1), (_, x2, y2) in zip(a, b))


@cache
def _font(path: Path, revision: int) -> tuple[hb.Font, TTFont]:
    return hb.Font(hb.Face(hb.Blob.from_file_path(path))), TTFont(path)


def _built_leaves(path: Path, text: str) -> list[tuple[str, float, float]]:
    """The 1998 outlines the built font draws for *text*, as (legacy glyph, x, y)."""

    hb_font, ttf = _font(path, path.stat().st_mtime_ns)
    buffer = hb.Buffer()
    buffer.add_str(text)
    buffer.guess_segment_properties()
    hb.shape(hb_font, buffer)
    glyf = ttf["glyf"]
    leaves: list[tuple[str, float, float]] = []

    def walk(name: str, x: float, y: float) -> None:
        glyph = glyf[name]
        if glyph.isComposite():
            for component in glyph.components:
                walk(component.glyphName, x + component.x, y + component.y)
        elif glyph.numberOfContours:
            leaves.append((name.removeprefix("cms."), x, y) if name.startswith("cms.") and ".c" not in name[4:] else (name, x, y))

    pen = 0
    for info, position in zip(buffer.glyph_infos, buffer.glyph_positions):
        walk(hb_font.glyph_to_string(info.codepoint), pen + position.x_offset, position.y_offset)
        pen += position.x_advance
    return sorted(leaves, key=lambda leaf: leaf[1])


def _gaps(path: Path, text: str) -> list[float]:
    """Where the shaped text has blank space of its own, such as the gap an MVS puts before a suffix."""

    hb_font, ttf = _font(path, path.stat().st_mtime_ns)
    buffer = hb.Buffer()
    buffer.add_str(text)
    buffer.guess_segment_properties()
    hb.shape(hb_font, buffer)
    glyph_set = ttf.getGlyphSet()
    found, pen = [], 0
    for info, position in zip(buffer.glyph_infos, buffer.glyph_positions):
        bounds = BoundsPen(glyph_set)
        glyph_set[hb_font.glyph_to_string(info.codepoint)].draw(bounds)
        if position.x_advance and bounds.bounds is None:
            found.append(pen)
        pen += position.x_advance
    return found


def _legacy_leaves(legacy: LegacyFont, keys: str) -> list[tuple[str, float, float]]:
    x = 0
    leaves = []
    for key in keys:
        name = legacy.keyed_glyphs().get(key)
        if name is None:
            return []
        if legacy.ttf["glyf"][name].numberOfContours:
            leaves.append((name, x, 0))
        x += legacy.advance(name)
    return leaves


def pin(golden: Golden) -> None:
    """Accept what every cut draws now as this golden's expected drawing."""

    from .build import build
    from .config import CUTS

    for cut in CUTS.values():
        if not cut.output_path.exists():
            build(cut.id)
        golden.snapshot[cut.id] = check(golden, cut.output_path, LegacyFont.open(cut.id)).signature
