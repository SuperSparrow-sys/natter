"""Form: Basisklasse für Fenster.

Siehe konzept-natter.md, Abschnitt 4.3, 5.2. `create_components()` wird
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

    on_create = Event(doc="Wird unmittelbar vor der ersten Anzeige ausgelöst")

    def __init__(self) -> None:
        self._qwidget = QWidget()
        self._qwidget.setWindowTitle(self.caption)
        self._qwidget.resize(self.width, self.height)
        self._qwidget.setStyleSheet(qss_erzeugen(self.theme))
        self.create_components()
        if self.on_create is not None:
            self.on_create(self)

    def create_components(self) -> None:
        """Erzeugt die Kind-Komponenten. Wird vom generierten
        `u_*_design.py` überschrieben (Abschnitt 4.3)."""

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        if name == "caption":
            self._qwidget.setWindowTitle(wert)
        elif name in ("width", "height"):
            self._qwidget.resize(self.width, self.height)
        elif name == "theme":
            self._qwidget.setStyleSheet(qss_erzeugen(wert))

    def show(self) -> None:
        self._qwidget.show()

    def close(self) -> None:
        """Entspricht `Close` aus der LCL."""
        self._qwidget.close()
