"""Neighbour rules: a piece typed differently depending on the piece right before it.

The 1998 keyboard spaces strokes by key choice (`e` brings more stem before its tooth than
`E`), and a typist picks by what precedes, whichever letter it belongs to. A rule
`"A.medi" after "A.init" = "e"` is applied in two places:

- inside a written form, by drawing the form from its pieces with the rule's keys, so
  mongfontbuilder finds the form already drawn;
- between letters, by a contextual substitution run after mongfontbuilder's shaping, which
  swaps a glyph that starts with the piece for a copy drawn with the rule's keys.
"""

from __future__ import annotations

from fontTools.misc.transform import Transform
from mongfontbuilder import GlyphDescriptor
from ufoLib2 import Font
from ufoLib2.objects import Component

from .mapping import Mapping
from .targets import atoms_of, variants

Rule = tuple[str, str]  # (piece, the piece right before it)


def rule_glyph(piece: str, previous: str) -> str:
    return f"cmsr.{piece}.after.{previous}"


def rules(mapping: Mapping) -> dict[Rule, str]:
    return {(entry.name, previous): keys for entry in mapping.all() for previous, keys in mapping.rules(entry).items()}


def add_inner_forms(ufo: Font, found: dict[Rule, str]) -> None:
    """Draw every written form that has a rule inside it from its pieces, before composing."""

    for written in dict.fromkeys(variant.written for variant in variants()):
        name = "_" + written
        if name in ufo:
            continue
        units, position = GlyphDescriptor.parse(name).units, GlyphDescriptor.parse(name).position
        atoms = atoms_of(units, position)
        members = [
            rule_glyph(atom, atoms[index - 1]) if index and (atom, atoms[index - 1]) in found else "_" + atom
            for index, atom in enumerate(atoms)
        ]
        if members == ["_" + atom for atom in atoms] or not all(member in ufo for member in members):
            continue
        glyph = ufo.newGlyph(name)
        x = 0
        for member in members:
            glyph.components.append(Component(member, Transform(dx=x)))
            x += ufo[member].width
        glyph.width = x


def features(ufo: Font, found: dict[Rule, str]) -> str:
    """The substitutions between letters, as feature code to append to the composer's."""

    if not found:
        return ""
    output = {name: atoms for name in ufo.keys() if (atoms := _output_atoms(name))}
    flattened = {name: _flatten(ufo, name) for name in output}

    # First every alternate, so a rule's context can include what another rule produced.
    swaps: dict[Rule, dict[str, str]] = {}
    for piece, previous in sorted(found):
        replacement = rule_glyph(piece, previous)
        if replacement not in ufo:
            continue
        swaps[piece, previous] = {}
        for name, components in flattened.items():
            if components and components[0][0] == "_" + piece:
                # A `._` suffix is mongfontbuilder's own for a variant of a glyph: readers of
                # glyph names (its suites among them) skip it and still see the written form.
                alternate = f"{name}._after_{previous.replace('.', '_')}"
                _draw_alternate(ufo, alternate, ufo[name].width, components, replacement)
                swaps[piece, previous][name] = alternate
    alternates_of: dict[str, list[str]] = {}
    for table in swaps.values():
        for name, alternate in table.items():
            alternates_of.setdefault(name, []).append(alternate)

    blocks: list[str] = []
    lookups: list[str] = []
    for index, ((piece, previous), table) in enumerate(swaps.items()):
        ends = sorted(
            {name for name, atoms in output.items() if atoms[-1] == previous}
            | {alternate for name, atoms in output.items() if atoms[-1] == previous for alternate in alternates_of.get(name, [])}
        )
        if not table or not ends:
            continue
        single, chain = f"cmsr_swap_{index}", f"cmsr_after_{index}"
        blocks.append(
            f"lookup {single} {{\n"
            + "".join(f"    sub {name} by {alternate};\n" for name, alternate in sorted(table.items()))
            + f"}} {single};\n"
        )
        blocks.append(
            f"lookup {chain} {{\n    lookupflag IgnoreMarks;\n"
            f"    sub [{' '.join(ends)}] [{' '.join(sorted(table))}]' lookup {single};\n}} {chain};\n"
        )
        lookups.append(chain)
    if not lookups:
        return ""
    return "\n".join(blocks) + "\nfeature rclt {\n" + "".join(f"    lookup {name};\n" for name in lookups) + "} rclt;\n"


def _output_atoms(name: str) -> list[str] | None:
    """The pieces a shaped glyph is written with, read off its name."""

    try:
        descriptor = GlyphDescriptor.parse(name)
    except (AssertionError, ValueError, KeyError):
        return None
    if not descriptor.codePoints:
        return None
    return atoms_of(descriptor.units, descriptor.position)


def _is_piece(name: str) -> bool:
    if name.startswith("cmsr."):
        return True
    try:
        return len(GlyphDescriptor.parse(name).units) == 1 and not GlyphDescriptor.parse(name).codePoints
    except (AssertionError, ValueError, KeyError):
        return False


def _flatten(ufo: Font, name: str, dx: float = 0, dy: float = 0) -> list[tuple[str, float, float]]:
    """The glyph as pieces with their offsets, through any written forms in between.

    A glyph drawn straight from the 1998 keys has no pieces to find, and comes back as its
    keys; a rule can then not apply to it, which is what a drawn whole form should mean.
    """

    found = []
    for component in ufo[name].components:
        x = dx + component.transformation.dx
        y = dy + component.transformation.dy
        if _is_piece(component.baseGlyph) or component.baseGlyph.startswith("cms."):
            found.append((component.baseGlyph, x, y))
        else:
            found.extend(_flatten(ufo, component.baseGlyph, x, y))
    return found


def _draw_alternate(ufo: Font, name: str, width: float, components: list, replacement: str) -> None:
    first, x0, y0 = components[0]
    shift = ufo[replacement].width - ufo[first].width
    glyph = ufo.newGlyph(name)
    glyph.components.append(Component(replacement, Transform(dx=x0, dy=y0)))
    for base, x, y in components[1:]:
        glyph.components.append(Component(base, Transform(dx=x + shift, dy=y)))
    glyph.width = width + shift
