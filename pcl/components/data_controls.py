"""Data Controls (Abschnitt 10.1): an eine `DataSource` gebundene
Anzeige-/Bedienkomponenten – `DBGrid`, `DBEdit`, `DBText`,
`DBNavigator`, `DBComboBox`.

Jede Komponente registriert sich bei ihrer `DataSource` (siehe
`DataSource.aktualisieren` in `pcl/components/data_access.py`) und
zeichnet sich neu, sobald diese benachrichtigt wird – nach Navigation
über `DBNavigator` geschieht das automatisch, nach einem eigenen
``query.open``/``query.set_field`` im Code ruft man
``data_source.aktualisieren`` selbst auf.

Die `DataSource` ist überall freiwillig. Bis verlangte
jede dieser Komponenten sie im Konstruktor – `DBGrid(parent, quelle)`.
Der Designer erzeugt Komponenten aber mit ``typ(formular)`` allein, und
damit ließ sich keine einzige davon auf ein Formular legen oder vom
Eigenschaften-Rundlauf prüfen (der offene Punkt aus M11). Ohne Quelle
zeigen sie jetzt eine leere Anzeige, statt beim Anlegen zu scheitern.

Für den kurzen Weg – `SQLite3Connection.query` liefert eine Liste von
`dict`s – hat `DBGrid` zusätzlich `show_rows`: eine Zeile statt
Abfrage, Datenquelle und Benachrichtigung.
"""

from __future__ import annotations

import weakref
from typing import Any

from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)

from pcl.components.data_access import DataSource, anzeigetext
from pcl.components.tabelle import TabellenAnsicht
from pcl.control import Control
from pcl.properties import Event, Prop
from pcl.zahlen import zahl


def _quelle_wechseln(
    control: Control,
    alt: DataSource | None,
    neu: DataSource | None,
) -> None:
    """Meldet `control` bei der alten Quelle ab und bei der neuen an.
    Ohne die Abmeldung stand ein Steuerelement nach jeder Zuweisung
    einmal mehr in der Liste, auch bei einer Quelle, zu der es nicht
    mehr gehörte (Punkt 245)."""
    if alt is not None and alt is not neu:
        alt._abmelden(control._aktualisieren)
    if neu is not None:
        neu._registrieren(control._aktualisieren)


def _beim_zerstoeren_abmelden(control: Control, attribut: str) -> None:
    """Meldet `control` ab, sobald Qt sein Widget zerstört. Die
    Verbindung hält nur einen schwachen Verweis auf das Steuerelement,
    sonst hielte gerade sie es am Leben."""
    selbst = weakref.ref(control)

    def zerstoert(*_argumente: Any) -> None:
        control_ = selbst()
        if control_ is None:
            return
        quelle = control_.__dict__.get(attribut)
        if quelle is not None:
            quelle._abmelden(control_._aktualisieren)

    control._qwidget.destroyed.connect(zerstoert)


class _DatenControl(Control):
    """Gemeinsame Basis der Komponenten mit einer `data_source`.

    Sie trägt zwei Dinge. `_abfrage()` liefert die Abfrage hinter der
    Datenquelle oder `None` – ohne diese eine Stelle stünde in jeder
    Anzeige-Methode zweimal derselbe `is not None`-Test.

    Und `data_source` ist eine echte Eigenschaft, kein einfaches
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
        _quelle_wechseln(self, None, data_source)
        _beim_zerstoeren_abmelden(self, "_data_source")
        self._aktualisieren()

    @property
    def data_source(self) -> DataSource | None:
        """Die `DataSource`, deren Abfrage angezeigt wird, oder `None`."""
        return self._data_source

    @data_source.setter
    def data_source(self, quelle: DataSource | None) -> None:
        _quelle_wechseln(self, self._data_source, quelle)
        self._data_source = quelle
        self._aktualisieren()

    def _abfrage(self) -> Any:
        if self._data_source is None:
            return None
        return self._data_source.dataset

    def _aktualisieren(self) -> None:
        """Von den Unterklassen überschrieben - `DBNavigator` zeigt
        nichts an und lässt es dabei bewenden."""


class DBGrid(_DatenControl):
    """Zeigt Datensätze als Tabelle an. Qt-Basis: `QTableView` mit
    einem Modell, das die Zeilen der Abfrage unverändert hält und nur
    die sichtbaren Zellen in Text umwandelt (wie beim `StringGrid`,
    `pcl/components/tabelle.py`).

    Zwei Wege führen zur Anzeige. Der kurze braucht keine `DataSource`::

        self.g_konten.show_rows(self.db.query("SELECT * FROM konto"))

    Der ausführliche bindet eine `DataSource` und wird gebraucht, wo ein
    `DBNavigator` mitläuft – der bewegt einen Datensatzzeiger, den eine
    Liste von `dict`s nicht hat.
    """

    neue_attribute_erlaubt = True

    def __init__(self, parent: Control, data_source: DataSource | None = None) -> None:
        #: Solange die Tabelle neu gefüllt wird, meldet Qt jede
        #: verschobene Zelle als Zeilenwechsel. Das ist keiner.
        self._fuellt = False
        #: Welche Abfrage in welchem Stand zuletzt eingefüllt wurde.
        #: Solange beides gleich bleibt, hat sich höchstens der
        #: Datensatzzeiger bewegt.
        self._gefuellt_mit: tuple[Any, int] | None = None
        super().__init__(parent, data_source)

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        widget = TabellenAnsicht(eltern_widget, anzeigetext)
        # Schreibgeschützt: eine geänderte Zelle ginge sonst nirgends
        # hin. Geändert wird ein Datensatz über ein `DBEdit`.
        widget.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        widget.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        widget.currentCellChanged.connect(self._bei_zeilenwechsel)
        return widget

    def _bei_zeilenwechsel(self, zeile: int, *_rest: int) -> None:
        """Ein Klick auf eine andere Zeile bewegt den Datensatzzeiger.

        Bis Punkt 125 tat das nur der `DBNavigator`; ein `DBText`
        neben der Tabelle zeigte nach dem Klick weiter den alten
        Datensatz.
        """
        if self._fuellt or zeile < 0:
            return
        query = self._abfrage()
        if query is None or zeile >= query.record_count:
            return
        if zeile == query.record_index:
            return
        query._zeiger_setzen(zeile)
        self._data_source.aktualisieren()

    def _aktualisieren(self) -> None:
        self._fuellt = True
        try:
            query = self._abfrage()
            stand = None if query is None else (query, query._stand)
            alt = self._gefuellt_mit
            if (
                stand is not None and alt is not None
                and alt[0] is query and alt[1] == query._stand
            ):
                # Nur der Zeiger ist gewandert. Vorher wurde auch dann
                # jede Zelle neu angelegt; bei 20.000 Zeilen dauerte
                # jeder Schritt eine Viertelsekunde (Punkt 260).
                self._auswahl_setzen(query)
            else:
                self._neu_fuellen()
                self._gefuellt_mit = stand
        finally:
            self._fuellt = False

    def _auswahl_setzen(self, query: Any) -> None:
        widget = self._qwidget
        if query.eof:
            widget.clearSelection()
        else:
            widget.selectRow(query.record_index)

    def _neu_fuellen(self) -> None:
        query = self._abfrage()
        modell = self._qwidget.modell
        if query is None or not query.column_names:
            modell.titel_setzen([])
            modell.inhalt_setzen(0, [])
            return
        spalten = query.column_names
        modell.titel_setzen(spalten)
        # Die Zeilen der Abfrage selbst, ohne sie umzuwandeln: Text
        # wird erst beim Anzeigen daraus, und nur für die Zellen, die
        # zu sehen sind. Eine Zelle je `QTableWidgetItem` kostete bei
        # 100.000 Zeilen 290 MB (Punkt 356).
        modell.inhalt_setzen(len(spalten), query.all_rows())
        if not query.eof:
            self._qwidget.selectRow(query.record_index)

    def show_rows(self, zeilen: list[dict[str, Any]]) -> None:
        """Zeigt Zeilen an, wie `SQLite3Connection.query()` sie liefert –
        ohne `SQLQuery` und ohne `DataSource`::

            self.g_konten.show_rows(self.db.query("SELECT * FROM konto"))

        Die Spaltenüberschriften stammen aus den Schlüsseln der ersten
        Zeile. Eine leere Liste leert die Tabelle."""
        self._gefuellt_mit = None
        self._fuellt = True
        try:
            self._zeilen_zeigen(zeilen)
        finally:
            self._fuellt = False

    def _zeilen_zeigen(self, zeilen: list[dict[str, Any]]) -> None:
        modell = self._qwidget.modell
        spalten = list(zeilen[0]) if zeilen else []
        modell.titel_setzen(spalten)
        modell.inhalt_setzen(
            len(spalten),
            [[zeile.get(spalte) for spalte in spalten] for zeile in zeilen],
        )


class DBText(_DatenControl):
    """Reine Textanzeige eines Feldes der aktuellen Zeile. Qt-Basis:
    `QLabel`."""

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
    """Eingabefeld, gebunden an ein Feld der aktuellen Zeile. Qt-Basis:
    `QLineEdit`. Änderungen wirken auf den Zwischen-
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
        alt = query.field_by_name(self.field).value
        query.set_field(self.field, _eingabe_lesen(self._qwidget.text(), alt))


def _eingabe_lesen(eingabe: str, alt: Any) -> Any:
    """Der Wert, den eine Eingabe in einem `DBEdit` bedeutet. Stand im
    Feld eine Zahl, wird der Text als Zahl gelesen, mit Komma wie mit
    Punkt; sonst käme „1,5“ als Text in den Puffer (Punkt 246). Ein
    leeres Feld über einer Zahl oder einem leeren Wert wird wieder
    leer (`None`). Was sich nicht als Zahl lesen lässt, bleibt Text,
    wie es getippt wurde."""
    if isinstance(alt, bool) or not isinstance(alt, (int, float, type(None))):
        return eingabe
    if not eingabe.strip():
        return None
    if alt is None:
        return eingabe
    try:
        wert = zahl(eingabe)
    except ValueError:
        return eingabe
    if isinstance(alt, int) and wert.is_integer():
        return int(wert)
    return wert


class DBComboBox(Control):
    """Auswahlliste, deren Einträge aus einer zweiten `DataSource`
    stammen. Qt-Basis: `QComboBox`."""

    neue_attribute_erlaubt = True

    list_field = Prop(
        str, "", kategorie="Datenbank", doc="Anzuzeigende Spalte der Lookup-Datenquelle"
    )

    def __init__(self, parent: Control, list_source: DataSource | None = None) -> None:
        self._list_source = list_source
        super().__init__(parent)
        _quelle_wechseln(self, None, list_source)
        _beim_zerstoeren_abmelden(self, "_list_source")
        self._aktualisieren()

    @property
    def list_source(self) -> DataSource | None:
        """Die `DataSource`, aus der die Einträge stammen, oder `None`."""
        return self._list_source

    @list_source.setter
    def list_source(self, quelle: DataSource | None) -> None:
        _quelle_wechseln(self, self._list_source, quelle)
        self._list_source = quelle
        self._aktualisieren()

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        return QComboBox(eltern_widget)

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "list_field":
            self._aktualisieren()

    def _aktualisieren(self) -> None:
        query = self._list_source.dataset if self._list_source is not None else None
        # Wie beim `DBGrid`: wandert nur der Datensatzzeiger, bleiben
        # die Einträge dieselben (Punkt 260).
        stand = (
            None if query is None else (query, query._stand, self.list_field)
        )
        alt = self.__dict__.get("_gefuellt_mit")
        if (
            stand is not None and alt is not None and alt[0] is query
            and alt[1:] == stand[1:]
        ):
            return
        self._gefuellt_mit = stand
        widget = self._qwidget
        widget.blockSignals(True)
        widget.clear()
        if query is not None and self.list_field in query.column_names:
            spalten_index = query.column_names.index(self.list_field)
            for zeile in query.all_rows():
                widget.addItem(anzeigetext(zeile[spalten_index]))
        widget.blockSignals(False)

    @property
    def text(self) -> str:
        return self._qwidget.currentText()

    @property
    def item_index(self) -> int:
        return self._qwidget.currentIndex()


class DBNavigator(_DatenControl):
    """Knopfleiste zum Blättern durch die Datensätze und zum
    Bearbeiten. Qt-Basis: Leiste aus `QPushButton`, beschriftet mit
    Erster, Zurück, Vor, Letzter, Einfügen, Löschen, Speichern und
    Abbrechen.

    Vereinfachung, bewusst dokumentiert: Erster/Zurück/Vor/Letzter
    bewegen direkt den Datensatzzeiger von ``data_source.dataset`` und
    benachrichtigen die `DataSource` automatisch. Einfügen/Löschen/
    Speichern/Abbrechen lösen dagegen nur die Ereignisse
    ``on_insert``/``on_delete``/``on_save``/``on_cancel`` aus – eine
    passende SQL-Anweisung entsteht nicht von selbst, der Kurs schreibt
    SQL immer selbst
    (``self.query.sql = ...`` / ``exec_sql()``);
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
        # dem "Visueller Feinschliff"-Sammelpunkt aus PLAN.md (Git-Historie).
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
