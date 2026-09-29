"""Eine offene Transaktion im Datenbank-Panel vor dem Start und vor
dem Schließen (Punkt 276).

Solange im Panel eine mit BEGIN begonnene Transaktion offen ist, hält
Natter die Sperre auf der Datenbankdatei. Bis 0.3.6 startete F5
trotzdem ohne ein Wort, und das Programm scheiterte beim Schreiben
nach fünf Sekunden mit „database is locked“. Beim Schließen von
Natter nahm `trennen()` die Transaktion wortlos zurück.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from PySide6.QtWidgets import QMessageBox

from ide.shell.hauptfenster import TRANSAKTION_EINTRAG, HauptFenster
from pcl import SQLite3Connection


class _Beendet:
    """Steht für ein Programm, das schon wieder zu Ende ist."""

    pid = 0
    stdout = None
    returncode = 0

    def poll(self) -> int:
        return 0

    def wait(self, timeout: float | None = None) -> int:
        return 0

    def kill(self) -> None:
        pass


def _projekt(ordner: Path) -> Path:
    (ordner / "main.py").write_text("pass\n", encoding="utf-8")
    daten = {
        "format": "natter-project/1",
        "name": "Test",
        "type": "gui",
        "main": "main.py",
    }
    pfad = ordner / "test.natter"
    pfad.write_text(json.dumps(daten), encoding="utf-8")
    return pfad


def _von_aussen(pfad: Path) -> list[tuple[int, str]]:
    with closing(sqlite3.connect(pfad, timeout=0)) as pruefung:
        return pruefung.execute(
            "SELECT nr, name FROM schueler ORDER BY nr"
        ).fetchall()


def _ausfuehren(fenster: HauptFenster, sql: str) -> None:
    panel = fenster.datenbank_panel
    panel._sql_eingabe.setPlainText(sql)
    panel._sql_ausfuehren()


@pytest.fixture
def fenster_mit_transaktion(
    tmp_path: Path, hauptfenster: HauptFenster, monkeypatch
):
    """Ein Hauptfenster mit Projekt, dessen Datenbank-Panel nach
    BEGIN und INSERT eine offene Transaktion hält. Gestartet wird
    ein Ersatz; gezählt wird, wie oft."""
    db = SQLite3Connection(tmp_path / "klasse.db")
    db.execute("CREATE TABLE schueler (nr INTEGER PRIMARY KEY, name TEXT)")
    db.execute("INSERT INTO schueler VALUES (1, 'Ada')")
    db.connected = False

    fenster = hauptfenster
    fenster.projekt_oeffnen(_projekt(tmp_path))
    panel = fenster.datenbank_panel
    panel._sqlite_pfad.setText("klasse.db")
    panel._verbinden()
    assert panel.verbindung is not None, panel._status_label.text()
    _ausfuehren(fenster, "BEGIN")
    _ausfuehren(fenster, "INSERT INTO schueler VALUES (2, 'Grace')")
    assert panel.transaktion_offen

    gestartet: list[object] = []

    def starten(projekt, **_):
        gestartet.append(projekt)
        return _Beendet()

    monkeypatch.setattr(
        "ide.shell.hauptfenster.projekt_starten", starten
    )
    fenster.gestartet = gestartet
    fenster.datei = tmp_path / "klasse.db"
    yield fenster
    fenster.laufender_prozess = None


def _antwort_beim_start(monkeypatch, antwort: str) -> list[int]:
    gefragt: list[int] = []

    def fragen(_self) -> str:
        gefragt.append(1)
        return antwort

    monkeypatch.setattr(
        HauptFenster,
        "_transaktion_vor_dem_start_fragen",
        fragen,
        raising=False,
    )
    return gefragt


def test_festschreiben_vor_dem_start(
    fenster_mit_transaktion, monkeypatch
) -> None:
    fenster = fenster_mit_transaktion
    gefragt = _antwort_beim_start(monkeypatch, "festschreiben")

    fenster._projekt_starten_aktion()

    assert gefragt == [1]
    assert len(fenster.gestartet) == 1
    assert not fenster.datenbank_panel.transaktion_offen
    assert _von_aussen(fenster.datei) == [(1, "Ada"), (2, "Grace")]


def test_zuruecknehmen_vor_dem_start(
    fenster_mit_transaktion, monkeypatch
) -> None:
    fenster = fenster_mit_transaktion
    _antwort_beim_start(monkeypatch, "zuruecknehmen")

    fenster._projekt_starten_aktion()

    assert len(fenster.gestartet) == 1
    assert not fenster.datenbank_panel.transaktion_offen
    # Die Verbindung bleibt; nur die Transaktion ist weg.
    assert fenster.datenbank_panel.verbindung is not None
    assert _von_aussen(fenster.datei) == [(1, "Ada")]


def test_abbrechen_startet_weder_so_noch_mit_debugger(
    fenster_mit_transaktion, monkeypatch
) -> None:
    fenster = fenster_mit_transaktion
    gefragt = _antwort_beim_start(monkeypatch, "abbrechen")

    fenster._projekt_starten_aktion()
    fenster._mit_debugger_starten()

    assert gefragt == [1, 1]
    assert fenster.gestartet == []
    assert fenster.debug_sitzung is None
    assert fenster.datenbank_panel.transaktion_offen
    assert "Transaktion offen" in fenster.statusBar().currentMessage()


def test_ohne_offene_transaktion_wird_nicht_gefragt(
    fenster_mit_transaktion, monkeypatch
) -> None:
    fenster = fenster_mit_transaktion
    _ausfuehren(fenster, "COMMIT")
    gefragt = _antwort_beim_start(monkeypatch, "abbrechen")

    fenster._projekt_starten_aktion()

    assert gefragt == []
    assert len(fenster.gestartet) == 1


def _antwort_beim_schliessen(monkeypatch, knopf) -> list[list[str]]:
    gefragt: list[list[str]] = []

    def fragen(_self, namen):
        gefragt.append(list(namen))
        return knopf

    monkeypatch.setattr(HauptFenster, "_vor_dem_schliessen_fragen", fragen)
    return gefragt


def test_speichern_beim_schliessen_schreibt_die_transaktion_fest(
    fenster_mit_transaktion, monkeypatch
) -> None:
    fenster = fenster_mit_transaktion
    gefragt = _antwort_beim_schliessen(
        monkeypatch, QMessageBox.StandardButton.Save
    )

    assert fenster.close()

    assert gefragt == [[TRANSAKTION_EINTRAG]]
    assert _von_aussen(fenster.datei) == [(1, "Ada"), (2, "Grace")]


def test_verwerfen_beim_schliessen_nimmt_zurueck(
    fenster_mit_transaktion, monkeypatch
) -> None:
    fenster = fenster_mit_transaktion
    gefragt = _antwort_beim_schliessen(
        monkeypatch, QMessageBox.StandardButton.Discard
    )

    assert fenster.close()

    assert gefragt == [[TRANSAKTION_EINTRAG]]
    assert _von_aussen(fenster.datei) == [(1, "Ada")]


def test_abbrechen_beim_schliessen_laesst_alles_offen(
    fenster_mit_transaktion, monkeypatch
) -> None:
    fenster = fenster_mit_transaktion
    _antwort_beim_schliessen(monkeypatch, QMessageBox.StandardButton.Cancel)

    assert not fenster.close()

    assert fenster.datenbank_panel.transaktion_offen
    # Danach nimmt die Voreinstellung der Tests zurück, damit die
    # Fixture das Fenster schließen kann.
    monkeypatch.setattr(
        HauptFenster,
        "_vor_dem_schliessen_fragen",
        lambda self, namen: QMessageBox.StandardButton.Discard,
    )


def test_projektwechsel_fragt_nach_der_transaktion(
    fenster_mit_transaktion, monkeypatch, tmp_path: Path
) -> None:
    """Auch wenn dasselbe Projekt noch einmal geöffnet wird: die
    Verbindung des Panels geht dabei zu."""
    fenster = fenster_mit_transaktion
    gefragt = _antwort_beim_schliessen(
        monkeypatch, QMessageBox.StandardButton.Save
    )

    fenster.projekt_oeffnen(tmp_path / "test.natter")

    assert gefragt == [[TRANSAKTION_EINTRAG]]
    assert _von_aussen(fenster.datei) == [(1, "Ada"), (2, "Grace")]
