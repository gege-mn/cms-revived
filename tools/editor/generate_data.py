#!/usr/bin/env python3
"""Generate the data the CMs <-> Unicode editor runs on.

Two products:

* ``data/forms.json`` -- every Hudum written form the specification knows about
  for the MNG locale (letter x joining position x FVS variant), each with the
  reference outline taken from Noto Sans Mongolian by glyph name, plus the
  written units and the GB/T reference the mongfontbuilder data gives it.

* ``data/cms-glyphs.json`` -- the outline of every glyph the 1998 CMs fonts map
  to ASCII, normalised to a 1000-unit em with the baseline at y=1000, so the
  browser can lay a typed legacy run out exactly.

The reference outlines are addressed by name (``uni1820.AA.init``).  That name
is the written units of the variant in the mongfontbuilder data plus the
joining position, which is how Noto names its glyphs; every variant the data
lists for Hudum in MNG resolves this way (216 of 216 at the time of writing).

    python3 generate_data.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from fontTools import unicodedata
from fontTools.misc.transform import Transform
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

HERE = Path(__file__).resolve().parent
VENDOR = HERE / "vendor" / "mongfontbuilder"
OUT = HERE / "data"

POSITIONS = ("isol", "init", "medi", "fina")
POSITION_ORDER = {p: i for i, p in enumerate(POSITIONS)}

# FVS code points.  Kept as integers: never write these characters literally.
FVS_CODE_POINTS = {"1": 0x180B, "2": 0x180C, "3": 0x180D, "4": 0x180F}

HUDUM_RANGE = (0x1820, 0x1842)
TARGET_EM = 1000


def number(value: float) -> str:
    """Short, stable number formatting for SVG path data."""
    return f"{round(value, 2):g}"


def geometry(font: TTFont, glyph_name: str) -> tuple[str, list[float], float] | None:
    """Path, bounds and advance of *glyph_name*, in a 1000-unit em, y down.

    The baseline sits at y=1000 and the ascender area is negative y, which is
    the coordinate system an SVG viewBox wants.
    """
    glyph_set = font.getGlyphSet()
    if glyph_name not in glyph_set:
        return None

    scale = TARGET_EM / font["head"].unitsPerEm
    transform = Transform(scale, 0, 0, -scale, 0, TARGET_EM)

    pen = SVGPathPen(glyph_set, ntos=number)
    glyph_set[glyph_name].draw(TransformPen(pen, transform))

    bounds_pen = BoundsPen(glyph_set)
    glyph_set[glyph_name].draw(TransformPen(bounds_pen, transform))

    advance = font["hmtx"][glyph_name][0] * scale
    bounds = list(bounds_pen.bounds) if bounds_pen.bounds else [0, 0, 0, 0]
    return pen.getCommands(), bounds, round(advance, 2)


def resolve_units(table: dict, position: str, fvs: str) -> tuple[list[str], str]:
    """Written units and joining position of a variant.

    A variant may name another position's variant instead of written units
    (``["init", 0]``); follow those references to the units themselves.
    """
    written = table[position][fvs]["written"]
    target_position = position
    for _ in range(8):
        if not (isinstance(written, list) and written and written[0] in POSITIONS):
            return written, target_position
        target_position = written[0]
        written = table[target_position][str(written[1])]["written"]
    raise ValueError(f"variant reference loop at {position}/{fvs}")


def load_mongfontbuilder_data() -> tuple[dict, dict, dict]:
    variants = json.loads((VENDOR / "variants.json").read_text())
    aliases = json.loads((VENDOR / "aliases.json").read_text())
    locales = json.loads((VENDOR / "locales.json").read_text())
    return variants, aliases, locales


def hudum_letters(aliases: dict, variants: dict) -> list[tuple[str, str]]:
    """(code point hex, character name) of the Hudum letters in MNG."""
    letters = []
    for char_name, alias_data in aliases.items():
        if not isinstance(alias_data, dict) or "MNG" not in alias_data:
            continue
        if char_name not in variants:
            continue
        code_point = ord(unicodedata.lookup(char_name))
        if HUDUM_RANGE[0] <= code_point <= HUDUM_RANGE[1]:
            letters.append((code_point, char_name))
    return sorted(letters)


def build_forms(noto: TTFont) -> tuple[list[dict], list[float]]:
    variants, aliases, locales = load_mongfontbuilder_data()
    mng = locales["MNG"]
    category_aliases = set(mng["categories"]["vowel"] + mng["categories"]["consonant"])

    items: list[dict] = []
    boxes: list[list[float]] = []

    missings: list[str] = []
    for code_point, char_name in hudum_letters(aliases, variants):
        alias = aliases[char_name]["MNG"]
        table = variants[char_name]
        for position in POSITIONS:
            for fvs, variant in table[position].items():
                if "MNG" not in variant["locales"]:
                    continue
                units, target_position = resolve_units(table, position, fvs)
                glyph_name = f"uni{code_point:04X}.{''.join(units)}.{target_position}"
                shape = geometry(noto, glyph_name)
                if shape is None:
                    missings.append(glyph_name)
                    continue
                path, bounds, advance = shape
                boxes.append(bounds)
                data = variant["locales"]["MNG"]
                is_default = bool(variant.get("default"))
                code_points = [code_point]
                # The default form is the one written without an FVS, even when
                # the specification files it under FVS2 or FVS3; only a variant
                # that the text has to ask for carries the FVS code point.
                if fvs in FVS_CODE_POINTS and not is_default:
                    code_points.append(FVS_CODE_POINTS[fvs])
                items.append(
                    {
                        "id": f"u{code_point:04X}.{position}.{fvs}",
                        "codePoints": code_points,
                        "letter": alias,
                        "letterChar": chr(code_point),
                        "charName": char_name,
                        "position": position,
                        "fvs": fvs,
                        "fvsCodePoint": FVS_CODE_POINTS.get(fvs) if not is_default else None,
                        "variant": fvs,
                        "written": "".join(units),
                        "writtenPosition": target_position,
                        "glyph": glyph_name,
                        "path": path,
                        "bounds": [round(v, 2) for v in bounds],
                        "advance": advance,
                        "default": is_default,
                        "archaic": bool(data.get("archaic")),
                        "conditions": data.get("conditions", []),
                        "gb": data.get("gb"),
                    }
                )

    if missings:
        print(f"reference glyphs missing from Noto: {len(missings)}", file=sys.stderr)
        for name in missings[:20]:
            print("  " + name, file=sys.stderr)

    items.sort(
        key=lambda i: (
            i["codePoints"][0],
            POSITION_ORDER[i["position"]],
            0 if i["default"] else 1,
            int(i["fvs"]),
        )
    )
    return items, boxes


def build_cms_glyphs(cms_dir: Path) -> tuple[dict, list[list[float]]]:
    families = {"CMSUG": "CMs Urga", "CMSUB": "CMs Ulaanbaatar", "CMSHR": "CMs Huree"}
    output: dict = {"upem": TARGET_EM, "families": {}}
    boxes: list[list[float]] = []

    for stem, label in families.items():
        font = TTFont(cms_dir / f"{stem}.TTF")
        cmap = font.getBestCmap()
        glyphs: dict[str, dict] = {}
        for code_point, glyph_name in sorted(cmap.items()):
            shape = geometry(font, glyph_name)
            if shape is None:
                continue
            path, bounds, advance = shape
            glyphs[chr(code_point)] = {
                "d": path,
                "bounds": [round(v, 2) for v in bounds],
                "advance": advance,
                "glyph": glyph_name,
            }
            boxes.append(bounds)
        output["families"][stem] = {"label": label, "glyphs": glyphs}

    return output, boxes


def global_view_box(boxes: list[list[float]], padding: float = 80) -> list[float]:
    x0 = min(b[0] for b in boxes) - padding
    y0 = min(b[1] for b in boxes) - padding
    x1 = max(b[2] for b in boxes) + padding
    y1 = max(b[3] for b in boxes) + padding
    return [round(x0, 1), round(y0, 1), round(x1 - x0, 1), round(y1 - y0, 1)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--noto",
        type=Path,
        default=HERE / "fonts" / "NotoSansMongolian-Regular.ttf",
        help="reference font (Noto Sans Mongolian)",
    )
    parser.add_argument(
        "--cms-dir",
        type=Path,
        default=HERE.parent.parent / "cms",
        help="directory holding CMSUG.TTF, CMSUB.TTF, CMSHR.TTF",
    )
    args = parser.parse_args()

    noto = TTFont(args.noto)
    forms, form_boxes = build_forms(noto)
    cms, cms_boxes = build_cms_glyphs(args.cms_dir)

    view_box = global_view_box(form_boxes + cms_boxes)
    meta = {
        "generated": __import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds"),
        "referenceFont": "Noto Sans Mongolian",
        "referenceUpem": noto["head"].unitsPerEm,
        "mongfontbuilderData": "0.15.3",
        "locale": "MNG",
        "viewBox": view_box,
        "em": TARGET_EM,
    }

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "forms.json").write_text(
        json.dumps({"meta": meta, "items": forms}, ensure_ascii=False, separators=(",", ":"))
        + "\n"
    )
    (OUT / "cms-glyphs.json").write_text(
        json.dumps({"meta": meta, **cms}, ensure_ascii=False, separators=(",", ":")) + "\n"
    )

    defaults = sum(1 for i in forms if i["default"])
    print(f"forms: {len(forms)} ({defaults} default), cms glyphs: "
          f"{sum(len(f['glyphs']) for f in cms['families'].values())}")
    print(f"viewBox: {view_box}")


if __name__ == "__main__":
    main()
