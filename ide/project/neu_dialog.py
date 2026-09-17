"""„Neues Projekt …“-Dialog (Abschnitt 7.2, 7.5): Vorlage, Name und
Zielordner abfragen, dann `ide.project.neu.projekt_erzeugen()` aufrufen.

Bisher gab es zwar die reine Logik (`projekt_erzeugen()`, seit M2), aber
keine Möglichkeit, ein neues Projekt tatsächlich aus der laufenden IDE
heraus anzulegen (Nutzer-Feedback, September 2026: „ist da alles?“ beim
Blick auf das Projekt-Menü) – dieser Dialog schließt die Lücke.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ide.project.neu import VORLAGEN

_VORLAGEN_ANZEIGE = {
    "gui": "GUI-Anwendung",
    "console": "Konsolenanwendung",
}


class NeuesProjektDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Neues Projekt")
        self.setMinimumWidth(420)

        self.vorlage_auswahl = QComboBox()
        for vorlage in VORLAGEN:
            self.vorlage_auswahl.addItem(_VORLAGEN_ANZEIGE.get(vorlage, vorlage), vorlage)

        self.name_eingabe = QLineEdit()
        self.name_eingabe.setPlaceholderText("z. B. Ampel")

        self.ordner_eingabe = QLineEdit()
        self.ordner_eingabe.setPlaceholderText("Übergeordneter Ordner")
        self.ordner_knopf = QPushButton("Durchsuchen …")
        self.ordner_knopf.clicked.connect(self._ordner_waehlen)
        ordner_zeile = QHBoxLayout()
        ordner_zeile.addWidget(self.ordner_eingabe)
        ordner_zeile.addWidget(self.ordner_knopf)
        ordner_widget = QWidget()
        ordner_widget.setLayout(ordner_zeile)

        formular = QFormLayout()
        formular.addRow("Vorlage:", self.vorlage_auswahl)
        formular.addRow("Name:", self.name_eingabe)
        formular.addRow("Ordner:", ordner_widget)

        self.knopfleiste = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.knopfleiste.accepted.connect(self.accept)
        self.knopfleiste.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(formular)
        layout.addWidget(self.knopfleiste)

    def _ordner_waehlen(self) -> None:
        ordner = QFileDialog.getExistingDirectory(self, "Übergeordneter Ordner")
        if ordner:
            self.ordner_eingabe.setText(ordner)

    def werte(self) -> tuple[str, Path, str] | None:
        """`(vorlage, projektordner, name)`, oder `None`, wenn Name oder
        Ordner fehlen. `projektordner` ist `ordner/name` – der eigentliche,
        neu anzulegende Projektordner (siehe `projekt_erzeugen()`)."""
        name = self.name_eingabe.text().strip()
        ordner = self.ordner_eingabe.text().strip()
        if not name or not ordner:
            return None
        vorlage = self.vorlage_auswahl.currentData()
        return vorlage, Path(ordner) / name, name
