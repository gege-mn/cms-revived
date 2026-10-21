"""Build a Unicode font from one 1998 cut and the mapping.

The 1998 glyphs come in once, unencoded, as `cms.<name>`. Every target is a composite of
them in typing order, so a piece is drawn with exactly the outlines and advances the old
keyboard drew it with. mongfontbuilder then writes the shaping and builds every variant out
of the pieces.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from fontTools.misc.transform import Transform
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from mongfontbuilder.otl import MongFeaComposer
from mongfontbuilder.spec import applySpecToFont
from ufo2ft import compileTTF
from ufoLib2 import Font
from ufoLib2.objects import Component

from . import config
from .legacy import LegacyFont
from .mapping import Mapping, Mark
from .targets import CONTROLS, Target, targets

PLACEHOLDER_WIDTH = 400


@dataclass
class BuildResult:
    cut_id: str
    path: Path
    placeholders: list[str] = field(default_factory=list)
    drawn: list[str] = field(default_factory=list)
    keyed: list[str] = field(default_factory=list)


def build(cut_id: str, mapping: Mapping | None = None, *, strict: bool = False) -> BuildResult:
    mapping = mapping or Mapping.load()
    cut = config.CUTS[cut_id]
    legacy = LegacyFont.open(cut_id)
    result = BuildResult(cut_id, cut.output_path)

    ufo = Font()
    _set_info(ufo, cut, legacy)
    _import_legacy(ufo, legacy)
    drawings = Font.open(cut.drawings_path) if cut.drawings_path.exists() else None
    stem = _stem(legacy)

    for entry in mapping.all():
        target = mapping.targets.get(entry.name) or Target(entry.name, "form")
        keys = entry.keys_for(cut_id)
        if drawings is not None and target.glyph in drawings:
            _copy_drawing(ufo, drawings[target.glyph], target.glyph)
            result.drawn.append(entry.name)
        elif keys or entry.marks:
            _compose_keys(ufo, legacy, target.glyph, keys or "", entry.marks)
            result.keyed.append(entry.name)
        elif target.kind in ("piece", "char"):
            _placeholder(ufo, target.glyph, stem)
            result.placeholders.append(entry.name)
        else:
            continue
        if target.kind == "char":
            ufo[target.glyph].unicodes = [int(target.name[2:], 16)]

    if strict and result.placeholders:
        raise SystemExit(f"{cut_id}: {len(result.placeholders)} targets still unmapped")

    _add_controls(ufo, legacy)

    composer = MongFeaComposer(
        cmap={code_point: name for name in ufo.keys() for code_point in ufo[name].unicodes},
        glyphs=[*ufo.keys()],
        locales=[config.LOCALE],
    )
    scale = legacy.units_per_em / 1000
    applySpecToFont(composer.compose(), ufo, initPadding=40 * scale, finaPadding=100 * scale)
    ufo.features.text = composer.asFeatureFile().asFea()

    cut.output_path.parent.mkdir(parents=True, exist_ok=True)
    # The outlines come straight from a TrueType font: already quadratic and already in
    # TrueType contour direction. Glyph names stay readable so shaping can be checked by name.
    compileTTF(
        ufo,
        useProductionNames=False,
        removeOverlaps=False,
        reverseDirection=False,
    ).save(cut.output_path)
    return result


def _set_info(ufo: Font, cut: config.Cut, legacy: LegacyFont) -> None:
    source = legacy.ttf
    info = ufo.info
    major, minor = config.VERSION
    info.familyName = cut.family
    info.styleName = "Regular"
    info.versionMajor = major
    info.versionMinor = minor
    info.copyright = config.COPYRIGHT
    info.openTypeNameDesigner = config.DESIGNER
    info.openTypeNameManufacturer = config.MANUFACTURER
    info.openTypeOS2VendorID = config.VENDOR_ID
    if config.VENDOR_URL:
        info.openTypeNameManufacturerURL = config.VENDOR_URL
    info.openTypeNameDescription = config.DESCRIPTION
    info.openTypeNameLicense = config.LICENSE
    info.openTypeNameVersion = f"Version {major}.{minor:03d}; dEgi 1998, Unicode rework 2026"
    info.postscriptFontName = cut.postscript_name
    info.unitsPerEm = legacy.units_per_em
    info.ascender = source["hhea"].ascent
    info.descender = source["hhea"].descent
    info.openTypeHheaAscender = source["hhea"].ascent
    info.openTypeHheaDescender = source["hhea"].descent
    info.openTypeHheaLineGap = source["hhea"].lineGap
    info.openTypeOS2TypoAscender = source["OS/2"].sTypoAscender
    info.openTypeOS2TypoDescender = source["OS/2"].sTypoDescender
    info.openTypeOS2TypoLineGap = source["OS/2"].sTypoLineGap
    info.openTypeOS2WinAscent = source["OS/2"].usWinAscent
    info.openTypeOS2WinDescent = source["OS/2"].usWinDescent


def legacy_glyph_name(name: str) -> str:
    return f"cms.{name}"


def _import_legacy(ufo: Font, legacy: LegacyFont) -> None:
    glyph_set = legacy.ttf.getGlyphSet()
    for name in legacy.ttf.getGlyphOrder():
        recording = DecomposingRecordingPen(glyph_set)
        glyph_set[name].draw(recording)
        target = ufo.newGlyph(".notdef" if name == ".notdef" else legacy_glyph_name(name))
        recording.replay(target.getPen())
        target.width = legacy.advance(name)


def _compose_keys(ufo: Font, legacy: LegacyFont, glyph_name: str, keys: str, marks: list[Mark] = ()) -> None:
    glyph = ufo.newGlyph(glyph_name)
    x = 0
    for key in keys:
        name = legacy.glyph_name(key)
        glyph.components.append(Component(legacy_glyph_name(name), Transform(dx=x)))
        x += legacy.advance(name)
    for mark in marks:
        base = _mark_glyph(ufo, legacy, mark)
        glyph.components.append(Component(base, Transform(dx=mark.dx, dy=mark.dy)))
    glyph.width = x


def _mark_glyph(ufo: Font, legacy: LegacyFont, mark: Mark) -> str:
    """The glyph a mark is drawn from: the whole key, or just the contours it lifts."""

    name = legacy.glyph_name(mark.key)
    if mark.contours is None:
        return legacy_glyph_name(name)
    lifted = f"{legacy_glyph_name(name)}.c{'_'.join(str(index) for index in mark.contours)}"
    if lifted not in ufo:
        contours = legacy.contours(name)
        glyph = ufo.newGlyph(lifted)
        pen = glyph.getPen()
        for index in mark.contours:
            for operator, arguments in contours[index]:
                getattr(pen, operator)(*arguments)
    return lifted


def _copy_drawing(ufo: Font, source, glyph_name: str) -> None:
    glyph = ufo.newGlyph(glyph_name)
    source.drawPoints(glyph.getPointPen())
    glyph.width = source.width


def _stem(legacy: LegacyFont) -> tuple[float, float]:
    """The vertical extent of the stem, read off the stem extender on the hyphen key."""

    glyph_set = legacy.ttf.getGlyphSet()
    pen = BoundsPen(glyph_set)
    glyph_set[legacy.glyph_name("-")].draw(pen)
    _, bottom, _, top = pen.bounds
    return bottom, top


def _placeholder(ufo: Font, glyph_name: str, stem: tuple[float, float]) -> None:
    """A stem segment with an empty box hanging off it: joins the run, and is plainly missing."""

    bottom, top = stem
    width = PLACEHOLDER_WIDTH
    inset = (top - bottom) / 2
    box_bottom = bottom - width * 0.75
    glyph = ufo.newGlyph(glyph_name)
    pen = glyph.getPen()
    for x0, y0, x1, y1, clockwise in (
        (0, bottom, width, top, True),
        (inset, box_bottom, width - inset, bottom, True),
        (inset * 2, box_bottom + inset, width - inset * 2, bottom - inset, False),
    ):
        points = [(x0, y0), (x0, y1), (x1, y1), (x1, y0)]
        if not clockwise:
            points.reverse()
        pen.moveTo(points[0])
        for point in points[1:]:
            pen.lineTo(point)
        pen.closePath()
    glyph.width = width


def _add_controls(ufo: Font, legacy: LegacyFont) -> None:
    space = legacy.advance(legacy.glyph_name(" "))
    widths = {"space": space, "mvs": space / 2, "nnbsp": space / 2}
    for name, code_point in CONTROLS.items():
        if name not in ufo:
            ufo.newGlyph(name).width = round(widths.get(name, 0))
        ufo[name].unicodes = [code_point]
    narrow = ufo.newGlyph("mvs.narrow")
    narrow.width = round(space * 0.18)
