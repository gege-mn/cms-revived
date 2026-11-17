# CMs Revived 1.0.1 (legacy keyboard)

Built 2026-11-17 alongside Gege CMs Revived 1.0.1, from its mapping. Version 1.001.

The CMs Ulaanbaatar, Urga and Huree fonts are dEgi's 1998 files: the same 96 characters (ASCII and
U+2010), and his glyphs, metrics and hinting untouched. To these they add the joins of
Gege CMs Revived 1.0.1 as `liga`/`calt` substitutions on the keys CMs typed, so the 1.0.1 fixes
(see [CHANGELOG.md](../../CHANGELOG.md)) reach old documents too. With ligatures off they draw
exactly like 1998.

| Font | Rules | Corpora drawn as the Unicode build (by frequency) | Goldens | Features off = 1998 |
| --- | --- | --- | --- | --- |
| `CMsUlaanbaatarRevived-Regular.ttf` | 314 | 99.84% | all | yes |
| `CMsUrgaRevived-Regular.ttf` | 206 | 99.87% | all | yes |
| `CMsHureeRevived-Regular.ttf` | 320 | 99.85% | all | yes |

## dp cuts

`CMsUlaanbaatardpRevived-Regular.ttf`, `CMsUrgadpRevived-Regular.ttf`, `CMsHureedpRevived-Regular.ttf`:
dEgi's dp files (mirrored for letterpress) as the base, the same rules, and the added glyphs flipped
as he flipped his (y → 800 − y). With features off they are his dp fonts exactly.
