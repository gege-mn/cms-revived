# Decisions

Settled calls, with the reason for each. They hold until the owner (Batmend Ganbaatar)
changes them. Dates are when each was decided.

## Name and credit

- **Gege CMs Ulaanbaatar Revived** (also Gege CMs Urga Revived, Gege CMs Huree Revived)
  (2026-11-03). L'Atelier Gege prefixes everything it publishes with "Gege". dEgi's own
  family names stay in the middle; "Revived" keeps the rework from being mistaken for his
  1998 fonts. Prefix and suffix are `FAMILY_PREFIX` and `FAMILY_SUFFIX` in `cmsr/config.py`.
- dEgi is named first in every field, the rework second. All names and metadata live in
  `cmsr/config.py` and nowhere else.
- Alphas from Alpha 5 on carry the final family name; the label ("Alpha 5") goes in the
  version string (`cmsr release "Alpha 5" --final-name`). A later build therefore installs
  over an earlier one. Alphas 1–4 had the label in the family name.

## Permission and terms

- dEgi has not been reached. His permission is **not** a release gate: releases go out
  under the good-faith commitments in [NOTICE.md](../NOTICE.md) (free for personal use,
  never sold, dEgi credited first, any request of his honoured).
- The fonts are not open source and cannot be: the outlines are dEgi's.
- The repository is public at https://github.com/gege-mn/cms-revived (2026-11-03),
  **including dEgi's 1998 TTFs** in `cms/`, under the same good-faith terms. They come out
  if he asks.
- The tooling code (`cmsr/`, `editor/`) has no licence yet, so it is all rights reserved.
  Open question, see [state.md](state.md).

## Scope

- Hudum (locale MNG) only. The `*DP.TTF` cuts in `cms/` are out of scope.
- **The legacy-keyed companion, CMs Ulaanbaatar Revived** (also Urga, Huree; no Gege prefix)
  (2026-11-12, owner's call). dEgi's 1998 file as the base, his keys at their ASCII places,
  his glyphs, metrics and hinting untouched; the Unicode build's joins added as `liga` and
  `calt` substitutions on the key sequences CMs typed. With ligatures off it is his 1998 font
  (Word's default), so old documents can switch fonts at once. The substitutions are learned
  from the corpora and goldens (`cmsr/companion.py`), never listed by hand; `cmsr check` holds
  it to 99.8% of the corpora (by frequency) drawn as the Unicode build, every golden, and
  features off identical to 1998. What the keys cannot tell apart (wa and ē after an arch,
  typos typed like real words) goes to the more common word.
- **Unicode only** (2026-10-22), for the Gege fonts. The 1998 keys are not encoded at their ASCII positions:
  three keys collide with Unicode punctuation (`!` is final k, `(` and `)` are the Hx
  finals) and Latin text would render as pieces. Old documents typed the CMs way still
  need dEgi's originals.
- **v1 ships without the five letters no 1998 key draws** (2026-10-23): k2 (`K2.*`), zhi
  (`Rh.*`), `Zr.init`, final s with FVS1 (`Sz.fina`) and the birga (U+1800). The build cuts
  them, and everything drawn from them, out of the compiled font. Text with them falls back
  to the plain form (s + FVS1 shows the plain final s) or to another font (k2, zhi, birga
  are not in the cmap).

## Glyph shapes

- **Shapes come from dEgi's own outlines.** Compose from his keys or contours. Freehand or
  "derived" drawing was tried and rejected: every glyph built for the five missing letters
  (2026-10-23), a freehand birga, and smoothed joins. The missing letters wait for a human:
  the owner, a type designer, or dEgi.
- Joins are fixed through the mapping (keys, `shift`, `trim`, `marks`, `after` rules) with
  spacing **measured from dEgi's teeth per cut**, never picked by eye. Measured gap between
  two teeth: Ulaanbaatar 152, Urga 154, Huree 41 units. Keep each rule to the case reported
  and key it on the exact preceding form (a rule after `O.medi` also caught plain o; keying
  on `BO.medi` fixed it). Never run a stem under an arch: it reads as KHA's tick.
- Joins the owner finds bad in shape they draw themselves in Fontra, as rule glyphs
  `cmsr.<piece>.after.<piece or @group>` in `drawings/<cut>.ufo`.
- Arch + medial d/t is drawn per arch family, not per arch (2026-11-11): `@arch-g` (g),
  `@arch-bpf` (b, p, f), `@arch-k` (k). It need not be seamless: the arch's closing slope
  and the long strokes (shilbe, medial d) differ optically, and other fonts leave that join
  as it is.
- The same per-family drawings carry arch + r and arch + s (2026-11-11). Huree's g after b/p/f
  and after g, and its b after g, are drawn by the owner too.
- **The first of two arches is small** (2026-11-11). When an arch is followed by another
  arch, every arch but the last takes its small form: g uses dEgi's `h` (the g inside ng
  too), b/p/f/k their own drawings (`cmsr.<piece>.before.@arch`). Huree's arches are all
  small already. Arch + arch spacing is measured as ink start + dEgi's reach (the distance
  from his key's ink to the next letter). b, p and f drawn by eye share one advance.
- **Suffix initials have no leading nirugu after the gap** (2026-11-11), in Ulaanbaatar and
  Urga: -i (`I.isol`), -iyan/-iyar (`I.init`), -yin/-yi (`u1836.I.init`), -du/-dür
  (`D.init`), -u/-ün. Huree is left as dEgi drew it (owner's call). Final hö/hü drop the
  trailing nirugu (`GO.fina`).
- **Arch + ē** (2026-11-11): mid-word, Ulaanbaatar and Huree keep the Alpha 5 glyphs (the
  owner's preference); Urga uses the owner's w per arch family (`cms.w.@arch-*`; p and f
  are b's moved down by how much later their stems end). Word-final ē after an arch is the
  mid-word glyph split in two, overlapping 12 units: the arch half
  (`cmsr.<arch>.before.W.fina`) and the ē half with dEgi's short tail `A`
  (`cmsr.W.fina.after.<arch>`).
- **No gaps between letters** (2026-11-11). Huree's medial b/p/f and their ē glyphs lead in
  with the owner's nirugu from `_G.medi`; Huree's looped t sits 8 closer. Checked by a
  scan of the corpora for neighbours whose ink does not touch.
- **wa after an arch takes ē's shape** (2026-11-11): CMs typed wa and ē with the same `w`, so
  wa after b/p/f/g/k uses the halves of the arch + ē glyph (`cmsr.<arch>.before.W.medi`,
  `cmsr.W.medi.after.<arch>`). Word-initial wa and ē keep their own shapes. A p after wa or
  pē sits where CMs typed it (`pwp`), dEgi's stem filling up to it.
- **Final t ends with dEgi's mini tail `A`** (2026-11-11), as final ē does. Huree's looped
  t (medial and final) leads in with a nirugu cut from dEgi's stem key, up to where the loop
  starts.
- Never run a stem under an arch, even to close a gap: tried for Urga's ng + p/f and
  rejected; the owner drew those joins instead.
- Before regenerating anything the owner edited by hand, back it up and say which edits
  would be replaced. (Urga's pē and fē were once overwritten this way and had to be
  restored.)

## Review

- **Only the owner confirms.** `ok` / `fixed` in `mapping/goldens.toml` and `ok` in
  `mapping/pieces.toml` come only from the owner's own clicks in the editor. Tools and
  agents fill in keys and leave goldens `pending`, mapping entries `draft`.
- Alpha 5 accepts five goldens as known failures, left `pending` with a note (2026-11-03):
  nobsi, front, pwptid, jišiγsen, üjeγdel.

## Shaping test

- The fonts follow UTN #57 / Unicode 16 (mongfontbuilder's model). Five cases of China's
  EAC suite (`eac-hudum > XIM11-39, -40, -41, -46, -1012`) answer differently from that
  model and are expected to fail, as in mongfontbuilder's own runner. Three treat NNBSP as
  the pre-2024 suffix connector; two use EAC's FVS table where it differs from UTN's.
  On all five the fonts shape exactly like Noto Sans Mongolian v3. Not bugs, not fixable
  without breaking the model. Typed text with NNBSP suffixes (what keyboards still emit)
  joins the same as MVS.
