"""Standard-Komponenten: Button, Label, Edit, CheckBox, RadioButton, Memo,
ListBox, ComboBox, ScrollBar.

Siehe konzept-natter.md, Abschnitt 5.2 (Palette „Standard“). Weitere
Standard-Komponenten (RadioGroup, GroupBox, Panel, MainMenu, PopupMenu)
sind in keinem der 18 Referenzprojekte tatsächlich genutzt (`RadioGroup1`
in `f_Pizza` ist nur deklariert) und daher zurückgestellt.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QScrollBar,
    QWidget,
)

from pcl.control import Control
from pcl.properties import Event, Prop
from pcl.strings import Strings


class Button(Control):
    """Schaltfläche für Klick-Ereignisse. Qt-Basis: `QPushButton`."""

    caption = Prop(str, "Button", kategorie="Darstellung", doc="Beschriftung des Buttons")
    on_click = Event(doc="Wird beim Klicken ausgelöst")

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        widget = QPushButton(eltern_widget)
        widget.setText(self.caption)
        widget.clicked.connect(self._bei_klick)
        return widget

    def _bei_klick(self) -> None:
        if self.on_click is not None:
            self.on_click(self)

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "caption":
            self._qwidget.setText(wert)


class _KlickbaresLabel(QLabel):
    """`QLabel`, das Mausklicks an das besitzende `Label` weiterreicht
    (Abschnitt 5.1: `on_click` – z. B. für Cookie-Klicker-artige
    Übungen, in denen ein Label statt eines Buttons angeklickt wird)."""

    def __init__(self, eltern_widget: QWidget, label: Label) -> None:
        super().__init__(eltern_widget)
        self._label = label

    def mousePressEvent(self, event: Any) -> None:
        super().mousePressEvent(event)
        self._label._bei_klick()


class Label(Control):
    """Textanzeige, per `on_click` auch anklickbar. Qt-Basis: `QLabel`.

    `color`/`transparent` wie Lazarus' `TLabel` (Nutzer-Feedback
    September 2026): ein Label kann eine eigene Hintergrundfarbe zeigen
    - nützlich, um es sichtbar über einer `Shape` zu platzieren."""

    caption = Prop(str, "Label1", kategorie="Darstellung", doc="Anzeigetext")
    color = Prop(
        str,
        "",
        kategorie="Darstellung",
        doc="Hintergrundfarbe als #RRGGBB (nur bei transparent=False)",
    )
    transparent = Prop(
        bool, True, kategorie="Darstellung", doc="Wenn wahr (Standard), kein eigener Hintergrund"
    )
    on_click = Event(doc="Wird beim Klicken ausgelöst")

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        widget = _KlickbaresLabel(eltern_widget, self)
        widget.setText(self.caption)
        return widget

    def _bei_klick(self) -> None:
        if self.on_click is not None:
            self.on_click(self)

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "caption":
            self._qwidget.setText(wert)
        elif name in ("color", "transparent"):
            self._eigenes_qss_anwenden()

    def _qss_teile(self) -> list[str]:
        teile = super()._qss_teile()
        if not self.transparent and self.color:
            teile.append(f"background-color: {self.color};")
        return teile


class Edit(Control):
    """Einzeiliges Eingabefeld. Qt-Basis: `QLineEdit`."""

    text = Prop(str, "", kategorie="Darstellung", doc="Eingegebener bzw. angezeigter Text")
    read_only = Prop(bool, False, kategorie="Verhalten", doc="Wenn wahr, nicht bearbeitbar")
    color = Prop(
        str, "", kategorie="Darstellung", doc="Hintergrundfarbe als #RRGGBB, leer = Theme-Standard"
    )
    on_change = Event(doc="Wird bei jeder Änderung des Textes ausgelöst")

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        widget = QLineEdit(eltern_widget)
        widget.setText(self.text)
        widget.setReadOnly(self.read_only)
        widget.textChanged.connect(self._bei_textaenderung)
        return widget

    def _bei_textaenderung(self, neuer_text: str) -> None:
        # QLineEdit.setText ändert die Anzeige nicht erneut, wenn der Text
        # bereits übereinstimmt, daher keine Endlosschleife über Prop.__set__.
        self.text = neuer_text
        if self.on_change is not None:
            self.on_change(self)

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "text":
            self._qwidget.setText(wert)
        elif name == "read_only":
            self._qwidget.setReadOnly(wert)
        elif name == "color":
            self._eigenes_qss_anwenden()

    def _qss_teile(self) -> list[str]:
        teile = super()._qss_teile()
        if self.color:
            teile.append(f"background-color: {self.color};")
        return teile


class CheckBox(Control):
    """Kontrollkästchen. Qt-Basis: `QCheckBox`."""

    caption = Prop(str, "CheckBox1", kategorie="Darstellung", doc="Beschriftung")
    checked = Prop(
        bool, False, kategorie="Verhalten", doc="Legt fest, ob das Kästchen angehakt ist"
    )
    on_change = Event(doc="Wird beim Umschalten ausgelöst")

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        widget = QCheckBox(eltern_widget)
        widget.setText(self.caption)
        widget.setChecked(self.checked)
        widget.toggled.connect(self._bei_umschalten)
        return widget

    def _bei_umschalten(self, wert: bool) -> None:
        self.checked = wert
        if self.on_change is not None:
            self.on_change(self)

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "caption":
            self._qwidget.setText(wert)
        elif name == "checked":
            self._qwidget.setChecked(wert)


class Memo(Control):
    """Mehrzeiliges Textfeld. Qt-Basis: `QPlainTextEdit`.

    `lines` ist eine aufklappbare `Strings`-Untereigenschaft (Abschnitt
    5.0, 11.2), kein eigenständiges `Prop` – wie `Shape.brush`.
    """

    def __init__(self, parent: Control) -> None:
        self._lines = Strings(self._lines_geaendert)
        super().__init__(parent)

    @property
    def lines(self) -> Strings:
        return self._lines

    @lines.setter
    def lines(self, werte: list[str]) -> None:
        self._lines.zuweisen(werte)

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        return QPlainTextEdit(eltern_widget)

    def _lines_geaendert(self) -> None:
        self._qwidget.setPlainText("\n".join(self._lines))


class ListBox(Control):
    """Einfache Auswahlliste. Qt-Basis: `QListWidget`."""

    item_index = Prop(
        int, -1, kategorie="Verhalten", doc="Index des ausgewählten Eintrags, -1 = keine Auswahl"
    )

    def __init__(self, parent: Control) -> None:
        self._items = Strings(self._items_geaendert)
        super().__init__(parent)

    @property
    def items(self) -> Strings:
        return self._items

    @items.setter
    def items(self, werte: list[str]) -> None:
        self._items.zuweisen(werte)

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        widget = QListWidget(eltern_widget)
        widget.currentRowChanged.connect(self._bei_zeilenwechsel)
        return widget

    def _items_geaendert(self) -> None:
        self._qwidget.clear()
        self._qwidget.addItems(list(self._items))

    def _bei_zeilenwechsel(self, zeile: int) -> None:
        self.item_index = zeile

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "item_index":
            self._qwidget.setCurrentRow(wert)


class ComboBox(Control):
    """Dropdown-Auswahl. Qt-Basis: `QComboBox`."""

    item_index = Prop(
        int, -1, kategorie="Verhalten", doc="Index des ausgewählten Eintrags, -1 = keine Auswahl"
    )
    text = Prop(str, "", kategorie="Darstellung", doc="Angezeigter bzw. ausgewählter Text")

    def __init__(self, parent: Control) -> None:
        self._items = Strings(self._items_geaendert)
        super().__init__(parent)

    @property
    def items(self) -> Strings:
        return self._items

    @items.setter
    def items(self, werte: list[str]) -> None:
        self._items.zuweisen(werte)

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        widget = QComboBox(eltern_widget)
        widget.currentIndexChanged.connect(self._bei_index_wechsel)
        widget.currentTextChanged.connect(self._bei_text_wechsel)
        return widget

    def _items_geaendert(self) -> None:
        self._qwidget.clear()
        self._qwidget.addItems(list(self._items))

    def _bei_index_wechsel(self, index: int) -> None:
        self.item_index = index

    def _bei_text_wechsel(self, text: str) -> None:
        self.text = text

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "item_index":
            self._qwidget.setCurrentIndex(wert)
        elif name == "text":
            self._qwidget.setCurrentText(wert)


class RadioButton(Control):
    """Optionsfeld, typischerweise in einer Gruppe mit anderen
    `RadioButton`-Komponenten. Qt-Basis: `QRadioButton`."""

    caption = Prop(str, "RadioButton1", kategorie="Darstellung", doc="Beschriftung")
    checked = Prop(
        bool, False, kategorie="Verhalten", doc="Legt fest, ob die Option ausgewählt ist"
    )
    on_change = Event(doc="Wird beim Umschalten ausgelöst")

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        widget = QRadioButton(eltern_widget)
        widget.setText(self.caption)
        widget.setChecked(self.checked)
        widget.toggled.connect(self._bei_umschalten)
        return widget

    def _bei_umschalten(self, wert: bool) -> None:
        self.checked = wert
        if self.on_change is not None:
            self.on_change(self)

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "caption":
            self._qwidget.setText(wert)
        elif name == "checked":
            self._qwidget.setChecked(wert)


class ScrollBar(Control):
    """Bildlaufleiste, im Unterricht oft zur Eingabe eines Zahlenwerts
    genutzt. Qt-Basis: `QScrollBar` (horizontal)."""

    minimum = Prop(int, 0, kategorie="Verhalten", doc="Kleinster möglicher Wert")
    maximum = Prop(int, 100, kategorie="Verhalten", doc="Größter möglicher Wert")
    position = Prop(int, 0, kategorie="Verhalten", doc="Aktueller Wert")
    on_change = Event(doc="Wird bei Änderung der Position ausgelöst")

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        widget = QScrollBar(Qt.Orientation.Horizontal, eltern_widget)
        widget.setMinimum(self.minimum)
        widget.setMaximum(self.maximum)
        widget.setValue(self.position)
        widget.valueChanged.connect(self._bei_wertaenderung)
        return widget

    def _bei_wertaenderung(self, wert: int) -> None:
        self.position = wert
        if self.on_change is not None:
            self.on_change(self)

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "minimum":
            self._qwidget.setMinimum(wert)
        elif name == "maximum":
            self._qwidget.setMaximum(wert)
        elif name == "position":
            self._qwidget.setValue(wert)
