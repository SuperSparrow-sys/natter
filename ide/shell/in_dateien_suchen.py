"""„Suchen → In allen Dateien suchen …“ (Strg+Umschalt+F, Punkt 102).

Durchsucht die Units des offenen Projekts - die Dateien, die im
Projekt-Explorer stehen - und zeigt jede Zeile mit Treffer als
„Datei, Zeile: Text“. Ein Doppelklick oder Eingabe öffnet die Datei an
dieser Zeile. Offene Editoren zählen mit ihrem aktuellen Text, auch
wenn er noch nicht gespeichert ist.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ide.shell.suchen_dialog import treffer_in_text

_ORT = Qt.ItemDataRole.UserRole


class InDateienSuchen(QDialog):
    def __init__(
        self,
        dateien: list[Path],
        text_von: Callable[[Path], str],
        oeffnen: Callable[[Path, int], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("In allen Dateien suchen")
        self.resize(640, 420)
        self._dateien = dateien
        self._text_von = text_von
        self._oeffnen = oeffnen

        self.suchfeld = QLineEdit()
        self.suchfeld.setPlaceholderText("Suchen …")
        self.suchfeld.returnPressed.connect(self.suchen)
        self.gross_klein = QCheckBox("Groß- und Kleinschreibung beachten")
        self.ganze_woerter = QCheckBox("Nur ganze Wörter")
        knopf = QPushButton("Suchen")
        knopf.clicked.connect(self.suchen)
        self.ergebnis = QLabel("")
        self.liste = QListWidget()
        self.liste.itemActivated.connect(self._springen)

        zeile = QHBoxLayout()
        zeile.addWidget(self.suchfeld, 1)
        zeile.addWidget(knopf)
        layout = QVBoxLayout(self)
        layout.addLayout(zeile)
        layout.addWidget(self.gross_klein)
        layout.addWidget(self.ganze_woerter)
        layout.addWidget(self.liste, 1)
        layout.addWidget(self.ergebnis)

    def suchen(self) -> int:
        self.liste.clear()
        anzahl = 0
        for pfad in self._dateien:
            for nummer, zeile in treffer_in_text(
                self._text_von(pfad),
                self.suchfeld.text(),
                gross_klein=self.gross_klein.isChecked(),
                ganze_woerter=self.ganze_woerter.isChecked(),
            ):
                eintrag = QListWidgetItem(f"{pfad.name}, Zeile {nummer}: {zeile.strip()}")
                eintrag.setData(_ORT, (str(pfad), nummer))
                self.liste.addItem(eintrag)
                anzahl += 1
        dateien = len({self.liste.item(i).data(_ORT)[0] for i in range(self.liste.count())})
        if not anzahl:
            self.ergebnis.setText(f"„{self.suchfeld.text()}“ kommt in keiner Datei vor.")
        else:
            self.ergebnis.setText(
                f"{anzahl} Zeilen in {dateien} Dateien."
                if dateien != 1
                else f"{anzahl} Zeilen in 1 Datei."
            )
        return anzahl

    def zeilen(self) -> list[str]:
        return [self.liste.item(i).text() for i in range(self.liste.count())]

    def _springen(self, eintrag: QListWidgetItem) -> None:
        pfad, zeile = eintrag.data(_ORT)
        self._oeffnen(Path(pfad), zeile)
