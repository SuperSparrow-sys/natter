"""Data Controls (Abschnitt 10.1): an eine `DataSource` gebundene
Anzeige-/Bedienkomponenten – `DBGrid`, `DBEdit`, `DBText`,
`DBNavigator`, `DBComboBox`.

Jede Komponente registriert sich bei ihrer `DataSource` (siehe
`DataSource.aktualisieren()` in `pcl/components/data_access.py`) und
zeichnet sich neu, sobald diese benachrichtigt wird – nach Navigation
über `DBNavigator` geschieht das automatisch, nach einem eigenen
``query.open()``/``query.set_field()`` im Code ruft man
``data_source.aktualisieren()`` selbst auf.

**Die `DataSource` ist überall freiwillig.** Bis September 2026 verlangte
jede dieser Komponenten sie im Konstruktor – `DBGrid(parent, quelle)`.
Der Designer erzeugt Komponenten aber mit ``typ(formular)`` allein, und
damit ließ sich keine einzige davon auf ein Formular legen oder vom
Eigenschaften-Rundlauf prüfen (der offene Punkt aus M11). Ohne Quelle
zeigen sie jetzt eine leere Anzeige, statt beim Anlegen zu scheitern.

Für den kurzen Weg – `SQLite3Connection.query()` liefert eine Liste von
`dict`s – hat `DBGrid` zusätzlich `show_rows()`: eine Zeile statt
Abfrage, Datenquelle und Benachrichtigung.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from pcl.components.data_access import DataSource
from pcl.control import Control
from pcl.properties import Event, Prop


class _DatenControl(Control):
    """Gemeinsame Basis der Komponenten mit einer `data_source`.

    Sie trägt zwei Dinge. `_abfrage()` liefert die Abfrage hinter der
    Datenquelle oder `None` – ohne diese eine Stelle stünde in jeder
    Anzeige-Methode zweimal derselbe `is not None`-Test.

    Und `data_source` ist eine **echte Eigenschaft**, kein einfaches
    Attribut. Das ist nötig, seit die Datenquelle freiwillig ist: wer
    sie nachträglich zuweist (``self.g_konten.data_source = quelle``),
    bekäme sonst eine Komponente, die sich nie meldet. Die Anmeldung bei
    der `DataSource` geschah bis dahin ausschließlich im Konstruktor –
    die Zuweisung lief durch, die Tabelle blieb stumm leer. Der Setter
    meldet an und zeichnet neu.
    """

    def __init__(self, parent: Control, data_source: DataSource | None = None) -> None:
        # Vor `super().__init__`, weil es noch kein Widget gibt, auf dem
        # sich neu zeichnen liesse.
        self._data_source = data_source
        super().__init__(parent)
        if data_source is not None:
            data_source._registrieren(self._aktualisieren)
        self._aktualisieren()

    @property
    def data_source(self) -> DataSource | None:
        """Die `DataSource`, deren Abfrage angezeigt wird, oder `None`."""
        return self._data_source

    @data_source.setter
    def data_source(self, quelle: DataSource | None) -> None:
        self._data_source = quelle
        if quelle is not None:
            quelle._registrieren(self._aktualisieren)
        self._aktualisieren()

    def _abfrage(self) -> Any:
        if self._data_source is None:
            return None
        return self._data_source.dataset

    def _aktualisieren(self) -> None:
        """Von den Unterklassen überschrieben - `DBNavigator` zeigt
        nichts an und lässt es dabei bewenden."""


class DBGrid(_DatenControl):
    """Zeigt Datensätze als Tabelle an. Qt-Basis: `QTableWidget` (wie
    `StringGrid`).

    Zwei Wege führen zur Anzeige. Der kurze braucht keine `DataSource`::

        self.g_konten.show_rows(self.db.query("SELECT * FROM konto"))

    Der ausführliche bindet eine `DataSource` und wird gebraucht, wo ein
    `DBNavigator` mitläuft – der bewegt einen Datensatzzeiger, den eine
    Liste von `dict`s nicht hat.
    """

    neue_attribute_erlaubt = True

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        return QTableWidget(eltern_widget)

    def _aktualisieren(self) -> None:
        query = self._abfrage()
        widget = self._qwidget
        widget.setRowCount(0)
        widget.setColumnCount(0)
        if query is None or not query.column_names:
            return
        spalten = query.column_names
        widget.setColumnCount(len(spalten))
        widget.setHorizontalHeaderLabels(spalten)
        zeilen = query.all_rows()
        widget.setRowCount(len(zeilen))
        for zeile_index, zeile in enumerate(zeilen):
            for spalten_index, wert in enumerate(zeile):
                text = "" if wert is None else str(wert)
                widget.setItem(zeile_index, spalten_index, QTableWidgetItem(text))
        if not query.eof:
            widget.selectRow(query.record_index)

    def show_rows(self, zeilen: list[dict[str, Any]]) -> None:
        """Zeigt Zeilen an, wie `SQLite3Connection.query()` sie liefert –
        ohne `SQLQuery` und ohne `DataSource`::

            self.g_konten.show_rows(self.db.query("SELECT * FROM konto"))

        Die Spaltenüberschriften stammen aus den Schlüsseln der ersten
        Zeile. Eine leere Liste leert die Tabelle."""
        widget = self._qwidget
        widget.setRowCount(0)
        widget.setColumnCount(0)
        if not zeilen:
            return
        spalten = list(zeilen[0])
        widget.setColumnCount(len(spalten))
        widget.setHorizontalHeaderLabels(spalten)
        widget.setRowCount(len(zeilen))
        for zeile_index, zeile in enumerate(zeilen):
            for spalten_index, spalte in enumerate(spalten):
                wert = zeile.get(spalte)
                text = "" if wert is None else str(wert)
                widget.setItem(zeile_index, spalten_index, QTableWidgetItem(text))


class DBText(_DatenControl):
    """Reine Textanzeige eines Feldes der aktuellen Zeile (Abschnitt
    10.1). Qt-Basis: `QLabel`."""

    neue_attribute_erlaubt = True

    field = Prop(str, "", kategorie="Datenbank", doc="Name des angezeigten Feldes")

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        return QLabel(eltern_widget)

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "field":
            self._aktualisieren()

    def _aktualisieren(self) -> None:
        query = self._abfrage()
        if query is None or query.eof or not self.field:
            self._qwidget.setText("")
            return
        self._qwidget.setText(query.field_by_name(self.field).as_string)


class DBEdit(_DatenControl):
    """Eingabefeld, gebunden an ein Feld der aktuellen Zeile (Abschnitt
    10.1). Qt-Basis: `QLineEdit`. Änderungen wirken auf den Zwischen-
    speicher der `SQLQuery` (siehe `SQLQuery.set_field()`), nicht direkt
    auf die Datenbank."""

    neue_attribute_erlaubt = True

    field = Prop(str, "", kategorie="Datenbank", doc="Name des gebundenen Feldes")

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        widget = QLineEdit(eltern_widget)
        widget.editingFinished.connect(self._bei_bearbeitung_beendet)
        return widget

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "field":
            self._aktualisieren()

    def _aktualisieren(self) -> None:
        query = self._abfrage()
        aktiv = query is not None and not query.eof and bool(self.field)
        self._qwidget.setEnabled(aktiv)
        self._qwidget.setText(query.field_by_name(self.field).as_string if aktiv else "")

    def _bei_bearbeitung_beendet(self) -> None:
        query = self._abfrage()
        if query is None or query.eof or not self.field:
            return
        query.set_field(self.field, self._qwidget.text())


class DBComboBox(Control):
    """Auswahlliste, deren Einträge aus einer Lookup-`DataSource`
    stammen (Abschnitt 10.1). Qt-Basis: `QComboBox`."""

    neue_attribute_erlaubt = True

    list_field = Prop(
        str, "", kategorie="Datenbank", doc="Anzuzeigende Spalte der Lookup-Datenquelle"
    )

    def __init__(self, parent: Control, list_source: DataSource | None = None) -> None:
        self._list_source = list_source
        super().__init__(parent)
        if list_source is not None:
            list_source._registrieren(self._aktualisieren)
        self._aktualisieren()

    @property
    def list_source(self) -> DataSource | None:
        """Die `DataSource`, aus der die Einträge stammen, oder `None`."""
        return self._list_source

    @list_source.setter
    def list_source(self, quelle: DataSource | None) -> None:
        self._list_source = quelle
        if quelle is not None:
            quelle._registrieren(self._aktualisieren)
        self._aktualisieren()

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        return QComboBox(eltern_widget)

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "list_field":
            self._aktualisieren()

    def _aktualisieren(self) -> None:
        query = self._list_source.dataset if self._list_source is not None else None
        widget = self._qwidget
        widget.blockSignals(True)
        widget.clear()
        if query is not None and self.list_field in query.column_names:
            spalten_index = query.column_names.index(self.list_field)
            for zeile in query.all_rows():
                widget.addItem(str(zeile[spalten_index]))
        widget.blockSignals(False)

    @property
    def text(self) -> str:
        return self._qwidget.currentText()

    @property
    def item_index(self) -> int:
        return self._qwidget.currentIndex()


class DBNavigator(_DatenControl):
    """Symbolleiste zur Datensatznavigation (Abschnitt 10.1: Erster/
    Zurück/Vor/Letzter/Einfügen/Löschen/Speichern/Abbrechen). Qt-Basis:
    Leiste aus `QPushButton`.

    **Vereinfachung, bewusst dokumentiert:** Erster/Zurück/Vor/Letzter
    bewegen direkt den Datensatzzeiger von ``data_source.dataset`` und
    benachrichtigen die `DataSource` automatisch. Einfügen/Löschen/
    Speichern/Abbrechen lösen dagegen nur die Ereignisse
    ``on_insert``/``on_delete``/``on_save``/``on_cancel`` aus – anders
    als in Lazarus, wo der Dataset automatisch die passende SQL-
    Anweisung erzeugt, schreibt der Kurs SQL immer selbst
    (Abschnitt 10.1: ``self.query.sql = ...`` / ``exec_sql()``);
    `DBNavigator` stellt dafür nur die Schaltfläche und den Auslöser
    bereit, die tatsächliche Anweisung schreibt die Ereignis-Methode."""

    neue_attribute_erlaubt = True

    on_insert = Event(doc='Wird bei Klick auf "Einfügen" ausgelöst')
    on_delete = Event(doc='Wird bei Klick auf "Löschen" ausgelöst')
    on_save = Event(doc='Wird bei Klick auf "Speichern" ausgelöst')
    on_cancel = Event(doc='Wird bei Klick auf "Abbrechen" ausgelöst')

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        widget = QWidget(eltern_widget)
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        # Einfache ASCII-Beschriftungen statt Pfeil-/Glyphen-Symbolen -
        # unter QT_QPA_PLATFORM=offscreen rendern manche Einzelzeichen
        # (z. B. "|") mit falscher Glyphe (siehe AGENTS.md, Abschnitt
        # "Tests"); eigene SVG-Symbole wie beim Rest der IDE folgen mit
        # dem "Visueller Feinschliff"-Sammelpunkt aus docs/PLAN.md.
        self.knopf_erster = self._knopf(layout, "<<", self._erster)
        self.knopf_zurueck = self._knopf(layout, "<", self._zurueck)
        self.knopf_vor = self._knopf(layout, ">", self._vor)
        self.knopf_letzter = self._knopf(layout, ">>", self._letzter)
        self.knopf_einfuegen = self._knopf(layout, "+", self._einfuegen)
        self.knopf_loeschen = self._knopf(layout, "-", self._loeschen)
        self.knopf_speichern = self._knopf(layout, "Speichern", self._speichern)
        self.knopf_abbrechen = self._knopf(layout, "Abbrechen", self._abbrechen)
        return widget

    def _knopf(self, layout: QHBoxLayout, text: str, handler: Any) -> QPushButton:
        knopf = QPushButton(text)
        knopf.clicked.connect(handler)
        layout.addWidget(knopf)
        return knopf

    def _erster(self) -> None:
        dataset = self._abfrage()
        if dataset is not None:
            dataset.first()
            self._data_source.aktualisieren()

    def _zurueck(self) -> None:
        dataset = self._abfrage()
        if dataset is not None and dataset.record_index > 0:
            dataset.prior()
            self._data_source.aktualisieren()

    def _vor(self) -> None:
        dataset = self._abfrage()
        if dataset is not None and dataset.record_index < dataset.record_count - 1:
            dataset.next()
            self._data_source.aktualisieren()

    def _letzter(self) -> None:
        dataset = self._abfrage()
        if dataset is not None:
            dataset.last()
            self._data_source.aktualisieren()

    def _einfuegen(self) -> None:
        if self.on_insert is not None:
            self.on_insert(self)

    def _loeschen(self) -> None:
        if self.on_delete is not None:
            self.on_delete(self)

    def _speichern(self) -> None:
        if self.on_save is not None:
            self.on_save(self)

    def _abbrechen(self) -> None:
        if self.on_cancel is not None:
            self.on_cancel(self)
