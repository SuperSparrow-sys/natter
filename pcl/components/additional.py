"""Additional-Komponenten: Shape.

Siehe konzept-natter.md, Abschnitt 5.2 (Palette „Zusätzlich“). Weitere
Additional-Komponenten (StringGrid, Image, SpinEdit, ...) folgen in M1,
Schritt 6.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget

from pcl.control import Control
from pcl.errors import NatterPropertyError
from pcl.properties import Prop, typ_beschreibung

_FORMEN = ("rectangle", "circle")


class Brush:
    """Aufklappbare Untereigenschaft eines `Shape`, z. B.
    ``self.s_rot.brush.color = "#e53935"`` (Abschnitt 5.0, 5.1).

    Kein `Prop`, weil sie an einem festen Attributnamen (`brush`) hängt statt
    selbst zugewiesen zu werden – nur `color` ist veränderlich.
    """

    def __init__(self, besitzer: "Shape") -> None:
        self._besitzer = besitzer
        self._farbe = "#000000"

    @property
    def color(self) -> str:
        return self._farbe

    @color.setter
    def color(self, wert: str) -> None:
        if not isinstance(wert, str):
            raise NatterPropertyError(
                f"Shape.brush.color erwartet {typ_beschreibung(str)}, "
                f"erhalten wurde {typ_beschreibung(type(wert))}."
            )
        self._farbe = wert
        self._besitzer._qwidget.update()


class _ShapeQWidget(QWidget):
    def __init__(self, eltern_widget: QWidget, shape: "Shape") -> None:
        super().__init__(eltern_widget)
        self._shape = shape

    def paintEvent(self, event: Any) -> None:  # noqa: N802 (Qt-Konvention)
        maler = QPainter(self)
        maler.setRenderHint(QPainter.RenderHint.Antialiasing)
        farbe = QColor(self._shape.brush.color)
        maler.setBrush(farbe)
        maler.setPen(farbe)
        flaeche = self.rect().adjusted(0, 0, -1, -1)
        if self._shape.shape == "circle":
            maler.drawEllipse(flaeche)
        else:
            maler.drawRect(flaeche)


class Shape(Control):
    """Einfache geometrische Form zum Zeichnen. Qt-Basis: eigenes Painting
    (`QPainter` auf einem `QWidget`)."""

    shape = Prop(
        str,
        "rectangle",
        kategorie="Darstellung",
        doc=f"Form der Zeichnung: {' oder '.join(_FORMEN)}",
    )

    def __init__(self, parent: Control) -> None:
        self._brush = Brush(self)
        super().__init__(parent)

    @property
    def brush(self) -> Brush:
        return self._brush

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        return _ShapeQWidget(eltern_widget, self)

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "shape":
            self._qwidget.update()
