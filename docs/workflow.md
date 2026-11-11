# How the work is done

## The loop

1. Change the mapping (`mapping/pieces.toml`, by hand or in the editor) or a drawing
   (`drawings/<CUT>.ufo`, in Fontra). Never edit `dist/` or `cms/`.
2. `uv run cmsr check --cut all`: builds all three cuts, runs the shaping suites and the
   goldens, and loads the editor data. Any line other than the expected ones is a regression.
3. Look at real words set vertically, in the editor or on the specimen page, before calling
   a join done.

## Editor

`uv run cmsr editor --open` serves http://localhost:8787 (`--port` to change it).

Restart it after any change to `cmsr/` (the mapping model, the build): a server started on
older code writes the mapping back without what it does not know. On 2026-11-11 a save
from a stale server dropped every `before` rule.

- `/`: every piece, its keys per cut, live shaping. Edits are written back to
  `mapping/pieces.toml`; it rewrites the file and keeps only its own header comment.
- `/goldens`: words and the CMs keys that typed them. Confirm when the build draws the
  word as CMs did, or mark "differs on purpose" (status `fixed`, which pins a snapshot of
  the drawing per cut). Only the owner presses these.
- `/specimen`: all cuts setting real text side by side.

## Goldens

`mapping/goldens.toml`: `pending` (keys proposed), `ok` (confirmed), `fixed` (differs on
purpose). `cmsr check` holds every build to the confirmed ones.

- `uv run cmsr goldens` prints how much of real text the confirmed goldens check.
- `uv run cmsr goldens --add 10` adds ten pending words, each covering joins no golden checks
  yet. It needs the corpora (README).

## Drawings (Fontra)

New or fixed glyphs live in `drawings/<CUT>.ufo` (CMSUB Ulaanbaatar, CMSUG Urga, CMSHR
Huree). The owner uses Fontra Pak, which serves on http://localhost:8000. Its view state goes
in the URL fragment as base64 of zlib-compressed JSON (with the zlib header; raw deflate and
`?text=` open an empty canvas):

```python
import base64, json, urllib.parse, zlib
state = {"location": {}, "text": "/_BW.medi /_BW.init",
         "selectedGlyph": {"lineIndex": 0, "glyphIndex": 0, "isEditing": True}}
url = ("http://localhost:8000/editor.html?project=" + urllib.parse.quote(abs_ufo_path, safe="")
       + "#" + base64.b64encode(zlib.compress(json.dumps(state).encode(), 9)).decode())
```

Each open is a new tab: close older ones so a stale tab doesn't save over newer files.
Reference outlines can sit in extra UFO layers, which the build ignores.

A drawn glyph named after a target (`_BW.medi`) replaces its keys. A drawn join rule is
named `cmsr.<piece>.after.<piece or @group>`. It is used only once an `after` rule for that
pair exists in the mapping.

## Missing glyphs

A target with no keys, marks or drawing is built as a box so that mongfontbuilder can
compose the shaping, then cut out of the compiled font with every glyph drawn from it and
every rule that reaches it (`_leave_out` in `cmsr/build.py`). The check skips the suite
cases for those letters and reports how many it skipped. When a letter is drawn, it comes
back on its own, and so do its cases.

## Releasing

```sh
uv run cmsr check --cut all
uv run cmsr release "Alpha 6" --final-name   # → releases/alpha-6/ with NOTES.md
git add releases/alpha-6 && git commit -m "Alpha 6: …"
git tag alpha-6 && git push origin main alpha-6
gh release create alpha-6 --repo gege-mn/cms-revived --prerelease \
  --title "Gege CMs Revived Alpha 6" --notes-file <notes.md> releases/alpha-6/*.ttf
```

Without `--final-name` the label goes into the family name instead, so the snapshot installs
beside other builds (how Alphas 1–4 were made). Release notes go first to dEgi's credit and the
terms (free for personal use, not to be sold), then what is left out and what is known wrong.
See the Alpha 5 release for the shape. Bump `VERSION` in `cmsr/config.py` for a version
that should sort after the last one.

## Checking against the reference

`reference/NotoSansMongolian-Regular.ttf` (Noto v3, the new model) is for comparison only.
When a shaping case is in doubt, shape the same code points in both fonts with uharfbuzz
and compare the written units. Write invisible characters (NNBSP U+202F, MVS U+180E,
FVS U+180B–180D, U+180F) as `\u` escapes, never as literals.
