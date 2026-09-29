"""Transaktionen im Schülerprogramm und im Datenbank-Panel, deutsche
Meldungen für die häufigsten SQL-Fehler und Spaltenköpfe bei einem
JOIN (Punkte 265, 266, 268, 269). Headless gegen echtes SQLite."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

import pytest

from ide.database import DatenbankPanel
from ide.database.panel import _fehlertext
from pcl import SQLite3Connection
from pcl.errors import NatterDatenbankError
from pcl.fehlerkatalog import _datenbankmeldung_eindeutschen


def _konten_in_datei(pfad: Path) -> SQLite3Connection:
    db = SQLite3Connection(pfad)
    db.execute("CREATE TABLE konto (nr INTEGER PRIMARY KEY, stand INTEGER)")
    db.execute("INSERT INTO konto VALUES (1, 100), (2, 0), (3, 7)")
    return db


def _von_aussen(pfad: Path) -> list[tuple[Any, ...]]:
    with closing(sqlite3.connect(pfad, timeout=0)) as pruefung:
        return pruefung.execute(
            "SELECT nr, stand FROM konto ORDER BY nr"
        ).fetchall()


# -- Punkt 265 ---------------------------------------------------------


def test_valueerror_im_transaktionsblock_laesst_nichts_offen(
    tmp_path: Path,
) -> None:
    """Das Überweisungsmuster aus der Komponenten-Referenz mit einer
    Eingabe, die keine Zahl ist, zwischen den beiden Anweisungen."""
    pfad = tmp_path / "bank.sqlite"
    db = _konten_in_datei(pfad)

    def ueberweisen(eingabe: str) -> None:
        with db.transaction():
            db.execute("UPDATE konto SET stand = stand - 50 WHERE nr = 1")
            betrag = int(eingabe)
            db.execute(
                "UPDATE konto SET stand = stand + :b WHERE nr = 2", b=betrag
            )

    with pytest.raises(ValueError):
        ueberweisen("abc")
    assert not db.verbindung.in_transaction
    assert _von_aussen(pfad) == [(1, 100), (2, 0), (3, 7)]

    # Der nächste Klick scheitert nicht mehr an BEGIN.
    ueberweisen("50")
    assert _von_aussen(pfad) == [(1, 50), (2, 50), (3, 7)]

    # Ein späteres execute() ist festgeschrieben und von außen zu
    # sehen, ohne dass die Datei gesperrt ist.
    db.execute("INSERT INTO konto VALUES (4, 1)")
    assert not db.verbindung.in_transaction
    assert (4, 1) in _von_aussen(pfad)
    db.connected = False


def test_sql_fehler_im_transaktionsblock_nimmt_alles_zurueck(
    tmp_path: Path,
) -> None:
    pfad = tmp_path / "bank.sqlite"
    db = _konten_in_datei(pfad)
    with pytest.raises(NatterDatenbankError):
        with db.transaction():
            db.execute("UPDATE konto SET stand = 0 WHERE nr = 1")
            db.execute("INSERT INTO konto VALUES (2, 1)")
    assert not db.verbindung.in_transaction
    assert _von_aussen(pfad) == [(1, 100), (2, 0), (3, 7)]
    db.connected = False


def test_schliessen_nimmt_offene_transaktion_zurueck_und_meldet_es(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pfad = tmp_path / "bank.sqlite"
    db = _konten_in_datei(pfad)
    db.execute("BEGIN")
    db.execute("DELETE FROM konto")

    db.connected = False

    fehlerausgabe = capsys.readouterr().err
    assert "Transaktion offen" in fehlerausgabe
    assert "bank.sqlite" in fehlerausgabe
    assert _von_aussen(pfad) == [(1, 100), (2, 0), (3, 7)]


def test_schliessen_ohne_offene_transaktion_meldet_nichts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db = _konten_in_datei(tmp_path / "bank.sqlite")
    db.connected = False
    assert capsys.readouterr().err == ""


# -- Punkt 266 ---------------------------------------------------------


def _panel_mit_datei(pfad: Path) -> DatenbankPanel:
    _konten_in_datei(pfad).connected = False
    panel = DatenbankPanel()
    panel._sqlite_pfad.setText(str(pfad))
    panel._verbinden()
    assert panel.verbindung is not None, panel._status_label.text()
    return panel


def _ausfuehren(panel: DatenbankPanel, sql: str) -> str:
    panel._sql_eingabe.setPlainText(sql)
    panel._sql_ausfuehren()
    return panel._status_label.text()


def test_rollback_im_panel_nimmt_das_delete_zurueck(tmp_path: Path) -> None:
    pfad = tmp_path / "bank.sqlite"
    panel = _panel_mit_datei(pfad)

    assert "Transaktion offen" in _ausfuehren(panel, "BEGIN")
    assert panel.transaktion_offen
    status = _ausfuehren(panel, "DELETE FROM konto")
    assert "3 Zeilen geändert." in status
    assert "Transaktion offen" in status
    status = _ausfuehren(panel, "ROLLBACK")
    assert "SQL-Fehler" not in status
    assert not panel.transaktion_offen

    assert len(_von_aussen(pfad)) == 3
    panel.trennen()


def test_commit_im_panel_schreibt_fest(tmp_path: Path) -> None:
    pfad = tmp_path / "bank.sqlite"
    panel = _panel_mit_datei(pfad)
    _ausfuehren(panel, "BEGIN")
    _ausfuehren(panel, "DELETE FROM konto WHERE nr = 3")
    assert len(_ausfuehren(panel, "SELECT * FROM konto")) > 0
    assert panel.transaktion_offen
    _ausfuehren(panel, "COMMIT")
    assert not panel.transaktion_offen
    assert not panel.verbindung.verbindung.in_transaction
    assert _von_aussen(pfad) == [(1, 100), (2, 0)]
    panel.trennen()


def test_fehler_in_der_transaktion_haelt_sie_offen(tmp_path: Path) -> None:
    pfad = tmp_path / "bank.sqlite"
    panel = _panel_mit_datei(pfad)
    _ausfuehren(panel, "BEGIN")
    _ausfuehren(panel, "DELETE FROM konto WHERE nr = 3")
    status = _ausfuehren(panel, "INSERT INTO konto VALUES (1, 5)")
    assert "SQL-Fehler" in status
    assert "Transaktion offen" in status
    _ausfuehren(panel, "ROLLBACK")
    assert len(_von_aussen(pfad)) == 3
    panel.trennen()


def test_trennen_nimmt_offene_transaktion_zurueck(tmp_path: Path) -> None:
    pfad = tmp_path / "bank.sqlite"
    panel = _panel_mit_datei(pfad)
    _ausfuehren(panel, "BEGIN")
    _ausfuehren(panel, "DELETE FROM konto")

    panel.trennen()

    assert "zurückgenommen" in panel._status_label.text()
    assert len(_von_aussen(pfad)) == 3


def test_ohne_begin_schreibt_das_panel_weiter_sofort_fest(
    tmp_path: Path,
) -> None:
    """Punkt 237 gilt weiter: jede einzelne Anweisung ist sofort in
    der Datei."""
    pfad = tmp_path / "bank.sqlite"
    panel = _panel_mit_datei(pfad)
    status = _ausfuehren(panel, "DELETE FROM konto WHERE nr = 3")
    assert "Transaktion" not in status
    assert not panel.verbindung.verbindung.in_transaction
    assert len(_von_aussen(pfad)) == 2
    panel.trennen()


def test_import_bei_offener_transaktion_wird_abgelehnt(
    tmp_path: Path,
) -> None:
    pfad = tmp_path / "bank.sqlite"
    csv_datei = tmp_path / "noten.csv"
    csv_datei.write_text("name;note\nAnna;1\n", encoding="utf-8")
    panel = _panel_mit_datei(pfad)
    _ausfuehren(panel, "BEGIN")
    _ausfuehren(panel, "DELETE FROM konto")
    with pytest.raises(NatterDatenbankError, match="Transaktion offen"):
        panel.csv_importieren(csv_datei)
    _ausfuehren(panel, "ROLLBACK")
    assert len(_von_aussen(pfad)) == 3
    panel.trennen()


# -- Punkt 279 ---------------------------------------------------------


def _panel_mit_offener_transaktion(
    pfad: Path, monkeypatch: pytest.MonkeyPatch, antwort: str
) -> tuple[DatenbankPanel, list[str]]:
    """Ein Panel nach BEGIN und zwei INSERT. Die Nachfrage liefert
    `antwort` und merkt sich, wofür gefragt wurde."""
    panel = _panel_mit_datei(pfad)
    _ausfuehren(panel, "BEGIN")
    _ausfuehren(panel, "INSERT INTO konto VALUES (4, 1)")
    status = _ausfuehren(panel, "INSERT INTO konto VALUES (5, 2)")
    assert "Transaktion offen" in status
    gefragt: list[str] = []

    def fragen(vorhaben: str) -> str:
        gefragt.append(vorhaben)
        return antwort

    monkeypatch.setattr(panel, "_transaktion_fragen", fragen)
    return panel, gefragt


def test_verbinden_fragt_und_schreibt_fest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pfad = tmp_path / "bank.sqlite"
    panel, gefragt = _panel_mit_offener_transaktion(
        pfad, monkeypatch, "festschreiben"
    )

    panel._verbinden_knopf.click()

    assert gefragt == ["verbinden"]
    assert panel.verbindung is not None
    assert panel._status_label.text() == "Verbunden"
    assert len(_von_aussen(pfad)) == 5
    assert _ausfuehren(panel, "SELECT count(*) FROM konto")
    assert panel.ergebnis_tabelle.item(0, 0).text() == "5"
    panel.trennen()


def test_verbinden_nimmt_nur_auf_ausdruecklichen_wunsch_zurueck(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pfad = tmp_path / "bank.sqlite"
    panel, gefragt = _panel_mit_offener_transaktion(
        pfad, monkeypatch, "zuruecknehmen"
    )

    panel._verbinden_knopf.click()

    assert gefragt == ["verbinden"]
    assert panel.verbindung is not None
    assert not panel.transaktion_offen
    assert len(_von_aussen(pfad)) == 3
    panel.trennen()


def test_verbinden_abbrechen_laesst_die_transaktion_offen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pfad = tmp_path / "bank.sqlite"
    panel, gefragt = _panel_mit_offener_transaktion(
        pfad, monkeypatch, "abbrechen"
    )
    verbindung = panel.verbindung

    panel._verbinden_knopf.click()

    assert gefragt == ["verbinden"]
    assert panel.verbindung is verbindung
    assert panel.transaktion_offen
    assert "weiter offen" in panel._status_label.text()
    _ausfuehren(panel, "COMMIT")
    assert len(_von_aussen(pfad)) == 5
    panel.trennen()


def test_trennen_fragt_bei_offener_transaktion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pfad = tmp_path / "bank.sqlite"
    panel, gefragt = _panel_mit_offener_transaktion(
        pfad, monkeypatch, "abbrechen"
    )

    panel._trennen_knopf.click()

    assert gefragt == ["trennen"]
    assert panel.verbindung is not None
    assert panel.transaktion_offen
    assert panel._status_label.text().startswith("Nicht getrennt")

    monkeypatch.setattr(panel, "_transaktion_fragen", lambda _: "festschreiben")
    panel._trennen_knopf.click()

    assert panel.verbindung is None
    assert len(_von_aussen(pfad)) == 5


def test_ohne_offene_transaktion_fragt_niemand(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pfad = tmp_path / "bank.sqlite"
    panel = _panel_mit_datei(pfad)
    _ausfuehren(panel, "INSERT INTO konto VALUES (4, 1)")

    def fragen(vorhaben: str) -> str:
        raise AssertionError("ohne offene Transaktion keine Nachfrage")

    monkeypatch.setattr(panel, "_transaktion_fragen", fragen)
    panel._verbinden_knopf.click()
    assert panel._status_label.text() == "Verbunden"
    panel._trennen_knopf.click()
    assert panel.verbindung is None
    assert panel._status_label.text() == "Nicht verbunden"
    assert len(_von_aussen(pfad)) == 4


# -- Punkt 268 ---------------------------------------------------------


_FEHLERFAELLE: list[tuple[str, dict[str, Any]]] = [
    ("CREATE TABLE konto (x)", {}),
    ("INSERT INTO konto VALUES (1, 2)", {}),
    ("SELECT :wer", {}),
    ("SELECT 1; SELECT 2", {}),
    ("SELECT lower2('a')", {}),
    ("INSERT INTO konto VALUES (5, 'a', -5)", {}),
    ("INSERT INTO konto VALUES ('abc', 'a', 5)", {}),
    ("SELECT nr FROM konto, k2", {}),
    ("SELECT :x", {"x": [1]}),
    ("SELECT ?", {"x": 1}),
    ("COMMIT", {}),
    ("ROLLBACK", {}),
    ("BEGIN", {}),
]


@pytest.mark.parametrize(("sql", "parameter"), _FEHLERFAELLE)
def test_haeufige_sql_fehler_kommen_deutsch_an(
    sql: str, parameter: dict[str, Any]
) -> None:
    db = SQLite3Connection(":memory:")
    db.execute(
        "CREATE TABLE konto (nr INTEGER PRIMARY KEY, inhaber TEXT, "
        "stand INTEGER CHECK (stand >= 0))"
    )
    db.execute("CREATE TABLE k2 (nr INTEGER)")
    if sql == "BEGIN":
        db.execute("BEGIN")

    with pytest.raises(NatterDatenbankError) as fehler:
        db.execute(sql, **parameter)

    treibertext = str(fehler.value.__cause__)
    for meldung in (
        _datenbankmeldung_eindeutschen(str(fehler.value)),
        _fehlertext(fehler.value),
    ):
        assert treibertext not in meldung, meldung
        assert meldung.startswith("SQL-Fehler: ")
    db.connected = False


def test_panel_und_pcl_nennen_mehrere_anweisungen_gleich(tmp_path: Path) -> None:
    db = SQLite3Connection(":memory:")
    with pytest.raises(NatterDatenbankError) as fehler:
        db.query("SELECT 1; SELECT 2")
    im_programm = _datenbankmeldung_eindeutschen(str(fehler.value))

    panel = _datei_panel(tmp_path)
    panel._verbinden()
    im_panel = _ausfuehren(panel, "SELECT 1; SELECT 2")
    assert im_panel == im_programm
    assert "nur eine Anweisung auf einmal" in im_panel
    panel.trennen()


def _datei_panel(ordner: Path) -> DatenbankPanel:
    """Ein Panel vor dem Verbinden mit einer leeren Datei; ohne Datei
    verbindet es nicht (Punkt 430)."""
    pfad = ordner / "probe.sqlite"
    sqlite3.connect(pfad).close()
    panel = DatenbankPanel()
    panel._sqlite_pfad.setText(str(pfad))
    return panel


# -- Punkt 269 ---------------------------------------------------------


def test_join_zeigt_die_echten_spaltennamen(tmp_path: Path) -> None:
    panel = _datei_panel(tmp_path)
    panel._verbinden()
    _ausfuehren(panel, "CREATE TABLE a (id INTEGER, name TEXT)")
    _ausfuehren(panel, "CREATE TABLE b (id INTEGER, a_id INTEGER, name TEXT)")
    _ausfuehren(panel, "INSERT INTO a VALUES (1, 'x')")
    _ausfuehren(panel, "INSERT INTO b VALUES (7, 1, 'y')")

    _ausfuehren(panel, "SELECT * FROM a JOIN b ON b.a_id = a.id")

    tabelle = panel.ergebnis_tabelle
    koepfe = [
        tabelle.horizontalHeaderItem(i).text()
        for i in range(tabelle.columnCount())
    ]
    assert koepfe == ["id", "name", "id", "a_id", "name"]
    werte = [tabelle.item(0, i).text() for i in range(tabelle.columnCount())]
    assert werte == ["1", "x", "7", "1", "y"]
    panel.trennen()


def test_echte_spalte_mit_doppelpunkt_bleibt_stehen(tmp_path: Path) -> None:
    panel = _datei_panel(tmp_path)
    panel._verbinden()
    _ausfuehren(panel, 'SELECT 1 AS "x:1", 2 AS y')
    tabelle = panel.ergebnis_tabelle
    koepfe = [
        tabelle.horizontalHeaderItem(i).text()
        for i in range(tabelle.columnCount())
    ]
    assert koepfe == ["x:1", "y"]
    panel.trennen()
