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
from fontTools.pens.reverseContourPen import ReverseContourPen
from fontTools.pens.transformPen import TransformPen
from mongfontbuilder.otl import MongFeaComposer
from mongfontbuilder.spec import applySpecToFont
from pathops import Path as Outline
from pathops import PathOp, op
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
    # Targets nothing draws yet. They are built as boxes, so the shaping can be composed, then cut
    # out of the font with everything drawn from them: the text falls back to the plain form.
    left_out: list[str] = field(default_factory=list)
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
    _override_keys(ufo, drawings)
    stem = _stem(legacy)

    for entry in mapping.all():
        target = mapping.targets.get(entry.name) or Target(entry.name, "form")
        keys = entry.keys_for(cut_id)
        if drawings is not None and target.glyph in drawings:
            _copy_drawing(ufo, drawings[target.glyph], target.glyph)
            result.drawn.append(entry.name)
        elif keys or entry.marks:
            _compose_keys(
                ufo, legacy, target.glyph, keys or "", entry.marks, entry.shift_for(cut_id), entry.trim_for(cut_id), stem,
                entry.drop, _variants(ufo, mapping, cut_id, None),
            )
            result.keyed.append(entry.name)
        elif target.kind in ("piece", "char"):
            _placeholder(ufo, target.glyph, stem)
            result.left_out.append(entry.name)
        else:
            continue
        if target.kind == "char":
            ufo[target.glyph].unicodes = [int(target.name[2:], 16)]

    found_rules = neighbours.rules(mapping)
    for (piece, previous), rule in found_rules.items():
        name = neighbours.rule_glyph(piece, previous)
        drawn = _rule_drawing(drawings, mapping, piece, previous)
        if drawn is not None:
            _copy_drawing(ufo, drawn, name)
        else:
            entry = mapping.get(piece)
            trim = rule.trim or entry.trim_for(cut_id)
            shift = rule.shifts.get(cut_id, rule.shift)
            _compose_keys(ufo, legacy, name, rule.keys, rule.marks or entry.marks, shift, trim, stem, None, _variants(ufo, mapping, cut_id, previous))
    found_before = neighbours.before_rules(mapping)
    for (piece, following), rule in found_before.items():
        name = neighbours.before_rule_glyph(piece, following)
        drawn = _before_drawing(drawings, mapping, piece, following)
        if drawn is not None:
            _copy_drawing(ufo, drawn, name)
        else:
            entry = mapping.get(piece)
            _compose_keys(ufo, legacy, name, rule.keys, rule.marks or entry.marks, rule.shifts.get(cut_id, rule.shift), rule.trim, stem)
    neighbours.add_inner_forms(ufo, found_rules)
    _add_shorter_ligatures(ufo, mapping, found_rules)

    if strict and result.left_out:
        raise SystemExit(f"{cut_id}: {len(result.left_out)} targets still unmapped")

    _add_controls(ufo, legacy)

    composer = MongFeaComposer(
        cmap={code_point: name for name in ufo.keys() for code_point in ufo[name].unicodes},
        glyphs=[*ufo.keys()],
        locales=[config.LOCALE],
    )
    scale = legacy.units_per_em / 1000
    applySpecToFont(composer.compose(), ufo, initPadding=40 * scale, finaPadding=100 * scale)
    _letter_forms(ufo, mapping)
    ufo.features.text = composer.asFeatureFile().asFea() + neighbours.features(ufo, found_rules, found_before)

    cut.output_path.parent.mkdir(parents=True, exist_ok=True)
    # The outlines come straight from a TrueType font: already quadratic and already in
    # TrueType contour direction. Glyph names stay readable so shaping can be checked by name.
    ttf = compileTTF(
        ufo,
        useProductionNames=False,
        removeOverlaps=False,
        reverseDirection=False,
    )
    left_out = {(mapping.targets.get(name) or Target(name, "form")).glyph for name in result.left_out}
    _leave_out(ttf, _drawn_from(ufo, left_out))
    ttf.save(cut.output_path)
    return result


def _drawn_from(ufo: Font, names: set[str]) -> set[str]:
    found = set(names)
    while True:
        more = {glyph.name for glyph in ufo if glyph.name not in found and any(c.baseGlyph in found for c in glyph.components)}
        if not more:
            return found
        found |= more


def _leave_out(ttf, names: set[str]) -> None:
    if not names:
        return
    from fontTools import subset

    options = subset.Options()
    options.layout_features = ["*"]
    options.layout_closure = False
    options.name_IDs = ["*"]
    options.name_languages = ["*"]
    options.name_legacy = True
    options.glyph_names = True
    options.notdef_glyph = True
    options.notdef_outline = True
    options.legacy_kern = True
    options.hinting = True
    options.drop_tables = []
    options.prune_unicode_ranges = False
    options.recalc_bounds = True
    keep = [name for name in ttf.getGlyphOrder() if name not in names]
    subsetter = subset.Subsetter(options)
    subsetter.populate(glyphs=keep)
    subsetter.subset(ttf)
    # The rules that reached the left-out glyphs are gone now; a second pass from the cmap,
    # following the rules, drops what only they reached (joins drawn after a left-out piece).
    options.layout_closure = True
    subsetter = subset.Subsetter(options)
    subsetter.populate(unicodes=ttf.getBestCmap().keys())
    subsetter.subset(ttf)


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
    label = f"; {config.VERSION_LABEL}" if config.VERSION_LABEL else ""
    info.openTypeNameVersion = f"Version {major}.{minor:03d}{label}; dEgi 1998, Unicode rework 2026"
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


def composed_preview(cut_id: str, keys: str, marks, shift, trim: str, drop) -> tuple[Font, str]:
    """One entry's keys composed as the build composes them, for the editor's preview of
    what a browser cannot redo: dropped teeth and keys clipped under the key before."""

    legacy = LegacyFont.open(cut_id)
    ufo = Font()
    _import_legacy(ufo, legacy)
    cut = config.CUTS[cut_id]
    _override_keys(ufo, Font.open(cut.drawings_path) if cut.drawings_path.exists() else None)
    _compose_keys(ufo, legacy, "preview", keys, marks, shift, trim, _stem(legacy), drop, _variants(ufo, Mapping.load(), cut_id, None))
    return ufo, "preview"


def _letter_forms(ufo: Font, mapping: Mapping) -> None:
    """A form mapped for one letter only (u1835.I.init: j's I.init, J), where letters share the
    written unit but CMs typed them differently; i and y keep the shared I.init. The letter's
    other glyphs on that unit, such as the isolate drawn with it (u1835.I.init._isol), follow."""

    for entry in mapping.all():
        own = f"_{entry.name}"
        if entry.kind != "form" or entry.name not in ufo or own not in ufo:
            continue
        shared = "_" + entry.name.split(".", 1)[1]
        for name in [entry.name, *(name for name in ufo.keys() if name.startswith(f"{entry.name}._"))]:
            glyph = ufo[name]
            for component in glyph.components:
                if component.baseGlyph == shared:
                    component.baseGlyph = own
                    # keep the padding mongfontbuilder added around the shared piece
                    glyph.width += ufo[own].width - ufo[shared].width


def _override_keys(ufo: Font, drawings: Font | None) -> None:
    """A drawing named after a 1998 glyph (cms.<name>) redraws that key for the whole cut, so
    every piece and ligature typed with it gets the fix, such as a bowl nudged into place."""

    for name in drawings.keys() if drawings is not None else ():
        if name.startswith("cms.") and name in ufo:
            target = ufo[name]
            target.clearContours()
            drawings[name].draw(target.getPen())
            target.width = drawings[name].width
    # cms.<name>.@<group> redraws the key only right after a piece of that group (see _variants).
    for name in drawings.keys() if drawings is not None else ():
        base, _, group = name.partition(".@")
        if name.startswith("cms.") and group and base in ufo:
            _copy_drawing(ufo, drawings[name], name)


def _outline_of(ufo: Font, name: str) -> tuple:
    recording = DecomposingRecordingPen(ufo)
    ufo[name].draw(recording)
    return ufo[name].width, tuple(recording.value)


def _variants(ufo: Font, mapping: Mapping, cut_id: str, previous: str | None):
    """Which drawing of a key to set: cms.<name>.@<group> when what comes before belongs to the
    group (the smallest such group wins), else the key itself. What comes before is the key
    before in the same keys (k before E in ekE), or for the first key the rule's previous piece.
    Only keys set as they are take a variant; trimmed, clipped or dropped keys keep the key."""

    def groups_of(pieces: set[str]) -> list[str]:
        return sorted((name for name, members in mapping.groups.items() if pieces & set(members)), key=lambda name: len(mapping.groups[name]))

    def choose(keys: str, index: int, glyph: str) -> str:
        base = legacy_glyph_name(glyph)
        if index > 0:
            pieces = {entry.name for entry in mapping.all() if entry.keys_for(cut_id) == keys[index - 1]}
        else:
            pieces = {previous} if previous else set()
        for group in groups_of(pieces):
            name = f"{base}.@{group}"
            if name in ufo:
                # Until it is redrawn a variant is the key itself, and keeping the key's name
                # keeps the goldens pinned to it.
                return base if _outline_of(ufo, name) == _outline_of(ufo, base) else name
        return base

    return choose


def _compose_keys(
    ufo: Font,
    legacy: LegacyFont,
    glyph_name: str,
    keys: str,
    marks: list[Mark] = (),
    shift: dict[int, int] | None = None,
    trim: str = "",
    stem: tuple[float, float] = (0, 0),
    drop: dict[int, int] | None = None,
    variant=None,
) -> None:
    glyph = ufo.newGlyph(glyph_name)
    x = 0
    origins = []
    for index, key in enumerate(keys):
        x += (shift or {}).get(index, 0)
        name = legacy.glyph_name(key)
        origins.append(x)
        if (drop or {}).get(index):
            # The key before draws these teeth; what is left starts on the stem, over that key's,
            # and is clipped to that key's ink as a moved key is (Huree's stem is not a bar).
            dropped = _dropped(ufo, legacy, name, drop[index], stem)
            if index > 0:
                previous = legacy.glyph_name(keys[index - 1])
                reach = origins[index - 1] + legacy.advance(previous) - x
                if reach > 0:
                    dropped = _clipped(ufo, legacy, name, previous, legacy.advance(previous) - reach, reach, stem, dropped)
            glyph.components.append(Component(dropped, Transform(dx=x)))
            x += legacy.advance(name)
            continue
        start = index == 0 and trim in ("start", "both")
        end = index == len(keys) - 1 and trim in ("end", "both")
        if start or end:
            trimmed, advance = _trimmed(ufo, legacy, name, stem, start, end)
            glyph.components.append(Component(trimmed, Transform(dx=x)))
            x += advance
            continue
        if (shift or {}).get(index, 0) < 0 and index > 0 and keys[index - 1] == "-" and glyph.components:
            # dEgi's stem piece slid under a key would run on through its counter (an arch
            # would read as KHA): the stem stops where the key begins.
            previous = legacy.glyph_name(keys[index - 1])
            if glyph.components[-1].baseGlyph == legacy_glyph_name(previous):
                length = x - origins[index - 1]
                glyph.components[-1] = Component(_stem_to(ufo, legacy, previous, length), Transform(dx=origins[index - 1]))
                glyph.components.append(Component(legacy_glyph_name(name), Transform(dx=x)))
                x += legacy.advance(name)
                continue
        if (shift or {}).get(index, 0) < 0 and index > 0:
            # A key redrawn for this arch family (w.@arch-g under gē) is drawn to fit the arch:
            # it goes in whole, with its own advance, instead of dEgi's key clipped under it.
            drawn = variant(keys, index, name) if variant else legacy_glyph_name(name)
            if drawn != legacy_glyph_name(name):
                glyph.components.append(Component(drawn, Transform(dx=x)))
                x += ufo[drawn].width
                continue
            previous = legacy.glyph_name(keys[index - 1])
            reach = origins[index - 1] + legacy.advance(previous) - x
            clipped = _clipped(ufo, legacy, name, previous, legacy.advance(previous) - reach, reach, stem)
            glyph.components.append(Component(clipped, Transform(dx=x)))
            x += legacy.advance(name)
            continue
        chosen = variant(keys, index, name) if variant else legacy_glyph_name(name)
        glyph.components.append(Component(chosen, Transform(dx=x)))
        # A redrawn key keeps the advance it was drawn with (Urga's w for an arch family).
        x += ufo[chosen].width if chosen != legacy_glyph_name(name) else legacy.advance(name)
    for mark in marks:
        base = _mark_glyph(ufo, legacy, mark)
        dx = mark.dx
        if mark.on is not None:
            dx += origins[mark.on] + legacy.tip(legacy.glyph_name(keys[mark.on])) - legacy.tip(legacy.glyph_name(mark.key))
        glyph.components.append(Component(base, Transform(dx=dx, dy=mark.dy)))
    glyph.width = x


SPECK = 8  # font units


def _clipped(
    ufo: Font,
    legacy: LegacyFont,
    name: str,
    previous: str,
    offset: float,
    reach: float,
    stem: tuple[float, float],
    source: str | None = None,
) -> str:
    """A key moved back into the key before it, without the stem it pokes past that key's bowl.

    Up to the previous key's end its own stub carries the stem, so where the moved key's
    stem leaves the previous key's ink it is cutting across a counter or a curve."""

    source = source or legacy_glyph_name(name)
    clipped = f"{source}.under_{previous}_{round(reach)}"
    if clipped in ufo:
        return clipped

    def outline(glyph_name: str, dx: float = 0) -> Outline:
        path = Outline()
        ufo[glyph_name].draw(TransformPen(path.getPen(), (1, 0, 0, 1, dx, 0)))
        path.simplify()
        return path

    def box(x0: float, y0: float, x1: float, y1: float) -> Outline:
        path = Outline()
        pen = path.getPen()
        pen.moveTo((x0, y0))
        pen.lineTo((x0, y1))
        pen.lineTo((x1, y1))
        pen.lineTo((x1, y0))
        pen.closePath()
        return path

    # Line by line along the stem, only up to where the previous key's ink reaches on that
    # line: past it the moved key is the stem itself, which some keys leave to the next one.
    before = outline(legacy_glyph_name(previous), -offset)
    left = -legacy.units_per_em
    behind = Outline()
    step = 4
    for y in range(round(stem[0]), round(stem[1]), step):
        ink = op(box(left, y, reach, y + step), before, PathOp.INTERSECTION)
        if ink.bounds:
            behind = op(behind, box(left, y, ink.bounds[2], y + step), PathOp.UNION)
    uncovered = op(behind, before, PathOp.DIFFERENCE)
    result = op(outline(source), uncovered, PathOp.DIFFERENCE)
    # The line-by-line steps can leave a speck of a few units where two curves cross.
    kept = Outline()
    for contour, bounds in zip(result.contours, _contour_bounds(result)):
        if bounds[2] - bounds[0] > SPECK or bounds[3] - bounds[1] > SPECK:
            contour.draw(kept.getPen())
    result = kept
    glyph = ufo.newGlyph(clipped)
    glyph.width = legacy.advance(name)
    # pathops winds contours the PostScript way; overlapping the previous key's TrueType
    # contours the other way round would cancel out to a hole.
    result.draw(ReverseContourPen(glyph.getPen()))
    return clipped


def _dropped(ufo: Font, legacy: LegacyFont, name: str, teeth: int, stem: tuple[float, float]) -> str:
    """The key without its first *teeth* teeth, and the stem that leads into them."""

    dropped = f"{legacy_glyph_name(name)}.drop{teeth}"
    if dropped in ufo:
        return dropped
    bottom, _ = stem
    whole = Outline()
    ufo[legacy_glyph_name(name)].draw(whole.getPen())
    whole.simplify()
    far = legacy.units_per_em * 4
    below = op(whole, _box(-far, -far, far, bottom - 1), PathOp.INTERSECTION)
    found = sorted(_contour_bounds(below), key=lambda bounds: bounds[0])
    if len(found) <= teeth:
        raise ValueError(f"{name} has {len(found)} teeth below its stem, cannot drop {teeth}")
    cut = found[teeth - 1][2]
    kept = op(whole, _box(cut, -far, far, far), PathOp.INTERSECTION)
    glyph = ufo.newGlyph(dropped)
    glyph.width = legacy.advance(name)
    kept.draw(ReverseContourPen(glyph.getPen()))
    return dropped


def _box(x0: float, y0: float, x1: float, y1: float) -> Outline:
    path = Outline()
    pen = path.getPen()
    pen.moveTo((x0, y0))
    pen.lineTo((x0, y1))
    pen.lineTo((x1, y1))
    pen.lineTo((x1, y0))
    pen.closePath()
    return path


def _contour_bounds(path: Outline) -> list[tuple[float, float, float, float]]:
    found = []
    for contour in path.contours:
        part = Outline()
        contour.draw(part.getPen())
        found.append(part.bounds)
    return found


def _stem_to(ufo: Font, legacy: LegacyFont, name: str, length: float) -> str:
    """The stem piece cut to *length*: it is a plain bar, so pulling its end points in is the cut."""

    cut = f"{legacy_glyph_name(name)}.to_{round(length)}"
    if cut not in ufo:
        glyph = ufo.newGlyph(cut)
        pen = glyph.getPen()
        for contour in legacy.contours(name):
            for operator, arguments in contour:
                getattr(pen, operator)(*((min(point[0], length), point[1]) if point is not None else None for point in arguments))
        glyph.width = length
    return cut


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


def _trimmed(
    ufo: Font, legacy: LegacyFont, name: str, stem: tuple[float, float], start: bool, end: bool
) -> tuple[str, float]:
    """The key with its stem cut where its body begins or ends: what hangs below or rises above."""

    bottom, top = stem
    contours = legacy.contours(name)
    points = [point for contour in contours for _, arguments in contour for point in arguments if point is not None]
    body = [x for x, y in points if y < bottom - 1 or y > top + 1]
    # A tooth can leave the stem before its lowest point: Ulaanbaatar's i leans back, so its
    # leading edge starts on the stem at 55 while its body below starts at 163. Cutting at
    # 163 sliced the tooth flat, so the start cut also stops where the body leaves the stem.
    on_stem = lambda point: bottom - 1 <= point[1] <= top + 1
    leaving = [
        point[0]
        for contour in contours
        for ring in [[point for _, arguments in contour for point in arguments if point is not None]]
        for index, point in enumerate(ring)
        if on_stem(point) and not (on_stem(ring[index - 1]) and on_stem(ring[(index + 1) % len(ring)]))
    ]
    advance = legacy.advance(name)
    first = min(body + leaving) if start and body else 0
    last = max(body) if end and body else advance
    # An end cut keeps the bare `.trim`: goldens accepted as fixes pin glyph names.
    trimmed = f"{legacy_glyph_name(name)}.trim" + {(True, False): "_start", (True, True): "_both"}.get((start, end), "")
    if trimmed not in ufo:
        glyph = ufo.newGlyph(trimmed)
        pen = glyph.getPen()

        # The stem beside the body is a plain bar, so pulling its end points in is the cut.
        def cut(point: tuple[float, float]) -> tuple[float, float]:
            x, y = point
            if bottom - 1 <= y <= top + 1:
                x = min(max(x, first), last)
            return x - first, y

        for contour in contours:
            for operator, arguments in contour:
                getattr(pen, operator)(*(cut(point) if point is not None else None for point in arguments))
        glyph.width = last - first
    return trimmed, last - first


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


def _before_drawing(drawings: Font | None, mapping: Mapping, piece: str, following: str):
    """A "before" rule drawn by hand: under its own name, or under its group's."""

    if drawings is None:
        return None
    before = mapping.get(piece).before
    names = [neighbours.before_rule_glyph(piece, following)]
    if following not in before:
        names += [
            neighbours.before_rule_glyph(piece, rule)
            for rule in before
            if rule.startswith("@") and following in mapping.groups.get(rule[1:], [])
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
