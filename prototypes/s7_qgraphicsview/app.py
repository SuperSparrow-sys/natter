"""S7: zwei Formen mit andockender, rechtwinkliger Verbindung.

Siehe prototypes/s7_qgraphicsview/README.md.
"""

import sys

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QPainterPath, QPen
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsItem,
    QGraphicsPathItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
)


class VerbundenesRechteck(QGraphicsRectItem):
    def __init__(self, x: float, y: float, w: float, h: float, verbindung: "Verbindung | None" = None):
        super().__init__(0, 0, w, h)
        self.setPos(x, y)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.verbindung = verbindung

    def itemChange(self, change, value):
        if (
            change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged
            and self.verbindung is not None
        ):
            self.verbindung.aktualisieren()
        return super().itemChange(change, value)


class Verbindung(QGraphicsPathItem):
    def __init__(self, von: VerbundenesRechteck, zu: VerbundenesRechteck):
        super().__init__()
        self.von = von
        self.zu = zu
        stift = QPen()
        stift.setWidthF(1.5)
        self.setPen(stift)
        self.setZValue(-1)

    def aktualisieren(self) -> None:
        von_punkt = self.von.sceneBoundingRect().center()
        von_punkt.setX(self.von.sceneBoundingRect().right())
        zu_punkt = self.zu.sceneBoundingRect().center()
        zu_punkt.setX(self.zu.sceneBoundingRect().left())
        mitte_x = (von_punkt.x() + zu_punkt.x()) / 2

        pfad = QPainterPath(von_punkt)
        pfad.lineTo(QPointF(mitte_x, von_punkt.y()))
        pfad.lineTo(QPointF(mitte_x, zu_punkt.y()))
        pfad.lineTo(zu_punkt)
        self.setPath(pfad)


def main() -> None:
    app = QApplication(sys.argv)

    szene = QGraphicsScene(QRectF(0, 0, 500, 300))
    links = VerbundenesRechteck(40, 100, 120, 80)
    rechts = VerbundenesRechteck(340, 60, 120, 80)
    verbindung = Verbindung(links, rechts)
    links.verbindung = verbindung
    rechts.verbindung = verbindung

    szene.addItem(links)
    szene.addItem(rechts)
    szene.addItem(verbindung)
    verbindung.aktualisieren()

    ansicht = QGraphicsView(szene)
    ansicht.setWindowTitle("S7 – Rechtwinklige Verbindung (Formen verschieben)")
    ansicht.resize(560, 360)
    ansicht.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
