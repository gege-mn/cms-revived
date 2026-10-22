"""What a Hudum font has to draw, as mongfontbuilder sees it.

Everything here is derived from the pinned mongfontbuilder data, so a new version of the
library changes the targets without anyone editing a list.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from typing import Literal

from fontTools import unicodedata
from mongfontbuilder import GlyphDescriptor, data
from mongfontbuilder.otl import MongFeaComposer
from mongfontbuilder.otl.iib import LigatureCollector

from .config import LOCALE

Kind = Literal["piece", "mvs", "ligature", "char", "form"]

CONTROLS = {
    "space": 0x0020,
    "nirugu": 0x180A,
    "fvs1": 0x180B,
    "fvs2": 0x180C,
    "fvs3": 0x180D,
    "fvs4": 0x180F,
    "mvs": 0x180E,
    "nnbsp": 0x202F,
    "zwj": 0x200D,
    "zwnj": 0x200C,
}

# Punctuation and digits a Hudum font carries besides the letters. U+180A is the nirugu,
# which shaping treats as a control but which is drawn as a piece of stem.
CHARS = [
    0x1800, 0x1801, 0x1802, 0x1803, 0x1804, 0x1805, 0x180A,
    *range(0x1810, 0x181A),
    0x0021, 0x003F, 0x0028, 0x0029, 0x3008, 0x3009, 0x300A, 0x300B,
]


@dataclass(frozen=True)
class Target:
    name: str
    kind: Kind
    required: bool = True

    @property
    def glyph(self) -> str:
        if self.kind == "char":
            return char_glyph_name(int(self.name[2:], 16))
        return "_" + self.name


@dataclass(frozen=True)
class Variant:
    """One written form of a letter: letter x joining position x FVS."""

    id: str
    code_point: int
    position: str
    fvs: int
    default: bool
    units: tuple[str, ...]
    written_position: str
    glyph: str

    @property
    def written(self) -> str:
        return "".join(self.units) + "." + self.written_position

    @property
    def atoms(self) -> list[str]:
        return atoms_of(self.units, self.written_position)


def char_glyph_name(code_point: int) -> str:
    return "nirugu" if code_point == 0x180A else f"u{code_point:04X}"


def atoms_of(units: tuple[str, ...] | list[str], position: str) -> list[str]:
    """The written form broken into single written units, each in its own position."""

    count = len(units)
    atoms = []
    for index, unit in enumerate(units):
        joins_before = position in ("medi", "fina") or index > 0
        joins_after = position in ("init", "medi") or index < count - 1
        atoms.append(
            f"{unit}."
            + ("medi" if joins_before and joins_after else "init" if joins_after else "fina" if joins_before else "isol")
        )
    return atoms


@cache
def variants() -> list[Variant]:
    found = []
    for char_name, positions in data.variants.items():
        code_point = ord(unicodedata.lookup(char_name))
        for position, by_fvs in positions.items():
            for fvs, variant in by_fvs.items():
                if LOCALE not in variant.locales:
                    continue
                descriptor = GlyphDescriptor.fromData(char_name, position, variant, locale=LOCALE)
                found.append(
                    Variant(
                        id=f"u{code_point:04X}.{position}.{fvs}",
                        code_point=code_point,
                        position=position,
                        fvs=int(fvs),
                        default=bool(variant.default),
                        units=tuple(descriptor.units),
                        written_position=descriptor.position,
                        glyph=str(descriptor),
                    )
                )
    return found


@cache
def targets() -> list[Target]:
    pieces: list[str] = []
    for variant in variants():
        for atom in variant.atoms:
            if atom not in pieces:
                pieces.append(atom)

    found = [Target(piece, "piece") for piece in pieces]
    found += [
        Target(f"{unit}.{position}.mvs", "mvs", required=False)
        for unit, positions in data.writtenUnits.items()
        for position, codes in positions.items()
        if "pre_mvs" in _codes(codes) and f"{unit}.{position}" in pieces
    ]
    found += [Target(name, "ligature", required) for name, required in _ligatures(pieces).items()]
    found += [Target(f"U+{code_point:04X}", "char") for code_point in CHARS]
    return found


def _codes(codes: object) -> set[str]:
    if isinstance(codes, dict):
        return set(codes)
    return {name for name in dir(codes) if not name.startswith("_")}


def _ligatures(pieces: list[str]) -> dict[str, bool]:
    """The ligatures the shaping would use, given every piece is drawn.

    The composer only writes a ligature when the font draws it, so ask it with a glyph set
    that has every piece and read off what it would substitute.
    """

    composer = MongFeaComposer(
        cmap={code_point: name for name, code_point in CONTROLS.items()},
        glyphs=[*CONTROLS, *("_" + piece for piece in pieces)],
        locales=[LOCALE],
    )
    composer.initWrittenUnits()
    composer.constructPredefinedGlyphs()
    composer.initControls()
    composer.initVariants()
    found: dict[str, bool] = {}
    for ligature, required in LigatureCollector(composer).collect().values():
        name = "".join(ligature.units) + "." + ligature.position
        found[name] = found.get(name, False) or required
    return dict(sorted(found.items(), key=lambda item: (not item[1], _ligature_order(item[0]))))


def _ligature_order(name: str) -> tuple[int, str]:
    position = name.rsplit(".", 1)[1]
    return ("isol", "init", "medi", "fina").index(position), name


def is_written_form(name: str) -> bool:
    if name in {variant.glyph for variant in variants()}:
        return True
    try:
        GlyphDescriptor.parse("_" + name)
    except (AssertionError, ValueError):
        return False
    return True
