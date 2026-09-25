"""Integritätsprüfung beim Start und über „Werkzeuge → Umgebung prüfen“.

Siehe docs/bericht.md, Abschnitt 7.5: bei jedem Start werden Signatur
und Prüfsummen der Kerndateien geprüft (schnell), beim ersten Start und
auf Wunsch alle Dateien; bei Abweichung erscheint eine verständliche
Meldung mit der Liste der betroffenen Dateien und der Start läuft nur
nach Bestätigung weiter.

Im Entwicklungsbaum gibt es kein `manifest.json` - dort entfällt die
Prüfung ersatzlos, statt bei jedem `python -m ide` zu warnen.
"""

from __future__ import annotations

import sys
from pathlib import Path

from ide.integritaet.manifest import (
    MANIFEST_DATEINAME,
    ManifestFehler,
    PruefErgebnis,
    manifest_pruefen,
)


def programmordner() -> Path | None:
    """Der Ordner der ausgelieferten Installation, oder `None` im
    Entwicklungsbaum.

    Bis M12 war die Frage einfach: PyInstaller setzt `sys.frozen`, und
    der Programmordner ist der Ordner neben der Exe. Seit M13 läuft
    Natter als ganz gewöhnliches `pythonw.exe -m ide` - `sys.frozen`
    gibt es dort nicht mehr, und die Prüfung fiel damit in der
    ausgelieferten Fassung stillschweigend ganz aus. Bemerkt hätte das
    niemand: sie meldet sich ja nur, wenn etwas nicht stimmt.

    Erkennungsmerkmal ist deshalb jetzt das `manifest.json` selbst. Es
    liegt eine Ebene über der mitgelieferten Python, also neben
    `Natter.exe`:

        <Installation>/Natter.exe
        <Installation>/manifest.json
        <Installation>/python/pythonw.exe   <- sys.executable

    Im Entwicklungsbaum zeigt derselbe Weg auf `.venv`, und dort liegt
    kein Manifest - die Prüfung entfällt wie bisher ersatzlos.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    moeglich = Path(sys.executable).resolve().parent.parent
    return moeglich if (moeglich / MANIFEST_DATEINAME).is_file() else None


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
