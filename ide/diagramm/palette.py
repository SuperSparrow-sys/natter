"""FormenPalette: Formenliste links im Diagramm-Fenster
(Abschnitt 13.2).

Aufbau wie im Konzept skizziert: Suchfeld oben, darunter Gruppen je
Diagrammtyp, Tooltip mit Name und Kurzbeschreibung. Ein einfacher Klick
macht die Form „scharf“ (Abschnitt 13.3: „anklicken und auf die Fläche
klicken“) – dasselbe Muster wie die Komponentenpalette im
Formular-Designer.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QLineEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ide.diagramm.formen import FORMEN_JE_TYP, formen_fuer
from ide.diagramm.neu import TYP_BESCHRIFTUNGEN

KIND_ROLLE = Qt.ItemDataRole.UserRole


class FormenPalette(QWidget):
    #: `shape["kind"]` der angeklickten Form
    form_gewaehlt = Signal(str)

    def __init__(self, diagrammtyp: str) -> None:
        super().__init__()
        self.diagrammtyp = diagrammtyp

        self.suche = QLineEdit()
        self.suche.setPlaceholderText("Suche …")
        self.suche.setClearButtonEnabled(True)
        self.suche.textChanged.connect(self._filtern)

        self.baum = QTreeWidget()
        self.baum.setHeaderHidden(True)
        self.baum.setEditTriggers(QTreeWidget.EditTrigger.NoEditTriggers)
        self.baum.itemClicked.connect(self._bei_klick)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self.suche)
        layout.addWidget(self.baum, 1)

        self._aufbauen()

    def _aufbauen(self) -> None:
        """Die Gruppe des eigenen Diagrammtyps steht oben und ist
        aufgeklappt; die übrigen Typen erscheinen erst, wenn sie eigene
        Formen haben (siehe M9.md, „Danach“)."""
        eigene = formen_fuer(self.diagrammtyp)
        if eigene:
            self._gruppe_anlegen(TYP_BESCHRIFTUNGEN[self.diagrammtyp], eigene, aufgeklappt=True)

        for typ, formen in FORMEN_JE_TYP.items():
            if typ != self.diagrammtyp:
                self._gruppe_anlegen(TYP_BESCHRIFTUNGEN[typ], formen, aufgeklappt=False)

    def _gruppe_anlegen(self, titel: str, formen, aufgeklappt: bool) -> None:
        gruppe = QTreeWidgetItem([titel])
        self.baum.addTopLevelItem(gruppe)
        for art in formen:
            eintrag = QTreeWidgetItem([art.beschriftung])
            eintrag.setData(0, KIND_ROLLE, art.kind)
            eintrag.setToolTip(0, f"{art.beschriftung} – {art.beschreibung}")
            gruppe.addChild(eintrag)
        gruppe.setExpanded(aufgeklappt)

    def _bei_klick(self, eintrag: QTreeWidgetItem, spalte: int) -> None:
        kind = eintrag.data(0, KIND_ROLLE)
        if kind:
            self.form_gewaehlt.emit(kind)

    def _filtern(self, text: str) -> None:
        """Blendet Formen aus, deren Beschriftung den Suchtext nicht
        enthält; leere Gruppen verschwinden mit."""
        suchtext = text.strip().lower()
        for i in range(self.baum.topLevelItemCount()):
            gruppe = self.baum.topLevelItem(i)
            sichtbare = 0
            for j in range(gruppe.childCount()):
                kind_eintrag = gruppe.child(j)
                passt = suchtext in kind_eintrag.text(0).lower()
                kind_eintrag.setHidden(not passt)
                sichtbare += int(passt)
            gruppe.setHidden(sichtbare == 0)
            if suchtext:
                gruppe.setExpanded(True)
