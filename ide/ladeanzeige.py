"""Das Bild, das während des Startens zu sehen ist.

Natter braucht vom Doppelklick bis zum fertigen Fenster gut eine
Sekunde: der Starter muss eine Python hochfahren, diese Python lädt Qt
und die Module der IDE, und erst dann entsteht das Hauptfenster. Ein
Teil davon ließ sich abkürzen (siehe `ide/schema.py` und den Kopf von
`ide/designer/canvas.py`), der Rest nicht - eine Oberfläche dieser
Größe kommt nicht ohne Qt aus.

Was bleibt, ist die Wartezeit sichtbar zu machen. Ohne Rückmeldung
klickt man ein zweites Mal, weil nichts passiert; mit Rückmeldung
wartet man. Deshalb erscheint sofort ein kleines Bild mit dem Namen,
der Versionsnummer und einer Zeile, die sagt, woran gerade gearbeitet
wird.

Bewusst ohne Bilddatei und ohne eigenen Faden: gezeichnet wird auf ein
`QPixmap`, das ein paar Rechtecke und zwei Zeilen Text trägt. Alles
andere wäre langsamer als das, was es überbrücken soll.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QSplashScreen

#: Größe des Bildes in Punkten. Klein genug, um nicht im Weg zu stehen,
#: groß genug, dass der Name lesbar ist.
_BREITE = 420
_HOEHE = 170

_HINTERGRUND = "#ffffff"
_RAHMEN = "#c8c8c8"
_NAME = "#1a1a1a"
_NEBENTEXT = "#5a5a5a"
_BALKEN = "#0a64c8"


def _bild(version: str) -> QPixmap:
    pixmap = QPixmap(_BREITE, _HOEHE)
    pixmap.fill(QColor(_HINTERGRUND))

    maler = QPainter(pixmap)
    maler.setPen(QColor(_RAHMEN))
    maler.drawRect(0, 0, _BREITE - 1, _HOEHE - 1)

    maler.setPen(QColor(_NAME))
    schrift = QFont("Segoe UI", 28)
    schrift.setBold(True)
    maler.setFont(schrift)
    maler.drawText(32, 72, "Natter")

    maler.setPen(QColor(_NEBENTEXT))
    maler.setFont(QFont("Segoe UI", 10))
    maler.drawText(34, 98, f"Version {version}")

    # Ein ruhender Balken am unteren Rand. Er füllt sich nicht - eine
    # Anzeige, die einen Fortschritt behauptet, den niemand kennt, ist
    # schlimmer als keine.
    maler.fillRect(0, _HOEHE - 4, _BREITE, 4, QColor(_BALKEN))
    maler.end()
    return pixmap


class Ladeanzeige(QSplashScreen):
    """Das Startbild samt der Zeile, die den Stand meldet."""

    def __init__(self, version: str) -> None:
        super().__init__(_bild(version))
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, False)

    def melden(self, text: str) -> None:
        """Schreibt `text` unten in das Bild und zeichnet sofort neu.

        `processEvents()` ist hier richtig und nicht der Notnagel, der
        er sonst wäre: es gibt noch kein Fenster, das jemand bedienen
        könnte, und ohne diese Runde bliebe das Bild leer, bis alles
        fertig ist - also genau dann, wenn es niemand mehr braucht.
        """
        self.showMessage(
            f"   {text}",
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom,
            QColor(_NEBENTEXT),
        )
        QApplication.processEvents()
