"""Shaping conformance: mongfontbuilder's Hudum suites run against a built font.

The suites check which written units the shaping picks, not what they look like: they prove
the font is wired, and the proofs prove the drawing. Cases with a letter the build leaves out
(nothing draws it yet) are skipped.
The reading of glyph names follows the suites' own runner (mongfontbuilder/tests/utils.py).
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

import uharfbuzz as hb
from fontTools import unicodedata
from mongfontbuilder.testSuites import glyphNameMapping, testSuitesDir
from mongfontbuilder.utils import getCharNameByAlias

from .config import LOCALE

SUITES = ("core-hudum", "eac-hudum")

# Cases the EAC spec answers differently from the UTN model mongfontbuilder follows; the
# library's own runner expects them to fail (tests/fixtures.py, EAC_XFAIL).
EXPECTED_FAILURES = {
    "eac-hudum > XIM11-39",
    "eac-hudum > XIM11-40",
    "eac-hudum > XIM11-41",
    "eac-hudum > XIM11-46",
    "eac-hudum > XIM11-1012",
}


@dataclass
class Case:
    index: str
    letters: str
    goal: str

    @property
    def text(self) -> str:
        return "".join(unicodedata.lookup(getCharNameByAlias(LOCALE, name)) for name in self.letters.split())


@dataclass
class Failure:
    case: Case
    result: str
    expected: bool


def cases() -> list[Case]:
    found = []
    for suite in SUITES:
        with (testSuitesDir / f"{suite}.tsv").open(encoding="utf-8") as file:
            for row in csv.reader(file, delimiter="\t"):
                if row and not row[0].startswith("#"):
                    index, letters, goal = row
                    found.append(Case(f"{suite} > {index}", letters, goal))
    return found


def shape_units(font: hb.Font, text: str) -> str:
    buffer = hb.Buffer()
    buffer.add_str(text)
    buffer.guess_segment_properties()
    hb.shape(font, buffer)

    units = ""
    for info in buffer.glyph_infos:
        name = font.glyph_to_string(info.codepoint)
        name = glyphNameMapping.get(name) or name
        units += _units(name.replace("._", "@").replace(".mvs", "@mvs"))
    units = (
        units.replace("RightLeft", "")
        .replace("RightBaludaLeft", "Baluda")
        .replace("RightTribaludaLeft", "Tribaluda")
    )
    return (
        " ".join(re.findall("[A-Z][a-z0-9]*", units))
        .replace("Nirugu", "Ni")
        .replace("Left", "<")
        .replace("Right", ">")
        .replace("Widespace", "-")
        .replace("Narrowspace", "_")
    )


def _units(name: str) -> str:
    parts = name.split(".")
    if len(parts) == 1:
        return ""
    written, position = parts[-2], parts[-1]
    units = "".join(re.findall("[A-Z][a-z0-9]*", written))
    if position.startswith("init"):
        return units + "Right"
    if position.startswith("medi"):
        return "Left" + units + "Right"
    if position.startswith("fina"):
        return "Left" + units
    return units


def run(path: Path, left_out: list[str] = ()) -> tuple[int, list[Failure], int]:
    font = hb.Font(hb.Face(hb.Blob.from_file_path(path)))
    units = {name.split(".")[0] for name in left_out if not name.startswith("U+")}
    all_cases = cases()
    kept = [case for case in all_cases if not units & set(case.goal.split())]
    failures = []
    for case in kept:
        result = shape_units(font, case.text)
        if result != case.goal:
            failures.append(Failure(case, result, case.index in EXPECTED_FAILURES))
    return len(kept), failures, len(all_cases) - len(kept)
