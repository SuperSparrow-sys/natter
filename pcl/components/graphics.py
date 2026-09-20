"""Zeichenfläche: `PaintBox` mit ihrer `Canvas` (Abschnitt 5.2).

Bis M15 konnte ein Natter-Programm keinen einzigen Punkt setzen. Es gab
`Shape` – fertige Formen, die man im Designer hinlegt – aber nichts, um
mit Koordinaten zu zeichnen. Genau das kommt im Unterricht vor.

    def b_zeichnen_click(self, sender):
        stift = self.pb_bild.canvas
        stift.pen.color = "#c42b1c"
        stift.move_to(10, 10)
        stift.line_to(120, 80)
        stift.brush.color = "#f2b134"
        stift.ellipse(30, 30, 90, 90)
        stift.text_out(10, 110, "Hallo")

Gezeichnet wird in ein `QPixmap`, nicht im `paintEvent`. Das ist der
ganze Trick und der Grund, warum diese Klasse überhaupt eigenen Zustand
hält: Qt fordert ein Widget zum Neuzeichnen auf, sobald es verdeckt war,
in der Größe geändert oder gescrollt wurde. Wer dabei nur im
`paintEvent` malt, verliert alles Gezeichnete beim ersten Fenster, das
darüberfährt – ein Fehler, der Lernende ratlos macht, weil ihr Code
richtig aussieht und trotzdem nichts stehen bleibt. Hier liegt das Bild
im Pixmap, und das `paintEvent` legt es nur noch hin.

Ohne Kantenglättung. Eine gezeichnete Linie hat exakt die Farbe,
die im Stift steht – sonst lieferte `canvas.pixels[x, y]` an jeder Kante
eine Mischfarbe, und „ist dieser Punkt rot?" wäre nicht zu beantworten.
Lazarus' `TCanvas` glättet ebenfalls nicht.

Eigene `Pen`- und `Brush`-Klassen, obwohl `Shape` in
`additional.py` schon einen `Brush` hat. Der Plan in
`docs/arbeitspakete/M15.md` sah vor, ihn wiederzuverwenden. Beim Bauen
sprach mehr dagegen als dafür: `Shape.brush` kennt nur `color`, eine
`Canvas` braucht zusätzlich `style` (gefüllt oder nur Umriss), und ein
`Shape` würde dieses `style` ignorieren – eine Eigenschaft, die je nach
Besitzer wirkt oder nicht, ist schlimmer als fünfzehn Zeilen doppelt.
`Shape` hat für denselben Zweck seit M1 sein eigenes `transparent`.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget

from pcl.control import Control
from pcl.errors import NatterPropertyError
from pcl.properties import Event, Prop, typ_beschreibung

#: Füllarten einer `Brush` (wie `TBrushStyle` in Lazarus, auf die zwei
#: im Unterricht gebrauchten eingedampft).
FUELLARTEN = ("solid", "clear")

_STANDARD_HINTERGRUND = "#ffffff"
_STANDARD_STIFT = "#000000"
_STANDARD_FUELLUNG = "#ffffff"


def _farbe_pruefen(wer: str, wert: Any) -> str:
    if not isinstance(wert, str):
        raise NatterPropertyError(
            f"{wer} erwartet {typ_beschreibung(str)}, "
            f"erhalten wurde {typ_beschreibung(type(wert))}."
        )
    if not QColor(wert).isValid():
        raise NatterPropertyError(
            f"{wer}: {wert!r} ist keine Farbe. Erwartet wird #RRGGBB, also "
            'zum Beispiel "#c42b1c".'
        )
    return wert


class Pen:
    """Der Stift einer `Canvas` (wie `TPen` in Lazarus): Farbe und
    Breite der Linien, die `line_to`, `rectangle` und `ellipse`
    ziehen."""

    def __init__(self) -> None:
        self._farbe = _STANDARD_STIFT
        self._breite = 1

    @property
    def color(self) -> str:
        """Linienfarbe als ``#RRGGBB``."""
        return self._farbe

    @color.setter
    def color(self, wert: str) -> None:
        self._farbe = _farbe_pruefen("Canvas.pen.color", wert)

    @property
    def width(self) -> int:
        """Linienbreite in Pixeln, mindestens 1."""
        return self._breite

    @width.setter
    def width(self, wert: int) -> None:
        if not isinstance(wert, int) or isinstance(wert, bool):
            raise NatterPropertyError(
                f"Canvas.pen.width erwartet {typ_beschreibung(int)}, "
                f"erhalten wurde {typ_beschreibung(type(wert))}."
            )
        if wert < 1:
            raise NatterPropertyError(
                f"Canvas.pen.width erwartet eine Breite ab 1, erhalten wurde {wert}."
            )
        self._breite = wert


class Brush:
    """Die Füllung einer `Canvas` (wie `TBrush` in Lazarus): womit
    `rectangle` und `ellipse` innen gefüllt werden.

    ``style = "clear"`` zeichnet nur den Umriss – dasselbe, was
    ``Brush.Style := bsClear`` in Lazarus tut."""

    def __init__(self) -> None:
        self._farbe = _STANDARD_FUELLUNG
        self._art = "solid"

    @property
    def color(self) -> str:
        """Füllfarbe als ``#RRGGBB``."""
        return self._farbe

    @color.setter
    def color(self, wert: str) -> None:
        self._farbe = _farbe_pruefen("Canvas.brush.color", wert)

    @property
    def style(self) -> str:
        """``"solid"`` füllt, ``"clear"`` lässt nur den Umriss stehen."""
        return self._art

    @style.setter
    def style(self, wert: str) -> None:
        if wert not in FUELLARTEN:
            raise NatterPropertyError(
                f"Canvas.brush.style erwartet {' oder '.join(repr(f) for f in FUELLARTEN)}, "
                f"erhalten wurde {wert!r}."
            )
        self._art = wert


class Pixels:
    """Einzelne Bildpunkte einer `Canvas`, Zugriff über
    ``self.pb_bild.canvas.pixels[x, y]`` (wie ``Canvas.Pixels[x, y]`` in
    Lazarus). Lesen liefert die Farbe als ``#RRGGBB``, Zuweisen setzt
    den Punkt."""

    def __init__(self, besitzer: Canvas) -> None:
        self._besitzer = besitzer

    def __getitem__(self, stelle: tuple[int, int]) -> str:
        x, y = self._stelle_pruefen(stelle)
        bild = self._besitzer._pixmap.toImage()
        if not (0 <= x < bild.width() and 0 <= y < bild.height()):
            raise NatterPropertyError(
                f"Canvas.pixels[{x}, {y}] liegt außerhalb der Zeichenfläche "
                f"({bild.width()} x {bild.height()} Pixel)."
            )
        return bild.pixelColor(x, y).name()

    def __setitem__(self, stelle: tuple[int, int], farbe: str) -> None:
        x, y = self._stelle_pruefen(stelle)
        _farbe_pruefen("Canvas.pixels", farbe)
        maler = self._besitzer._maler()
        maler.setPen(QColor(farbe))
        maler.drawPoint(x, y)
        maler.end()
        self._besitzer._fertig()

    @staticmethod
    def _stelle_pruefen(stelle: Any) -> tuple[int, int]:
        if not isinstance(stelle, tuple) or len(stelle) != 2:
            raise NatterPropertyError(
                "Canvas.pixels erwartet zwei Zahlen: pixels[x, y]."
            )
        return int(stelle[0]), int(stelle[1])


class Canvas:
    """Die Zeichenfläche einer `PaintBox` (wie `TCanvas` in Lazarus).

    Der Ursprung liegt links oben, `x` läuft nach rechts, `y` nach
    unten – wie in Lazarus und wie überall in der Bildschirmgrafik.
    """

    def __init__(self, besitzer: PaintBox) -> None:
        self._besitzer = besitzer
        self._pixmap = QPixmap(1, 1)
        self._pixmap.fill(QColor(_STANDARD_HINTERGRUND))
        self._pen = Pen()
        self._brush = Brush()
        self._stift_x = 0
        self._stift_y = 0

    @property
    def pen(self) -> Pen:
        """Der Stift: ``canvas.pen.color``, ``canvas.pen.width``."""
        return self._pen

    @property
    def brush(self) -> Brush:
        """Die Füllung: ``canvas.brush.color``, ``canvas.brush.style``."""
        return self._brush

    @property
    def pixels(self) -> Pixels:
        """Einzelne Bildpunkte: ``canvas.pixels[x, y]``."""
        return Pixels(self)

    @property
    def width(self) -> int:
        """Breite der Zeichenfläche in Pixeln."""
        return self._pixmap.width()

    @property
    def height(self) -> int:
        """Höhe der Zeichenfläche in Pixeln."""
        return self._pixmap.height()

    # -- Zeichnen ------------------------------------------------------

    def move_to(self, x: int, y: int) -> None:
        """Setzt den Stift auf ``(x, y)``, ohne zu zeichnen."""
        self._stift_x, self._stift_y = int(x), int(y)

    def line_to(self, x: int, y: int) -> None:
        """Zieht eine Linie von der aktuellen Stiftstelle nach
        ``(x, y)`` und setzt den Stift dorthin."""
        ziel_x, ziel_y = int(x), int(y)
        maler = self._maler()
        maler.setPen(self._qt_stift())
        maler.drawLine(self._stift_x, self._stift_y, ziel_x, ziel_y)
        maler.end()
        self._stift_x, self._stift_y = ziel_x, ziel_y
        self._fertig()

    def line(self, x1: int, y1: int, x2: int, y2: int) -> None:
        """Zieht eine Linie von ``(x1, y1)`` nach ``(x2, y2)`` – die
        Kurzform für ``move_to`` gefolgt von ``line_to``."""
        self.move_to(x1, y1)
        self.line_to(x2, y2)

    def rectangle(self, x1: int, y1: int, x2: int, y2: int) -> None:
        """Zeichnet ein Rechteck von der Ecke ``(x1, y1)`` zur Ecke
        ``(x2, y2)``: Rand in `pen`, Fläche in `brush`."""
        self._form_zeichnen("rect", x1, y1, x2, y2)

    def ellipse(self, x1: int, y1: int, x2: int, y2: int) -> None:
        """Zeichnet eine Ellipse in das Rechteck ``(x1, y1)`` bis
        ``(x2, y2)``. Ein Kreis ist eine Ellipse in einem Quadrat."""
        self._form_zeichnen("ellipse", x1, y1, x2, y2)

    def text_out(self, x: int, y: int, text: str) -> None:
        """Schreibt `text` an die Stelle ``(x, y)``. ``(x, y)`` ist die
        linke obere Ecke des Textes – in Lazarus ebenso, während Qt
        von sich aus die Schriftlinie meint."""
        if not isinstance(text, str):
            raise NatterPropertyError(
                f"Canvas.text_out erwartet {typ_beschreibung(str)}, "
                f"erhalten wurde {typ_beschreibung(type(text))}."
            )
        maler = self._maler()
        maler.setPen(QColor(self._pen.color))
        maler.setFont(self._besitzer._qwidget.font())
        hoehe = maler.fontMetrics().ascent()
        maler.drawText(QPoint(int(x), int(y) + hoehe), text)
        maler.end()
        self._fertig()

    def fill_rect(self, x1: int, y1: int, x2: int, y2: int) -> None:
        """Füllt ein Rechteck vollständig mit `brush.color`, ohne
        Rand (wie `FillRect` in Lazarus)."""
        maler = self._maler()
        maler.fillRect(*self._rechteck(x1, y1, x2, y2), QColor(self._brush.color))
        maler.end()
        self._fertig()

    def clear(self) -> None:
        """Löscht die ganze Zeichenfläche – sie wird wieder weiß."""
        self._pixmap.fill(QColor(_STANDARD_HINTERGRUND))
        self._stift_x = self._stift_y = 0
        self._fertig()

    # -- Innenleben ----------------------------------------------------

    def _maler(self) -> QPainter:
        # Ohne Kantenglättung, mit Absicht. Qt glättet von sich aus
        # nicht, Lazarus' `TCanvas` auch nicht - und hier hängt mehr
        # daran als das Aussehen: mit Glättung liegt an der Kante einer
        # roten Linie nicht Rot, sondern eine Mischfarbe. `pixels[x, y]`
        # gäbe dann `#e1958d` zurück, wo eine Schülerin `#c42b1c`
        # erwartet, und ein Vergleich „ist der Punkt rot?" schlüge fehl,
        # obwohl er aussieht, als müsste er stimmen.
        return QPainter(self._pixmap)

    def _qt_stift(self) -> QPen:
        stift = QPen(QColor(self._pen.color))
        stift.setWidth(self._pen.width)
        return stift

    @staticmethod
    def _rechteck(x1: int, y1: int, x2: int, y2: int) -> tuple[int, int, int, int]:
        """Links, oben, Breite, Höhe – auch wenn die Ecken verkehrt
        herum angegeben wurden."""
        links, rechts = sorted((int(x1), int(x2)))
        oben, unten = sorted((int(y1), int(y2)))
        return links, oben, rechts - links, unten - oben

    def _form_zeichnen(self, art: str, x1: int, y1: int, x2: int, y2: int) -> None:
        maler = self._maler()
        maler.setPen(self._qt_stift())
        if self._brush.style == "clear":
            maler.setBrush(Qt.BrushStyle.NoBrush)
        else:
            maler.setBrush(QColor(self._brush.color))
        links, oben, breite, hoehe = self._rechteck(x1, y1, x2, y2)
        if art == "ellipse":
            maler.drawEllipse(links, oben, breite, hoehe)
        else:
            maler.drawRect(links, oben, breite, hoehe)
        maler.end()
        self._fertig()

    def _fertig(self) -> None:
        self._besitzer._qwidget.update()

    def _groesse_anpassen(self, breite: int, hoehe: int) -> None:
        """Vergrößert/verkleinert die Fläche und behält den Inhalt.

        Ohne das Übertragen wäre nach jeder Größenänderung alles weg –
        auch beim Ziehen am Rand im Designer."""
        breite, hoehe = max(1, breite), max(1, hoehe)
        if (breite, hoehe) == (self._pixmap.width(), self._pixmap.height()):
            return
        neu = QPixmap(breite, hoehe)
        neu.fill(QColor(_STANDARD_HINTERGRUND))
        maler = QPainter(neu)
        maler.drawPixmap(0, 0, self._pixmap)
        maler.end()
        self._pixmap = neu


class _PaintBoxQWidget(QWidget):
    """Legt das Pixmap hin und zieht den Rahmen darum. Mehr passiert im
    `paintEvent` bewusst nicht – gezeichnet wird ins Pixmap."""

    def __init__(self, eltern_widget: QWidget, paintbox: PaintBox) -> None:
        super().__init__(eltern_widget)
        self._paintbox = paintbox

    def paintEvent(self, event: Any) -> None:  # noqa: N802 (Qt-Konvention)
        maler = QPainter(self)
        maler.drawPixmap(0, 0, self._paintbox.canvas._pixmap)
        maler.setPen(QColor(self._paintbox.border_color))
        maler.drawRect(self.rect().adjusted(0, 0, -1, -1))

    def resizeEvent(self, event: Any) -> None:  # noqa: N802 (Qt-Konvention)
        super().resizeEvent(event)
        self._paintbox._groesse_uebernehmen(self.width(), self.height())


class PaintBox(Control):
    """Freie Zeichenfläche (entspricht ``TPaintBox`` in Lazarus).
    Qt-Basis: eigenes Painting auf einem `QWidget` über ein `QPixmap`.

    Gezeichnet wird über `canvas`::

        self.pb_bild.canvas.rectangle(10, 10, 100, 60)

    Das Gezeichnete bleibt stehen – auch wenn ein anderes Fenster
    darüberfährt oder das Formular größer gezogen wird.
    """

    border_color = Prop(
        str,
        "#90a4ae",
        kategorie="Darstellung",
        doc="Farbe des Rahmens um die Zeichenfläche als #RRGGBB",
    )

    on_paint = Event(
        doc=(
            "Wird ausgelöst, wenn die Zeichenfläche neu entstanden ist – "
            "beim ersten Anzeigen und nach jeder Größenänderung"
        )
    )

    def __init__(self, parent: Control | None = None) -> None:
        self._canvas = Canvas(self)
        super().__init__(parent)
        self._canvas._groesse_anpassen(self.width, self.height)

    @property
    def canvas(self) -> Canvas:
        """Die Zeichenfläche: ``self.pb_bild.canvas.line_to(50, 50)``."""
        return self._canvas

    def clear(self) -> None:
        """Löscht die Zeichenfläche – die Kurzform für
        ``self.pb_bild.canvas.clear()``."""
        self._canvas.clear()

    def repaint(self) -> None:
        """Löst `on_paint` von Hand aus, damit sich das Bild neu
        aufbauen lässt (wie `Invalidate` in Lazarus)."""
        if self.on_paint is not None:
            self.on_paint(self)

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        return _PaintBoxQWidget(eltern_widget, self)

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "border_color":
            self._qwidget.update()
        elif name in ("width", "height"):
            # Nicht auf `resizeEvent` warten: Qt stellt das Ereignis für
            # ein noch nicht gezeigtes Widget in die Schlange, statt es
            # sofort zuzustellen. `self.pb_bild.width = 300` im
            # `form_create` hätte die Fläche sonst erst irgendwann später
            # vergrößert - und bis dahin in der alten Größe gezeichnet.
            self._groesse_uebernehmen(self.width, self.height)

    def _groesse_uebernehmen(self, breite: int, hoehe: int) -> None:
        vorher = (self._canvas.width, self._canvas.height)
        self._canvas._groesse_anpassen(breite, hoehe)
        if (self._canvas.width, self._canvas.height) != vorher:
            self.repaint()
