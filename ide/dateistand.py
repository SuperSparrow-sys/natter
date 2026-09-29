"""Erkennt, dass eine in Natter offene Datei auf der Platte geändert
wurde (Punkt 286).

Ein zweites Natter-Fenster auf demselben Projekt, ein anderer Editor
oder eine Synchronisierung über das Netzlaufwerk können eine Datei
ändern, während sie in Natter offen ist. Bis 0.3.6 schrieb das
Speichern dann einfach den eigenen Stand darüber, und die andere
Änderung war ohne Nachfrage weg.

Der Stand ist Änderungszeit und Größe als kurzer Text. Beides liefert
ein einziger `stat`-Aufruf, auch auf einem Netzlaufwerk, ohne die
Datei zu lesen. Jeder Editor trägt den Stand, in dem er seine Datei
zuletzt gelesen oder geschrieben hat, als Qt-Eigenschaft
`EIGENSCHAFT`; der Designer merkt sich den seiner `.pfm` selbst. So
hat jedes Fenster seinen eigenen Stand, auch zwei Fenster im selben
Prozess.
"""

from __future__ import annotations

import os
from pathlib import Path

#: Name der Qt-Eigenschaft eines Editors, die seinen Dateistand trägt.
EIGENSCHAFT = "dateistand"


def kennung(pfad: Path | str) -> str:
    """Änderungszeit und Größe von `pfad`, leer ohne Datei."""
    try:
        info = os.stat(pfad)
    except OSError:
        return ""
    return f"{info.st_mtime_ns}:{info.st_size}"


def von_aussen_geaendert(gemerkt: str | None, pfad: Path | str) -> bool:
    """Ob `pfad` nicht mehr im Stand `gemerkt` ist. Ohne gemerkten
    Stand und bei einer inzwischen gelöschten Datei gilt die Datei als
    nicht geändert: beim Speichern geht dann nichts verloren."""
    if not gemerkt:
        return False
    aktuell = kennung(pfad)
    return bool(aktuell) and aktuell != gemerkt
