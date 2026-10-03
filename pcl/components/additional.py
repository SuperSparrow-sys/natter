"""Additional-Komponenten: Shape, StringGrid, Image, SpinEdit,
FloatSpinEdit, TrackBar, ProgressBar.

Siehe README.md, Abschnitt 5.2 (Palette „Zusätzlich“). Die
Wertkomponenten (SpinEdit, FloatSpinEdit, TrackBar, ProgressBar) sind
jeweils ein dünner Mantel um ein Qt-Standardwidget: ein `Prop` je
Eigenschaft, `_bei_prop_aenderung` reicht die Zuweisung an das
Widget weiter, und das Signal des Widgets schreibt den Wert zurück in
den `Prop`. Dadurch wirken Code und Bedienung in beide Richtungen, ohne
dass es eine zweite Quelle für den Wert gäbe.

`TrackBar` und `ProgressBar` wären einen eigenen Palettenreiter wert.
Den gibt es in Natter noch nicht (`ide/shell/hauptfenster.py` verbindet
die Klick-Signale von genau zwei Listen), deshalb stehen sie unter
„Zusätzlich“.

MaskEdit, PaintBox und HtmlViewer standen hier bis M15 als
zurückgestellt; sie sind inzwischen gebaut und wohnen in
`pcl/components/eingaben.py`, `graphics.py` und `medien.py`.
"""

from __future__ import annotations

import operator
import os
import sys
from pathlib import Path
from typing import Any

from PySide6.QtCore import QLocale, Qt
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDoubleSpinBox,
    QLabel,
    QProgressBar,
    QSlider,
    QSpinBox,
    QWidget,
)

from pcl.components.tabelle import TabellenAnsicht
from pcl.control import Control
from pcl.errors import NatterPropertyError, NatterZellenError
from pcl.properties import (
    ART_FARBE,
    STANDARD_BRUSH_FARBE,
    Event,
    Prop,
    farbe_pruefen,
    typ_beschreibung,
)
from pcl.strings import Strings
from pcl.zahlen import text as zahl_text

_DEUTSCH = QLocale(QLocale.Language.German, QLocale.Country.Germany)

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
                f"Shape.brush.color erwartet {typ_beschreibung(str, akkusativ=True)}, "
                f"erhalten wurde {typ_beschreibung(type(wert))}."
            )
        farbe_pruefen("Shape.brush.color", wert)
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
 (`QPainter` auf einem `QWidget`). Füllung (`brush.color`) und Rand
 (`pen_color`) sind unabhängig voneinander -
 Gewünscht: „Rahmen, Rahmenfarbe“ fehlte bisher,
 Rand und Füllung nutzten dieselbe Farbe."""

    shape = Prop(
        str,
        "rectangle",
        kategorie="Darstellung",
        doc=f"Form der Zeichnung: {' oder '.join(_FORMEN)}",
        werte=_FORMEN,
    )
    pen_color = Prop(
        str,
        "#000000",
        kategorie="Darstellung",
        doc="Randfarbe als #RRGGBB, unabhängig von der Füllfarbe",
        art=ART_FARBE,
    )
    transparent = Prop(
        bool,
        False,
        kategorie="Darstellung",
        doc="Wenn wahr, keine Füllung - nur der Rand wird gezeichnet",
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


def _zelltext(wert: Any) -> str:
    """Der Text einer Zelle. Was das Programm über `cells[…]`
    hineinschreibt, ist schon Text; `load_dataframe` legt die Werte
    aus dem `DataFrame` unverändert ab, und erst hier wird Text daraus,
    nur für die Zellen, die jemand ansieht oder abfragt.

    Kommazahlen mit Dezimalkomma wie überall in Natter und wie mit
    `text()` geschrieben: 0.1 + 0.2 als „0,3“, 1e-05 als „0,00001“.
    Mit `str()` standen Rundungsreste, ein „e“ und bis 0.3.3 ein
    Dezimalpunkt in der Tabelle."""
    if isinstance(wert, str):
        return wert
    if isinstance(wert, float):
        return zahl_text(wert)
    return str(wert)


class Cells:
    """Aufklappbare Untereigenschaft eines `StringGrid`, Zugriff über
    ``self.sg_tabelle.cells[spalte, zeile]`` (Abschnitt 5.1)."""

    def __init__(self, besitzer: StringGrid) -> None:
        self._besitzer = besitzer

    def _pruefen(self, index: tuple[int, int]) -> tuple[int, int]:
        """Spalte und Zeile, wenn es die Zelle gibt; sonst ein Fehler
        mit dem gültigen Bereich."""
        ergebnis: list[int] = []
        for art, wert, anzahl, name in (
            ("Spalte", index[0], self._besitzer.col_count, "Spalten"),
            ("Zeile", index[1], self._besitzer.row_count, "Zeilen"),
        ):
            try:
                if isinstance(wert, bool):
                    raise TypeError
                # `operator.index` statt `isinstance(int)`: eine Zahl
                # aus numpy oder pandas ist auch ein Index.
                wert = operator.index(wert)
            except TypeError:
                raise NatterPropertyError(
                    f"StringGrid.cells erwartet als {art} "
                    f"{typ_beschreibung(int, akkusativ=True)}, "
                    f"erhalten wurde {typ_beschreibung(type(wert))}."
                ) from None
            ergebnis.append(wert)
            if not 0 <= wert < anzahl:
                bereich = f"(0 bis {anzahl - 1})" if anzahl else "(keine)"
                raise NatterZellenError(
                    f"{art} {wert} gibt es nicht, die Tabelle hat "
                    f"{anzahl} {name} {bereich}."
                )
        return ergebnis[0], ergebnis[1]

    def __getitem__(self, index: tuple[int, int]) -> str:
        spalte, zeile = self._pruefen(index)
        return self._besitzer._qwidget.modell.text(zeile, spalte)

    def __setitem__(self, index: tuple[int, int], wert: str) -> None:
        if not isinstance(wert, str):
            raise NatterPropertyError(
                f"StringGrid.cells erwartet {typ_beschreibung(str, akkusativ=True)}, "
                f"erhalten wurde {typ_beschreibung(type(wert))}."
            )
        spalte, zeile = self._pruefen(index)
        # `on_edit_cell` meint die Änderung durch den Benutzer. Was das
        # Programm selbst hineinschreibt, ist keine - sonst löste schon
        # das Füllen der Tabelle hundert Ereignisse aus. `text_setzen`
        # meldet deshalb nur die neue Anzeige, keine Bearbeitung.
        self._besitzer._qwidget.modell.text_setzen(zeile, spalte, wert)


class ColWidths:
    """Die Spaltenbreiten eines `StringGrid`, Zugriff über
    ``self.sg_tabelle.col_widths[spalte] = 120``."""

    def __init__(self, besitzer: StringGrid) -> None:
        self._besitzer = besitzer

    def _pruefen(self, spalte: Any) -> int:
        anzahl = self._besitzer.col_count
        if isinstance(spalte, bool) or not isinstance(spalte, int):
            raise NatterPropertyError(
                f"StringGrid.col_widths erwartet als Spalte "
                f"{typ_beschreibung(int, akkusativ=True)}, "
                f"erhalten wurde {typ_beschreibung(type(spalte))}."
            )
        if not 0 <= spalte < anzahl:
            bereich = f"(0 bis {anzahl - 1})" if anzahl else "(keine)"
            raise NatterZellenError(
                f"Spalte {spalte} gibt es nicht, die Tabelle hat {anzahl} Spalten {bereich}."
            )
        return spalte

    def __getitem__(self, spalte: int) -> int:
        return self._besitzer._qwidget.columnWidth(self._pruefen(spalte))

    def __setitem__(self, spalte: int, breite: int) -> None:
        if isinstance(breite, bool) or not isinstance(breite, int):
            raise NatterPropertyError(
                f"StringGrid.col_widths erwartet als Breite "
                f"{typ_beschreibung(int, akkusativ=True)}, "
                f"erhalten wurde {typ_beschreibung(type(breite))}."
            )
        self._besitzer._qwidget.setColumnWidth(self._pruefen(spalte), breite)

    def __len__(self) -> int:
        return self._besitzer.col_count


class StringGrid(Control):
    """Tabelle aus Text-Zellen. Qt-Basis: `QTableView` mit einem
    Modell, das die Texte als Listen hält (`pcl/components/tabelle.py`);
    auch 100.000 Zeilen sind so in Bruchteilen einer Sekunde gefüllt.

    Beide Ereignisse bekommen `spalte` und `zeile` mit - in dieser
    Reihenfolge, wie `cells[spalte, zeile]` -, `on_edit_cell`
    zusätzlich den neuen Text.

    `col_titles` beschriftet die Spaltenköpfe; ohne stehen dort die
    Nummern 1, 2, 3. `col_widths[spalte]` liest und setzt die Breite
    einer einzelnen Spalte, `default_col_width` die aller übrigen.
    """

    row_count = Prop(
        int, 5, kategorie="Daten", doc="Anzahl der Zeilen, ab 0", minimum=0
    )
    col_count = Prop(
        int, 5, kategorie="Daten", doc="Anzahl der Spalten, ab 0", minimum=0
    )
    default_col_width = Prop(
        int,
        100,
        kategorie="Layout",
        doc="Breite der Spalten in Pixeln, sofern col_widths nichts anderes sagt",
    )
    read_only = Prop(
        bool,
        False,
        kategorie="Verhalten",
        doc="Wenn wahr, lassen sich die Zellen nicht bearbeiten; das Programm "
        "kann weiter hineinschreiben",
    )

    on_select_cell = Event(doc="Wird ausgelöst, wenn eine andere Zelle ausgewählt wird")
    on_edit_cell = Event(doc="Wird ausgelöst, nachdem eine Zelle geändert wurde")

    #: Ein Doppelklick im Designer meint die Auswahl, nicht die
    #: Änderung.
    standard_ereignis = "on_select_cell"

    _eingabe_loest_standardknopf_aus = False

    def __init__(self, parent: Control) -> None:
        self._cells = Cells(self)
        self._col_widths = ColWidths(self)
        self._col_titles = Strings(self._titel_anwenden)
        super().__init__(parent)

    @property
    def cells(self) -> Cells:
        return self._cells

    @property
    def col_widths(self) -> ColWidths:
        return self._col_widths

    @property
    def col_titles(self) -> Strings:
        return self._col_titles

    @col_titles.setter
    def col_titles(self, werte: list[str]) -> None:
        self._col_titles.zuweisen(werte)

    @property
    def col(self) -> int:
        """Spalte der gewählten Zelle, -1 ohne Auswahl."""
        if self._qwidget.currentRow() < 0:
            return -1
        return self._qwidget.currentColumn()

    @col.setter
    def col(self, wert: int) -> None:
        wert = self._auswahl_pruefen("col", wert, self.col_count)
        self._zelle_waehlen(wert, -1 if wert == -1 else self.row)

    @property
    def row(self) -> int:
        """Zeile der gewählten Zelle, -1 ohne Auswahl."""
        if self._qwidget.currentColumn() < 0:
            return -1
        return self._qwidget.currentRow()

    @row.setter
    def row(self, wert: int) -> None:
        wert = self._auswahl_pruefen("row", wert, self.row_count)
        self._zelle_waehlen(-1 if wert == -1 else self.col, wert)

    def _auswahl_pruefen(self, name: str, wert: object, anzahl: int) -> int:
        try:
            if isinstance(wert, bool):
                raise TypeError
            zahl = operator.index(wert)
        except TypeError:
            raise NatterPropertyError(
                f"StringGrid.{name} erwartet {typ_beschreibung(int, akkusativ=True)}, "
                f"erhalten wurde {typ_beschreibung(type(wert))}."
            ) from None
        if not -1 <= zahl < anzahl:
            raise NatterPropertyError(
                f"StringGrid.{name} erwartet eine Zahl von -1 bis "
                f"{anzahl - 1}, erhalten wurde {zahl}."
            )
        return zahl

    def _zelle_waehlen(self, spalte: int, zeile: int) -> None:
        """Wählt eine Zelle. Steht nur eine der beiden Angaben fest,
        weil noch nichts gewählt war, gilt für die andere 0. Wer -1
        setzt, hebt die Auswahl ganz auf."""
        widget = self._qwidget
        if spalte == -1 and zeile == -1:
            widget.setCurrentCell(-1, -1)
            widget.clearSelection()
            return
        widget.setCurrentCell(max(zeile, 0), max(spalte, 0))

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        widget = TabellenAnsicht(eltern_widget, _zelltext)
        widget.setRowCount(self.row_count)
        widget.setColumnCount(self.col_count)
        widget.horizontalHeader().setDefaultSectionSize(self.default_col_width)
        self._bearbeiten_erlaubt = widget.editTriggers()
        widget.currentCellChanged.connect(self._bei_zellwechsel)
        widget.modell.zelle_bearbeitet.connect(self._bei_zellaenderung)
        return widget

    def _titel_anwenden(self) -> None:
        """Beschriftet die Spaltenköpfe aus `col_titles`. Spalten ohne
        Titel zeigen wieder ihre Nummer."""
        self._qwidget.modell.titel_setzen(list(self._col_titles))

    def _bei_zellwechsel(self, zeile: int, spalte: int, *_vorher: int) -> None:
        # Qt zeigt mit -1 an, dass gar keine Zelle mehr ausgewählt ist
        # (etwa nachdem die letzte Zeile gelöscht wurde). Das ist keine
        # Auswahl und soll deshalb auch keine melden.
        if zeile >= 0 and spalte >= 0:
            self._ereignis_ausloesen("on_select_cell", spalte, zeile)

    def _bei_zellaenderung(self, zeile: int, spalte: int, text: str) -> None:
        self._ereignis_ausloesen("on_edit_cell", spalte, zeile, text)

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "row_count":
            self._qwidget.setRowCount(wert)
        elif name == "col_count":
            self._qwidget.setColumnCount(wert)
        elif name == "default_col_width":
            self._qwidget.horizontalHeader().setDefaultSectionSize(wert)
        elif name == "read_only":
            self._qwidget.setEditTriggers(
                QAbstractItemView.EditTrigger.NoEditTriggers
                if wert
                else self._bearbeiten_erlaubt
            )

    def load_dataframe(self, df: Any) -> None:
        """Zeigt einen pandas-`DataFrame` an (Abschnitt 11.6)."""
        from pcl.dataframe import load_dataframe

        load_dataframe(self, df)

    def to_dataframe(self) -> Any:
        """Liest den Inhalt als pandas-`DataFrame` zurück (Abschnitt 11.6)."""
        from pcl.dataframe import to_dataframe

        return to_dataframe(self)


def _bilddatei_finden(pfad: str, besitzer: Control) -> str:
    """Wo eine Bilddatei mit relativem Pfad wirklich liegt.

    Der Designer speichert ein Bild relativ zum Projektordner
    (`assets/cookie.png`). Das gestartete Programm läuft zwar im
    Projektordner, ein Doppelklick auf `main.py` oder ein Aufruf aus
    einem anderen Ordner aber nicht; der Designer selbst läuft nie
    dort. Gesucht wird deshalb der Reihe nach: im Arbeitsordner, im
    Projektordner, den der Designer beim Laden am Formular vermerkt,
    und neben dem gestarteten Hauptprogramm.

    Im Designer gilt nur der Projektordner, wie beim Exe-Export. Eine
    `.pfm` aus fremder Hand kann einen Pfad auf einen anderen Rechner
    nennen; schon die Frage, ob es die Datei gibt, baut dann eine
    Verbindung zu diesem Rechner auf und hielt das Fenster rund 40
    Sekunden an (Punkt 334). Ob ein Pfad im Projektordner liegt, wird
    deshalb nur am Text entschieden, ohne das Dateisystem zu fragen.
    Ein Pfad außerhalb ergibt eine leere Angabe, also kein Bild.
    """
    kandidat = Path(pfad)
    projektordner = getattr(besitzer._formular(), "_projektordner", None)
    if projektordner is not None:
        return _im_projektordner(pfad, Path(projektordner))
    if kandidat.is_absolute() or kandidat.exists():
        return pfad
    basen: list[Path] = []
    hauptprogramm = getattr(sys.modules.get("__main__"), "__file__", None)
    if hauptprogramm:
        basen.append(Path(hauptprogramm).resolve().parent)
    for basis in basen:
        if (basis / kandidat).exists():
            return str(basis / kandidat)
    return pfad


def _im_projektordner(pfad: str, projektordner: Path) -> str:
    """`pfad` im Projektordner als vollständiger Pfad, sonst leer.

    Verglichen wird nur der Text nach `os.path.normpath`, damit ein
    Netzpfad gar nicht erst berührt wird; `..` wird dabei
    aufgelöst."""
    ordner = os.path.normpath(projektordner)
    ziel = os.path.normpath(os.path.join(ordner, pfad))
    try:
        gemeinsam = os.path.commonpath(
            [os.path.normcase(ordner), os.path.normcase(ziel)]
        )
    except ValueError:
        return ""
    if gemeinsam != os.path.normcase(ordner):
        return ""
    return ziel


def _relativ_zum_projekt(pfad: str, besitzer: Control) -> str:
    """Ein absoluter Pfad im Projektordner, relativ zu ihm geschrieben.

    Nur im Designer bekannt: er vermerkt den Projektordner beim Laden
    am Formular. Zieht jemand ein Bild hinein, kommt es mit seinem
    absoluten Pfad an; im Objektinspektor und in der `.pfm` soll aber
    `assets/keks.png` stehen und nicht der Pfad auf diesem Rechner.

    Wie in `_im_projektordner` nur am Text entschieden: `resolve()`
    hätte einen Pfad auf einen anderen Rechner schon angefragt.
    """
    projektordner = getattr(besitzer._formular(), "_projektordner", None)
    if projektordner is None or not Path(pfad).is_absolute():
        return pfad
    ziel = _im_projektordner(pfad, Path(projektordner))
    if not ziel:
        return pfad
    relativ = os.path.relpath(ziel, os.path.normpath(projektordner))
    return Path(relativ).as_posix()


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

    @property
    def file(self) -> str:
        """Die Bilddatei als Text, leer heißt kein Bild.

        Das ist die Form, in der der Designer das Bild speichert:
        `.pfm` und erzeugter Code tragen ``picture.file =
        "assets/cookie.png"``. Zuweisen lädt das Bild, eine leere
        Zeichenkette entfernt es.
        """
        return self._pfad or ""

    @file.setter
    def file(self, pfad: str) -> None:
        if pfad == "":
            self.clear()
        else:
            self.load_from_file(pfad)

    def load_from_file(self, pfad: str) -> None:
        if not isinstance(pfad, str):
            raise NatterPropertyError(
                f"Image.picture.load_from_file erwartet "
                f"{typ_beschreibung(str, akkusativ=True)}, "
                f"erhalten wurde {typ_beschreibung(type(pfad))}."
            )
        self._pfad = _relativ_zum_projekt(pfad, self._besitzer)
        # Das ungeskalierte Bild bleibt hier liegen: `stretch` und
        # `proportional` rechnen bei jeder Größenänderung neu, und wer
        # zweimal hintereinander skaliert, bekommt Treppen.
        self._original = QPixmap(_bilddatei_finden(pfad, self._besitzer))
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

    Ein Bild hat `on_click`, weil es häufig gebraucht wird: im
    Beispielprojekt `04_CookieKlicker` ist das anklickbare Bild die
    ganze Spielidee,
    und ohne dieses Ereignis müsste ein durchsichtiger Knopf darüber
    gelegt werden - ein Kniff, den kein Lehrbuch erklärt.

    `stretch` steht auf `True`, und das aus gutem Grund: ohne
    Skalierung wird ein zu großes Bild oben links abgeschnitten. Die
    Kekse in `04_CookieKlicker` sind 512×512 Punkte groß und liegen in
    einem 300×300 großen `Image` - unskaliert sähe man ein Viertel
    Keks. Wer das Bild in Originalgröße will, schreibt
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
        Es zieht das Bild ohne Rücksicht auf das Seitenverhältnis
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


def _bereich_gleichziehen(komponente: Control, wert_name: str) -> None:
    """Liest Bereich und Wert aus dem Widget zurück in die `Prop`s.

    Ein Minimum über dem Maximum schiebt Qt das Maximum mit hoch
    (und umgekehrt). Ohne das Zurücklesen zeigte der Objektinspektor
    danach `maximum = 100`, während das Feld keine Zahl unter 200
    mehr annahm.
    """
    widget = komponente._qwidget
    _prop_gleichziehen(komponente, "minimum", widget.minimum())
    _prop_gleichziehen(komponente, "maximum", widget.maximum())
    _prop_gleichziehen(komponente, wert_name, widget.value())


class SpinEdit(Control):
    """Zahleneingabe mit Pfeilknöpfen. Qt-Basis: `QSpinBox`.

    Der Wert heißt hier `value`, während `ScrollBar` und `TrackBar` ihn
    `position` nennen: bei einem Schieber ist die Stellung gemeint, bei
    einem Zahlenfeld die Zahl."""

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
            _bereich_gleichziehen(self, "value")


class FloatSpinEdit(Control):
    """Eingabe einer Kommazahl mit Pfeilknöpfen. Qt-Basis:
    `QDoubleSpinBox`."""

    minimum = Prop(float, 0.0, kategorie="Verhalten", doc="Kleinster möglicher Wert")
    maximum = Prop(float, 100.0, kategorie="Verhalten", doc="Größter möglicher Wert")
    value = Prop(float, 0.0, kategorie="Verhalten", doc="Aktueller Wert")
    increment = Prop(float, 1.0, kategorie="Verhalten", doc="Schrittweite der beiden Pfeilknöpfe")
    decimals = Prop(int, 2, kategorie="Darstellung", doc="Anzahl der angezeigten Nachkommastellen")
    on_change = Event(doc="Wird bei jeder Änderung des Wertes ausgelöst")

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        widget = QDoubleSpinBox(eltern_widget)
        # Immer deutsch, auch auf einem Rechner mit englischer
        # Systemsprache: sonst zeigte das Feld „2.50“ und nähme nur
        # den Punkt an.
        widget.setLocale(_DEUTSCH)
        widget.setDecimals(self.decimals)
        widget.setRange(float(self.minimum), float(self.maximum))
        widget.setSingleStep(float(self.increment))
        widget.setValue(float(self.value))
        widget.valueChanged.connect(self._bei_wertaenderung)
        # Nach dem Tippen in der festen Schreibweise: „2,5“ wird „2,50“.
        widget.editingFinished.connect(
            lambda: widget.lineEdit().setText(widget.textFromValue(widget.value()))
        )
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
        elif name == "value" and float(wert) != self._qwidget.value():
            # Nur bei einem anderen Wert: auch derselbe Wert schrieb das
            # Feld neu. Beim Tippen kam jede Ziffer als Änderung hier
            # an, aus „2“ wurde sofort „2,00“, und das Komma danach
            # passte nicht mehr hinein - „2,5“ ließ sich nicht tippen.
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
    (waagerecht). `maximum = 10` und `frequency = 1` als Standard und
    nicht die 100 der `ScrollBar`: ein Regler mit sichtbaren
    Teilstrichen braucht wenige, große Schritte."""

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
            _bereich_gleichziehen(self, "position")


class ProgressBar(Control):
    """Fortschrittsbalken. Qt-Basis: `QProgressBar`."""

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
        # Deutsch mit Leerzeichen vor dem Prozentzeichen: „50 %“.
        widget.setFormat("%p %")
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

        `QProgressBar.setValue()` ignoriert einen Wert außerhalb des
        Bereichs stillschweigend, statt ihn wie `QSpinBox`/`QSlider` auf
        die Grenze zu kappen: `position = 300` bei `maximum = 100` ließ
        den Balken kommentarlos auf 0 stehen. Für jemanden, der gerade
        `position = fertig_prozent` schreibt, ist das die denkbar
        unbrauchbarste Reaktion, deshalb hier dieselbe Kappung wie bei
        den übrigen Wertkomponenten.
        """
        self._qwidget.setRange(self.minimum, self.maximum)
        # Nur den Bereich: der Wert des Widgets steht nach einem
        # `setRange` auf -1 und soll `position` nicht überschreiben.
        _prop_gleichziehen(self, "minimum", self._qwidget.minimum())
        _prop_gleichziehen(self, "maximum", self._qwidget.maximum())
        self._qwidget.setValue(max(self.minimum, min(self.maximum, self.position)))
        _prop_gleichziehen(self, "position", self._qwidget.value())
