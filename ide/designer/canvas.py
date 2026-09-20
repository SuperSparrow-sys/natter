"""DesignerCanvas: zeigt ein Formular mit echten `pcl`-Komponenten,
Klick/Ziehen/Tastatur bearbeiten es statt die echte Interaktion
auszulösen. Jede Änderung läuft über ein Kommando (Undo/Redo).

Siehe README.md, Abschnitt 7.7: „Der Designer rendert echte
pcl-Komponenten“, Tastenkürzel wie dort beschrieben (Pfeiltasten =
Rasterschritt, Alt+Pfeil = 1 px, Umschalt+Pfeil = Größe, Entf = löschen,
Strg+D = duplizieren, dazu Strg+Z/Strg+Umschalt+Z bzw. Strg+Y für
Rückgängig/Wiederholen, Command-Pattern). `komponente_platzieren()` ist
das Gegenstück für die Komponentenpalette (Abschnitt 7.3). Acht sichtbare
Größenanfasser (wie in Lazarus) an der ausgewählten Komponente lassen
sich zusätzlich zur Tastatur mit der Maus ziehen (`_Anfasser`,
`_ANFASSER_VERHALTEN`).
"""

from __future__ import annotations

import types
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import QEvent, QMimeData, QObject, QPoint, Qt
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import QDialog, QMenu, QWidget

from ide.codegen.design import design_datei_erzeugen
from ide.codegen.ereignis import handler_methode_einfuegen, handler_methode_umbenennen
from ide.designer.bilder import bild_in_assets_uebernehmen, ist_bilddatei
from ide.designer.kommando import EigenschaftKommando, Kommandostapel
from ide.designer.laden import platzhalter_erzeugen
from ide.designer.pfm_schreiben import formular_als_pfm_speichern
from ide.inspector.komponentenbaum import kind_komponenten
from pcl.components.additional import Image
from pcl.control import EREIGNIS_PARAMETER, MAUS_EREIGNISSE
from pcl.form import Form
from pcl.properties import eigenschaften, ereignisse

#: Beim Ablegen mehrerer Bilder auf einmal werden die neuen Komponenten
#: leicht versetzt, damit sie sich nicht vollständig überdecken.
_MEHRFACH_VERSATZ = 16

#: Größte Kantenlänge einer per Drag & Drop erzeugten `Image`-Komponente;
#: ein 2500×2500-Foto (wie in `tests/daten/lazarus/l_Pet`) soll das Formular
#: nicht sprengen.
_BILD_MAXKANTE = 240

_ANFASSER_GROESSE = 7
_ANFASSER_FARBE = "#0067c0"

# Name -> (links_je_dx, breite_je_dx, oben_je_dy, hoehe_je_dy): wie stark
# sich `left`/`width`/`top`/`height` je Pixel Mausbewegung ändern, z. B.
# "nw" verschiebt links UND oben, während sich Breite/Höhe gegenläufig
# verkleinern; "e" ändert nur die Breite.
_ANFASSER_VERHALTEN: dict[str, tuple[int, int, int, int]] = {
    "nw": (1, -1, 1, -1),
    "n": (0, 0, 1, -1),
    "ne": (0, 1, 1, -1),
    "e": (0, 1, 0, 0),
    "se": (0, 1, 0, 1),
    "s": (0, 0, 0, 1),
    "sw": (1, -1, 0, 1),
    "w": (1, -1, 0, 0),
}

#: Die Anfasser, die das Formular bekommt.
#:
#: Nur rechts, unten und in der rechten unteren Ecke: im Designer sitzt
#: das Formular fest in der linken oberen Ecke seines Rollbereichs, und
#: `left`/`top` gibt es an einem Formular gar nicht - ein Zug an „nw"
#: müsste es also verschieben, und verschieben lässt es sich nicht.
#:
#: Vorher hatte es gar keine: `_anfasser_aktualisieren` blendete
#: alle aus, sobald das Formular ausgewählt war. Die Fenstergröße ließ
#: sich damit nur über `width`/`height` im Objektinspektor ändern -
#: vom Nutzer gemeldet („der designer hat eine zu kleine fläche, diese
#: soll anpassbar sein über die ecken zum ziehen").
_ANFASSER_FUER_FORMULAR = ("e", "s", "se")

#: Kleiner darf ein Formular beim Ziehen nicht werden. Bei einem
#: Pixel lägen seine drei Anfasser übereinander in einem Punkt, und ein
#: versehentlich zusammengezogenes Formular wäre nicht mehr
#: aufzuziehen. Eine gewöhnliche Komponente darf weiter bis auf einen
#: Pixel schrumpfen - sie lässt sich über den Objektinspektor immer
#: wieder vergrößern.
_MINDESTGROESSE_FORMULAR = 16

_ANFASSER_CURSOR: dict[str, Qt.CursorShape] = {
    "nw": Qt.CursorShape.SizeFDiagCursor,
    "se": Qt.CursorShape.SizeFDiagCursor,
    "ne": Qt.CursorShape.SizeBDiagCursor,
    "sw": Qt.CursorShape.SizeBDiagCursor,
    "n": Qt.CursorShape.SizeVerCursor,
    "s": Qt.CursorShape.SizeVerCursor,
    "e": Qt.CursorShape.SizeHorCursor,
    "w": Qt.CursorShape.SizeHorCursor,
}

# Der Auswahlrahmen besteht aus vier dünnen Streifen, die über der
# ausgewählten Komponente liegen – wie die acht Größenanfasser und wie
# der Rahmen in Lazarus. Früher stand er als QSS-Regel
# `*[design_ausgewaehlt="true"] { border: 2px solid ... }` im Stylesheet
# des Formulars. Das war bequem, hat den Designer aber stillschweigend
# vom laufenden Programm entfernt: sobald eine Komponente ein eigenes
# Stylesheet bekam (Schriftart oder Hintergrundfarbe, siehe
# `_eigenes_qss_anwenden`), übernahm Qts Stylesheet-Stil ihre Maße und
# gab ihr die 2 px Rahmenbreite der Regel dauerhaft mit – auch wenn sie
# gar nicht ausgewählt war. Ein `Label` rückte seinen Text dadurch um
# 5 px nach rechts, eine `StringGrid` verlor ringsum 2 px: im Designer,
# nicht im Programm (M11, Abschnitt 3).
_RAHMEN_DICKE = 2
_RAHMEN_FARBE = "#0067c0"
RASTER = 8

#: Die Rasterpunkte auf dem Formular. Hell genug, um beim Entwerfen
#: nicht zu stören, dunkel genug, um die Fläche überhaupt zu zeigen -
#: `border` aus `design/tokens.json`.
_RASTER_FARBE = "#d0d0d0"

#: Die Kante des Formulars. Dieselbe Farbe, eine Spur kräftiger wäre
#: ein Rahmen, den man für eine Auswahl halten könnte.
_FORMULAR_KANTE = "#b8b8b8"


def _am_raster(wert: int) -> int:
    """Den nächsten Rasterpunkt zu `wert` - nie unter null."""
    return max(0, round(wert / RASTER) * RASTER)


def _groessenwerte(komponente: Any) -> dict[str, int]:
    """Position und Größe einer Komponente - beim Formular nur die
    Größe, denn `left`/`top` gibt es dort nicht."""
    werte = {"width": komponente.width, "height": komponente.height}
    if hasattr(komponente, "left"):
        werte["left"] = komponente.left
        werte["top"] = komponente.top
    return werte



class _RasterFlaeche(QWidget):
    """Zeichnet die Rasterpunkte des Designers."""

    def paintEvent(self, ereignis: Any) -> None:  # noqa: N802 (Qt-Konvention)
        maler = QPainter(self)
        maler.setPen(QColor(_RASTER_FARBE))
        breite, hoehe = self.width(), self.height()
        y = 0
        while y < hoehe:
            x = 0
            while x < breite:
                maler.drawPoint(x, y)
                x += RASTER
            y += RASTER
        # Die Kante des Formulars mitzeichnen: ohne sie endet der Raster
        # irgendwo zwischen zwei Punkten, und das sieht aus wie ein
        # Zufall statt wie ein Rand.
        maler.setPen(QColor(_FORMULAR_KANTE))
        maler.drawRect(0, 0, breite - 1, hoehe - 1)


def _ereignis_kurzname(ereignis_name: str) -> str:
    """Methodenname nutzt `<ereignis>` ohne das `on_`-Präfix des
    Attributnamens (Abschnitt 4.4/9: `on_click` -> `b_ein_click`, nicht
    `b_ein_on_click`, wie in allen Beispielprojekten von Hand benannt)."""
    return ereignis_name.removeprefix("on_")


def _standard_ereignis(typ: type) -> str | None:
    """Das Ereignis, das ein Doppelklick verknüpft (Abschnitt 4.4).

    Gemeint ist das kennzeichnende Ereignis der Komponente: bei
    einem `Edit` die Änderung, bei einem `Zeitgeber` der Takt, bei einem
    `Button` der Klick. Die Maus-Ereignisse aus `Control` zählen dafür
    nicht mit - sie hat seit M15 jede sichtbare Komponente, und mit
    ihnen wäre nichts mehr eindeutig.

    Vorher stand hier schlicht „genau ein Ereignis". Das war dieselbe
    Absicht mit einem Maßstab, der nur so lange trug, wie die meisten
    Komponenten ein einziges Ereignis hatten - mit den Maus-Ereignissen
    lieferte er für jede Komponente `None`, und der Doppelklick im
    Designer legte gar keine Methode mehr an.

    Hat eine Komponente mehrere eigene Ereignisse, muss sie selbst
    sagen, welches gemeint ist - über `standard_ereignis`. Das
    `StringGrid` etwa hat `on_select_cell` und `on_edit_cell`;
    kennzeichnend ist die Auswahl. Sagt sie nichts, bleibt es bei
    `None` (der `DBNavigator` mit Einfügen/Löschen/Speichern/Abbrechen:
    dort wäre jede Wahl geraten).
    """
    alle = ereignisse(typ)
    eigene = [name for name in alle if name not in MAUS_EREIGNISSE]
    genannt = getattr(typ, "standard_ereignis", None)
    if genannt is not None and genannt in alle:
        return genannt
    if len(eigene) == 1:
        return eigene[0]
    if eigene:
        return None
    # Keins außer der Maus: dann ist der Klick gemeint - beim `Label`,
    # beim `Shape`, beim `Panel` und beim `Button`, dessen `on_click`
    # seit M15 ebenfalls aus `Control` kommt.
    return "on_click" if "on_click" in alle else None


def _bildpfade_aus_mime(mime: QMimeData) -> list[Path]:
    """Die abgelegten Bilddateien eines Drag & Drop (Abschnitt 11.4).
    Der Windows-Explorer liefert `text/uri-list` mit `file:`-URLs; alles
    andere (Text, Ordner, Nicht-Bilder) wird ignoriert, damit der
    Designer die Ablage dann gar nicht erst annimmt."""
    if mime is None or not mime.hasUrls():
        return []
    pfade = []
    for url in mime.urls():
        if not url.isLocalFile():
            continue
        pfad = Path(url.toLocalFile())
        if ist_bilddatei(pfad) and pfad.is_file():
            pfade.append(pfad)
    return pfade


def _bildgroesse(pfad: Path) -> tuple[int, int]:
    """Startgröße einer per Drag & Drop erzeugten `Image`-Komponente:
    die echten Bildmaße, auf `_BILD_MAXKANTE` heruntergerechnet. Ein
    nicht lesbares Bild bekommt die Palettengröße aus
    `_STANDARDGROESSEN`."""
    pixmap = QPixmap(str(pfad))
    if pixmap.isNull() or pixmap.width() <= 0 or pixmap.height() <= 0:
        return _STANDARDGROESSEN["Image"]
    breite, hoehe = pixmap.width(), pixmap.height()
    laengste = max(breite, hoehe)
    if laengste > _BILD_MAXKANTE:
        faktor = _BILD_MAXKANTE / laengste
        breite, hoehe = max(1, round(breite * faktor)), max(1, round(hoehe * faktor))
    return breite, hoehe


class _LoeschenKommando:
    def __init__(self, canvas: DesignerCanvas, komponente: Any, name: str | None) -> None:
        self.canvas = canvas
        self.komponente = komponente
        self.name = name

    def tun(self) -> None:
        self.canvas._komponente_entfernen(self.komponente)

    def rueckgaengig(self) -> None:
        if self.name is not None:
            self.canvas._komponente_wiederherstellen(self.name, self.komponente)


class _DuplizierenKommando:
    def __init__(self, canvas: DesignerCanvas, urspruenglich: Any) -> None:
        self.canvas = canvas
        basis = canvas._attributname(urspruenglich) or type(urspruenglich).__name__.lower()
        self.name = canvas._eindeutigen_namen_finden(f"{basis}_kopie")

        self.neue_komponente = type(urspruenglich)(canvas.formular)
        for eigenschaft_name in eigenschaften(type(urspruenglich)):
            setattr(
                self.neue_komponente, eigenschaft_name, getattr(urspruenglich, eigenschaft_name)
            )
        self.neue_komponente.left = urspruenglich.left + RASTER
        self.neue_komponente.top = urspruenglich.top + RASTER

        canvas._ueberwachung_einrichten(self.neue_komponente)
        # sofort wieder lösen: tun() fügt sie (erneut) ein - symmetrisch zu rueckgaengig()
        canvas._komponente_entfernen(self.neue_komponente)

    def tun(self) -> None:
        self.canvas._komponente_wiederherstellen(self.name, self.neue_komponente)

    def rueckgaengig(self) -> None:
        self.canvas._komponente_entfernen(self.neue_komponente)


class _UmbenennenKommando:
    """Benennt das Form-Attribut einer Komponente um (Abschnitt 7.6: die
    Eigenschaft „Name“ ist kein `Prop` der Komponente, sondern der
    Attributname im Formular selbst).

    Die selbst erzeugten Ereignismethoden gehen mit. Wer
    `cb_ausgabe` in `cb_minus` umbenennt, will nicht
    `cb_minus.on_change = self.cb_ausgabe_change` zurückbehalten -
    Lazarus zieht die Handler dort ebenfalls mit. Umbenannt wird nur,
    was Natter selbst angelegt hat, erkennbar am Namen
    `<komponente>_<ereignis>`; einen Namen, den der Schüler selbst
    vergeben hat, fasst niemand an.
    """

    def __init__(self, canvas: DesignerCanvas, komponente: Any, neuer_name: str) -> None:
        self.canvas = canvas
        self.komponente = komponente
        self.neuer_name = neuer_name
        self.alter_name = canvas._attributname(komponente)
        self.umbenannte_methoden = self._selbst_erzeugte_methoden()

    def _selbst_erzeugte_methoden(self) -> list[tuple[str, str, str]]:
        """(Ereignis, alter Methodenname, neuer Methodenname) für jede
        Methode, die Natter selbst angelegt hat."""
        gefunden = []
        for ereignis_name in ereignisse(type(self.komponente)):
            handler = getattr(self.komponente, ereignis_name, None)
            if handler is None:
                continue
            kurz = _ereignis_kurzname(ereignis_name)
            erwartet = f"{self.alter_name}_{kurz}"
            if handler.__name__ == erwartet:
                gefunden.append((ereignis_name, erwartet, f"{self.neuer_name}_{kurz}"))
        return gefunden

    def _methoden_umbenennen(self, rueckwaerts: bool = False) -> None:
        if not self.umbenannte_methoden or self.canvas.unit_pfad is None:
            return
        if not self.canvas.unit_pfad.exists():
            return
        quelltext = self.canvas.unit_pfad.read_text(encoding="utf-8")
        for ereignis_name, alt_name, neu_name in self.umbenannte_methoden:
            von, nach = (neu_name, alt_name) if rueckwaerts else (alt_name, neu_name)
            quelltext, gefunden = handler_methode_umbenennen(quelltext, von, nach)
            if not gefunden:
                continue
            # Der Handler am Objekt zeigt auf die Methode des Formulars;
            # nach dem Umbenennen muss er auf den neuen Namen zeigen,
            # sonst schriebe `pfm_schreiben` den alten in die `.pfm`.
            platzhalter = platzhalter_erzeugen(nach)
            setattr(self.komponente, ereignis_name, types.MethodType(
                platzhalter, self.canvas.formular
            ))
        self.canvas.unit_pfad.write_text(quelltext, encoding="utf-8")

    def tun(self) -> None:
        delattr(self.canvas.formular, self.alter_name)
        setattr(self.canvas.formular, self.neuer_name, self.komponente)
        self._methoden_umbenennen()

    def rueckgaengig(self) -> None:
        delattr(self.canvas.formular, self.neuer_name)
        setattr(self.canvas.formular, self.alter_name, self.komponente)
        self._methoden_umbenennen(rueckwaerts=True)


# Sinnvolle Startgrößen je Komponententyp beim Ablegen aus der Palette
# (wie in Lazarus - dort bekommt z. B. ein frisches TStringGrid ebenfalls
# eine größere Startfläche als ein TCheckBox). Der einheitliche
# `Control`-Standard 75×25 (`pcl/control.py`) passt nur für die
# kompakten Komponenten; bei einer 5×5-StringGrid oder einer
# horizontalen ScrollBar sah er beim Rundgang durch alle Palettentypen
# nur verzerrt/zusammengequetscht aus. Wirkt sich NUR auf das
# interaktive Platzieren aus, nicht auf den `Control.width/height`-Prop-
# Standard selbst (den nutzt z. B. auch generierter `_design.py`-Code).
_STANDARDGROESSEN: dict[str, tuple[int, int]] = {
    "CheckBox": (110, 25),
    "RadioButton": (110, 25),
    "Memo": (180, 90),
    "ListBox": (140, 90),
    "ScrollBar": (150, 17),
    "StringGrid": (220, 150),
    "Image": (100, 100),
    # Eine Zeichenflaeche im Querformat, gross genug zum Zeichnen.
    "PaintBox": (200, 150),
    # Ein Zeitgeber zeigt nur sein Symbol - quadratisch und klein, wie
    # das Entwurfszeit-Symbol einer nicht sichtbaren Komponente in
    # Lazarus. Für die beiden Menüs gilt dasselbe.
    "Timer": (32, 32),
    "MainMenu": (32, 32),
    "PopupMenu": (32, 32),
}


class _BildKommando:
    """Setzt `Image.picture` auf eine Bilddatei und merkt sich den
    vorherigen Pfad (Abschnitt 11.4). `picture` ist kein `Prop`, sondern
    eine aufklappbare Untereigenschaft mit eigener Methode
    (`load_from_file`/`clear`) – deshalb ein eigenes Kommando statt
    `EigenschaftKommando`."""

    def __init__(self, komponente: Any, neuer_pfad: str) -> None:
        self.komponente = komponente
        self._neuer_pfad = neuer_pfad
        self._alter_pfad: str | None = komponente.picture.pfad

    def tun(self) -> None:
        self._anwenden(self._neuer_pfad)

    def rueckgaengig(self) -> None:
        self._anwenden(self._alter_pfad)

    def _anwenden(self, pfad: str | None) -> None:
        if pfad is None:
            self.komponente.picture.clear()
        else:
            self.komponente.picture.load_from_file(pfad)


class _PlatzierenKommando:
    """Wie `_DuplizierenKommando`, aber mit einer frischen Komponente in
    Standardwerten statt einer Kopie (Abschnitt 7.3: Palette → Formular)."""

    def __init__(self, canvas: DesignerCanvas, typ: type, x: int, y: int) -> None:
        self.canvas = canvas
        self.name = canvas._eindeutigen_namen_finden(typ.__name__.lower())

        # Liegt an dieser Stelle ein Behälter, gehört die Komponente
        # hinein - wie in Lazarus, wo ein Knopf über einem Panel dessen
        # Kind wird. `left`/`top` zählen dann ab der linken oberen Ecke
        # des Behälters, nicht ab der des Formulars.
        eltern, ex, ey = canvas._behaelter_bei(x, y)
        self.neue_komponente = typ(eltern)
        # Am Raster einrasten, wie in Lazarus bei „Snap to grid".
        # Ohne das legte der Designer Komponenten auf krumme
        # Koordinaten, und der Design-Prüfer meldete anschließend
        # „steht nicht am 8px-Raster" - für etwas, das der Schüler gar
        # nicht verursacht hat, sondern das Werkzeug selbst (im
        # Durchgang durch den Schuelerweg aufgefallen). Die Pfeiltasten
        # verschieben seit jeher in Rasterschritten; das Ablegen zieht
        # damit nach.
        self.neue_komponente.left = _am_raster(ex)
        self.neue_komponente.top = _am_raster(ey)
        breite, hoehe = _STANDARDGROESSEN.get(typ.__name__, (None, None))
        if breite is not None:
            self.neue_komponente.width = breite
            self.neue_komponente.height = hoehe

        canvas._ueberwachung_einrichten(self.neue_komponente)
        canvas._komponente_entfernen(self.neue_komponente)

    def tun(self) -> None:
        self.canvas._komponente_wiederherstellen(self.name, self.neue_komponente)

    def rueckgaengig(self) -> None:
        self.canvas._komponente_entfernen(self.neue_komponente)


class DesignerCanvas(QObject):
    def __init__(self, formular: Form, pfm_pfad: Path | None = None) -> None:
        super().__init__()
        self.formular = formular
        self.pfm_pfad = Path(pfm_pfad) if pfm_pfad is not None else None
        # Namenskonvention aus Abschnitt 4.1: u_main.pfm <-> u_main.py
        self.unit_pfad = self.pfm_pfad.with_suffix(".py") if self.pfm_pfad is not None else None
        self.kommandos = Kommandostapel()
        self.ausgewaehlte_komponente: Any = None
        self._auswahl_beobachter: list[Callable[[Any], None]] = []
        self._aenderung_beobachter: list[Callable[[], None]] = []
        self._widget_zu_komponente: dict[QWidget, Any] = {}
        self._ziehen_komponente: Any = None
        self._ziehen_start: QPoint | None = None
        self._ziehen_start_werte: dict[str, Any] | None = None
        self._anfasser_widget_zu_name: dict[QWidget, str] = {}
        self._anfasser_ziehen: str | None = None
        self._anfasser_start: QPoint | None = None
        self._anfasser_start_werte: dict[str, int] | None = None
        self._platzierungs_typ: type | None = None
        self._bild_beobachter: list[Callable[[str], None]] = []

        # Drag & Drop einer Bilddatei aus dem Windows-Explorer bzw. dem
        # Projekt-Explorer (Abschnitt 11.4). Nur das Formular-Widget
        # nimmt Ablagen an; Qt reicht die Ereignisse von Kind-Widgets
        # ohne `acceptDrops` dorthin weiter, die Position ist dann
        # bereits in Formular-Koordinaten.
        formular._qwidget.setAcceptDrops(True)
        self._ueberwachung_einrichten(formular)
        self._raster_erzeugen()
        self._rahmen_erzeugen()
        self._anfasser_erzeugen()

    def _ueberwachung_einrichten(self, objekt: Any) -> None:
        widget = objekt._qwidget
        self._widget_zu_komponente[widget] = objekt
        widget.installEventFilter(self)
        # Eine Komponente ohne eigene Anzeige - ein Zeitgeber etwa -
        # versteckt ihr Widget beim Erzeugen, damit sie im fertigen
        # Programm nicht zu sehen ist. Im Designer muss man sie
        # anklicken können, also kommt sie hier zum Vorschein.
        if getattr(type(objekt), "nur_im_designer", False):
            widget.show()
        for _, komponente in kind_komponenten(objekt):
            self._ueberwachung_einrichten(komponente)

    def _raster_erzeugen(self) -> None:
        """Der Punkteraster auf dem Formular - wie in Lazarus.

        Ein frisch angelegtes Formular war im Designer gar nicht zu
        sehen: es ist weiß, die Arbeitsfläche darum war es auch, und
        ohne eine einzige Komponente gab es nichts, woran sich die Kante
        erkennen ließ. Wer ein neues Projekt anlegte, sah eine leere
        weiße Seite und wusste nicht, wohin er etwas ziehen soll.

        Der Raster zeigt beides auf einmal: wo das Formular aufhört und
        in welchen Schritten eine Komponente einrastet (`RASTER`).

        Ein eigenes Kind-Widget statt eines Übermalens: es liegt
        unter allen Komponenten (`lower()`), nimmt keine
        Mausereignisse an - sonst gäbe `childAt` es statt des Formulars
        zurück, und der Klick auf den Hintergrund wählte nichts mehr aus
        - und geht bei jeder Größenänderung einfach mit.
        """
        self._raster_widget = _RasterFlaeche(self.formular._qwidget)
        self._raster_widget.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents
        )
        self._raster_widget.lower()
        self._raster_aktualisieren()

    def _raster_aktualisieren(self) -> None:
        widget = getattr(self, "_raster_widget", None)
        if widget is None:
            return
        widget.setGeometry(self.formular._qwidget.rect())
        widget.lower()
        widget.show()

    def _rahmen_erzeugen(self) -> None:
        """Die vier Streifen des Auswahlrahmens. Sie hängen wie die
        Anfasser am Formular-Widget und nehmen keine Mausereignisse an –
        sonst ließe sich eine Komponente an ihrem eigenen Rand weder
        anklicken noch ziehen."""
        self._rahmen_kanten = []
        for _ in range(4):
            kante = QWidget(self.formular._qwidget)
            kante.setStyleSheet(f"background-color: {_RAHMEN_FARBE};")
            kante.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            kante.hide()
            self._rahmen_kanten.append(kante)

    def _rahmen_aktualisieren(self) -> None:
        komponente = self.ausgewaehlte_komponente
        if komponente is None:
            for kante in self._rahmen_kanten:
                kante.hide()
            return

        if komponente is self.formular:
            # Das Formular selbst hat kein `left`/`top` auf sich selbst;
            # der Rahmen liegt innen an seinen eigenen Kanten.
            links, oben = 0, 0
            breite, hoehe = self.formular._qwidget.width(), self.formular._qwidget.height()
            aussen = 0
        else:
            links, oben = komponente.left, komponente.top
            breite, hoehe = komponente.width, komponente.height
            # Außen herum statt darüber: so verdeckt der Rahmen nichts
            # von der Komponente selbst.
            aussen = _RAHMEN_DICKE

        d = _RAHMEN_DICKE
        x, y = links - aussen, oben - aussen
        b, h = breite + 2 * aussen, hoehe + 2 * aussen
        geometrien = (
            (x, y, b, d),  # oben
            (x, y + h - d, b, d),  # unten
            (x, y, d, h),  # links
            (x + b - d, y, d, h),  # rechts
        )
        for kante, (kx, ky, kb, kh) in zip(self._rahmen_kanten, geometrien, strict=True):
            kante.setGeometry(kx, ky, kb, kh)
            kante.show()
            kante.raise_()

    def _anfasser_erzeugen(self) -> None:
        for name in _ANFASSER_VERHALTEN:
            anfasser = QWidget(self.formular._qwidget)
            anfasser.setFixedSize(_ANFASSER_GROESSE, _ANFASSER_GROESSE)
            anfasser.setStyleSheet(
                f"background-color: {_ANFASSER_FARBE}; border: 1px solid white;"
            )
            anfasser.setCursor(_ANFASSER_CURSOR[name])
            anfasser.hide()
            anfasser.installEventFilter(self)
            self._anfasser_widget_zu_name[anfasser] = name

    def _anfasser_aktualisieren(self) -> None:
        komponente = self.ausgewaehlte_komponente
        if komponente is None:
            for anfasser in self._anfasser_widget_zu_name:
                anfasser.hide()
            return

        ist_formular = komponente is self.formular
        # Das Formular sitzt fest in der linken oberen Ecke und hat kein
        # `left`/`top`; gezogen wird es nur nach rechts und nach unten.
        links = 0 if ist_formular else komponente.left
        oben = 0 if ist_formular else komponente.top
        erlaubt = _ANFASSER_FUER_FORMULAR if ist_formular else tuple(_ANFASSER_VERHALTEN)

        mitte = _ANFASSER_GROESSE // 2
        breite, hoehe = komponente.width, komponente.height
        positionen = {
            "nw": (links, oben),
            "n": (links + breite // 2, oben),
            "ne": (links + breite, oben),
            "e": (links + breite, oben + hoehe // 2),
            "se": (links + breite, oben + hoehe),
            "s": (links + breite // 2, oben + hoehe),
            "sw": (links, oben + hoehe),
            "w": (links, oben + hoehe // 2),
        }
        for anfasser, name in self._anfasser_widget_zu_name.items():
            if name not in erlaubt:
                anfasser.hide()
                continue
            x, y = positionen[name]
            # Am Formular liegen die drei Anfasser innen an der
            # Kante: ein Anfasser, der halb über den Rand hinausragt,
            # wäre außerhalb des Formular-Widgets und damit unsichtbar.
            if ist_formular:
                x = min(x - mitte, breite - _ANFASSER_GROESSE)
                y = min(y - mitte, hoehe - _ANFASSER_GROESSE)
            else:
                x, y = x - mitte, y - mitte
            anfasser.move(x, y)
            anfasser.raise_()
            anfasser.show()
            anfasser.raise_()

    def anfasser_widget(self, name: str) -> QWidget:
        """Das Größenanfasser-Widget an Position `name` (`"nw"`, `"n"`,
        `"ne"`, `"e"`, `"se"`, `"s"`, `"sw"`, `"w"`) – für echte
        `QMouseEvent`s in Tests, sonst intern über `eventFilter`
        angesprochen."""
        return next(w for w, n in self._anfasser_widget_zu_name.items() if n == name)

    # -- Ereignisse -----------------------------------------------------

    def eventFilter(self, beobachtetes_objekt: QObject, ereignis: QEvent) -> bool:
        typ = ereignis.type()

        if typ in (QEvent.Type.DragEnter, QEvent.Type.DragMove):
            if _bildpfade_aus_mime(ereignis.mimeData()):
                ereignis.acceptProposedAction()
                return True
            return False

        if typ == QEvent.Type.Drop:
            pfade = _bildpfade_aus_mime(ereignis.mimeData())
            if not pfade:
                return False
            position = ereignis.position().toPoint()
            for versatz, pfad in enumerate(pfade):
                self.bild_ablegen(
                    pfad,
                    position.x() + versatz * _MEHRFACH_VERSATZ,
                    position.y() + versatz * _MEHRFACH_VERSATZ,
                    # Beim Ablegen mehrerer Dateien auf einmal entsteht
                    # für jede eine eigene Komponente - sonst ersetzte
                    # das zweite Bild das eben erst erzeugte erste,
                    # weil es versetzt genau darauf landet.
                    immer_neu=versatz > 0,
                )
            ereignis.acceptProposedAction()
            return True

        if typ == QEvent.Type.MouseButtonDblClick:
            # Qt schickt vor dem Doppelklick bereits einen normalen Press,
            # der einen Ziehvorgang gestartet haben könnte - den verwerfen.
            self._ziehen_komponente = None
            self._ziehen_start = None
            self._ziehen_start_werte = None
            komponente = self._widget_zu_komponente.get(beobachtetes_objekt)
            if komponente is not None:
                # Ein Menü hat kein Standardereignis - seine Einträge
                # haben jeweils eigene. Der Doppelklick öffnet deshalb
                # den Menü-Editor, statt wirkungslos zu verpuffen.
                if not self.menue_bearbeiten(komponente):
                    self.ereignis_handler_erzeugen(komponente)
            return True

        if typ == QEvent.Type.MouseButtonPress and self._platzierungs_typ is not None:
            self._platzierung_bei_klick_ausfuehren(beobachtetes_objekt, ereignis)
            return True

        if typ == QEvent.Type.MouseButtonPress:
            anfasser_name = self._anfasser_widget_zu_name.get(beobachtetes_objekt)
            if anfasser_name is not None:
                komponente = self.ausgewaehlte_komponente
                self._anfasser_ziehen = anfasser_name
                self._anfasser_start = ereignis.globalPosition().toPoint()
                self._anfasser_start_werte = _groessenwerte(komponente)
                return True

            komponente = self._widget_zu_komponente.get(beobachtetes_objekt)
            if komponente is not None:
                self._auswaehlen(komponente)
                if komponente is not self.formular:
                    self._ziehen_komponente = komponente
                    self._ziehen_start = ereignis.globalPosition().toPoint()
                    self._ziehen_start_werte = {"left": komponente.left, "top": komponente.top}
                return True  # Klick abfangen: keine echte Interaktion im Designer

        elif typ == QEvent.Type.MouseMove and self._anfasser_ziehen is not None:
            self._anfasser_ziehen_verarbeiten(ereignis)
            return True

        elif typ == QEvent.Type.MouseMove and self._ziehen_komponente is not None:
            aktuell = ereignis.globalPosition().toPoint()
            delta = aktuell - self._ziehen_start
            if delta.x() or delta.y():
                # Live-Vorschau während des Ziehens, noch kein Kommando
                self._ziehen_komponente.left += delta.x()
                self._ziehen_komponente.top += delta.y()
                self._ziehen_start = aktuell
                self._anfasser_aktualisieren()
                self._rahmen_aktualisieren()
            return True

        elif typ == QEvent.Type.MouseButtonRelease and self._anfasser_ziehen is not None:
            self._anfasser_ziehen_beenden()
            return True

        elif typ == QEvent.Type.MouseButtonRelease and self._ziehen_komponente is not None:
            self._ziehen_beenden()
            return True

        elif typ == QEvent.Type.KeyPress and self._tastatur_verarbeiten(ereignis):
            return True

        elif typ == QEvent.Type.ContextMenu:
            komponente = self._widget_zu_komponente.get(beobachtetes_objekt)
            if komponente is None:
                return False
            self._auswaehlen(komponente)
            menue = self.kontextmenue_fuer(komponente)
            menue.exec(ereignis.globalPos())
            return True

        return False

    def kontextmenue_fuer(self, komponente: Any) -> QMenu:
        """Das Menü zur rechten Maustaste auf `komponente`
        (M11, Abschnitt 3).

        Die drei Dinge gab es alle schon – aber nur über Tasten (Entf,
        Strg+D) oder einen Doppelklick. Wer sie nicht kennt, probiert
        die rechte Maustaste; in Lazarus liegt dort das Menü zu einer
        Komponente. Die Tastenkürzel stehen daneben, damit man sie beim
        nächsten Mal direkt benutzt.

        Getrennt vom Anzeigen, damit der Rundlauf in
        `tests/test_ide_funktionspruefung.py` jeden Eintrag auslösen
        kann, ohne ein Menü zu öffnen, das auf einen Klick wartet.
        """
        # Ein `QMenu` ohne Eltern gehört niemandem, Python räumt es samt
        # seiner `QAction`s weg, sobald der Aufrufer nur die Einträge
        # behält („Internal C++ object already deleted“). Beim Öffnen
        # fiel das nie auf, weil `exec()` das Menü so lange am Leben
        # hält - also braucht es ein Eltern-Widget.
        #
        # Das ist bewusst das *Fenster* und nicht das Formular-Widget:
        # das Formular trägt das pcl-Stylesheet des später laufenden
        # Programms (hell, eigene Farben). Ein daran gehängtes Menü erbt
        # das und stand im dunklen IDE-Design hell auf dem Bildschirm
        # (bei der Bildschirmfoto-Prüfung zu M11 aufgefallen). Steht der
        # Designer allein da, ist das Formular selbst das Fenster - dann
        # ändert sich nichts.
        menue = QMenu(self.formular._qwidget.window())
        ereignis_name = _standard_ereignis(type(komponente))
        if ereignis_name is not None and self.unit_pfad is not None:
            kurz = _ereignis_kurzname(ereignis_name)
            eintrag = menue.addAction(f"Methode für „{kurz}“ anlegen")
            eintrag.triggered.connect(
                lambda *_, k=komponente: self.ereignis_handler_erzeugen(k)
            )
            menue.addSeparator()

        ist_formular = komponente is self.formular
        doppeln = menue.addAction("Duplizieren\tStrg+D")
        doppeln.setEnabled(not ist_formular)
        doppeln.triggered.connect(lambda *_, k=komponente: self.duplizieren(k))

        loeschen = menue.addAction("Löschen\tEntf")
        # Das Formular selbst lässt sich nicht löschen - der Eintrag
        # bleibt trotzdem stehen, grau: ein Menü, das je nach Klickort
        # anders aussieht, verwirrt mehr, als es hilft.
        loeschen.setEnabled(not ist_formular)
        loeschen.triggered.connect(lambda *_, k=komponente: self.loeschen(k))

        menue.addSeparator()
        zurueck = menue.addAction("Rückgängig\tStrg+Z")
        zurueck.setEnabled(self.kommandos.kann_rueckgaengig)
        zurueck.triggered.connect(lambda *_: self.rueckgaengig())
        vor = menue.addAction("Wiederholen\tStrg+Y")
        vor.setEnabled(self.kommandos.kann_wiederholen)
        vor.triggered.connect(lambda *_: self.wiederholen())
        return menue

    def _anfasser_ziehen_verarbeiten(self, ereignis: QEvent) -> None:
        aktuell = ereignis.globalPosition().toPoint()
        delta = aktuell - self._anfasser_start
        if not delta.x() and not delta.y():
            return

        komponente = self.ausgewaehlte_komponente
        start = self._anfasser_start_werte
        links_je_dx, breite_je_dx, oben_je_dy, hoehe_je_dy = _ANFASSER_VERHALTEN[
            self._anfasser_ziehen
        ]
        kleinste = (
            _MINDESTGROESSE_FORMULAR if komponente is self.formular else 1
        )
        neu = {
            "width": max(kleinste, start["width"] + breite_je_dx * delta.x()),
            "height": max(kleinste, start["height"] + hoehe_je_dy * delta.y()),
        }
        # `left`/`top` nur, wenn es sie gibt: ein Formular hat keine.
        if "left" in start:
            neu["left"] = start["left"] + links_je_dx * delta.x()
            neu["top"] = start["top"] + oben_je_dy * delta.y()
        for name, wert in neu.items():
            setattr(komponente, name, wert)
        self._raster_aktualisieren()
        self._anfasser_aktualisieren()
        self._rahmen_aktualisieren()

    def _anfasser_ziehen_beenden(self) -> None:
        komponente = self.ausgewaehlte_komponente
        startwerte = self._anfasser_start_werte
        endwerte = _groessenwerte(komponente)

        self._anfasser_ziehen = None
        self._anfasser_start = None
        self._anfasser_start_werte = None

        if endwerte == startwerte:
            return  # keine tatsächliche Größenänderung, kein Kommando nötig

        for name, wert in startwerte.items():
            setattr(komponente, name, wert)
        self.kommandos.ausfuehren(
            EigenschaftKommando(komponente, endwerte, alte_werte=startwerte)
        )
        self._nach_aenderung(komponente)

    def _ziehen_beenden(self) -> None:
        komponente = self._ziehen_komponente
        endwerte = {"left": komponente.left, "top": komponente.top}
        startwerte = self._ziehen_start_werte

        self._ziehen_komponente = None
        self._ziehen_start = None
        self._ziehen_start_werte = None

        if endwerte == startwerte:
            return  # keine tatsächliche Bewegung, kein Kommando nötig

        komponente.left, komponente.top = startwerte["left"], startwerte["top"]
        self.kommandos.ausfuehren(
            EigenschaftKommando(komponente, endwerte, alte_werte=startwerte)
        )
        self._nach_aenderung(komponente)

    def _tastatur_verarbeiten(self, ereignis) -> bool:
        taste = ereignis.key()
        modifikatoren = ereignis.modifiers()

        if taste == Qt.Key.Key_Z and modifikatoren & Qt.KeyboardModifier.ControlModifier:
            if modifikatoren & Qt.KeyboardModifier.ShiftModifier:
                self.wiederholen()
            else:
                self.rueckgaengig()
            return True
        if taste == Qt.Key.Key_Y and modifikatoren & Qt.KeyboardModifier.ControlModifier:
            self.wiederholen()
            return True

        komponente = self.ausgewaehlte_komponente
        if komponente is None or komponente is self.formular:
            return False

        if taste == Qt.Key.Key_Delete:
            self.loeschen()
            return True
        if taste == Qt.Key.Key_F2 and self.menue_bearbeiten(komponente):
            return True
        if taste == Qt.Key.Key_D and modifikatoren & Qt.KeyboardModifier.ControlModifier:
            self.duplizieren()
            return True

        richtung = {
            Qt.Key.Key_Left: (-1, 0),
            Qt.Key.Key_Right: (1, 0),
            Qt.Key.Key_Up: (0, -1),
            Qt.Key.Key_Down: (0, 1),
        }.get(taste)
        if richtung is None:
            return False

        dx, dy = richtung
        if modifikatoren & Qt.KeyboardModifier.ShiftModifier:
            self.groesse_aendern(dx * RASTER, dy * RASTER)
        elif modifikatoren & Qt.KeyboardModifier.AltModifier:
            self.verschieben(dx, dy)
        else:
            self.verschieben(dx * RASTER, dy * RASTER)
        return True

    # -- Undo/Redo ----------------------------------------------------------

    def rueckgaengig(self) -> None:
        """Real gefunden: beide Richtungen meldeten die Änderung nur an
        die Beobachter, schrieben sie aber nicht zurück. Der Designer
        zeigte nach Strg+Z also den zurückgenommenen Stand, `.pfm` und
        `u_*_design.py` behielten den zurückgenommenen Schritt trotzdem -
        das Programm lief weiter mit der rückgängig gemachten Änderung."""
        self.kommandos.rueckgaengig()
        self._nach_aenderung(self.ausgewaehlte_komponente or self.formular)

    def wiederholen(self) -> None:
        self.kommandos.wiederholen()
        self._nach_aenderung(self.ausgewaehlte_komponente or self.formular)

    # -- Auswahl ----------------------------------------------------------

    def _behaelter_bei(self, x: int, y: int) -> tuple[Any, int, int]:
        """Wohin eine bei Formular-Koordinaten (x, y) abgelegte
        Komponente gehört: `(Eltern, x, y)`, die Koordinaten umgerechnet
        auf die Eltern.

        Gesucht wird der innerste Behälter an dieser Stelle – ein
        Panel in einer GroupBox nimmt die Komponente auf, nicht die
        GroupBox darum. Liegt dort keiner, bleibt es beim Formular.

        Der Auswahlrahmen und die Anfasser liegen als eigene Widgets auf
        dem Formular und würden `childAt` beantworten, obwohl sie keine
        Komponenten sind; sie stehen nicht in `_widget_zu_komponente`
        und fallen deshalb von selbst heraus.
        """
        widget = self.formular._qwidget.childAt(x, y)
        while widget is not None and widget is not self.formular._qwidget:
            komponente = self._widget_zu_komponente.get(widget)
            if komponente is not None and getattr(type(komponente), "ist_behaelter", False):
                # `mapFrom` statt einer Subtraktion von `left`/`top`:
                # bei einem Behälter im Behälter stimmt die Differenz
                # sonst nur eine Ebene tief.
                punkt = widget.mapFrom(self.formular._qwidget, QPoint(x, y))
                return komponente, punkt.x(), punkt.y()
            widget = widget.parentWidget()
        return self.formular, x, y

    def klick_bei(self, x: int, y: int) -> Any:
        """Findet die Komponente an Formular-Koordinaten (x, y) – für
        Klicks auf den Formular-Hintergrund (kein Kind-Widget dort) und
        für Tests, ohne echte Mausereignisse zu erzeugen."""
        ziel_widget = self.formular._qwidget.childAt(x, y) or self.formular._qwidget
        komponente = self._widget_zu_komponente.get(ziel_widget)
        if komponente is not None:
            self._auswaehlen(komponente)
        return komponente

    def auswahl_beobachten(self, beobachter: Callable[[Any], None]) -> None:
        self._auswahl_beobachter.append(beobachter)

    def aenderung_beobachten(self, beobachter: Callable[[], None]) -> None:
        """Registriert `beobachter`, aufgerufen nach jeder in die `.pfm`
        zurückgeschriebenen Änderung (Abschnitt 14: „automatisch beim
        Speichern eines Formulars“ – hier gibt es keine eigene
        Speichern-Aktion, jede Änderung schreibt sofort zurück)."""
        self._aenderung_beobachter.append(beobachter)

    def _auswaehlen(self, komponente: Any) -> None:
        self.ausgewaehlte_komponente = komponente
        self._benachrichtigen(komponente)

    # -- Bearbeiten ---------------------------------------------------------

    def verschieben(self, dx: int, dy: int, komponente: Any = None) -> None:
        ziel = komponente if komponente is not None else self.ausgewaehlte_komponente
        self.kommandos.ausfuehren(
            EigenschaftKommando(ziel, {"left": ziel.left + dx, "top": ziel.top + dy})
        )
        self._nach_aenderung(ziel)

    def groesse_aendern(self, dw: int, dh: int, komponente: Any = None) -> None:
        ziel = komponente if komponente is not None else self.ausgewaehlte_komponente
        self.kommandos.ausfuehren(
            EigenschaftKommando(
                ziel,
                {"width": max(1, ziel.width + dw), "height": max(1, ziel.height + dh)},
            )
        )
        self._nach_aenderung(ziel)

    def loeschen(self, komponente: Any = None) -> None:
        ziel = komponente if komponente is not None else self.ausgewaehlte_komponente
        if ziel is None or ziel is self.formular:
            return
        name = self._attributname(ziel)
        self.kommandos.ausfuehren(_LoeschenKommando(self, ziel, name))
        self._nach_aenderung(self.formular)

    def duplizieren(self, komponente: Any = None) -> Any:
        ziel = komponente if komponente is not None else self.ausgewaehlte_komponente
        if ziel is None or ziel is self.formular:
            return None
        kommando = _DuplizierenKommando(self, ziel)
        self.kommandos.ausfuehren(kommando)
        self._nach_aenderung(kommando.neue_komponente)
        return kommando.neue_komponente

    def komponente_platzieren(self, typ: type, x: int, y: int) -> Any:
        """Platziert eine neue Komponente aus der Palette an Formular-
        Koordinaten (x, y) (Abschnitt 7.3). `tun()` des Kommandos wählt
        sie über `_komponente_wiederherstellen()` bereits aus."""
        kommando = _PlatzierenKommando(self, typ, x, y)
        self.kommandos.ausfuehren(kommando)
        self._nach_aenderung(kommando.neue_komponente)
        return kommando.neue_komponente

    def bild_beobachten(self, beobachter: Callable[[str], None]) -> None:
        """Meldet nach jedem abgelegten Bild den projektrelativen Pfad
        (`"assets/cookie.png"`) – das Hauptfenster zeigt ihn in der
        Statuszeile an."""
        self._bild_beobachter.append(beobachter)

    def bild_ablegen(self, bild_pfad: Path, x: int, y: int, *, immer_neu: bool = False) -> Any:
        """Drag & Drop einer Bilddatei ins Formular (Abschnitt 11.4):
        legt sie als Kopie in `assets/` des Projekts ab und zeigt sie an.

        Liegt an (x, y) bereits eine `Image`-Komponente, bekommt diese
        das neue Bild (rückgängig machbar); sonst entsteht dort eine neue
        `Image`-Komponente in der Größe des Bildes (auf
        `_BILD_MAXKANTE` begrenzt). `immer_neu=True` erzwingt eine neue
        Komponente, auch wenn dort schon ein Bild liegt.

        Bewusst dokumentiert: die `.pfm` kennt die Eigenschaft
        `picture` noch nicht – sie ist kein `Prop`, sondern eine
        aufklappbare Untereigenschaft mit eigener Lademethode, und ein
        neuer `.pfm`-Eigenschaftsname wäre eine Formatänderung samt
        Schema (siehe AGENTS.md, „Schnittstellen zuerst“). Die
        `Image`-Komponente selbst samt Lage und Größe wird gespeichert,
        das Bild lädt der Kurs mit
        ``self.i_bild.picture.load_from_file("assets/…")``."""
        bild_pfad = Path(bild_pfad)
        if self.pfm_pfad is not None:
            absoluter_pfad, relativer_pfad = bild_in_assets_uebernehmen(
                bild_pfad, self.pfm_pfad.parent
            )
        else:
            absoluter_pfad, relativer_pfad = bild_pfad.resolve(), bild_pfad.name

        ziel = None if immer_neu else self._komponente_an_position(x, y)
        if isinstance(ziel, Image):
            self.kommandos.ausfuehren(_BildKommando(ziel, str(absoluter_pfad)))
            self._nach_aenderung(ziel)
        else:
            ziel = self.komponente_platzieren(Image, x, y)
            breite, hoehe = _bildgroesse(absoluter_pfad)
            ziel.width, ziel.height = breite, hoehe
            ziel.picture.load_from_file(str(absoluter_pfad))
            self._nach_aenderung(ziel)

        for beobachter in self._bild_beobachter:
            beobachter(relativer_pfad)
        return ziel

    def _komponente_an_position(self, x: int, y: int) -> Any:
        """Die Komponente unter (x, y) in Formular-Koordinaten, oder das
        Formular selbst. Größenanfasser zählen nicht mit – sie liegen
        über der Auswahl und sind keine Komponenten."""
        widget = self.formular._qwidget.childAt(QPoint(x, y))
        while widget is not None and widget is not self.formular._qwidget:
            if widget in self._anfasser_widget_zu_name:
                return self.formular
            komponente = self._widget_zu_komponente.get(widget)
            if komponente is not None:
                return komponente
            widget = widget.parentWidget()
        return self.formular

    def platzierungsmodus_setzen(self, typ: type | None) -> None:
        """„Klick auf ein Palettensymbol, dann Klick auf das Formular“
        (Abschnitt 7.3, wie in Lazarus) – Ergänzung zum bisherigen
        Doppelklick (der immer mittig platziert). `typ=None` bricht den
        Modus ab (z. B. Escape). Der nächste Klick auf das Formular oder
        eine seiner Komponenten platziert `typ` genau dort und beendet
        den Modus wieder automatisch (kein „Anheften“, wie in Lazarus'
        einfachem Modus ohne Reißnadel-Symbol)."""
        self._platzierungs_typ = typ
        cursor = Qt.CursorShape.CrossCursor if typ is not None else Qt.CursorShape.ArrowCursor
        self.formular._qwidget.setCursor(cursor)

    def _platzierung_bei_klick_ausfuehren(
        self, beobachtetes_objekt: QObject, ereignis: Any
    ) -> None:
        typ = self._platzierungs_typ
        self.platzierungsmodus_setzen(None)
        if typ is None:
            return

        position = ereignis.position().toPoint()
        komponente = self._widget_zu_komponente.get(beobachtetes_objekt)
        if komponente is not None and komponente is not self.formular:
            x, y = komponente.left + position.x(), komponente.top + position.y()
        else:
            x, y = position.x(), position.y()

        self.komponente_platzieren(typ, x, y)

    def eigenschaft_uebernehmen(
        self, komponente: Any, name: str, alter_wert: Any, neuer_wert: Any
    ) -> None:
        """Übernimmt eine im Objektinspektor bereits live gesetzte
        Eigenschaft: Undo-Eintrag anlegen und `.pfm` samt generiertem Code
        neu schreiben.

        Real gefunden: der Objektinspektor setzte den Wert nur am
        Live-Objekt. Die Anzeige im Designer stimmte damit sofort (und
        jeder Screenshot sah richtig aus), aber weder die `.pfm` noch
        `u_*_design.py` erfuhren je davon - jede allein über den
        Inspektor gesetzte Eigenschaft war nach dem nächsten Öffnen
        wieder weg und erreichte das laufende Programm nie."""
        self.kommandos.ausfuehren(
            EigenschaftKommando(komponente, {name: neuer_wert}, {name: alter_wert})
        )
        self._nach_aenderung(komponente)

    def komponente_umbenennen(self, komponente: Any, neuer_name: str) -> None:
        """Ändert den Namen (Form-Attribut) von `komponente` – die
        Eigenschaft „Name“ im Objektinspektor (Abschnitt 7.6). Löst
        `ValueError` bei ungültigem Bezeichner oder bereits vergebenem
        Namen aus."""
        if komponente is self.formular:
            raise ValueError("Das Formular selbst kann nicht umbenannt werden.")
        if not neuer_name.isidentifier():
            raise ValueError(f"{neuer_name!r} ist kein gültiger Bezeichner.")

        alter_name = self._attributname(komponente)
        if neuer_name == alter_name:
            return
        if neuer_name in vars(self.formular):
            raise ValueError(f"Der Name {neuer_name!r} wird bereits verwendet.")

        kommando = _UmbenennenKommando(self, komponente, neuer_name)
        self.kommandos.ausfuehren(kommando)
        self._nach_aenderung(komponente)

    def menue_bearbeiten(self, komponente: Any) -> bool:
        """Öffnet den Menü-Editor für `komponente`, wenn sie ein Menü
        ist. Liefert `True`, wenn sie eines war – sonst `False`, damit
        der Aufrufer wie bisher weitermachen kann.

        Erreichbar per Doppelklick auf das Symbol, per F2 und über die
        Zeile `entries` im Objektinspektor. Drei Wege zur selben Sache,
        aber alle drei öffnen denselben Dialog – anders als bei dem
        Fall aus M11, wo zwei Wege zu derselben Funktion sich
        unterschiedlich verhielten.

        Ein Dialogdurchgang ist ein Undo-Schritt: das ganze
        Ergebnis geht als ein `EigenschaftKommando` auf den Stapel,
        egal wie viele Einträge darin geändert wurden.
        """
        if not hasattr(type(komponente), "entries"):
            return False

        from ide.inspector.menue_editor import MenueEditor

        dialog = MenueEditor(komponente.entries, self.formular._qwidget.window())
        # Gegen `QDialog.DialogCode` und nicht gegen `MenueEditor`
        # selbst: so lässt sich der Dialog in einem Test durch einen
        # Platzhalter ersetzen, ohne dass hier etwas fehlt.
        angenommen = dialog.exec() == QDialog.DialogCode.Accepted
        if not angenommen and not dialog.uebernommen:
            return True
        self.kommandos.ausfuehren(EigenschaftKommando(komponente, {"entries": dialog.eintraege()}))
        self._nach_aenderung(komponente)
        return True

    def ereignis_handler_erzeugen(self, komponente: Any) -> str | None:
        """Doppelklick auf `komponente` (Abschnitt 4.4): erzeugt bei
        Bedarf die Standard-Ereignis-Methode in der Formular-Unit (per
        `libcst`, ohne Formatierungsverlust) und verknüpft sie. Ohne
        zugrunde liegende `.pfm`-Datei oder ohne eindeutiges Standard-
        ereignis passiert nichts (`None`). Bereits verknüpfte Ereignisse
        werden nicht erneut erzeugt, nur der vorhandene Name geliefert."""
        if self.unit_pfad is None:
            return None
        ereignis_name = _standard_ereignis(type(komponente))
        if ereignis_name is None:
            return None

        vorhandener_handler = getattr(komponente, ereignis_name)
        if vorhandener_handler is not None:
            return vorhandener_handler.__name__

        if komponente is self.formular:
            # das Formular selbst heißt im generierten Code nicht nach der
            # Klasse, sondern immer "form" (Abschnitt 4.4: form_create)
            komponenten_name = "form"
        else:
            komponenten_name = self._attributname(komponente) or type(komponente).__name__.lower()
        methodenname = f"{komponenten_name}_{_ereignis_kurzname(ereignis_name)}"

        klassenname = type(self.formular).__name__
        quelltext = self.unit_pfad.read_text(encoding="utf-8")
        neuer_quelltext = handler_methode_einfuegen(
            quelltext,
            klassenname,
            methodenname,
            EREIGNIS_PARAMETER.get(ereignis_name, ()),
        )
        self.unit_pfad.write_text(neuer_quelltext, encoding="utf-8")

        gebundene_methode = types.MethodType(platzhalter_erzeugen(methodenname), self.formular)
        setattr(self.formular, methodenname, gebundene_methode)

        self.kommandos.ausfuehren(
            EigenschaftKommando(komponente, {ereignis_name: gebundene_methode})
        )
        self._nach_aenderung(komponente)
        return methodenname

    # -- Struktur-Hilfsmethoden (auch von den Kommandos oben genutzt) -------

    def _komponente_entfernen(self, komponente: Any) -> None:
        name = self._attributname(komponente)
        if name is not None:
            delattr(self.formular, name)
        self._widget_zu_komponente.pop(komponente._qwidget, None)
        komponente._qwidget.hide()
        komponente._qwidget.setParent(None)
        if self.ausgewaehlte_komponente is komponente:
            self.ausgewaehlte_komponente = None
            self._auswaehlen(self.formular)

    def _komponente_wiederherstellen(self, name: str, komponente: Any) -> None:
        # Zurück an die eigenen Eltern, nicht pauschal ans Formular:
        # sonst sprang eine rückgängig gemachte Löschung aus ihrem Panel
        # heraus und lag danach auf dem Formular, an einer Stelle, die
        # sich aus Panel-Koordinaten ergab.
        eltern = komponente.eltern if komponente.eltern is not None else self.formular
        komponente._qwidget.setParent(eltern._qwidget)
        komponente._qwidget.show()
        setattr(self.formular, name, komponente)
        self._widget_zu_komponente[komponente._qwidget] = komponente
        self._auswaehlen(komponente)

    def name_von(self, komponente: Any) -> str | None:
        """Der Name (Formular-Attribut) von `komponente`, z. B.
        `"b_anmelden"` – für den Objektinspektor (Abschnitt 7.6), der
        `caption`/`text` (Anzeigetext) und `name` (Bezeichner im Code)
        auseinanderhält, wie in Lazarus."""
        return self._attributname(komponente)

    def _attributname(self, komponente: Any) -> str | None:
        for name, wert in vars(self.formular).items():
            if wert is komponente:
                return name
        return None

    def _eindeutigen_namen_finden(self, basis: str) -> str:
        name = basis
        vorhandene = set(vars(self.formular))
        zaehler = 2
        while name in vorhandene:
            name = f"{basis}{zaehler}"
            zaehler += 1
        return name

    def _benachrichtigen(self, komponente: Any) -> None:
        self._anfasser_aktualisieren()
        self._rahmen_aktualisieren()
        for beobachter in self._auswahl_beobachter:
            beobachter(komponente)

    def _nach_aenderung(self, komponente: Any) -> None:
        if self.pfm_pfad is not None:
            formular_als_pfm_speichern(self.formular, self.pfm_pfad)
            # Real gefunden (beim Nachbauen eines Referenzprojekts):
            # ohne dies blieb `u_..._design.py` nach der ersten
            # Projekterzeugung für immer auf dem allerersten Stand
            # stehen - der Designer selbst zeigte jede Änderung korrekt
            # (er rendert direkt aus dem Live-Formular), aber das
            # tatsächlich laufende Schülerprogramm (`create_components()`
            # in der generierten Design-Datei) sah neue/verschobene/
            # geänderte Komponenten nie.
            design_datei_erzeugen(self.pfm_pfad, self._design_pfad())
        self._benachrichtigen(komponente)
        for beobachter in self._aenderung_beobachter:
            beobachter()

    def _design_pfad(self) -> Path:
        """`u_main.pfm` -> `u_main_design.py` (Namenskonvention aus
        `ide/project/neu.py`)."""
        return self.pfm_pfad.parent / f"{self.pfm_pfad.stem}_design.py"
