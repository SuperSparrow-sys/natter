"""Pfadauflösung für mitgelieferte Datenordner der IDE (`schemas/`),
die zur Laufzeit gelesen werden statt importiert zu werden. In einer
mit PyInstaller gebauten Exe (`tools/ide_paketieren.py`) liegen diese
Ordner nicht mehr relativ zum Quellcode, sondern im Bundle-Ordner
(`sys._MEIPASS`) - dasselbe Muster wie `pcl/theme/__init__.py` für
`design/tokens.json` (dort eigenständig, weil `pcl` nicht von `ide`
abhängen darf). Eine einzige Quelle für `ide/codegen/design.py`,
`ide/designer/pfm_schreiben.py` und `ide/project/projekt.py`, statt
drei eigenen Kopien."""

from __future__ import annotations

import sys
from pathlib import Path

_PROJEKT_WURZEL = Path(__file__).resolve().parent.parent


def daten_ordner(name: str) -> Path:
    """`name` (z. B. `"schemas"`) relativ zur Projektwurzel, oder im
    Bundle-Ordner, falls als PyInstaller-Exe eingefroren."""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass is not None:
        return Path(meipass) / name
    return _PROJEKT_WURZEL / name
