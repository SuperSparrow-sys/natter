"""Befehlspalette: „Hilfe → Befehl suchen …“ (Strg+Umschalt+P).

Jeder Befehl von Natter steht einmal im Aktionsregister
(`ide/actions`), mit Namen, Menü und Tastenkürzel. Die Palette zeigt sie
alle in einer Liste; wer weiß, was er will, aber nicht, in welchem Menü
es steht, tippt ein Stück vom Namen und drückt Eingabe (Punkt 82).
Ausgegraute Befehle erscheinen nicht - sie täten an dieser Stelle
nichts.

Die Filterlogik ist ohne `exec()` testbar, wie bei der Schnellauswahl.
"""

from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout

from ide.actions import Aktion
from ide.shell.tastenkuerzel import deutsche_taste

_AKTION_ROLLE = Qt.ItemDataRole.UserRole


def _zeile(aktion: Aktion) -> str:
    ort = f"{aktion.menue} → {aktion.name}" if aktion.menue else aktion.name
    taste = deutsche_taste(aktion.tastenkuerzel) if aktion.tastenkuerzel else ""
    return f"{ort}    {taste}" if taste else ort


class Befehlspalette(QDialog):
    def __init__(self, aktionen: Iterable[Aktion], parent=None) -> None:  # noqa: ANN001
        super().__init__(parent)
        self.setWindowTitle("Befehl suchen")
        self.resize(520, 420)
        self._aktionen = sorted(
            (a for a in aktionen if a.qaction.isEnabled() and a.qaction.isVisible()),
            key=lambda a: (a.menue, a.name.lower()),
        )
        self.gewaehlte_aktion: Aktion | None = None

        self.suchfeld = QLineEdit()
        self.suchfeld.setPlaceholderText("Befehl suchen …")
        self.suchfeld.textChanged.connect(self._filtern)
        self.suchfeld.returnPressed.connect(self._aktuelle_zeile_uebernehmen)

        self.liste = QListWidget()
        self.liste.itemActivated.connect(self._uebernehmen)

        layout = QVBoxLayout(self)
        layout.addWidget(self.suchfeld)
        layout.addWidget(self.liste)
        self._filtern("")

    def _filtern(self, text: str) -> None:
        """Jedes Wort des Suchtextes muss im Namen oder Menü vorkommen,
        egal in welcher Reihenfolge: „speich unter“ findet „Datei →
        Speichern unter …“."""
        woerter = text.lower().split()
        self.liste.clear()
        for aktion in self._aktionen:
            zeile = _zeile(aktion)
            if all(wort in zeile.lower() for wort in woerter):
                eintrag = QListWidgetItem(zeile)
                eintrag.setData(_AKTION_ROLLE, aktion.id)
                self.liste.addItem(eintrag)
        if self.liste.count():
            self.liste.setCurrentRow(0)

    def _aktuelle_zeile_uebernehmen(self) -> None:
        eintrag = self.liste.currentItem()
        if eintrag is not None:
            self._uebernehmen(eintrag)

    def _uebernehmen(self, eintrag: QListWidgetItem) -> None:
        kennung = eintrag.data(_AKTION_ROLLE)
        self.gewaehlte_aktion = next(a for a in self._aktionen if a.id == kennung)
        self.accept()

    def gefilterte_zeilen(self) -> list[str]:
        return [self.liste.item(i).text() for i in range(self.liste.count())]
