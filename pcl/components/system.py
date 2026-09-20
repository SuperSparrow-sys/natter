"""System-Komponenten: Timer.

Siehe README.md, Abschnitt 5.2 (Palette „System“). Ein `Timer`
zeigt im laufenden Programm nichts an - er tickt nur. Im Designer muss
man ihn trotzdem anfassen können, um im Objektinspektor sein Intervall
einzustellen. Lazarus löst das seit jeher mit einem kleinen Symbol auf
dem Formular, das im fertigen Programm verschwindet, und genau so macht
Natter es auch: `Timer` ist eine gewöhnliche `Control` mit
`nur_im_designer = True`.

Dass er damit im Designer liegt, ist kein Beiwerk (Nutzer-Hinweis
: „der Timer muss als Komponente auch mit rein, der ist
wichtig"). Vorher musste er im Quelltext erzeugt werden - eine
Sonderregel, die man erst kennen muss:

 self.t_ampel = Timer(self) # geht weiterhin
 self.t_ampel.interval = 2000
 self.t_ampel.on_timer = self.t_ampel_timer

Vorbild ist `TTimer` aus Lazarus (`t_hunger: TTimer` mit
`OnTimer = t_hungerTimer`, im Quelltext über `t_hunger.enabled := true`
geschaltet) - deshalb dieselben beiden Eigenschaften
`enabled`/`interval` und dasselbe eine Ereignis.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from pcl.control import Control
from pcl.properties import Event, Prop


class _ZeitgeberSymbol(QWidget):
    """Das Symbol, das ein `Timer` im Designer zeigt: eine kleine Uhr.

    Gezeichnet statt als Bilddatei beigelegt - so gibt es nichts, was
    beim Paketieren vergessen werden kann, und die Linienstärke passt
    sich der Größe an.
    """

    RAHMEN = QColor("#6f7d8c")
    ZEIGER = QColor("#2f7fd0")
    GRUND = QColor("#eef3f8")

    def paintEvent(self, event: Any) -> None:  # noqa: N802 (Qt-Konvention)
        maler = QPainter(self)
        maler.setRenderHint(QPainter.RenderHint.Antialiasing)

        rand = 2.0
        flaeche = QRectF(self.rect()).adjusted(rand, rand, -rand, -rand)
        seite = min(flaeche.width(), flaeche.height())
        kreis = QRectF(flaeche.left(), flaeche.top(), seite, seite)
        kreis.moveCenter(flaeche.center())

        maler.setBrush(self.GRUND)
        maler.setPen(QPen(self.RAHMEN, max(1.0, seite / 16)))
        maler.drawEllipse(kreis)

        # Stundenzeiger nach oben, Minutenzeiger nach rechts - die Uhr
        # steht auf drei, das ist als Symbol am besten zu erkennen.
        mitte = kreis.center()
        stift = QPen(self.ZEIGER, max(1.0, seite / 14))
        stift.setCapStyle(Qt.PenCapStyle.RoundCap)
        maler.setPen(stift)
        maler.drawLine(mitte.x(), mitte.y(), mitte.x(), mitte.y() - seite * 0.28)
        maler.drawLine(mitte.x(), mitte.y(), mitte.x() + seite * 0.22, mitte.y())
        maler.end()


class Timer(Control):
    """Zeitgeber, der in festem Abstand `on_timer` auslöst. Qt-Basis:
    `QTimer`.

    Wie `TTimer` in Lazarus läuft ein frisch erzeugter `Timer` sofort
    (`enabled` ist standardmäßig wahr) und wird über `enabled` an- und
    abgeschaltet - ein `start()`/`stop()` gibt es bewusst nicht, damit es
    nur einen Schalter gibt.

    Im laufenden Programm ist er unsichtbar (`nur_im_designer`); auf
    dem Formular im Designer zeigt er eine kleine Uhr, die man
    anklicken und im Objektinspektor einstellen kann.
    """

    nur_im_designer = True

    enabled = Prop(bool, True, kategorie="Verhalten", doc="Legt fest, ob der Zeitgeber läuft")
    interval = Prop(
        int,
        1000,
        kategorie="Verhalten",
        doc="Abstand zwischen zwei Auslösungen in Millisekunden",
    )

    on_timer = Event(doc="Wird nach jeweils `interval` Millisekunden ausgelöst")

    def __init__(self, parent: Any = None) -> None:
        # Der QTimer muss vor `super().__init__` stehen: die Basis
        # wendet die Eigenschaften an, und `_bei_prop_aenderung` greift
        # auf ihn zu.
        self._qtimer = QTimer()
        self._qtimer.setInterval(self.interval)
        self._qtimer.timeout.connect(self._bei_zeitpunkt)
        super().__init__(parent)
        if self.enabled:
            self._qtimer.start()

    def _qwidget_erzeugen(self, eltern_widget: QWidget | None) -> QWidget:
        return _ZeitgeberSymbol(eltern_widget)

    def _bei_zeitpunkt(self) -> None:
        if self.on_timer is not None:
            self.on_timer(self)

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "interval":
            # setInterval wirkt auch bei laufendem QTimer sofort; ein
            # Neustart wäre nicht nötig und würde die bereits verstrichene
            # Zeit verwerfen.
            self._qtimer.setInterval(wert)
        elif name == "enabled":
            if wert:
                self._qtimer.start()
            else:
                self._qtimer.stop()
