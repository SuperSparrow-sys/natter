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


# -- Ohne DataSource -----------------------------------
#
# Bis dahin verlangte jede dieser Komponenten eine `DataSource` im
# Konstruktor. Der Designer erzeugt Komponenten aber mit `typ(formular)`
# allein - keine davon liess sich also auf ein Formular legen oder vom
# Eigenschaften-Rundlauf pruefen (der offene Punkt aus M11).


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
