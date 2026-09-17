"""ProjektExplorer: Baumansicht mit Formularen und Units.

Siehe konzept-natter.md, Abschnitt 7.4: „Gruppen Formulare, Units,
Assets; Formular-Units als ein Eintrag“. `Assets` folgt, sobald Bild-/
Sound-Komponenten Dateien in `assets/` erwarten (siehe `pcl.Image`).
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHeaderView, QMenu, QToolButton, QTreeWidget, QTreeWidgetItem

from ide.project import Projekt

PFAD_ROLLE = Qt.ItemDataRole.UserRole


class ProjektExplorer(QTreeWidget):
    #: Nutzer-Feedback (September 2026): Units umbenennen/löschen über
    #: einen „⋮“-Knopf statt nur über den Windows-Explorer nebenbei.
    umbenennen_angefordert = Signal(Path)
    loeschen_angefordert = Signal(Path)

    def __init__(self) -> None:
        super().__init__()
        self.setHeaderHidden(True)
        self.setColumnCount(2)
        self.header().setStretchLastSection(False)
        self.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(1, 26)

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
            self._eintrag_hinzufuegen(self.units_gruppe, pfad.name, pfad, mit_menue=True)

        self.expandAll()

    def _eintrag_hinzufuegen(
        self, gruppe: QTreeWidgetItem, beschriftung: str, pfad: Path, mit_menue: bool = False
    ) -> None:
        eintrag = QTreeWidgetItem([beschriftung])
        eintrag.setData(0, PFAD_ROLLE, str(pfad))
        gruppe.addChild(eintrag)
        if mit_menue:
            self.setItemWidget(eintrag, 1, self._knopf_erzeugen(pfad))

    def _knopf_erzeugen(self, pfad: Path) -> QToolButton:
        """Kleiner „⋮“-Knopf für „Umbenennen …“/„Löschen …“ (nur Units –
        ein Formular besteht aus `.pfm` + `.py` und wird bewusst
        (noch) nicht darüber umbenannt/gelöscht, das bräuchte
        zusätzlich Anpassungen an Imports/Ereignisverknüpfungen)."""
        knopf = QToolButton()
        knopf.setText("⋮")
        knopf.setAutoRaise(True)
        knopf.setFixedSize(22, 22)
        knopf.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

        menue = QMenu(knopf)
        menue.addAction("Umbenennen …", lambda: self.umbenennen_angefordert.emit(pfad))
        menue.addAction("Löschen …", lambda: self.loeschen_angefordert.emit(pfad))
        knopf.setMenu(menue)
        return knopf
