"""Local server for the mapping editor.

Every read and write goes through mapping/pieces.toml, reloaded each time, so a hand edit
of the file while the editor runs is never overwritten by a stale copy.
"""

from __future__ import annotations

import json
import threading
import webbrowser
from functools import cache
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from fontTools import unicodedata
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont
from mongfontbuilder import data, splitWrittens

from . import config
from .build import _stem, build
from .check import run
from .legacy import LegacyFont
from .mapping import Entry, Mapping, Mark
from .targets import LOCALE, atoms_of, targets, variants

EDITOR_DIR = config.ROOT / "editor"
REFERENCE_FONT = config.ROOT / "reference" / "NotoSansMongolian-Regular.ttf"

lock = threading.Lock()
last_builds: dict[str, dict] = {}


def _number(value: float) -> str:
    return f"{round(value, 1):g}"


def _outline(glyph_set, name: str) -> dict:
    recording = DecomposingRecordingPen(glyph_set)
    glyph_set[name].draw(recording)
    pen = SVGPathPen(glyph_set, ntos=_number)
    recording.replay(pen)
    bounds = BoundsPen(glyph_set)
    recording.replay(bounds)
    return {"path": pen.getCommands(), "bounds": [round(value) for value in bounds.bounds or (0, 0, 0, 0)]}


def _contour(glyph_set, recording: list) -> dict:
    pen = SVGPathPen(glyph_set, ntos=_number)
    bounds = BoundsPen(glyph_set)
    for operator, arguments in recording:
        getattr(pen, operator)(*arguments)
        getattr(bounds, operator)(*arguments)
    return {"path": pen.getCommands(), "bounds": [round(value) for value in bounds.bounds or (0, 0, 0, 0)]}


@cache
def _legacy(cut_id: str) -> dict:
    font = LegacyFont.open(cut_id)
    glyph_set = font.ttf.getGlyphSet()
    return {
        "upm": font.units_per_em,
        "ascent": font.ttf["hhea"].ascent,
        "descent": font.ttf["hhea"].descent,
        "stem": list(_stem(font)),
        "keys": {
            key: {
                "glyph": name,
                "advance": font.advance(name),
                **_outline(glyph_set, name),
                "contours": [_contour(glyph_set, contour) for contour in font.contours(name)],
            }
            for key, name in font.keyed_glyphs().items()
        },
    }


def _label(code_point: int) -> str:
    alias = data.aliases[unicodedata.name(chr(code_point))]
    return alias if isinstance(alias, str) else alias.get(LOCALE, f"u{code_point:04X}")


@cache
def _static_data() -> dict:
    reference = TTFont(REFERENCE_FONT)
    glyph_set = reference.getGlyphSet()
    cmap = reference.getBestCmap()
    reference_glyphs: dict[str, dict] = {}

    def add_reference(name: str | None) -> str | None:
        if name is None or name not in glyph_set:
            return None
        if name not in reference_glyphs:
            reference_glyphs[name] = {"advance": reference["hmtx"][name][0], **_outline(glyph_set, name)}
        return name

    variant_rows = []
    used_by: dict[str, list[str]] = {}
    for variant in variants():
        for atom in dict.fromkeys(variant.atoms):
            used_by.setdefault(atom, []).append(variant.id)
        variant_rows.append(
            {
                "id": variant.id,
                "label": _label(variant.code_point),
                "codePoint": variant.code_point,
                "position": variant.position,
                "fvs": variant.fvs,
                "default": variant.default,
                "written": variant.written,
                "atoms": variant.atoms,
                "reference": add_reference(f"uni{variant.code_point:04X}.{variant.written}"),
            }
        )

    target_rows = []
    for target in targets():
        if target.kind == "char":
            code_point = int(target.name[2:], 16)
            atoms: list[str] = []
            reference_name = add_reference(cmap.get(code_point))
            label = unicodedata.name(chr(code_point), target.name).title()
        else:
            written, position = target.name.split(".")[:2]
            atoms = atoms_of(splitWrittens(written), position)
            reference_name = add_reference(target.name)
            label = ""
        target_rows.append(
            {
                "name": target.name,
                "kind": target.kind,
                "required": target.required,
                "atoms": atoms,
                "label": label,
                "reference": reference_name,
                "usedBy": used_by.get(target.name, []),
            }
        )

    return {
        "cuts": [{"id": cut.id, "name": cut.name, "family": cut.family} for cut in config.CUTS.values()],
        "defaultCut": config.DEFAULT_CUT,
        "legacy": {cut_id: _legacy(cut_id) for cut_id in config.CUTS},
        "reference": {
            "upm": reference["head"].unitsPerEm,
            "ascent": reference["hhea"].ascent,
            "descent": reference["hhea"].descent,
            "glyphs": reference_glyphs,
        },
        "targets": target_rows,
        "variants": variant_rows,
    }


def _mapping_state(mapping: Mapping) -> dict:
    return {
        "entries": {entry.name: entry.as_dict() for entry in mapping.all()},
        "problems": mapping.problems(),
    }


def _build(cut_id: str) -> dict:
    result = build(cut_id)
    total, failures = run(result.path)
    unexpected = [failure for failure in failures if not failure.expected]
    report = {
        "cut": cut_id,
        "font": f"/dist/{result.path.name}",
        "revision": result.path.stat().st_mtime_ns,
        "placeholders": len(result.placeholders),
        "keyed": len(result.keyed),
        "drawn": len(result.drawn),
        "cases": total,
        "failures": [
            {"index": failure.case.index, "letters": failure.case.letters, "got": failure.result, "want": failure.case.goal}
            for failure in unexpected
        ],
    }
    last_builds[cut_id] = report
    return report


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, directory=str(config.ROOT), **kwargs)

    def log_message(self, format: str, *args) -> None:
        pass

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/data":
            with lock:
                mapping = Mapping.load()
                return self._json({**_static_data(), **_mapping_state(mapping), "builds": last_builds})
        if path == "/" or path == "/index.html":
            self.path = "/editor/index.html"
        elif not (path.startswith("/editor/") or path.startswith("/dist/") or path.startswith("/reference/")):
            return self.send_error(404)
        super().do_GET()

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        try:
            with lock:
                if path == "/api/entry":
                    mapping = Mapping.load()
                    mapping.set(
                        Entry(
                            body["name"],
                            "piece",
                            keys=body.get("keys") or None,
                            status=body.get("status", "todo"),
                            note=body.get("note", ""),
                            cuts={cut: keys for cut, keys in body.get("cuts", {}).items() if keys},
                            marks=[Mark.from_dict(mark) for mark in body.get("marks", [])],
                        )
                    )
                    mapping.save()
                    return self._json(_mapping_state(mapping))
                if path == "/api/build":
                    return self._json(_build(body.get("cut", config.DEFAULT_CUT)))
        except (KeyError, ValueError) as error:
            return self._json({"error": str(error)}, status=400)
        self.send_error(404)

    def _json(self, value: object, status: int = 200) -> None:
        payload = json.dumps(value, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def serve(port: int = 8787, open_browser: bool = False) -> None:
    for candidate in range(port, port + 20):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", candidate), Handler)
            break
        except OSError:
            continue
    else:
        raise SystemExit(f"no free port in {port}–{port + 19}")
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"editor at {url}  (Ctrl+C to stop)")
    if open_browser:
        threading.Timer(0.3, webbrowser.open, (url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
