"""Führt `harness.py` als eigenen Prozess im Projektordner aus und liefert
strukturierte `Testergebnis`-Objekte statt Text zu parsen (Abschnitt 8.6).
"""

from __future__ import annotations

import json
import locale
import subprocess
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ide.prozess import (
    auftrag_zuweisen,
    ohne_konsole,
    prozessbaum_beenden,
)
from pcl.zahlen import text as zahl_text

_HARNESS_PFAD = Path(__file__).resolve().parent / "harness.py"
#: Wie `harness.ERGEBNIS_MARKE`. Nicht importiert: das Skript läuft als
#: eigener Prozess und soll nichts aus `ide` brauchen.
_ERGEBNIS_MARKE = "@@natter-testergebnis@@"
_STANDARD_ZEITLIMIT = 60.0


@dataclass(frozen=True)
class Testergebnis:
    # Reiner Namenszufall mit pytests Standard-Sammelmuster ("Test*") -
    # das hier ist eine Datenklasse, kein Testfall.
    __test__ = False

    id: str
    status: str  # "bestanden" | "fehlgeschlagen" | "fehler"
    dauer: float
    nachricht: str | None = None
    soll: str | None = None
    ist: str | None = None


def tests_ausfuehren(
    projekt_ordner: Path,
    *,
    pattern: str = "test_*.py",
    ziel: str | None = None,
    zeitlimit: float = _STANDARD_ZEITLIMIT,
    prozess_gestartet: Callable[[subprocess.Popen], None] | None = None,
) -> list[Testergebnis]:
    """Entdeckt und führt Tests im Projektordner aus. `ziel` adressiert
    wie `unittest` selbst ein Modul, eine Klasse oder eine einzelne
    Methode (`test_x`, `test_x.Klasse`, `test_x.Klasse.methode`) – ohne
    `ziel` laufen alle nach `pattern` gefundenen Tests.

    `prozess_gestartet` bekommt den Prozess von `harness.py` gleich
    nach dem Start. Das Hauptfenster meldet ihn damit bei seiner
    Hintergrundarbeit an und kann ihn beim Schließen beenden; sonst
    liefe ein Test mit Endlosschleife ohne Elternteil weiter
    (Punkt 254)."""
    befehl = [sys.executable, str(_HARNESS_PFAD), "--pattern", pattern]
    if ziel:
        befehl += ["--ziel", ziel]

    # Die Ausgabe geht in eine Datei statt in ein Rohr. Startet ein
    # Test selbst einen Prozess, erbt der die Rohre, und
    # `subprocess.run` las nach der Zeitgrenze ohne eigene Grenze
    # weiter, bis auch dieser Prozess endete (Punkt 247).
    # Aus einer Datei wird gelesen, was da ist.
    with tempfile.TemporaryFile() as ausgabe_datei:
        prozess = subprocess.Popen(
            befehl,
            **ohne_konsole(
                cwd=projekt_ordner,
                # Ohne Eingabe: ein input() im geprüften Code scheitert
                # sofort mit EOFError, statt bis zur Zeitgrenze auf
                # eine Konsole zu warten, die es nicht gibt.
                stdin=subprocess.DEVNULL,
                stdout=ausgabe_datei,
                stderr=subprocess.DEVNULL,
            ),
        )
        # Im Auftragsobjekt endet beim Abbruch auch, was ein Test
        # gestartet hat, selbst wenn es den Harness überlebt
        # (Punkt 281).
        auftrag_zuweisen(prozess)
        if prozess_gestartet is not None:
            prozess_gestartet(prozess)
        try:
            prozess.wait(timeout=zeitlimit)
        except subprocess.TimeoutExpired:
            # Ein Test mit einer Endlosschleife. Beendet wird der
            # ganze Baum, auch was der Test selbst gestartet hat;
            # gemeldet wird das als Ergebnis wie jeder andere Fehler,
            # damit es im Test-Explorer erscheint.
            prozessbaum_beenden(prozess)
            return [
                Testergebnis(
                    id=ziel or "Testlauf",
                    status="fehler",
                    dauer=zeitlimit,
                    nachricht=(
                        f"Nach {zahl_text(zeitlimit)} Sekunden "
                        f"abgebrochen - vermutlich eine Endlosschleife."
                    ),
                )
            ]
        # Der Lauf ist zu Ende. Was ein Test gestartet und nicht
        # wieder beendet hat, gehört niemandem mehr und endet mit ihm.
        prozessbaum_beenden(prozess)
        ausgabe_datei.seek(0)
        ausgabe = ausgabe_datei.read().decode(
            locale.getpreferredencoding(False), errors="replace"
        )
    # Schreibt der getestete Code an der Umlenkung vorbei direkt auf
    # die Standardausgabe, steht das vor der Marke und wird übergangen.
    if _ERGEBNIS_MARKE in ausgabe:
        ausgabe = ausgabe.rsplit(_ERGEBNIS_MARKE, 1)[1]
    if not ausgabe.strip():
        return []
    return [Testergebnis(**eintrag) for eintrag in json.loads(ausgabe)]
