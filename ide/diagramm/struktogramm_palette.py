"""Blockpalette des Struktogramm-Editors (Abschnitt 13.5).

Bewusst dieselbe Bedienung wie die Formen-Palette des
Klassendiagramms: Block anklicken macht ihn scharf, der nächste Klick
auf eine Einfügestelle setzt ihn dorthin. Wer beides benutzt, muss
nichts umlernen.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLineEdit, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from ide.diagramm.struktogramm import BLOCK_BESCHRIFTUNGEN

KIND_ROLLE = Qt.ItemDataRole.UserRole

#: Reihenfolge wie im Konzept aufgezählt (Abschnitt 13.5), gruppiert
#: nach dem, was Schülerinnen und Schüler im Unterricht zusammen lernen.
GRUPPEN: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Folge", ("statement", "call", "jump")),
    ("Auswahl", ("branch", "multi_branch")),
    ("Wiederholung", ("count_loop", "head_loop", "foot_loop", "forever_loop")),
    ("Sonderformen", ("parallel", "try")),
)

BESCHREIBUNGEN = {
    "statement": "Ein einzelner Verarbeitungsschritt.",
    "branch": "Zweiseitige Auswahl mit Ja- und Nein-Zweig.",
    "multi_branch": "Mehrseitige Auswahl mit beliebig vielen Fällen.",
    "count_loop": "Schleife mit bekannter Anzahl von Durchläufen.",
    "head_loop": "Bedingung wird vor jedem Durchlauf geprüft.",
    "foot_loop": "Bedingung wird nach jedem Durchlauf geprüft.",
    "call": "Aufruf eines anderen Unterprogramms.",
    "jump": "Vorzeitiges Verlassen (Abbruch, Rücksprung).",
    "forever_loop": "Läuft ohne Bedingung, bis ein Aussprung sie verlässt.",
    "parallel": "Mehrere Stränge, die nebenläufig gedacht sind.",
    "try": "Versuch, Behandlung des Fehlers und Abschluss.",
}


class BlockPalette(QWidget):
    block_gewaehlt = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.suche = QLineEdit()
        self.suche.setPlaceholderText("Suche …")
        self.suche.textChanged.connect(self._filtern)

        self.baum = QTreeWidget()
        self.baum.setHeaderHidden(True)
        self.baum.itemClicked.connect(self._geklickt)

        for gruppe, arten in GRUPPEN:
            knoten = QTreeWidgetItem(self.baum, [gruppe])
            knoten.setFlags(Qt.ItemFlag.ItemIsEnabled)
            for art in arten:
                eintrag = QTreeWidgetItem(knoten, [BLOCK_BESCHRIFTUNGEN[art]])
                eintrag.setData(0, KIND_ROLLE, art)
                eintrag.setToolTip(0, BESCHREIBUNGEN.get(art, ""))
            knoten.setExpanded(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self.suche)
        layout.addWidget(self.baum)

    def _geklickt(self, eintrag: QTreeWidgetItem, spalte: int) -> None:
        art = eintrag.data(0, KIND_ROLLE)
        if art:
            self.block_gewaehlt.emit(str(art))

    def _filtern(self, text: str) -> None:
        gesucht = text.strip().lower()
        for i in range(self.baum.topLevelItemCount()):
            gruppe = self.baum.topLevelItem(i)
            sichtbar_in_gruppe = False
            for j in range(gruppe.childCount()):
                kind = gruppe.child(j)
                passt = gesucht in kind.text(0).lower()
                kind.setHidden(not passt)
                sichtbar_in_gruppe = sichtbar_in_gruppe or passt
            gruppe.setHidden(not sichtbar_in_gruppe)
