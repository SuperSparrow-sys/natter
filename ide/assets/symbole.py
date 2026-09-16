"""Lädt SVG-Symbole aus `ide/assets/icons/` als `QIcon` – für
Werkzeugleiste, Fenster-Icon und (später) Palette/Baum (Abschnitt 7.3,
7.9). Symbolnamen entsprechen den Dateinamen ohne `.svg`, siehe `Aktion.
symbol` in `ide/actions/register.py`.
"""

from __future__ import annotations

from functools import cache
from pathlib import Path

# Muss vor der ersten QIcon(...)-Erstellung aus einer .svg-Datei importiert
# werden, sonst bleibt das Icon leer (isNull()==True) - der SVG-Icon-Engine-
# Plugin (qsvgicon) wird sonst nicht registriert, obwohl er installiert ist.
from PySide6 import QtSvg  # noqa: F401
from PySide6.QtGui import QIcon

_ICON_ORDNER = Path(__file__).resolve().parent / "icons"


@cache
def symbol(name: str) -> QIcon:
    """Liefert das Symbol `name` (Dateiname ohne `.svg`). Unbekannter Name
    liefert ein leeres `QIcon` statt eines Fehlers – Aufrufer müssen kein
    Symbol angeben (`Aktion.symbol` ist standardmäßig leer)."""
    if not name:
        return QIcon()
    pfad = _ICON_ORDNER / f"{name}.svg"
    if not pfad.exists():
        return QIcon()
    return QIcon(str(pfad))
