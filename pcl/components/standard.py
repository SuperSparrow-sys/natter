"""Standard-Komponenten: Button, Label, Edit, CheckBox, RadioButton, Memo,
ListBox, ComboBox.

Siehe konzept-natter.md, Abschnitt 5.2 (Palette „Standard“). Weitere
Standard-Komponenten (RadioGroup, ScrollBar, GroupBox, Panel, MainMenu,
PopupMenu) folgen später in M1, Schritt 6.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
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


class Label(Control):
    """Textanzeige ohne eigene Bedienung. Qt-Basis: `QLabel`."""

    caption = Prop(str, "Label1", kategorie="Darstellung", doc="Anzeigetext")

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        widget = QLabel(eltern_widget)
        widget.setText(self.caption)
        return widget

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "caption":
            self._qwidget.setText(wert)


class Edit(Control):
    """Einzeiliges Eingabefeld. Qt-Basis: `QLineEdit`."""

    text = Prop(str, "", kategorie="Darstellung", doc="Eingegebener bzw. angezeigter Text")
    on_change = Event(doc="Wird bei jeder Änderung des Textes ausgelöst")

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        widget = QLineEdit(eltern_widget)
        widget.setText(self.text)
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
