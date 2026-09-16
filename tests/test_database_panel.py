"""Tests für das Datenbank-Panel (Abschnitt 10.2). Siehe
docs/arbeitspakete/M5.md, Schritt 8. Headless, gegen echtes
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

    # Der Dump muss auf einer frischen Tabelle tatsächlich ausführbar sein.
    zweites_panel = _verbunden()
    zweites_panel._sql_eingabe.setPlainText("CREATE TABLE kunden (name TEXT, punkte INTEGER)")
    zweites_panel._sql_ausfuehren()
    zweites_panel._sql_eingabe.setPlainText(dump.strip().rstrip(";"))
    zweites_panel._sql_ausfuehren()
    zweites_panel._sql_eingabe.setPlainText("SELECT COUNT(*) AS anzahl FROM kunden")
    zweites_panel._sql_ausfuehren()
    assert zweites_panel.ergebnis_tabelle.item(0, 0).text() == "1"
