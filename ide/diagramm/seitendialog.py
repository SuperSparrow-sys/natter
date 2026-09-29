"""„Datei → Seite einrichten …“ im Diagramm-Editor (Punkt 67).

Das Seitenformat stand fest auf dem, was beim Anlegen gewählt wurde:
`page` schrieb nur `ide/diagramm/neu.py`. Der Layout-Hinweis „liegt
außerhalb des Seitenbereichs“ riet trotzdem, unter „Seite einrichten“
ein größeres Format zu wählen.

Angeboten werden die Formate, die `seite.py` in Pixel umrechnen kann;
Export, Druck und der Seitenrand auf der Zeichenfläche lesen alle
dasselbe `page`.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QRadioButton,
    QWidget,
)

from ide.diagramm.seite import FORMATE_MM


class SeitenDialog(QDialog):
    def __init__(self, seite: dict[str, Any], eltern: QWidget | None = None) -> None:
        super().__init__(eltern)
        self.setWindowTitle("Seite einrichten")

        self.format = QComboBox()
        for name, (breite, hoehe) in FORMATE_MM.items():
            self.format.addItem(f"{name} ({breite:g} × {hoehe:g} mm)", name)
        gefunden = self.format.findData(str(seite.get("size", "A4")))
        self.format.setCurrentIndex(max(0, gefunden))

        self.hoch = QRadioButton("&Hochformat")
        self.quer = QRadioButton("&Querformat")
        gruppe = QButtonGroup(self)
        gruppe.addButton(self.hoch)
        gruppe.addButton(self.quer)
        quer = seite.get("orientation") == "landscape"
        (self.quer if quer else self.hoch).setChecked(True)
        ausrichtung = QHBoxLayout()
        ausrichtung.addWidget(self.hoch)
        ausrichtung.addWidget(self.quer)
        ausrichtung.addStretch(1)

        knoepfe = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        knoepfe.button(QDialogButtonBox.StandardButton.Cancel).setText("Abbrechen")
        knoepfe.accepted.connect(self.accept)
        knoepfe.rejected.connect(self.reject)

        layout = QFormLayout(self)
        layout.addRow("&Format:", self.format)
        layout.addRow("Ausrichtung:", ausrichtung)
        layout.addRow(knoepfe)

    def seite(self) -> dict[str, str]:
        """Das gewählte `page` für die `.pdiag`."""
        return {
            "size": str(self.format.currentData()),
            "orientation": "landscape" if self.quer.isChecked() else "portrait",
        }
