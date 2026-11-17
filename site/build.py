"""Writes site/public/, the homepage at cms-revived.gege.mn, from the released fonts.

uv run --with brotli python site/build.py
"""

from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from cmsr.companion import typed_keys  # noqa: E402
from cmsr.config import CONTACT, CUTS  # noqa: E402
from joins import Join  # noqa: E402

SITE = "https://cms-revived.gege.mn"
OUT = HERE / "public"
RELEASE = "1.0.1"
MAIN_DIR = ROOT / "releases" / RELEASE
LEGACY_DIR = ROOT / "releases" / f"legacy-{RELEASE}"
NOTO = Path.home() / "Projects/gege.mn/static/fonts"
NOTO_VERSION = "3.103"
LANGS = ("mn", "en", "fr")

# From releases/1.0.1/NOTES.md and docs/state.md.
CASES = (3548, 3553)
GOLDENS = 103

HERO_WORDS = ("mongγol", "bičig")
# Joins CMs drew differently, each as typed in 1998 and as the rework draws it. `at` places the
# zoom down the word; None finds where 1998's ink falls apart. Then the zoom's size in em.
JOINS = (
    ("ᠶᠡᠷᠦᠩᠬᠡᠢ", "CMSUB", 0.72, 0.8, "join_arches"),
    ("ᠲᠩᠷᠢ", "CMSUB", 0.7, 0.8, "join_r"),
    ("ᠮᠠᠲᠧᠷᠢᠶᠠᠯ", "CMSHR", None, 0.25, "join_t"),
    ("ᠢᠳᠡᠪᠬᠢᠲᠡᠢ", "CMSHR", None, 0.25, "join_arch_gap"),
)


def goldens() -> dict[str, dict]:
    data = tomllib.loads((ROOT / "mapping/goldens.toml").read_text())
    return {g["latin"]: g for g in data["golden"]}


def specimen() -> tuple[str, str, str]:
    lines = [line for line in (ROOT / "editor/specimen.txt").read_text().splitlines() if line.strip()]
    title, body = lines[0], lines[1]
    first = body.split("᠃")[0] + "᠃"
    return title, first, lines[3].split("\u1803")[0] + "\u1803"


def woff2(src: Path, dst: Path) -> None:
    font = TTFont(src)
    font.flavor = "woff2"
    font.save(dst)


def number(n: int, lang: str) -> str:
    s = f"{n:,}"
    return s.replace(",", " " if lang == "fr" else " ") if lang in ("mn", "fr") else s


def ink_length(path: Path, text: str, features: dict[str, bool]) -> float:
    """Length of the inked run in em: the advances run well past the ink in these fonts."""
    font = TTFont(path)
    glyf = font["glyf"]
    hbfont = hb.Font(hb.Face(hb.Blob.from_file_path(str(path))))
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(hbfont, buf, features)
    pen, lo, hi = 0, float("inf"), float("-inf")
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        g = glyf[font.getGlyphName(info.codepoint)]
        if g.numberOfContours:
            lo = min(lo, pen + pos.x_offset + g.xMin)
            hi = max(hi, pen + pos.x_offset + g.xMax)
        pen += pos.x_advance
    return (hi - lo) / font["head"].unitsPerEm


def og_image(gold: dict[str, dict]) -> None:
    words = " ".join(gold[w]["text"] for w in HERO_WORDS)
    columns = []
    x0 = 610
    for i, cut in enumerate(CUTS.values()):
        path = MAIN_DIR / f"{cut.postscript_name}.ttf"
        font = TTFont(path)
        glyphs = font.getGlyphSet()
        blob = hb.Blob.from_file_path(str(path))
        hbfont = hb.Font(hb.Face(blob))
        buf = hb.Buffer()
        buf.add_str(words)
        buf.guess_segment_properties()
        hb.shape(hbfont, buf, {})
        upem = font["head"].unitsPerEm
        scale = 150 / upem
        pen_x = 0
        paths = []
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
            pen = SVGPathPen(glyphs)
            glyphs[font.getGlyphName(info.codepoint)].draw(pen)
            d = pen.getCommands()
            if d:
                paths.append(f'<path transform="translate({pen_x + pos.x_offset} {pos.y_offset})" d="{d}"/>')
            pen_x += pos.x_advance
        top = (630 - pen_x * scale) / 2
        # Vertical Mongolian is the horizontal line turned a quarter clockwise.
        x = x0 + i * 190 + 400 * scale
        columns.append(
            f'<g fill="#000000" transform="translate({x:.1f} {top:.1f}) matrix(0 {scale:.5f} {scale:.5f} 0 0 0)">'
            + "".join(paths)
            + "</g>"
        )
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
<rect width="1200" height="630" fill="#ffffff"/>
<rect x="0" y="0" width="1200" height="14" fill="#1f43d6"/>
<text x="72" y="250" font-family="Helvetica Neue, Helvetica, sans-serif" font-size="68" font-weight="bold" letter-spacing="-2" fill="#000000">Gege CMs</text>
<text x="72" y="326" font-family="Helvetica Neue, Helvetica, sans-serif" font-size="68" font-weight="bold" letter-spacing="-2" fill="#000000">Revived</text>
<text x="72" y="392" font-family="Helvetica Neue, Helvetica, sans-serif" font-size="28" fill="#5b6270">dEgi, 1998. Unicode, 2026.</text>
<text x="72" y="560" font-family="Helvetica Neue, Helvetica, sans-serif" font-size="24" font-weight="500" fill="#1f43d6">cms-revived.gege.mn</text>
{"".join(columns)}
</svg>"""
    svg_path = OUT / "og.svg"
    svg_path.write_text(svg)
    subprocess.run(["rsvg-convert", "-w", "1200", "-h", "630", "-o", str(OUT / "og.png"), str(svg_path)], check=True)
    svg_path.unlink()


def page(lang: str, copy: dict, all_copy: dict[str, dict], gold: dict[str, dict], files: dict) -> str:
    sample = specimen()[2]
    t = dict(copy)
    t["site"] = SITE
    t["canonical"] = SITE + copy["path"]
    t["contact"] = CONTACT
    t["alternates"] = "\n".join(
        f'<link rel="alternate" hreflang="{c["lang"]}" href="{SITE}{c["path"]}">' for c in all_copy.values()
    ) + f'\n<link rel="alternate" hreflang="x-default" href="{SITE}/">'
    t["lang_links"] = "".join(
        f'<a href="{c["path"]}" hreflang="{c["lang"]}" lang="{c["lang"]}" title="{c["name"]}"'
        + (' aria-current="page"' if c["lang"] == lang else "")
        + f'>{c["lang"].upper()}</a>'
        for c in all_copy.values()
    )
    t["preloads"] = "\n".join(
        f'<link rel="preload" href="/fonts/{f}" as="font" type="font/woff2" crossorigin>' for f in files["woff2_main"]
    )
    t["font_faces"] = "\n".join(
        f'@font-face {{ font-family: "{family}"; src: url("/fonts/{f}") format("woff2"); font-display: block; }}'
        for family, f in files["faces"]
    )
    t["cuts"] = "".join(
        f'<article class="cut"><header><h3>{cut.name}</h3>'
        f'<a href="/download/{cut.postscript_name}.ttf" download>{copy["download_one"]}</a></header>'
        f'<textarea class="pad mongol f-{cut.id}" lang="mn-Mong" spellcheck="false" autocomplete="off" autocapitalize="off" aria-label="{cut.family}"></textarea></article>'
        for cut in CUTS.values()
    )
    t["sample_json"] = json.dumps(sample).replace("</", "<\\/")
    t["kb_buttons"] = "".join(
        f'<button type="button" data-layout="{k}" aria-pressed="false" data-hint="{html.escape(copy["kb_" + k + "_hint"])}">{copy["kb_" + k]}</button>'
        for k in ("standard", "latin", "monkhgal", "os")
    )
    t["hero_json"] = files["hero_json"]
    t["hero_1998_json"] = json.dumps(copy["hero_1998"], ensure_ascii=False)
    t["hero_2026_json"] = json.dumps(copy["hero_2026"], ensure_ascii=False)
    for key in ("fact_cases", "fact_goldens"):
        t[key] = copy[key].format(passed=number(CASES[0], lang), total=number(CASES[1], lang), goldens=GOLDENS)
    t["joins"] = files["joins"](copy)
    t["zip_main"] = "/download/" + files["zip_main"]
    t["zip_legacy"] = "/download/" + files["zip_legacy"]
    t["files_main"] = files_list(files["main"])
    t["files_legacy"] = files_list(files["legacy"])

    out = (HERE / "page.html").read_text()

    def fill(m: re.Match) -> str:
        key = m.group(1)
        if key not in t:
            raise KeyError(f"{lang}: no slot {key}")
        return str(t[key])

    return re.sub(r"\{\{(\w+)\}\}", fill, out)


def files_list(fonts: list[tuple[str, Path]]) -> str:
    return "".join(
        f'<li><a href="/download/{p.name}" download><span>{label}</span>'
        f"<span>{round(p.stat().st_size / 1024)} KB</span></a></li>"
        for label, p in fonts
    )


def pack(name: str, fonts: list[Path]) -> str:
    folder = name.removesuffix(".zip")
    with zipfile.ZipFile(OUT / "download" / name, "w", zipfile.ZIP_DEFLATED) as z:
        for f in fonts:
            z.write(f, f"{folder}/{f.name}")
        z.write(ROOT / "NOTICE.md", f"{folder}/NOTICE.md")
    return name


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "fonts").mkdir(parents=True)
    (OUT / "download").mkdir()

    main_fonts = [MAIN_DIR / f"{cut.postscript_name}.ttf" for cut in CUTS.values()]
    main_named = [(cut.family, MAIN_DIR / f"{cut.postscript_name}.ttf") for cut in CUTS.values()]
    legacy_named = [(cut.companion_family, LEGACY_DIR / cut.companion_path.name) for cut in CUTS.values()] + [
        (cut.companion_dp_family, LEGACY_DIR / cut.companion_dp_path.name) for cut in CUTS.values()
    ]
    legacy_fonts = [p for _, p in legacy_named]
    for f in main_fonts + legacy_fonts:
        shutil.copy2(f, OUT / "download" / f.name)

    faces = []
    woff2_main = []
    for cut, f in zip(CUTS.values(), main_fonts):
        name = f"{cut.postscript_name}-{RELEASE}.woff2"
        woff2(f, OUT / "fonts" / name)
        faces.append((cut.family, name))
        woff2_main.append(name)
    for cut in CUTS.values():
        name = f"{cut.companion_family.replace(' ', '')}-legacy-{RELEASE}.woff2"
        woff2(LEGACY_DIR / cut.companion_path.name, OUT / "fonts" / name)
        faces.append((cut.companion_family, name))
    noto = f"noto-sans-mongolian-{NOTO_VERSION}.woff2"
    shutil.copy2(NOTO / "noto-sans-mongolian.woff2", OUT / "fonts" / noto)
    shutil.copy2(NOTO / "OFL.txt", OUT / "fonts" / "noto-sans-mongolian-OFL.txt")
    faces.append(("Noto Sans Mongolian", noto))

    files = {
        "faces": faces,
        "woff2_main": woff2_main,
        "main": main_named,
        "legacy": legacy_named,
        "zip_main": pack(f"GegeCMsRevived-{RELEASE}.zip", main_fonts),
        "zip_legacy": pack(f"CMsRevived-legacy-{RELEASE}.zip", legacy_fonts),
    }

    hero = []
    for entry in tomllib.loads((HERE / "hero.toml").read_text())["word"]:
        cut = CUTS[entry["cut"]]
        keys = entry.get("keys") or typed_keys(cut.id, entry["text"])
        legacy = LEGACY_DIR / cut.companion_path.name
        ink = max(
            ink_length(legacy, keys, {"liga": False, "calt": False}),
            ink_length(MAIN_DIR / f"{cut.postscript_name}.ttf", entry["text"], {}),
        )
        hero.append(
            {
                "keys": keys,
                "text": entry["text"],
                "cut": cut.id,
                "family": cut.family,
                "legacyFamily": cut.companion_family + " (1998)",
                "ink": round(ink, 3),
            }
        )
    files["hero_json"] = json.dumps(hero, ensure_ascii=False)

    built = []
    for word, cut_id, at, size, key in JOINS:
        cut = CUTS[cut_id]
        join = Join.of(LEGACY_DIR / cut.companion_path.name, typed_keys(cut_id, word))
        built.append((word, cut, join, join.crop(at, size), key))

    def joins_html(copy: dict) -> str:
        return "".join(
            f'<figure class="join"><div class="join-art">'
            f'<div class="join-word" lang="mn-Mong">{join.whole(box, word)}</div>'
            f'<div class="join-zoom"><span>{join.svg("before", box, copy["joins_1998"])}<i>{copy["joins_1998"]}</i></span>'
            f'<span>{join.svg("after", box, copy["joins_now"])}<i>{copy["joins_now"]}</i></span></div></div>'
            f"<figcaption><b>{cut.name}</b> {copy[key]}</figcaption></figure>"
            for word, cut, join, box, key in built
        )

    files["joins"] = joins_html
    gold = goldens()
    all_copy = {lang: tomllib.loads((HERE / "copy" / f"{lang}.toml").read_text()) for lang in LANGS}
    for lang, copy in all_copy.items():
        target = OUT / copy["path"].strip("/") / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page(lang, copy, all_copy, gold, files))

    og_image(gold)
    if not (HERE / "node_modules").exists():
        subprocess.run(["bun", "install"], cwd=HERE, check=True)
    subprocess.run(["bun", "run", "bundle"], cwd=HERE, check=True)
    (OUT / "favicon.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="6" fill="#1f43d6"/>'
        '<text x="16" y="21" text-anchor="middle" font-family="Helvetica,Arial,sans-serif" font-size="13" font-weight="bold" fill="#fff">CMs</text></svg>'
    )
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n")
    urls = "".join(f"<url><loc>{SITE}{c['path']}</loc></url>" for c in all_copy.values())
    (OUT / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n'
    )
    (OUT / "_headers").write_text(
        "/fonts/*\n  Cache-Control: public, max-age=31536000, immutable\n  Access-Control-Allow-Origin: *\n"
        "/download/*\n  Cache-Control: public, max-age=3600\n"
    )
    print(f"wrote {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
