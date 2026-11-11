# Notice

## The original fonts

`cms/CMSUG.TTF`, `cms/CMSUB.TTF`, `cms/CMSHR.TTF` and their `DP` counterparts
are the CMs font set: CMs Urga, CMs Ulaanbaatar and CMs Huree, made by **dEgi**
in 1998 with Macromedia Fontographer 4.1.

Copyright © 1998 dEgi. All rights reserved.

The outlines, the glyph set and the typeface design are dEgi's work. They are
kept in this repository as the source material of a preservation and
Unicode-compatibility project. The `DP` cuts are mirrored for letterpress; only
the legacy-keyed companion has a mirrored version of them.

## Why this rework exists

CMs is among the most widely used Mongolian script fonts in Mongolia. It is
taught in government schools as part of the IT curriculum, and many people
still write with it, because Unicode Mongolian is little known and good input
methods for it are scarce.

But CMs predates Unicode. It draws Mongolian letters in the place of Latin
ones, so text typed with it cannot be searched, read by screen readers, or
displayed by anyone who does not have the font. This rework re-encodes dEgi's
outlines for Unicode, so the typeface people know can carry text that works
everywhere.

## Good faith

dEgi remains the author of the typeface. We have tried to reach him to ask his
permission and have not yet succeeded:

- We have written to an email address associated with him from the late
  1990s. We do not know whether it still reaches him.
- An academic who knows of him has offered to help find him.
- We found an archived website that appears to have been his, online from the
  late 1990s until about 2003. It is no longer online.

Until he is reached, we commit to the following:

- **Free of charge for personal use.** As far as we know, these are the terms
  the 1998 fonts were shared under, and the rework is shared on the same terms.
- **Not sold.** Neither the rework nor anything made from it will be sold
  without dEgi's permission.
- **Credit.** dEgi is named as the author of the typeface in every font built
  here, ahead of anyone who worked on the rework. The family names keep his
  (CMs Urga, CMs Ulaanbaatar, CMs Huree), marked "Gege … Revived" (Gege CMs
  Ulaanbaatar Revived) so that the rework is not mistaken for his 1998 fonts. The
  legacy-keyed companion, typed on his own keyboard, is "CMs … Revived" (CMs Ulaanbaatar
  Revived), for the same reason.
- **His decision.** Any request from dEgi, or from whoever holds his rights,
  will be honoured promptly: a change of credit, name or terms, or the
  withdrawal of the rework.

These commitments are ours. They grant no rights in dEgi's work beyond what he
gave, and they are not an open-source licence.

If you are dEgi, or know how to reach him, please write to **cms@gege.mn**.

## The rework

The Unicode rework of the CMs outlines and the tooling in this repository are
the work of Batmend Ganbaatar and L'Atelier Gege LLC, © 2026. dEgi remains the
author of the typeface and the original outlines. Glyphs drawn new for the
rework follow his design. Licensing beyond the commitments above will be
decided with dEgi.

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
