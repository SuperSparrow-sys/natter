"""Paketverwaltung (Abschnitt 7.2, 18: `ide/env/`): installierte Pakete
anzeigen, ein Paket installieren, die Paketliste als `requirements.txt`
exportieren – über `pip` als Subprozess.

**Vereinfachung, bewusst dokumentiert** (siehe docs/arbeitspakete/M7.md,
Schritt 3): arbeitet auf dem aktuell aktiven Python-Interpreter
(`sys.executable`), nicht auf den getrennten Paketordnern
`pakete-ide`/`pakete-projekt`/`pakete-zusatz` aus Abschnitt 17.6 – die
brauchen den noch nicht gebauten Starter/Launcher aus M8, der beim Start
jeweils nur den passenden Ordner in den Suchpfad hängt.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Paket:
    name: str
    version: str


class PaketFehler(RuntimeError):
    """`pip` meldete einen Fehler; die Nachricht enthält `pip`s eigene
    Fehlerausgabe."""


def installierte_pakete() -> list[Paket]:
    """Liste aller installierten Pakete (`pip list --format=json`)."""
    ergebnis = subprocess.run(
        [sys.executable, "-m", "pip", "list", "--format=json"],
        capture_output=True,
        text=True,
        check=True,
    )
    daten = json.loads(ergebnis.stdout)
    return [Paket(eintrag["name"], eintrag["version"]) for eintrag in daten]


def paket_installieren(name: str) -> str:
    """Installiert `name` per `pip install`. Liefert `pip`s Ausgabe bei
    Erfolg, löst `PaketFehler` bei Misserfolg aus."""
    ergebnis = subprocess.run(
        [sys.executable, "-m", "pip", "install", name],
        capture_output=True,
        text=True,
    )
    if ergebnis.returncode != 0:
        raise PaketFehler(ergebnis.stderr.strip() or ergebnis.stdout.strip())
    return ergebnis.stdout


def paketliste_exportieren(pfad: str | Path) -> None:
    """Schreibt `pip freeze` nach `pfad` (Abschnitt 7.2: „Paketliste
    exportieren (requirements.txt)“)."""
    ergebnis = subprocess.run(
        [sys.executable, "-m", "pip", "freeze"],
        capture_output=True,
        text=True,
        check=True,
    )
    Path(pfad).write_text(ergebnis.stdout, encoding="utf-8")
