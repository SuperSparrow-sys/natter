"""Zeileneditor für Sammlungs-Eigenschaften (`items`, `lines`).

Entspricht dem Zeichenketten-Editor hinter dem „…“-Knopf im Lazarus-
Objektinspektor: eine Zeile je Eintrag. Siehe konzept-natter.md,
Abschnitt 7.6 und `pcl.properties.SAMMLUNGS_EIGENSCHAFTEN`.
"""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QPlainTextEdit, QVBoxLayout


class SammlungDialog(QDialog):
    def __init__(self, eigenschaft: str, zeilen: list[str], eltern=None) -> None:
        super().__init__(eltern)
        self.setWindowTitle(f"{eigenschaft} bearbeiten")
        self.resize(360, 280)

        self._eingabe = QPlainTextEdit(self)
        self._eingabe.setPlainText("\n".join(zeilen))

        knoepfe = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        knoepfe.accepted.connect(self.accept)
        knoepfe.rejected.connect(self.reject)

        anordnung = QVBoxLayout(self)
        anordnung.addWidget(QLabel("Ein Eintrag je Zeile:", self))
        anordnung.addWidget(self._eingabe)
        anordnung.addWidget(knoepfe)

    def zeilen(self) -> list[str]:
        """Die eingegebenen Einträge. Eine leere Eingabe ergibt eine leere
        Liste statt einer Liste mit einer leeren Zeichenkette."""
        text = self._eingabe.toPlainText()
        return text.split("\n") if text else []
