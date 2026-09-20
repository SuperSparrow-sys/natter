"""Lineale und Hilfslinien für den Diagramm-Editor (M9, Teilschritt 2b;
umgesetzt in M15, Abschnitt 5).

Die drei letzten ausgegrauten Einträge im Menü „Ansicht" waren
„Lineale", „Hilfslinien" und „Minimap". Zoom, Raster, Seitenränder und
Layout-Hinweise waren längst aktiv.

Die Lineale liegen neben der Zeichenfläche, nicht darauf. Sie in den
`paintEvent` der Fläche zu malen wäre weniger Arbeit gewesen, hätte aber
das Diagramm unter sich begraben: die obersten und linkesten Zentimeter
des Blatts lägen dann hinter dem Lineal. Deshalb steckt die Fläche jetzt
in einem Raster aus Ecke, oberem Lineal, linkem Lineal und Rollbereich -
so, wie es jedes Zeichenprogramm macht.

Gezählt wird in Millimetern, passend zum Seitenformat: ein
Diagramm-Editor, der in Pixeln misst, hilft beim Drucken nicht weiter.
Die Umrechnung kommt aus `seite.py` (96 dpi), damit Lineal, Seitenrand
und Druck dieselbe Vorstellung von einem Zentimeter haben.

Eine Hilfslinie zieht man aus dem Lineal heraus und legt sie ab, wo
sie stehen soll. Sie wird mit der `.pdiag` gespeichert (Feld `guides`)
und rastet beim Verschieben von Formen ein - sonst wäre sie nur eine
Linie zum Ansehen.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QRect, Qt, Signal
from PySide6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QWidget

from ide.diagramm.seite import DPI

#: Breite des Linealstreifens in Pixeln. Genug für eine zweistellige
#: Zahl in 7 pt, nicht mehr - der Platz fehlt sonst dem Diagramm.
LINEALBREITE = 18

#: Abstand der beschrifteten Striche in Millimetern. Zwischenstriche
#: stehen bei jedem Zentimeter.
_BESCHRIFTUNG_MM = 10.0
_ZWISCHENSTRICH_MM = 5.0

#: Wie weit ein Klick von einer Hilfslinie entfernt sein darf, um sie zu
#: fassen (in Pixeln auf dem Bildschirm).
FANGABSTAND = 4


def mm_in_pixel(millimeter: float) -> float:
    return millimeter / 25.4 * DPI


def pixel_in_mm(pixel: float) -> float:
    return pixel * 25.4 / DPI


class Lineal(QWidget):
    """Ein Lineal am oberen oder linken Rand der Zeichenfläche.

    `hilfslinie_gezogen` meldet eine neue Hilfslinie, sobald jemand aus
    dem Lineal heraus auf die Fläche zieht und loslässt - mit der
    Position in Diagrammkoordinaten, nicht in Bildschirmpixeln.
    """

    hilfslinie_gezogen = Signal(float)

    def __init__(self, waagerecht: bool, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._waagerecht = waagerecht
        self.zoom = 1.0
        #: Wie weit die Fläche gerollt ist, in Bildschirmpixeln.
        self.versatz = 0
        #: Wo der Mauszeiger steht, in Bildschirmpixeln - oder `None`.
        self.marke: int | None = None
        self._zieht = False
        if waagerecht:
            self.setFixedHeight(LINEALBREITE)
        else:
            self.setFixedWidth(LINEALBREITE)
        self.setMouseTracking(True)
        self.setCursor(
            Qt.CursorShape.SplitHCursor if waagerecht else Qt.CursorShape.SplitVCursor
        )

    # -- Anzeige --------------------------------------------------------

    def stand_setzen(self, zoom: float, versatz: int) -> None:
        self.zoom = zoom
        self.versatz = versatz
        self.update()

    def marke_setzen(self, stelle: int | None) -> None:
        """Die Marke, die der Maus folgt. `None` blendet sie aus."""
        if self.marke != stelle:
            self.marke = stelle
            self.update()

    def paintEvent(self, ereignis: QPaintEvent) -> None:  # noqa: N802
        maler = QPainter(self)
        maler.fillRect(self.rect(), QColor("#f3f5f6"))
        maler.setPen(QColor("#c4ccd0"))
        if self._waagerecht:
            maler.drawLine(0, LINEALBREITE - 1, self.width(), LINEALBREITE - 1)
        else:
            maler.drawLine(LINEALBREITE - 1, 0, LINEALBREITE - 1, self.height())

        schrift = QFont(self.font())
        schrift.setPointSize(7)
        maler.setFont(schrift)

        laenge = self.width() if self._waagerecht else self.height()

        # Bei starker Verkleinerung stünden die Halbzentimeter-Striche
        # aufeinander - dann bleiben nur die beschrifteten stehen.
        schritt_mm = _ZWISCHENSTRICH_MM
        if mm_in_pixel(schritt_mm) * self.zoom < 4:
            schritt_mm = _BESCHRIFTUNG_MM

        nummer = 0
        while True:
            diagramm_mm = nummer * schritt_mm
            stelle = round(mm_in_pixel(diagramm_mm) * self.zoom) - self.versatz
            if stelle > laenge:
                break
            if stelle >= 0:
                beschriftet = abs(diagramm_mm % _BESCHRIFTUNG_MM) < 0.01
                self._strich_zeichnen(maler, stelle, diagramm_mm, beschriftet)
            nummer += 1
            if nummer > 10000:  # Sicherheitsnetz gegen eine Endlosschleife
                break

        if self.marke is not None:
            maler.setPen(QColor("#c42b1c"))
            if self._waagerecht:
                maler.drawLine(self.marke, 2, self.marke, LINEALBREITE - 2)
            else:
                maler.drawLine(2, self.marke, LINEALBREITE - 2, self.marke)

    def _strich_zeichnen(
        self, maler: QPainter, stelle: int, millimeter: float, beschriftet: bool
    ) -> None:
        maler.setPen(QColor("#7b8f9a"))
        laenge = LINEALBREITE - 6 if beschriftet else 4
        if self._waagerecht:
            maler.drawLine(stelle, LINEALBREITE - laenge, stelle, LINEALBREITE - 2)
        else:
            maler.drawLine(LINEALBREITE - laenge, stelle, LINEALBREITE - 2, stelle)

        if not beschriftet:
            return
        maler.setPen(QColor("#37474f"))
        text = f"{int(millimeter / 10)}"
        if self._waagerecht:
            maler.drawText(QRect(stelle + 2, 0, 24, 10), Qt.AlignmentFlag.AlignLeft, text)
        else:
            # Senkrecht gedreht wäre die Zahl bei 7 pt kaum zu lesen -
            # deshalb aufrecht, direkt neben dem Strich.
            maler.drawText(QRect(1, stelle + 1, LINEALBREITE - 4, 10),
                           Qt.AlignmentFlag.AlignLeft, text)

    # -- Hilfslinie herausziehen ----------------------------------------

    def mousePressEvent(self, ereignis: QMouseEvent) -> None:  # noqa: N802
        if ereignis.button() == Qt.MouseButton.LeftButton:
            self._zieht = True

    def mouseMoveEvent(self, ereignis: QMouseEvent) -> None:  # noqa: N802
        stelle = ereignis.position()
        self.marke_setzen(int(stelle.x() if self._waagerecht else stelle.y()))

    def mouseReleaseEvent(self, ereignis: QMouseEvent) -> None:  # noqa: N802
        if not self._zieht:
            return
        self._zieht = False
        stelle = ereignis.position()
        bildschirm = stelle.x() if self._waagerecht else stelle.y()
        diagramm = (bildschirm + self.versatz) / max(self.zoom, 0.01)
        if diagramm >= 0:
            self.hilfslinie_gezogen.emit(float(diagramm))

    def leaveEvent(self, ereignis: Any) -> None:  # noqa: N802
        self.marke_setzen(None)


def hilfslinien_lesen(daten: dict[str, Any]) -> list[dict[str, Any]]:
    """Die Hilfslinien einer `.pdiag`, verträglich mit Dateien ohne.

    Eine `.pdiag` aus der Zeit vor M15 hat kein `guides` - die soll sich
    weiter öffnen lassen, ohne dass jemand die Datei anfassen muss."""
    roh = daten.get("guides")
    if not isinstance(roh, list):
        return []
    linien = []
    for eintrag in roh:
        if not isinstance(eintrag, dict):
            continue
        richtung = eintrag.get("orientation")
        stelle = eintrag.get("pos")
        if richtung in ("h", "v") and isinstance(stelle, int | float):
            linien.append({"orientation": richtung, "pos": float(stelle)})
    return linien


def hilfslinien_zeichnen(
    maler: QPainter, linien: list[dict[str, Any]], breite: float, hoehe: float
) -> None:
    """Zeichnet die Hilfslinien in Diagrammkoordinaten.

    Gestrichelt und in einem Grün, das im Diagramm sonst nicht vorkommt -
    eine Hilfslinie soll als Hilfe erkennbar sein und nicht als Teil der
    Zeichnung."""
    vorher = maler.pen()
    feder = QPen(QColor("#1e8e3e"))
    feder.setStyle(Qt.PenStyle.DashLine)
    maler.setPen(feder)
    for linie in linien:
        stelle = int(linie["pos"])
        if linie["orientation"] == "v":
            maler.drawLine(stelle, 0, stelle, int(hoehe))
        else:
            maler.drawLine(0, stelle, int(breite), stelle)
    maler.setPen(vorher)
