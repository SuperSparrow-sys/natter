"""Tests für das Datenbank-Panel (Abschnitt 10.2). Siehe
Arbeitspaket M5, Schritt 8. Headless, gegen eine echte SQLite-Datei
im Probeordner (kein Mock).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from ide.database import DatenbankPanel


@pytest.fixture(autouse=True)
def _im_probeordner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Das Panel verbindet nur mit einer Datei (Punkt 430). Ein Name
    ohne Pfad landet so im Probeordner des Tests."""
    monkeypatch.chdir(tmp_path)


def _verbunden(name: str = "probe.sqlite") -> DatenbankPanel:
    sqlite3.connect(name).close()
    panel = DatenbankPanel()
    panel._sqlite_pfad.setText(name)
    panel._verbinden()
    return panel


def test_verbinden_mit_sqlite_datei_setzt_den_status() -> None:
    panel = _verbunden()
    assert panel.verbindung is not None
    assert panel._status_label.text() == "Verbunden"


@pytest.mark.parametrize("eingabe", ["", "   ", ":memory:"])
def test_ohne_datei_verbindet_das_panel_nicht(
    tmp_path: Path, eingabe: str
) -> None:
    """Punkt 430: ein leeres Feld verband still mit einer Datenbank im
    Arbeitsspeicher, deren Tabellen beim Trennen verloren waren."""
    projekt = tmp_path / "projekt"
    projekt.mkdir()
    panel = DatenbankPanel()
    panel.projektordner_setzen(projekt)
    panel._sqlite_pfad.setText(eingabe)

    panel._verbinden_knopf.click()

    assert panel.verbindung is None
    text = panel._status_label.text()
    assert text.startswith("Nicht verbunden.")
    assert "Datei wählen" in text
    assert "Namen eintragen" in text
    assert "im Projektordner" in text
    assert list(projekt.iterdir()) == []


def test_verbinden_mit_ungueltiger_sqlite_datei_zeigt_fehlermeldung(tmp_path: Path) -> None:
    panel = DatenbankPanel()
    panel._sqlite_pfad.setText(str(tmp_path / "nicht" / "vorhanden" / "db.sqlite"))

    panel._verbinden()

    assert panel.verbindung is None
    assert "fehlgeschlagen" in panel._status_label.text()


def test_tabellenbaum_wird_nach_sql_ausfuehren_befuellt() -> None:
    panel = _verbunden()
    panel._sql_eingabe.setPlainText("CREATE TABLE kunden (name TEXT, ort TEXT)")

    panel._sql_ausfuehren()

    namen = [
        panel.tabellenbaum.topLevelItem(i).text(0)
        for i in range(panel.tabellenbaum.topLevelItemCount())
    ]
    assert namen == ["kunden"]
    tabelle_eintrag = panel.tabellenbaum.topLevelItem(0)
    spalten = [tabelle_eintrag.child(i).text(0) for i in range(tabelle_eintrag.childCount())]
    assert spalten == ["name", "ort"]


def test_select_abfrage_zeigt_ergebnis_in_der_tabelle() -> None:
    panel = _verbunden()
    panel._sql_eingabe.setPlainText("CREATE TABLE t (n INTEGER)")
    panel._sql_ausfuehren()
    panel._sql_eingabe.setPlainText("INSERT INTO t (n) VALUES (1), (2), (3)")
    panel._sql_ausfuehren()

    panel._sql_eingabe.setPlainText("SELECT n FROM t ORDER BY n")
    panel._sql_ausfuehren()

    assert panel.ergebnis_tabelle.rowCount() == 3
    assert panel.ergebnis_tabelle.item(0, 0).text() == "1"


def test_sql_fehler_zeigt_verstaendliche_meldung_statt_absturz() -> None:
    panel = _verbunden()
    panel._sql_eingabe.setPlainText("SELECT * FROM nicht_vorhanden")

    panel._sql_ausfuehren()

    assert "SQL-Fehler" in panel._status_label.text()


def test_csv_importieren_erzeugt_die_erwartete_tabelle(tmp_path: Path) -> None:
    panel = _verbunden()
    csv_datei = tmp_path / "schueler.csv"
    csv_datei.write_text("name,punkte\nAnna,12\nBo,7\n", encoding="utf-8")

    tabellenname = panel.csv_importieren(csv_datei)

    assert tabellenname == "schueler"
    namen = [
        panel.tabellenbaum.topLevelItem(i).text(0)
        for i in range(panel.tabellenbaum.topLevelItemCount())
    ]
    assert "schueler" in namen

    panel._sql_eingabe.setPlainText("SELECT * FROM schueler ORDER BY name")
    panel._sql_ausfuehren()
    assert panel.ergebnis_tabelle.rowCount() == 2
    assert panel.ergebnis_tabelle.item(0, 0).text() == "Anna"


def test_csv_export_erzeugt_eine_gueltige_datei(tmp_path: Path) -> None:
    panel = _verbunden()
    panel._sql_eingabe.setPlainText("CREATE TABLE kunden (name TEXT)")
    panel._sql_ausfuehren()
    panel._sql_eingabe.setPlainText("INSERT INTO kunden (name) VALUES ('Anna')")
    panel._sql_ausfuehren()

    ziel = tmp_path / "export.csv"
    panel.tabelle_als_csv_exportieren("kunden", ziel)

    inhalt = ziel.read_text(encoding="utf-8")
    assert "name" in inhalt
    assert "Anna" in inhalt


def test_sql_dump_export_erzeugt_lauffaehige_insert_anweisungen(tmp_path: Path) -> None:
    panel = _verbunden()
    panel._sql_eingabe.setPlainText("CREATE TABLE kunden (name TEXT, punkte INTEGER)")
    panel._sql_ausfuehren()
    panel._sql_eingabe.setPlainText("INSERT INTO kunden VALUES ('Anna', 12)")
    panel._sql_ausfuehren()

    ziel = tmp_path / "dump.sql"
    panel.tabelle_als_sql_dump_exportieren("kunden", ziel)

    dump = ziel.read_text(encoding="utf-8")
    assert "INSERT INTO" in dump
    assert "'Anna'" in dump
    assert "12" in dump

    # Der Dump muss sich in eine leere Datenbank einspielen lassen;
    # er bringt die Tabellendefinition selbst mit (Punkt 242).
    zweites_panel = _verbunden("leer.sqlite")
    zweites_panel.verbindung.verbindung.executescript(dump)
    zweites_panel._sql_eingabe.setPlainText("SELECT COUNT(*) AS anzahl FROM kunden")
    zweites_panel._sql_ausfuehren()
    assert zweites_panel.ergebnis_tabelle.item(0, 0).text() == "1"


def _konten_anlegen(panel: DatenbankPanel) -> None:
    for sql in (
        "CREATE TABLE konten (nr INTEGER, inhaber TEXT, stand REAL)",
        "INSERT INTO konten VALUES (1, 'Anna', 10.5)",
        "INSERT INTO konten VALUES (2, 'Bo', 3)",
    ):
        panel._sql_eingabe.setPlainText(sql)
        panel._sql_ausfuehren()


def _zeilen(panel: DatenbankPanel, tabelle: str) -> list[tuple]:
    return panel.verbindung.verbindung.execute(
        f'SELECT * FROM "{tabelle}" ORDER BY 1'
    ).fetchall()


def test_csv_import_laesst_eine_gleichnamige_tabelle_stehen(
    tmp_path: Path,
) -> None:
    """Punkt 138: `konten.csv` ersetzte die vorhandene Tabelle
    `konten` ohne Rückfrage."""
    panel = _verbunden()
    _konten_anlegen(panel)
    vorher = _zeilen(panel, "konten")
    csv_datei = tmp_path / "konten.csv"
    csv_datei.write_text("name,ort\nCem,Köln\n", encoding="utf-8")

    name = panel.csv_importieren(csv_datei)

    assert name == "konten_2"
    assert _zeilen(panel, "konten") == vorher
    assert _zeilen(panel, "konten_2") == [("Cem", "Köln")]


def test_csv_import_dialog_fragt_vor_dem_ersetzen(
    tmp_path: Path, monkeypatch
) -> None:
    from PySide6.QtWidgets import QMessageBox

    panel = _verbunden()
    _konten_anlegen(panel)
    vorher = _zeilen(panel, "konten")
    csv_datei = tmp_path / "konten.csv"
    csv_datei.write_text("name,ort\nCem,Köln\n", encoding="utf-8")
    monkeypatch.setattr(
        "ide.database.panel.QFileDialog.getOpenFileName",
        staticmethod(lambda *a, **k: (str(csv_datei), "")),
    )
    gefragt: list[str] = []

    def antworten(knopf):
        def fragen(name: str):
            gefragt.append(name)
            return knopf

        return fragen

    monkeypatch.setattr(
        panel, "_tabelle_ersetzen_fragen",
        antworten(QMessageBox.StandardButton.Cancel),
    )
    panel._csv_importieren_dialog()
    assert gefragt == ["konten"]
    assert _zeilen(panel, "konten") == vorher
    assert "konten_2" not in panel._tabellennamen()

    monkeypatch.setattr(
        panel, "_tabelle_ersetzen_fragen",
        antworten(QMessageBox.StandardButton.Yes),
    )
    panel._csv_importieren_dialog()
    assert _zeilen(panel, "konten") == [("Cem", "Köln")]


def test_csv_import_ohne_verbindung_meldet_statt_zu_werfen(
    monkeypatch,
) -> None:
    meldungen: list[str] = []
    monkeypatch.setattr(
        "ide.database.panel.QMessageBox.warning",
        staticmethod(lambda _eltern, _titel, text: meldungen.append(text)),
    )
    panel = DatenbankPanel()

    panel._csv_importieren_dialog()

    assert len(meldungen) == 1
    assert "keine Datenbank verbunden" in meldungen[0]


def test_csv_import_fuellt_kurze_zeilen_auf_und_meldet_lange(
    tmp_path: Path, monkeypatch
) -> None:
    panel = _verbunden()
    kurz = tmp_path / "kurz.csv"
    kurz.write_text("a,b,c\n1,2\n", encoding="utf-8")
    assert panel.csv_importieren(kurz) == "kurz"
    assert _zeilen(panel, "kurz") == [(1, 2, "")]

    lang = tmp_path / "lang.csv"
    lang.write_text("a,b\n1,2\n3,4,5\n", encoding="utf-8")
    monkeypatch.setattr(
        "ide.database.panel.QFileDialog.getOpenFileName",
        staticmethod(lambda *a, **k: (str(lang), "")),
    )
    meldungen: list[str] = []
    monkeypatch.setattr(
        "ide.database.panel.QMessageBox.warning",
        staticmethod(lambda _eltern, _titel, text: meldungen.append(text)),
    )
    panel._csv_importieren_dialog()

    assert "Zeile 3" in meldungen[0]
    assert "lang" not in panel._tabellennamen()


def _abfragen(panel: DatenbankPanel, sql: str) -> list[tuple]:
    return panel.verbindung.verbindung.execute(sql).fetchall()


def test_csv_import_legt_zahlenspalten_als_zahlen_an(tmp_path: Path) -> None:
    """Punkt 288: alle Spalten wurden TEXT. ``menge > 50`` fand dann
    „Birne“ (9), und „0,5“ zählte in ``sum()`` als 0."""
    panel = _verbunden()
    csv_datei = tmp_path / "artikel.csv"
    csv_datei.write_text(
        "name;preis;menge\nApfel;0,5;10\nBirne;12;9\nKiwi;3;100\n",
        encoding="utf-8",
    )
    assert panel.csv_importieren(csv_datei) == "artikel"

    assert _abfragen(
        panel, "SELECT name FROM artikel WHERE menge > 50"
    ) == [("Kiwi",)]
    assert _abfragen(
        panel, "SELECT name FROM artikel ORDER BY menge DESC"
    ) == [("Kiwi",), ("Apfel",), ("Birne",)]
    assert _abfragen(panel, "SELECT max(menge) FROM artikel") == [(100,)]
    assert _abfragen(panel, "SELECT sum(preis) FROM artikel") == [(15.5,)]
    assert [
        (zeile[1], zeile[2])
        for zeile in _abfragen(panel, "PRAGMA table_info(artikel)")
    ] == [("name", "TEXT"), ("preis", "REAL"), ("menge", "INTEGER")]


def test_csv_import_erkennt_leere_und_gemischte_spalten(
    tmp_path: Path,
) -> None:
    """Leere Felder werden in Zahlenspalten NULL. Eine Spalte mit
    einem einzigen Nicht-Zahlwert bleibt ganz Text, ebenso Kennungen
    mit führender Null und Ziffernfolgen jenseits von 64 Bit."""
    panel = _verbunden()
    csv_datei = tmp_path / "werte.csv"
    csv_datei.write_text(
        "n;k;gemischt;plz;leer;gross\n"
        "1;2.5;7;01067;;12345678901234567890\n"
        ";-3;acht;04109;;1\n"
        "-4;1.234,5;9;10115;;2\n",
        encoding="utf-8",
    )
    panel.csv_importieren(csv_datei)

    assert [
        zeile[2] for zeile in _abfragen(panel, "PRAGMA table_info(werte)")
    ] == ["INTEGER", "REAL", "TEXT", "TEXT", "TEXT", "TEXT"]
    assert _abfragen(panel, "SELECT * FROM werte") == [
        (1, 2.5, "7", "01067", "", "12345678901234567890"),
        (None, -3.0, "acht", "04109", "", "1"),
        (-4, 1234.5, "9", "10115", "", "2"),
    ]


def test_csv_import_liest_den_dezimalpunkt_je_spalte(tmp_path: Path) -> None:
    """Neben „2.49“ ist „1.250“ eine Kommazahl und nicht 1250. Zelle
    für Zelle gelesen wurde jeder Wert mit drei Nachkommastellen still
    zur Tausenderzahl. Eine Spalte nur mit Tausenderpunkten bleibt,
    wie sie war; widersprüchliche Punkte ergeben Text."""
    panel = _verbunden()
    csv_datei = tmp_path / "masse.csv"
    csv_datei.write_text(
        "laenge;breite;preis;tausend;wirr\n"
        "0.125;52.520;1.299;1.000;2.5\n"
        "1.250;13.405;2.49;2.500;1.234.567\n"
        "2.375;8.5;0.99;3;1\n",
        encoding="utf-8",
    )
    panel.csv_importieren(csv_datei)

    assert [
        zeile[2] for zeile in _abfragen(panel, "PRAGMA table_info(masse)")
    ] == ["REAL", "REAL", "REAL", "REAL", "TEXT"]
    assert _abfragen(panel, "SELECT laenge, breite, preis, tausend FROM masse") == [
        (0.125, 52.52, 1.299, 1000.0),
        (1.25, 13.405, 2.49, 2500.0),
        (2.375, 8.5, 0.99, 3.0),
    ]


def test_mehrere_anweisungen_laufen_der_reihe_nach() -> None:
    """Ein Arbeitsblatt mit CREATE und INSERT lief vorher gar nicht:
    das Panel nahm nur eine Anweisung auf einmal. Ein Semikolon in
    einem Text trennt nicht."""
    panel = _verbunden()
    panel._sql_eingabe.setPlainText(
        "CREATE TABLE schueler (name TEXT);\n"
        "INSERT INTO schueler VALUES ('An;na');\n"
        "-- Kommentar\n"
        "INSERT INTO schueler VALUES ('Ben');\n"
        "SELECT name FROM schueler ORDER BY name;\n"
    )
    panel._sql_ausfuehren()

    assert panel.ergebnis_tabelle.rowCount() == 2
    assert panel.ergebnis_tabelle.item(0, 0).text() == "An;na"


def test_eine_gescheiterte_anweisung_nennt_ihre_nummer() -> None:
    panel = _verbunden()
    panel._sql_eingabe.setPlainText(
        "CREATE TABLE t (n INTEGER); INSERT INTO gibtsnicht VALUES (1);"
        " INSERT INTO t VALUES (2);"
    )
    panel._sql_ausfuehren()

    assert "Anweisung 2 von 3" in panel._status_label.text()
    assert _abfragen(panel, "SELECT count(*) FROM t") == [(0,)]


def test_nur_die_markierung_wird_ausgefuehrt() -> None:
    from PySide6.QtGui import QTextCursor

    panel = _verbunden()
    panel._sql_eingabe.setPlainText(
        "CREATE TABLE a (n INTEGER);\nCREATE TABLE b (n INTEGER);"
    )
    cursor = panel._sql_eingabe.textCursor()
    cursor.setPosition(0)
    cursor.movePosition(
        QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.KeepAnchor
    )
    panel._sql_eingabe.setTextCursor(cursor)
    panel._sql_ausfuehren()

    assert _abfragen(
        panel, "SELECT name FROM sqlite_master WHERE type = 'table'"
    ) == [("a",)]



def test_ein_sql_fehler_leert_das_ergebnis_und_nennt_den_punkt() -> None:
    """Punkt 510: nach einem Fehler stand das Ergebnis der vorigen
    Abfrage weiter in der Tabelle, als wäre es das der fehlerhaften.
    Punkt 512: an einer Kommazahl wie `2,0` nannte die Meldung nur
    das Komma."""
    panel = _verbunden()
    panel._sql_eingabe.setPlainText(
        "CREATE TABLE noten (note REAL); INSERT INTO noten VALUES (1.3)"
    )
    panel._sql_ausfuehren()
    panel._sql_eingabe.setPlainText("SELECT * FROM noten")
    panel._sql_ausfuehren()
    assert panel.ergebnis_tabelle.rowCount() == 1

    panel._sql_eingabe.setPlainText("SELECT * FROM noten WHERE note < 2,0")
    panel._sql_ausfuehren()

    assert panel.ergebnis_tabelle.rowCount() == 0
    assert panel.ergebnis_tabelle.columnCount() == 0
    assert "etwa 2.5 statt 2,5" in panel._status_label.text()


def test_csv_export_schreibt_kommazahlen_mit_komma(tmp_path: Path) -> None:
    """Punkt 511: die Datei trennt mit Semikolon wie eine deutsche
    Tabellenkalkulation, die Zahlen standen aber mit Punkt darin. Der
    Import liest das Komma wieder als Zahl."""
    panel = _verbunden()
    panel._sql_eingabe.setPlainText(
        "CREATE TABLE noten (name TEXT, note REAL);"
        "INSERT INTO noten VALUES ('Jörg', 2.5)"
    )
    panel._sql_ausfuehren()
    ziel = tmp_path / "noten.csv"

    panel.tabelle_als_csv_exportieren("noten", ziel)
    name = panel.csv_importieren(ziel)

    assert ziel.read_text(encoding="utf-8-sig").splitlines() == [
        "name;note", "Jörg;2,5"
    ]
    assert panel._roh().execute(f"SELECT note FROM {name}").fetchall() == [
        (2.5,)
    ]
