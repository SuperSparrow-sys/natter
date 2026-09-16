"""ProjektExplorer: Baumansicht mit Formularen und Units.

Siehe konzept-natter.md, Abschnitt 7.4: „Gruppen Formulare, Units,
Assets; Formular-Units als ein Eintrag“. `Assets` folgt, sobald Bild-/
Sound-Komponenten Dateien in `assets/` erwarten (siehe `pcl.Image`).
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem

from ide.project import Projekt

PFAD_ROLLE = Qt.ItemDataRole.UserRole


class ProjektExplorer(QTreeWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setHeaderHidden(True)

        self.formulare_gruppe = QTreeWidgetItem(["Formulare"])
        self.units_gruppe = QTreeWidgetItem(["Units"])
        self.addTopLevelItem(self.formulare_gruppe)
        self.addTopLevelItem(self.units_gruppe)

    def projekt_anzeigen(self, projekt: Projekt) -> None:
        self.formulare_gruppe.takeChildren()
        self.units_gruppe.takeChildren()

        formular_stems = {pfad.stem for pfad in projekt.formulare()}

        for pfad in projekt.formulare():
            # öffnet den Designer (Abschnitt 7.7), nicht den Rohtext;
            # "Formular/Code umschalten" (Abschnitt 7.9) folgt später
            self._eintrag_hinzufuegen(self.formulare_gruppe, pfad.stem, pfad)

        for pfad in projekt.units():
            if pfad.stem in formular_stems:
                continue  # gehört zu einem Formular, dort schon aufgeführt
            self._eintrag_hinzufuegen(self.units_gruppe, pfad.name, pfad)

        self.expandAll()

    def _eintrag_hinzufuegen(self, gruppe: QTreeWidgetItem, beschriftung: str, pfad: Path) -> None:
        eintrag = QTreeWidgetItem([beschriftung])
        eintrag.setData(0, PFAD_ROLLE, str(pfad))
        gruppe.addChild(eintrag)
