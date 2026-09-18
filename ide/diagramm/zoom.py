"""Zoom, Rollen und Ansicht verschieben – gemeinsam für alle drei
Zeichenflächen des Diagramm-Editors (M9, Teilschritt 2b und 6).

Bis hierher konnte nur das Klassendiagramm zoomen; Struktogramm und
Entscheidungstabelle standen fest auf 100 %. Gerade dort fehlt es aber
am ehesten: ein Struktogramm mit verschachtelten Schleifen wird schnell
länger als das Fenster, und eine Entscheidungstabelle breiter.

Statt die Rechnung dreimal zu schreiben, steckt sie hier in einer
Mischklasse. Jede Fläche muss dafür nur zwei Dinge mitbringen:

* `_inhalt_in_diagrammkoordinaten()` – wie groß der Inhalt **ohne**
  Zoom ist, in Diagrammkoordinaten
* ein eigenes Signal `zoom_geaendert = Signal(float)`

Das Signal bleibt bewusst in der jeweiligen Klasse: PySide6 meldet ein
`Signal` nur an, wenn es in einer Klasse steht, die am Ende wirklich
von `QObject` erbt – in einer reinen Mischklasse ginge es verloren.

Der Grundsatz dahinter ist derselbe wie im Klassendiagramm: **alles
rechnet in Diagrammkoordinaten, nur das Zeichnen skaliert.** Sonst
müsste jede einzelne Trefferprüfung den Zoom kennen, und genau dort
schleichen sich die Fehler ein.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QScrollArea

#: Grenzen der Zoomstufe. Weiter heraus wäre nichts mehr zu erkennen,
#: weiter hinein verliert man die Übersicht vollständig.
MIN_ZOOM = 0.25
MAX_ZOOM = 4.0


class ZoomMischung:
    """Zoomen, rollen, Ansicht verschieben. Siehe Modul-Docstring."""

    #: Vorgabe, damit die Fläche auch vor dem ersten `zoom_setzen()`
    #: rechnen kann.
    zoom = 1.0

    # -- Zoomstufe -------------------------------------------------------

    def zoom_setzen(self, wert: float) -> None:
        """Zoomstufe setzen (Abschnitt 13.2/13.3). Begrenzt, damit sich
        niemand aus Versehen so weit heraus- oder hineinzoomt, dass
        nichts mehr zu erkennen ist."""
        neu = max(MIN_ZOOM, min(MAX_ZOOM, wert))
        if abs(neu - self.zoom) < 0.001:
            return
        self.zoom = neu
        self.inhaltsgroesse_anpassen()
        self.zoom_geaendert.emit(neu)
        self.update()

    def zoom_aendern(self, faktor: float) -> None:
        self.zoom_setzen(self.zoom * faktor)

    def alles_anzeigen(self, breite: float, hoehe: float) -> None:
        """„Alles anzeigen“ (Strg+0): so weit herauszoomen, dass der
        ganze Inhalt in `breite`×`hoehe` passt. Bei leerem Inhalt
        passiert nichts, damit die Ansicht nicht ins Leere springt."""
        inhalt_breite, inhalt_hoehe = self._inhalt_in_diagrammkoordinaten()
        if inhalt_breite <= 0 or inhalt_hoehe <= 0:
            return
        self.zoom_setzen(min(breite / inhalt_breite, hoehe / inhalt_hoehe))

    # -- Größe der Fläche ------------------------------------------------

    def inhaltsgroesse(self) -> tuple[int, int]:
        """Wie groß die Fläche mindestens sein muss – in Bildschirm-
        pixeln, also mit dem Zoom multipliziert. Ohne das bliebe beim
        Hineinzoomen der untere Teil unerreichbar."""
        breite, hoehe = self._inhalt_in_diagrammkoordinaten()
        return int(breite * self.zoom), int(hoehe * self.zoom)

    def inhaltsgroesse_anpassen(self) -> None:
        """Setzt die Mindestgröße neu. Zusammen mit einer `QScrollArea`
        (`setWidgetResizable(True)`) heißt das: passt der Inhalt ins
        Fenster, füllt die Fläche es aus; passt er nicht, erscheinen
        Rollbalken."""
        self.setMinimumSize(*self.inhaltsgroesse())

    # -- Maus ------------------------------------------------------------

    def _diagrammpunkt(self, ereignis) -> QPoint:
        """Mausposition in Diagrammkoordinaten."""
        punkt = ereignis.position()
        return QPoint(int(punkt.x() / self.zoom), int(punkt.y() / self.zoom))

    def wheelEvent(self, ereignis) -> None:
        """Strg+Mausrad zoomt, ohne Strg rollt der Rollbereich wie
        gewohnt weiter."""
        if ereignis.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.zoom_aendern(1.1 if ereignis.angleDelta().y() > 0 else 1 / 1.1)
            ereignis.accept()
            return
        ereignis.ignore()

    # -- Ansicht verschieben ---------------------------------------------

    def rollbereich(self) -> QScrollArea | None:
        """Der `QScrollArea`, in dem die Fläche steckt. Sie hängt dort im
        Viewport, der eigentliche Rollbereich ist also der
        Großelternteil."""
        eltern = self.parentWidget()
        while eltern is not None:
            if isinstance(eltern, QScrollArea):
                return eltern
            eltern = eltern.parentWidget()
        return None

    def ansicht_verschieben(self, dx: int, dy: int) -> None:
        """Verschiebt den sichtbaren Ausschnitt (Leertaste+Ziehen bzw.
        mittlere Maustaste, Abschnitt 13.3)."""
        rollbereich = self.rollbereich()
        if rollbereich is None:
            return
        waagerecht = rollbereich.horizontalScrollBar()
        senkrecht = rollbereich.verticalScrollBar()
        waagerecht.setValue(waagerecht.value() - dx)
        senkrecht.setValue(senkrecht.value() - dy)
