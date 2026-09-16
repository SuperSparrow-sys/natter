"""DesignerCanvas: zeigt ein Formular mit echten `pcl`-Komponenten,
Klick wählt eine Komponente aus statt die echte Interaktion auszulösen.

Siehe konzept-natter.md, Abschnitt 7.7: „Der Designer rendert echte
pcl-Komponenten.“ Platzieren, Verschieben und Größenänderung folgen in
Schritt 4.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import QWidget

from ide.inspector.komponentenbaum import kind_komponenten
from pcl.form import Form

# Wird einmal an das Stylesheet des Formulars angehängt (kaskadiert zu
# allen Kindern, Abschnitt 6) statt einzelne Widget-Stylesheets zu
# überschreiben – so bleibt das Theme des Formulars unangetastet.
_AUSWAHL_REGEL = '\n*[design_ausgewaehlt="true"] { border: 2px solid #0067c0; }'
_MARKIERUNGS_EIGENSCHAFT = "design_ausgewaehlt"


class DesignerCanvas(QObject):
    def __init__(self, formular: Form) -> None:
        super().__init__()
        self.formular = formular
        self.ausgewaehlte_komponente: Any = None
        self._auswahl_beobachter: list[Callable[[Any], None]] = []
        self._widget_zu_komponente: dict[QWidget, Any] = {}

        formular._qwidget.setStyleSheet(formular._qwidget.styleSheet() + _AUSWAHL_REGEL)
        self._ueberwachung_einrichten(formular)

    def _ueberwachung_einrichten(self, objekt: Any) -> None:
        widget = objekt._qwidget
        self._widget_zu_komponente[widget] = objekt
        widget.installEventFilter(self)
        for _, komponente in kind_komponenten(objekt):
            self._ueberwachung_einrichten(komponente)

    def eventFilter(self, beobachtetes_objekt: QObject, ereignis: QEvent) -> bool:
        if ereignis.type() == QEvent.Type.MouseButtonPress:
            komponente = self._widget_zu_komponente.get(beobachtetes_objekt)
            if komponente is not None:
                self._auswaehlen(komponente)
                return True  # Klick abfangen: keine echte Interaktion im Designer
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

    def _auswaehlen(self, komponente: Any) -> None:
        if self.ausgewaehlte_komponente is not None:
            self._markierung_setzen(self.ausgewaehlte_komponente._qwidget, False)

        self.ausgewaehlte_komponente = komponente
        self._markierung_setzen(komponente._qwidget, True)

        for beobachter in self._auswahl_beobachter:
            beobachter(komponente)

    def _markierung_setzen(self, widget: QWidget, ausgewaehlt: bool) -> None:
        widget.setProperty(_MARKIERUNGS_EIGENSCHAFT, ausgewaehlt)
        widget.style().unpolish(widget)
        widget.style().polish(widget)
