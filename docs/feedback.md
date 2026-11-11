# Feedback from use

Problems and wishes seen while using the fonts in production, for the next version. One
line each: the word or text (romanized and in bichig), the cut, what looks wrong, and where
it was seen. Add `goldens` candidates here too; they go into `mapping/goldens.toml` as
`pending` when work resumes.

## Alpha 5

- angq-a (ᠠᠩᠬ᠎ᠠ), all cuts: the q after ng drew as one bare tooth with no tail (`AGH.fina`
  keys `ekE`). Now `ekE(` with the `(`'s first tooth dropped (E is the tooth on the arch),
  left as draft; golden added as pending.
- angg-a (ᠠᠩᠭ᠎ᠠ, 984 times in the corpora), all cuts: wanted like angq-a, `ekE)` with the
  first tooth dropped. The pinned mongfontbuilder has no `AGHx.fina` (Noto v3 does), so the
  text is `AG.medi` + `Hx.fina`; the fix would be an `after` rule on `Hx.fina` after
  `AG.medi`, which needs `drop` on rules.
- Letter + arch, Huree only: a hairline gap on the tooth side of the stem where any letter
  meets a medial arch (seen in tngri at large size, also in dEgi's font). A scan of the corpora
  (2026-11-11) found 39 letter + arch pairs, none in Ulaanbaatar or Urga: up to 18–20 units
  before g's arch (a, i, l, m, r, o, d before g; 66k for a + g alone), about 11–13 before b's,
  2–7 before p and f. Initial arches are not affected. To fix after arch + r, joined only
  where needed.
- cag-iyan (ᠴᠠᠭ ᠢᠶᠠᠨ), Ulaanbaatar, on the web: the top of the suffix's i looked cut off. The
  start trim of `I.init` sliced the front of the tooth; the cut now stops where the tooth
  leaves the stem.
