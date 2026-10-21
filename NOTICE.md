# Notice

## The original fonts

`cms/CMSUG.TTF`, `cms/CMSUB.TTF`, `cms/CMSHR.TTF` and their `DP` counterparts
are the CMs font set: CMs Urga, CMs Ulaanbaatar and CMs Huree, made by **dEgi**
in 1998 with Macromedia Fontographer 4.1.

Copyright © 1998 dEgi. All rights reserved.

The outlines, the glyph set and the typeface design are dEgi's work. They are
kept in this repository as the source material of a preservation and
Unicode-compatibility project. The `DP` cuts are mirrored for letterpress and
are out of scope.

**No permission is granted** to copy, modify, redistribute, sublicense or sell
the font files, or works derived from them, until written permission is
obtained from the copyright holder. This is not an open-source licence, and
nothing in this repository should be read as granting one.

## Good faith

This rework exists to keep dEgi's typeface usable now that text is written in
Unicode, which the 1998 fonts cannot display. It is done in good faith, and
dEgi remains its author.

We have not yet been able to reach him. As of October 2026:

- We have written to an email address associated with him around 1999. We do
  not know whether it still reaches him.
- A university professor who knows of him has offered to help find him.
- We found, in the Internet Archive, a website that appears to have been his,
  online from the late 1990s until about 2003.

What we commit to:

- dEgi is named as the author of the typeface in every font built here, ahead
  of anyone who worked on the rework.
- The family names keep his: CMs Urga, CMs Ulaanbaatar and CMs Huree, with a
  suffix that keeps the rework from being confused with his 1998 fonts.
- Any request from dEgi, or from whoever holds his rights, will be honoured
  promptly: a change of credit, name or terms, or the withdrawal of the
  rework.

If you are dEgi, or know how to reach him, please write to
batmend@gege.mn.

## The rework

The Unicode rework of the CMs outlines and the tooling in this repository are
the work of Batmend Ganbaatar and L'Atelier Gege LLC, © 2026. dEgi remains the
author of the typeface and the original outlines. Glyphs drawn new for the
rework follow his design. Licensing of the rework will be decided with dEgi;
until then the same reservation applies.

## Third-party components

- **mongfontbuilder** (a build dependency, pinned in `pyproject.toml`): MIT
  License, © 2023–2026 Kushim Jiang and Liang Hai.
  <https://github.com/Kushim-Jiang/mongolian>. It supplies the Unicode shaping
  logic and the conformance suites.
- **Noto Sans Mongolian** (`reference/`): SIL Open Font License 1.1, © 2022
  The Noto Project Authors. Used only as the reference face the editor compares
  forms against; nothing of it goes into the built fonts. Licence text kept
  alongside the font.
- The CMs fonts themselves are **not** covered by either of the above.
