"""Eigenständiges Testlauf-Skript (Abschnitt 8.6, 19): läuft als eigener
Prozess im Projektordner, entdeckt `test_*.py`-Dateien mit der
Standardbibliothek `unittest`, führt sie aus und gibt ein strukturiertes
JSON-Ergebnis auf stdout aus statt Textausgabe zu parsen.

Braucht absichtlich nichts aus `pcl`/`ide` – reines `unittest`, damit
Schülertests genau das ausführen, was sie mit `python -m unittest` auch
in der Kommandozeile täten (Abschnitt 8.6: „Tests in Dateien `test_*.py`
mit `unittest`“).

Aufruf: `python harness.py [--pattern MUSTER] [--ziel PUNKT.GETRENNTE.ID]
[--auslassen MODUL ...]`
`--ziel` adressiert wie `unittest`selbst ein Modul, eine Klasse oder eine
einzelne Methode (`test_x`, `test_x.Klasse`, `test_x.Klasse.methode`).
`--auslassen` überspringt Testmodule, die ein früherer, abgebrochener
Lauf schon erledigt hat.

Jedes Ergebnis steht sofort in einer eigenen Zeile hinter der Marke,
nicht erst am Ende. Bricht der Prozess mitten im Lauf ab, etwa weil
Qt ein Formular ohne `QApplication` nicht anlegen kann, bleibt so
erhalten, was bis dahin gelaufen ist. Dazu kommen Zeilen, die sagen,
welches Modul gerade geladen und welcher Test gerade gestartet wird,
und am Ende eine Zeile `{"fertig": true}`.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import traceback
import types
import unittest

# Bei Listen, Tupeln und anderen Folgen setzt unittest „Lists
# differ: “, „Tuples differ: “ oder „Sequences differ: “ vor den
# Vergleich. Der Vorsatz gehört nicht zum Ist-Wert.
_SOLL_IST_MUSTER = re.compile(
    r"^(?:\w+ differ: )?(?P<ist>.+?) != (?P<soll>.+)$"
)

#: Längere Werte werden für Tooltip und Protokoll gekürzt.
_WERT_HOECHSTLAENGE = 200

#: Steht in der Standardausgabe unmittelbar vor dem JSON-Ergebnis.
#: `ausfuehrung.py` liest nur, was danach kommt; alles davor hat der
#: getestete Code selbst geschrieben.
ERGEBNIS_MARKE = "@@natter-testergebnis@@"

#: Die echte Standardausgabe. Während der Tests zeigt `sys.stdout` auf
#: die Fehlerausgabe (siehe `main`).
_echte_ausgabe = sys.stdout


def _melden(eintrag: dict) -> None:
    """Schreibt eine Zeile hinter der Marke und leert den Puffer
    sofort, damit sie einen Absturz des Prozesses übersteht."""
    # Die Zeile beginnt mit einem Umbruch, falls der getestete Code
    # direkt auf die Standardausgabe geschrieben hat, ohne die Zeile
    # abzuschließen.
    _echte_ausgabe.write(
        "\n" + ERGEBNIS_MARKE + json.dumps(eintrag) + "\n"
    )
    _echte_ausgabe.flush()


def _wert_text(wert: object) -> str:
    try:
        text = repr(wert)
    except Exception:
        text = object.__repr__(wert)
    if len(text) > _WERT_HOECHSTLAENGE:
        text = text[: _WERT_HOECHSTLAENGE - 1] + "…"
    return text


def _werte_aus_assertequal(tb) -> tuple[str, str] | tuple[None, None]:
    """Soll und Ist aus dem Aufruf von `assertEqual` im Traceback.

    Die Meldung allein reicht nicht: bei Mengen schreibt unittest nur
    „Items in the first set but not the second: …“ ohne die Werte, und
    lange Folgen kürzt es zu „[0, 1[126 chars]…“. Die Argumente
    `first` (Ist) und `second` (Soll) stehen im Rahmen von
    `assertEqual` aus `unittest.case`."""
    while tb is not None:
        rahmen = tb.tb_frame
        if (
            rahmen.f_code.co_name == "assertEqual"
            and rahmen.f_globals.get("__name__") == "unittest.case"
        ):
            lokale = rahmen.f_locals
            if "first" in lokale and "second" in lokale:
                return (
                    _wert_text(lokale["second"]),
                    _wert_text(lokale["first"]),
                )
        tb = tb.tb_next
    return None, None


def _soll_ist_extrahieren(
    nachricht: str, tb=None
) -> tuple[str, str] | tuple[None, None]:
    """Soll und Ist eines fehlgeschlagenen Vergleichs.

    Zuerst aus den Argumenten von `assertEqual` (`tb` ist der
    Traceback des Fehlschlags), sonst aus der ersten Zeile der
    Meldung, die `assertEqual` als `"<ist> != <soll>"` formatiert,
    bei Folgen mit einem Vorsatz wie „Lists differ: “."""
    soll, ist = _werte_aus_assertequal(tb)
    if soll is not None:
        return soll, ist
    erste_zeile = nachricht.split("\n", 1)[0]
    treffer = _SOLL_IST_MUSTER.match(erste_zeile)
    if treffer is None:
        return None, None
    return treffer.group("soll"), treffer.group("ist")


class _Eintraege(list):
    """Eine Liste, die jeden neuen Eintrag sofort meldet."""

    def append(self, eintrag: dict) -> None:
        super().append(eintrag)
        _melden(eintrag)


class _StrukturiertesErgebnis(unittest.TestResult):
    def __init__(self) -> None:
        super().__init__()
        self.eintraege: list[dict] = _Eintraege()
        self._start: dict[unittest.TestCase, float] = {}

    def startTest(self, test: unittest.TestCase) -> None:
        super().startTest(test)
        _melden({"start": test.id(), "modul": type(test).__module__})
        self._start[test] = time.perf_counter()

    def _dauer(self, test: unittest.TestCase) -> float:
        return time.perf_counter() - self._start.get(test, time.perf_counter())

    def addSuccess(self, test: unittest.TestCase) -> None:
        super().addSuccess(test)
        self.eintraege.append(
            {"id": test.id(), "status": "bestanden", "dauer": self._dauer(test)}
        )

    def addFailure(self, test: unittest.TestCase, err) -> None:
        # Vor super().addFailure(): TestResult schneidet dort beim
        # Aufbereiten die Rahmen aus unittest vom Traceback ab, und
        # mit ihnen den Aufruf von assertEqual.
        nachricht = str(err[1])
        soll, ist = _soll_ist_extrahieren(nachricht, err[2])
        super().addFailure(test, err)
        self.eintraege.append(
            {
                "id": test.id(),
                "status": "fehlgeschlagen",
                "dauer": self._dauer(test),
                "nachricht": nachricht,
                "soll": soll,
                "ist": ist,
            }
        )

    def addError(self, test: unittest.TestCase, err) -> None:
        super().addError(test, err)
        test_id = test.id()
        nachricht = str(err[1])
        # Eine Testdatei, die sich nicht importieren lässt, meldet
        # unittest als Test "unittest.loader._FailedTest.<modul>" mit
        # englischem Text. Im Test-Explorer soll stattdessen die Datei
        # stehen und auf Deutsch, was passiert ist.
        if type(test).__name__ == "_FailedTest":
            test_id = test._testMethodName
            nachricht = ladefehler_meldung(test_id, nachricht)
        self.eintraege.append(
            {
                "id": test_id,
                "status": "fehler",
                "dauer": self._dauer(test),
                "nachricht": nachricht,
                "soll": None,
                "ist": None,
            }
        )


_EINGABE_HINWEIS = (
    "Beim Laden wurde input() aufgerufen, im Testlauf gibt es aber "
    "keine Eingabe. Das Hauptprogramm gehört in die Funktion main() "
    "von u_main.py; beim Import läuft nur, was außerhalb von "
    "Funktionen steht."
)


def ladefehler_meldung(modul: str, text: str) -> str:
    """Deutsche Meldung für eine Testdatei, deren Import scheitert.
    `text` ist die Meldung von unittest („Failed to import test
    module: …“ und der Traceback) oder ein eigener Traceback."""
    zeilen = text.splitlines()
    if zeilen and zeilen[0].startswith("Failed to import test module"):
        zeilen = zeilen[1:]
    traceback_text = "\n".join(zeilen).strip()
    letzte = next((z for z in reversed(zeilen) if z.strip()), "")
    teile = [f"Die Testdatei {modul}.py lässt sich nicht laden."]
    if letzte.startswith("EOFError"):
        teile.append(_EINGABE_HINWEIS)
    if traceback_text:
        teile.append(traceback_text)
    return "\n\n".join(teile)


class _Lader(unittest.TestLoader):
    """Meldet jedes Testmodul vor dem Import und lässt die Module aus
    `auslassen` ganz weg.

    Übersprungen wird schon der Import, weil auch er abstürzen kann,
    etwa mit einem Formular auf oberster Ebene der Testdatei. An
    Stelle des Moduls tritt ein leeres, in dem `discover` keine Tests
    findet."""

    def __init__(self, auslassen: set[str]) -> None:
        super().__init__()
        self._auslassen = auslassen

    def _get_module_from_name(self, name: str) -> types.ModuleType:
        if name in self._auslassen:
            return types.ModuleType(name)
        _melden({"laden": name})
        return super()._get_module_from_name(name)


def _suite_erzeugen(
    pattern: str, ziel: str | None, auslassen: set[str]
) -> unittest.TestSuite:
    lader = _Lader(auslassen)
    if ziel:
        return lader.loadTestsFromName(ziel)
    return lader.discover(start_dir=".", pattern=pattern)


def main() -> None:
    # Python legt bei "python harness.py" automatisch das Verzeichnis
    # DIESES Skripts in sys.path[0] ab, nicht das aktuelle Arbeits-
    # verzeichnis - loadTestsFromName() (für --ziel) bräuchte sonst das
    # Projektverzeichnis selbst, um test_*.py dort zu importieren.
    # discover() betrifft das nicht, das durchsucht das Dateisystem direkt.
    if "" not in sys.path and "." not in sys.path:
        sys.path.insert(0, "")

    parser = argparse.ArgumentParser()
    parser.add_argument("--pattern", default="test_*.py")
    parser.add_argument("--ziel", default=None)
    parser.add_argument("--auslassen", action="append", default=[])
    argumente = parser.parse_args()

    # Ein print() im geprüften Code ist im Anfangsunterricht die
    # Regel. Bis 0.3.5 landete es vor dem JSON auf derselben Ausgabe,
    # und der ganze Testlauf scheiterte mit einem JSONDecodeError.
    # Während der Tests geht die Ausgabe deshalb auf die
    # Fehlerausgabe, und das Ergebnis steht hinter einer Marke.
    sys.stdout = sys.stderr
    ergebnis = _StrukturiertesErgebnis()
    try:
        try:
            suite = _suite_erzeugen(
                argumente.pattern,
                argumente.ziel,
                set(argumente.auslassen),
            )
        except Exception:
            # loadTestsFromName reicht Fehler beim Import der Testdatei
            # durch, statt einen _FailedTest zu liefern. Ohne diesen
            # Zweig endete der Lauf ohne Ergebnis.
            modul = (argumente.ziel or "Testlauf").split(".")[0]
            ergebnis.eintraege.append(
                {
                    "id": argumente.ziel or "Testlauf",
                    "status": "fehler",
                    "dauer": 0.0,
                    "nachricht": ladefehler_meldung(
                        modul, traceback.format_exc()
                    ),
                    "soll": None,
                    "ist": None,
                }
            )
        else:
            suite.run(ergebnis)
    finally:
        sys.stdout = _echte_ausgabe

    _melden({"fertig": True})


if __name__ == "__main__":
    main()
    sys.exit(0)
