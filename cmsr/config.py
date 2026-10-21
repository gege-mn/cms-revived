from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEGACY_DIR = ROOT / "cms"
MAPPING_FILE = ROOT / "mapping" / "pieces.toml"
DRAWINGS_DIR = ROOT / "drawings"
DIST_DIR = ROOT / "dist"

LOCALE = "MNG"

# Working name, pending the author's word (see NOTICE.md). Changing it renames every cut.
FAMILY_SUFFIX = "Revived"

VERSION = (0, 100)  # major, minor as the font's three-digit minor: 0.100

# dEgi is named first everywhere; where a field holds one value, the rework comes second.
COPYRIGHT = "Copyright © 1998 dEgi. Unicode rework © 2026 L'Atelier Gege LLC."
DESIGNER = "dEgi; Batmend Ganbaatar (Unicode rework)"
MANUFACTURER = "dEgi; L'Atelier Gege LLC"
VENDOR_ID = "GEGE"
DESCRIPTION = (
    "CMs, the Classical Mongolian script typeface drawn by dEgi in 1998, re-encoded for "
    "Unicode. The outlines are dEgi's; the rework adds the Unicode encoding and shaping."
)
LICENSE = (
    "All rights reserved. No licence is granted until the original author's permission is "
    "obtained; see NOTICE.md."
)


@dataclass(frozen=True)
class Cut:
    id: str
    name: str

    @property
    def family(self) -> str:
        return f"CMs {self.name} {FAMILY_SUFFIX}"

    @property
    def postscript_name(self) -> str:
        return self.family.replace(" ", "") + "-Regular"

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
