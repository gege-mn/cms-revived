"""Which joins of real text the goldens cover, and which words would cover the rest.

A word is shaped with the built font and read as features: every glyph it uses (a written
form or ligature, which draws a set of pieces) and every pair of pieces that touch across
glyphs (where the neighbour rules act). Real text, weighted by how often each word occurs,
says which features matter; the goldens say which are already checked.
"""

from __future__ import annotations

import re
from collections import Counter
from functools import cache
from pathlib import Path

import uharfbuzz as hb

from . import goldens
from .config import ROOT
from .neighbours import _output_atoms

CORPORA = ROOT / "reference" / "corpora"
WORD = re.compile(r"[ᠠ-ᡂ᠋-᠏ ]+")

ROMAN = {
    0x1820: "a", 0x1821: "e", 0x1822: "i", 0x1823: "o", 0x1824: "u", 0x1825: "ö", 0x1826: "ü", 0x1827: "ē",
    0x1828: "n", 0x1829: "ng", 0x182A: "b", 0x182B: "p", 0x182C: "q", 0x182D: "γ", 0x182E: "m", 0x182F: "l",
    0x1830: "s", 0x1831: "š", 0x1832: "t", 0x1833: "d", 0x1834: "č", 0x1835: "j", 0x1836: "y", 0x1837: "r",
    0x1838: "w", 0x1839: "f", 0x183A: "k2", 0x183B: "k", 0x183C: "c", 0x183D: "z", 0x183E: "h", 0x183F: "ž",
    0x1840: "lh", 0x1841: "zh", 0x1842: "ch", 0x180E: "-", 0x202F: "-",
}


def romanize(word: str) -> str:
    return "".join(ROMAN.get(ord(character), "") for character in word)


@cache
def corpus_words() -> Counter:
    words: Counter = Counter()
    for path in sorted(CORPORA.glob("*.md")):
        words.update(WORD.findall(path.read_text(encoding="utf-8")))
    return words


def features(font: hb.Font, word: str) -> set[tuple]:
    buffer = hb.Buffer()
    buffer.add_str(word)
    buffer.guess_segment_properties()
    hb.shape(font, buffer)
    names = [font.glyph_to_string(info.codepoint).split("._after_")[0] for info in buffer.glyph_infos]
    found: set[tuple] = set()
    previous_atoms = None
    for name in names:
        atoms = _output_atoms(name)
        if atoms is None:
            previous_atoms = None  # a space, MVS or control: nothing joins across it
            continue
        found.add(("glyph", name))
        if previous_atoms:
            found.add(("join", previous_atoms[-1], atoms[0]))
        previous_atoms = atoms
    return found


def _font(path: Path) -> hb.Font:
    return hb.Font(hb.Face(hb.Blob.from_file_path(path)))


def report(path: Path) -> tuple[float, float]:
    """The share of real-text glyphs and joins, by frequency, that confirmed goldens check."""

    font = _font(path)
    covered: set[tuple] = set()
    for golden in goldens.load():
        if golden.status != "pending":
            covered |= features(font, golden.text)
    weight = {"glyph": Counter(), "join": Counter()}
    for word, count in corpus_words().items():
        for feature in features(font, word):
            weight[feature[0]][feature] += count
    shares = []
    for kind in ("glyph", "join"):
        total = sum(weight[kind].values())
        shares.append(sum(count for feature, count in weight[kind].items() if feature in covered) / total if total else 0)
    return shares[0], shares[1]


def suggest(path: Path, count: int = 10, min_frequency: int = 5, max_letters: int = 6) -> list[tuple[str, str, int, int]]:
    """Short, common words that each check joins no golden checks yet: (word, roman, new, freq)."""

    font = _font(path)
    existing = {golden.text for golden in goldens.load()}
    covered: set[tuple] = set()
    for golden in goldens.load():
        covered |= features(font, golden.text)

    candidates = []
    for word, frequency in corpus_words().items():
        letters = sum(1 for character in word if 0x1820 <= ord(character) <= 0x1842)
        if word in existing or frequency < min_frequency or not 2 <= letters <= max_letters:
            continue
        candidates.append((word, frequency, letters, features(font, word)))

    picked = []
    while len(picked) < count:
        best = max(
            candidates,
            key=lambda item: (len(item[3] - covered), -item[2], item[1]),
            default=None,
        )
        if best is None or not best[3] - covered:
            break
        word, frequency, _, found = best
        picked.append((word, romanize(word), len(found - covered), frequency))
        covered |= found
        candidates.remove(best)
    return picked
