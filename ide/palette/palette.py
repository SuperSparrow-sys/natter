"""Komponentenpalette mit Reitern Standard/Zusätzlich.

Siehe konzept-natter.md, Abschnitt 7.3. Nur die bisher in `pcl`
umgesetzten Komponenten (Stand M1/M3); `Allgemein`, `Dialoge`,
`Datensteuerung`, `Datenzugriff`, `System` folgen, sobald es dort etwas
zu platzieren gibt (Abschnitt 5.2). Ein eigener Reiter `Diagramm` lohnt
sich mit einer einzigen Komponente noch nicht – `Chart` steht deshalb
unter „Zusätzlich“.

Optik wie in Lazarus: ein einzeiliger, horizontal scrollbarer Streifen
aus reinen Symbol-Kacheln je Reiter (kein Fließtext unter dem Symbol),
der Komponentenname erscheint als Tooltip beim Überfahren mit der Maus.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QTabWidget

from ide.assets import symbol
from pcl.components.additional import (
    FloatSpinEdit,
    Image,
    ProgressBar,
    Shape,
    SpinEdit,
    StringGrid,
    TrackBar,
)
from pcl.components.chart import Chart
from pcl.components.standard import (
    Button,
    CheckBox,
    ComboBox,
    Edit,
    GroupBox,
    Label,
    ListBox,
    Memo,
    Panel,
    RadioButton,
    RadioGroup,
    ScrollBar,
)

TYP_ROLLE = Qt.ItemDataRole.UserRole
# Nutzer-Feedback (September 2026): insgesamt kompakter, näher an
# Lazarus' eigener, schmaler Symbolleiste (~24px Symbole).
_SYMBOL_GROESSE = QSize(22, 22)
_KACHEL_GROESSE = QSize(32, 32)

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
    # Die drei Behälter stehen wie in Lazarus im Reiter „Standard“ und
    # dort am Ende - sie kommen im Unterricht später dran als Knopf und
    # Textfeld, und die Reihenfolge der bisherigen Kacheln soll sich
    # nicht verschieben.
    GroupBox,
    Panel,
    RadioGroup,
)

ZUSAETZLICH_KOMPONENTEN = (
    StringGrid,
    Image,
    Shape,
    # „Zusätzlich“ statt „Standard“: ein Diagramm ist kein Grundbaustein
    # wie Knopf oder Textfeld (M10, Punkt 1).
    Chart,
    # `TrackBar` und `ProgressBar` gehören in Lazarus in den Reiter
    # „Common Controls“. Ein dritter Reiter wäre hier zwar schnell
    # angelegt, bliebe aber tot: `ide/shell/hauptfenster.py` verbindet
    # die Klick-Signale von genau `standard_liste` und
    # `zusaetzlich_liste` - eine Kachel in einem dritten Reiter ließe
    # sich nicht auf dem Formular ablegen.
    SpinEdit,
    FloatSpinEdit,
    TrackBar,
    ProgressBar,
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

    def symbole_erneuern(self, theme: str = "system") -> None:
        """Lädt die Palettensymbole im angegebenen Theme neu – nötig nach
        „Ansicht → Design", weil ein `QIcon` sich seine Farben merkt."""
        for seite in range(self.count()):
            liste = self.widget(seite)
            if not isinstance(liste, QListWidget):
                continue
            for zeile in range(liste.count()):
                eintrag = liste.item(zeile)
                typ = eintrag.data(TYP_ROLLE)
                if typ is not None:
                    eintrag.setIcon(
                        symbol(f"komponente_{typ.__name__.lower()}", theme)
                    )

    def ausgewaehlter_typ(self) -> type | None:
        """Der in der aktiven Palettenseite ausgewählte Komponententyp,
        oder `None`, wenn nichts ausgewählt ist."""
        liste = self.currentWidget()
        if not isinstance(liste, QListWidget):
            return None
        eintrag = liste.currentItem()
        return eintrag.data(TYP_ROLLE) if eintrag is not None else None
