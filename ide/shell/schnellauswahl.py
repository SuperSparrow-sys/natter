"""SchnellAuswahl: „Unit öffnen …“ (Strg+P).

Siehe konzept-natter.md, Abschnitt 7.4 („Schnellauswahl aller
Projektdateien mit Suche“) und 7.9 (Strg+P). Reine Filterlogik ist ohne
`exec()` testbar; nur der tatsächliche modale Dialogaufruf
(`HauptFenster._unit_oeffnen_dialog`) blockiert wie jeder echte Dialog.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QDialog, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout


class SchnellAuswahl(QDialog):
    def __init__(self, dateien: list[Path], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Unit öffnen")
        self._alle_dateien = sorted(dateien, key=lambda p: p.name.lower())
        self.ausgewaehlte_datei: Path | None = None

        self.suchfeld = QLineEdit()
        self.suchfeld.setPlaceholderText("Suchen …")
        self.suchfeld.textChanged.connect(self._filtern)
        self.suchfeld.returnPressed.connect(self._erste_zeile_uebernehmen)

        self.liste = QListWidget()
        self.liste.itemActivated.connect(self._uebernehmen)

        layout = QVBoxLayout(self)
        layout.addWidget(self.suchfeld)
        layout.addWidget(self.liste)

        self._filtern("")

    def _filtern(self, text: str) -> None:
        self.liste.clear()
        text_klein = text.lower()
        for pfad in self._alle_dateien:
            if text_klein in pfad.name.lower():
                self.liste.addItem(pfad.name)
        if self.liste.count() > 0:
            self.liste.setCurrentRow(0)

    def _erste_zeile_uebernehmen(self) -> None:
        if self.liste.count() > 0:
            self._uebernehmen(self.liste.item(0))

    def _uebernehmen(self, element: QListWidgetItem) -> None:
        name = element.text()
        for pfad in self._alle_dateien:
            if pfad.name == name:
                self.ausgewaehlte_datei = pfad
                break
        self.accept()

    def gefilterte_namen(self) -> list[str]:
        return [self.liste.item(i).text() for i in range(self.liste.count())]
