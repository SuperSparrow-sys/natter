"""Additional-Komponenten: Shape, StringGrid, Image, SpinEdit,
FloatSpinEdit, TrackBar, ProgressBar.

Siehe README.md, Abschnitt 5.2 (Palette „Zusätzlich“). Die
Wertkomponenten (SpinEdit, FloatSpinEdit, TrackBar, ProgressBar) sind
jeweils ein dünner Mantel um ein Qt-Standardwidget: ein `Prop` je
Lazarus-Eigenschaft, `_bei_prop_aenderung` reicht die Zuweisung an das
Widget weiter, und das Signal des Widgets schreibt den Wert zurück in
den `Prop`. Dadurch wirken Code und Bedienung in beide Richtungen, ohne
dass es eine zweite Quelle für den Wert gäbe.

`TrackBar` und `ProgressBar` gehören in Lazarus in den Reiter
„Common Controls“. Einen eigenen Palettenreiter dafür gibt es in Natter
noch nicht (`ide/shell/hauptfenster.py` verbindet die Klick-Signale von
genau zwei Listen), deshalb stehen sie unter „Zusätzlich“.

MaskEdit, PaintBox und HtmlViewer standen hier bis M15 als
zurückgestellt; sie sind inzwischen gebaut und wohnen in
`pcl/components/eingaben.py`, `graphics.py` und `medien.py`.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QLabel,
    QProgressBar,
    QSlider,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from pcl.control import Control
from pcl.errors import NatterPropertyError
from pcl.properties import STANDARD_BRUSH_FARBE, Event, Prop, typ_beschreibung

_FORMEN = ("rectangle", "circle", "rounded_rectangle")
_ECKENRADIUS = 12


class Brush:
    """Aufklappbare Untereigenschaft eines `Shape`, z. B.
    ``self.s_rot.brush.color = "#e53935"`` (Abschnitt 5.0, 5.1).

    Kein `Prop`, weil sie an einem festen Attributnamen (`brush`) hängt statt
    selbst zugewiesen zu werden – nur `color` ist veränderlich.
    """

    def __init__(self, besitzer: Shape) -> None:
        self._besitzer = besitzer
        self._farbe = STANDARD_BRUSH_FARBE

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
        if self._shape.transparent:
            maler.setBrush(Qt.BrushStyle.NoBrush)
        else:
            maler.setBrush(QColor(self._shape.brush.color))
        maler.setPen(QColor(self._shape.pen_color))
        flaeche = self.rect().adjusted(0, 0, -1, -1)
        if self._shape.shape == "circle":
            maler.drawEllipse(flaeche)
        elif self._shape.shape == "rounded_rectangle":
            maler.drawRoundedRect(flaeche, _ECKENRADIUS, _ECKENRADIUS)
        else:
            maler.drawRect(flaeche)


class Shape(Control):
    """Einfache geometrische Form zum Zeichnen. Qt-Basis: eigenes Painting
    (`QPainter` auf einem `QWidget`). Wie in Lazarus sind Füllung
    (`brush.color`) und Rand (`pen_color`) unabhängig voneinander -
    Nutzer-Feedback September 2026: „Rahmen, Rahmenfarbe“ fehlte bisher,
    Rand und Füllung nutzten dieselbe Farbe."""

    shape = Prop(
        str,
        "rectangle",
        kategorie="Darstellung",
        doc=f"Form der Zeichnung: {' oder '.join(_FORMEN)}",
    )
    pen_color = Prop(
        str, "#000000", kategorie="Darstellung", doc="Randfarbe als #RRGGBB (wie Lazarus Pen.Color)"
    )
    transparent = Prop(
        bool,
        False,
        kategorie="Darstellung",
        doc="Wenn wahr, keine Füllung - nur der Rand (wie Lazarus Brush.Style=bsClear)",
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
        if name in ("shape", "pen_color", "transparent"):
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
        # `on_edit_cell` meint die Änderung durch den Benutzer. Was das
        # Programm selbst hineinschreibt, ist keine - sonst löste schon
        # das Füllen der Tabelle hundert Ereignisse aus.
        self._besitzer._schreibt_selbst = True
        try:
            element = widget.item(zeile, spalte)
            if element is None:
                element = QTableWidgetItem()
                widget.setItem(zeile, spalte, element)
            element.setText(wert)
        finally:
            self._besitzer._schreibt_selbst = False


class StringGrid(Control):
    """Tabelle aus Text-Zellen. Qt-Basis: `QTableWidget`.

    Die beiden Ereignisse entsprechen `OnSelectCell` und
    `OnEditingDone` in Lazarus. Beide bekommen `spalte` und `zeile`
    mit - in dieser Reihenfolge, wie Lazarus' `(ACol, ARow)` und wie
    `cells[spalte, zeile]` -, `on_edit_cell` zusätzlich den neuen Text.
    """

    row_count = Prop(int, 5, kategorie="Daten", doc="Anzahl der Zeilen")
    col_count = Prop(int, 5, kategorie="Daten", doc="Anzahl der Spalten")

    on_select_cell = Event(doc="Wird ausgelöst, wenn eine andere Zelle ausgewählt wird")
    on_edit_cell = Event(doc="Wird ausgelöst, nachdem eine Zelle geändert wurde")

    #: Ein Doppelklick im Designer meint die Auswahl, nicht die
    #: Änderung - wie `OnSelectCell` in Lazarus.
    standard_ereignis = "on_select_cell"

    def __init__(self, parent: Control) -> None:
        self._cells = Cells(self)
        # Solange das Programm selbst schreibt (`cells[...] = ...`,
        # `load_dataframe`), darf `on_edit_cell` nicht feuern: gemeint
        # ist die Änderung **durch den Benutzer**, sonst löste schon das
        # Füllen der Tabelle hundert Ereignisse aus.
        self._schreibt_selbst = False
        super().__init__(parent)

    @property
    def cells(self) -> Cells:
        return self._cells

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        widget = QTableWidget(eltern_widget)
        widget.setRowCount(self.row_count)
        widget.setColumnCount(self.col_count)
        widget.currentCellChanged.connect(self._bei_zellwechsel)
        widget.itemChanged.connect(self._bei_zellaenderung)
        return widget

    def _bei_zellwechsel(self, zeile: int, spalte: int, *_vorher: int) -> None:
        # Qt zeigt mit -1 an, dass gar keine Zelle mehr ausgewählt ist
        # (etwa nachdem die letzte Zeile gelöscht wurde). Das ist keine
        # Auswahl und soll deshalb auch keine melden.
        if zeile >= 0 and spalte >= 0:
            self._ereignis_ausloesen("on_select_cell", spalte, zeile)

    def _bei_zellaenderung(self, eintrag: Any) -> None:
        if self._schreibt_selbst:
            return
        self._ereignis_ausloesen(
            "on_edit_cell", eintrag.column(), eintrag.row(), eintrag.text()
        )

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "row_count":
            self._qwidget.setRowCount(wert)
        elif name == "col_count":
            self._qwidget.setColumnCount(wert)

    def load_dataframe(self, df: Any) -> None:
        """Zeigt einen pandas-`DataFrame` an (Abschnitt 11.6)."""
        from pcl.dataframe import load_dataframe

        load_dataframe(self, df)

    def to_dataframe(self) -> Any:
        """Liest den Inhalt als pandas-`DataFrame` zurück (Abschnitt 11.6)."""
        from pcl.dataframe import to_dataframe

        return to_dataframe(self)


class Picture:
    """Aufklappbare Untereigenschaft eines `Image`, z. B.
    ``self.i_bild.picture.load_from_file("assets/cookie.png")``
    (Abschnitt 5.0, 11.4)."""

    def __init__(self, besitzer: Image) -> None:
        self._besitzer = besitzer
        self._pfad: str | None = None
        self._original = QPixmap()

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
        # Das ungeskalierte Bild bleibt hier liegen: `stretch` und
        # `proportional` rechnen bei jeder Größenänderung neu, und wer
        # zweimal hintereinander skaliert, bekommt Treppen.
        self._original = QPixmap(pfad)
        self._besitzer._bild_anzeigen()

    def clear(self) -> None:
        self._pfad = None
        self._original = QPixmap()
        self._besitzer._qwidget.clear()

    @property
    def original(self) -> QPixmap:
        """Das geladene Bild in seiner eigenen Größe."""
        return self._original


class Image(Control):
    """Bildanzeige, per `on_click` auch anklickbar. Qt-Basis: `QLabel`
    mit `QPixmap`.

    `on_click` wie Lazarus' `TImage.OnClick`: im Beispielprojekt
    `04_CookieKlicker` ist das anklickbare Bild die ganze Spielidee,
    und ohne dieses Ereignis müsste ein durchsichtiger Knopf darüber
    gelegt werden - ein Kniff, den kein Lehrbuch erklärt.

    Die drei Eigenschaften `stretch`, `proportional` und `center`
    heißen und wirken wie in Lazarus; **nur der Standardwert von
    `stretch` ist ein anderer.** In Lazarus steht er auf `False`, und
    ein zu großes Bild wird oben links abgeschnitten. Natter zeigt es
    stattdessen von Anfang an passend: die Kekse in
    `04_CookieKlicker` sind 512×512 Punkte groß und liegen in einem
    300×300 großen `Image` - mit Lazarus' Standard sähe man ein Viertel
    Keks. Wer das Lazarus-Verhalten will, schreibt
    ``self.i_bild.stretch = False``.
    """

    stretch = Prop(
        bool,
        True,
        kategorie="Darstellung",
        doc="Bild auf die Größe der Komponente ziehen",
    )
    proportional = Prop(
        bool,
        False,
        kategorie="Darstellung",
        doc="Beim Ziehen das Seitenverhältnis behalten",
    )
    center = Prop(
        bool,
        False,
        kategorie="Darstellung",
        doc="Bild mittig setzen, wenn es kleiner ist als die Komponente",
    )

    def __init__(self, parent: Control) -> None:
        self._picture = Picture(self)
        super().__init__(parent)

    @property
    def picture(self) -> Picture:
        return self._picture

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        return QLabel(eltern_widget)

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name in ("stretch", "proportional", "center", "width", "height"):
            self._bild_anzeigen()

    def _bild_anzeigen(self) -> None:
        """Setzt das Bild so ins `QLabel`, wie die drei Eigenschaften es
        verlangen.

        `setScaledContents` allein reicht nur für den einfachsten Fall.
        Es zieht das Bild **ohne** Rücksicht auf das Seitenverhältnis
        auf die volle Fläche; für `proportional` muss deshalb von Hand
        skaliert werden. Und weil `setScaledContents(True)` jede
        Ausrichtung überfährt, darf es gleichzeitig mit `center` gar
        nicht an sein.
        """
        original = self._picture.original
        widget = self._qwidget
        if original.isNull():
            widget.clear()
            return

        widget.setAlignment(
            Qt.AlignmentFlag.AlignCenter
            if self.center
            else Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )

        if self.stretch and not self.proportional:
            widget.setScaledContents(True)
            widget.setPixmap(original)
            return

        widget.setScaledContents(False)
        if not self.stretch:
            widget.setPixmap(original)
            return

        widget.setPixmap(
            original.scaled(
                self.width,
                self.height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )


def _prop_gleichziehen(komponente: Control, name: str, wert: Any) -> None:
    """Schreibt einen vom Qt-Widget abgeänderten Wert zurück in den `Prop`.

    Qt kappt einen zu großen Wert an `maximum` und rundet bei
    `QDoubleSpinBox` auf `decimals` – ohne diesen Abgleich stünde im
    `Prop` danach eine Zahl, die das Widget gar nicht anzeigt. Die
    Zuweisung geht bewusst am Deskriptor vorbei (direkt ins `__dict__`),
    damit `Prop.__set__` nicht ein zweites Mal ins Widget schreibt;
    dasselbe Vorgehen wie bei `connected` in
    `pcl/components/data_access.py`.
    """
    komponente.__dict__[f"_prop_{name}"] = wert


class SpinEdit(Control):
    """Zahleneingabe mit Pfeilknöpfen. Qt-Basis: `QSpinBox`.

    Entspricht `TSpinEdit` in Lazarus samt dessen Namen `Value` für den
    Wert (während `ScrollBar`/`TrackBar` ihn `position` nennen - auch das
    ist die Benennung der jeweiligen LCL-Komponente)."""

    minimum = Prop(int, 0, kategorie="Verhalten", doc="Kleinster möglicher Wert")
    maximum = Prop(int, 100, kategorie="Verhalten", doc="Größter möglicher Wert")
    value = Prop(int, 0, kategorie="Verhalten", doc="Aktueller Wert")
    increment = Prop(int, 1, kategorie="Verhalten", doc="Schrittweite der beiden Pfeilknöpfe")
    on_change = Event(doc="Wird bei jeder Änderung des Wertes ausgelöst")

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        widget = QSpinBox(eltern_widget)
        # setRange statt zweier Einzelaufrufe: setMinimum(50) würde bei
        # einem noch kleineren maximum das maximum stillschweigend
        # mitziehen.
        widget.setRange(self.minimum, self.maximum)
        widget.setSingleStep(self.increment)
        widget.setValue(self.value)
        widget.valueChanged.connect(self._bei_wertaenderung)
        return widget

    def _bei_wertaenderung(self, wert: int) -> None:
        self.value = wert
        if self.on_change is not None:
            self.on_change(self)

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "minimum":
            self._qwidget.setMinimum(wert)
        elif name == "maximum":
            self._qwidget.setMaximum(wert)
        elif name == "increment":
            self._qwidget.setSingleStep(wert)
        elif name == "value":
            self._qwidget.setValue(wert)
        if name in ("minimum", "maximum", "value"):
            _prop_gleichziehen(self, "value", self._qwidget.value())


class FloatSpinEdit(Control):
    """Eingabe einer Kommazahl mit Pfeilknöpfen. Qt-Basis:
    `QDoubleSpinBox`. Entspricht `TFloatSpinEdit` in Lazarus."""

    minimum = Prop(float, 0.0, kategorie="Verhalten", doc="Kleinster möglicher Wert")
    maximum = Prop(float, 100.0, kategorie="Verhalten", doc="Größter möglicher Wert")
    value = Prop(float, 0.0, kategorie="Verhalten", doc="Aktueller Wert")
    increment = Prop(float, 1.0, kategorie="Verhalten", doc="Schrittweite der beiden Pfeilknöpfe")
    decimals = Prop(int, 2, kategorie="Darstellung", doc="Anzahl der angezeigten Nachkommastellen")
    on_change = Event(doc="Wird bei jeder Änderung des Wertes ausgelöst")

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        widget = QDoubleSpinBox(eltern_widget)
        widget.setDecimals(self.decimals)
        widget.setRange(float(self.minimum), float(self.maximum))
        widget.setSingleStep(float(self.increment))
        widget.setValue(float(self.value))
        widget.valueChanged.connect(self._bei_wertaenderung)
        return widget

    def _bei_wertaenderung(self, wert: float) -> None:
        self.value = wert
        if self.on_change is not None:
            self.on_change(self)

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "minimum":
            self._qwidget.setMinimum(float(wert))
        elif name == "maximum":
            self._qwidget.setMaximum(float(wert))
        elif name == "increment":
            self._qwidget.setSingleStep(float(wert))
        elif name == "decimals":
            self._qwidget.setDecimals(wert)
        elif name == "value":
            self._qwidget.setValue(float(wert))
        if name in ("minimum", "maximum", "increment", "decimals", "value"):
            # Auch minimum/maximum/increment werden zurückgelesen: eine
            # zugewiesene ganze Zahl (Prop lässt int für float durch) soll
            # danach als float in der Eigenschaft stehen.
            for prop_name, gelesen in (
                ("minimum", self._qwidget.minimum()),
                ("maximum", self._qwidget.maximum()),
                ("increment", self._qwidget.singleStep()),
                ("value", self._qwidget.value()),
            ):
                _prop_gleichziehen(self, prop_name, gelesen)


class TrackBar(Control):
    """Schieberegler zur Eingabe eines Zahlenwerts. Qt-Basis: `QSlider`
    (waagerecht). Entspricht `TTrackBar` in Lazarus - daher `maximum = 10`
    und `frequency = 1` als Standard und nicht die 100 der `ScrollBar`."""

    # Standardgröße als Prop-Standard (wie bei `Chart`): mit den 75x25 aus
    # `Control` wäre von den Teilstrichen nichts zu erkennen.
    width = Prop(int, 150, kategorie="Layout", doc="Breite in Pixeln")
    height = Prop(int, 30, kategorie="Layout", doc="Höhe in Pixeln")

    minimum = Prop(int, 0, kategorie="Verhalten", doc="Kleinster möglicher Wert")
    maximum = Prop(int, 10, kategorie="Verhalten", doc="Größter möglicher Wert")
    position = Prop(int, 0, kategorie="Verhalten", doc="Aktueller Wert")
    frequency = Prop(
        int,
        1,
        kategorie="Darstellung",
        doc="Abstand der Teilstriche unter dem Schieber; 0 = keine Teilstriche",
    )
    on_change = Event(doc="Wird bei Änderung der Position ausgelöst")

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        widget = QSlider(Qt.Orientation.Horizontal, eltern_widget)
        widget.setRange(self.minimum, self.maximum)
        widget.setValue(self.position)
        self._teilstriche_anwenden(widget, self.frequency)
        widget.valueChanged.connect(self._bei_wertaenderung)
        return widget

    @staticmethod
    def _teilstriche_anwenden(widget: QSlider, frequency: int) -> None:
        widget.setTickInterval(frequency)
        widget.setTickPosition(
            QSlider.TickPosition.TicksBelow if frequency > 0 else QSlider.TickPosition.NoTicks
        )

    def _bei_wertaenderung(self, wert: int) -> None:
        self.position = wert
        if self.on_change is not None:
            self.on_change(self)

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "minimum":
            self._qwidget.setMinimum(wert)
        elif name == "maximum":
            self._qwidget.setMaximum(wert)
        elif name == "position":
            self._qwidget.setValue(wert)
        elif name == "frequency":
            self._teilstriche_anwenden(self._qwidget, wert)
        if name in ("minimum", "maximum", "position"):
            _prop_gleichziehen(self, "position", self._qwidget.value())


class ProgressBar(Control):
    """Fortschrittsbalken. Qt-Basis: `QProgressBar`. Entspricht
    `TProgressBar` in Lazarus."""

    # Standardgröße als Prop-Standard (wie bei `Chart`): 75x25 ergäbe
    # einen Stummel, in dem die Prozentzahl nicht mehr lesbar ist.
    width = Prop(int, 150, kategorie="Layout", doc="Breite in Pixeln")
    height = Prop(int, 22, kategorie="Layout", doc="Höhe in Pixeln")

    minimum = Prop(int, 0, kategorie="Verhalten", doc="Kleinster möglicher Wert")
    maximum = Prop(int, 100, kategorie="Verhalten", doc="Größter möglicher Wert")
    position = Prop(int, 0, kategorie="Verhalten", doc="Aktueller Wert (Füllstand)")
    show_text = Prop(bool, True, kategorie="Darstellung", doc="Prozentzahl im Balken anzeigen")

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        widget = QProgressBar(eltern_widget)
        widget.setRange(self.minimum, self.maximum)
        widget.setValue(self.position)
        widget.setTextVisible(self.show_text)
        widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return widget

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "show_text":
            self._qwidget.setTextVisible(wert)
        elif name in ("minimum", "maximum", "position"):
            self._wertebereich_anwenden()

    def _wertebereich_anwenden(self) -> None:
        """Setzt Bereich und Füllstand gemeinsam - und kappt den
        Füllstand selbst.

        `QProgressBar.setValue()` **ignoriert** einen Wert außerhalb des
        Bereichs stillschweigend, statt ihn wie `QSpinBox`/`QSlider` auf
        die Grenze zu kappen: `position = 300` bei `maximum = 100` ließ
        den Balken kommentarlos auf 0 stehen. Für jemanden, der gerade
        `position = fertig_prozent` schreibt, ist das die denkbar
        unbrauchbarste Reaktion, deshalb hier dieselbe Kappung wie bei
        den übrigen Wertkomponenten.
        """
        self._qwidget.setRange(self.minimum, self.maximum)
        self._qwidget.setValue(max(self.minimum, min(self.maximum, self.position)))
        _prop_gleichziehen(self, "position", self._qwidget.value())
