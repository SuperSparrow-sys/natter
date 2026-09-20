"""Minimap für den Diagramm-Editor (M9, Teilschritt 2b; umgesetzt in
M15, Abschnitt 5).

Ein verkleinertes Abbild des ganzen Diagramms unten rechts, mit einem
Rahmen um den Ausschnitt, den man gerade sieht. Ein Klick springt
dorthin.

Das Abbild entsteht aus der Zeichenfläche selbst (`render`), nicht
aus einer zweiten Zeichenroutine. Jede Form, jede Verbindung, jeder
Block sieht in der Minimap deshalb automatisch so aus wie im Diagramm -
und bleibt es auch, wenn später ein Diagrammtyp dazukommt. Eine eigene
Miniaturdarstellung wäre eine zweite Wahrheit, die irgendwann von der
ersten abweicht.

Gerendert wird nicht bei jedem Neuzeichnen: das Abbild einer großen
Fläche kostet spürbar Zeit, und die Minimap ändert sich seltener als
die Ansicht. Es entsteht neu, wenn sich das Diagramm ändert, und wird
dazwischen wiederverwendet.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPaintEvent, QPen, QPixmap
from PySide6.QtWidgets import QWidget

#: Größe des Fensterchens unten rechts.
GROESSE = QSize(160, 120)

#: Abstand zum Rand des Rollbereichs.
RAND = 12


class Minimap(QWidget):
    """Das verkleinerte Gesamtbild mit dem Ausschnittsrahmen.

    `sprung_gewuenscht` meldet die Stelle, auf die geklickt wurde - in
    Diagrammkoordinaten, damit der Aufrufer nur noch dorthin rollen
    muss.
    """

    sprung_gewuenscht = Signal(QPoint)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(GROESSE)
        self._abbild: QPixmap | None = None
        #: Der sichtbare Ausschnitt in Diagrammkoordinaten.
        self._ausschnitt = QRect()
        #: Die Größe des ganzen Diagramms in Diagrammkoordinaten.
        self._gesamt = QSize(1, 1)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Klicken springt zu dieser Stelle im Diagramm")

    # -- Inhalt ---------------------------------------------------------

    def abbild_setzen(self, abbild: QPixmap | None, gesamt: QSize) -> None:
        self._abbild = abbild
        self._gesamt = QSize(max(gesamt.width(), 1), max(gesamt.height(), 1))
        self.update()

    def ausschnitt_setzen(self, ausschnitt: QRect) -> None:
        if self._ausschnitt != ausschnitt:
            self._ausschnitt = QRect(ausschnitt)
            self.update()

    # -- Zeichnen -------------------------------------------------------

    def _massstab(self) -> float:
        """Wie stark das Diagramm verkleinert wird - so, dass es ganz
        hineinpasst."""
        breite = self.width() - 2
        hoehe = self.height() - 2
        return min(breite / self._gesamt.width(), hoehe / self._gesamt.height())

    def paintEvent(self, ereignis: QPaintEvent) -> None:  # noqa: N802
        maler = QPainter(self)
        maler.fillRect(self.rect(), QColor("#ffffff"))

        if self._abbild is not None and not self._abbild.isNull():
            verkleinert = self._abbild.scaled(
                self.size() - QSize(2, 2),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            maler.drawPixmap(1, 1, verkleinert)

        massstab = self._massstab()
        rahmen = QRect(
            1 + int(self._ausschnitt.x() * massstab),
            1 + int(self._ausschnitt.y() * massstab),
            max(int(self._ausschnitt.width() * massstab), 3),
            max(int(self._ausschnitt.height() * massstab), 3),
        )
        maler.setPen(QPen(QColor("#c42b1c"), 1))
        maler.drawRect(rahmen)

        maler.setPen(QPen(QColor("#7b8f9a"), 1))
        maler.drawRect(self.rect().adjusted(0, 0, -1, -1))

    # -- Klick ----------------------------------------------------------

    def mousePressEvent(self, ereignis: QMouseEvent) -> None:  # noqa: N802
        massstab = self._massstab()
        if massstab <= 0:
            return
        stelle = ereignis.position()
        self.sprung_gewuenscht.emit(
            QPoint(int((stelle.x() - 1) / massstab), int((stelle.y() - 1) / massstab))
        )

    def mouseMoveEvent(self, ereignis: QMouseEvent) -> None:  # noqa: N802
        """Ziehen verschiebt den Ausschnitt fortlaufend - so, wie man es
        von einer Minimap erwartet."""
        if ereignis.buttons() & Qt.MouseButton.LeftButton:
            self.mousePressEvent(ereignis)


def abbild_erzeugen(zeichenflaeche: Any, gesamt: QSize) -> QPixmap:
    """Das verkleinerte Gesamtbild der Zeichenfläche.

    Gerendert wird bei Zoom 1,0 und danach zurückgestellt: sonst hinge
    das Abbild an der gerade eingestellten Zoomstufe, und beim
    Hineinzoomen zeigte die Minimap immer weniger vom Diagramm - genau
    das Gegenteil dessen, wofür sie da ist.
    """
    vorher = getattr(zeichenflaeche, "zoom", 1.0)
    breite = max(gesamt.width(), 1)
    hoehe = max(gesamt.height(), 1)

    abbild = QPixmap(breite, hoehe)
    abbild.fill(QColor("#ffffff"))
    try:
        zeichenflaeche.zoom = 1.0
        zeichenflaeche.render(abbild, QPoint(0, 0), QRect(0, 0, breite, hoehe))
    finally:
        zeichenflaeche.zoom = vorher
    return abbild
