from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEGACY_DIR = ROOT / "cms"
MAPPING_FILE = ROOT / "mapping" / "pieces.toml"
DRAWINGS_DIR = ROOT / "drawings"
DIST_DIR = ROOT / "dist"

LOCALE = "MNG"

# Changing either renames every cut. dEgi may still ask for another name (NOTICE.md).
FAMILY_PREFIX = "Gege"
FAMILY_SUFFIX = "Revived"

VERSION = (1, 0)  # major, minor as the font's three-digit minor: 1.000
VERSION_LABEL: str | None = None  # e.g. "Alpha 5", for a snapshot that keeps the family name

# dEgi is named first everywhere; where a field holds one value, the rework comes second.
COPYRIGHT = "Copyright © 1998 dEgi. Unicode rework © 2026 L'Atelier Gege LLC."
DESIGNER = "dEgi; Batmend Ganbaatar (Unicode rework)"
MANUFACTURER = "dEgi; L'Atelier Gege LLC"
VENDOR_ID = "GEGE"
CONTACT = "cms@gege.mn"
VENDOR_URL: str | None = "https://github.com/gege-mn/cms-revived"
DESCRIPTION = (
    "CMs, the Classical Mongolian script typeface drawn by dEgi in 1998, re-encoded for "
    "Unicode. The outlines are dEgi's; the rework adds the Unicode encoding and shaping. "
    f"We have not yet reached dEgi. If you are him, or know how to reach him: {CONTACT}"
)
LICENSE = (
    "Free of charge for personal use. Not to be sold without the permission of dEgi, the "
    "original author, which has not yet been obtained. No other rights in his work are "
    f"granted. Contact: {CONTACT}"
)

# The legacy-keyed companion (cmsr/companion.py): dEgi's keyboard, the rework's joins.
COMPANION_DESCRIPTION = (
    "CMs, the Classical Mongolian script typeface drawn by dEgi in 1998, typed on his own "
    "keyboard as in 1998. The outlines are dEgi's; the rework adds the joins of the Unicode "
    "rework as ligatures, so text typed for CMs draws with them. Turn ligatures off and it is "
    f"his 1998 font. We have not yet reached dEgi. If you are him, or know how to reach him: {CONTACT}"
)
COMPANION_COPYRIGHT = "Copyright © 1998 dEgi. Rework © 2026 L'Atelier Gege LLC."
COMPANION_DESIGNER = "dEgi; Batmend Ganbaatar (rework)"
COMPANION_VERSION_NOTE = "dEgi 1998, legacy-keyed rework 2026"


@dataclass(frozen=True)
class Cut:
    id: str
    name: str

    @property
    def family(self) -> str:
        return f"{FAMILY_PREFIX} CMs {self.name} {FAMILY_SUFFIX}"

    @property
    def postscript_name(self) -> str:
        return self.family.replace(" ", "") + "-Regular"

    @property
    def companion_family(self) -> str:
        return f"CMs {self.name} {FAMILY_SUFFIX}"

    @property
    def companion_path(self) -> Path:
        return DIST_DIR / f"{self.companion_family.replace(' ', '')}-Regular.ttf"

    @property
    def legacy_path(self) -> Path:
        return LEGACY_DIR / f"{self.id}.TTF"

    @property
    def output_path(self) -> Path:
        return DIST_DIR / f"{self.postscript_name}.ttf"

    @property
    def drawings_path(self) -> Path:
        return DRAWINGS_DIR / f"{self.id}.ufo"


CUTS = {cut.id: cut for cut in (Cut("CMSUB", "Ulaanbaatar"), Cut("CMSUG", "Urga"), Cut("CMSHR", "Huree"))}
DEFAULT_CUT = "CMSUB"
