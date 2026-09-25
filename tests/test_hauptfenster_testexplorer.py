"""Tests für den Test-Explorer in HauptFenster (Abschnitt 8.6): Panel
„Tests“, „Alle Tests ausführen“, Doppelklick führt einen einzelnen Test
erneut aus, „Neue Test-Unit“. Siehe Arbeitspaket M4, Schritt 7.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PySide6.QtWidgets import QFileDialog

from ide.shell.hauptfenster import HauptFenster

_TESTDATEI_INHALT = '''\
import unittest


class TestBeispiel(unittest.TestCase):
    def test_bestehend(self):
        self.assertEqual(2 + 2, 4)

    def test_fehlschlagend(self):
        self.assertEqual(45, 50)
'''


def _projekt_mit_testdatei(fenster: HauptFenster, ordner: Path) -> None:
    ordner.mkdir(parents=True, exist_ok=True)
    (ordner / "main.py").write_text("pass\n", encoding="utf-8")
    (ordner / "test_beispiel.py").write_text(_TESTDATEI_INHALT, encoding="utf-8")
    daten = {"format": "natter-project/1", "name": "Test", "type": "console", "main": "main.py"}
    natter_pfad = ordner / "test.natter"
    natter_pfad.write_text(json.dumps(daten), encoding="utf-8")
    fenster.projekt_oeffnen(natter_pfad)


def test_ohne_projekt_zeigt_hinweis() -> None:
    """Ohne Projekt laeuft gar nichts an - es gibt nichts abzuwarten."""
    fenster = HauptFenster()
    fenster._alle_tests_ausfuehren_aktion()
    meldung = fenster.statusBar().currentMessage()
    assert meldung.startswith("Kein Projekt offen.")
    assert "Projekt → Öffnen" in meldung


def test_alle_tests_ausfuehren_befuellt_den_baum(tmp_path: Path, hintergrund_abwarten) -> None:
    fenster = HauptFenster()
    _projekt_mit_testdatei(fenster, tmp_path)

    fenster._alle_tests_ausfuehren_aktion()
    hintergrund_abwarten(fenster)

    assert fenster.tests_baum.topLevelItemCount() == 1  # ein Modul: test_beispiel
    modul_eintrag = fenster.tests_baum.topLevelItem(0)
    assert modul_eintrag.text(0) == "test_beispiel"
    assert modul_eintrag.childCount() == 1  # eine Klasse: TestBeispiel
    klassen_eintrag = modul_eintrag.child(0)
    assert klassen_eintrag.text(0) == "TestBeispiel"
    assert klassen_eintrag.childCount() == 2  # zwei Testmethoden


def test_status_und_dauer_werden_pro_test_angezeigt(tmp_path: Path, hintergrund_abwarten) -> None:
    fenster = HauptFenster()
    _projekt_mit_testdatei(fenster, tmp_path)

    fenster._alle_tests_ausfuehren_aktion()
    hintergrund_abwarten(fenster)

    klassen_eintrag = fenster.tests_baum.topLevelItem(0).child(0)
    eintraege = {klassen_eintrag.child(i).text(0): klassen_eintrag.child(i) for i in range(2)}
    assert eintraege["test_bestehend"].text(1) == "bestanden"
    assert eintraege["test_fehlschlagend"].text(1) == "fehlgeschlagen"

    # Die Dauer steht deutsch da - „0,003" und nicht „0.003" (Nutzer,
    # : „Alles in Deutschem Format"). Deshalb erst das
    # Komma zurücktauschen, bevor hier gerechnet wird.
    dauer = eintraege["test_bestehend"].text(2)
    assert "." not in dauer
    assert float(dauer.replace(",", ".")) >= 0


def test_fehlgeschlagener_test_zeigt_soll_ist_als_tooltip(
    tmp_path: Path,
    hintergrund_abwarten,
) -> None:
    fenster = HauptFenster()
    _projekt_mit_testdatei(fenster, tmp_path)

    fenster._alle_tests_ausfuehren_aktion()
    hintergrund_abwarten(fenster)

    klassen_eintrag = fenster.tests_baum.topLevelItem(0).child(0)
    fehlschlag = next(
        klassen_eintrag.child(i)
        for i in range(2)
        if klassen_eintrag.child(i).text(0) == "test_fehlschlagend"
    )
    assert "Soll: 50" in fehlschlag.toolTip(1)
    assert "Ist: 45" in fehlschlag.toolTip(1)


def test_statusleiste_zeigt_anzahl_und_fehlschlaege(tmp_path: Path, hintergrund_abwarten) -> None:
    fenster = HauptFenster()
    _projekt_mit_testdatei(fenster, tmp_path)

    fenster._alle_tests_ausfuehren_aktion()
    hintergrund_abwarten(fenster)

    meldung = fenster.statusBar().currentMessage()
    assert meldung.startswith("2 Tests gelaufen, 1 nicht bestanden")
    assert "Test-Explorer" in meldung


def test_doppelklick_fuehrt_genau_diesen_test_erneut_aus(
    tmp_path: Path,
    hintergrund_abwarten,
) -> None:
    fenster = HauptFenster()
    _projekt_mit_testdatei(fenster, tmp_path)
    fenster._alle_tests_ausfuehren_aktion()
    hintergrund_abwarten(fenster)

    klassen_eintrag = fenster.tests_baum.topLevelItem(0).child(0)
    bestehend = next(
        klassen_eintrag.child(i)
        for i in range(2)
        if klassen_eintrag.child(i).text(0) == "test_bestehend"
    )

    # main.py wird kaputt gemacht, aber test_beispiel.py bleibt gültig -
    # ein erneuter GEZIELTER Lauf dieses einen Tests muss trotzdem
    # funktionieren, weil er unabhängig vom Rest des Projekts ist.
    fenster._bei_test_doppelklick(bestehend, 0)

    assert bestehend.text(1) == "bestanden"


def test_doppelklick_auf_klassen_knoten_aktualisiert_alle_ihre_tests(
    tmp_path: Path,
    hintergrund_abwarten,
) -> None:
    fenster = HauptFenster()
    _projekt_mit_testdatei(fenster, tmp_path)
    fenster._alle_tests_ausfuehren_aktion()
    hintergrund_abwarten(fenster)

    modul_eintrag = fenster.tests_baum.topLevelItem(0)
    klassen_eintrag = modul_eintrag.child(0)
    assert klassen_eintrag.text(0) == "TestBeispiel"

    fenster._bei_test_doppelklick(klassen_eintrag, 0)

    status = {klassen_eintrag.child(i).text(0): klassen_eintrag.child(i).text(1) for i in range(2)}
    assert status == {"test_bestehend": "bestanden", "test_fehlschlagend": "fehlgeschlagen"}


def test_neue_test_unit_erzeugt_eine_lauffaehige_unittest_datei(
    tmp_path: Path,
    hintergrund_abwarten,
) -> None:
    fenster = HauptFenster()
    _projekt_mit_testdatei(fenster, tmp_path)

    fenster._neue_test_unit_aktion()

    neue_datei = tmp_path / "test_neu1.py"
    assert neue_datei.exists()
    assert "unittest" in neue_datei.read_text(encoding="utf-8")

    fenster._alle_tests_ausfuehren_aktion()
    hintergrund_abwarten(fenster)
    module = {
        fenster.tests_baum.topLevelItem(i).text(0)
        for i in range(fenster.tests_baum.topLevelItemCount())
    }
    assert "test_neu1" in module


def test_export_ohne_vorherigen_lauf_zeigt_hinweis() -> None:
    fenster = HauptFenster()
    fenster._testergebnisse_exportieren_aktion()
    meldung = fenster.statusBar().currentMessage()
    assert meldung.startswith("Noch keine Testergebnisse zum Exportieren")
    assert "Tests ausführen" in meldung


def test_export_schreibt_eine_gueltige_html_datei(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
, hintergrund_abwarten) -> None:
    fenster = HauptFenster()
    _projekt_mit_testdatei(fenster, tmp_path)
    fenster._alle_tests_ausfuehren_aktion()
    hintergrund_abwarten(fenster)

    ziel = tmp_path / "protokoll.html"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(ziel), "HTML (*.html)"))
    )

    fenster._testergebnisse_exportieren_aktion()

    inhalt = ziel.read_text(encoding="utf-8")
    assert "<html" in inhalt
    assert "test_bestehend" in inhalt
    assert "Soll: 50" not in inhalt  # Soll/Ist stehen in eigenen Zellen, nicht als Text
    assert "<td>50</td>" in inhalt
