"""Tests für das Datenbank-Panel (Abschnitt 10.2). Siehe
Arbeitspaket M5, Schritt 8. Headless, gegen echtes
`:memory:`-SQLite (kein Mock).
"""

from __future__ import annotations

from pathlib import Path

from ide.database import DatenbankPanel


def _verbunden() -> DatenbankPanel:
    panel = DatenbankPanel()
    panel._sqlite_pfad.setText(":memory:")
    panel._verbinden()
    return panel


def test_verbinden_gegen_memory_sqlite_setzt_den_status() -> None:
    panel = _verbunden()
    assert panel.verbindung is not None
    assert panel._status_label.text() == "Verbunden"


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
    zweites_panel = _verbunden()
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
