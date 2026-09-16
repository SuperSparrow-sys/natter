"""Standard-Komponenten: Button, Label, Edit, CheckBox, RadioButton.

Siehe konzept-natter.md, Abschnitt 5.2 (Palette „Standard“). Weitere
Standard-Komponenten (RadioGroup, Memo, ComboBox, ListBox, ScrollBar,
GroupBox, Panel, MainMenu, PopupMenu) folgen später in M1, Schritt 6
(brauchen die noch fehlende `Strings`-Sammlung bzw. Menüstruktur).
"""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QCheckBox, QLabel, QLineEdit, QPushButton, QRadioButton, QWidget

from pcl.control import Control
from pcl.properties import Event, Prop


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
