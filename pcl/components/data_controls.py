"""Data Controls (Abschnitt 10.1): an eine `DataSource` gebundene
Anzeige-/Bedienkomponenten – `DBGrid`, `DBEdit`, `DBText`,
`DBNavigator`, `DBComboBox`.

Jede Komponente registriert sich bei ihrer `DataSource` (siehe
`DataSource.aktualisieren()` in `pcl/components/data_access.py`) und
zeichnet sich neu, sobald diese benachrichtigt wird – nach Navigation
über `DBNavigator` geschieht das automatisch, nach einem eigenen
``query.open()``/``query.set_field()`` im Code ruft man
``data_source.aktualisieren()`` selbst auf.
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


class DBGrid(Control):
    """Zeigt alle Datensätze einer `DataSource` als Tabelle an. Qt-Basis:
    `QTableWidget` (wie `StringGrid`)."""

    neue_attribute_erlaubt = True

    def __init__(self, parent: Control, data_source: DataSource) -> None:
        self.data_source = data_source
        super().__init__(parent)
        data_source._registrieren(self._aktualisieren)
        self._aktualisieren()

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        return QTableWidget(eltern_widget)

    def _aktualisieren(self) -> None:
        query = self.data_source.dataset
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


class DBText(Control):
    """Reine Textanzeige eines Feldes der aktuellen Zeile (Abschnitt
    10.1). Qt-Basis: `QLabel`."""

    neue_attribute_erlaubt = True

    field = Prop(str, "", kategorie="Datenbank", doc="Name des angezeigten Feldes")

    def __init__(self, parent: Control, data_source: DataSource) -> None:
        self.data_source = data_source
        super().__init__(parent)
        data_source._registrieren(self._aktualisieren)
        self._aktualisieren()

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        return QLabel(eltern_widget)

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "field":
            self._aktualisieren()

    def _aktualisieren(self) -> None:
        query = self.data_source.dataset
        if query is None or query.eof or not self.field:
            self._qwidget.setText("")
            return
        self._qwidget.setText(query.field_by_name(self.field).as_string)


class DBEdit(Control):
    """Eingabefeld, gebunden an ein Feld der aktuellen Zeile (Abschnitt
    10.1). Qt-Basis: `QLineEdit`. Änderungen wirken auf den Zwischen-
    speicher der `SQLQuery` (siehe `SQLQuery.set_field()`), nicht direkt
    auf die Datenbank."""

    neue_attribute_erlaubt = True

    field = Prop(str, "", kategorie="Datenbank", doc="Name des gebundenen Feldes")

    def __init__(self, parent: Control, data_source: DataSource) -> None:
        self.data_source = data_source
        super().__init__(parent)
        data_source._registrieren(self._aktualisieren)
        self._aktualisieren()

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        widget = QLineEdit(eltern_widget)
        widget.editingFinished.connect(self._bei_bearbeitung_beendet)
        return widget

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "field":
            self._aktualisieren()

    def _aktualisieren(self) -> None:
        query = self.data_source.dataset
        aktiv = query is not None and not query.eof and bool(self.field)
        self._qwidget.setEnabled(aktiv)
        self._qwidget.setText(query.field_by_name(self.field).as_string if aktiv else "")

    def _bei_bearbeitung_beendet(self) -> None:
        query = self.data_source.dataset
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

    def __init__(self, parent: Control, list_source: DataSource) -> None:
        self.list_source = list_source
        super().__init__(parent)
        list_source._registrieren(self._aktualisieren)
        self._aktualisieren()

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        return QComboBox(eltern_widget)

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "list_field":
            self._aktualisieren()

    def _aktualisieren(self) -> None:
        query = self.list_source.dataset
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


class DBNavigator(Control):
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

    def __init__(self, parent: Control, data_source: DataSource) -> None:
        self.data_source = data_source
        super().__init__(parent)

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
        dataset = self.data_source.dataset
        if dataset is not None:
            dataset.first()
            self.data_source.aktualisieren()

    def _zurueck(self) -> None:
        dataset = self.data_source.dataset
        if dataset is not None and dataset.record_index > 0:
            dataset.prior()
            self.data_source.aktualisieren()

    def _vor(self) -> None:
        dataset = self.data_source.dataset
        if dataset is not None and dataset.record_index < dataset.record_count - 1:
            dataset.next()
            self.data_source.aktualisieren()

    def _letzter(self) -> None:
        dataset = self.data_source.dataset
        if dataset is not None:
            dataset.last()
            self.data_source.aktualisieren()

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
