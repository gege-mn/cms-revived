"""The legacy-keyed companion: dEgi's 1998 keyboard, with the rework's joins as ligatures.

Old documents were typed key by key in CMs. This font keeps every key where 1998 put it,
drawing exactly what dEgi drew, and adds substitutions that turn the key sequences a CMs
typist used into what the Unicode build draws for the same word. With features off, it is
dEgi's font.

The substitutions are learned, never listed by hand. Every word of the goldens and the
corpora is shaped with the Unicode build; each glyph it produces is read back as the keys a
typist would have used for it (the mapping's keys, with the rules that model the typist's
key choice); where the glyph draws something other than those keys, the keys become a
substitution, with as much context of the keys around them as it takes to tell that case
from the others.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from pathlib import Path

import uharfbuzz as hb
from fontTools.ttLib import TTFont
from mongfontbuilder import GlyphDescriptor

from .config import CUTS
from .mapping import Mapping
from .targets import atoms_of

# Keys that are not strokes of a word: a word starts or ends next to them.
NON_LETTERS = set(" ,.=/?:\"<>0123456789")


@dataclass(frozen=True)
class Typed:
    glyph: str  # what the Unicode build shapes
    keys: str  # what a CMs typist typed for it


@cache
def _typist_rules(cut_id: str) -> dict[tuple[str, str], str]:
    """(piece, previous piece) -> keys, for the rules that say which key a typist picked.

    Rules typed with other keys than the piece's own, without a shift or marks, are the
    typist's choice (e after a crown, E after an arch). Rules that move keys or lift marks
    onto them (n's dot on the tooth after an arch), the "before" rules
    (the small first arch: CMs typed k k, the rework draws h k) and drawn joins are the
    rework's fixes: the typist typed the piece's own keys.
    """

    mapping = Mapping.load()
    found = {}
    for entry in mapping.all():
        own = entry.keys_for(cut_id)
        for previous, rule in mapping.rules(entry).items():
            if rule.keys != own and not (rule.shift or rule.shifts.get(cut_id) or rule.marks):
                found[entry.name, previous] = rule.keys
    return found


@cache
def _mapping() -> Mapping:
    return Mapping.load()


def _written_keys(cut_id: str, base: str) -> str | None:
    """Keys mapped for a whole written form (a ligature, a letter's own form), if any."""

    mapping = _mapping()
    descriptor = GlyphDescriptor.parse(base)
    for name in (base, f"{''.join(descriptor.units)}.{descriptor.position}"):
        if name in mapping.entries and mapping.entries[name].keys_for(cut_id):
            if name == base or len(descriptor.units) > 1:
                return mapping.entries[name].keys_for(cut_id)
    return None


@cache
def _unicode_font(path: Path, revision: int) -> tuple[hb.Font, TTFont]:
    return hb.Font(hb.Face(hb.Blob.from_file_path(path))), TTFont(path)


def _is_fix(entry) -> bool:
    return bool(entry.marks or entry.drop or entry.shift or entry.shifts)


@cache
def _golden_typings(cut_id: str) -> dict[str, str]:
    """Written forms the rework draws on purpose otherwise than CMs typed them (angq-a's q,
    typed ek( and drawn as ekE( with a tooth dropped): the goldens say what was typed.

    A golden the mapping's keys do not reproduce, where one glyph is such a fix, gives that
    glyph the keys that make the word come out as the golden was typed, allowing one other
    key to differ (angq-a was typed with the F crown, not the usual f).
    """

    from . import goldens

    mapping = _mapping()
    found: dict[str, str] = {}
    for golden in goldens.load():
        items = typed(cut_id, golden.text, use_goldens=False)
        if "".join(item.keys for item in items) == golden.keys:
            continue
        best = None
        for index, item in enumerate(items):
            descriptor = _descriptor(item.glyph)
            if descriptor is None:
                continue
            written = f"{''.join(descriptor.units)}.{descriptor.position}"
            if written not in mapping.entries or not _is_fix(mapping.entries[written]):
                continue
            prefix = "".join(other.keys for other in items[:index])
            suffix = "".join(other.keys for other in items[index + 1 :])
            for start in range(len(golden.keys) + 1):
                for end in range(start + 1, len(golden.keys) + 1):
                    middle = golden.keys[start:end]
                    distance = _distance(prefix + middle + suffix, golden.keys)
                    if distance <= 1 and (best is None or distance < best[0]):
                        best = (distance, written, middle)
        if best is not None:
            found.setdefault(best[1], best[2])
    return found


def _distance(a: str, b: str) -> int:
    row = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        previous, row[0] = row[0], i
        for j, y in enumerate(b, 1):
            previous, row[j] = row[j], min(row[j] + 1, row[j - 1] + 1, previous + (x != y))
    return row[-1]


def _descriptor(name: str):
    try:
        descriptor = GlyphDescriptor.parse(name.split("._")[0])
    except (AssertionError, ValueError, KeyError):
        return None
    return descriptor if descriptor.codePoints and descriptor.units else None


def typed(cut_id: str, text: str, font_path: Path | None = None, use_goldens: bool = True) -> list[Typed]:
    """The Unicode build's glyphs for *text*, each with the keys CMs typed for it."""

    path = font_path or CUTS[cut_id].output_path
    font, ttf = _unicode_font(path, path.stat().st_mtime_ns)
    buffer = hb.Buffer()
    buffer.add_str(text)
    buffer.guess_segment_properties()
    hb.shape(font, buffer)
    rules = _typist_rules(cut_id)
    mapping = _mapping()
    found: list[Typed] = []
    previous_atom: str | None = None
    for info, position in zip(buffer.glyph_infos, buffer.glyph_positions):
        name = font.glyph_to_string(info.codepoint)
        base = name.split("._")[0]
        try:
            descriptor = GlyphDescriptor.parse(base)
            letter = bool(descriptor.codePoints) and bool(descriptor.units)
        except (AssertionError, ValueError, KeyError):
            letter = False
        if not letter:
            if name.startswith("fvs") or ttf["hmtx"][name][0] == 0:
                found.append(Typed(name, ""))
                continue
            entry = mapping.entries.get(f"U+{ord(text[info.cluster]):04X}")
            found.append(Typed(name, entry.keys_for(cut_id) if entry and entry.keys_for(cut_id) else " "))
            previous_atom = None
            continue
        atoms = atoms_of(descriptor.units, descriptor.position)
        written = f"{''.join(descriptor.units)}.{descriptor.position}"
        whole = (_golden_typings(cut_id).get(written) if use_goldens else None) or _written_keys(cut_id, base)
        if whole is not None:
            keys = whole
        else:
            keys = ""
            for index, atom in enumerate(atoms):
                before = atoms[index - 1] if index else previous_atom
                keys += rules.get((atom, before), mapping.get(atom).keys_for(cut_id) or "") if before else (mapping.get(atom).keys_for(cut_id) or "")
        found.append(Typed(name, keys))
        previous_atom = atoms[-1]
    return found


def typed_keys(cut_id: str, text: str) -> str:
    return "".join(item.keys for item in typed(cut_id, text))


Contour = tuple


def _contours(ttf: TTFont, name: str, dx: float = 0) -> list[Contour]:
    from fontTools.pens.recordingPen import DecomposingRecordingPen

    glyph_set = ttf.getGlyphSet()
    pen = DecomposingRecordingPen(glyph_set)
    glyph_set[name].draw(pen)
    found, current = [], []
    for operator, arguments in pen.value:
        current += [(round(x + dx), round(y)) for x, y in (point for point in arguments if point is not None)]
        if operator in ("closePath", "endPath"):
            found.append(tuple(current))
            current = []
    return found


def drawing(ttf: TTFont, names: list[str]) -> tuple[tuple[Contour, ...], int]:
    """What a run of glyphs draws, set one after another: its contours and its advance."""

    x, found = 0, []
    for name in names:
        found += _contours(ttf, name, x)
        x += ttf["hmtx"][name][0]
    return tuple(sorted(found)), x


# A key's place in its run of strokes, as the font's first lookups tag it: alone, first,
# inside, last. Words start and end next to a space or a punctuation key.
ALONE, FIRST, INSIDE, LAST = "s", "i", "m", "f"
CONTEXT = 4  # keys of context a rule may look at on each side
OUTSIDE = "?"  # beyond the word: unknown, never part of a rule
MAJORITY = 0.8  # share of the cases in a context a rule must be right for


def units(keys: str) -> list[str]:
    """Each key with its place: 'k.m' is k inside a word; punctuation and spaces stand alone."""

    found = []
    for index, key in enumerate(keys):
        if key in NON_LETTERS:
            found.append(key)
            continue
        before = index > 0 and keys[index - 1] not in NON_LETTERS
        after = index + 1 < len(keys) and keys[index + 1] not in NON_LETTERS
        found.append(f"{key}.{ {(False, False): ALONE, (False, True): FIRST, (True, True): INSIDE, (True, False): LAST}[before, after]}")
    return found


@dataclass
class Token:
    """One word as typed: its key units, and the Unicode build's glyphs over them."""

    word: str
    units: list[str]
    spans: list[tuple[int, int, str | None]]  # key range, and the glyph to draw there (None: the keys as they are)
    weight: int


@dataclass(frozen=True)
class Rule:
    span: tuple[str, ...]
    left: tuple[str, ...]
    right: tuple[str, ...]
    target: str | None  # None keeps the keys: an exception to the span's usual glyph


@dataclass
class Learned:
    rules: dict[tuple[str, ...], list[Rule]]  # per span, in the order they are tried
    unresolved: list[tuple[Token, int]]  # words whose keys alone cannot say which glyph (token, span start)


class Drawings:
    """Whether each Unicode glyph draws the same as the keys typed for it in dEgi's font."""

    def __init__(self, cut_id: str) -> None:
        from .legacy import LegacyFont

        self.unicode = TTFont(CUTS[cut_id].output_path)
        self.legacy = LegacyFont.open(cut_id)
        self.keyed = self.legacy.keyed_glyphs()
        self._unicode: dict[str, tuple] = {}
        self._keys: dict[str, tuple] = {}
        self._canonical: dict[tuple, str] = {}

    def canonical(self, name: str) -> str:
        """One glyph for each drawing: q and g share theirs in feminine words, and the keys
        cannot tell them apart, nor need to."""

        return self._canonical.setdefault(self.of_glyph(name), name)

    def of_glyph(self, name: str) -> tuple:
        if name not in self._unicode:
            self._unicode[name] = drawing(self.unicode, [name])
        return self._unicode[name]

    def of_keys(self, keys: str) -> tuple:
        if keys not in self._keys:
            self._keys[keys] = drawing(self.legacy.ttf, [self.keyed[key] for key in keys])
        return self._keys[keys]

    def fixed(self, item: Typed) -> bool:
        if not item.keys or any(key in NON_LETTERS for key in item.keys):
            return False  # spaces, gaps and punctuation keep their 1998 widths
        return self.of_glyph(item.glyph) != self.of_keys(item.keys)


def tokens(cut_id: str, words: dict[str, int], drawings: Drawings) -> list[Token]:
    found = []
    for word, weight in words.items():
        items = typed(cut_id, word)
        keys = "".join(item.keys for item in items)
        if not keys or any(key not in drawings.keyed for key in keys):
            continue
        spans, start = [], 0
        for item in items:
            if item.keys:
                spans.append((start, start + len(item.keys), drawings.canonical(item.glyph) if drawings.fixed(item) else None))
            start += len(item.keys)
        found.append(Token(word, units(keys), spans, weight))
    return found


def learn(found: list[Token]) -> Learned:
    """For every key span some glyph is typed with, the rules that pick its glyph.

    Every place the span's keys occur is a case, labelled with the glyph the Unicode build
    draws there, or None where the keys stay as they are (another glyph's keys, or a glyph
    that draws them unchanged). The span's usual glyph is the default; each case that
    differs gets the shortest context around it that only cases of its own glyph share.
    """

    # Sorted, so a rebuild numbers its rules and glyphs the same way (sets come out in hash order).
    spans = sorted({tuple(token.units[a:b]) for token in found for a, b, target in token.spans if target})
    by_first: dict[str, list[tuple[str, ...]]] = {}
    for span in spans:
        by_first.setdefault(span[0], []).append(span)

    # span -> (left context, right context) -> {label: weight}, with the cases behind each
    cases: dict[tuple[str, ...], dict[tuple, dict]] = {span: {} for span in spans}
    where: dict[tuple, list[tuple[Token, int]]] = {}
    for token in found:
        exact = {(a, b): target for a, b, target in token.spans}
        # Where a longer span's glyph starts, its lookup runs first and takes the keys.
        longer = {a: b for a, b, target in token.spans if target}
        padded = [OUTSIDE] * (CONTEXT - 1) + [" "] + token.units + [" "] + [OUTSIDE] * (CONTEXT - 1)
        for start, unit in enumerate(token.units):
            for span in by_first.get(unit, ()):
                end = start + len(span)
                if tuple(token.units[start:end]) != span:
                    continue
                if longer.get(start, end) > end:
                    continue
                label = exact.get((start, end))
                left = tuple(padded[start : start + CONTEXT])
                right = tuple(padded[end + CONTEXT : end + 2 * CONTEXT])
                labels = cases[span].setdefault((left, right), {})
                labels[label] = labels.get(label, 0) + token.weight
                where.setdefault((span, left, right, label), []).append((token, start))

    widths = sorted(((l, r) for l in range(CONTEXT + 1) for r in range(CONTEXT + 1)), key=lambda lr: (lr[0] + lr[1], lr[1]))
    rules: dict[tuple[str, ...], list[Rule]] = {}
    unresolved: list[tuple[Token, int]] = []
    for span, contexts in cases.items():
        totals: dict = {}
        for labels in contexts.values():
            for label, weight in labels.items():
                totals[label] = totals.get(label, 0) + weight
        default = max(totals, key=lambda label: (totals[label], label is None))
        windows: dict[tuple[int, int], dict[tuple, dict]] = {}
        for l, r in widths:
            table = windows.setdefault((l, r), {})
            for (left, right), labels in contexts.items():
                key = (left[CONTEXT - l :], right[:r])
                merged = table.setdefault(key, {})
                for label, weight in labels.items():
                    merged[label] = merged.get(label, 0) + weight
        chosen: dict[Rule, None] = {}

        def window_for(left: tuple, right: tuple, label, wider_than: int = -1) -> Rule | None:
            """The shortest context in which *label* is what nearly every case wants."""

            for l, r in widths:
                if l + r <= wider_than:
                    continue
                key = (left[CONTEXT - l :], right[:r])
                if OUTSIDE in key[0] or OUTSIDE in key[1]:
                    continue
                labels = windows[l, r][key]
                if labels.get(label, 0) >= MAJORITY * sum(labels.values()):
                    return Rule(span, key[0], key[1], label)
            return None

        def covering(left: tuple, right: tuple) -> Rule | None:
            for rule in sorted(chosen, key=lambda rule: -(len(rule.left) + len(rule.right))):
                if left[CONTEXT - len(rule.left) :] == rule.left and right[: len(rule.right)] == rule.right:
                    return rule
            return None

        # Cases unlike the default get a rule; then cases a rule took from the default, or from
        # another label, get a more specific one back. Typos in the corpora (čieγγ-a typed like
        # čingγ-a) lose to the common word.
        for _ in range(10):
            changed = False
            for (left, right), labels in contexts.items():
                for label in sorted(labels, key=lambda label: -labels[label]):
                    current = covering(left, right)
                    wants = current.target if current else default
                    if wants == label or labels[label] < MAJORITY * sum(labels.values()):
                        continue
                    rule = window_for(left, right, label, len(current.left) + len(current.right) if current else -1)
                    if rule is not None and rule not in chosen:
                        chosen[rule] = None
                        changed = True
            if not changed:
                break
        for (left, right), labels in contexts.items():
            current = covering(left, right)
            wants = current.target if current else default
            for label in labels:
                if label != wants:
                    unresolved += where[span, left, right, label]
        ordered = sorted(chosen, key=lambda rule: -(len(rule.left) + len(rule.right)))
        if default is not None:
            ordered.append(Rule(span, (), (), default))
        rules[span] = ordered
    return Learned(rules, unresolved)


GOLDEN_WEIGHT = 1000  # a golden counts like a word seen this often: the owner confirmed it


@dataclass
class CompanionResult:
    cut_id: str
    path: Path
    rules: int
    glyphs: int
    unresolved: list[tuple[Token, int]]


def training_words(cut_id: str) -> dict[str, int]:
    from . import goldens
    from .coverage import CORPORA, corpus_words

    if not any(CORPORA.glob("*.md")):
        raise SystemExit(f"the companion learns from the corpora, and {CORPORA} has none (README: Corpora)")
    words = dict(corpus_words())
    for golden in goldens.load():
        words[golden.text] = words.get(golden.text, 0) + GOLDEN_WEIGHT
    return words


def build_companion(cut_id: str) -> CompanionResult:
    """dEgi's 1998 font as he made it, plus the joins of the Unicode build as substitutions."""

    from .legacy import LegacyFont

    cut = CUTS[cut_id]
    drawings = Drawings(cut_id)
    found = tokens(cut_id, training_words(cut_id), drawings)
    learned = learn(found)

    # His own file is the base: his glyphs, metrics, cmap and hinting stay byte for byte.
    ttf = TTFont(cut.legacy_path)
    legacy = LegacyFont.open(cut_id)
    keyed = legacy.keyed_glyphs()
    order = list(ttf.getGlyphOrder())
    glyf, hmtx = ttf["glyf"], ttf["hmtx"]
    unicode = drawings.unicode

    def unit_glyph(unit: str) -> str:
        key, _, place = unit.partition(".")
        name = keyed[key or "."]
        return name if place in ("", ALONE) else f"{name}.{place}"

    def add(name: str, glyph, advance: int) -> None:
        order.append(name)
        glyf.glyphs[name] = glyph
        hmtx.metrics[name] = (advance, 0)

    def component_glyph(base: str):
        from fontTools.ttLib.tables._g_l_y_f import Glyph, GlyphComponent

        glyph = Glyph()
        component = GlyphComponent()
        component.glyphName, component.x, component.y, component.flags = base, 0, 0, 0x4  # ROUND_XY_TO_GRID
        glyph.components = [component]
        glyph.numberOfContours = -1
        return glyph

    letters = [name for key, name in keyed.items() if key not in NON_LETTERS]
    ttf.setGlyphOrder(order)
    for place in (FIRST, INSIDE, LAST):
        for name in letters:
            add(f"{name}.{place}", component_glyph(name), legacy.advance(name))

    # The Unicode build's glyphs, with the 1998 keys they are made of pointing at his.
    renamed: dict[str, str] = {}
    for key, name in keyed.items():
        source = f"cms.{name}"
        if source in unicode.getGlyphOrder() and drawing(unicode, [source]) == drawing(legacy.ttf, [name]):
            renamed[source] = name

    def copy(name: str) -> str:
        new = renamed.get(name, name)
        if new in glyf.glyphs:
            return new
        import copy as copying

        glyph = copying.deepcopy(unicode["glyf"][name])
        if glyph.isComposite():
            for component in glyph.components:
                component.glyphName = copy(component.glyphName)
        add(new, glyph, unicode["hmtx"][name][0])
        return new

    markers: dict[tuple[tuple[str, ...], str], str] = {}
    targets: dict[str, str] = {}
    for span, rules in learned.rules.items():
        for rule in rules:
            if rule.target is None or (span, rule.target) in markers:
                continue
            if rule.target not in targets:
                targets[rule.target] = copy(rule.target)
            marker = f"{unit_glyph(span[0])}.to{len(markers)}"
            markers[span, rule.target] = marker
            add(marker, component_glyph(unit_glyph(span[0])), legacy.advance(keyed[span[0].partition('.')[0]]))

    ttf.setGlyphOrder(order)
    glyf.glyphOrder = order
    for name in order:
        glyph = glyf[name]
        glyph.recalcBounds(glyf)
        if name in hmtx.metrics:
            hmtx.metrics[name] = (hmtx.metrics[name][0], getattr(glyph, "xMin", 0))

    _write_features(ttf, learned, letters, markers, targets, unit_glyph)
    _set_companion_names(ttf, cut, unicode["OS/2"].fsType)
    for table in ("hdmx", "LTSH", "VDMX", "kern"):
        if table in ttf:
            del ttf[table]
    cut.companion_path.parent.mkdir(parents=True, exist_ok=True)
    ttf.save(cut.companion_path)
    return CompanionResult(cut_id, cut.companion_path, sum(len(rules) for rules in learned.rules.values()), len(order), learned.unresolved)


def _write_features(ttf: TTFont, learned: Learned, letters: list[str], markers: dict, targets: dict, unit_glyph) -> None:
    from fontTools.feaLib.builder import addOpenTypeFeaturesFromString

    by_first: dict[str, list[str]] = {}
    for (span, _), marker in markers.items():
        by_first.setdefault(unit_glyph(span[0]), []).append(marker)

    def context(unit: str) -> str:
        name = unit_glyph(unit)
        return f"[{' '.join([name, *by_first.get(name, [])])}]"

    places = {place: [f"{name}.{place}" for name in letters] for place in (FIRST, INSIDE, LAST)}
    every = " ".join([*letters, *places[FIRST], *places[INSIDE], *places[LAST]])
    lines = [
        "languagesystem DFLT dflt;",
        "languagesystem latn dflt;",
        "",
        "# Each key's place in its word: alone (the key itself), first, inside, last.",
        "lookup cmsl_first {",
        f"    sub [{' '.join(letters)}]' [{' '.join(letters)}] by [{' '.join(places[FIRST])}];",
        "} cmsl_first;",
        "lookup cmsl_place {",
        f"    sub [{every}] [{' '.join(letters)}]' by [{' '.join(places[LAST])}];",
        f"    sub [{every}] [{' '.join(places[FIRST])}]' by [{' '.join(places[INSIDE])}];",
        "} cmsl_place;",
        "",
    ]
    for (span, target), marker in markers.items():
        lines.append(f"lookup cmsl_mark_{marker.replace('.', '_')} {{ sub {unit_glyph(span[0])} by {marker}; }} cmsl_mark_{marker.replace('.', '_')};")
    lines.append("")
    stage = ["cmsl_first", "cmsl_place"]
    # Longer spans first: where one glyph is typed with keys that start another, it takes them.
    for index, (span, rules) in enumerate(sorted(learned.rules.items(), key=lambda item: (-len(item[0]), item[0]))):
        name = f"cmsl_span_{index}"
        lines.append(f"lookup {name} {{  # {' '.join(span)}")
        first, rest = unit_glyph(span[0]), " ".join(unit_glyph(unit) for unit in span[1:])
        for rule in rules:
            left = " ".join(context(unit) for unit in rule.left)
            right = " ".join(context(unit) for unit in rule.right)
            if rule.target is None:
                lines.append(f"    ignore sub {left} {first}' {rest} {right};".replace("  ", " "))
            else:
                mark = f"cmsl_mark_{markers[span, rule.target].replace('.', '_')}"
                lines.append(f"    sub {left} {first}' lookup {mark} {rest} {right};".replace("  ", " "))
        lines.append(f"}} {name};")
        stage.append(name)
    singles = [(marker, targets[target]) for (span, target), marker in markers.items() if len(span) == 1]
    joins = [(span, marker, targets[target]) for (span, target), marker in markers.items() if len(span) > 1]
    if singles:
        lines += ["lookup cmsl_single {", *(f"    sub {marker} by {target};" for marker, target in singles), "} cmsl_single;"]
        stage.append("cmsl_single")
    if joins:
        lines += [
            "lookup cmsl_join {",
            *(f"    sub {marker} {' '.join(unit_glyph(unit) for unit in span[1:])} by {target};" for span, marker, target in joins),
            "} cmsl_join;",
        ]
        stage.append("cmsl_join")
    # liga and calt only, so "ligatures off" in any app brings back the 1998 drawing.
    for feature in ("liga", "calt"):
        lines += [f"feature {feature} {{", *(f"    lookup {name};" for name in stage), f"}} {feature};"]
    addOpenTypeFeaturesFromString(ttf, "\n".join(lines))


def build_companion_dp(cut_id: str) -> Path:
    """The companion for dEgi's dp cut, mirrored for letterpress: his dp file as the base,
    and every glyph the companion adds flipped as he flipped his, about the stem's axis.

    The rules are the companion's, unchanged: the keys and the glyph order are the same.
    """

    import copy

    from fontTools.pens.boundsPen import BoundsPen
    from fontTools.ttLib.tables.ttProgram import Program

    cut = CUTS[cut_id]
    companion = TTFont(cut.companion_path)
    ttf = TTFont(cut.legacy_dp_path)
    original = TTFont(cut.legacy_path)
    theirs = set(original.getGlyphOrder())
    if ttf.getGlyphOrder() != original.getGlyphOrder():
        raise SystemExit(f"{cut_id}: the dp cut's glyphs are not the regular cut's")

    def bounds(font: TTFont, name: str):
        pen = BoundsPen(font.getGlyphSet())
        font.getGlyphSet()[name].draw(pen)
        return pen.bounds

    # dEgi flipped y about the stem's middle: y -> axis - y (800 in all three cuts).
    _, regular_bottom, _, regular_top = bounds(original, "hyphen")
    _, dp_bottom, _, _ = bounds(ttf, "hyphen")
    axis = round(dp_bottom + regular_top)
    if axis != round(regular_bottom + bounds(ttf, "hyphen")[3]):
        raise SystemExit(f"{cut_id}: the dp stem is not the regular one flipped")

    order = companion.getGlyphOrder()
    glyf, hmtx = ttf["glyf"], ttf["hmtx"]
    ttf.setGlyphOrder(order)
    glyf.glyphOrder = order
    for name in order:
        if name in theirs:
            continue
        glyph = copy.deepcopy(companion["glyf"][name])
        if glyph.isComposite():
            # Each part is flipped already (dEgi's dp glyph, or one flipped here): only its offset turns.
            for component in glyph.components:
                component.y = -component.y
        elif glyph.numberOfContours > 0:
            coordinates = glyph.getCoordinates(companion["glyf"])[0]
            ends = list(glyph.endPtsOfContours)
            flags = list(glyph.flags)
            start, points, new_flags = 0, [], []
            for end in ends:
                contour = list(range(start, end + 1))
                # Flipping turns a contour the other way round: read it backwards to keep TrueType's direction.
                contour = contour[:1] + contour[1:][::-1]
                points += [(coordinates[index][0], axis - coordinates[index][1]) for index in contour]
                new_flags += [flags[index] for index in contour]
                start = end + 1
            glyph.coordinates = type(glyph.coordinates)(points)
            glyph.flags = bytearray(new_flags)
            glyph.program = Program()
            glyph.program.fromBytecode(b"")
        glyf.glyphs[name] = glyph
        hmtx.metrics[name] = companion["hmtx"][name]
    for name in order:
        if name not in theirs:
            glyf[name].recalcBounds(glyf)
            hmtx.metrics[name] = (hmtx.metrics[name][0], getattr(glyf[name], "xMin", 0))
    ttf["GSUB"] = copy.deepcopy(companion["GSUB"])
    _set_companion_names(ttf, cut, companion["OS/2"].fsType, cut.companion_dp_family)
    for table in ("hdmx", "LTSH", "VDMX", "kern"):
        if table in ttf:
            del ttf[table]
    ttf.save(cut.companion_dp_path)
    return cut.companion_dp_path


def _set_companion_names(ttf: TTFont, cut, fs_type: int, family: str | None = None) -> None:
    from . import config

    major, minor = config.VERSION
    family = family or cut.companion_family
    postscript = family.replace(" ", "") + "-Regular"
    version = f"Version {major}.{minor:03d}; {config.COMPANION_VERSION_NOTE}"
    names = {
        0: config.COMPANION_COPYRIGHT,
        1: family,
        2: "Regular",
        3: f"{major}.{minor:03d};{config.VENDOR_ID};{postscript}",
        4: f"{family} Regular",
        5: version,
        6: postscript,
        8: config.MANUFACTURER,
        9: config.COMPANION_DESIGNER,
        10: config.COMPANION_DESCRIPTION,
        13: config.LICENSE,
    }
    if config.VENDOR_URL:
        names[11] = config.VENDOR_URL
    table = ttf["name"]
    table.names = []
    for name_id, text in names.items():
        table.setName(text, name_id, 3, 1, 0x409)
        if name_id in (1, 2, 4, 6):
            table.setName(text, name_id, 1, 0, 0)
    ttf["head"].fontRevision = major + minor / 1000
    ttf["OS/2"].achVendID = config.VENDOR_ID
    ttf["OS/2"].fsType = fs_type  # as the Unicode build, not 1998's restricted embedding
    ttf["post"].formatType = 2.0


@dataclass
class Evaluation:
    passed: int  # weight of the words drawn exactly as the Unicode build draws them
    total: int
    failures: list[tuple[Token, str]]  # the word and what the companion drew instead


def evaluate(cut_id: str, found: list[Token], drawings: Drawings, path: Path | None = None) -> Evaluation:
    """Shape each word's keys with the companion and hold every glyph's stretch of keys to
    what the Unicode build draws for it."""

    path = path or CUTS[cut_id].companion_path
    font = hb.Font(hb.Face(hb.Blob.from_file_path(path)))
    ttf = TTFont(path)
    cache_: dict[str, list] = {}
    result = Evaluation(0, 0, [])
    for token in found:
        keys = "".join(unit.partition(".")[0] or "." for unit in token.units)
        buffer = hb.Buffer()
        buffer.add_str(keys)
        buffer.guess_segment_properties()
        hb.shape(font, buffer)
        pen, placed = 0, []
        for info, position in zip(buffer.glyph_infos, buffer.glyph_positions):
            placed.append((info.cluster, font.glyph_to_string(info.codepoint), pen + position.x_offset, position.x_advance))
            pen += position.x_advance
        ok = True
        items = [item for item in typed(cut_id, token.word) if item.keys]
        for (a, b, _), item in zip(token.spans, items):
            if any(key in NON_LETTERS for key in item.keys):
                continue
            segment = [glyph for glyph in placed if a <= glyph[0] < b]
            if not segment:
                ok = False
                break
            x0 = segment[0][2]
            contours = []
            for _, name, x, _ in segment:
                if name not in cache_:
                    cache_[name] = _contours(ttf, name)
                contours += [tuple((px + x - x0, py) for px, py in contour) for contour in cache_[name]]
            if (tuple(sorted(contours)), sum(glyph[3] for glyph in segment)) != drawings.of_glyph(item.glyph):
                ok = False
                break
        result.total += token.weight
        if ok:
            result.passed += token.weight
        else:
            result.failures.append((token, " ".join(name for _, name, _, _ in placed)))
    return result


def same_as_1998(cut_id: str, path: Path | None = None, dp: bool = False) -> list[str]:
    """Keys that do not draw exactly as in dEgi's font (or his dp cut) with features off:
    should be none."""

    from .legacy import LegacyFont

    cut = CUTS[cut_id]
    path = path or (cut.companion_dp_path if dp else cut.companion_path)
    ttf, original = TTFont(path), TTFont(cut.legacy_dp_path if dp else cut.legacy_path)
    font = hb.Font(hb.Face(hb.Blob.from_file_path(path)))
    problems = []
    for key, name in LegacyFont.open(cut_id).keyed_glyphs().items():
        buffer = hb.Buffer()
        buffer.add_str(key)
        buffer.guess_segment_properties()
        hb.shape(font, buffer, {"liga": False, "calt": False})
        shaped = font.glyph_to_string(buffer.glyph_infos[0].codepoint)
        mine, theirs = ttf["glyf"][shaped], original["glyf"][name]
        if (
            shaped != name
            or mine.compile(ttf["glyf"]) != theirs.compile(original["glyf"])
            or ttf["hmtx"][shaped] != original["hmtx"][name]
        ):
            problems.append(key)
    for table in ("fpgm", "prep", "cvt "):
        if table in original and ttf[table].compile(ttf) != original[table].compile(original):
            problems.append(table)
    return problems


def check_goldens(cut_id: str, drawings: Drawings, path: Path | None = None) -> list[tuple[str, str]]:
    """Goldens whose typed keys the companion does not draw as the Unicode build: (latin, why)."""

    from . import goldens

    failed = []
    for golden in goldens.load():
        model = typed_keys(cut_id, golden.text)
        if model != golden.keys:
            failed.append((golden.latin, f"typed {golden.keys!r}; the companion knows it as {model!r}"))
            continue
        token = tokens(cut_id, {golden.text: 1}, drawings)
        if not token:
            failed.append((golden.latin, "keys not in the font"))
            continue
        if evaluate(cut_id, token, drawings, path).failures:
            failed.append((golden.latin, f"{golden.keys!r} draws otherwise than the Unicode build"))
    return failed
