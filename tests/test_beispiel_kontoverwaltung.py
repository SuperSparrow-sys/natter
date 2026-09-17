"""Abnahmetest für das Beispielprojekt Kontoverwaltung (M5, Schritt 9).

Erweitert `referenz/lazarus/n_konto` um echte SQLite-Persistenz
(Abschnitt 10). Das Projekt wird wie in AGENTS.md vorgeschrieben aus
`beispielprojekte/Kontoverwaltung/` in `tmp_path` kopiert statt direkt
zu verwenden, weil `u_main.py` eine echte `konten.sqlite`-Datei im
Arbeitsverzeichnis anlegt (siehe auch tests/test_m4_abnahme.py für
dieselbe Begründung bei der Ampel).
"""

from __future__ import annotations

import importlib
import shutil
import sqlite3
import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

_PROJEKT_ORDNER = Path(__file__).resolve().parent.parent / "beispielprojekte" / "Kontoverwaltung"
_PROJEKT_MODULE = ("main", "u_main", "u_konto")


@pytest.fixture
def form1_klasse(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    projekt_kopie = tmp_path / "Kontoverwaltung"
    shutil.copytree(_PROJEKT_ORDNER, projekt_kopie)
    monkeypatch.chdir(projekt_kopie)

    sys.path.insert(0, str(projekt_kopie))
    for name in _PROJEKT_MODULE:
        sys.modules.pop(name, None)
    try:
        modul = importlib.import_module("u_main")
        yield modul.Form1
    finally:
        sys.path.remove(str(projekt_kopie))
        for name in _PROJEKT_MODULE:
            sys.modules.pop(name, None)


def test_startet_mit_zwei_beispielkonten(form1_klasse) -> None:
    formular = form1_klasse()

    assert formular.dbg_konten._qwidget.rowCount() == 2
    assert formular.abfrage.field_by_name("besitzer").as_string == "Anna Beispiel"
    assert formular.abfrage.field_by_name("kontostand").as_float == 500.0


def test_datenbankdatei_wird_tatsaechlich_angelegt(form1_klasse) -> None:
    form1_klasse()
    assert Path("konten.sqlite").exists()


def test_einzahlen_erhoeht_den_kontostand_und_zeigt_es_im_grid(form1_klasse) -> None:
    formular = form1_klasse()

    formular.e_betrag.text = "100"
    formular.b_einzahlen._qwidget.click()

    assert formular.abfrage.field_by_name("kontostand").as_float == 600.0
    assert formular.dbg_konten._qwidget.item(0, 2).text() == "600.0"


def test_abheben_mit_zu_wenig_geld_zeigt_meldung_und_aendert_nichts(form1_klasse) -> None:
    formular = form1_klasse()

    formular.e_betrag.text = "1000"
    formular.b_abheben._qwidget.click()

    assert "Nicht genügend Geld" in formular.l_meldung.caption
    assert formular.abfrage.field_by_name("kontostand").as_float == 500.0


def test_abheben_mit_ausreichend_geld_funktioniert(form1_klasse) -> None:
    formular = form1_klasse()

    formular.e_betrag.text = "50"
    formular.b_abheben._qwidget.click()

    assert formular.abfrage.field_by_name("kontostand").as_float == 450.0
    assert formular.l_meldung.caption == ""


def test_besitzer_umbenennen_und_speichern_wird_dauerhaft_in_der_datenbank_uebernommen(
    form1_klasse,
) -> None:
    formular = form1_klasse()

    formular.dbe_besitzer._qwidget.setText("Anna Neu")
    formular.dbe_besitzer._qwidget.editingFinished.emit()
    formular.dbn_konten.knopf_speichern.click()

    assert "Gespeichert" in formular.l_meldung.caption

    # Direkt gegen die Datei geprüft (nicht nur über dieselbe offene
    # Verbindung) - das bestätigt echte Persistenz, keinen reinen
    # In-Memory-Zustand.
    verbindung = sqlite3.connect("konten.sqlite")
    besitzer = verbindung.execute(
        "SELECT besitzer FROM konten WHERE kontonr = '1001'"
    ).fetchone()[0]
    verbindung.close()
    assert besitzer == "Anna Neu"


def test_navigator_vor_wechselt_zum_zweiten_konto(form1_klasse) -> None:
    formular = form1_klasse()

    formular.dbn_konten.knopf_vor.click()

    assert formular.abfrage.field_by_name("besitzer").as_string == "Bo Beispiel"
    assert formular.abfrage.field_by_name("kontostand").as_float == 250.0


def test_neues_konto_ueber_einfuegen_anlegen(form1_klasse) -> None:
    """Nutzer-Feedback: „funktioniert noch nicht richtig mit Person neu
    anlegen" - `on_insert` war bisher gar nicht mit `dbn_konten`
    verknüpft, der „+"-Knopf tat nichts."""
    formular = form1_klasse()

    def eingeben() -> None:
        dialog = QApplication.activeModalWidget()
        dialog.setTextValue("1003")
        dialog.accept()

    QTimer.singleShot(0, eingeben)
    formular.dbn_konten.knopf_einfuegen.click()

    assert "1003" in formular.l_meldung.caption
    assert formular.dbg_konten._qwidget.rowCount() == 3
    verbindung = sqlite3.connect("konten.sqlite")
    zeile = verbindung.execute(
        "SELECT besitzer, kontostand FROM konten WHERE kontonr = '1003'"
    ).fetchone()
    verbindung.close()
    assert zeile == ("", 0.0)


def test_neues_konto_mit_bestehender_kontonummer_wird_abgelehnt(form1_klasse) -> None:
    formular = form1_klasse()

    def eingeben() -> None:
        dialog = QApplication.activeModalWidget()
        dialog.setTextValue("1001")  # existiert schon
        dialog.accept()

    QTimer.singleShot(0, eingeben)
    formular.dbn_konten.knopf_einfuegen.click()

    assert "gibt es schon" in formular.l_meldung.caption
    assert formular.dbg_konten._qwidget.rowCount() == 2


def test_einfuegen_ohne_eingabe_bricht_ab(form1_klasse) -> None:
    formular = form1_klasse()

    def abbrechen() -> None:
        dialog = QApplication.activeModalWidget()
        dialog.reject()

    QTimer.singleShot(0, abbrechen)
    formular.dbn_konten.knopf_einfuegen.click()

    assert formular.dbg_konten._qwidget.rowCount() == 2


def test_konto_ueber_loeschen_entfernen(form1_klasse) -> None:
    """Wie „+" war auch „-" (`on_delete`) bisher nicht verknüpft."""
    formular = form1_klasse()

    formular.dbn_konten.knopf_loeschen.click()

    assert "1001" in formular.l_meldung.caption
    assert formular.dbg_konten._qwidget.rowCount() == 1
    verbindung = sqlite3.connect("konten.sqlite")
    anzahl = verbindung.execute(
        "SELECT COUNT(*) FROM konten WHERE kontonr = '1001'"
    ).fetchone()[0]
    verbindung.close()
    assert anzahl == 0
