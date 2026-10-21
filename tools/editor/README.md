# CMs ↔ Unicode — form elicitation editor

A local page for mapping the 1998 CMs keyboard encoding onto Unicode written
forms. The reference pane shows one Hudum form (letter × joining position ×
FVS variant) taken from Noto Sans Mongolian by exact glyph name; the CMs pane
shows what a typed legacy key sequence actually draws, using the original
outlines. You judge the pair, and the judgement is written to disk as you go.

Nothing in this tool modifies the 1998 fonts. It only reads them.

## Run

```sh
python3 tools/editor/server.py --open
```

No dependencies beyond Python 3 and the standard library. The page is served
at `http://127.0.0.1:8787/` (the next free port if that one is taken).

To regenerate the reference data after changing the vendored data or the
reference font:

```sh
python3 tools/editor/generate_data.py
```

That needs `fonttools` (`pip install fonttools`).

## What is on screen

- **Reference** — one form, drawn from Noto Sans Mongolian. Below it: the
  Unicode character name, joining position, written units, GB/T reference,
  conditions, and the code points as chips. Invisible characters (MVS, FVS,
  NNBSP) are shown as red `U+180B`-style chips, never as bare characters.
- **CMs** — type the 1998 keys. The run is laid out exactly as the font lays
  it out: glyphs advance by their own widths, then the run is turned 90°
  clockwise so the pre-rotated outlines stand upright and read top to bottom.
- **Verdicts** — `Same form` (↵), `Variant`, `Component`, `Not in CMs`, `Skip`.
  `Tab` / `Shift+Tab` move without judging. `Esc` clears the keys.
- **Free mode** — arbitrary Unicode text against arbitrary CMs keys, for
  words and combinations. `Save pair` records a word-level example.
- **Family** — Urga, Ulaanbaatar or Huree. The mapping is shared: switch cuts
  to check that the same keys draw the same form in each.

## Where the work goes

Every change is POSTed to the local server and written immediately:

| File | What |
|---|---|
| `state/state.json` | the whole editor state |
| `state/latest.md` | a readable digest: current form, last verdicts, progress, free pairs |
| `state/events.jsonl` | one line per save, for history |

`state/` is deliberately outside version control. `latest.md` is the file to
read when you want to know what has happened without opening the page.

## Data

| File | What |
|---|---|
| `data/forms.json` | 216 Hudum forms for `MNG` (140 default + FVS variants), each with written units, GB/T reference, conditions, and an SVG path from Noto |
| `data/cms-glyphs.json` | every glyph the three CMs cuts map to ASCII, as SVG paths normalised to a 1000-unit em with the baseline at y=1000 |
| `vendor/mongfontbuilder/` | the specification data (`variants.json`, `aliases.json`, `locales.json`) from [mongfontbuilder](https://github.com/Kushim-Jiang/mongolian), MIT |
| `fonts/` | Noto Sans Mongolian (OFL 1.1), the reference face |

The reference outlines are addressed by name — `uni1820.AA.init` — which is
the written units of the variant plus its joining position, the way Noto names
its glyphs. All 216 variants the data lists for Hudum in `MNG` resolve this
way.

## Why the outlines are paths, not a live font

The 1998 glyphs are drawn rotated for a horizontal text engine, and their
advance widths are the only positioning information in the font. Rendering
them as text in the browser would leave the rotation and the run direction to
CSS; rendering them as paths lets the tool lay the run out exactly, which is
what the pixel-for-pixel comparison with the old font will need later.

All CMs outlines here come from the **regular** cuts (`CMSUG.TTF`,
`CMSUB.TTF`, `CMSHR.TTF`), not the `*DP` letterpress cuts. The DP cuts are a
different drawing, not a different encoding.

## First-run checks

- The page starts on the first unconfirmed default form.
- `Same form` with an empty CMs box is allowed but recorded as an empty key
  sequence — useful for "this form does not exist", though `Not in CMs` says
  it better.
- If the server is stopped, the page keeps working but says
  `not saved — is server.py running?` and nothing reaches disk.
