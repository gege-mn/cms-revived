# Changelog

What changed in Gege CMs Revived (the Unicode fonts) and in CMs Revived (the legacy-keyed
companion), newest first. Every shape is dEgi's 1998 outline, or a fix composed from his
outlines and drawn by the owner in Fontra; nothing is drawn freehand. Each release's own build
report is `releases/<version>/NOTES.md`.

## 1.0.1 (2026-11-17)

Fixes to joins and letters seen after 1.0.0, most of them in Huree. Huree had gaps and nicks too
small to see at text size. 1.0.0's checks passed them, because most came straight from dEgi's
keys, and the goldens were only viewed small. 1.0.1 was checked again from scratch: every golden
viewed one at a time at screen height, all three cuts side by side, against 1998. The family
names are unchanged, so 1.0.1 installs over 1.0.0. Ulaanbaatar draws exactly as in 1.0.0; only
its version number changed.

### Huree

- **Tooth before b, f and g**: a nick where the tooth or lead-in stem meets b, f or g. dEgi's b
  key steps in from the stem's edge before its curve (in his `eb` too), and that step was in
  every Huree drawing with b, f and g, the bē, fē and gē ligatures, and their "before" rules (16
  glyphs: `_B.medi`, `_F.medi`, `_BW.medi`, `_FW.medi`, `_GW.medi`, `_GxW.medi`,
  `cmsr.B.medi.before.*`, `cmsr.F.medi.before.*`, `cmsr.G.medi.before.W.*`,
  `cmsr.Gx.medi.before.W.*`). The b's edge now runs straight from the stem into its curve.
  Seen in abdar-a (ᠠᠪᠳᠠᠷ᠎ᠠ).
- **ng + q/γ in the middle of a word**: a nick under the n tooth where the arch begins
  (`_AGH.medi`, `_AGHx.medi`). Seen in mongγol (ᠮᠣᠩᠭᠣᠯ).
- **Final ng + q** (angq-a, ᠠᠩᠬ᠎ᠠ): in 1.0.0 the q's tail sat 61 units back into the arch's
  closing and left a step on the back of the stem. Redrawn by the owner from the 1.0.0 outline
  (`_AGH.fina`), with the nick under the n tooth closed as in the medial form.
- **ts at the start of a word**: the loop was a separate contour that didn't touch the hook, in
  dEgi's key `}` too. The loop now joins the hook. This is drawn in the key itself
  (`cms.braceright`), so every initial and standalone ts gets it. Seen in cai (ᠼᠠᠢ).
- **z in the middle of a word**: the same separate loop, in dEgi's `[`, now joined
  (`cms.bracketleft`). Seen in aziy-a (ᠠᠽᠢᠶ᠎ᠠ).
- **z at the start of a word, and ts in the middle and at the end** (`{`, `]`): their loops
  reshaped to match (`cms.braceleft`, `cms.bracketright`). The same goes for final z, which is
  typed with `[`.
- **č after b**: a slight gap where b meets č, closed by moving č's stem in to meet b. This
  applies only after b (`cmsr.Ch.medi.after.B.medi`). Applied to every medial č, the same move
  left a step on the back of the stem after every other letter (a scan of the corpora caught it
  in about 14,000 words), so everywhere else č stays dEgi's. Seen in abčö (ᠠᠪᠴᠥ), tobčiy-a.
- **g after bü**: g's arch stood apart from bü's stem (`cmsr.G.medi.after.BO.medi`). Seen in
  ebüγe (ᠡᠪᠦᠭᠡ).
- **w + p**: a seam where w meets the p after it, closed (`cmsr.P.medi.after.W.medi`). The p and
  w before it were trimmed at the back where they overlapped
  (`cmsr.P.init.before.W.medi`, `cmsr.W.medi.after.P.init`). Seen in pwptid (ᠫᠸᠫᠲ᠋ᠢᠳ᠋).

### Urga

- **ng + γ in the middle of a word**: an extra stretch of stem (nirugu) between the arch and the
  tooth, removed (`_AGHx.medi`). Seen in mongγol (ᠮᠣᠩᠭᠣᠯ), on the homepage.
- **g after bü**: the stem stopped short of g's arch, leaving a gap inside the glyph; the stem
  now runs into the arch as in dEgi's typing (`cmsr.G.medi.after.BO.medi`). Seen in ebüγe
  (ᠡᠪᠦᠭᠡ).
- **w + p**: the same seam as Huree's, closed (`cmsr.P.medi.after.W.medi`). Seen in pwptid.

### The companion: CMs Revived legacy 1.0.1

CMs Ulaanbaatar, Urga and Huree Revived, and their dp cuts, rebuilt with the 1.0.1 joins. The
glyphs they add are the Unicode build's, so every fix above reaches old documents too. With
ligatures off they still draw exactly like dEgi's 1998 files.

### Checks

- Shaping: 3548/3553 cases pass per cut. The 5 failures are the expected cases where the EAC
  spec and the UTN model disagree; 136 cases are skipped for the letters left out.
- Goldens: 103/103 confirmed in every cut: 82 draw exactly what CMs typed, 21 differ on
  purpose. All 103 were reviewed at full size on 2026-11-17.
- A scan of the two news corpora covered every context of every glyph that changed since
  1.0.0. No word comes apart, and no change leaves new white at a join: what each glyph lost,
  it lost the same way in every word. Ulaanbaatar has no changed glyphs.

### Tooling (not in the fonts)

- **The goldens page** (`/goldens` in the editor) is a review. One golden at a time, in order,
  the three cuts side by side at screen height. Hold Space to see what the same keys drew in
  1998, in the same place.
  - **Looks right** stores the right status on its own: "matches CMs" when every cut draws
    exactly what the keys typed, "differs on purpose" otherwise. Before, two buttons asked you
    to choose, and a wrong choice failed the check.
  - **Something's wrong** flags the golden with a note.
  - Each verdict records the date in `mapping/goldens.toml` (`reviewed`, `flag`), so a pass can
    stop and resume. **Start a new pass** begins again from the first.
  - The list view stays, under **List**.
- **The homepage**, cms-revived.gege.mn (mn, en, fr), lives in `site/`.
  - Downloads.
  - The three cuts set vertically.
  - A typing pad that types in every cut at once, with the Standard keyboard by default.
  - A before-and-after of the joins against dEgi's 1998 fonts.
  - Web fonts any site can link: `https://cms-revived.gege.mn/css/cms-revived.css` loads the
    three cuts (woff2, with TTF for older browsers) from `/fonts/`, by version.
  - `bg:title`, `bg:description` and `bg:image` tags, so devter (gege-pub) shows the page's card in
    bichig. The bichig is in `site/bg.txt`.

## legacy 1.0.0 (2026-11-12)

The first release of the legacy-keyed companion: CMs Ulaanbaatar, Urga and Huree Revived.
- dEgi's 1998 files, with the same 96 characters and his glyphs, metrics and hinting
  untouched.
- The joins of Gege CMs Revived 1.0.0 added as `liga`/`calt` substitutions on the keys CMs
  typed, learned from the news corpora and the goldens. It draws 99.84–99.87% of the corpora
  (by frequency) as the Unicode build does, and 99.1% of words held out of the learning.
- With ligatures off, it draws exactly like 1998.
- dp cuts (CMs Ulaanbaatar dp Revived and the others), mirrored for letterpress as dEgi
  mirrored his.

## 1.0.0 (2026-11-11)

The first public release. The family names are the same as Alpha 5, so 1.0 installs over it.

- **Arch joins redrawn**: arch + d/t, r and s per arch family (g, b/p/f, k); Huree's b + g,
  g + g, g + b and ng.
- **The first of two arches is small**, as in handwriting (jangγi, idebkitei, öγbe).
- **Arch + ē remade**, with a proper word-final ē. wa after an arch takes ē's shape, and p and l
  after them are spaced as in CMs.
- **Suffixes** (Ulaanbaatar, Urga): -i, -iyan, -yin, -yi, -du/-dür and -u/-ün start without a
  stray leading stem; final hö/hü ends without a trailing one.
- **No gaps between letters**: Huree's hairline gaps before arches and its looped t are closed.
  Final t ends with the short tail.
- angq-a is drawn as one custom final; the top of the -iyan suffix is no longer cut off.
- Not drawn yet, and left out: k2, zhi, initial zra, final s with FVS1, and the birga. Text with
  them falls back to the plain form or to another font.

## Alphas (2026-10-22 to 2026-11-03)

Labelled snapshots, each installable beside the others.

- **Alpha 1**: all three cuts, mapped from dEgi's keys.
- **Alpha 2**: ts, z, po/fo/ko and the l after arches from dEgi's own keys; Ulaanbaatar's arches
  nudged; bē drawn; 52 goldens.
- **Alpha 3**: bē and the arch + ē family as stand-ins; i/j/y split at the start of a word.
- **Alpha 4**: the ellipsis and four dots, built from dEgi's dots.
- **Alpha 5**: the final names (Gege CMs … Revived). The letters no key draws are cut, and five
  goldens are accepted as known failures. Used in production until 1.0.0.
