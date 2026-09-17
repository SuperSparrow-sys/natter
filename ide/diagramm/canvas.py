"""DiagrammCanvas: Zeichenfläche des Diagramm-Editors (Abschnitt 13.2,
13.3).

Anders als der Formular-Designer (`ide/designer/canvas.py`, ein echtes
`QWidget` je Komponente) malt der Diagramm-Editor alle Formen selbst in
einem einzigen Widget: Diagrammformen sind keine bedienbaren
Steuerelemente, es können sehr viele werden, und Verbindungen (Schritt
4) lassen sich ohnehin nur frei zeichnen.

Stand M9, Schritt 2: anzeigen, platzieren, auswählen. Verschieben/
Größe/Undo folgen in Schritt 3.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPaintEvent
from PySide6.QtWidgets import QWidget

from ide.diagramm.datei import Diagramm
from ide.diagramm.formen import form_art
from ide.diagramm.stil import stil as stil_zu_namen
from ide.diagramm.zeichnen import form_rechteck, form_zeichnen, mindesthoehe

RASTER = 8


def _am_raster(wert: float) -> int:
    return int(round(wert / RASTER) * RASTER)


def _raster_aufrunden(wert: float) -> int:
    """Wie `_am_raster`, aber nie nach unten – für Mindestgrößen, die
    sonst genau unter den nötigen Wert gerundet würden."""
    return int(-(-wert // RASTER) * RASTER)


class DiagrammCanvas(QWidget):
    auswahl_geaendert = Signal(object)  # das ausgewählte shape-dict oder None
    geaendert = Signal()

    def __init__(self, diagramm: Diagramm) -> None:
        super().__init__()
        self.diagramm = diagramm
        self.ausgewaehlte_form: dict[str, Any] | None = None
        self._platzierungs_kind: str | None = None
        self.raster_sichtbar = True
        self.setMinimumSize(640, 480)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    # -- Daten ----------------------------------------------------------

    @property
    def formen(self) -> list[dict[str, Any]]:
        return self.diagramm.daten.setdefault("shapes", [])

    def _neue_id(self) -> str:
        vorhandene = {form.get("id") for form in self.formen}
        nummer = 1
        while f"s{nummer}" in vorhandene:
            nummer += 1
        return f"s{nummer}"

    # -- Platzieren -----------------------------------------------------

    def platzierungsmodus_setzen(self, kind: str | None) -> None:
        """„Form aus der Palette anklicken, dann auf die Fläche klicken“
        (Abschnitt 13.3) – gleiches Muster wie die Komponentenpalette im
        Formular-Designer. `None` bricht ab."""
        self._platzierungs_kind = kind
        self.setCursor(
            Qt.CursorShape.CrossCursor if kind else Qt.CursorShape.ArrowCursor
        )

    def form_platzieren(self, kind: str, x: float, y: float) -> dict[str, Any]:
        """Legt eine neue Form an. `x`/`y` ist die Mitte (der Klickpunkt),
        damit die Form dort erscheint, wohin geklickt wurde – am Raster
        eingerastet (Abschnitt 13.3)."""
        art = form_art(kind)
        form: dict[str, Any] = {
            "id": self._neue_id(),
            "kind": kind,
            "x": _am_raster(x - art.breite / 2),
            "y": _am_raster(y - art.hoehe / 2),
            "w": art.breite,
            "h": art.hoehe,
            "text": dict(art.standardtext),
        }
        if kind == "abstract_class":
            form["abstract"] = True
        self.hoehe_anpassen(form)

        self.formen.append(form)
        self._auswaehlen(form)
        self.geaendert.emit()
        self.update()
        return form

    def hoehe_anpassen(self, form: dict[str, Any]) -> None:
        """Vergrößert `form`, bis ihr Text vollständig hineinpasst
        (Abschnitt 13.6). Verkleinert nie – eine von Hand größer
        gezogene Form soll groß bleiben."""
        noetig = _raster_aufrunden(mindesthoehe(form))
        if noetig > form["h"]:
            form["h"] = noetig
            self.update()

    # -- Auswahl --------------------------------------------------------

    def form_bei(self, x: float, y: float) -> dict[str, Any] | None:
        """Oberste Form an dieser Stelle (spätere Formen liegen oben)."""
        for form in reversed(self.formen):
            if form_rechteck(form).contains(x, y):
                return form
        return None

    def _auswaehlen(self, form: dict[str, Any] | None) -> None:
        if form is self.ausgewaehlte_form:
            return
        self.ausgewaehlte_form = form
        self.auswahl_geaendert.emit(form)
        self.update()

    def auswahl_aufheben(self) -> None:
        self._auswaehlen(None)

    # -- Ereignisse -----------------------------------------------------

    def mousePressEvent(self, ereignis: QMouseEvent) -> None:
        punkt: QPoint = ereignis.position().toPoint()
        if self._platzierungs_kind is not None:
            kind = self._platzierungs_kind
            # einmalig: nach dem Platzieren zurück zum Auswahlwerkzeug
            self.platzierungsmodus_setzen(None)
            self.form_platzieren(kind, punkt.x(), punkt.y())
            return
        self._auswaehlen(self.form_bei(punkt.x(), punkt.y()))

    # -- Zeichnen -------------------------------------------------------

    def paintEvent(self, ereignis: QPaintEvent) -> None:
        stil = stil_zu_namen(self.diagramm.stil)
        maler = QPainter(self)
        maler.fillRect(self.rect(), QColor(stil.hintergrund))

        if self.raster_sichtbar:
            self._raster_zeichnen(maler, stil.raster)

        for form in self.formen:
            form_zeichnen(maler, form, stil, ausgewaehlt=form is self.ausgewaehlte_form)

    def _raster_zeichnen(self, maler: QPainter, farbe: str) -> None:
        """Punktraster (Abschnitt 13.6) statt Gitternetzlinien – ruhiger
        und im dunklen Theme weniger aufdringlich."""
        maler.setPen(QColor(farbe))
        for x in range(0, self.width(), RASTER):
            for y in range(0, self.height(), RASTER):
                maler.drawPoint(x, y)
