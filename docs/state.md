# Where it stands

As of **Alpha 5** (2026-11-03), released as a GitHub prerelease:
https://github.com/gege-mn/cms-revived/releases/tag/alpha-5 (tag `alpha-5`; the files are
also in `releases/alpha-5/`). The owner is using it in production and will come back for
the next version. Note anything seen in use in [feedback.md](feedback.md).

## The fonts

| | |
|---|---|
| Families | Gege CMs Ulaanbaatar Revived, Gege CMs Urga Revived, Gege CMs Huree Revived |
| PostScript | `GegeCMsUlaanbaatarRevived-Regular` (and Urga, Huree) |
| Version | `Version 0.100; Alpha 5; dEgi 1998, Unicode rework 2026` |
| Vendor URL | https://github.com/gege-mn/cms-revived |
| Shaping (`cmsr check`) | 3548/3553 per cut: the 5 failures are the expected EAC cases ([decisions.md](decisions.md#shaping-test)); 136 cases skipped for the left-out letters |
| Goldens | 96/96 confirmed pass in every cut; 5 pending, accepted as known failures |
| Mapping | pieces and punctuation: ok 111, new 9 |

## Known gaps in Alpha 5

- **Left out** (nothing draws them yet): k2 (`K2.init/medi/fina`), zhi (`Rh.init/medi/fina`),
  `Zr.init`, `Sz.fina`, the birga U+1800.
- **Known failures** (goldens left pending, drawn wrong):
  - nobsi: the b + s join. The owner plans to draw `cmsr.S.medi.after.@arch` (or
    `.after.B.medi`) in Fontra.
  - front: arch + r. The owner plans to draw `cmsr.R.medi.after.@arch`.
  - pwptid: keys `pwpDidA`. In CMs `p` is both P.init and P.medi and `P` is the pu ligature.
    The owner said it "still has problems". Once a stray confirmed `K` was saved for it from
    the goldens page; cause not looked into.
  - jišiγsen: never reviewed.
  - üjeγdel: one of the 19 coverage-picked words, not confirmed.
  A hand-drawn rule glyph is only used once a matching `after` rule exists in the mapping.
- **Stand-ins:** the arch + ē family (`BW`, `PW`, `FW`, `KW`, `GW`, `GxW`, init and medi) is
  drawn as stand-ins. bē itself was hand-edited and is fine.

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
