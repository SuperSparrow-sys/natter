"""Komponentenpalette mit Reitern Standard/Zusätzlich.

Siehe konzept-natter.md, Abschnitt 7.3. Nur die bisher in `pcl`
umgesetzten Komponenten (Stand M1/M3); `Allgemein`, `Dialoge`,
`Datensteuerung`, `Datenzugriff`, `System`, `Diagramm` folgen, sobald es
dort etwas zu platzieren gibt (Abschnitt 5.2).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QTabWidget

from pcl.components.additional import Image, Shape, StringGrid
from pcl.components.standard import (
    Button,
    CheckBox,
    ComboBox,
    Edit,
    Label,
    ListBox,
    Memo,
    RadioButton,
    ScrollBar,
)

TYP_ROLLE = Qt.ItemDataRole.UserRole

STANDARD_KOMPONENTEN = (
    Button,
    Label,
    Edit,
    Memo,
    CheckBox,
    RadioButton,
    ListBox,
    ComboBox,
    ScrollBar,
)

ZUSAETZLICH_KOMPONENTEN = (
    StringGrid,
    Image,
    Shape,
)


class Komponentenpalette(QTabWidget):
    def __init__(self) -> None:
        super().__init__()
        self.standard_liste = self._liste_erzeugen(STANDARD_KOMPONENTEN)
        self.zusaetzlich_liste = self._liste_erzeugen(ZUSAETZLICH_KOMPONENTEN)
        self.addTab(self.standard_liste, "Standard")
        self.addTab(self.zusaetzlich_liste, "Zusätzlich")

    def _liste_erzeugen(self, komponenten: tuple[type, ...]) -> QListWidget:
        liste = QListWidget()
        for typ in komponenten:
            eintrag = QListWidgetItem(typ.__name__)
            eintrag.setData(TYP_ROLLE, typ)
            liste.addItem(eintrag)
        return liste

    def ausgewaehlter_typ(self) -> type | None:
        """Der in der aktiven Palettenseite ausgewählte Komponententyp,
        oder `None`, wenn nichts ausgewählt ist."""
        liste = self.currentWidget()
        if not isinstance(liste, QListWidget):
            return None
        eintrag = liste.currentItem()
        return eintrag.data(TYP_ROLLE) if eintrag is not None else None
