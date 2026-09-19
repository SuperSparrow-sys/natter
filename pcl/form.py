"""Form: Basisklasse für Fenster.

Siehe README.md, Abschnitt 4.3, 5.2. `create_components()` wird
vom generierten `u_*_design.py` überschrieben und erzeugt beim Aufruf die
Kind-Komponenten (z. B. ``self.b_ein = Button(self)``).
"""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QWidget

from pcl.properties import Event, Komponente, Prop
from pcl.theme import qss_erzeugen


class Form(Komponente):
    """Basisklasse aller Formulare.

    Eigene Attribute (``self.ampel = Ampel()``) bleiben erlaubt – die
    Sperre gegen unbekannte Eigenschaften aus `Komponente` gilt nur für
    Komponenten, die auf dem Formular platziert werden (Abschnitt 5.0).
    """

    neue_attribute_erlaubt = True

    caption = Prop(str, "Form1", kategorie="Darstellung", doc="Fenstertitel")
    width = Prop(int, 480, kategorie="Layout", doc="Fensterbreite in Pixeln")
    height = Prop(int, 360, kategorie="Layout", doc="Fensterhöhe in Pixeln")
    theme = Prop(
        str, "system", kategorie="Darstellung", doc="Farbschema: system, light oder dark"
    )
    color = Prop(
        str, "", kategorie="Darstellung", doc="Hintergrundfarbe als #RRGGBB, leer = Theme-Standard"
    )

    on_create = Event(doc="Wird unmittelbar vor der ersten Anzeige ausgelöst")

    def __init__(self) -> None:
        self._qwidget = QWidget()
        self._qwidget.setWindowTitle(self.caption)
        self._qwidget.resize(self.width, self.height)
        self._stylesheet_aktualisieren()
        self.create_components()
        if self.on_create is not None:
            self.on_create(self)

    def _stylesheet_aktualisieren(self) -> None:
        # `color` wird als zweiter, für "QWidget" spezifischerer Regelblock
        # angehängt statt die Eigenschaft in qss_erzeugen() einzumischen -
        # überschreibt bei Bedarf nur background-color, der Rest des
        # Theme-Stylesheets bleibt unangetastet.
        stylesheet = qss_erzeugen(self.theme)
        if self.color:
            stylesheet += f"\nQWidget {{ background-color: {self.color}; }}"
        self._qwidget.setStyleSheet(stylesheet)

    def create_components(self) -> None:
        """Erzeugt die Kind-Komponenten. Wird vom generierten
        `u_*_design.py` überschrieben (Abschnitt 4.3)."""

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        if name == "caption":
            self._qwidget.setWindowTitle(wert)
        elif name in ("width", "height"):
            self._qwidget.resize(self.width, self.height)
        elif name in ("theme", "color"):
            self._stylesheet_aktualisieren()

    def show(self) -> None:
        self._qwidget.show()

    def close(self) -> None:
        """Entspricht `Close` aus der LCL."""
        self._qwidget.close()
