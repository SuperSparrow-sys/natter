"""DesignerCanvas: zeigt ein Formular mit echten `pcl`-Komponenten,
Klick/Ziehen/Tastatur bearbeiten es statt die echte Interaktion
auszulösen. Jede Änderung läuft über ein Kommando (Undo/Redo).

Siehe konzept-natter.md, Abschnitt 7.7: „Der Designer rendert echte
pcl-Komponenten“, Tastenkürzel wie dort beschrieben (Pfeiltasten =
Rasterschritt, Alt+Pfeil = 1 px, Umschalt+Pfeil = Größe, Entf = löschen,
Strg+D = duplizieren, dazu Strg+Z/Strg+Umschalt+Z bzw. Strg+Y für
Rückgängig/Wiederholen, Command-Pattern). `komponente_platzieren()` ist
das Gegenstück für die Komponentenpalette (Abschnitt 7.3). Sichtbare
Größenanfasser zum Ziehen (statt nur Tastatur) sind eine spätere
Verfeinerung.
"""

from __future__ import annotations

import types
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import QEvent, QObject, QPoint, Qt
from PySide6.QtWidgets import QWidget

from ide.codegen.ereignis import handler_methode_einfuegen
from ide.designer.kommando import EigenschaftKommando, Kommandostapel
from ide.designer.laden import platzhalter_erzeugen
from ide.designer.pfm_schreiben import formular_als_pfm_speichern
from ide.inspector.komponentenbaum import kind_komponenten
from pcl.form import Form
from pcl.properties import eigenschaften, ereignisse

# Wird einmal an das Stylesheet des Formulars angehängt (kaskadiert zu
# allen Kindern, Abschnitt 6) statt einzelne Widget-Stylesheets zu
# überschreiben – so bleibt das Theme des Formulars unangetastet.
_AUSWAHL_REGEL = '\n*[design_ausgewaehlt="true"] { border: 2px solid #0067c0; }'
_MARKIERUNGS_EIGENSCHAFT = "design_ausgewaehlt"
RASTER = 8


def _standard_ereignis(typ: type) -> str | None:
    """Das Ereignis, das ein Doppelklick verknüpft (Abschnitt 4.4).
    Nur eindeutig, wenn der Komponententyp genau ein Ereignis hat -
    Komponenten ohne oder mit mehreren Ereignissen liefern `None`."""
    events = ereignisse(typ)
    return next(iter(events)) if len(events) == 1 else None


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


class _PlatzierenKommando:
    """Wie `_DuplizierenKommando`, aber mit einer frischen Komponente in
    Standardwerten statt einer Kopie (Abschnitt 7.3: Palette → Formular)."""

    def __init__(self, canvas: DesignerCanvas, typ: type, x: int, y: int) -> None:
        self.canvas = canvas
        self.name = canvas._eindeutigen_namen_finden(typ.__name__.lower())

        self.neue_komponente = typ(canvas.formular)
        self.neue_komponente.left = x
        self.neue_komponente.top = y

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
        self._widget_zu_komponente: dict[QWidget, Any] = {}
        self._ziehen_komponente: Any = None
        self._ziehen_start: QPoint | None = None
        self._ziehen_start_werte: dict[str, Any] | None = None

        formular._qwidget.setStyleSheet(formular._qwidget.styleSheet() + _AUSWAHL_REGEL)
        self._ueberwachung_einrichten(formular)

    def _ueberwachung_einrichten(self, objekt: Any) -> None:
        widget = objekt._qwidget
        self._widget_zu_komponente[widget] = objekt
        widget.installEventFilter(self)
        for _, komponente in kind_komponenten(objekt):
            self._ueberwachung_einrichten(komponente)

    # -- Ereignisse -----------------------------------------------------

    def eventFilter(self, beobachtetes_objekt: QObject, ereignis: QEvent) -> bool:
        typ = ereignis.type()

        if typ == QEvent.Type.MouseButtonDblClick:
            # Qt schickt vor dem Doppelklick bereits einen normalen Press,
            # der einen Ziehvorgang gestartet haben könnte - den verwerfen.
            self._ziehen_komponente = None
            self._ziehen_start = None
            self._ziehen_start_werte = None
            komponente = self._widget_zu_komponente.get(beobachtetes_objekt)
            if komponente is not None and komponente is not self.formular:
                self.ereignis_handler_erzeugen(komponente)
            return True

        if typ == QEvent.Type.MouseButtonPress:
            komponente = self._widget_zu_komponente.get(beobachtetes_objekt)
            if komponente is not None:
                self._auswaehlen(komponente)
                if komponente is not self.formular:
                    self._ziehen_komponente = komponente
                    self._ziehen_start = ereignis.globalPosition().toPoint()
                    self._ziehen_start_werte = {"left": komponente.left, "top": komponente.top}
                return True  # Klick abfangen: keine echte Interaktion im Designer

        elif typ == QEvent.Type.MouseMove and self._ziehen_komponente is not None:
            aktuell = ereignis.globalPosition().toPoint()
            delta = aktuell - self._ziehen_start
            if delta.x() or delta.y():
                # Live-Vorschau während des Ziehens, noch kein Kommando
                self._ziehen_komponente.left += delta.x()
                self._ziehen_komponente.top += delta.y()
                self._ziehen_start = aktuell
            return True

        elif typ == QEvent.Type.MouseButtonRelease and self._ziehen_komponente is not None:
            self._ziehen_beenden()
            return True

        elif typ == QEvent.Type.KeyPress and self._tastatur_verarbeiten(ereignis):
            return True

        return False

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
        self.kommandos.rueckgaengig()
        self._benachrichtigen(self.ausgewaehlte_komponente or self.formular)

    def wiederholen(self) -> None:
        self.kommandos.wiederholen()
        self._benachrichtigen(self.ausgewaehlte_komponente or self.formular)

    # -- Auswahl ----------------------------------------------------------

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

    def _auswaehlen(self, komponente: Any) -> None:
        if self.ausgewaehlte_komponente is not None:
            self._markierung_setzen(self.ausgewaehlte_komponente._qwidget, False)
        self.ausgewaehlte_komponente = komponente
        self._markierung_setzen(komponente._qwidget, True)
        self._benachrichtigen(komponente)

    def _markierung_setzen(self, widget: QWidget, ausgewaehlt: bool) -> None:
        widget.setProperty(_MARKIERUNGS_EIGENSCHAFT, ausgewaehlt)
        widget.style().unpolish(widget)
        widget.style().polish(widget)

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

        komponenten_name = self._attributname(komponente) or type(komponente).__name__.lower()
        methodenname = f"{komponenten_name}_{ereignis_name}"

        klassenname = type(self.formular).__name__
        quelltext = self.unit_pfad.read_text(encoding="utf-8")
        neuer_quelltext = handler_methode_einfuegen(quelltext, klassenname, methodenname)
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
        komponente._qwidget.setParent(self.formular._qwidget)
        komponente._qwidget.show()
        setattr(self.formular, name, komponente)
        self._widget_zu_komponente[komponente._qwidget] = komponente
        self._auswaehlen(komponente)

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
        for beobachter in self._auswahl_beobachter:
            beobachter(komponente)

    def _nach_aenderung(self, komponente: Any) -> None:
        if self.pfm_pfad is not None:
            formular_als_pfm_speichern(self.formular, self.pfm_pfad)
        self._benachrichtigen(komponente)
