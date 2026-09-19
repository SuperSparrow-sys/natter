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

from ide.run.interpreter import ist_gebaut


@dataclass(frozen=True)
class Paket:
    name: str
    version: str


#: Warum die Paketverwaltung in der gebauten Exe nicht arbeiten kann.
#:
#: Sie läuft über `pip` im laufenden Python. Die `Natter.exe` bringt
#: ihren Python fest eingebaut mit; dort ist kein `pip`, und ein
#: nachträglich installiertes Paket läge in einem Ordner, den die Exe
#: beim nächsten Start gar nicht mehr ansieht. Bis M12 rief sie
#: stattdessen `sys.executable` auf - und das ist in der Exe die Exe
#: selbst, es ging also ein zweites Natter-Fenster auf (M12).
GEBAUT_HINWEIS = (
    "Die Paketverwaltung arbeitet über pip und steht in der installierten "
    "Natter-Version nicht zur Verfügung: dort ist Python fest eingebaut. "
    "Alles, was der Unterricht braucht, ist bereits enthalten."
)


class PaketFehler(RuntimeError):
    """`pip` meldete einen Fehler; die Nachricht enthält `pip`s eigene
    Fehlerausgabe."""


def installierte_pakete() -> list[Paket]:
    """Liste aller installierten Pakete (`pip list --format=json`).
    Löst `PaketFehler` aus, wenn `pip` fehlschlägt (Nutzer-Feedback,
    echter Absturz: `check=True` ließ eine unbehandelte
    `CalledProcessError` bis zur IDE durchschlagen, statt wie
    `paket_installieren()` einen sauberen Fehler mit `pip`s eigener
    Meldung zu liefern)."""
    if ist_gebaut():
        raise PaketFehler(GEBAUT_HINWEIS)
    ergebnis = subprocess.run(
        [sys.executable, "-m", "pip", "list", "--format=json"],
        capture_output=True,
        text=True,
    )
    if ergebnis.returncode != 0:
        raise PaketFehler(ergebnis.stderr.strip() or ergebnis.stdout.strip())
    daten = json.loads(ergebnis.stdout)
    return [Paket(eintrag["name"], eintrag["version"]) for eintrag in daten]


def paket_installieren(name: str) -> str:
    """Installiert `name` per `pip install`. Liefert `pip`s Ausgabe bei
    Erfolg, löst `PaketFehler` bei Misserfolg aus."""
    if ist_gebaut():
        raise PaketFehler(GEBAUT_HINWEIS)
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
    exportieren (requirements.txt)“). Löst `PaketFehler` aus, wenn `pip`
    fehlschlägt (siehe `installierte_pakete`)."""
    if ist_gebaut():
        raise PaketFehler(GEBAUT_HINWEIS)
    ergebnis = subprocess.run(
        [sys.executable, "-m", "pip", "freeze"],
        capture_output=True,
        text=True,
    )
    if ergebnis.returncode != 0:
        raise PaketFehler(ergebnis.stderr.strip() or ergebnis.stdout.strip())
    Path(pfad).write_text(ergebnis.stdout, encoding="utf-8")
