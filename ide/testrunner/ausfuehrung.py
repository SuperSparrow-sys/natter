"""Führt `harness.py` als eigenen Prozess im Projektordner aus und liefert
strukturierte `Testergebnis`-Objekte statt Text zu parsen (Abschnitt 8.6).
"""

from __future__ import annotations

import json
import locale
import os
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from ide.prozess import (
    auftrag_zuweisen,
    ohne_konsole,
    prozessbaum_beenden,
)
from pcl.pruefungsmodus import laeuft as pruefungsmodus_laeuft
from pcl.zahlen import text as zahl_text

_HARNESS_PFAD = Path(__file__).resolve().parent / "harness.py"
#: Wie `harness.ERGEBNIS_MARKE`. Nicht importiert: das Skript läuft als
#: eigener Prozess und soll nichts aus `ide` brauchen.
_ERGEBNIS_MARKE = "@@natter-testergebnis@@"
_STANDARD_ZEITLIMIT = 60.0

#: So beginnt die Meldung, mit der Qt den Prozess beendet, wenn ein
#: Fenster vor der QApplication entsteht („QWidget: Must construct a
#: QApplication before a QWidget“).
_QT_OHNE_ANWENDUNG = "Must construct a QApplication"


#: Die Zustände, die als nicht bestanden zählen. Ein übersprungener
#: Test ist weder bestanden noch gescheitert (Punkt 555).
NICHT_BESTANDEN = ("fehlgeschlagen", "fehler")


@dataclass(frozen=True)
class Testergebnis:
    # Reiner Namenszufall mit pytests Standard-Sammelmuster ("Test*") -
    # das hier ist eine Datenklasse, kein Testfall.
    __test__ = False

    id: str
    status: str  # "bestanden" | "fehlgeschlagen" | "fehler" | "übersprungen"
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
    (Punkt 254).

    Alle Tests laufen in einem Prozess. Bricht er ab, steht an Stelle
    des Tests, der gerade lief, ein Eintrag mit Status „fehler“, und
    ein neuer Prozess übernimmt die Testmodule, die noch nicht dran
    waren (Punkt 425). Ein Prozess je Datei wäre einfacher, kostete
    aber bei jeder Datei den Start des Interpreters, auch wenn nichts
    abstürzt. `zeitlimit` gilt für alle Prozesse zusammen."""
    ende = time.monotonic() + zeitlimit
    ergebnisse: list[Testergebnis] = []
    auslassen: list[str] = []
    while True:
        lauf = _harness_ausfuehren(
            projekt_ordner,
            pattern=pattern,
            ziel=ziel,
            auslassen=auslassen,
            zeitlimit=max(ende - time.monotonic(), 0.0),
            prozess_gestartet=prozess_gestartet,
        )
        ergebnisse += lauf.ergebnisse
        if lauf.zeit_abgelaufen:
            # Ein Test mit einer Endlosschleife. Gemeldet wird das als
            # Ergebnis wie jeder andere Fehler, damit es im
            # Test-Explorer erscheint.
            ergebnisse.append(
                Testergebnis(
                    id=lauf.laufender_test or ziel or "Testlauf",
                    status="fehler",
                    dauer=zeitlimit,
                    nachricht=(
                        f"Nach {zahl_text(zeitlimit)} Sekunden "
                        f"abgebrochen - vermutlich eine Endlosschleife."
                    ),
                )
            )
            return ergebnisse
        if (
            lauf.fertig
            and lauf.rueckgabewert == 0
            and lauf.ungueltige_zeile is None
        ):
            return ergebnisse
        ergebnisse.append(_abbruch_ergebnis(lauf, ziel))
        # Der nächste Lauf lässt alles aus, was schon dran war,
        # einschließlich des Moduls, in dem der Abbruch geschah. Kommt
        # nichts Neues dazu, liefe er wieder in denselben Abbruch.
        neu = [m for m in lauf.begonnene_module if m not in auslassen]
        if lauf.fertig or ziel or not neu:
            return ergebnisse
        auslassen += neu


@dataclass
class _Lauf:
    """Was ein einzelner Prozess von `harness.py` gemeldet hat."""

    ergebnisse: list[Testergebnis] = field(default_factory=list)
    #: Ob die Schlusszeile des Harness ankam.
    fertig: bool = False
    rueckgabewert: int | None = None
    zeit_abgelaufen: bool = False
    #: Der zuletzt gestartete Test, solange zu ihm kein Ergebnis kam.
    laufender_test: str | None = None
    #: Das zuletzt gemeldete Modul, beim Laden oder beim Start eines
    #: seiner Tests.
    letztes_modul: str | None = None
    #: Ob `letztes_modul` beim Laden gemeldet wurde.
    beim_laden: bool = False
    #: Module, deren Tests begonnen haben, und `letztes_modul`.
    begonnene_module: list[str] = field(default_factory=list)
    qt_ohne_anwendung: bool = False
    #: Eine Zeile hinter der Marke, die sich nicht lesen ließ.
    ungueltige_zeile: str | None = None


def _harness_ausfuehren(
    projekt_ordner: Path,
    *,
    pattern: str,
    ziel: str | None,
    auslassen: list[str],
    zeitlimit: float,
    prozess_gestartet: Callable[[subprocess.Popen], None] | None,
) -> _Lauf:
    befehl = [sys.executable, str(_HARNESS_PFAD), "--pattern", pattern]
    if ziel:
        befehl += ["--ziel", ziel]
    for modul in auslassen:
        befehl += ["--auslassen", modul]
    # Qt schreibt seine Meldungen unter Windows nur dann auf die
    # Fehlerausgabe, wenn sie eine Konsole ist; sonst gehen sie an den
    # Debugger des Systems. Gebraucht wird die Meldung, um einen
    # Abbruch wegen fehlender QApplication zu erkennen.
    umgebung = {**os.environ, "QT_FORCE_STDERR_LOGGING": "1"}

    # Die Ausgabe geht in eine Datei statt in ein Rohr. Startet ein
    # Test selbst einen Prozess, erbt der die Rohre, und
    # `subprocess.run` las nach der Zeitgrenze ohne eigene Grenze
    # weiter, bis auch dieser Prozess endete (Punkt 247).
    # Aus einer Datei wird gelesen, was da ist.
    with (
        tempfile.TemporaryFile() as ausgabe_datei,
        tempfile.TemporaryFile() as fehler_datei,
    ):
        prozess = subprocess.Popen(
            befehl,
            **ohne_konsole(
                cwd=projekt_ordner,
                env=umgebung,
                # Ohne Eingabe: ein input() im geprüften Code scheitert
                # sofort mit EOFError, statt bis zur Zeitgrenze auf
                # eine Konsole zu warten, die es nicht gibt.
                stdin=subprocess.DEVNULL,
                stdout=ausgabe_datei,
                stderr=fehler_datei,
            ),
        )
        # Im Auftragsobjekt endet beim Abbruch auch, was ein Test
        # gestartet hat, selbst wenn es den Harness überlebt
        # (Punkt 281).
        auftrag_zuweisen(prozess)
        if prozess_gestartet is not None:
            prozess_gestartet(prozess)
        zeit_abgelaufen = False
        try:
            prozess.wait(timeout=zeitlimit)
        except subprocess.TimeoutExpired:
            zeit_abgelaufen = True
        # Der Lauf ist zu Ende, oder die Zeit ist um. Beendet wird der
        # ganze Baum: was ein Test gestartet und nicht wieder beendet
        # hat, gehört niemandem mehr und endet mit ihm.
        prozessbaum_beenden(prozess)
        ausgabe_datei.seek(0)
        ausgabe = ausgabe_datei.read().decode(
            locale.getpreferredencoding(False), errors="replace"
        )
        # Nur das Ende: die Meldung von Qt steht unmittelbar vor dem
        # Abbruch, und davor kann beliebig viel Ausgabe der Tests
        # liegen.
        fehler_datei.seek(0, os.SEEK_END)
        fehler_datei.seek(max(fehler_datei.tell() - 65536, 0))
        fehler_ende = fehler_datei.read().decode(
            locale.getpreferredencoding(False), errors="replace"
        )
    lauf = _ausgabe_auswerten(ausgabe)
    lauf.zeit_abgelaufen = zeit_abgelaufen
    if not zeit_abgelaufen:
        lauf.rueckgabewert = prozess.returncode
    lauf.qt_ohne_anwendung = _QT_OHNE_ANWENDUNG in fehler_ende
    return lauf


def _ausgabe_auswerten(ausgabe: str) -> _Lauf:
    """Liest die Zeilen hinter der Marke.

    Schreibt der getestete Code an der Umlenkung vorbei direkt auf die
    Standardausgabe, steht das zwischen den Zeilen des Harness und wird
    übergangen. Die Marke muss dafür nicht am Zeilenanfang stehen, und
    was hinter dem JSON auf derselben Zeile folgt, zählt nicht."""
    lauf = _Lauf()
    leser = json.JSONDecoder()
    for zeile in ausgabe.splitlines():
        position = zeile.find(_ERGEBNIS_MARKE)
        if position < 0:
            continue
        rest = zeile[position + len(_ERGEBNIS_MARKE):]
        try:
            eintrag, _ = leser.raw_decode(rest.strip())
            if not isinstance(eintrag, dict):
                raise ValueError(eintrag)
            _eintrag_uebernehmen(lauf, eintrag)
        except (ValueError, TypeError):
            lauf.ungueltige_zeile = rest.strip()
    if lauf.letztes_modul and (
        lauf.letztes_modul not in lauf.begonnene_module
    ):
        lauf.begonnene_module.append(lauf.letztes_modul)
    return lauf


def _eintrag_uebernehmen(lauf: _Lauf, eintrag: dict) -> None:
    if eintrag.get("fertig") is True:
        lauf.fertig = True
    elif "laden" in eintrag:
        lauf.letztes_modul = str(eintrag["laden"])
        lauf.beim_laden = True
        lauf.laufender_test = None
    elif "start" in eintrag:
        modul = str(eintrag.get("modul") or "")
        lauf.laufender_test = str(eintrag["start"])
        lauf.letztes_modul = modul
        lauf.beim_laden = False
        if modul and modul not in lauf.begonnene_module:
            lauf.begonnene_module.append(modul)
    else:
        ergebnis = Testergebnis(**eintrag)
        lauf.ergebnisse.append(ergebnis)
        if ergebnis.id == lauf.laufender_test:
            lauf.laufender_test = None


def _abbruch_ergebnis(lauf: _Lauf, ziel: str | None) -> Testergebnis:
    """Der Eintrag für einen Prozess, der ohne Schlusszeile oder mit
    einem Rückgabewert ungleich 0 endete oder eine unlesbare Zeile
    geschrieben hat."""
    wert = (
        "ohne Rückgabewert"
        if lauf.rueckgabewert is None
        else f"mit Rückgabewert {_rueckgabewert_text(lauf.rueckgabewert)}"
    )
    if lauf.fertig and lauf.rueckgabewert == 0:
        test_id = ziel or "Testlauf"
        text = "Die Tests sind durchgelaufen."
    elif lauf.fertig:
        test_id = ziel or "Testlauf"
        text = (
            "Die Tests sind durchgelaufen, aber der Testprozess endete "
            f"danach {wert}."
        )
    elif lauf.laufender_test is not None:
        test_id = lauf.laufender_test
        text = (
            "Der Testlauf ist während dieses Tests abgebrochen. Der "
            f"Testprozess endete {wert}."
        )
    elif lauf.beim_laden and lauf.letztes_modul:
        test_id = lauf.letztes_modul
        datei = lauf.letztes_modul.replace(".", "/") + ".py"
        text = (
            f"Der Testlauf ist beim Laden der Testdatei {datei} "
            f"abgebrochen. Der Testprozess endete {wert}."
        )
    else:
        test_id = ziel or lauf.letztes_modul or "Testlauf"
        text = f"Der Testlauf ist abgebrochen. Der Testprozess endete {wert}."
    teile = [text]
    if lauf.qt_ohne_anwendung and not pruefungsmodus_laeuft():
        teile.append(
            "Qt hat den Prozess beendet, weil ein Formular ohne "
            "QApplication angelegt wurde. Ein Formular im Test braucht "
            "vorher eine, etwa mit Application() aus pcl in setUpClass."
        )
    if lauf.ungueltige_zeile is not None:
        teile.append(
            "Eine Zeile des Testergebnisses ließ sich nicht lesen: "
            f"{lauf.ungueltige_zeile[:200]}"
        )
    return Testergebnis(
        id=test_id, status="fehler", dauer=0.0, nachricht="\n\n".join(teile)
    )


def _rueckgabewert_text(wert: int) -> str:
    """Kleine Werte dezimal, Statuscodes von Windows wie 0xC0000409
    hexadezimal, so wie Windows sie selbst nennt."""
    if 0 <= wert < 0x10000:
        return str(wert)
    return f"0x{wert & 0xFFFFFFFF:08X}"
