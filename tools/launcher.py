"""Der Starter, aus dem `Natter.exe` gebaut wird (M13).

Seit M13 liegt Natter als gewöhnliche Python-Installation vor (siehe
`docs/arbeitspakete/M13.md`). Gestartet wird sie über diesen schlanken
Starter: er sucht die mitgelieferte `pythonw.exe` neben sich und
übergibt ihr `-m ide` samt allem, was an `Natter.exe` übergeben wurde
(etwa der Pfad einer doppelgeklickten `.natter`-Datei).

Warum überhaupt eine eigene Exe, statt im Startmenü direkt auf
`pythonw.exe` zu verweisen: so trägt das Programm sein eigenes Symbol,
seine eigene Versionsangabe und seine eigene Signatur – und im Explorer
steht „Natter“ und nicht „pythonw“.

Bewusst ohne jede Abhängigkeit über die Standardbibliothek hinaus: so
bleibt die gebaute Exe klein und startet ohne spürbare Verzögerung.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

#: Unterordner der Installation, in dem die mitgelieferte Python liegt.
PYTHON_ORDNER = "python"

#: Ohne Konsolenfenster - die IDE ist ein Fensterprogramm.
STARTER = "pythonw.exe"

#: Umgebungsvariablen, die auf eine fremde Python-Installation zeigen.
#:
#: Natter bringt alles mit und soll auch genau das benutzen. Findet die
#: mitgelieferte Python über eine dieser Variablen die Pakete einer
#: anderen Installation, kommen dort eine ältere PySide6-Fassung oder
#: ein halb eingerichtetes NumPy zum Vorschein - und Natter geht auf
#: einem Rechner kaputt, auf dem nie jemand etwas an Natter geändert
#: hat. Auf Entwicklerrechnern ist das der Normalfall; beim Bau der
#: Auslieferung hat genau das zugeschlagen (M13, siehe
#: `tools/ide_paketieren.py`).
FREMDE_UMGEBUNG = ("PYTHONPATH", "PYTHONHOME", "PYTHONUSERBASE", "VIRTUAL_ENV")


def installationsordner() -> Path:
    """Der Ordner, in dem `Natter.exe` liegt."""
    return Path(sys.executable).resolve().parent


def python_pfad(wurzel: Path | None = None) -> Path:
    wurzel = wurzel if wurzel is not None else installationsordner()
    return wurzel / PYTHON_ORDNER / STARTER


def fehlende_installation_melden(pfad: Path) -> None:
    """Sagt, was fehlt – und zwar sichtbar.

    Ein Fensterprogramm ohne Konsole hat sonst keine Möglichkeit dazu;
    ohne diese Meldung würde ein Doppelklick auf `Natter.exe` einfach
    nichts tun.
    """
    text = (
        "Natter ist nicht vollständig installiert.\n\n"
        f"Erwartet wurde:\n{pfad}\n\n"
        "Bitte Natter neu installieren."
    )
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, text, "Natter", 0x10)
    except Exception:
        print(text, file=sys.stderr)


def eigene_umgebung() -> dict[str, str]:
    """Die Umgebung, in der Natter läuft: die des Nutzers, aber ohne
    Verweise auf fremde Python-Installationen.

    Erbt alles Übrige unverändert - `PATH`, Proxy-Einstellungen und
    was die Schule sonst setzt, wird gebraucht, etwa damit über das
    Menü „Pakete“ Nachinstallieren funktioniert.
    """
    umgebung = {
        name: wert
        for name, wert in os.environ.items()
        if name.upper() not in FREMDE_UMGEBUNG
    }
    umgebung["PYTHONNOUSERSITE"] = "1"
    return umgebung


def main() -> int:
    ziel = python_pfad()
    if not ziel.is_file():
        fehlende_installation_melden(ziel)
        return 1

    befehl = [str(ziel), "-m", "ide", *sys.argv[1:]]
    # `cwd` auf den Installationsordner: ein relativer Pfad in argv
    # kommt vom Explorer immer absolut, und so landen etwaige
    # Hilfsdateien nicht im zuletzt benutzten Ordner des Nutzers.
    return subprocess.call(befehl, cwd=str(installationsordner()), env=eigene_umgebung())


if __name__ == "__main__":
    sys.exit(main())
