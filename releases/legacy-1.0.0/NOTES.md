# CMs Revived 1.0.0 (legacy keyboard)

Built 2026-11-12 on commit 1aa86d4 plus the companion builder (cmsr/companion.py), from the
Gege CMs Revived 1.0.0 mapping. Version 1.000.

The CMs Ulaanbaatar, Urga and Huree fonts are dEgi's 1998 files: the same 96 characters (ASCII and
U+2010), and his glyphs, metrics and hinting untouched. To these they add the joins of
Gege CMs Revived 1.0.0 as `liga`/`calt` substitutions on the keys CMs typed. With
ligatures off they draw exactly like 1998.

| Font | Rules | Corpora drawn as the Unicode build (by frequency) | Goldens | Features off = 1998 |
| --- | --- | --- | --- | --- |
| `CMsUlaanbaatarRevived-Regular.ttf` | 314 | 99.84% | all | yes |
| `CMsUrgaRevived-Regular.ttf` | 206 | 99.87% | all | yes |
| `CMsHureeRevived-Regular.ttf` | 303 | 99.85% | all | yes |

On words held out of the learning: 99.1%.

## dp cuts (added 2026-11-12)

`CMsUlaanbaatardpRevived-Regular.ttf`, `CMsUrgadpRevived-Regular.ttf`, `CMsHureedpRevived-Regular.ttf`:
dEgi's dp files (mirrored for letterpress) as the base, the same rules, and the added glyphs flipped
as he flipped his (y → 800 − y). Built from the regular files above; with features off they are his
dp fonts exactly.
