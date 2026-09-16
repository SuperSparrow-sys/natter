"""Additional-Komponenten: Shape, StringGrid, Image.

Siehe konzept-natter.md, Abschnitt 5.2 (Palette „Zusätzlich“). Weitere
Additional-Komponenten (SpinEdit, FloatSpinEdit, MaskEdit, PaintBox,
HtmlViewer) sind in keinem der 18 Referenzprojekte in `referenz/lazarus/`
tatsächlich im Einsatz und daher zurückgestellt (Abschnitt 21: „MVP
strikt an den Übungsprojekten ausrichten“).
"""

from __future__ import annotations

from typing import Any

from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import QLabel, QTableWidget, QTableWidgetItem, QWidget

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

    def __init__(self, besitzer: Shape) -> None:
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
    def __init__(self, eltern_widget: QWidget, shape: Shape) -> None:
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


class Cells:
    """Aufklappbare Untereigenschaft eines `StringGrid`, Zugriff über
    ``self.sg_tabelle.cells[spalte, zeile]`` (Abschnitt 5.1)."""

    def __init__(self, besitzer: StringGrid) -> None:
        self._besitzer = besitzer

    def __getitem__(self, index: tuple[int, int]) -> str:
        spalte, zeile = index
        element = self._besitzer._qwidget.item(zeile, spalte)
        return element.text() if element is not None else ""

    def __setitem__(self, index: tuple[int, int], wert: str) -> None:
        if not isinstance(wert, str):
            raise NatterPropertyError(
                f"StringGrid.cells erwartet {typ_beschreibung(str)}, "
                f"erhalten wurde {typ_beschreibung(type(wert))}."
            )
        spalte, zeile = index
        widget = self._besitzer._qwidget
        element = widget.item(zeile, spalte)
        if element is None:
            element = QTableWidgetItem()
            widget.setItem(zeile, spalte, element)
        element.setText(wert)


class StringGrid(Control):
    """Tabelle aus Text-Zellen. Qt-Basis: `QTableWidget`."""

    row_count = Prop(int, 5, kategorie="Daten", doc="Anzahl der Zeilen")
    col_count = Prop(int, 5, kategorie="Daten", doc="Anzahl der Spalten")

    def __init__(self, parent: Control) -> None:
        self._cells = Cells(self)
        super().__init__(parent)

    @property
    def cells(self) -> Cells:
        return self._cells

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        widget = QTableWidget(eltern_widget)
        widget.setRowCount(self.row_count)
        widget.setColumnCount(self.col_count)
        return widget

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "row_count":
            self._qwidget.setRowCount(wert)
        elif name == "col_count":
            self._qwidget.setColumnCount(wert)


class Picture:
    """Aufklappbare Untereigenschaft eines `Image`, z. B.
    ``self.i_bild.picture.load_from_file("assets/cookie.png")``
    (Abschnitt 5.0, 11.4)."""

    def __init__(self, besitzer: Image) -> None:
        self._besitzer = besitzer
        self._pfad: str | None = None

    @property
    def pfad(self) -> str | None:
        return self._pfad

    def load_from_file(self, pfad: str) -> None:
        if not isinstance(pfad, str):
            raise NatterPropertyError(
                f"Image.picture.load_from_file erwartet {typ_beschreibung(str)}, "
                f"erhalten wurde {typ_beschreibung(type(pfad))}."
            )
        self._pfad = pfad
        self._besitzer._qwidget.setPixmap(QPixmap(pfad))

    def clear(self) -> None:
        self._pfad = None
        self._besitzer._qwidget.clear()


class Image(Control):
    """Bildanzeige. Qt-Basis: `QLabel` mit `QPixmap`."""

    def __init__(self, parent: Control) -> None:
        self._picture = Picture(self)
        super().__init__(parent)

    @property
    def picture(self) -> Picture:
        return self._picture

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        widget = QLabel(eltern_widget)
        widget.setScaledContents(True)
        return widget
