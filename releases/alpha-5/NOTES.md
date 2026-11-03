# Gege CMs Revived Alpha 5

Built 2026-11-03 from commit 502f897. A snapshot of the work, not a release.

Pieces and punctuation: new 9, ok 111.

## Gege CMs Ulaanbaatar Revived

- `GegeCMsUlaanbaatarRevived-Regular.ttf`
- shaping: 3548/3553 cases pass
- goldens: 96/96 confirmed match
- left out (not drawn yet): 9 (Sz.fina, K2.init, K2.medi, K2.fina, Rh.init, Rh.medi, Rh.fina, Zr.init, U+1800)

## Gege CMs Urga Revived

- `GegeCMsUrgaRevived-Regular.ttf`
- shaping: 3548/3553 cases pass
- goldens: 96/96 confirmed match
- left out (not drawn yet): 9 (Sz.fina, K2.init, K2.medi, K2.fina, Rh.init, Rh.medi, Rh.fina, Zr.init, U+1800)

## Gege CMs Huree Revived

- `GegeCMsHureeRevived-Regular.ttf`
- shaping: 3548/3553 cases pass
- goldens: 96/96 confirmed match
- left out (not drawn yet): 9 (Sz.fina, K2.init, K2.medi, K2.fina, Rh.init, Rh.medi, Rh.fina, Zr.init, U+1800)

## Known failures

Five words are drawn wrong in this build and accepted as known failures for Alpha 5:
nobsi, front, pwptid, jišiγsen and üjeγdel (b+s and arch+r joins among them). They stay
pending in `mapping/goldens.toml`.
