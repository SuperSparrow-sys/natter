"""DesignerCanvas: zeigt ein Formular mit echten `pcl`-Komponenten,
Klick/Ziehen/Tastatur bearbeiten es statt die echte Interaktion
auszulösen.

Siehe konzept-natter.md, Abschnitt 7.7: „Der Designer rendert echte
pcl-Komponenten.“ Tastenkürzel wie dort beschrieben: Pfeiltasten
(Rasterschritt), Alt+Pfeil (1 px), Umschalt+Pfeil (Größe), Entf
(löschen), Strg+D (duplizieren). Platzieren aus der Palette folgt mit
Schritt 6; Größenanfasser zum Ziehen (statt nur Tastatur) sind als
spätere Verfeinerung offen.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import QEvent, QObject, QPoint, Qt
from PySide6.QtWidgets import QWidget

from ide.designer.pfm_schreiben import formular_als_pfm_speichern
from ide.inspector.komponentenbaum import kind_komponenten
from pcl.form import Form
from pcl.properties import eigenschaften

# Wird einmal an das Stylesheet des Formulars angehängt (kaskadiert zu
# allen Kindern, Abschnitt 6) statt einzelne Widget-Stylesheets zu
# überschreiben – so bleibt das Theme des Formulars unangetastet.
_AUSWAHL_REGEL = '\n*[design_ausgewaehlt="true"] { border: 2px solid #0067c0; }'
_MARKIERUNGS_EIGENSCHAFT = "design_ausgewaehlt"
RASTER = 8


class DesignerCanvas(QObject):
    def __init__(self, formular: Form, pfm_pfad: Path | None = None) -> None:
        super().__init__()
        self.formular = formular
        self.pfm_pfad = Path(pfm_pfad) if pfm_pfad is not None else None
        self.ausgewaehlte_komponente: Any = None
        self._auswahl_beobachter: list[Callable[[Any], None]] = []
        self._widget_zu_komponente: dict[QWidget, Any] = {}
        self._ziehen_komponente: Any = None
        self._ziehen_start: QPoint | None = None

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

        if typ == QEvent.Type.MouseButtonPress:
            komponente = self._widget_zu_komponente.get(beobachtetes_objekt)
            if komponente is not None:
                self._auswaehlen(komponente)
                if komponente is not self.formular:
                    self._ziehen_komponente = komponente
                    self._ziehen_start = ereignis.globalPosition().toPoint()
                return True  # Klick abfangen: keine echte Interaktion im Designer

        elif typ == QEvent.Type.MouseMove and self._ziehen_komponente is not None:
            aktuell = ereignis.globalPosition().toPoint()
            delta = aktuell - self._ziehen_start
            if delta.x() or delta.y():
                self._ziehen_komponente.left += delta.x()
                self._ziehen_komponente.top += delta.y()
                self._ziehen_start = aktuell
            return True

        elif typ == QEvent.Type.MouseButtonRelease and self._ziehen_komponente is not None:
            self._nach_aenderung(self._ziehen_komponente)
            self._ziehen_komponente = None
            self._ziehen_start = None
            return True

        elif typ == QEvent.Type.KeyPress and self._tastatur_verarbeiten(ereignis):
            return True

        return False

    def _tastatur_verarbeiten(self, ereignis) -> bool:
        komponente = self.ausgewaehlte_komponente
        if komponente is None or komponente is self.formular:
            return False

        taste = ereignis.key()
        modifikatoren = ereignis.modifiers()

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
        ziel.left = ziel.left + dx
        ziel.top = ziel.top + dy
        self._nach_aenderung(ziel)

    def groesse_aendern(self, dw: int, dh: int, komponente: Any = None) -> None:
        ziel = komponente if komponente is not None else self.ausgewaehlte_komponente
        ziel.width = max(1, ziel.width + dw)
        ziel.height = max(1, ziel.height + dh)
        self._nach_aenderung(ziel)

    def loeschen(self, komponente: Any = None) -> None:
        ziel = komponente if komponente is not None else self.ausgewaehlte_komponente
        if ziel is None or ziel is self.formular:
            return

        name = self._attributname(ziel)
        if name is not None:
            delattr(self.formular, name)

        del self._widget_zu_komponente[ziel._qwidget]
        ziel._qwidget.setParent(None)
        ziel._qwidget.deleteLater()

        self.ausgewaehlte_komponente = None
        self._auswaehlen(self.formular)

    def duplizieren(self, komponente: Any = None) -> Any:
        ziel = komponente if komponente is not None else self.ausgewaehlte_komponente
        if ziel is None or ziel is self.formular:
            return None

        urspruenglicher_name = self._attributname(ziel) or type(ziel).__name__.lower()
        neuer_name = self._eindeutigen_namen_finden(f"{urspruenglicher_name}_kopie")

        neue_komponente = type(ziel)(self.formular)
        for name in eigenschaften(type(ziel)):
            setattr(neue_komponente, name, getattr(ziel, name))
        neue_komponente.left = ziel.left + RASTER
        neue_komponente.top = ziel.top + RASTER

        setattr(self.formular, neuer_name, neue_komponente)
        self._ueberwachung_einrichten(neue_komponente)
        self._auswaehlen(neue_komponente)
        self._nach_aenderung(neue_komponente)
        return neue_komponente

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
