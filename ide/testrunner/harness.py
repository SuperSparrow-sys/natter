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
import unittest

_SOLL_IST_MUSTER = re.compile(r"^(?P<ist>.+?) != (?P<soll>.+)$")


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
        self.eintraege.append(
            {
                "id": test.id(),
                "status": "fehler",
                "dauer": self._dauer(test),
                "nachricht": str(err[1]),
                "soll": None,
                "ist": None,
            }
        )


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

    suite = _suite_erzeugen(argumente.pattern, argumente.ziel)
    ergebnis = _StrukturiertesErgebnis()
    suite.run(ergebnis)

    print(json.dumps(ergebnis.eintraege))


if __name__ == "__main__":
    main()
    sys.exit(0)
