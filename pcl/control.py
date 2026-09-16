"""Control: Basisklasse aller platzierbaren pcl-Komponenten mit Qt-Anbindung.

Siehe konzept-natter.md, Abschnitt 5. Verbindet den Prop-Zugriff aus
`pcl.properties` mit einem echten QWidget: eine Zuweisung wie
``self.b_ok.caption = "OK"`` ändert sofort die Anzeige (live). Konkrete
Komponenten (Button, Label, Shape, ...) folgen in M1, Schritt 3.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QWidget

from pcl.properties import Komponente, Prop


class Control(Komponente):
    """Gemeinsame Basis aller auf einem Formular platzierten Komponenten."""

    left = Prop(int, 0, kategorie="Layout", doc="Position von links in Pixeln")
    top = Prop(int, 0, kategorie="Layout", doc="Position von oben in Pixeln")
    width = Prop(int, 75, kategorie="Layout", doc="Breite in Pixeln")
    height = Prop(int, 25, kategorie="Layout", doc="Höhe in Pixeln")
    enabled = Prop(
        bool, True, kategorie="Verhalten", doc="Legt fest, ob die Komponente bedienbar ist"
    )

    def __init__(self, parent: Komponente) -> None:
        eltern_widget: QWidget = parent._qwidget
        self._qwidget: QWidget = self._qwidget_erzeugen(eltern_widget)
        self._geometrie_anwenden()
        self._qwidget.setEnabled(self.enabled)
        self._qwidget.show()

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        """Erzeugt das zugehörige QWidget. Von konkreten Komponenten
        überschrieben (z. B. `Button` erzeugt ein `QPushButton`)."""
        raise NotImplementedError("Konkrete Komponenten erzeugen ihr eigenes QWidget")

    def _geometrie_anwenden(self) -> None:
        self._qwidget.setGeometry(self.left, self.top, self.width, self.height)

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        if name in ("left", "top", "width", "height"):
            self._geometrie_anwenden()
        elif name == "enabled":
            self._qwidget.setEnabled(wert)
