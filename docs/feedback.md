# Feedback from use

Problems and wishes seen while using the fonts in production, for the next version. One
line each: the word or text (romanized and in bichig), the cut, what looks wrong, and where
it was seen. Add `goldens` candidates here too; they go into `mapping/goldens.toml` as
`pending` when work resumes.

## Alpha 5

- angq-a (ᠠᠩᠬ᠎ᠠ), all cuts: the q after ng drew as one bare tooth with no tail (`AGH.fina`
  keys `ekE`). Now `ekE(` with the `(`'s first tooth dropped (E is the tooth on the arch),
  confirmed by the owner (2026-11-11).
- angg-a (ᠠᠩᠭ᠎ᠠ, 984 times in the corpora), all cuts: wanted like angq-a, `ekE)` with the
  first tooth dropped. The pinned mongfontbuilder has no `AGHx.fina` (Noto v3 does), so the
  text is `AG.medi` + `Hx.fina`; the fix would be an `after` rule on `Hx.fina` after
  `AG.medi`, which needs `drop` on rules.
- Letter + arch, Huree only: a hairline gap on the tooth side of the stem where any letter
  meets a medial arch (seen in tngri at large size, also in dEgi's font). A scan of the corpora
  (2026-11-11) found 39 letter + arch pairs, none in Ulaanbaatar or Urga: up to 18–20 units
  before g's arch (a, i, l, m, r, o, d before g; 66k for a + g alone), about 11–13 before b's,
  2–7 before p and f. Initial arches are not affected. Fixed (2026-11-11): the owner's leading
  nirugu on medial g, then b/p/f and the ē glyphs; a corpus scan finds no gap left.
- cag-iyan (ᠴᠠᠭ ᠢᠶᠠᠨ), Ulaanbaatar, on the web: the top of the suffix's i looked cut off. The
  start trim of `I.init` sliced the front of the tooth; the cut now stops where the tooth
  leaves the stem. Urga's -iyan, -yin and -yi were then drawn without the leading nirugu.

## Toward 1.0 (2026-11-11)

- argentin (ᠠᠷᠭᠧᠨ᠋ᠲ᠋ᠢᠨ), Huree: the looped t never touched the letter before (4 units short,
  8 after n). Huree's t now sits 8 closer.
- Left open, rare: Huree p + t (8 words, 16 units) and ng + t (6 words, 4 units); Urga pē + p
  (pēptid, the pending pwptid golden).
