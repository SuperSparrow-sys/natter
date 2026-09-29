"""Eigenständiges Testlauf-Skript (Abschnitt 8.6, 19): läuft als eigener
Prozess im Projektordner, entdeckt `test_*.py`-Dateien mit der
Standardbibliothek `unittest`, führt sie aus und gibt ein strukturiertes
JSON-Ergebnis auf stdout aus statt Textausgabe zu parsen.

Braucht absichtlich nichts aus `pcl`/`ide` – reines `unittest`, damit
Schülertests genau das ausführen, was sie mit `python -m unittest` auch
in der Kommandozeile täten (Abschnitt 8.6: „Tests in Dateien `test_*.py`
mit `unittest`“).

Aufruf: `python harness.py [--pattern MUSTER] [--ziel PUNKT.GETRENNTE.ID]`
`--ziel` adressiert wie `unittest`selbst ein Modul, eine Klasse oder eine
einzelne Methode (`test_x`, `test_x.Klasse`, `test_x.Klasse.methode`).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import traceback
import unittest

_SOLL_IST_MUSTER = re.compile(r"^(?P<ist>.+?) != (?P<soll>.+)$")

#: Steht in der Standardausgabe unmittelbar vor dem JSON-Ergebnis.
#: `ausfuehrung.py` liest nur, was danach kommt; alles davor hat der
#: getestete Code selbst geschrieben.
ERGEBNIS_MARKE = "@@natter-testergebnis@@"


def _soll_ist_extrahieren(nachricht: str) -> tuple[str, str] | tuple[None, None]:
    """`assertEqual` formatiert Fehlschläge standardmäßig als
    `"<ist> != <soll>"` (erste Zeile der Meldung, vor einem optionalen
    eigenen `msg`-Zusatz)."""
    erste_zeile = nachricht.split("\n", 1)[0]
    treffer = _SOLL_IST_MUSTER.match(erste_zeile)
    if treffer is None:
        return None, None
    return treffer.group("soll"), treffer.group("ist")


class _StrukturiertesErgebnis(unittest.TestResult):
    def __init__(self) -> None:
        super().__init__()
        self.eintraege: list[dict] = []
        self._start: dict[unittest.TestCase, float] = {}

    def startTest(self, test: unittest.TestCase) -> None:
        super().startTest(test)
        self._start[test] = time.perf_counter()

    def _dauer(self, test: unittest.TestCase) -> float:
        return time.perf_counter() - self._start.get(test, time.perf_counter())

    def addSuccess(self, test: unittest.TestCase) -> None:
        super().addSuccess(test)
        self.eintraege.append(
            {"id": test.id(), "status": "bestanden", "dauer": self._dauer(test)}
        )

    def addFailure(self, test: unittest.TestCase, err) -> None:
        super().addFailure(test, err)
        nachricht = str(err[1])
        soll, ist = _soll_ist_extrahieren(nachricht)
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


def _suite_erzeugen(pattern: str, ziel: str | None) -> unittest.TestSuite:
    lader = unittest.TestLoader()
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
    argumente = parser.parse_args()

    # Ein print() im geprüften Code ist im Anfangsunterricht die
    # Regel. Bis 0.3.5 landete es vor dem JSON auf derselben Ausgabe,
    # und der ganze Testlauf scheiterte mit einem JSONDecodeError.
    # Während der Tests geht die Ausgabe deshalb auf die
    # Fehlerausgabe, und das Ergebnis steht hinter einer Marke.
    echte_ausgabe = sys.stdout
    sys.stdout = sys.stderr
    ergebnis = _StrukturiertesErgebnis()
    try:
        try:
            suite = _suite_erzeugen(argumente.pattern, argumente.ziel)
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
        sys.stdout = echte_ausgabe

    print(ERGEBNIS_MARKE)
    print(json.dumps(ergebnis.eintraege))


if __name__ == "__main__":
    main()
    sys.exit(0)
