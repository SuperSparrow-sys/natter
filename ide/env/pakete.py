"""Paketverwaltung (Abschnitt 7.2, 18: `ide/env/`): installierte Pakete
anzeigen, ein Paket installieren, die Paketliste als `requirements.txt`
exportieren – über `pip` als Subprozess.

Vereinfachung, bewusst dokumentiert (siehe Arbeitspaket M7,
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

from ide.prozess import ohne_konsole


@dataclass(frozen=True)
class Paket:
    name: str
    version: str


#: Ergänzung zur pip-Meldung, wenn das Installationsverzeichnis
#: schreibgeschützt ist.
#:
#: Natter liegt seit M13 als gewöhnliche Python-Installation vor, pip
#: arbeitet also wieder ganz normal. Nur: wer Natter systemweit nach
#: `C:\Programme` installiert hat, darf dort ohne Administratorrechte
#: nicht hineinschreiben. Die Voreinstellung des Installers ist deshalb
#: die Installation nur für den angemeldeten Nutzer.
KEIN_SCHREIBRECHT_HINWEIS = (
    " Natter ist in einem Ordner installiert, in den ohne "
    "Administratorrechte nicht geschrieben werden darf. Pakete lassen "
    "sich nur nachinstallieren, wenn Natter nur für den angemeldeten "
    "Nutzer installiert ist."
)


class PaketFehler(RuntimeError):
    """`pip` meldete einen Fehler; die Nachricht enthält `pip`s eigene
    Fehlerausgabe."""


def installierte_pakete() -> list[Paket]:
    """Liste aller installierten Pakete (`pip list --format=json`).
 Löst `PaketFehler` aus, wenn `pip` fehlschlägt (Rückmeldung,
 echter Absturz: `check=True` ließ eine unbehandelte
 `CalledProcessError` bis zur IDE durchschlagen, statt wie
 `paket_installieren` einen sauberen Fehler mit `pip`s eigener
 Meldung zu liefern)."""
    ergebnis = subprocess.run(
        [sys.executable, "-m", "pip", "list", "--format=json"],
        **ohne_konsole(capture_output=True, text=True),
    )
    if ergebnis.returncode != 0:
        raise PaketFehler(ergebnis.stderr.strip() or ergebnis.stdout.strip())
    daten = json.loads(ergebnis.stdout)
    return [Paket(eintrag["name"], eintrag["version"]) for eintrag in daten]


def paket_installieren(name: str) -> str:
    """Installiert `name` per `pip install`. Liefert `pip`s Ausgabe bei
    Erfolg, löst `PaketFehler` bei Misserfolg aus."""
    ergebnis = subprocess.run(
        [sys.executable, "-m", "pip", "install", name],
        **ohne_konsole(capture_output=True, text=True),
    )
    if ergebnis.returncode != 0:
        raise PaketFehler(_mit_rechtehinweis(ergebnis))
    return ergebnis.stdout


def _mit_rechtehinweis(ergebnis: subprocess.CompletedProcess) -> str:
    """`pip`s eigene Meldung, bei fehlenden Schreibrechten ergänzt.

    `pip` schreibt in diesem Fall nur „Could not install packages due to
    an OSError: [Errno 13] Permission denied“ - richtig, aber ohne den
    entscheidenden Hinweis, woran es liegt (M13).
    """
    meldung = ergebnis.stderr.strip() or ergebnis.stdout.strip()
    zeichen = ("Permission denied", "Errno 13", "WinError 5", "Zugriff verweigert")
    if any(z in meldung for z in zeichen):
        return meldung + KEIN_SCHREIBRECHT_HINWEIS
    return meldung


def paketliste_exportieren(pfad: str | Path) -> None:
    """Schreibt `pip freeze` nach `pfad` (Abschnitt 7.2: „Paketliste
    exportieren (requirements.txt)“). Löst `PaketFehler` aus, wenn `pip`
    fehlschlägt (siehe `installierte_pakete`)."""
    ergebnis = subprocess.run(
        [sys.executable, "-m", "pip", "freeze"],
        **ohne_konsole(capture_output=True, text=True),
    )
    if ergebnis.returncode != 0:
        raise PaketFehler(ergebnis.stderr.strip() or ergebnis.stdout.strip())
    Path(pfad).write_text(ergebnis.stdout, encoding="utf-8")
