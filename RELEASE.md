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

- [x] The five known-failure goldens: nobsi, front, jišiγsen and üjeγdel settled; pwptid waits
      for the owner on /goldens.
- [ ] A licence for the tooling code (`cmsr/`, `editor/`), or a decision to leave it unlicensed.
- [ ] A home for the news corpora, so the goldens tools work on another machine.

## After a release

- [ ] Draw the left-out letters. A freehand birga was tried and rejected; it needs a better source.
- [ ] Smooth Urga's arch + ē join (`cms.w.@arch-*` in `drawings/CMSUG.ufo`): accepted for 1.0 as it is,
      the owner finds it "slapped on" and may retry another day (2026-11-11).
- [ ] Ulaanbaatar's mid-word pē, fē, gē and kē are still the Alpha 5 stand-ins (bē's tail on each
      arch); the owner prefers them for now. Huree's were rebuilt from the owner's halves; Urga's
      come from the owner's w. k2ē waits for k2.
- [ ] Huree p + t and ng + t, Urga pē + p: small gaps left (see docs/feedback.md).
- [ ] angg-a like angq-a: needs `drop` on rules.
- [ ] Smooth the arch + r joins (`cmsr.R.medi.after.@arch-*`) in every cut. The owner's drawings
      fix the extra spine; the curves could be smoother, which needs a type designer's hand.
      Most readers won't notice (2026-11-11).

## Ideas

- [x] A legacy-keyed companion, "CMs Ulaanbaatar Revived" (no Gege prefix, no Unicode): built
      by `cmsr build` into `dist/CMs<Cut>Revived-Regular.ttf` (2026-11-12), see docs/decisions.md.
- [x] Released the companion as `legacy-v1.0.0` (2026-11-12), files in `releases/legacy-1.0.0/`.
