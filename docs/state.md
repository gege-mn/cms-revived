# Where it stands

As of **1.0.0** (2026-11-11), the first public release: tag `v1.0.0`, files also in
`releases/1.0.0/`. Alpha 5 (2026-11-03) was in production use before it; note anything seen
in use in [feedback.md](feedback.md).

## The fonts

| | |
|---|---|
| Families | Gege CMs Ulaanbaatar Revived, Gege CMs Urga Revived, Gege CMs Huree Revived |
| PostScript | `GegeCMsUlaanbaatarRevived-Regular` (and Urga, Huree) |
| Version | `Version 1.000; 1.0.0; dEgi 1998, Unicode rework 2026` |
| Vendor URL | https://github.com/gege-mn/cms-revived |
| Shaping (`cmsr check`) | 3548/3553 per cut: the 5 failures are the expected EAC cases ([decisions.md](decisions.md#shaping-test)); 136 cases skipped for the left-out letters |
| Goldens | 103/103 confirmed pass in every cut, none pending |
| Mapping | pieces and punctuation: ok 111, new 9 |

## The companion: legacy-v1.0.0 (2026-11-12)

CMs Ulaanbaatar Revived, CMs Urga Revived, CMs Huree Revived: dEgi's keyboard with the joins of
the Unicode build as `liga`/`calt` substitutions, built into `dist/` next to the Gege fonts. With dp cuts (CMs Ulaanbaatar dp Revived…), mirrored for
letterpress like dEgi's. Released as tag `legacy-v1.0.0`, files in `releases/legacy-1.0.0/`; v1.0.0 stays the "latest" GitHub release.
Draws 99.84–99.87% of the corpora (by frequency) as the Unicode build, every golden, and 1998
exactly with features off. On words held out of its learning, 99.1%.

## Since Alpha 5

The joins, drawn or composed from dEgi's outlines, with every rule in
[decisions.md](decisions.md):

- Arch + d/t, r, s per arch family; Huree's b + g, g + g, g + b and ng.
- The first of two arches small; arch + arch spacing from dEgi's reach.
- Suffix initials without the leading nirugu (Ulaanbaatar, Urga); final hö/hü.
- Arch + ē remade, final ē after an arch, wa after an arch in ē's shape, p after wa/pē at
  CMs spacing; final t with the mini tail.
- No gaps between letters: Huree's medial arches and looped t lead in with a nirugu; a scan
  of the corpora finds no neighbours that fail to touch.
- angq-a's custom final; the -iyan cut.

## Known gaps in 1.0.0

- **Left out** (nothing draws them yet): k2 (`K2.init/medi/fina`), zhi (`Rh.init/medi/fina`),
  `Zr.init`, `Sz.fina`, the birga U+1800.
- **Small gaps left, rare:** Huree p + t (8 words) and ng + t (6 words).
- angg-a is not yet drawn like angq-a; Urga's arch + ē join could be smoother; Ulaanbaatar's
  mid-word pē, fē, gē, kē are the Alpha 5 stand-ins. See [RELEASE.md](../RELEASE.md).

## Coverage

Confirmed goldens check 99% of the glyphs and about 98% of the joins in real text (by
frequency, over the two news corpora). The 109 `auto` ligatures are not glyphs: the build
shapes those words from their parts, so they are reviewed through the joins the goldens
check. `uv run cmsr goldens` prints the current share.

## Open

The to-do list is [RELEASE.md](../RELEASE.md). Besides it:

- A licence for the tooling code (`cmsr/`, `editor/`). Fonts keep NOTICE.md's terms.
- The news corpora (`reference/corpora/`) exist only on the original machine; see
  [README](../README.md#corpora).
