"""Integritätsprüfung beim Start und über „Werkzeuge → Umgebung prüfen“.

Siehe konzept-natter.md, Abschnitt 17.8: bei jedem Start werden Signatur
und Prüfsummen der Kerndateien geprüft (schnell), beim ersten Start und
auf Wunsch alle Dateien; bei Abweichung erscheint eine verständliche
Meldung mit der Liste der betroffenen Dateien und der Start läuft nur
nach Bestätigung weiter.

Im Entwicklungsbaum (nicht als Exe gebaut) gibt es kein `manifest.json` -
dort entfällt die Prüfung ersatzlos, statt bei jedem `python -m ide` zu
warnen.
"""

from __future__ import annotations

import sys
from pathlib import Path

from ide.integritaet.manifest import ManifestFehler, PruefErgebnis, manifest_pruefen


def programmordner() -> Path | None:
    """Der Ordner der gebauten Installation, oder `None` im
    Entwicklungsbaum. PyInstaller setzt `sys.frozen`; der Programmordner
    ist dann der Ordner neben der Exe, nicht `sys._MEIPASS`."""
    if not getattr(sys, "frozen", False):
        return None
    return Path(sys.executable).resolve().parent


def installation_pruefen(
    ordner: Path | None = None, *, vollstaendig: bool = False
) -> PruefErgebnis | None:
    """Prüft die Installation. Gibt `None` zurück, wenn es nichts zu
    prüfen gibt (Entwicklungsbaum oder fehlendes Manifest) - ein
    fehlendes Manifest ist kein Manipulationsverdacht, sondern der
    Normalfall außerhalb einer gebauten Installation."""
    ordner = ordner if ordner is not None else programmordner()
    if ordner is None:
        return None
    try:
        return manifest_pruefen(ordner, nur_kern=not vollstaendig)
    except ManifestFehler:
        return None
