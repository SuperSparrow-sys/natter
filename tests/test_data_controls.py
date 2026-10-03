"""Tests für die Data Controls (Abschnitt 10.1). Siehe
Arbeitspaket M5, Schritt 5. Headless, gegen echtes
`:memory:`-SQLite (kein Mock).
"""

from __future__ import annotations

import pytest

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
    # Das DBGrid an derselben Datenquelle zeigt den neuen Wert sofort;
    # bis 0.4.3 erst nach einem `aktualisieren()` von Hand.
    assert formular.dbg_kunden._qwidget.item(0, 0).text() == "Anna-Maria"
    assert formular.dbn_kunden.knopf_erster.toolTip() == "Erster Datensatz"


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


# -- Ohne DataSource -----------------------------------
#
# Bis dahin verlangte jede dieser Komponenten eine `DataSource` im
# Konstruktor. Der Designer erzeugt Komponenten aber mit `typ(formular)`
# allein - keine davon liess sich also auf ein Formular legen oder vom
# Eigenschaften-Rundlauf prüfen (der offene Punkt aus M11).


def test_alle_data_controls_lassen_sich_ohne_datenquelle_anlegen() -> None:
    formular = Form()
    for typ in (DBGrid, DBText, DBEdit, DBNavigator):
        assert typ(formular).data_source is None
    assert DBComboBox(formular).list_source is None


def test_dbgrid_ohne_datenquelle_zeigt_eine_leere_tabelle() -> None:
    formular = Form()
    grid = DBGrid(formular)
    assert grid._qwidget.rowCount() == 0
    assert grid._qwidget.columnCount() == 0


def test_dbtext_und_dbedit_ohne_datenquelle_bleiben_leer() -> None:
    formular = Form()
    text = DBText(formular)
    text.field = "name"
    assert text._qwidget.text() == ""

    feld = DBEdit(formular)
    feld.field = "name"
    assert feld._qwidget.text() == ""
    assert feld._qwidget.isEnabled() is False


def test_dbnavigator_ohne_datenquelle_klickt_ins_leere_statt_abzustuerzen() -> None:
    formular = Form()
    navigator = DBNavigator(formular)
    for knopf in (
        navigator.knopf_erster,
        navigator.knopf_zurueck,
        navigator.knopf_vor,
        navigator.knopf_letzter,
    ):
        knopf.click()


# -- show_rows: der kurze Weg -------------------------------------------


def test_show_rows_zeigt_die_zeilen_aus_query_unmittelbar_an() -> None:
    """Eine Zeile statt Abfrage, Datenquelle und Benachrichtigung:
    `grid.show_rows(db.query("SELECT ..."))`."""
    db = _verbindung_mit_kunden()
    formular = Form()
    grid = DBGrid(formular)
    grid.show_rows(db.query("SELECT name, ort FROM kunden ORDER BY name"))

    widget = grid._qwidget
    assert widget.columnCount() == 2
    assert [widget.horizontalHeaderItem(s).text() for s in range(2)] == ["name", "ort"]
    assert widget.rowCount() == 3
    assert widget.item(0, 0).text() == "Anna"
    assert widget.item(2, 1).text() == "Coburg"


def test_show_rows_mit_leerer_liste_leert_die_tabelle() -> None:
    db = _verbindung_mit_kunden()
    formular = Form()
    grid = DBGrid(formular)
    grid.show_rows(db.query("SELECT name FROM kunden"))
    assert grid._qwidget.rowCount() == 3

    grid.show_rows([])
    assert grid._qwidget.rowCount() == 0
    assert grid._qwidget.columnCount() == 0


def test_show_rows_zeigt_none_als_leere_zelle() -> None:
    db = SQLite3Connection(":memory:")
    db.execute("CREATE TABLE t (a TEXT, b TEXT)")
    db.execute("INSERT INTO t (a, b) VALUES ('x', NULL)")

    formular = Form()
    grid = DBGrid(formular)
    grid.show_rows(db.query("SELECT a, b FROM t"))
    assert grid._qwidget.item(0, 1).text() == ""


def test_data_source_nachtraeglich_zuweisen_zeigt_die_daten_wirklich_an() -> None:
    """Gefunden beim Schreiben der Komponenten-Referenz, nicht von einem
    Test: `data_source` war ein einfaches Attribut, und die Anmeldung bei
    der `DataSource` geschah nur im Konstruktor. Die Zuweisung lief
    durch, die Tabelle blieb leer - der stillste aller Fehler."""
    verbindung = _verbindung_mit_kunden()
    abfrage = SQLQuery(verbindung)
    abfrage.sql = "SELECT name FROM kunden ORDER BY name"
    abfrage.open()

    formular = Form()
    grid = DBGrid(formular)
    assert grid._qwidget.rowCount() == 0

    grid.data_source = DataSource(abfrage)
    assert grid._qwidget.rowCount() == 3
    assert grid._qwidget.item(0, 0).text() == "Anna"


def test_data_source_nachtraeglich_zuweisen_meldet_auch_spaetere_aenderungen() -> None:
    verbindung = _verbindung_mit_kunden()
    abfrage = SQLQuery(verbindung)
    abfrage.sql = "SELECT name FROM kunden ORDER BY name"
    abfrage.open()
    quelle = DataSource(abfrage)

    formular = Form()
    text = DBText(formular)
    text.field = "name"
    text.data_source = quelle
    assert text._qwidget.text() == "Anna"

    abfrage.next()
    quelle.aktualisieren()
    assert text._qwidget.text() == "Bo"


def test_list_source_nachtraeglich_zuweisen_fuellt_die_combobox() -> None:
    verbindung = _verbindung_mit_kunden()
    abfrage = SQLQuery(verbindung)
    abfrage.sql = "SELECT ort FROM kunden ORDER BY ort"
    abfrage.open()

    formular = Form()
    auswahl = DBComboBox(formular)
    auswahl.list_field = "ort"
    auswahl.list_source = DataSource(abfrage)
    assert auswahl._qwidget.count() == 3


# -- Punkt 125: Klick auf eine Gitterzeile bewegt den Zeiger -------------


def test_klick_auf_die_dritte_gitterzeile_zeigt_deren_wert_im_dbtext() -> None:
    formular = _Formular()
    formular.dbg_kunden._qwidget.setCurrentCell(2, 0)
    assert formular.abfrage.record_index == 2
    assert formular.dbt_ort._qwidget.text() == "Coburg"
    assert formular.dbe_name._qwidget.text() == "Cem"


def test_nach_dem_klick_bleibt_die_zeile_im_gitter_gewaehlt() -> None:
    formular = _Formular()
    formular.dbg_kunden._qwidget.setCurrentCell(1, 0)
    assert formular.dbg_kunden._qwidget.currentRow() == 1


def test_zellen_im_dbgrid_sind_schreibgeschuetzt() -> None:
    from PySide6.QtWidgets import QAbstractItemView

    formular = _Formular()
    ausloeser = formular.dbg_kunden._qwidget.editTriggers()
    assert ausloeser == QAbstractItemView.EditTrigger.NoEditTriggers


# -- Punkt 245: Abmelden bei der DataSource -----------------------------


def test_geschlossene_formulare_bleiben_nicht_bei_der_quelle() -> None:
    """50 Detailfenster an derselben Quelle geöffnet und geschlossen:
    danach standen 50 Einträge in der Liste der Quelle."""
    import gc

    from PySide6.QtWidgets import QApplication

    verbindung = _verbindung_mit_kunden()
    abfrage = SQLQuery(verbindung)
    abfrage.sql = "SELECT name FROM kunden ORDER BY name"
    abfrage.open()
    quelle = DataSource(abfrage)

    class _Detail(Form):
        def create_components(self) -> None:
            self.dbe_name = DBEdit(self, quelle)
            self.dbe_name.field = "name"

    for _ in range(50):
        detail = _Detail()
        detail.show()
        QApplication.processEvents()
        detail.close()
        QApplication.processEvents()
    del detail
    gc.collect()

    quelle.aktualisieren()
    assert len(quelle._listener) < 2


def test_neue_quelle_meldet_bei_der_alten_ab() -> None:
    verbindung = _verbindung_mit_kunden()
    abfrage = SQLQuery(verbindung)
    abfrage.sql = "SELECT name FROM kunden ORDER BY name"
    abfrage.open()
    alte, neue = DataSource(abfrage), DataSource(abfrage)

    formular = Form()
    text = DBText(formular, alte)
    auswahl = DBComboBox(formular, alte)
    text.data_source = neue
    text.data_source = neue
    auswahl.list_source = neue

    assert alte._listener == []
    assert len(neue._listener) == 2


def test_ein_zerstoertes_widget_meldet_sich_ab() -> None:
    from shiboken6 import delete

    verbindung = _verbindung_mit_kunden()
    abfrage = SQLQuery(verbindung)
    abfrage.sql = "SELECT name FROM kunden ORDER BY name"
    abfrage.open()
    quelle = DataSource(abfrage)
    formular = Form()
    text = DBText(formular, quelle)
    text.field = "name"

    delete(text._qwidget)

    assert quelle._listener == []
    quelle.aktualisieren()


# -- Punkt 246: leere Felder, Kommazahlen, Binärdaten --------------------


def _formular_mit_gemischten_werten() -> Form:
    db = SQLite3Connection(":memory:")
    db.execute("CREATE TABLE t (name TEXT, stand REAL, bild BLOB)")
    db.execute("INSERT INTO t VALUES ('A', 1.5, NULL)")
    db.execute("INSERT INTO t VALUES (NULL, NULL, X'89504E47')")
    abfrage = SQLQuery(db)
    abfrage.sql = "SELECT name, stand, bild FROM t ORDER BY rowid"
    abfrage.open()
    formular = Form()
    formular.abfrage = abfrage
    formular.quelle = DataSource(abfrage)
    formular.gitter = DBGrid(formular, formular.quelle)
    formular.stand_text = DBText(formular, formular.quelle)
    formular.stand_text.field = "stand"
    formular.stand_edit = DBEdit(formular, formular.quelle)
    formular.stand_edit.field = "stand"
    formular.auswahl = DBComboBox(formular, formular.quelle)
    formular.auswahl.list_field = "name"
    formular.kurz = DBGrid(formular)
    formular.kurz.show_rows(db.query("SELECT name, stand, bild FROM t"))
    return formular


def test_data_controls_zeigen_werte_deutsch_lesbar() -> None:
    formular = _formular_mit_gemischten_werten()

    for gitter in (formular.gitter, formular.kurz):
        zellen = [
            [gitter._qwidget.item(z, s).text() for s in range(3)]
            for z in range(2)
        ]
        assert zellen == [
            ["A", "1,5", ""],
            ["", "", "(Binärdaten, 4 Bytes)"],
        ]
    assert formular.stand_text._qwidget.text() == "1,5"
    assert formular.stand_edit._qwidget.text() == "1,5"
    eintraege = [
        formular.auswahl._qwidget.itemText(i)
        for i in range(formular.auswahl._qwidget.count())
    ]
    assert eintraege == ["A", ""]


def test_dbedit_liest_eine_kommazahl_als_zahl() -> None:
    formular = _formular_mit_gemischten_werten()

    formular.stand_edit._qwidget.setText("2,25")
    formular.stand_edit._qwidget.editingFinished.emit()

    assert formular.abfrage.field_by_name("stand").value == 2.25


# -- Punkt 260 ---------------------------------------------------------


class _GrosseTabelle(Form):
    def create_components(self) -> None:
        self.db = SQLite3Connection(":memory:")
        self.db.verbindung.execute(
            "CREATE TABLE m (a INTEGER, b REAL, c TEXT, d TEXT, e INTEGER)"
        )
        self.db.verbindung.executemany(
            "INSERT INTO m VALUES (?, ?, ?, ?, ?)",
            ((i, i / 4, f"Name {i}", f"Ort {i % 97}", i % 7)
             for i in range(20_000)),
        )
        self.db.verbindung.commit()
        self.abfrage = SQLQuery(self.db)
        self.abfrage.sql = "SELECT * FROM m ORDER BY a"
        self.abfrage.open()
        self.ds = DataSource(self.abfrage)
        self.dbg = DBGrid(self, self.ds)
        self.dbt = DBText(self, self.ds)
        self.dbt.field = "c"
        self.dbn = DBNavigator(self, self.ds)
        self.dbc = DBComboBox(self, self.ds)
        self.dbc.list_field = "d"


def test_zeilenwechsel_in_grosser_tabelle_baut_sie_nicht_neu_auf() -> None:
    import time

    formular = _GrosseTabelle()
    grid = formular.dbg._qwidget
    neu_gefuellt: list[bool] = []
    grid.modell.modelReset.connect(lambda: neu_gefuellt.append(True))

    dauern = []
    for _ in range(10):
        start = time.perf_counter()
        formular.dbn.knopf_vor.click()
        dauern.append(time.perf_counter() - start)
    start = time.perf_counter()
    grid.setCurrentCell(500, 0)
    dauern.append(time.perf_counter() - start)

    assert max(dauern) < 0.05, dauern
    assert formular.abfrage.record_index == 500
    assert formular.dbt._qwidget.text() == "Name 500"
    assert grid.currentRow() == 500
    # Das Modell wurde nicht neu gefüllt.
    assert neu_gefuellt == []


def test_geaenderte_daten_fuellen_die_tabelle_trotzdem_neu() -> None:
    formular = _Formular()
    formular.dbn_kunden.knopf_vor.click()

    formular.abfrage.set_field("name", "Berta")
    formular.ds_kunden.aktualisieren()

    grid = formular.dbg_kunden._qwidget
    assert grid.item(1, 0).text() == "Berta"
    assert grid.currentRow() == 1


# -- to_dataframe() an einer gebundenen Abfrage (Punkt 426) -------------


@pytest.mark.parametrize("weg", ["navigator", "gitterklick"])
def test_to_dataframe_laesst_gebundene_controls_weiterarbeiten(
    weg: str,
) -> None:
    formular = _Formular()

    tabelle = formular.abfrage.to_dataframe()

    assert list(tabelle["name"]) == ["Anna", "Bo", "Cem"]
    assert formular.abfrage.record_count == 3
    assert formular.abfrage.record_index == 0
    assert formular.abfrage.column_names == ["name", "ort"]
    if weg == "navigator":
        formular.dbn_kunden.knopf_vor.click()
    else:
        formular.dbg_kunden._qwidget.setCurrentCell(1, 0)
    assert formular.abfrage.record_index == 1
    assert formular.dbt_ort._qwidget.text() == "Bonn"
    assert formular.dbe_name._qwidget.text() == "Bo"


def test_der_navigator_an_einer_ungeoeffneten_abfrage_tut_nichts() -> None:
    """Punkt 551: „<<“ und „>>“ beendeten das Programm mit
    `SQLQuery.first() ohne vorheriges open()`."""
    formular = _Formular()
    formular.abfrage.close()

    for knopf in (
        formular.dbn_kunden.knopf_erster,
        formular.dbn_kunden.knopf_zurueck,
        formular.dbn_kunden.knopf_vor,
        formular.dbn_kunden.knopf_letzter,
    ):
        knopf.click()
