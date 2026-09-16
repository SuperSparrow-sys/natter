"""Standard-Komponenten: Button, Label.

Siehe konzept-natter.md, Abschnitt 5.2 (Palette „Standard“). Weitere
Standard-Komponenten (Edit, CheckBox, RadioButton, ...) folgen in M1,
Schritt 6.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QLabel, QPushButton, QWidget

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
