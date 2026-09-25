"""Tests für ide/testrunner/ausfuehrung.py: Tests als eigener Prozess
ausführen, strukturiertes Ergebnis statt Textausgabe (Abschnitt 8.6).
Siehe Arbeitspaket M4, Schritt 7.
"""

from __future__ import annotations

from pathlib import Path

from ide.testrunner import tests_ausfuehren as ausfuehren

_TESTDATEI_INHALT = '''\
import unittest


class TestBeispiel(unittest.TestCase):
    def test_bestehend(self):
        self.assertEqual(2 + 2, 4)

    def test_fehlschlagend(self):
        self.assertEqual(45, 50)

    def test_wirft_fehler(self):
        raise RuntimeError("kaputt")
'''


def _projekt_mit_testdatei(tmp_path: Path) -> Path:
    (tmp_path / "test_beispiel.py").write_text(_TESTDATEI_INHALT, encoding="utf-8")
    return tmp_path


def test_entdeckt_und_fuehrt_alle_tests_aus(tmp_path: Path) -> None:
    projekt = _projekt_mit_testdatei(tmp_path)
    ergebnisse = ausfuehren(projekt)

    namen = {e.id.rsplit(".", 1)[-1]: e for e in ergebnisse}
    assert set(namen) == {"test_bestehend", "test_fehlschlagend", "test_wirft_fehler"}
    assert namen["test_bestehend"].status == "bestanden"
    assert namen["test_fehlschlagend"].status == "fehlgeschlagen"
    assert namen["test_wirft_fehler"].status == "fehler"


def test_soll_ist_werden_bei_assertequal_fehlschlag_extrahiert(tmp_path: Path) -> None:
    projekt = _projekt_mit_testdatei(tmp_path)
    ergebnisse = ausfuehren(projekt)

    fehlschlag = next(e for e in ergebnisse if e.id.endswith("test_fehlschlagend"))
    assert fehlschlag.soll == "50"
    assert fehlschlag.ist == "45"


def test_fehler_hat_keine_soll_ist_werte(tmp_path: Path) -> None:
    projekt = _projekt_mit_testdatei(tmp_path)
    ergebnisse = ausfuehren(projekt)

    fehler = next(e for e in ergebnisse if e.id.endswith("test_wirft_fehler"))
    assert fehler.soll is None
    assert fehler.ist is None
    assert fehler.nachricht == "kaputt"


def test_jeder_test_hat_eine_dauer_ab_0(tmp_path: Path) -> None:
    projekt = _projekt_mit_testdatei(tmp_path)
    ergebnisse = ausfuehren(projekt)

    assert all(e.dauer >= 0 for e in ergebnisse)


def test_ziel_beschraenkt_auf_eine_einzelne_methode(tmp_path: Path) -> None:
    projekt = _projekt_mit_testdatei(tmp_path)
    ergebnisse = ausfuehren(projekt, ziel="test_beispiel.TestBeispiel.test_bestehend")

    assert len(ergebnisse) == 1
    assert ergebnisse[0].id.endswith("test_bestehend")


def test_leerer_projektordner_liefert_keine_ergebnisse(tmp_path: Path) -> None:
    assert ausfuehren(tmp_path) == []
