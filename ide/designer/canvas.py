"""DesignerCanvas: zeigt ein Formular mit echten `pcl`-Komponenten,
Klick/Ziehen/Tastatur bearbeiten es statt die echte Interaktion
auszulösen. Jede Änderung läuft über ein Kommando (Undo/Redo).

Siehe README.md, Abschnitt 7.7: „Der Designer rendert echte
pcl-Komponenten“, Tastenkürzel wie dort beschrieben (Pfeiltasten =
Rasterschritt, Alt+Pfeil = 1 px, Umschalt+Pfeil = Größe, Entf = löschen,
Strg+D = duplizieren, dazu Strg+Z/Strg+Umschalt+Z bzw. Strg+Y für
Rückgängig/Wiederholen, Command-Pattern). `komponente_platzieren()` ist
das Gegenstück für die Komponentenpalette (Abschnitt 7.3). Acht sichtbare
Größenanfasser an der ausgewählten Komponente lassen
sich zusätzlich zur Tastatur mit der Maus ziehen (`_Anfasser`,
`_ANFASSER_VERHALTEN`).

`ide.codegen.ereignis` wird erst dort importiert, wo es gebraucht wird,
und nicht am Kopf: es zieht `libcst` nach sich, und das kostet beim
Start der IDE 130 Millisekunden - für eine Bibliothek, die erst beim
Doppelklick auf eine Komponente etwas zu tun bekommt.
"""

from __future__ import annotations

import json
import keyword
import os
import re
import time
import types
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import (
    QEvent,
    QMimeData,
    QObject,
    QPoint,
    QPointF,
    QRect,
    Qt,
    QTimer,
)
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QRubberBand,
    QWidget,
)

from ide import dateistand
from ide.atomar import atomar_schreiben
from ide.codegen.design import (
    PfmBeschaedigt,
    design_datei_erzeugen,
    pfm_pruefen,
)
from ide.designer.bilder import bild_in_assets_uebernehmen, ist_bilddatei
from ide.designer.kommando import EigenschaftKommando, Kommandostapel
from ide.designer.laden import (
    methoden_im_quelltext,
    platzhalter_erzeugen,
    unit_lesen,
)
from ide.designer.pfm_schreiben import formular_als_pfm_speichern
from ide.inspector.komponentenbaum import kind_komponenten
from ide.schema import fehler_beschreiben, schema_fehler
from pcl.components.additional import Image
from pcl.control import ALLGEMEINE_EREIGNISSE, EREIGNIS_PARAMETER, Control
from pcl.form import Form
from pcl.properties import VERWEIS_EIGENSCHAFTEN, ereignisse

#: Beim Ablegen mehrerer Bilder auf einmal werden die neuen Komponenten
#: leicht versetzt, damit sie sich nicht vollständig überdecken.
_MEHRFACH_VERSATZ = 16

#: Größte Kantenlänge einer per Drag & Drop erzeugten `Image`-Komponente;
#: ein 2500×2500-Foto (wie in `tests/daten/lfm/l_Pet`) soll das Formular
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
# ausgewählten Komponente liegen – wie die acht Größenanfasser.
# Früher stand er als QSS-Regel
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


#: Die Rasterweiten, die das Kontextmenü des Designers anbietet.
RASTER_WEITEN = (4, 8, 16)

#: So lange wartet der Designer nach einer Änderung, bevor er `.pfm`
#: und `_design.py` schreibt und die Beobachter (Design-Prüfung,
#: Komponentenbaum) benachrichtigt. Jede weitere Änderung in dieser
#: Zeit schiebt den Zeitpunkt hinaus; wer eine Pfeiltaste gedrückt
#: hält, löst am Ende einen einzigen Schreibvorgang aus (Punkt 312).
SCHREIB_VERZOEGERUNG_MS = 400


def _am_raster(wert: int, raster: int = RASTER) -> int:
    """Den nächsten Rasterpunkt zu `wert` - nie unter null."""
    return max(0, round(wert / raster) * raster)


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

    raster = RASTER

    def paintEvent(self, ereignis: Any) -> None:  # noqa: N802 (Qt-Konvention)
        maler = QPainter(self)
        maler.setPen(QColor(_RASTER_FARBE))
        breite, hoehe = self.width(), self.height()
        y = 0
        while y < hoehe:
            x = 0
            while x < breite:
                maler.drawPoint(x, y)
                x += self.raster
            y += self.raster
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
    eigene = [name for name in alle if name not in ALLGEMEINE_EREIGNISSE]
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
    from pcl.bilddatei import bild_laden

    pixmap = bild_laden(pfad)
    if pixmap.isNull() or pixmap.width() <= 0 or pixmap.height() <= 0:
        return _STANDARDGROESSEN["Image"]
    breite, hoehe = pixmap.width(), pixmap.height()
    laengste = max(breite, hoehe)
    if laengste > _BILD_MAXKANTE:
        faktor = _BILD_MAXKANTE / laengste
        breite, hoehe = max(1, round(breite * faktor)), max(1, round(hoehe * faktor))
    return breite, hoehe


def _inhalt(objekt: Any) -> list[tuple[str, Any]]:
    """Alle Komponenten in einem Behälter, auch verschachtelte."""
    ergebnis = []
    for name, kind in kind_komponenten(objekt):
        ergebnis.append((name, kind))
        ergebnis.extend(_inhalt(kind))
    return ergebnis


class _LoeschenKommando:
    """Löscht eine Komponente. Bei einem Behälter gehen die Namen seines
    Inhalts mit (Punkt 109): sie standen bis 0.3.5 weiter als Attribute
    am Formular, und ein neuer Knopf bekam deshalb `b_innen2` statt des
    frei gewordenen `b_innen`.

    Die Reihenfolge der Attribute merkt es sich (Punkt 170): sie ist
    die Tab-Reihenfolge im Programm. Beim Zurückholen hängte `setattr`
    die Komponente ans Ende, und aus `b_1, b_2, b_3` wurde nach Löschen
    und Rückgängig `b_2, b_3, b_1`."""

    def __init__(self, canvas: DesignerCanvas, komponente: Any, name: str | None) -> None:
        self.canvas = canvas
        self.komponente = komponente
        self.name = name
        self.inhalt = _inhalt(komponente)
        self.reihenfolge: list[str] = []

    def tun(self) -> None:
        self.reihenfolge = list(vars(self.canvas.formular))
        self.canvas._komponente_entfernen(self.komponente)
        for name, _ in self.inhalt:
            if hasattr(self.canvas.formular, name):
                delattr(self.canvas.formular, name)

    def rueckgaengig(self) -> None:
        if self.name is not None:
            self.canvas._komponente_wiederherstellen(self.name, self.komponente)
        for name, kind in self.inhalt:
            setattr(self.canvas.formular, name, kind)
            self.canvas._widget_zu_komponente[kind._qwidget] = kind
        vorhanden = vars(self.canvas.formular)
        attribute_ordnen(
            self.canvas.formular, [n for n in self.reihenfolge if n in vorhanden]
        )


def attribute_ordnen(objekt: Any, namen: list[str]) -> None:
    """Bringt die Attribute `namen` von `objekt` in diese Reihenfolge.

    Die Reihenfolge der Komponenten in der `.pfm` und damit die
    Tab-Reihenfolge im laufenden Programm ist die Reihenfolge, in der
    sie als Attribute am Formular stehen (`kind_komponenten`). Die
    genannten Attribute rücken zusammen an die Stelle des ersten von
    ihnen, alle übrigen bleiben, wo sie waren.
    """
    daten = vars(objekt)
    gesucht = set(namen)
    neu: dict[str, Any] = {}
    for name, wert in daten.items():
        if name not in gesucht:
            neu[name] = wert
        elif not any(n in neu for n in gesucht):
            for eingereiht in namen:
                neu[eingereiht] = daten[eingereiht]
    daten.clear()
    daten.update(neu)


class _UmhaengenKommando:
    """Hängt eine Komponente in einen anderen Behälter (Punkt 72):
    in ein Panel hinein, aus ihm heraus oder von einem in ein anderes.
    `left`/`top` gelten danach ab der Ecke des neuen Behälters."""

    def __init__(
        self,
        canvas: DesignerCanvas,
        komponente: Any,
        neue_eltern: Any,
        neue_lage: tuple[int, int],
        alte_lage: tuple[int, int],
    ) -> None:
        self.canvas = canvas
        self.komponente = komponente
        self.alte_eltern = komponente.eltern or canvas.formular
        self.neue_eltern = neue_eltern
        self.neue_lage = neue_lage
        self.alte_lage = alte_lage

    def _setzen(self, eltern: Any, lage: tuple[int, int]) -> None:
        k = self.komponente
        # `eltern` ist in pcl nur lesbar: gesetzt wird es beim Anlegen.
        # Der Designer ist die einzige Stelle, die es später ändert.
        k._eltern = eltern
        k._qwidget.setParent(eltern._qwidget)
        k.left, k.top = lage
        k._qwidget.show()
        k._qwidget.raise_()

    def tun(self) -> None:
        self._setzen(self.neue_eltern, self.neue_lage)

    def rueckgaengig(self) -> None:
        self._setzen(self.alte_eltern, self.alte_lage)


#: Format der Zwischenablage für Komponenten: eine Liste von Einträgen,
#: wie sie in `children` einer `.pfm` stehen.
ZWISCHENABLAGE_TYP = "application/x-natter-komponenten"


def _ereignisse_entfernen(eintrag: dict[str, Any]) -> None:
    eintrag.pop("events", None)
    for kind in eintrag.get("children", []):
        _ereignisse_entfernen(kind)


def _ereignisse_sammeln(
    eintraege: list[dict[str, Any]], gesammelt: dict[str, dict[str, str]] | None = None
) -> dict[str, dict[str, str]]:
    """Name des Eintrags -> seine `events`, auch aus Behältern."""
    gesammelt = {} if gesammelt is None else gesammelt
    for eintrag in eintraege:
        if eintrag.get("events"):
            gesammelt[eintrag["name"]] = dict(eintrag["events"])
        _ereignisse_sammeln(eintrag.get("children", []), gesammelt)
    return gesammelt


def _namen_in(eintraege: list[dict[str, Any]]) -> set[str]:
    namen: set[str] = set()
    for eintrag in eintraege:
        namen.add(eintrag["name"])
        namen |= _namen_in(eintrag.get("children", []))
    return namen


def _verweise_herausnehmen(
    eintraege: list[dict[str, Any]],
    bekannt: set[str],
    gesammelt: dict[str, dict[str, str]] | None = None,
) -> dict[str, dict[str, str]]:
    """Nimmt Verweise wie `popup_menu` auf Komponenten heraus, die
    nicht mit in den Einträgen stehen, und liefert sie als
    Name des Eintrags -> {Eigenschaft: Name des Ziels}.

    Der Zwischenbau in `_eintraege_bauen` kennt nur die Einträge
    selbst; ein Verweis auf das Klappmenü des Formulars fiele dort
    weg. Er wird danach gegen die Komponenten des Zielformulars
    aufgelöst (Punkt 172)."""
    gesammelt = {} if gesammelt is None else gesammelt
    for eintrag in eintraege:
        eigenschaften_ = eintrag.get("properties", {})
        for name in VERWEIS_EIGENSCHAFTEN:
            ziel = eigenschaften_.get(name)
            if ziel and ziel not in bekannt:
                gesammelt.setdefault(eintrag["name"], {})[name] = ziel
                del eigenschaften_[name]
        _verweise_herausnehmen(eintrag.get("children", []), bekannt, gesammelt)
    return gesammelt


def _menue_handler_umbenennen(
    eintraege: list[dict[str, Any]], von: str, nach: str
) -> bool:
    """Ersetzt in einem Menübaum `on_click == von` durch `nach`.
    `True`, wenn sich etwas geändert hat."""
    geaendert = False
    for eintrag in eintraege:
        if eintrag.get("on_click") == von:
            eintrag["on_click"] = nach
            geaendert = True
        if _menue_handler_umbenennen(eintrag.get("children", []), von, nach):
            geaendert = True
    return geaendert


#: So lange darf zwischen zwei Pfeiltasten liegen, damit sie zu einem
#: Schritt für Rückgängig zusammengefasst werden (Punkt 487).
_TASTENFOLGE_S = 1.0


class _GruppenKommando:
    """Mehrere Kommandos als ein Schritt - ein Strg+Z nimmt das
    Verschieben oder Löschen einer ganzen Auswahl zurück (Punkt 73)."""

    def __init__(self, kommandos: list[Any]) -> None:
        self.kommandos = kommandos

    def tun(self) -> None:
        for kommando in self.kommandos:
            kommando.tun()

    def rueckgaengig(self) -> None:
        for kommando in reversed(self.kommandos):
            kommando.rueckgaengig()


class _EinfuegenKommando:
    """Fügt Komponenten aus der Zwischenablage ein (Punkt 73).
    `komponenten` sind (Name, Komponente, obenauf) - obenauf heißt: liegt
    unmittelbar im Ziel und nicht in einem mit eingefügten Behälter."""

    def __init__(self, canvas: DesignerCanvas, komponenten: list[tuple[str, Any, bool]]) -> None:
        self.canvas = canvas
        self.komponenten = komponenten

    def tun(self) -> None:
        for name, komponente, obenauf in self.komponenten:
            if obenauf:
                self.canvas._komponente_wiederherstellen(name, komponente)
            else:
                setattr(self.canvas.formular, name, komponente)
                self.canvas._widget_zu_komponente[komponente._qwidget] = komponente

    def rueckgaengig(self) -> None:
        for name, komponente, obenauf in reversed(self.komponenten):
            if obenauf:
                self.canvas._komponente_entfernen(komponente)
            elif hasattr(self.canvas.formular, name):
                delattr(self.canvas.formular, name)


class _ReihenfolgeKommando:
    """Ändert die Reihenfolge der Komponenten in einem Behälter
    (Punkt 61)."""

    def __init__(self, canvas: DesignerCanvas, vorher: list[str], nachher: list[str]) -> None:
        self.canvas = canvas
        self.vorher = vorher
        self.nachher = nachher

    def tun(self) -> None:
        attribute_ordnen(self.canvas.formular, self.nachher)

    def rueckgaengig(self) -> None:
        attribute_ordnen(self.canvas.formular, self.vorher)


def _pfad_schluessel(pfad: str | Path) -> str:
    """Ein Pfad in einer Form, in der zwei Schreibweisen derselben
    Datei gleich sind (Groß- und Kleinschreibung, `..`, Schrägstriche
    unter Windows)."""
    return os.path.normcase(os.path.abspath(str(pfad)))


def _utf16_laenge(text: str) -> int:
    """Länge in den Einheiten, in denen Qt Textpositionen zählt. Ein
    Zeichen außerhalb der Grundebene (etwa ein Emoji) zählt dort
    doppelt."""
    return len(text.encode("utf-16-le")) // 2


def editortext_ersetzen(editor: QPlainTextEdit, text: str) -> None:
    """Ersetzt den Text eines offenen Editors als ein Bearbeitungsschritt
    des Editors: Strg+Z dort holt den alten Text zurück, der Cursor
    bleibt ungefähr, wo er war, und ob der Editor als geändert gilt,
    bleibt, wie es vorher war.

    Ersetzt wird nur der Abschnitt, in dem sich alter und neuer Text
    unterscheiden. Beim Einfügen einer Methode ist das nur die neue
    Methode; der übrige Text und seine Faltungen bleiben unberührt, und
    ältere Schritte im Rückgängig-Verlauf behalten ihren Sinn
    (Punkt 248)."""
    alt = editor.toPlainText()
    if alt == text:
        return
    geaendert = editor.document().isModified()
    stelle = editor.textCursor().position()
    anfang = 0
    grenze = min(len(alt), len(text))
    while anfang < grenze and alt[anfang] == text[anfang]:
        anfang += 1
    ende = 0
    while (
        ende < grenze - anfang
        and alt[len(alt) - 1 - ende] == text[len(text) - 1 - ende]
    ):
        ende += 1
    cursor = QTextCursor(editor.document())
    cursor.setPosition(_utf16_laenge(alt[:anfang]))
    cursor.setPosition(
        _utf16_laenge(alt[: len(alt) - ende]),
        QTextCursor.MoveMode.KeepAnchor,
    )
    # Ein eigener Block, damit Qt den Schritt nicht mit dem zuletzt
    # Getippten zusammenlegt.
    cursor.beginEditBlock()
    cursor.insertText(text[anfang : len(text) - ende])
    cursor.endEditBlock()
    cursor.setPosition(min(stelle, _utf16_laenge(text)))
    editor.setTextCursor(cursor)
    editor.document().setModified(geaendert)


class _UmbenennenKommando:
    """Benennt das Form-Attribut einer Komponente um (Abschnitt 7.6: die
    Eigenschaft „Name“ ist kein `Prop` der Komponente, sondern der
    Attributname im Formular selbst).

    Die selbst erzeugten Ereignismethoden gehen mit. Wer
    `cb_ausgabe` in `cb_minus` umbenennt, will nicht
    `cb_minus.on_change = self.cb_ausgabe_change` zurückbehalten.
    Umbenannt wird nur,
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
        """Benennt die Methoden in der Unit um, auf der Platte und in
        jedem Editor, in dem die Unit gerade offen ist.

        Bis Punkt 114 nur auf der Platte: der Editor zeigte weiter den
        alten Namen, und sein nächstes Speichern schrieb ihn zurück in
        die Datei, während die `.pfm` schon auf den neuen verwies. Das
        Programm brach dann beim Start mit `AttributeError` ab. Ob der
        Editor ungespeicherte Änderungen hat, bleibt dabei, wie es war:
        in beiden Fällen stimmen Platte und Editor mit der `.pfm`
        überein.

        Nach dem Umbenennen zeigt jeder Verweis auf die alte Methode auf
        die neue, nicht nur der dieser Komponente (Punkt 147): hängen
        `b_ok` und `b_abbrechen` beide an `b_ok_click`, zeigte
        `b_abbrechen` sonst auf eine Methode, die es nicht mehr gab.

        Eine Unit, die sich nicht übersetzen lässt, bleibt, wie sie
        ist, und die Verweise ebenfalls; so passen beide weiter
        zusammen. Vor dem ersten Umbenennen prüft das schon
        `komponente_umbenennen` (Punkt 141); hier geht es um
        Rückgängig und Wiederholen, nachdem die Unit inzwischen einen
        Fehler bekommen hat."""
        if not self.umbenannte_methoden or self.canvas.unit_pfad is None:
            return
        from ide.codegen.ereignis import handler_methode_umbenennen, syntaxfehler_zeile

        paare = [
            (neu, alt) if rueckwaerts else (alt, neu)
            for _, alt, neu in self.umbenannte_methoden
        ]

        def umbenennen(quelltext: str) -> tuple[str, set[str]]:
            if syntaxfehler_zeile(quelltext) is not None:
                return quelltext, set()
            gefunden_fuer: set[str] = set()
            for von, nach in paare:
                quelltext, gefunden = handler_methode_umbenennen(quelltext, von, nach)
                if gefunden:
                    gefunden_fuer.add(von)
            return quelltext, gefunden_fuer

        umbenannt: set[str] = set()
        try:
            auf_der_platte = unit_lesen(self.canvas.unit_pfad)
        except (OSError, ValueError):
            # Nicht da oder nicht als UTF-8 lesbar: behandelt wie eine
            # Unit mit Syntaxfehler, sie bleibt, wie sie ist.
            auf_der_platte = None
        if auf_der_platte is not None:
            quelltext, umbenannt = umbenennen(auf_der_platte)
            if umbenannt:
                # Ein `OSError` hier (schreibgeschützte Unit, Punkt
                # 255) kommt vor jeder anderen Änderung; `tun` und
                # `rueckgaengig` setzen dann das Formular zurück.
                vorher = dateistand.kennung(self.canvas.unit_pfad)
                atomar_schreiben(self.canvas.unit_pfad, quelltext, encoding="utf-8")
                self.canvas._unit_stand_nachfuehren(vorher)
        for editor in self.canvas._offene_unit_editoren():
            quelltext, gefunden = umbenennen(editor.toPlainText())
            if gefunden:
                editortext_ersetzen(editor, quelltext)
                umbenannt |= gefunden

        for von, nach in paare:
            if von in umbenannt:
                self.canvas._handler_umhaengen(von, nach)

    def _umhaengen(self, von: str, nach: str) -> None:
        """Ersetzt das Attribut `von` durch `nach` an derselben Stelle.
        Bis 0.3.5 rückte eine umbenannte Komponente dabei ans Ende der
        Attribute und damit ans Ende der Tab-Reihenfolge.

        Erst das neue Attribut setzen, dann das alte entfernen: scheitert
        das Setzen (Punkt 113, ein Name wie `caption` ist an der
        Formularklasse ein Prop mit Typprüfung), bleibt die Komponente
        unter ihrem alten Namen am Formular. Umgekehrt war sie danach
        verschwunden, und die nächste Änderung schrieb die `.pfm` ohne
        sie."""
        reihenfolge = [nach if name == von else name for name in vars(self.canvas.formular)]
        setattr(self.canvas.formular, nach, self.komponente)
        delattr(self.canvas.formular, von)
        attribute_ordnen(self.canvas.formular, reihenfolge)

    def tun(self) -> None:
        self._umhaengen(self.alter_name, self.neuer_name)
        try:
            self._methoden_umbenennen()
        except OSError:
            # Die Unit ließ sich nicht schreiben. Bis Punkt 255 hieß
            # die Komponente danach im Designer schon neu, in der
            # `.pfm` noch alt, und Rückgängig ging nicht.
            self._umhaengen(self.neuer_name, self.alter_name)
            raise

    def rueckgaengig(self) -> None:
        self._umhaengen(self.neuer_name, self.alter_name)
        try:
            self._methoden_umbenennen(rueckwaerts=True)
        except OSError:
            self._umhaengen(self.alter_name, self.neuer_name)
            raise


# Sinnvolle Startgrößen je Komponententyp beim Ablegen aus der Palette
# - ein frisches `StringGrid` braucht mehr Platz als ein `CheckBox`.
# Der einheitliche
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
    # Eine Zeichenfläche im Querformat, gross genug zum Zeichnen.
    "PaintBox": (200, 150),
    # Ein Zeitgeber zeigt nur sein Symbol - quadratisch und klein, so
    # wie jede Komponente, die im laufenden Programm unsichtbar ist.
    # Für die beiden Menüs gilt dasselbe.
    "Timer": (32, 32),
    "MainMenu": (32, 32),
    "PopupMenu": (32, 32),
    # Datensteuerelemente (Punkt 60): eine Tabelle braucht Platz für
    # ein paar Zeilen, die Navigationsleiste für ihre acht Knöpfe.
    "DBGrid": (260, 150),
    "DBText": (120, 25),
    "DBEdit": (120, 25),
    "DBComboBox": (140, 25),
    "DBNavigator": (240, 30),
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
    """Legt eine frische Komponente in Standardwerten an (Abschnitt
    7.3: Palette → Formular)."""

    def __init__(self, canvas: DesignerCanvas, typ: type, x: int, y: int) -> None:
        self.canvas = canvas
        self.name = canvas._eindeutigen_namen_finden(typ.__name__.lower())

        # Liegt an dieser Stelle ein Behälter, gehört die Komponente
        # hinein: ein Knopf über einem Panel wird dessen Kind.
        # `left`/`top` zählen dann ab der linken oberen Ecke
        # des Behälters, nicht ab der des Formulars.
        eltern, ex, ey = canvas._behaelter_bei(x, y)
        self.neue_komponente = typ(eltern)
        # Am Raster einrasten.
        # Ohne das legte der Designer Komponenten auf krumme
        # Koordinaten, und der Design-Prüfer meldete anschließend
        # „steht nicht am 8px-Raster" - für etwas, das der Schüler gar
        # nicht verursacht hat, sondern das Werkzeug selbst (im
        # Durchgang durch den Schülerweg aufgefallen). Die Pfeiltasten
        # verschieben seit jeher in Rasterschritten; das Ablegen zieht
        # damit nach.
        self.neue_komponente.left = _am_raster(ex, canvas.raster)
        self.neue_komponente.top = _am_raster(ey, canvas.raster)
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


_MAUSEREIGNISSE = (
    QEvent.Type.MouseButtonPress,
    QEvent.Type.MouseButtonRelease,
    QEvent.Type.MouseButtonDblClick,
    QEvent.Type.MouseMove,
)


class _MethodeAnlegenKommando:
    """Doppelklick auf eine Komponente: Methode in der Unit anlegen und
    verknüpfen, als ein Rückgängig-Schritt.

    Bis 0.4.3 kannte das Rückgängigmachen nur die Verknüpfung, und die
    leere Methode blieb in der Unit stehen (Punkt 537). Entfernt wird
    sie nur, solange Datei und offene Editoren noch genau den Stand
    direkt nach dem Anlegen haben; was jemand inzwischen geschrieben
    hat, bleibt stehen. Wiederholen legt sie auf demselben Weg wieder
    an."""

    def __init__(
        self,
        canvas: DesignerCanvas,
        bindung: EigenschaftKommando,
        vorher: str,
        nachher: str,
    ) -> None:
        self._canvas = canvas
        self._bindung = bindung
        self._vorher = vorher
        self._nachher = nachher
        self._erster_lauf = True

    def tun(self) -> None:
        self._bindung.tun()
        if self._erster_lauf:
            # Die Unit ist schon geschrieben.
            self._erster_lauf = False
            return
        self._unit_tauschen(self._vorher, self._nachher)

    def rueckgaengig(self) -> None:
        self._bindung.rueckgaengig()
        self._unit_tauschen(self._nachher, self._vorher)

    def _unit_tauschen(self, erwartet: str, neu: str) -> None:
        _unit_tauschen(self._canvas, erwartet, neu)


class _UnitTauschKommando:
    """Ersetzt den Text der Unit, etwa ohne die leeren Methoden einer
    gelöschten Komponente (Punkt 537). Wie bei
    `_MethodeAnlegenKommando` nur, solange Datei und offene Editoren
    genau den erwarteten Stand haben."""

    def __init__(self, canvas: DesignerCanvas, vorher: str, nachher: str) -> None:
        self._canvas = canvas
        self._vorher = vorher
        self._nachher = nachher

    def tun(self) -> None:
        _unit_tauschen(self._canvas, self._vorher, self._nachher)

    def rueckgaengig(self) -> None:
        _unit_tauschen(self._canvas, self._nachher, self._vorher)


def _unit_tauschen(canvas: DesignerCanvas, erwartet: str, neu: str) -> None:
    texte = canvas._unit_quelltexte()
    if texte and all(text == erwartet for text in texte):
        canvas._unit_schreiben(neu, "Die Unit bleibt deshalb, wie sie ist.")


class _EscapeWache(QObject):
    """Beendet mit Escape den Platziermodus eines Designers, egal
    welches Widget gerade den Fokus hat. Hängt nur während des Modus an
    der Anwendung und fängt nichts außer dieser einen Taste ab."""

    def __init__(self, canvas: DesignerCanvas) -> None:
        # Mit dem Designer als Eltern endet die Wache mit ihm im
        # Hauptfaden (Punkt 550).
        super().__init__(canvas)
        self._canvas = canvas

    def eventFilter(self, objekt: QObject, ereignis: QEvent) -> bool:  # noqa: N802
        if (
            ereignis.type() == QEvent.Type.KeyPress
            and ereignis.key() == Qt.Key.Key_Escape
            and self._canvas._platzierungs_typ is not None
        ):
            self._canvas.platzierungsmodus_setzen(None)
            return True
        return False


class DesignerCanvas(QObject):
    def __init__(self, formular: Form, pfm_pfad: Path | None = None) -> None:
        # Das Formular-Widget als Eltern: der Designer lebt und stirbt
        # mit seinem Formular, im Hauptfaden. Ohne Eltern gehörte er
        # Python, und weil das Hauptfenster ihn über Lambdas festhält,
        # räumte ihn erst die Speicherbereinigung ab - in irgendeinem
        # Python-Faden, etwa dem Lesefaden von jedi. Dort konnte Qt
        # die laufende Schreib-Uhr nicht abmelden, und sie feuerte
        # danach in freigegebenen Speicher: Natter stürzte ab (Punkt
        # 534, am Speicherabbild nachgewiesen: Timer mit 400 ms in
        # `QEventDispatcherWin32Private::sendTimerEvent`).
        super().__init__(formular._qwidget)
        self.formular = formular
        self.pfm_pfad = Path(pfm_pfad) if pfm_pfad is not None else None
        # Namenskonvention aus Abschnitt 4.1: u_main.pfm <-> u_main.py
        self.unit_pfad = self.pfm_pfad.with_suffix(".py") if self.pfm_pfad is not None else None
        self.kommandos = Kommandostapel()
        self.ausgewaehlte_komponente: Any = None
        #: Bei einer Mehrfachauswahl alle ausgewählten Komponenten, die
        #: zuletzt gewählte am Ende; sie ist zugleich
        #: `ausgewaehlte_komponente` und steht im Objektinspektor
        #: (Punkt 73). Bei einer einzelnen Auswahl leer.
        self._mehrfach: list[Any] = []
        #: Die laufende Folge von Pfeiltasten: (Art und Auswahl, Kommando,
        #: Zeitpunkt), siehe `_schritt_ausfuehren`.
        self._tastenfolge: tuple[Any, Any, float] | None = None
        self._zusatz_rahmen: list[QFrame] = []
        self._ziehen_gruppe: dict[Any, tuple[int, int]] = {}
        self._band: QRubberBand | None = None
        self._band_start: QPoint | None = None
        self._auswahl_beobachter: list[Callable[[Any], None]] = []
        self._aenderung_beobachter: list[Callable[[], None]] = []
        #: Wahr, solange eine Änderung noch nicht geschrieben und den
        #: Beobachtern noch nicht gemeldet ist (`jetzt_schreiben`).
        self.schreiben_ausstehend = False
        self._schreib_uhr = QTimer(self)
        self._schreib_uhr.setSingleShot(True)
        self._schreib_uhr.setInterval(SCHREIB_VERZOEGERUNG_MS)
        self._schreib_uhr.timeout.connect(self.jetzt_schreiben)
        # Ohne das Formular-Widget gibt es nichts mehr zu schreiben;
        # die Uhr liefe sonst in ein gelöschtes Qt-Objekt.
        formular._qwidget.destroyed.connect(self._schreib_uhr.stop)
        #: Wahr, solange eine Änderung im Designer steht, aber nicht in
        #: der `.pfm` (Punkt 235). Das Hauptfenster kennzeichnet den
        #: Reiter damit.
        self.ungespeichert = False
        self._schreibfehler_gemeldet = False
        #: Wahr, nachdem das Überschreiben einer von außen geänderten
        #: `.pfm` abgelehnt wurde. Bis zum nächsten Strg+S schreibt der
        #: Designer dann nicht mehr und fragt auch nicht bei jeder
        #: weiteren Änderung erneut (Punkt 286).
        self.ueberschreiben_abgelehnt = False
        #: Der Stand der `.pfm` beim Laden oder letzten Schreiben.
        self.pfm_stand = (
            dateistand.kennung(self.pfm_pfad) if self.pfm_pfad else ""
        )
        self._widget_zu_komponente: dict[QWidget, Any] = {}
        #: Innere Widgets einer Komponente (Viewport und Bildlaufleisten
        #: einer Tabelle oder Liste). Ihre Mausereignisse gehen an die
        #: Komponente, zu der sie gehören (Punkt 50).
        self._innere_widgets: set[QWidget] = set()
        self._ziehen_komponente: Any = None
        self._ziehen_start: QPoint | None = None
        self._ziehen_start_werte: dict[str, Any] | None = None
        self._anfasser_widget_zu_name: dict[QWidget, str] = {}
        self._anfasser_ziehen: str | None = None
        self._anfasser_start: QPoint | None = None
        self._anfasser_start_werte: dict[str, int] | None = None
        self._platzierungs_typ: type | None = None
        self._escape_wache = _EscapeWache(self)
        #: Rasterweite in Pixeln: Schrittweite der Pfeiltasten, Punkte
        #: auf der Fläche, Einrasten beim Ablegen (Punkt 105). Gilt für
        #: diesen Designer, solange er offen ist; gespeichert wird sie
        #: nicht.
        self.raster = RASTER
        self._bild_beobachter: list[Callable[[str], None]] = []
        #: Wer wissen will, zu welcher Methode ein Doppelklick führt
        #: (Unit, Klasse, Methode, Parameter) - das Hauptfenster
        #: öffnet die Unit dort (Punkt 37).
        self._methoden_beobachter: list[Callable[[Path, str, str, tuple], None]] = []

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
        # Das Formular wird vor seinen Komponenten eingerichtet; ihre
        # Widgets standen dabei als „innere“ in der Liste.
        self._innere_widgets.discard(widget)
        widget.installEventFilter(self)
        # Ein StringGrid, ein Memo oder eine ListBox bestehen aus
        # mehreren Widgets; ein Klick in die Zellen landet im Viewport.
        # Ohne Filter dort legte ein Klick mit gewählter Kachel nichts an,
        # und die Komponente ließ sich nicht per Klick auswählen.
        for inneres in widget.findChildren(QWidget):
            if inneres not in self._widget_zu_komponente:
                self._innere_widgets.add(inneres)
                inneres.installEventFilter(self)
        # Eine Komponente ohne eigene Anzeige - ein Zeitgeber etwa -
        # versteckt ihr Widget beim Erzeugen, damit sie im fertigen
        # Programm nicht zu sehen ist. Im Designer muss man sie
        # anklicken können, also kommt sie hier zum Vorschein.
        if getattr(type(objekt), "nur_im_designer", False):
            widget.show()
            # Das Symbol ist gezeichnet und hat keinen Text; ohne Namen
            # übergeht es ein Bildschirmleser ganz.
            widget.setAccessibleName(type(objekt).__name__)
            # Ein gezeichnetes Symbol nimmt von sich aus keinen
            # Tastaturfokus an. Nach einem Klick darauf gingen F2, Entf
            # und die Pfeiltasten deshalb an ein anderes Widget, und der
            # Menü-Editor ließ sich nur per Doppelklick öffnen.
            widget.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        for _, komponente in kind_komponenten(objekt):
            self._ueberwachung_einrichten(komponente)

    def _raster_erzeugen(self) -> None:
        """Der Punkteraster auf dem Formular.

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
        widget.raster = self.raster
        widget.setGeometry(self.formular._qwidget.rect())
        widget.lower()
        widget.show()
        widget.update()

    def raster_setzen(self, weite: int) -> None:
        """Ändert die Rasterweite. Vorhandene Komponenten bleiben, wo
        sie sind; erst das nächste Verschieben oder Ablegen rastet im
        neuen Raster ein."""
        self.raster = max(1, int(weite))
        self._raster_aktualisieren()

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

    def _zusatz_rahmen_aktualisieren(self) -> None:
        """Gestrichelte Rahmen um die übrigen Komponenten einer
        Mehrfachauswahl; die zuletzt gewählte trägt den vollen Rahmen
        mit Anfassern."""
        weitere = [k for k in self._mehrfach if k is not self.ausgewaehlte_komponente]
        while len(self._zusatz_rahmen) < len(weitere):
            rahmen = QFrame(self.formular._qwidget)
            rahmen.setStyleSheet(
                f"QFrame {{ border: 1px dashed {_RAHMEN_FARBE}; background: transparent; }}"
            )
            rahmen.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            self._zusatz_rahmen.append(rahmen)
        for rahmen, komponente in zip(self._zusatz_rahmen, weitere, strict=False):
            ecke = komponente._qwidget.mapTo(self.formular._qwidget, QPoint(0, 0))
            rahmen.setGeometry(
                ecke.x() - 2, ecke.y() - 2,
                komponente._qwidget.width() + 4, komponente._qwidget.height() + 4,
            )
            rahmen.show()
            rahmen.raise_()
        for rahmen in self._zusatz_rahmen[len(weitere):]:
            rahmen.hide()

    def _rahmen_aktualisieren(self) -> None:
        self._zusatz_rahmen_aktualisieren()
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

        if (
            typ in _MAUSEREIGNISSE
            and beobachtetes_objekt in self._innere_widgets
            and beobachtetes_objekt not in self._widget_zu_komponente
        ):
            return self._an_komponente_weiterreichen(beobachtetes_objekt, ereignis)

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
                zusatz = ereignis.modifiers() & (
                    Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier
                )
                if zusatz and komponente is not self.formular:
                    # Strg- oder Umschalt-Klick: zur Auswahl dazu oder
                    # wieder heraus (Punkt 73).
                    self.auswahl_umschalten(komponente)
                    return True
                if komponente is self.formular:
                    self._auswaehlen(komponente)
                    self._band_beginnen(ereignis.position().toPoint())
                    return True
                if komponente in self._mehrfach:
                    # In eine Mehrfachauswahl geklickt: sie bleibt, und
                    # Ziehen verschiebt alle zusammen.
                    self.ausgewaehlte_komponente = komponente
                    self._benachrichtigen(komponente)
                else:
                    self._auswaehlen(komponente)
                self._ziehen_komponente = komponente
                self._ziehen_start = ereignis.globalPosition().toPoint()
                self._ziehen_start_werte = {"left": komponente.left, "top": komponente.top}
                self._ziehen_gruppe = {
                    k: (k.left, k.top)
                    for k in self._obenauf(self._mehrfach)
                    if k is not komponente
                }
                return True  # Klick abfangen: keine echte Interaktion im Designer

        elif typ == QEvent.Type.MouseMove and self._anfasser_ziehen is not None:
            self._anfasser_ziehen_verarbeiten(ereignis)
            return True

        elif typ == QEvent.Type.MouseMove and self._band_start is not None:
            self._band_ziehen(ereignis.position().toPoint())
            return True

        elif typ == QEvent.Type.MouseButtonRelease and self._band_start is not None:
            self._band_beenden(ereignis.position().toPoint())
            return True

        elif typ == QEvent.Type.MouseMove and self._ziehen_komponente is not None:
            aktuell = ereignis.globalPosition().toPoint()
            delta = aktuell - self._ziehen_start
            if delta.x() or delta.y():
                # Live-Vorschau während des Ziehens, noch kein Kommando
                self._ziehen_komponente.left += delta.x()
                self._ziehen_komponente.top += delta.y()
                for mit in self._ziehen_gruppe:
                    mit.left += delta.x()
                    mit.top += delta.y()
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

        elif (
            typ == QEvent.Type.ShortcutOverride
            and self.ausgewaehlte_komponente is not None
            and ereignis.modifiers() & Qt.KeyboardModifier.AltModifier
            and ereignis.key()
            in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down)
        ):
            # Alt+Pfeil verschiebt im Designer um einen Bildpunkt. Ohne
            # das griff Alt+Links als Fensterkürzel „Zurück zur vorigen
            # Stelle“, bevor der Designer die Taste sah (Punkt 577).
            ereignis.accept()
            return True

        elif typ == QEvent.Type.ContextMenu:
            komponente = self._widget_zu_komponente.get(beobachtetes_objekt)
            if komponente is None:
                return False
            self.rechtsklick_auswaehlen(komponente)
            menue = self.kontextmenue_fuer(komponente)
            menue.exec(ereignis.globalPos())
            return True

        return False

    def rechtsklick_auswaehlen(self, komponente: Any) -> None:
        """Die Auswahl vor dem Kontextmenü. Ein Rechtsklick in eine
        Mehrfachauswahl lässt sie stehen, damit „Ausrichten“ etwas
        auszurichten hat; die angeklickte Komponente wird der Bezug
        (Punkt 105). Sonst wird die angeklickte allein ausgewählt."""
        if komponente in self._mehrfach:
            self.ausgewaehlte_komponente = komponente
            self._benachrichtigen(komponente)
        else:
            self._auswaehlen(komponente)

    def kontextmenue_fuer(self, komponente: Any) -> QMenu:
        """Das Menü zur rechten Maustaste auf `komponente`
        (M11, Abschnitt 3).

        Die drei Dinge gab es alle schon – aber nur über Tasten (Entf,
        Strg+D) oder einen Doppelklick. Wer sie nicht kennt, probiert
        die rechte Maustaste, und dort liegt das Menü zu einer
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

        # Tab-Reihenfolge (Punkt 61). Die Design-Prüfung meldete eine
        # ungünstige Reihenfolge schon lange, ändern ließ sie sich nur
        # durch Löschen und neu Anlegen.
        menue.addSeparator()
        geschwister = [] if ist_formular else self._geschwister(komponente)
        name = None if ist_formular else self._attributname(komponente)
        stelle = geschwister.index(name) if name in geschwister else -1
        frueher = menue.addAction("Früher in der Tab-Reihenfolge")
        frueher.setEnabled(stelle > 0)
        frueher.triggered.connect(
            lambda *_, k=komponente: self.tab_reihenfolge_verschieben(k, -1)
        )
        spaeter = menue.addAction("Später in der Tab-Reihenfolge")
        spaeter.setEnabled(0 <= stelle < len(geschwister) - 1)
        spaeter.triggered.connect(
            lambda *_, k=komponente: self.tab_reihenfolge_verschieben(k, 1)
        )
        ordnen = menue.addAction("Tab-Reihenfolge nach Lage ordnen")
        ordnen.triggered.connect(lambda *_: self.tab_reihenfolge_nach_lage())

        # Ausrichten, Verteilen, gleiche Größe (Punkt 105). Das
        # Untermenü steht immer da und ist grau, solange nicht mehrere
        # Komponenten ausgewählt sind - aus demselben Grund wie beim
        # grauen „Löschen“ am Formular.
        menue.addSeparator()
        anzahl = len(self._obenauf(self.ausgewaehlte_komponenten()))
        ausrichten = menue.addMenu("Ausrichten")
        ausrichten.setEnabled(anzahl >= 2)
        for text, kante in (
            ("Linke Kanten", "links"),
            ("Rechte Kanten", "rechts"),
            ("Obere Kanten", "oben"),
            ("Untere Kanten", "unten"),
        ):
            aktion = ausrichten.addAction(text)
            aktion.triggered.connect(lambda *_, k=kante: self.ausrichten(k))
        ausrichten.addSeparator()
        for text, richtung in (
            ("Waagerecht gleichmäßig verteilen", "waagerecht"),
            ("Senkrecht gleichmäßig verteilen", "senkrecht"),
        ):
            aktion = ausrichten.addAction(text)
            aktion.setEnabled(anzahl >= 3)
            aktion.triggered.connect(lambda *_, r=richtung: self.verteilen(r))
        ausrichten.addSeparator()
        breite = ausrichten.addAction("Gleiche Breite")
        breite.triggered.connect(lambda *_: self.gleiche_groesse(breite=True))
        hoehe = ausrichten.addAction("Gleiche Höhe")
        hoehe.triggered.connect(lambda *_: self.gleiche_groesse(hoehe=True))

        raster = menue.addMenu("Raster")
        for weite in RASTER_WEITEN:
            aktion = raster.addAction(f"{weite} Pixel")
            aktion.setCheckable(True)
            aktion.setChecked(weite == self.raster)
            aktion.triggered.connect(lambda *_, w=weite: self.raster_setzen(w))

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
        gruppe = self._ziehen_gruppe

        self._ziehen_komponente = None
        self._ziehen_start = None
        self._ziehen_start_werte = None
        self._ziehen_gruppe = {}

        if endwerte == startwerte:
            return  # keine tatsächliche Bewegung, kein Kommando nötig

        if gruppe:
            # Eine ganze Auswahl verschoben: alle in einem Schritt. Jede
            # landet im Behälter unter ihrer Mitte, wie eine einzeln
            # gezogene (Punkt 168). Bis dahin blieben alle in ihrem
            # alten Behälter; zwei gemeinsam auf ein Panel gezogene
            # Knöpfe lagen dann unter dem Panel und waren verdeckt.
            alle = {komponente: (startwerte["left"], startwerte["top"]), **gruppe}
            ziele = {k: self._behaelter_fuer(k, set(alle)) for k in alle}
            kommandos: list[Any] = []
            for mit, (links, oben) in alle.items():
                behaelter, x, y = ziele[mit]
                if behaelter is not (mit.eltern or self.formular):
                    mit.left, mit.top = links, oben
                    kommandos.append(
                        _UmhaengenKommando(
                            self,
                            mit,
                            behaelter,
                            (_am_raster(x, self.raster), _am_raster(y, self.raster)),
                            (links, oben),
                        )
                    )
                else:
                    kommandos.append(
                        EigenschaftKommando(
                            mit, {"left": mit.left, "top": mit.top},
                            alte_werte={"left": links, "top": oben},
                        )
                    )
            self.kommandos.ausfuehren(_GruppenKommando(kommandos))
            self._nach_aenderung(komponente)
            return

        ziel, x, y = self._behaelter_fuer(komponente)
        komponente.left, komponente.top = startwerte["left"], startwerte["top"]
        if ziel is not (komponente.eltern or self.formular):
            self.kommandos.ausfuehren(
                _UmhaengenKommando(
                    self,
                    komponente,
                    ziel,
                    (_am_raster(x, self.raster), _am_raster(y, self.raster)),
                    (startwerte["left"], startwerte["top"]),
                )
            )
        else:
            self.kommandos.ausfuehren(
                EigenschaftKommando(komponente, endwerte, alte_werte=startwerte)
            )
        self._nach_aenderung(komponente)

    def _an_komponente_weiterreichen(self, inneres: QWidget, ereignis: Any) -> bool:
        """Reicht ein Mausereignis aus einem inneren Widget an die
        Komponente weiter, zu der es gehört, mit der Stelle umgerechnet
        auf deren Widget. Die nächste Komponente nach oben zählt: in
        einem Panel ist das die Komponente darin, nicht das Panel."""
        ziel = inneres.parentWidget()
        while ziel is not None and ziel not in self._widget_zu_komponente:
            ziel = ziel.parentWidget()
        if ziel is None:
            return False
        stelle = inneres.mapTo(ziel, ereignis.position().toPoint())
        weitergereicht = QMouseEvent(
            ereignis.type(),
            QPointF(stelle),
            ereignis.globalPosition(),
            ereignis.button(),
            ereignis.buttons(),
            ereignis.modifiers(),
        )
        return self.eventFilter(ziel, weitergereicht)

    def _tastatur_verarbeiten(self, ereignis) -> bool:
        taste = ereignis.key()
        modifikatoren = ereignis.modifiers()

        if taste == Qt.Key.Key_Escape and self._platzierungs_typ is not None:
            self.platzierungsmodus_setzen(None)
            return True
        if taste == Qt.Key.Key_Z and modifikatoren & Qt.KeyboardModifier.ControlModifier:
            if modifikatoren & Qt.KeyboardModifier.ShiftModifier:
                self.wiederholen()
            else:
                self.rueckgaengig()
            return True
        if taste == Qt.Key.Key_Y and modifikatoren & Qt.KeyboardModifier.ControlModifier:
            self.wiederholen()
            return True

        strg = bool(modifikatoren & Qt.KeyboardModifier.ControlModifier)
        if strg and taste == Qt.Key.Key_A:
            self.alles_auswaehlen()
            return True
        if strg and taste == Qt.Key.Key_V:
            self.einfuegen()
            return True

        komponente = self.ausgewaehlte_komponente
        if komponente is None or komponente is self.formular:
            return False

        if strg and taste == Qt.Key.Key_C:
            self.kopieren()
            return True
        if strg and taste == Qt.Key.Key_X:
            self.ausschneiden()
            return True
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
            self.groesse_aendern(dx * self.raster, dy * self.raster, per_taste=True)
        elif modifikatoren & Qt.KeyboardModifier.AltModifier:
            self.verschieben(dx, dy, per_taste=True)
        else:
            self.verschieben(dx * self.raster, dy * self.raster, per_taste=True)
        return True

    # -- Undo/Redo ----------------------------------------------------------

    def rueckgaengig(self) -> None:
        """Real gefunden: beide Richtungen meldeten die Änderung nur an
        die Beobachter, schrieben sie aber nicht zurück. Der Designer
        zeigte nach Strg+Z also den zurückgenommenen Stand, `.pfm` und
        `u_*_design.py` behielten den zurückgenommenen Schritt trotzdem -
        das Programm lief weiter mit der rückgängig gemachten Änderung."""
        kommando = self.kommandos.letztes_kommando
        try:
            self.kommandos.rueckgaengig()
        except OSError as fehler:
            self._stapelschritt_gescheitert(fehler)
            return
        self._nach_aenderung(
            self.ausgewaehlte_komponente or self.formular,
            sofort=isinstance(kommando, _UmbenennenKommando),
        )

    def wiederholen(self) -> None:
        try:
            self.kommandos.wiederholen()
        except OSError as fehler:
            self._stapelschritt_gescheitert(fehler)
            return
        self._nach_aenderung(
            self.ausgewaehlte_komponente or self.formular,
            sofort=isinstance(
                self.kommandos.letztes_kommando, _UmbenennenKommando
            ),
        )

    def _stapelschritt_gescheitert(self, fehler: OSError) -> None:
        """Rückgängig oder Wiederholen eines Umbenennens, nachdem die
        Unit inzwischen schreibgeschützt ist (Punkt 255). Das Kommando
        hat nichts geändert und bleibt auf seinem Stapel."""
        self._meldung_zeigen(
            f"Eine Datei konnte nicht gespeichert werden:\n{fehler}\n\n"
            "Der Schritt ist deshalb nicht ausgeführt. Er lässt sich "
            "wiederholen, sobald die Datei beschreibbar ist."
        )

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

    def _behaelter_fuer(
        self, komponente: Any, mitgezogen: set[Any] | None = None
    ) -> tuple[Any, int, int]:
        """Wohin `komponente` nach dem Verschieben gehört (Punkt 72):
        der innerste Behälter unter ihrer Mitte, sie selbst und alles,
        was in ihr liegt, ausgenommen. Zurück kommen der Behälter und
        die linke obere Ecke der Komponente in dessen Koordinaten.

        `mitgezogen` sind die übrigen Komponenten einer gemeinsam
        gezogenen Auswahl. Ein Behälter darunter nimmt keine andere
        auf: er wandert ja mit, und wie die Auswahl zueinander liegt,
        ändert sich nicht.

        `_behaelter_bei` taugt hier nicht: `childAt` fände die gerade
        gezogene Komponente selbst, weil sie obenauf liegt."""
        formular_widget = self.formular._qwidget
        ecke = komponente._qwidget.mapTo(formular_widget, QPoint(0, 0))
        mitte = QPoint(
            ecke.x() + komponente._qwidget.width() // 2,
            ecke.y() + komponente._qwidget.height() // 2,
        )
        treffer, kleinste = self.formular, None
        for widget, kandidat in self._widget_zu_komponente.items():
            if not getattr(type(kandidat), "ist_behaelter", False):
                continue
            if kandidat is komponente or self._liegt_in(kandidat, komponente):
                continue
            if mitgezogen and (
                kandidat in mitgezogen
                or any(self._liegt_in(kandidat, m) for m in mitgezogen)
            ):
                continue
            if not widget.isVisible():
                continue
            oben_links = widget.mapTo(formular_widget, QPoint(0, 0))
            if not QRect(oben_links, widget.size()).contains(mitte):
                continue
            flaeche = widget.width() * widget.height()
            if kleinste is None or flaeche < kleinste:
                treffer, kleinste = kandidat, flaeche
        punkt = treffer._qwidget.mapFrom(formular_widget, ecke)
        return treffer, punkt.x(), punkt.y()

    def _liegt_in(self, komponente: Any, behaelter: Any) -> bool:
        eltern = getattr(komponente, "eltern", None)
        while eltern is not None and eltern is not self.formular:
            if eltern is behaelter:
                return True
            eltern = getattr(eltern, "eltern", None)
        return False

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
        Speichern-Aktion, jede Änderung schreibt von sich aus zurück).

        Geschrieben und benachrichtigt wird kurz nach der letzten
        Änderung einer Folge, nicht nach jeder einzelnen
        (`SCHREIB_VERZOEGERUNG_MS`, `jetzt_schreiben`)."""
        self._aenderung_beobachter.append(beobachter)

    def _auswaehlen(self, komponente: Any) -> None:
        self._mehrfach = []
        self.ausgewaehlte_komponente = komponente
        self._benachrichtigen(komponente)

    # -- Mehrfachauswahl und Zwischenablage (Punkt 73) -----------------

    def ausgewaehlte_komponenten(self) -> list[Any]:
        """Alle ausgewählten Komponenten, das Formular nie."""
        if self._mehrfach:
            return list(self._mehrfach)
        k = self.ausgewaehlte_komponente
        return [] if k is None or k is self.formular else [k]

    def auswahl_setzen(self, komponenten: list[Any]) -> None:
        komponenten = [k for k in komponenten if k is not None and k is not self.formular]
        if not komponenten:
            self._auswaehlen(self.formular)
        elif len(komponenten) == 1:
            self._auswaehlen(komponenten[0])
        else:
            self._mehrfach = komponenten
            self.ausgewaehlte_komponente = komponenten[-1]
            self._benachrichtigen(komponenten[-1])

    def auswahl_umschalten(self, komponente: Any) -> None:
        """Strg- oder Umschalt-Klick: `komponente` kommt zur Auswahl
        dazu oder fällt heraus."""
        auswahl = self.ausgewaehlte_komponenten()
        if komponente in auswahl:
            auswahl.remove(komponente)
        else:
            auswahl.append(komponente)
        self.auswahl_setzen(auswahl)

    def alles_auswaehlen(self) -> None:
        """Strg+A: alle Komponenten, die unmittelbar auf dem Formular
        liegen."""
        self.auswahl_setzen([k for _, k in kind_komponenten(self.formular)])

    def _obenauf(self, komponenten: list[Any]) -> list[Any]:
        """Ohne die, die in einem ebenfalls ausgewählten Behälter
        liegen - sie wandern mit ihm und würden sonst doppelt
        verschoben oder gelöscht."""
        return [k for k in komponenten if not any(self._liegt_in(k, b) for b in komponenten)]

    def _band_beginnen(self, punkt: QPoint) -> None:
        self._band_start = punkt
        if self._band is None:
            self._band = QRubberBand(QRubberBand.Shape.Rectangle, self.formular._qwidget)
        self._band.setGeometry(QRect(punkt, punkt))

    def _band_ziehen(self, punkt: QPoint) -> None:
        self._band.setGeometry(QRect(self._band_start, punkt).normalized())
        self._band.show()
        self._band.raise_()

    def _band_beenden(self, punkt: QPoint) -> None:
        """Rahmen aufziehen auf der freien Fläche: ausgewählt wird, was
        der Rahmen berührt - unter den Komponenten, die unmittelbar auf
        dem Formular liegen."""
        bereich = QRect(self._band_start, punkt).normalized()
        self._band_start = None
        self._band.hide()
        if bereich.width() < 3 and bereich.height() < 3:
            return
        getroffen = [
            k for _, k in kind_komponenten(self.formular)
            if QRect(k.left, k.top, k.width, k.height).intersects(bereich)
        ]
        self.auswahl_setzen(getroffen)

    def kopieren(self) -> bool:
        """Legt die ausgewählten Komponenten in die Zwischenablage, im
        Format der `.pfm`, mit ihren Ereignissen und ihrem Klappmenü.
        Was davon beim Einfügen bleibt, entscheidet `einfuegen`: nur,
        was es im Zielformular gibt."""
        from ide.designer.pfm_schreiben import _namen_der_komponenten, kind_als_dict

        komponenten = self._obenauf(self.ausgewaehlte_komponenten())
        if not komponenten:
            return False
        namen = _namen_der_komponenten(self.formular)
        eintraege = [kind_als_dict(self._attributname(k), k, namen) for k in komponenten]
        daten = QMimeData()
        daten.setData(ZWISCHENABLAGE_TYP, json.dumps(eintraege).encode("utf-8"))
        QApplication.clipboard().setMimeData(daten)
        return True

    def ausschneiden(self) -> bool:
        if not self.kopieren():
            return False
        self.loeschen()
        return True

    def einfuegen(self) -> list[Any]:
        """Fügt Komponenten aus der Zwischenablage ein - aus diesem oder
        einem anderen Formular. Ist ein Behälter ausgewählt, kommen sie
        hinein, sonst aufs Formular. Belegte Namen bekommen „_kopie“,
        und wer genau auf seinem Vorbild landen würde, rückt ein Stück
        nach rechts unten.

        Ereignisse bleiben verknüpft, wenn es die Methode im Zielformular
        gibt (Punkt 169). Im selben Formular ist das immer so: wer einen
        Knopf ausschneidet und in ein Panel einfügt, will ihn umsetzen
        und nicht seine Ereignisse verlieren. In einem anderen Formular
        fehlt die Methode meist, und die Verknüpfung fällt weg, denn
        die Methode kommt nicht mit. Dasselbe gilt für das Klappmenü
        (Punkt 172)."""
        roh = QApplication.clipboard().mimeData()
        if roh is None or not roh.hasFormat(ZWISCHENABLAGE_TYP):
            return []
        try:
            eintraege = json.loads(bytes(roh.data(ZWISCHENABLAGE_TYP)).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return []
        # Der Inhalt wird zu Quelltext, den der Designer ausführt. Die
        # Zwischenablage kann jedes Programm füllen; stehen darin statt
        # Namen Anweisungen, wird nichts eingefügt (Punkt 226).
        try:
            pfm_pruefen({"format": "pfm/1", "class": "_Einfuegen",
                         "type": "Form", "properties": {},
                         "children": eintraege})
        except (PfmBeschaedigt, schema_fehler()) as fehler:
            self._meldung_zeigen(
                "Der Inhalt der Zwischenablage ist beschädigt und wird "
                f"nicht eingefügt.\n\n{fehler_beschreiben(fehler)}"
            )
            return []

        # Hinein nur in einen einzeln ausgewählten Behälter, der nicht
        # selbst kopiert wurde - ein kopiertes Panel gehört neben sein
        # Vorbild, nicht in es hinein.
        ziel = self.ausgewaehlte_komponente
        kopierte_namen = {e.get("name") for e in eintraege}
        if (
            ziel is None
            or len(self.ausgewaehlte_komponenten()) != 1
            or not getattr(type(ziel), "ist_behaelter", False)
            or self._attributname(ziel) in kopierte_namen
        ):
            ziel = self.formular
        verknuepft = _ereignisse_sammeln(eintraege)
        for eintrag in eintraege:
            _ereignisse_entfernen(eintrag)
        return self._eintraege_einsetzen(eintraege, ziel, verknuepft)

    def _eintraege_einsetzen(
        self,
        eintraege: list[dict[str, Any]],
        ziel: Any,
        ereignisse_je_name: dict[str, dict[str, str]] | None = None,
    ) -> list[Any]:
        """Baut Komponenten aus `.pfm`-Einträgen und setzt sie als ein
        Undo-Schritt in `ziel` ein. Gemeinsamer Weg für Einfügen und
        Duplizieren."""
        return self._gebaute_einsetzen(
            self._eintraege_bauen(eintraege, ziel, ereignisse_je_name)
        )

    def _gebaute_einsetzen(self, neu: list[tuple[str, Any, bool]]) -> list[Any]:
        """Setzt, was `_eintraege_bauen` gebaut hat, als einen
        Undo-Schritt ein und wählt es aus."""
        if not neu:
            return []
        for name, _, _ in neu:
            delattr(self.formular, name)
        self.kommandos.ausfuehren(_EinfuegenKommando(self, neu))
        oben = [k for _, k, obenauf in neu if obenauf]
        self.auswahl_setzen(oben)
        self._nach_aenderung(oben[-1] if oben else self.formular)
        return oben

    def _eintraege_bauen(
        self,
        eintraege: list[dict[str, Any]],
        ziel: Any,
        ereignisse_je_name: dict[str, dict[str, str]] | None = None,
    ) -> list[tuple[str, Any, bool]]:
        """Baut Komponenten aus `.pfm`-Einträgen für `ziel`, noch ohne
        Undo-Schritt. Ihre Namen stehen danach vorläufig am Formular,
        damit ein weiterer Bau sie nicht noch einmal vergibt;
        `_gebaute_einsetzen` nimmt sie wieder weg.

        Die Einträge dürfen keine `events` tragen: der Zwischenbau hat
        die Methoden des Formulars nicht. `ereignisse_je_name` verknüpft
        danach Ereignisse mit Methoden dieses Formulars, nach den Namen
        der Einträge; eine Methode, die es hier nicht gibt, bleibt
        unverknüpft."""
        from ide.codegen.design import design_code_erzeugen

        eintraege = json.loads(json.dumps(eintraege))
        verweise = _verweise_herausnehmen(eintraege, _namen_in(eintraege))
        self._methoden_nachladen()
        vorlage = {"format": "pfm/1", "class": "_Einfuegen", "type": "Form",
                   "properties": {}, "children": eintraege}
        namensraum: dict[str, Any] = {}
        exec(compile(design_code_erzeugen(vorlage, "einfuegen.pfm"), "<einfuegen>", "exec"),
             namensraum)
        zwischen = namensraum["_EinfuegenDesign"]()
        for name, verknuepft in (ereignisse_je_name or {}).items():
            komponente = vars(zwischen).get(name)
            for ereignis_name, methode in verknuepft.items():
                handler = getattr(self.formular, methode, None)
                if (
                    komponente is not None
                    and callable(handler)
                    and not isinstance(handler, Control)
                ):
                    setattr(komponente, ereignis_name, handler)
        for name, verknuepft in verweise.items():
            komponente = vars(zwischen).get(name)
            for eigenschaft, ziel_name in verknuepft.items():
                verweis = vars(self.formular).get(ziel_name)
                if komponente is None or not isinstance(verweis, Control):
                    continue
                # Ein Name, der hier zu etwas anderem als einem
                # Klappmenü gehört, lehnt die Typprüfung ab.
                try:
                    setattr(komponente, eigenschaft, verweis)
                except (TypeError, ValueError):
                    pass

        belegte = {(k.left, k.top) for _, k in kind_komponenten(ziel)}
        obenauf_namen = {e["name"] for e in eintraege}
        neu: list[tuple[str, Any, bool]] = []
        for name, komponente in list(vars(zwischen).items()):
            if not isinstance(komponente, Control):
                continue
            obenauf = name in obenauf_namen
            neuer_name = name
            if hasattr(self.formular, neuer_name) or any(n == neuer_name for n, _, _ in neu):
                neuer_name = self._eindeutigen_namen_finden(f"{name}_kopie")
            if obenauf:
                komponente._eltern = ziel
                komponente._qwidget.setParent(ziel._qwidget)
                while (komponente.left, komponente.top) in belegte:
                    komponente.left += 2 * RASTER
                    komponente.top += 2 * RASTER
                belegte.add((komponente.left, komponente.top))
            self._ueberwachung_einrichten(komponente)
            neu.append((neuer_name, komponente, obenauf))
            # Der Name muss schon jetzt vergeben sein, sonst fände
            # `_eindeutigen_namen_finden` für die nächste Kopie denselben.
            setattr(self.formular, neuer_name, komponente)
        return neu

    # -- Bearbeiten ---------------------------------------------------------

    def verschieben(
        self, dx: int, dy: int, komponente: Any = None, *, per_taste: bool = False
    ) -> None:
        if komponente is None and len(self._mehrfach) > 1:
            kommandos = [
                EigenschaftKommando(k, {"left": k.left + dx, "top": k.top + dy})
                for k in self._obenauf(self._mehrfach)
            ]
            self._schritt_ausfuehren("verschieben", kommandos, per_taste)
            self._nach_aenderung(self.ausgewaehlte_komponente)
            return
        ziel = komponente if komponente is not None else self.ausgewaehlte_komponente
        self._schritt_ausfuehren(
            "verschieben",
            [EigenschaftKommando(ziel, {"left": ziel.left + dx, "top": ziel.top + dy})],
            per_taste,
        )
        self._nach_aenderung(ziel)

    def _schritt_ausfuehren(
        self, art: str, kommandos: list[Any], per_taste: bool
    ) -> None:
        """Führt einen Schritt aus Verschieben oder Größe ändern aus.

        Mit der Pfeiltaste hängt ein Schritt an den vorigen an, solange
        dieselbe Auswahl mit derselben Art Taste weiterbewegt wird und
        zwischen zwei Drücken weniger als `_TASTENFOLGE_S` liegt. Ein
        Strg+Z nimmt dann die ganze Folge zurück. Bis 0.4.3 kostete
        jeder Druck einen eigenen Schritt, und eine mit gehaltener
        Taste um 30 Pixel geschobene Komponente brauchte 30 × Strg+Z
        (Punkt 487)."""
        jetzt = time.monotonic()
        schluessel = (art, tuple(id(k.komponente) for k in kommandos))
        folge = self._tastenfolge
        oben = self.kommandos.letztes_kommando
        if (
            per_taste
            and folge is not None
            and folge[0] == schluessel
            and folge[1] is oben
            and jetzt - folge[2] < _TASTENFOLGE_S
        ):
            for kommando in kommandos:
                kommando.tun()
            oben.kommandos.extend(kommandos)
        else:
            oben = _GruppenKommando(kommandos)
            self.kommandos.ausfuehren(oben)
        self._tastenfolge = (schluessel, oben, jetzt) if per_taste else None

    def groesse_aendern(
        self, dw: int, dh: int, komponente: Any = None, *, per_taste: bool = False
    ) -> None:
        """Umschalt+Pfeil. Bei einer Mehrfachauswahl ändert sich die
        Größe aller ausgewählten Komponenten, in einem Schritt
        (Punkt 180); vorher nur die der zuletzt gewählten."""
        if komponente is None and len(self._mehrfach) > 1:
            kommandos = [
                EigenschaftKommando(
                    k,
                    {"width": max(1, k.width + dw), "height": max(1, k.height + dh)},
                )
                for k in self._mehrfach
            ]
            self._schritt_ausfuehren("groesse", kommandos, per_taste)
            self._nach_aenderung(self.ausgewaehlte_komponente)
            return
        ziel = komponente if komponente is not None else self.ausgewaehlte_komponente
        self._schritt_ausfuehren(
            "groesse",
            [
                EigenschaftKommando(
                    ziel,
                    {"width": max(1, ziel.width + dw), "height": max(1, ziel.height + dh)},
                )
            ],
            per_taste,
        )
        self._nach_aenderung(ziel)

    # -- Ausrichten, Verteilen, gleiche Größe (Punkt 105) --------------

    def _formular_rechteck(self, komponente: Any) -> tuple[int, int, int, int]:
        """(x, y, Breite, Höhe) in Formular-Koordinaten. Die Komponenten
        einer Auswahl können in verschiedenen Behältern liegen; ihr
        `left`/`top` lässt sich dann nicht unmittelbar vergleichen."""
        ecke = komponente._qwidget.mapTo(self.formular._qwidget, QPoint(0, 0))
        return ecke.x(), ecke.y(), komponente.width, komponente.height

    def _auswahl_mit_bezug(self) -> tuple[list[Any], Any]:
        """Die Auswahl ohne Komponenten in ausgewählten Behältern, dazu
        die Bezugskomponente: die zuletzt angeklickte."""
        auswahl = self._obenauf(self.ausgewaehlte_komponenten())
        bezug = self.ausgewaehlte_komponente
        if bezug not in auswahl and auswahl:
            bezug = auswahl[-1]
        return auswahl, bezug

    def _als_ein_schritt(self, neue_werte: dict[Any, dict[str, int]]) -> bool:
        """Setzt die Werte aller Komponenten als ein Undo-Schritt.
        `False`, wenn sich nichts ändern würde."""
        kommandos = [
            EigenschaftKommando(k, werte)
            for k, werte in neue_werte.items()
            if any(getattr(k, name) != wert for name, wert in werte.items())
        ]
        if not kommandos:
            return False
        self.kommandos.ausfuehren(_GruppenKommando(kommandos))
        self._nach_aenderung(self.ausgewaehlte_komponente)
        return True

    def ausrichten(self, kante: str) -> bool:
        """Richtet die ausgewählten Komponenten an einer Kante der
        Bezugskomponente aus: `"links"`, `"rechts"`, `"oben"` oder
        `"unten"`."""
        auswahl, bezug = self._auswahl_mit_bezug()
        if len(auswahl) < 2:
            return False
        bx, by, bb, bh = self._formular_rechteck(bezug)
        neu: dict[Any, dict[str, int]] = {}
        for k in auswahl:
            x, y, b, h = self._formular_rechteck(k)
            dx = dy = 0
            if kante == "links":
                dx = bx - x
            elif kante == "rechts":
                dx = (bx + bb) - (x + b)
            elif kante == "oben":
                dy = by - y
            elif kante == "unten":
                dy = (by + bh) - (y + h)
            else:
                raise ValueError(f"Unbekannte Kante {kante!r}.")
            neu[k] = {"left": k.left + dx, "top": k.top + dy}
        return self._als_ein_schritt(neu)

    def verteilen(self, richtung: str) -> bool:
        """Verteilt die ausgewählten Komponenten `"waagerecht"` oder
        `"senkrecht"` mit gleichen Abständen. Die beiden äußeren bleiben
        stehen, die übrigen rücken dazwischen. Braucht mindestens
        drei."""
        auswahl, _ = self._auswahl_mit_bezug()
        if len(auswahl) < 3:
            return False
        if richtung not in ("waagerecht", "senkrecht"):
            raise ValueError(f"Unbekannte Richtung {richtung!r}.")
        waagerecht = richtung == "waagerecht"
        achse, groesse = (0, 2) if waagerecht else (1, 3)
        rechtecke = {k: self._formular_rechteck(k) for k in auswahl}
        geordnet = sorted(auswahl, key=lambda k: rechtecke[k][achse])
        anfang = rechtecke[geordnet[0]][achse]
        letzte = rechtecke[geordnet[-1]]
        ende = letzte[achse] + letzte[groesse]
        belegt = sum(rechtecke[k][groesse] for k in geordnet)
        luecke = (ende - anfang - belegt) / (len(geordnet) - 1)
        stelle = float(anfang)
        neu: dict[Any, dict[str, int]] = {}
        for k in geordnet:
            versatz = round(stelle) - rechtecke[k][achse]
            if waagerecht:
                neu[k] = {"left": k.left + versatz}
            else:
                neu[k] = {"top": k.top + versatz}
            stelle += rechtecke[k][groesse] + luecke
        return self._als_ein_schritt(neu)

    def gleiche_groesse(self, *, breite: bool = False, hoehe: bool = False) -> bool:
        """Gibt allen ausgewählten Komponenten die Breite und/oder Höhe
        der Bezugskomponente."""
        auswahl, bezug = self._auswahl_mit_bezug()
        if len(auswahl) < 2 or not (breite or hoehe):
            return False
        neu: dict[Any, dict[str, int]] = {}
        for k in auswahl:
            werte = {}
            if breite:
                werte["width"] = bezug.width
            if hoehe:
                werte["height"] = bezug.height
            neu[k] = werte
        return self._als_ein_schritt(neu)

    def loeschen(self, komponente: Any = None) -> None:
        """Löscht `komponente`, ohne Angabe die Auswahl.

        Benutzt die Unit eine der Komponenten noch (`self.<name>`),
        fragt der Designer vorher nach (Punkt 294). Sonst endete das
        Programm erst beim Lauf mit einer Meldung, in der von einer
        fehlenden Komponente nichts stand."""
        if komponente is None and len(self._mehrfach) > 1:
            ziele = list(self._mehrfach)
        else:
            ziel = (
                komponente
                if komponente is not None
                else self.ausgewaehlte_komponente
            )
            ziele = [] if ziel is None or ziel is self.formular else [ziel]
        if not ziele or not self._loeschen_trotz_verwendung(ziele):
            return
        aufraeumen = self._leere_methoden_entfernen(ziele)
        if komponente is None and len(self._mehrfach) > 1:
            kommandos = [
                _LoeschenKommando(self, k, self._attributname(k))
                for k in self._obenauf(self._mehrfach)
            ]
            self._mehrfach = []
            if aufraeumen is not None:
                kommandos.append(aufraeumen)
            self.kommandos.ausfuehren(_GruppenKommando(kommandos))
            self._auswaehlen(self.formular)
            self._nach_aenderung(self.formular)
            return
        ziel = komponente if komponente is not None else self.ausgewaehlte_komponente
        if ziel is None or ziel is self.formular:
            return
        name = self._attributname(ziel)
        loeschen = _LoeschenKommando(self, ziel, name)
        self.kommandos.ausfuehren(
            loeschen if aufraeumen is None else _GruppenKommando([loeschen, aufraeumen])
        )
        self._nach_aenderung(self.formular)

    def _leere_methoden_entfernen(self, ziele: list[Any]) -> _UnitTauschKommando | None:
        """Ein Kommando, das die Ereignis-Methoden der gelöschten
        Komponenten aus der Unit nimmt, solange sie noch leer sind, wie
        der Designer sie angelegt hat, und keine andere Komponente sie
        benutzt. Bis 0.4.3 blieben sie stehen (Punkt 537); so ein Rest
        stand eingecheckt in einem Beispielprojekt. Geschriebener Code
        bleibt immer, und bei ungespeicherten Änderungen im Editor
        wird nichts angefasst."""
        if self.unit_pfad is None:
            return None
        texte = self._unit_quelltexte()
        if not texte or any(text != texte[0] for text in texte):
            return None
        quelltext = texte[0]
        geloescht: list[Any] = []
        offen = list(ziele)
        while offen:
            k = offen.pop()
            geloescht.append(k)
            offen.extend(kind for _, kind in kind_komponenten(k))
        bleibende = [
            k
            for k in vars(self.formular).values()
            if isinstance(k, Control) and all(k is not g for g in geloescht)
        ]

        def methoden(komponenten: list[Any]) -> set[str]:
            namen: set[str] = set()
            for k in komponenten:
                for ereignis in ereignisse(type(k)):
                    handler = getattr(k, ereignis, None)
                    if handler is not None and hasattr(handler, "__name__"):
                        namen.add(handler.__name__)
            return namen

        from ide.codegen.ereignis import leere_handler_methode_entfernen

        klassenname = type(self.formular).__name__
        neu = quelltext
        for name in sorted(methoden(geloescht) - methoden(bleibende)):
            # Wird die Methode irgendwo aufgerufen, gehört sie nicht
            # mehr nur zur Komponente.
            if len(re.findall(rf"\b{re.escape(name)}\b", neu)) > 1:
                continue
            ohne = leere_handler_methode_entfernen(neu, klassenname, name)
            if ohne is not None:
                neu = ohne
        if neu == quelltext:
            return None
        return _UnitTauschKommando(self, quelltext, neu)

    def duplizieren(self, komponente: Any = None) -> Any:
        """Eine Kopie von `komponente` im selben Behälter, ein
        Rasterschritt nach rechts unten versetzt.

        Derselbe Weg wie Kopieren und Einfügen (Punkt 121). Vorher
        übernahm die Kopie nur die einfachen Eigenschaften: Einträge
        einer Liste, Zeilen eines Memos, Menüeinträge, Schrift und der
        Inhalt eines Panels fehlten, und die Kopie eines Knopfs aus
        einem Panel lag auf dem Formular. Die Ereignisse bleiben mit
        denselben Methoden verknüpft; die stehen in der Unit dieses
        Formulars. Das Klappmenü bleibt ebenfalls (Punkt 172).

        Ohne `komponente` ist die Auswahl gemeint; bei einer
        Mehrfachauswahl (Strg+D) wird jede ausgewählte Komponente
        verdoppelt, in einem Rückgängig-Schritt (Punkt 180). Zurück
        kommt dann die Kopie der zuletzt gewählten."""
        if komponente is None and len(self._mehrfach) > 1:
            neu: list[tuple[str, Any, bool]] = []
            for k in self._obenauf(self._mehrfach):
                eintrag, verknuepft = self._duplikat_eintrag(k)
                neu += self._eintraege_bauen(
                    [eintrag], k.eltern or self.formular, verknuepft
                )
            oben = self._gebaute_einsetzen(neu)
            return oben[-1] if oben else None

        ziel = komponente if komponente is not None else self.ausgewaehlte_komponente
        if ziel is None or ziel is self.formular:
            return None
        eintrag, verknuepft = self._duplikat_eintrag(ziel)
        eltern = ziel.eltern or self.formular
        neu_oben = self._eintraege_einsetzen([eintrag], eltern, verknuepft)
        return neu_oben[0] if neu_oben else None

    def _duplikat_eintrag(
        self, komponente: Any
    ) -> tuple[dict[str, Any], dict[str, dict[str, str]]]:
        """Der Eintrag für die Kopie von `komponente`, schon versetzt,
        und die Ereignisse daraus, nach den Namen der Einträge."""
        from ide.designer.pfm_schreiben import _namen_der_komponenten, kind_als_dict

        eintrag = kind_als_dict(
            self._attributname(komponente),
            komponente,
            _namen_der_komponenten(self.formular),
        )
        eintrag["properties"]["left"] = komponente.left + self.raster
        eintrag["properties"]["top"] = komponente.top + self.raster
        verknuepft = _ereignisse_sammeln([eintrag])
        _ereignisse_entfernen(eintrag)
        return eintrag, verknuepft

    # -- Reihenfolge (Punkt 61) ---------------------------------------

    def _geschwister(self, komponente: Any) -> list[str]:
        eltern = getattr(komponente, "eltern", None) or self.formular
        return [name for name, _ in kind_komponenten(eltern)]

    def tab_reihenfolge_verschieben(self, komponente: Any, schritt: int) -> bool:
        """Eine Stelle früher (`schritt=-1`) oder später (`+1`) in der
        Tab-Reihenfolge ihres Behälters. `False`, wenn es nicht weiter
        geht."""
        if komponente is None or komponente is self.formular:
            return False
        name = self._attributname(komponente)
        vorher = self._geschwister(komponente)
        if name not in vorher:
            return False
        stelle = vorher.index(name)
        ziel = stelle + schritt
        if not 0 <= ziel < len(vorher):
            return False
        nachher = list(vorher)
        nachher.insert(ziel, nachher.pop(stelle))
        self.kommandos.ausfuehren(_ReihenfolgeKommando(self, vorher, nachher))
        self._nach_aenderung(komponente)
        return True

    def tab_reihenfolge_nach_lage(self) -> bool:
        """Ordnet die Komponenten jedes Behälters in Lesereihenfolge:
        zeilenweise von oben nach unten, in einer Zeile von links nach
        rechts - dieselbe Regel, nach der die Design-Prüfung
        `bedienbarkeit.tab_reihenfolge` meldet. `False`, wenn schon
        alles stimmt."""
        from ide.lint.regeln import lesereihenfolge

        vorher: list[str] = []
        nachher: list[str] = []
        behaelter = [self.formular]
        while behaelter:
            eltern = behaelter.pop(0)
            kinder = kind_komponenten(eltern)
            behaelter.extend(k for _, k in kinder)
            if len(kinder) < 2:
                continue
            geordnet = lesereihenfolge(
                kinder, lambda eintrag: (eintrag[1].left, eintrag[1].top)
            )
            vorher.extend(name for name, _ in kinder)
            nachher.extend(name for name, _ in geordnet)
        if vorher == nachher:
            return False
        self.kommandos.ausfuehren(_ReihenfolgeKommando(self, vorher, nachher))
        self._nach_aenderung(self.formular)
        return True

    def komponente_platzieren(self, typ: type, x: int, y: int) -> Any:
        """Platziert eine neue Komponente aus der Palette an Formular-
        Koordinaten (x, y) (Abschnitt 7.3). `tun()` des Kommandos wählt
        sie über `_komponente_wiederherstellen()` bereits aus."""
        kommando = _PlatzierenKommando(self, typ, x, y)
        self.kommandos.ausfuehren(kommando)
        self._nach_aenderung(kommando.neue_komponente)
        return kommando.neue_komponente

    def methode_beobachten(
        self, beobachter: Callable[[Path, str, str, tuple], None]
    ) -> None:
        """Meldet nach `ereignis_handler_erzeugen` Unit, Klasse, Methode
        und Parameter - für neue wie für schon vorhandene Methoden."""
        self._methoden_beobachter.append(beobachter)

    def _methode_melden(self, methodenname: str, ereignis_name: str) -> None:
        if self.unit_pfad is None:
            return
        klassenname = type(self.formular).__name__
        parameter = tuple(EREIGNIS_PARAMETER.get(ereignis_name, ()))
        for beobachter in self._methoden_beobachter:
            beobachter(self.unit_pfad, klassenname, methodenname, parameter)

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

        Das Bild steht als `picture` in der `.pfm`, als Pfad relativ zum
        Projektordner (Punkt 57), und erscheint im gestarteten Programm
        ohne eine Zeile Code."""
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
        (Abschnitt 7.3) – Ergänzung zum bisherigen
        Doppelklick (der immer mittig platziert). `typ=None` bricht den
        Modus ab (z. B. Escape). Der nächste Klick auf das Formular oder
        eine seiner Komponenten platziert `typ` genau dort und beendet
        den Modus wieder automatisch - ein „Anheften“, das mehrere
        Komponenten desselben Typs hintereinander setzt, gibt es
        nicht."""
        self._platzierungs_typ = typ
        cursor = Qt.CursorShape.CrossCursor if typ is not None else Qt.CursorShape.ArrowCursor
        self.formular._qwidget.setCursor(cursor)
        # Escape soll das Platzieren beenden, auch wenn der Fokus noch
        # auf der Palette liegt, auf die eben geklickt wurde. Deshalb
        # wacht ein eigener Filter an der ganzen Anwendung, solange der
        # Modus läuft (Punkt 122).
        anwendung = QApplication.instance()
        if anwendung is None:
            return
        if typ is not None:
            anwendung.installEventFilter(self._escape_wache)
        else:
            anwendung.removeEventFilter(self._escape_wache)

    def _platzierung_bei_klick_ausfuehren(
        self, beobachtetes_objekt: QObject, ereignis: Any
    ) -> None:
        typ = self._platzierungs_typ
        self.platzierungsmodus_setzen(None)
        if typ is None:
            return

        # Die Klickstelle gilt im getroffenen Widget. Auf das Formular
        # umgerechnet wird sie mit `mapTo`: `left`/`top` eines Knopfs in
        # einem Panel zählen ab der Ecke des Panels, und die neue
        # Komponente landete mit der alten Rechnung auf dem Formular
        # an einer Stelle, die mit dem Klick nichts zu tun hatte
        # (Punkt 122). Den Behälter an dieser Stelle sucht dann
        # `_PlatzierenKommando` über `_behaelter_bei`.
        position = ereignis.position().toPoint()
        if isinstance(beobachtetes_objekt, QWidget):
            punkt = beobachtetes_objekt.mapTo(self.formular._qwidget, position)
        else:
            punkt = position
        self.komponente_platzieren(typ, punkt.x(), punkt.y())

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
        # `class` oder `for` sind Bezeichner im Sinne von
        # `isidentifier()`, im erzeugten `self.class = Edit(self)` aber
        # ein Syntaxfehler, und das Programm startet nicht (Punkt 120).
        if keyword.iskeyword(neuer_name):
            raise ValueError(
                f"{neuer_name!r} ist ein Schlüsselwort von Python und "
                "kann kein Name sein."
            )

        alter_name = self._attributname(komponente)
        if neuer_name == alter_name:
            return
        if neuer_name in vars(self.formular):
            raise ValueError(f"Der Name {neuer_name!r} wird bereits verwendet.")
        # Eigenschaften und Methoden der Formularklasse stehen nicht in
        # `vars(self.formular)`. Eine Komponente namens `caption`
        # scheiterte an der Typprüfung des Props, eine namens `show`
        # verdeckte die Methode, und `form.show()` rief im Programm
        # ein Edit auf (Punkt 113).
        if hasattr(type(self.formular), neuer_name):
            raise ValueError(
                f"{neuer_name!r} ist bereits eine Eigenschaft oder "
                "Methode des Formulars."
            )
        # Die Klasse kennt nur die Methoden vom Öffnen des Designers.
        # Eine danach in der Unit geschriebene Methode `berechnen`
        # verdeckte sonst ein Knopf `self.berechnen` (Punkt 173).
        texte = self._unit_quelltexte()
        vorhandene_methoden = self._unit_methodennamen(texte)
        if neuer_name in vorhandene_methoden:
            raise ValueError(
                f"{neuer_name!r} ist bereits eine Methode in "
                f"{self.unit_pfad.name}."
            )

        kommando = _UmbenennenKommando(self, komponente, neuer_name)
        if kommando.umbenannte_methoden and self.unit_pfad is not None:
            # Erst prüfen, dann ändern (Punkt 141): scheitert das
            # Umbenennen der Methoden an einem Syntaxfehler, bleibt
            # alles, wie es war - das Formular, die `.pfm` und der
            # Rückgängig-Stapel.
            meldung = self._syntaxfehler_melden(
                texte,
                "Die Komponente lässt sich erst umbenennen, wenn er "
                "behoben ist.",
            )
            if meldung is not None:
                raise ValueError(meldung)
            # Ebenso ein Schreibschutz und eine Unit, die nicht in
            # UTF-8 gespeichert ist (Punkte 255 und 256).
            folge = "Die Komponente lässt sich deshalb nicht umbenennen."
            meldung = self._unit_nicht_beschreibbar(folge)
            if meldung is not None:
                raise ValueError(meldung)
            if self.unit_pfad.exists():
                try:
                    unit_lesen(self.unit_pfad)
                except UnicodeDecodeError:
                    raise ValueError(
                        f"„{self.unit_pfad.name}“ ist nicht in UTF-8 "
                        f"gespeichert. {folge}"
                    ) from None
            # Steht die neue Methode schon in der Unit, etwa von einer
            # gelöschten Komponente gleichen Namens, gäbe es sie danach
            # zweimal, und Python benutzte nur die zweite (Punkt 140).
            for _, _, neu in kommando.umbenannte_methoden:
                if neu in vorhandene_methoden:
                    raise ValueError(
                        f"In {self.unit_pfad.name} steht schon eine Methode "
                        f"{neu!r}. Solange es sie gibt, lässt sich die "
                        f"Komponente nicht in {neuer_name!r} umbenennen."
                    )
        try:
            self.kommandos.ausfuehren(kommando)
        except OSError as fehler:
            # Das Kommando hat sich selbst zurückgesetzt und steht
            # nicht auf dem Stapel.
            raise ValueError(
                f"„{self.unit_pfad.name}“ konnte nicht gespeichert "
                f"werden: {fehler}. Die Komponente behält ihren Namen."
            ) from fehler
        self._nach_aenderung(komponente, sofort=True)

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

        from ide.inspector.menue_editor import MenueEditor, menue_methode_anlegen

        dialog = MenueEditor(
            komponente.entries,
            self.formular._qwidget.window(),
            methode_anlegen=lambda name: menue_methode_anlegen(self, name),
        )
        # Gegen `QDialog.DialogCode` und nicht gegen `MenueEditor`
        # selbst: so lässt sich der Dialog in einem Test durch einen
        # Platzhalter ersetzen, ohne dass hier etwas fehlt.
        angenommen = dialog.exec() == QDialog.DialogCode.Accepted
        if not angenommen and not dialog.uebernommen:
            return True
        self.kommandos.ausfuehren(EigenschaftKommando(komponente, {"entries": dialog.eintraege()}))
        self._nach_aenderung(komponente)
        return True

    def ereignis_handler_erzeugen(
        self, komponente: Any, ereignis_name: str | None = None
    ) -> str | None:
        """Erzeugt bei Bedarf eine Ereignis-Methode und verknüpft sie.

        Ohne `ereignis_name` ist das kennzeichnende Ereignis gemeint -
        der Doppelklick auf die Komponente im Designer (Abschnitt 4.4).
        Mit Namen ist genau dieses Ereignis gemeint; so ruft der Reiter
        „Ereignisse" des Objektinspektors an, wo jede Zeile für sich
        steht. Geschrieben wird per `libcst`, also ohne dass die
        Formatierung der Unit leidet.

        Ohne zugrunde liegende `.pfm`-Datei oder ohne eindeutiges
        Standardereignis passiert nichts (`None`). Bereits verknüpfte
        Ereignisse werden nicht erneut erzeugt, nur der vorhandene Name
        geliefert. Hat die Unit einen Syntaxfehler, erscheint eine
        Meldung, und es kommt ebenfalls `None` zurück.
        """
        if self.unit_pfad is None:
            return None
        if ereignis_name is None:
            ereignis_name = _standard_ereignis(type(komponente))
        if ereignis_name is None or ereignis_name not in ereignisse(type(komponente)):
            return None

        vorhandener_handler = getattr(komponente, ereignis_name)
        if vorhandener_handler is not None:
            self._methode_melden(vorhandener_handler.__name__, ereignis_name)
            return vorhandener_handler.__name__

        if komponente is self.formular:
            # das Formular selbst heißt im generierten Code nicht nach der
            # Klasse, sondern immer "form" (Abschnitt 4.4: form_create)
            komponenten_name = "form"
        else:
            komponenten_name = self._attributname(komponente) or type(komponente).__name__.lower()
        methodenname = f"{komponenten_name}_{_ereignis_kurzname(ereignis_name)}"

        klassenname = type(self.formular).__name__
        folge = "Die Methode lässt sich deshalb nicht anlegen."
        meldung = self._unit_nicht_beschreibbar(folge)
        if meldung is not None:
            self._meldung_zeigen(meldung)
            return None
        quelltext = self._unit_lesen_oder_melden(folge)
        if quelltext is None:
            return None
        # Eine Unit mit Syntaxfehler kann `libcst` nicht umschreiben.
        # Gemeldet wird das vorher, mit der Zeile, statt mit einem
        # `ParserSyntaxError` in der allgemeinen Fehlermeldung
        # (Punkt 141). Geändert ist dann noch nichts. Geprüft werden
        # auch die offenen Editoren: eine ungespeicherte, angefangene
        # Zeile dort ließ sonst das Einfügen in den Editor scheitern,
        # nachdem Datei und `.pfm` die Methode schon hatten.
        meldung = self._syntaxfehler_melden(
            [
                quelltext,
                *(e.toPlainText() for e in self._offene_unit_editoren()),
            ],
            "Die Methode lässt sich erst anlegen, wenn er behoben ist.",
        )
        if meldung is not None:
            self._meldung_zeigen(meldung)
            return None
        from ide.codegen.ereignis import handler_methode_einfuegen

        neuer_quelltext = handler_methode_einfuegen(
            quelltext,
            klassenname,
            methodenname,
            EREIGNIS_PARAMETER.get(ereignis_name, ()),
        )
        if not self._unit_schreiben(neuer_quelltext, folge):
            return None

        gebundene_methode = types.MethodType(platzhalter_erzeugen(methodenname), self.formular)
        setattr(self.formular, methodenname, gebundene_methode)

        self.kommandos.ausfuehren(
            _MethodeAnlegenKommando(
                self,
                EigenschaftKommando(komponente, {ereignis_name: gebundene_methode}),
                quelltext,
                unit_lesen(self.unit_pfad),
            )
        )
        self._nach_aenderung(komponente, sofort=True)
        self._methode_melden(methodenname, ereignis_name)
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

    def _offene_unit_editoren(self) -> list[QPlainTextEdit]:
        """Die Editoren, in denen die Unit dieses Formulars gerade
        offen ist. Das Hauptfenster hängt den Dateipfad jedes Editors
        als Qt-Eigenschaft „pfad“ an das Widget; darüber findet der
        Designer sie, ohne das Hauptfenster zu kennen."""
        if self.unit_pfad is None:
            return []
        gesucht = _pfad_schluessel(self.unit_pfad)
        return [
            widget
            for widget in QApplication.allWidgets()
            if isinstance(widget, QPlainTextEdit)
            and widget.property("pfad")
            and _pfad_schluessel(widget.property("pfad")) == gesucht
        ]

    def _unit_quelltexte(self) -> list[str]:
        """Die Unit, wie sie auf der Platte steht, und wie sie in jedem
        offenen Editor steht."""
        texte = []
        if self.unit_pfad is not None and self.unit_pfad.exists():
            try:
                texte.append(unit_lesen(self.unit_pfad))
            except (OSError, ValueError):
                pass
        texte.extend(editor.toPlainText() for editor in self._offene_unit_editoren())
        return texte

    def _syntaxfehler_melden(self, texte: list[str], folge: str) -> str | None:
        """Die Meldung zum ersten Syntaxfehler in `texte`, oder `None`.
        `folge` sagt, was deshalb gerade nicht geht."""
        from ide.codegen.ereignis import syntaxfehler_zeile

        for text in texte:
            zeile = syntaxfehler_zeile(text)
            if zeile is not None:
                return (
                    f"{self.unit_pfad.name} hat in Zeile {zeile} einen "
                    f"Syntaxfehler. {folge}"
                )
        return None

    def _unit_nicht_beschreibbar(self, folge: str) -> str | None:
        """Die Meldung, wenn die Unit schreibgeschützt ist, sonst
        `None`. `folge` sagt, was deshalb nicht geht.

        Geprüft wird vor jeder Änderung und nicht erst beim Schreiben
        (Punkt 255): das Umbenennen hatte die Komponente am Formular
        schon umbenannt, als das Schreiben der Unit scheiterte. Material
        der Lehrkraft auf einem Netzlaufwerk ohne Schreibrecht oder ein
        aus einem ZIP-Anhang kopierter Ordner sind an einer Schule keine
        Seltenheit.
        """
        pfad = self.unit_pfad
        if pfad is None or not pfad.exists() or os.access(pfad, os.W_OK):
            return None
        return (
            f"„{pfad.name}“ ist schreibgeschützt. {folge}\n\n"
            "Häufige Gründe: die Datei liegt auf einem Netzlaufwerk "
            "ohne Schreibrecht, oder sie stammt von einer CD oder aus "
            "einem ZIP-Anhang und trägt noch den Schreibschutz. In den "
            "Eigenschaften der Datei lässt er sich abschalten."
        )

    def _unit_lesen_oder_melden(self, folge: str) -> str | None:
        """Die Unit von der Platte, oder `None` nach einer Meldung.

        Eine Unit in Windows-1252 („ANSI“) endete bis Punkt 256 mit
        `UnicodeDecodeError` in der allgemeinen Fehlermeldung. Sie wird
        jetzt gemeldet und nicht umgedeutet: als cp1252 zu lesen und als
        UTF-8 zurückzuschreiben, änderte die Kodierung einer Datei
        stillschweigend, und ob sie wirklich cp1252 ist, lässt sich an
        den Bytes nicht sicher erkennen. Der Editor öffnet sie aus
        demselben Grund nicht.
        """
        try:
            return unit_lesen(self.unit_pfad)
        except UnicodeDecodeError:
            self._meldung_zeigen(
                f"„{self.unit_pfad.name}“ ist nicht in UTF-8 gespeichert. "
                f"{folge}\n\n"
                "Abhilfe: die Datei im Editor von Windows öffnen und über "
                "„Speichern unter“ mit der Codierung „UTF-8“ neu speichern."
            )
        except OSError as fehler:
            self._meldung_zeigen(
                f"„{self.unit_pfad.name}“ lässt sich nicht lesen:\n"
                f"{fehler}\n\n{folge}"
            )
        return None

    def _unit_schreiben(self, quelltext: str, folge: str) -> bool:
        """Schreibt die Unit. Liefert, ob es geklappt hat; sonst steht
        eine Meldung da, und nichts ist geändert.

        Der Schreibschutz ist vorher geprüft. Ein Netzlaufwerk kann das
        Schreiben aber auch ohne ihn verweigern, und ein Virenscanner
        kann die Datei gerade halten."""
        vorher = dateistand.kennung(self.unit_pfad)
        try:
            atomar_schreiben(self.unit_pfad, quelltext, encoding="utf-8")
        except OSError as fehler:
            self._meldung_zeigen(
                f"„{self.unit_pfad.name}“ konnte nicht gespeichert "
                f"werden:\n{fehler}\n\n{folge}"
            )
            return False
        # Die neue Methode kommt nur in die Editoren dieses Fensters
        # (`_zur_methode_springen` im Hauptfenster).
        self._unit_stand_nachfuehren(vorher, nur_eigenes_fenster=True)
        return True

    def _unit_stand_nachfuehren(
        self, vorher: str, *, nur_eigenes_fenster: bool = False
    ) -> None:
        """Nach dem Schreiben der Unit durch den Designer: Editoren,
        die die Unit im Stand `vorher` kannten, kennen jetzt den neuen.
        Die Änderung kommt aus Natter selbst und landet auch im Text
        des Editors; beim nächsten Speichern wird deshalb nicht
        gefragt (Punkt 286). Ein Editor, dessen Datei schon vorher von
        außen geändert war, behält seinen alten Stand, und die
        Nachfrage kommt weiterhin.

        Die Formularklasse liest die Unit beim nächsten Abgleich neu,
        auch wenn Änderungszeit und Größe gleich geblieben sind. Das
        kann vorkommen, weil Windows die Änderungszeit nur in Schritten
        von einigen Millisekunden fortschreibt, und ein Umbenennen
        ändert die Größe nicht, wenn beide Namen gleich lang sind."""
        if "_unit_stand" in vars(type(self.formular)):
            type(self.formular)._unit_stand = None
        nachher = dateistand.kennung(self.unit_pfad)
        fenster = self.formular._qwidget.window()
        for editor in self._offene_unit_editoren():
            if nur_eigenes_fenster and editor.window() is not fenster:
                continue
            if editor.property(dateistand.EIGENSCHAFT) == vorher:
                editor.setProperty(dateistand.EIGENSCHAFT, nachher)

    def _unit_methodennamen(self, texte: list[str]) -> set[str]:
        """Die Methoden der Formularklasse, frisch aus der Unit
        gelesen. Die Klasse im Designer kennt nur, was beim Öffnen
        dastand (Punkt 173)."""
        klassenname = type(self.formular).__name__
        namen: set[str] = set()
        for text in texte:
            namen |= set(methoden_im_quelltext(text, klassenname) or {})
        return namen

    def _methoden_nachladen(self) -> None:
        """Gleicht die Methoden der Formularklasse mit der Unit ab
        (`ide.designer.laden.unit_methoden_ergaenzen`)."""
        nachladen = getattr(type(self.formular), "_methoden_nachladen", None)
        if nachladen is not None:
            nachladen()

    def _meldung_zeigen(self, text: str) -> None:
        QMessageBox.warning(self.formular._qwidget.window(), "Formular-Designer", text)

    def _handler_umhaengen(self, von: str, nach: str) -> None:
        """Lässt jeden Verweis auf die Methode `von` auf `nach` zeigen:
        an allen Komponenten, am Formular selbst und in den Einträgen
        der Menüs (Punkt 147)."""
        objekte = [self.formular] + [
            k for k in vars(self.formular).values() if isinstance(k, Control)
        ]
        neu = types.MethodType(platzhalter_erzeugen(nach), self.formular)
        for objekt in objekte:
            for ereignis_name in ereignisse(type(objekt)):
                handler = getattr(objekt, ereignis_name, None)
                if handler is not None and getattr(handler, "__name__", None) == von:
                    setattr(objekt, ereignis_name, neu)
            # Ein Menüeintrag trägt den Namen der Methode. Geändert wird
            # der Baum im Menü selbst: die Zuweisung an `entries` prüfte
            # außerhalb des Designers, ob es die Methode schon gibt.
            baum = getattr(objekt, "_eintraege", None)
            if isinstance(baum, list) and _menue_handler_umbenennen(baum, von, nach):
                objekt._menue_erneuern()
        # `ereignis_handler_erzeugen` legt die Methode auch am Formular
        # ab; dort gehört sie unter den neuen Namen.
        if isinstance(vars(self.formular).get(von), types.MethodType):
            delattr(self.formular, von)
            setattr(self.formular, nach, neu)

    def name_von(self, komponente: Any) -> str | None:
        """Der Name (Formular-Attribut) von `komponente`, z. B.
        `"b_anmelden"` – für den Objektinspektor (Abschnitt 7.6), der
        `caption`/`text` (Anzeigetext) und `name` (Bezeichner im Code)
        auseinanderhält."""
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
        # Auch die Namen der Formularklasse: sonst bekäme eine neue
        # Komponente denselben Namen wie eine Eigenschaft des Formulars.
        while name in vorhandene or hasattr(type(self.formular), name):
            name = f"{basis}{zaehler}"
            zaehler += 1
        return name

    def _benachrichtigen(self, komponente: Any) -> None:
        self._anfasser_aktualisieren()
        self._rahmen_aktualisieren()
        for beobachter in self._auswahl_beobachter:
            beobachter(komponente)

    def _nach_aenderung(
        self, komponente: Any, *, sofort: bool = False
    ) -> None:
        """Nach jeder Änderung am Formular.

        Rahmen, Anfasser und Objektinspektor folgen sofort. Schreiben,
        Codegen, Design-Prüfung und Komponentenbaum laufen erst kurz
        nach der letzten Änderung einer Folge, einmal für alle
        zusammen. Bis Punkt 312 lief das alles nach jedem einzelnen
        Schritt; mit 200 Komponenten brauchte eine Pfeiltaste eine
        Sekunde und zwanzigmal Rückgängig über zwanzig Sekunden.

        `sofort` gilt für Änderungen, die im selben Zug die Unit auf
        der Platte schreiben (Umbenennen, neue Ereignis-Methode). Die
        `.pfm` folgt dann ohne Wartezeit, damit beide Dateien
        zueinander passen, auch wenn Natter kurz danach abbricht.
        """
        self._benachrichtigen(komponente)
        self.schreiben_ausstehend = True
        if sofort:
            self.jetzt_schreiben()
        else:
            self._schreib_uhr.start()

    def jetzt_schreiben(self) -> bool:
        """Schreibt eine ausstehende Änderung sofort und benachrichtigt
        die Beobachter. Liefert, ob die Dateien auf dem Stand des
        Designers sind.

        Wer `.pfm` oder `_design.py` lesen oder das Formular schließen
        will, ruft das vorher auf: beim Speichern, Starten, Exportieren,
        Schließen eines Reiters oder des Fensters und beim Wechsel des
        Projekts. Ohne ausstehende Änderung geschieht nichts.
        """
        if not self.schreiben_ausstehend:
            return not self.ungespeichert
        self._schreib_uhr.stop()
        self.schreiben_ausstehend = False
        gespeichert = self.speichern() if self.pfm_pfad is not None else True
        for beobachter in self._aenderung_beobachter:
            beobachter()
        return gespeichert

    def speichern(self) -> bool:
        """Schreibt `.pfm` und `_design.py`. Liefert, ob es geklappt hat.

        Ein Schreibfehler (Formular auf einem schreibgeschützten
        Netzlaufwerk, abgezogener USB-Stick, vom Virenscanner gesperrte
        Datei) endete bis Punkt 235 als Ausnahme mitten im Designer.
        Die Änderung stand danach im Designer und im Rückgängig-Stapel,
        aber nicht auf der Platte, und Komponentenbaum und Prüfung
        erfuhren nichts mehr davon. Jetzt wird der Fehler einmal
        gemeldet, bis das Schreiben wieder klappt, und `ungespeichert`
        bleibt wahr, damit der Reiter die Änderung als nicht
        gespeichert führt.
        """
        if self.pfm_pfad is None:
            return True
        # Ein zweites Natter-Fenster auf demselben Projekt schreibt
        # dieselbe `.pfm`. Ohne diese Prüfung überschrieb jede Änderung
        # hier dessen Stand ohne Nachfrage (Punkt 286). Die
        # `_design.py` entsteht aus der `.pfm` und braucht keine
        # eigene Prüfung.
        if dateistand.von_aussen_geaendert(
            self.pfm_stand, self.pfm_pfad
        ) and (
            self.ueberschreiben_abgelehnt
            or not self._von_aussen_geaendert_fragen()
        ):
            self.ueberschreiben_abgelehnt = True
            self.ungespeichert = True
            return False
        self.ueberschreiben_abgelehnt = False
        try:
            formular_als_pfm_speichern(self.formular, self.pfm_pfad)
            self.pfm_stand = dateistand.kennung(self.pfm_pfad)
            # Real gefunden (beim Nachbauen eines Referenzprojekts):
            # ohne dies blieb `u_..._design.py` nach der ersten
            # Projekterzeugung für immer auf dem allerersten Stand
            # stehen - der Designer selbst zeigte jede Änderung korrekt
            # (er rendert direkt aus dem Live-Formular), aber das
            # tatsächlich laufende Schülerprogramm (`create_components()`
            # in der generierten Design-Datei) sah neue/verschobene/
            # geänderte Komponenten nie.
            design_datei_erzeugen(self.pfm_pfad, self._design_pfad())
        except OSError as fehler:
            self.ungespeichert = True
            if not self._schreibfehler_gemeldet:
                self._schreibfehler_gemeldet = True
                self._meldung_zeigen(
                    f"„{self.pfm_pfad.name}“ konnte nicht gespeichert "
                    f"werden:\n{fehler}\n\n"
                    "Die Änderung steht im Designer, aber nicht in der "
                    "Datei. Gespeichert wird wieder, sobald die Datei "
                    "beschreibbar ist, spätestens mit Strg+S.\n\n"
                    "Häufige Gründe: der USB-Stick ist abgezogen, die "
                    "Datei ist schreibgeschützt oder in einem anderen "
                    "Programm geöffnet."
                )
            return False
        self.ungespeichert = False
        self._schreibfehler_gemeldet = False
        return True

    def _verwendung_in_der_unit(
        self, komponenten: list[Any]
    ) -> tuple[str, int] | None:
        """Der erste Name unter `komponenten` (samt Inhalt von
        Behältern), den die Unit als `self.<name>` benutzt, mit der
        Zeile. Der Text im offenen Editor geht dem auf der Platte vor,
        er ist der neuere."""
        namen: list[str] = []
        for komponente in komponenten:
            name = self._attributname(komponente)
            if name is not None:
                namen.append(name)
            namen.extend(n for n, _ in _inhalt(komponente))
        if not namen:
            return None
        for text in reversed(self._unit_quelltexte()):
            for nummer, zeile in enumerate(text.splitlines(), start=1):
                for name in namen:
                    if re.search(rf"\bself\.{re.escape(name)}\b", zeile):
                        return name, nummer
        return None

    def _loeschen_trotz_verwendung(self, komponenten: list[Any]) -> bool:
        verwendung = self._verwendung_in_der_unit(komponenten)
        if verwendung is None:
            return True
        name, zeile = verwendung
        return self._loeschen_trotzdem_fragen(name, zeile)

    def _loeschen_trotzdem_fragen(self, name: str, zeile: int) -> bool:
        """Ob `name` trotz der Verwendung in der Unit gelöscht werden
        soll. Eigene Methode, damit Tests die Antwort vorgeben
        können."""
        antwort = QMessageBox.question(
            self.formular._qwidget.window(),
            "Formular-Designer",
            f"„{name}“ wird in {self.unit_pfad.name} in Zeile {zeile} "
            "benutzt. Ohne die Komponente bricht das Programm an dieser "
            "Stelle ab.\n\nTrotzdem löschen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return antwort == QMessageBox.StandardButton.Yes

    def _von_aussen_geaendert_fragen(self) -> bool:
        """Ob die von außen geänderte `.pfm` überschrieben werden
        soll. Eigene Methode, damit Tests die Antwort vorgeben
        können."""
        antwort = QMessageBox.question(
            self.formular._qwidget.window(),
            "Formular-Designer",
            f"„{self.pfm_pfad.name}“ wurde seit dem Öffnen außerhalb "
            "dieses Fensters geändert, zum Beispiel in einem zweiten "
            "Natter-Fenster.\n\nMit der Änderung aus dem Designer "
            "überschreiben? Die andere Änderung geht dabei verloren.\n\n"
            "Bei „Nein“ bleibt die Änderung nur im Designer. Um den "
            "Stand von der Platte zu übernehmen, den Designer-Reiter "
            "ohne Speichern schließen und das Formular neu öffnen.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return antwort == QMessageBox.StandardButton.Yes

    def _design_pfad(self) -> Path:
        """`u_main.pfm` -> `u_main_design.py` (Namenskonvention aus
        `ide/project/neu.py`)."""
        return self.pfm_pfad.parent / f"{self.pfm_pfad.stem}_design.py"
