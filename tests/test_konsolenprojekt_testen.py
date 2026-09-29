"""Tests in einem frisch angelegten Konsolenprojekt: `u_main.py` lässt
sich ohne Nebenwirkung importieren, der Testlauf hat keine Eingabe,
und eine Testdatei, deren Import scheitert, wird auf Deutsch gemeldet."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from ide.project import projekt_erzeugen
from ide.testrunner import tests_ausfuehren as _ausfuehren

_TESTDATEI = '''\
import unittest

from u_main import verdoppeln


class VerdoppelnTest(unittest.TestCase):
    def test_verdoppeln(self) -> None:
        self.assertEqual(verdoppeln(21), 42)
'''


def _funktion_einfuegen(u_main: Path) -> None:
    """Ergänzt die Vorlage so, wie es eine Schülerin täte: eine eigene
    Funktion über main(), und in main() eine Eingabe."""
    text = u_main.read_text(encoding="utf-8")
    text = text.replace(
        "def main():\n",
        "def verdoppeln(zahl):\n"
        "    return 2 * zahl\n\n\n"
        "def main():\n"
        "    zahl = int(input(\"Zahl: \"))\n"
        "    print(verdoppeln(zahl))\n",
    )
    u_main.write_text(text, encoding="utf-8")


def test_frisches_konsolenprojekt_laesst_funktion_testen(
    tmp_path: Path,
) -> None:
    ziel = tmp_path / "Rechnen"
    projekt_erzeugen("console", ziel, "Rechnen")
    _funktion_einfuegen(ziel / "u_main.py")
    (ziel / "test_neu1.py").write_text(_TESTDATEI, encoding="utf-8")

    ergebnisse = _ausfuehren(ziel, zeitlimit=60)

    assert [(e.id, e.status) for e in ergebnisse] == [
        ("test_neu1.VerdoppelnTest.test_verdoppeln", "bestanden")
    ]


def test_konsolenprojekt_startet_weiter_ueber_main(tmp_path: Path) -> None:
    ziel = tmp_path / "Rechnen"
    projekt_erzeugen("console", ziel, "Rechnen")
    _funktion_einfuegen(ziel / "u_main.py")

    lauf = subprocess.run(
        [sys.executable, "main.py"],
        cwd=ziel,
        input="5\n",
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert lauf.returncode == 0, lauf.stderr
    assert "Hallo, Rechnen!" in lauf.stdout
    assert "10" in lauf.stdout


@pytest.mark.parametrize("ziel_id", [None, "test_neu1"])
def test_ladefehler_wird_deutsch_gemeldet(
    tmp_path: Path, ziel_id: str | None
) -> None:
    (tmp_path / "u_main.py").write_text(
        "name = input('Name: ')\n\n\ndef verdoppeln(zahl):\n"
        "    return 2 * zahl\n",
        encoding="utf-8",
    )
    (tmp_path / "test_neu1.py").write_text(_TESTDATEI, encoding="utf-8")

    ergebnisse = _ausfuehren(tmp_path, ziel=ziel_id, zeitlimit=60)

    assert len(ergebnisse) == 1
    ergebnis = ergebnisse[0]
    assert ergebnis.status == "fehler"
    assert not ergebnis.id.startswith("unittest.")
    assert ergebnis.id.startswith("test_neu1")
    assert ergebnis.nachricht is not None
    assert ergebnis.nachricht.startswith(
        "Die Testdatei test_neu1.py lässt sich nicht laden."
    )
    assert "input()" in ergebnis.nachricht
    assert "Failed to import" not in ergebnis.nachricht


def test_testlauf_bekommt_keine_eingabe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    aufrufe: list[dict] = []

    class _Prozess:
        # Seit Punkt 247 startet der Testlauf mit `Popen` und liest
        # die Ausgabe aus einer Datei. Seit Punkt 425 wertet er auch
        # den Rückgabewert aus.
        returncode = 0

        def __init__(self, befehl, **kwargs) -> None:  # noqa: ANN001
            aufrufe.append(kwargs)

        def wait(self, timeout=None) -> int:  # noqa: ANN001
            return 0

        # Nach dem Lauf wird aufgeräumt, was er hinterlassen hat
        # (Punkt 281); dafür fragt der Testlauf, ob er noch läuft.
        def poll(self) -> int:
            return 0

    monkeypatch.setattr("ide.testrunner.ausfuehrung.subprocess.Popen", _Prozess)

    _ausfuehren(tmp_path)

    assert aufrufe[0]["stdin"] is subprocess.DEVNULL
