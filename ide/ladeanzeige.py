"""Das Bild, das während des Startens zu sehen ist.

Natter braucht vom Start der Python bis zum fertigen Fenster knapp eine
Sekunde: Qt laden, die Module der IDE laden, das Hauptfenster
aufbauen. Ein Teil davon ließ sich abkürzen (siehe `ide/schema.py` und
den Kopf von `ide/designer/canvas.py`), der Rest nicht - eine
Oberfläche dieser Größe kommt nicht ohne Qt aus.

Was bleibt, ist die Wartezeit sichtbar zu machen. Ohne Rückmeldung
klickt man ein zweites Mal, weil nichts passiert.

Bewusst kein `QSplashScreen`, obwohl Qt genau dafür eine Klasse
mitbringt. Sie zu zeigen kostet auf diesem Rechner rund 1030
Millisekunden - mehr, als der ganze Start ohne sie dauert. Ein
rahmenloses `QLabel` mit demselben Bild kostet 50. Gemessen mit vier
Läufen je Variante, der erste (kalte) jeweils nicht gewertet:

    QSplashScreen zeigen    1030 ms
    QLabel zeigen             50 ms

Ein Startbild, das die Wartezeit verdreifacht, die es überbrücken
soll, wäre die schlechteste aller Lösungen gewesen.

Auch sonst so einfach wie möglich: gezeichnet wird auf ein `QPixmap`,
das ein paar Rechtecke und zwei Zeilen Text trägt, keine Bilddatei,
kein eigener Faden.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QWidget

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


class Ladeanzeige(QWidget):
    """Das Startbild samt der Zeile, die den Stand meldet."""

    def __init__(self, version: str) -> None:
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setFixedSize(_BREITE, _HOEHE)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)

        bild = QLabel(self)
        bild.setPixmap(_bild(version))
        bild.setGeometry(0, 0, _BREITE, _HOEHE)

        self._stand = QLabel(self)
        self._stand.setStyleSheet(f"color: {_NEBENTEXT}; background: transparent;")
        self._stand.setFont(QFont("Segoe UI", 9))
        self._stand.setGeometry(34, _HOEHE - 34, _BREITE - 68, 20)

        self._mittig_setzen()

    def _mittig_setzen(self) -> None:
        """Auf die Mitte des Bildschirms, auf dem der Mauszeiger steht.

        Ohne das säße das Bild in der linken oberen Ecke - dort, wo
        Windows ein Fenster ohne eigene Angabe hinlegt.
        """
        bildschirm = QApplication.screenAt(self.cursor().pos()) or QApplication.primaryScreen()
        if bildschirm is None:
            return
        flaeche = bildschirm.availableGeometry()
        self.move(
            flaeche.center().x() - _BREITE // 2,
            flaeche.center().y() - _HOEHE // 2,
        )

    def melden(self, text: str) -> None:
        """Schreibt `text` in das Bild und zeichnet sofort neu.

        `processEvents()` ist hier richtig und nicht der Notnagel, der
        er sonst wäre: es gibt noch kein Fenster, das jemand bedienen
        könnte, und ohne diese Runde bliebe das Bild leer, bis alles
        fertig ist - also genau dann, wenn es niemand mehr braucht.
        """
        self._stand.setText(text)
        QApplication.processEvents()

    def finish(self, fenster: QWidget) -> None:
        """Blendet das Bild aus, sobald `fenster` da ist.

        Heißt wie das Gegenstück von `QSplashScreen`, damit der Aufruf
        in `ide/main.py` unverändert lesbar bleibt.
        """
        self.close()
