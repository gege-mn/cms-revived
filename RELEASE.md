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
- [ ] The `auto` ligatures reviewed, through the goldens.

## After a release

- [ ] Draw the left-out letters. A freehand birga was tried and rejected; it needs a better source.
- [ ] Remake the arch + ē family (`BW`, `PW`, `FW`, `KW`, `GW`, `GxW`, initial and medial) in every
      cut. The current drawings are stand-ins: dEgi's b and w overlapped, the others carrying bē's
      tail on their own arch. Huree's gē and hē need their own shape for its smaller arch;
      k2ē waits for k2. The `w` and `bu` layers in `drawings/<cut>.ufo` are references for it.
