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

from . import config, neighbours
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
            _compose_keys(ufo, legacy, target.glyph, keys or "", entry.marks, entry.shift, stem if entry.trim else None)
            result.keyed.append(entry.name)
        elif target.kind in ("piece", "char"):
            _placeholder(ufo, target.glyph, stem)
            result.placeholders.append(entry.name)
        else:
            continue
        if target.kind == "char":
            ufo[target.glyph].unicodes = [int(target.name[2:], 16)]

    found_rules = neighbours.rules(mapping)
    for (piece, previous), keys in found_rules.items():
        name = neighbours.rule_glyph(piece, previous)
        drawn = _rule_drawing(drawings, mapping, piece, previous)
        if drawn is not None:
            _copy_drawing(ufo, drawn, name)
        else:
            entry = mapping.get(piece)
            _compose_keys(ufo, legacy, name, keys, entry.marks, trim=stem if entry.trim else None)
    neighbours.add_inner_forms(ufo, found_rules)
    _add_shorter_ligatures(ufo, mapping, found_rules)

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
    ufo.features.text = composer.asFeatureFile().asFea() + neighbours.features(ufo, found_rules)

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


def _add_shorter_ligatures(ufo: Font, mapping: Mapping, found_rules: dict) -> None:
    """Give every drawn ligature the shorter ligatures it is built on.

    mongfontbuilder writes a longer ligature from the glyph a shorter one produces (GOI from
    GO + I), so once GOI is drawn the font must carry GO as well; it is drawn from its
    pieces, which is what the text would show without it.
    """

    ligatures = [target for target in mapping.targets.values() if target.kind == "ligature"]
    for target in ligatures:
        if target.glyph not in ufo:
            continue
        units, position = target.name.split(".")[:2]
        for shorter in ligatures:
            short_units, short_position = shorter.name.split(".")[:2]
            prefix_position = "init" if position in ("isol", "init") else "medi"
            if short_position == prefix_position and units.startswith(short_units) and units != short_units:
                neighbours.compose_from_pieces(ufo, shorter.name, found_rules)


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


def _compose_keys(
    ufo: Font,
    legacy: LegacyFont,
    glyph_name: str,
    keys: str,
    marks: list[Mark] = (),
    shift: dict[int, int] | None = None,
    trim: tuple[float, float] | None = None,
) -> None:
    glyph = ufo.newGlyph(glyph_name)
    x = 0
    origins = []
    for index, key in enumerate(keys):
        x += (shift or {}).get(index, 0)
        name = legacy.glyph_name(key)
        origins.append(x)
        if trim and index == len(keys) - 1:
            trimmed, advance = _trimmed(ufo, legacy, name, trim)
            glyph.components.append(Component(trimmed, Transform(dx=x)))
            x += advance
            continue
        glyph.components.append(Component(legacy_glyph_name(name), Transform(dx=x)))
        x += legacy.advance(name)
    for mark in marks:
        base = _mark_glyph(ufo, legacy, mark)
        dx = mark.dx
        if mark.on is not None:
            dx += origins[mark.on] + legacy.tip(legacy.glyph_name(keys[mark.on])) - legacy.tip(legacy.glyph_name(mark.key))
        glyph.components.append(Component(base, Transform(dx=dx, dy=mark.dy)))
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


def _trimmed(ufo: Font, legacy: LegacyFont, name: str, stem: tuple[float, float]) -> tuple[str, float]:
    """The key with its stem cut where its body ends: what hangs below or rises above it."""

    bottom, top = stem
    contours = legacy.contours(name)
    points = [point for contour in contours for _, arguments in contour for point in arguments if point is not None]
    body = [x for x, y in points if y < bottom - 1 or y > top + 1]
    end = max(body) if body else legacy.advance(name)
    trimmed = f"{legacy_glyph_name(name)}.trim"
    if trimmed not in ufo:
        glyph = ufo.newGlyph(trimmed)
        pen = glyph.getPen()
        # The stem past the body is a plain bar, so pulling its end points back is the cut.
        clamp = lambda point: (min(point[0], end), point[1]) if bottom - 1 <= point[1] <= top + 1 else point  # noqa: E731
        for contour in contours:
            for operator, arguments in contour:
                getattr(pen, operator)(*(clamp(point) if point is not None else None for point in arguments))
        glyph.width = end
    return trimmed, end


def _rule_drawing(drawings: Font | None, mapping: Mapping, piece: str, previous: str):
    """A rule drawn by hand, where no 1998 keys can type it: under the rule's own name, or
    under its group's (cmsr.L.medi.after.@arch draws L.medi after every arch letter)."""

    if drawings is None:
        return None
    after = mapping.get(piece).after
    names = [neighbours.rule_glyph(piece, previous)]
    # As with keys, a rule for the piece itself wins over its group's drawing.
    if previous not in after:
        names += [
            neighbours.rule_glyph(piece, rule)
            for rule in after
            if rule.startswith("@") and previous in mapping.groups.get(rule[1:], [])
        ]
    return next((drawings[name] for name in names if name in drawings), None)


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
    # The narrow MVS only ever stands before a chachlag a/e, and CMs draws that gap into the
    # a itself (the T key starts with blank space), so the mark adds none of its own.
    ufo.newGlyph("mvs.narrow").width = 0
