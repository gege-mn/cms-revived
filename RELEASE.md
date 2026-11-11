# Before a public release

Snapshots (`cmsr release "<label>"`) can go out at any time. dEgi has not been reached, so
releases go out under the good-faith commitments in [NOTICE.md](NOTICE.md). A public release
waits for:

- [x] bē (`BW.init`, `BW.medi`) hand-edited in every cut: dEgi's b and w overlapped, u's edge
      carrying b's arm through the stem in Ulaanbaatar and Urga.
- [x] The glyphs no 1998 key draws are left out of v1: k2 (`K2.*`), zhi (`Rh.*`), `Zr.init`,
      s final FVS1 (`Sz.fina`) and the birga (U+1800). The build cuts them and everything drawn
      from them, so the text falls back to the plain form or to another font. The ellipsis and
      four dots are done, built from dEgi's own dots.
- [x] Published at https://github.com/gege-mn/cms-revived, also the fonts' vendor URL.
- [x] The `auto` ligatures reviewed, through the goldens: 96 confirmed. Five are known
      failures, accepted for Alpha 5 and left pending: nobsi, front (rule glyphs to draw),
      pwptid, jišiγsen, üjeγdel.

## Next version

Alpha 5 is in production use. Start from what [docs/feedback.md](docs/feedback.md) collected.

- [ ] Fix the five known-failure goldens (see [docs/state.md](docs/state.md)): nobsi and front
      need the owner's rule glyphs (`cmsr.S.medi.after.@arch`, `cmsr.R.medi.after.@arch`).
- [ ] A licence for the tooling code (`cmsr/`, `editor/`), or a decision to leave it unlicensed.
- [ ] A home for the news corpora, so the goldens tools work on another machine.

## After a release

- [ ] Draw the left-out letters. A freehand birga was tried and rejected; it needs a better source.
- [ ] Smooth Urga's arch + ē join (`cms.w.@arch-*` in `drawings/CMSUG.ufo`): accepted for 1.0 as it is,
      the owner finds it "slapped on" and may retry another day (2026-11-11).
- [ ] Remake the arch + ē family (`BW`, `PW`, `FW`, `KW`, `GW`, `GxW`, initial and medial) in every
      cut. The current drawings are stand-ins: dEgi's b and w overlapped, the others carrying bē's
      tail on their own arch. Huree's gē and hē need their own shape for its smaller arch;
      k2ē waits for k2. The `w` and `bu` layers in `drawings/<cut>.ufo` are references for it.
- [ ] Smooth the arch + r joins (`cmsr.R.medi.after.@arch-*`) in every cut. The owner's drawings
      fix the extra spine; the curves could be smoother, which needs a type designer's hand.
      Most readers won't notice (2026-11-11).

## Ideas

- [ ] A legacy-keyed companion, "CMs Ulaanbaatar Revived" (no Gege prefix, no Unicode): dEgi's
      ASCII keys in the cmap as in 1998, his glyphs with the rework's fixes, and contextual
      substitutions that turn the key sequences CMs typed into the fixed joins (`ek(` → the
      custom angq-a glyph, an arch key + `d` → the drawn d). Old documents typed the CMs way
      would render fixed. The goldens' typed keys become its test: each must shape like the
      Unicode build. Raised 2026-11-11; not started.
