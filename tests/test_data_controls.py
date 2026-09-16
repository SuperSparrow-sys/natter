"""Tests für die Data Controls (Abschnitt 10.1). Siehe
docs/arbeitspakete/M5.md, Schritt 5. Headless, gegen echtes
`:memory:`-SQLite (kein Mock).
"""

from __future__ import annotations

from pcl import (
    DataSource,
    DBComboBox,
    DBEdit,
    DBGrid,
    DBNavigator,
    DBText,
    Form,
    SQLite3Connection,
    SQLQuery,
)


def _verbindung_mit_kunden() -> SQLite3Connection:
    verbindung = SQLite3Connection()
    verbindung.connected = True
    anlegen = SQLQuery(verbindung)
    anlegen.sql = "CREATE TABLE kunden (name TEXT, ort TEXT)"
    anlegen.exec_sql()
    for name, ort in (("Anna", "Köln"), ("Bo", "Bonn"), ("Cem", "Coburg")):
        einfuegen = SQLQuery(verbindung)
        einfuegen.sql = "INSERT INTO kunden (name, ort) VALUES (:name, :ort)"
        einfuegen.params["name"] = name
        einfuegen.params["ort"] = ort
        einfuegen.exec_sql()
    return verbindung


class _Formular(Form):
    def create_components(self) -> None:
        self.verbindung = _verbindung_mit_kunden()
        self.abfrage = SQLQuery(self.verbindung)
        self.abfrage.sql = "SELECT name, ort FROM kunden ORDER BY name"
        self.abfrage.open()
        self.ds_kunden = DataSource(self.abfrage)
        self.dbg_kunden = DBGrid(self, self.ds_kunden)
        self.dbe_name = DBEdit(self, self.ds_kunden)
        self.dbe_name.field = "name"
        self.dbt_ort = DBText(self, self.ds_kunden)
        self.dbt_ort.field = "ort"
        self.dbn_kunden = DBNavigator(self, self.ds_kunden)
        self.dbc_ort = DBComboBox(self, self.ds_kunden)
        self.dbc_ort.list_field = "ort"


def test_dbgrid_zeigt_alle_zeilen_und_spalten() -> None:
    formular = _Formular()
    grid = formular.dbg_kunden._qwidget
    assert grid.columnCount() == 2
    assert grid.rowCount() == 3
    assert grid.item(0, 0).text() == "Anna"
    assert grid.item(2, 0).text() == "Cem"


def test_dbedit_und_dbtext_zeigen_das_feld_der_ersten_zeile() -> None:
    formular = _Formular()
    assert formular.dbe_name._qwidget.text() == "Anna"
    assert formular.dbt_ort._qwidget.text() == "Köln"


def test_dbnavigator_vor_bewegt_den_datensatzzeiger_und_aktualisiert_controls() -> None:
    formular = _Formular()
    formular.dbn_kunden.knopf_vor.click()
    assert formular.abfrage.record_index == 1
    assert formular.dbe_name._qwidget.text() == "Bo"
    assert formular.dbt_ort._qwidget.text() == "Bonn"


def test_dbnavigator_letzter_und_zurueck() -> None:
    formular = _Formular()
    formular.dbn_kunden.knopf_letzter.click()
    assert formular.dbe_name._qwidget.text() == "Cem"

    formular.dbn_kunden.knopf_zurueck.click()
    assert formular.dbe_name._qwidget.text() == "Bo"


def test_dbnavigator_vor_am_letzten_datensatz_bleibt_dort_stehen() -> None:
    formular = _Formular()
    formular.dbn_kunden.knopf_letzter.click()
    formular.dbn_kunden.knopf_vor.click()
    assert formular.dbe_name._qwidget.text() == "Cem"


def test_dbnavigator_zurueck_am_ersten_datensatz_bleibt_dort_stehen() -> None:
    formular = _Formular()
    formular.dbn_kunden.knopf_zurueck.click()
    assert formular.dbe_name._qwidget.text() == "Anna"


def test_dbnavigator_loest_einfuegen_loeschen_speichern_abbrechen_aus() -> None:
    formular = _Formular()
    ereignisse = []
    formular.dbn_kunden.on_insert = lambda sender: ereignisse.append("insert")
    formular.dbn_kunden.on_delete = lambda sender: ereignisse.append("delete")
    formular.dbn_kunden.on_save = lambda sender: ereignisse.append("save")
    formular.dbn_kunden.on_cancel = lambda sender: ereignisse.append("cancel")

    formular.dbn_kunden.knopf_einfuegen.click()
    formular.dbn_kunden.knopf_loeschen.click()
    formular.dbn_kunden.knopf_speichern.click()
    formular.dbn_kunden.knopf_abbrechen.click()

    assert ereignisse == ["insert", "delete", "save", "cancel"]


def test_dbedit_eingabe_aendert_das_feld_im_query_puffer() -> None:
    formular = _Formular()
    formular.dbe_name._qwidget.setText("Anna-Maria")
    formular.dbe_name._qwidget.editingFinished.emit()

    assert formular.abfrage.field_by_name("name").as_string == "Anna-Maria"
    # DBGrid sieht die Änderung erst nach einer erneuten Benachrichtigung -
    # DBEdit selbst löst keine automatische Neuzeichnung anderer Controls aus.
    formular.ds_kunden.aktualisieren()
    assert formular.dbg_kunden._qwidget.item(0, 0).text() == "Anna-Maria"


def test_dbcombobox_zeigt_die_lookup_spalte() -> None:
    formular = _Formular()
    combo = formular.dbc_ort._qwidget
    eintraege = [combo.itemText(i) for i in range(combo.count())]
    assert eintraege == ["Köln", "Bonn", "Coburg"]


def test_dbgrid_ohne_offene_abfrage_bleibt_leer() -> None:
    formular = Form()
    quelle = DataSource()
    grid = DBGrid(formular, quelle)
    assert grid._qwidget.rowCount() == 0
    assert grid._qwidget.columnCount() == 0
