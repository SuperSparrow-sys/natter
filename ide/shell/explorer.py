"""ProjektExplorer: Baumansicht mit Formularen und Units.

Siehe konzept-natter.md, Abschnitt 7.4: „Gruppen Formulare, Units,
Assets; Formular-Units als ein Eintrag“. `Assets` folgt, sobald Bild-/
Sound-Komponenten Dateien in `assets/` erwarten (siehe `pcl.Image`).
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
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
        # QTreeWidgetItem ist standardmäßig per Doppelklick umbenennbar
        # (Qt.ItemIsEditable gehört zu den Standard-Flags) - kollidierte
        # mit unserem eigenen Doppelklick-zum-Öffnen und mit dem
        # dedizierten „⋮ → Umbenennen …“ (Nutzer-Screenshot: ein
        # unstyled, mitten im Baum eingeblendetes Eingabefeld, das gar
        # nicht unsere eigene Umbenennen-Funktion war).
        self.setEditTriggers(QTreeWidget.EditTrigger.NoEditTriggers)
        # Qts eingebaute Baum-Einrückung malt die Auswahlfarbe für den
        # Einrückungsbereich eines ausgewählten Kind-Elements nicht über
        # QSS steuerbar, sondern als deckenden, unpassenden Balken
        # (Nutzer-Screenshot: „die zwei blauen Balken“) - unabhängig von
        # der Einrückungstiefe. Ohne Einrückung tritt das nicht auf; die
        # Gruppenüberschriften sind stattdessen fett, das reicht als
        # Hierarchie-Hinweis für die nur zwei Ebenen hier.
        self.setIndentation(0)

        self.formulare_gruppe = QTreeWidgetItem(["Formulare"])
        self.units_gruppe = QTreeWidgetItem(["Units"])
        self.diagramme_gruppe = QTreeWidgetItem(["Diagramme"])
        fett = QFont()
        fett.setBold(True)
        for gruppe in (self.formulare_gruppe, self.units_gruppe, self.diagramme_gruppe):
            gruppe.setFont(0, fett)
        self.addTopLevelItem(self.formulare_gruppe)
        self.addTopLevelItem(self.units_gruppe)
        self.addTopLevelItem(self.diagramme_gruppe)

    def projekt_anzeigen(self, projekt: Projekt) -> None:
        self.formulare_gruppe.takeChildren()
        self.units_gruppe.takeChildren()
        self.diagramme_gruppe.takeChildren()

        formular_stems = {pfad.stem for pfad in projekt.formulare()}

        for pfad in projekt.formulare():
            # öffnet den Designer (Abschnitt 7.7), nicht den Rohtext;
            # "Formular/Code umschalten" (Abschnitt 7.9) folgt später
            self._eintrag_hinzufuegen(self.formulare_gruppe, pfad.stem, pfad)

        for pfad in projekt.units():
            if pfad.stem in formular_stems:
                continue  # gehört zu einem Formular, dort schon aufgeführt
            self._eintrag_hinzufuegen(self.units_gruppe, pfad.name, pfad, mit_menue=True)

        for pfad in projekt.diagramme():
            # öffnet den Diagramm-Editor in einem eigenen Fenster
            # (Abschnitt 13.1), nicht den Rohtext
            self._eintrag_hinzufuegen(self.diagramme_gruppe, pfad.stem, pfad)

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
        # Als `setItemWidget` eingebettetes Widget bekommt sonst die
        # deckende QWidget-Standardhintergrundfarbe aus dem IDE-Theme -
        # die stimmt bei einer ausgewählten/gehoverten Zeile nicht mehr
        # mit deren (halbtransparenter) Hervorhebungsfarbe überein und
        # wirkt wie ein zu dunkler Fleck (Nutzer-Screenshot). Ohne
        # eigenen Hintergrund scheint die Zeilenfarbe immer durch. Der
        # Dropdown-Pfeil neben dem „⋮“ wird ebenfalls unterdrückt – bei
        # einem reinen Symbolknopf unnötig.
        knopf.setStyleSheet(
            "QToolButton { background: transparent; border: none; }"
            "QToolButton::menu-indicator { image: none; width: 0px; }"
        )

        menue = QMenu(knopf)
        menue.addAction("Umbenennen …", lambda: self.umbenennen_angefordert.emit(pfad))
        menue.addAction("Löschen …", lambda: self.loeschen_angefordert.emit(pfad))
        knopf.setMenu(menue)
        return knopf
