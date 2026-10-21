"""The mapping: which 1998 keys draw each target. The one source of truth of the rework."""

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from .config import CUTS, MAPPING_FILE
from .legacy import LegacyFont
from .targets import Kind, Target, is_written_form, targets

Status = Literal["todo", "draft", "ok", "new", "auto"]
STATUSES: tuple[Status, ...] = ("todo", "draft", "ok", "new", "auto")

SECTIONS: dict[str, Kind] = {
    "pieces": "piece",
    "mvs": "mvs",
    "ligatures": "ligature",
    "chars": "char",
    "forms": "form",
}

HEADER = """\
# CMs Revived: which 1998 keys draw each Unicode target.
#
# keys    the CMs key sequence that draws it, as typed on the 1998 keyboard
# cuts    per-cut keys where a cut differs, e.g. cuts = { CMSHR = "fx" }
# status  todo   not mapped yet; the build draws a placeholder box
#         draft  mapped, waiting for a human eye
#         ok     confirmed
#         new    CMs has no such piece; drawn in drawings/<cut>.ufo
#         auto   built from its parts (ligatures, pre-MVS forms)
#
# pieces     single written units in a joining position: everything is built from these
# mvs        the shape a unit takes before an MVS, where it has one of its own
# ligatures  bow letters and others drawn as one form; "auto" joins the parts as they are
# chars      punctuation, digits and the nirugu, by code point
# forms      any other whole written form drawn differently from its parts
#
# The editor (cmsr editor) rewrites this file; comments other than this header are not kept.
"""


@dataclass
class Entry:
    name: str
    kind: Kind
    keys: str | None = None
    status: Status = "todo"
    note: str = ""
    cuts: dict[str, str] = field(default_factory=dict)

    def keys_for(self, cut_id: str) -> str | None:
        return self.cuts.get(cut_id, self.keys)

    def as_dict(self) -> dict:
        found: dict = {"name": self.name, "kind": self.kind, "status": self.status}
        if self.keys is not None:
            found["keys"] = self.keys
        if self.cuts:
            found["cuts"] = self.cuts
        if self.note:
            found["note"] = self.note
        return found


def default_entry(target: Target) -> Entry:
    status: Status = "auto" if target.kind in ("ligature", "mvs") else "todo"
    return Entry(target.name, target.kind, status=status)


class Mapping:
    def __init__(self, entries: dict[str, Entry], path: Path = MAPPING_FILE) -> None:
        self.entries = entries
        self.path = path
        self.targets = {target.name: target for target in targets()}

    @classmethod
    def load(cls, path: Path = MAPPING_FILE) -> Mapping:
        entries: dict[str, Entry] = {}
        if path.exists():
            raw = tomllib.loads(path.read_text(encoding="utf-8"))
            for section, kind in SECTIONS.items():
                for name, fields in raw.get(section, {}).items():
                    entries[name] = Entry(
                        name,
                        kind,
                        keys=fields.get("keys"),
                        status=fields.get("status", "todo"),
                        note=fields.get("note", ""),
                        cuts=dict(fields.get("cuts", {})),
                    )
        return cls(entries, path)

    def get(self, name: str) -> Entry:
        if name in self.entries:
            return self.entries[name]
        return default_entry(self.targets[name])

    def all(self) -> list[Entry]:
        """Every target in target order, then the extra forms."""

        found = [self.get(name) for name in self.targets]
        found += [entry for name, entry in self.entries.items() if name not in self.targets]
        return found

    def set(self, entry: Entry) -> None:
        if entry.name in self.targets:
            entry.kind = self.targets[entry.name].kind
        elif not is_written_form(entry.name):
            raise ValueError(f"{entry.name!r} is neither a target nor a written form")
        else:
            entry.kind = "form"
        self.entries[entry.name] = entry

    def problems(self) -> list[str]:
        found = []
        fonts = {cut_id: LegacyFont.open(cut_id) for cut_id in CUTS}
        for entry in self.all():
            if entry.status not in STATUSES:
                found.append(f"{entry.name}: unknown status {entry.status!r}")
            if entry.status in ("draft", "ok") and not entry.keys:
                found.append(f"{entry.name}: {entry.status} without keys")
            if entry.status == "auto" and entry.kind not in ("ligature", "mvs"):
                found.append(f"{entry.name}: only ligatures and pre-MVS forms can be auto")
            for cut_id, font in fonts.items():
                keys = entry.keys_for(cut_id) or ""
                missing = sorted({key for key in keys if key not in font.keyed_glyphs()})
                if missing:
                    found.append(f"{entry.name}: {cut_id} has no glyph on {''.join(missing)!r}")
        return found

    def save(self) -> None:
        by_section: dict[str, list[Entry]] = {section: [] for section in SECTIONS}
        kind_to_section = {kind: section for section, kind in SECTIONS.items()}
        for entry in self.all():
            by_section[kind_to_section[entry.kind]].append(entry)

        lines = [HEADER]
        for section, entries in by_section.items():
            if not entries:
                continue
            lines.append(f"[{section}]")
            for entry in entries:
                line = f"{_string(entry.name)} = {_inline(entry)}"
                target = self.targets.get(entry.name)
                if target and target.kind == "ligature" and target.required:
                    line += "  # required"
                lines.append(line)
            lines.append("")

        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".toml.tmp")
        temporary.write_text("\n".join(lines), encoding="utf-8")
        temporary.replace(self.path)


def _string(value: str) -> str:
    # JSON string escapes are a subset of TOML basic-string escapes.
    return json.dumps(value, ensure_ascii=False)


def _inline(entry: Entry) -> str:
    fields = []
    if entry.keys is not None:
        fields.append(f"keys = {_string(entry.keys)}")
    if entry.cuts:
        cuts = ", ".join(f"{cut} = {_string(keys)}" for cut, keys in sorted(entry.cuts.items()))
        fields.append(f"cuts = {{ {cuts} }}")
    fields.append(f"status = {_string(entry.status)}")
    if entry.note:
        fields.append(f"note = {_string(entry.note)}")
    return "{ " + ", ".join(fields) + " }"
