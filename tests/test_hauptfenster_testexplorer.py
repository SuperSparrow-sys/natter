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


def test_ohne_projekt_zeigt_hinweis(hauptfenster) -> None:
    """Ohne Projekt laeuft gar nichts an - es gibt nichts abzuwarten."""
    hauptfenster._alle_tests_ausfuehren_aktion()
    meldung = hauptfenster.statusBar().currentMessage()
    assert meldung.startswith("Kein Projekt offen.")
    assert "Projekt → Projekt öffnen …" in meldung


def test_alle_tests_ausfuehren_befuellt_den_baum(
    tmp_path: Path, hintergrund_abwarten, hauptfenster
) -> None:
    _projekt_mit_testdatei(hauptfenster, tmp_path)

    hauptfenster._alle_tests_ausfuehren_aktion()
    hintergrund_abwarten(hauptfenster)

    assert hauptfenster.tests_baum.topLevelItemCount() == 1  # ein Modul: test_beispiel
    modul_eintrag = hauptfenster.tests_baum.topLevelItem(0)
    assert modul_eintrag.text(0) == "test_beispiel"
    assert modul_eintrag.childCount() == 1  # eine Klasse: TestBeispiel
    klassen_eintrag = modul_eintrag.child(0)
    assert klassen_eintrag.text(0) == "TestBeispiel"
    assert klassen_eintrag.childCount() == 2  # zwei Testmethoden


def test_status_und_dauer_werden_pro_test_angezeigt(
    tmp_path: Path, hintergrund_abwarten, hauptfenster
) -> None:
    _projekt_mit_testdatei(hauptfenster, tmp_path)

    hauptfenster._alle_tests_ausfuehren_aktion()
    hintergrund_abwarten(hauptfenster)

    klassen_eintrag = hauptfenster.tests_baum.topLevelItem(0).child(0)
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
    hintergrund_abwarten, hauptfenster,
) -> None:
    _projekt_mit_testdatei(hauptfenster, tmp_path)

    hauptfenster._alle_tests_ausfuehren_aktion()
    hintergrund_abwarten(hauptfenster)

    klassen_eintrag = hauptfenster.tests_baum.topLevelItem(0).child(0)
    fehlschlag = next(
        klassen_eintrag.child(i)
        for i in range(2)
        if klassen_eintrag.child(i).text(0) == "test_fehlschlagend"
    )
    assert "Soll: 50" in fehlschlag.toolTip(1)
    assert "Ist: 45" in fehlschlag.toolTip(1)


def test_statusleiste_zeigt_anzahl_und_fehlschlaege(
    tmp_path: Path, hintergrund_abwarten, hauptfenster
) -> None:
    _projekt_mit_testdatei(hauptfenster, tmp_path)

    hauptfenster._alle_tests_ausfuehren_aktion()
    hintergrund_abwarten(hauptfenster)

    meldung = hauptfenster.statusBar().currentMessage()
    assert meldung.startswith("2 Tests gelaufen, 1 nicht bestanden")
    assert "Test-Explorer" in meldung


def test_doppelklick_fuehrt_genau_diesen_test_erneut_aus(
    tmp_path: Path,
    hintergrund_abwarten, hauptfenster,
) -> None:
    _projekt_mit_testdatei(hauptfenster, tmp_path)
    hauptfenster._alle_tests_ausfuehren_aktion()
    hintergrund_abwarten(hauptfenster)

    klassen_eintrag = hauptfenster.tests_baum.topLevelItem(0).child(0)
    bestehend = next(
        klassen_eintrag.child(i)
        for i in range(2)
        if klassen_eintrag.child(i).text(0) == "test_bestehend"
    )

    # main.py wird kaputt gemacht, aber test_beispiel.py bleibt gültig -
    # ein erneuter GEZIELTER Lauf dieses einen Tests muss trotzdem
    # funktionieren, weil er unabhängig vom Rest des Projekts ist.
    hauptfenster._bei_test_doppelklick(bestehend, 0)
    hintergrund_abwarten(hauptfenster)

    assert bestehend.text(1) == "bestanden"


def test_doppelklick_auf_klassen_knoten_aktualisiert_alle_ihre_tests(
    tmp_path: Path,
    hintergrund_abwarten, hauptfenster,
) -> None:
    _projekt_mit_testdatei(hauptfenster, tmp_path)
    hauptfenster._alle_tests_ausfuehren_aktion()
    hintergrund_abwarten(hauptfenster)

    modul_eintrag = hauptfenster.tests_baum.topLevelItem(0)
    klassen_eintrag = modul_eintrag.child(0)
    assert klassen_eintrag.text(0) == "TestBeispiel"

    hauptfenster._bei_test_doppelklick(klassen_eintrag, 0)
    hintergrund_abwarten(hauptfenster)

    status = {klassen_eintrag.child(i).text(0): klassen_eintrag.child(i).text(1) for i in range(2)}
    assert status == {"test_bestehend": "bestanden", "test_fehlschlagend": "fehlgeschlagen"}


def _eintrag(fenster: HauptFenster, name: str):  # noqa: ANN202
    klassen_eintrag = fenster.tests_baum.topLevelItem(0).child(0)
    return next(
        klassen_eintrag.child(i)
        for i in range(klassen_eintrag.childCount())
        if klassen_eintrag.child(i).text(0) == name
    )


def test_doppelklick_speichert_vorher_und_testet_den_neuen_stand(
    tmp_path: Path,
    hintergrund_abwarten, hauptfenster,
) -> None:
    # Punkt 185: eine geänderte, nicht gespeicherte Testdatei ergab
    # weiter „bestanden“.
    _projekt_mit_testdatei(hauptfenster, tmp_path)
    hauptfenster._alle_tests_ausfuehren_aktion()
    hintergrund_abwarten(hauptfenster)
    bestehend = _eintrag(hauptfenster, "test_bestehend")
    assert bestehend.text(1) == "bestanden"

    editor = hauptfenster.datei_oeffnen(tmp_path / "test_beispiel.py")
    neu = editor.toPlainText().replace("2 + 2, 4", "1, 2")
    editor.selectAll()
    editor.insertPlainText(neu)
    assert editor.document().isModified()

    hauptfenster._bei_test_doppelklick(bestehend, 0)
    hintergrund_abwarten(hauptfenster)

    assert "1, 2" in (tmp_path / "test_beispiel.py").read_text(
        encoding="utf-8"
    )
    assert _eintrag(hauptfenster, "test_bestehend").text(1) == "fehlgeschlagen"


def test_doppelklick_auf_eine_endlosschleife_haelt_das_fenster_nicht_an(
    tmp_path: Path,
    hintergrund_abwarten,
    monkeypatch: pytest.MonkeyPatch, hauptfenster_bauen,
) -> None:
    # Punkt 185: der Lauf geschah im Faden der Oberfläche und endete
    # nach dem Zeitlimit mit einem unbehandelten TimeoutExpired.
    import time

    from ide.shell import hauptfenster
    from ide.testrunner.ausfuehrung import tests_ausfuehren

    monkeypatch.setattr(
        hauptfenster,
        "tests_ausfuehren",
        lambda ordner, **k: tests_ausfuehren(ordner, zeitlimit=4, **k),
    )
    fenster = hauptfenster_bauen()
    _projekt_mit_testdatei(fenster, tmp_path)
    fenster._alle_tests_ausfuehren_aktion()
    hintergrund_abwarten(fenster)
    bestehend = _eintrag(fenster, "test_bestehend")
    (tmp_path / "test_beispiel.py").write_text(
        _TESTDATEI_INHALT.replace(
            "self.assertEqual(2 + 2, 4)", "while True:\n            pass"
        ),
        encoding="utf-8",
    )

    beginn = time.monotonic()
    fenster._bei_test_doppelklick(bestehend, 0)
    dauer = time.monotonic() - beginn

    assert dauer < 2
    assert fenster._hintergrundarbeit.isRunning()
    hintergrund_abwarten(fenster)
    eintrag = _eintrag(fenster, "test_bestehend")
    assert eintrag.text(1) == "fehler"
    assert "Sekunden abgebrochen" in eintrag.toolTip(1)


def test_neue_test_unit_erzeugt_eine_lauffaehige_unittest_datei(
    tmp_path: Path,
    hintergrund_abwarten, hauptfenster,
) -> None:
    _projekt_mit_testdatei(hauptfenster, tmp_path)

    hauptfenster._neue_test_unit_aktion()

    neue_datei = tmp_path / "test_neu1.py"
    assert neue_datei.exists()
    assert "unittest" in neue_datei.read_text(encoding="utf-8")

    hauptfenster._alle_tests_ausfuehren_aktion()
    hintergrund_abwarten(hauptfenster)
    module = {
        hauptfenster.tests_baum.topLevelItem(i).text(0)
        for i in range(hauptfenster.tests_baum.topLevelItemCount())
    }
    assert "test_neu1" in module


def test_export_ohne_vorherigen_lauf_zeigt_hinweis(hauptfenster) -> None:
    hauptfenster._testergebnisse_exportieren_aktion()
    meldung = hauptfenster.statusBar().currentMessage()
    assert meldung.startswith("Noch keine Testergebnisse zum Exportieren")
    assert "Tests ausführen" in meldung


def test_export_schreibt_eine_gueltige_html_datei(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
, hintergrund_abwarten, hauptfenster) -> None:
    _projekt_mit_testdatei(hauptfenster, tmp_path)
    hauptfenster._alle_tests_ausfuehren_aktion()
    hintergrund_abwarten(hauptfenster)

    ziel = tmp_path / "protokoll.html"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(ziel), "HTML (*.html)"))
    )

    hauptfenster._testergebnisse_exportieren_aktion()

    inhalt = ziel.read_text(encoding="utf-8")
    assert "<html" in inhalt
    assert "test_bestehend" in inhalt
    assert "Soll: 50" not in inhalt  # Soll/Ist stehen in eigenen Zellen, nicht als Text
    assert '<td class="mehrzeilig">50</td>' in inhalt


def test_eine_freie_testfunktion_haengt_direkt_am_modul(hauptfenster) -> None:  # noqa: ANN001
    """Punkt 508: `test_kurz.test_start` hat keine Klasse; ohne die
    Unterscheidung stand der Name der Funktion als Klasse da und der
    Test noch einmal darunter."""
    from ide.testrunner.ausfuehrung import Testergebnis

    hauptfenster._tests_baum_befuellen([
        Testergebnis("test_kurz.test_start", "bestanden", 0.0),
        Testergebnis("test_klasse.KontoTest.test_x", "bestanden", 0.0),
    ])

    baum = hauptfenster.tests_baum
    module = {baum.topLevelItem(i).text(0): baum.topLevelItem(i)
              for i in range(baum.topLevelItemCount())}
    kurz = module["test_kurz"]
    assert [kurz.child(i).text(0) for i in range(kurz.childCount())] == ["test_start"]
    assert kurz.child(0).childCount() == 0
    klasse = module["test_klasse"].child(0)
    assert klasse.text(0) == "KontoTest" and klasse.child(0).text(0) == "test_x"
