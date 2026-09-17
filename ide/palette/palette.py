"""Komponentenpalette mit Reitern Standard/Zusätzlich.

Siehe konzept-natter.md, Abschnitt 7.3. Nur die bisher in `pcl`
umgesetzten Komponenten (Stand M1/M3); `Allgemein`, `Dialoge`,
`Datensteuerung`, `Datenzugriff`, `System`, `Diagramm` folgen, sobald es
dort etwas zu platzieren gibt (Abschnitt 5.2).

Optik wie in Lazarus: ein einzeiliger, horizontal scrollbarer Streifen
aus reinen Symbol-Kacheln je Reiter (kein Fließtext unter dem Symbol),
der Komponentenname erscheint als Tooltip beim Überfahren mit der Maus.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QTabWidget

from ide.assets import symbol
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
_SYMBOL_GROESSE = QSize(28, 28)
_KACHEL_GROESSE = QSize(40, 40)

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
        # Kompakter, einzeiliger Streifen wie in Lazarus statt einer
        # beliebig hoch wachsenden Liste.
        self.setMaximumHeight(_KACHEL_GROESSE.height() + 34)

    def _liste_erzeugen(self, komponenten: tuple[type, ...]) -> QListWidget:
        liste = QListWidget()
        liste.setViewMode(QListWidget.ViewMode.IconMode)
        liste.setFlow(QListWidget.Flow.LeftToRight)
        liste.setWrapping(False)
        liste.setResizeMode(QListWidget.ResizeMode.Fixed)
        liste.setMovement(QListWidget.Movement.Static)
        liste.setIconSize(_SYMBOL_GROESSE)
        liste.setGridSize(_KACHEL_GROESSE)
        liste.setUniformItemSizes(True)
        liste.setSpacing(1)
        liste.setFixedHeight(_KACHEL_GROESSE.height() + 6)
        liste.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        liste.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        for typ in komponenten:
            eintrag = QListWidgetItem(symbol(f"komponente_{typ.__name__.lower()}"), "")
            eintrag.setData(TYP_ROLLE, typ)
            eintrag.setToolTip(typ.__name__)
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
