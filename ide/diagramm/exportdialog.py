"""Kleiner Dialog für die PNG-Einstellungen (Abschnitt 13.2:
„PNG-Export mit wählbarer Auflösung“).

Nur für PNG: SVG und PDF sind auflösungsfrei, bei ihnen gäbe es nichts
einzustellen. Deshalb erscheint der Dialog auch nur, wenn wirklich eine
`.png` gewählt wurde – wer ein PDF exportiert, wird nicht mit einer
überflüssigen Rückfrage aufgehalten.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QVBoxLayout,
    QWidget,
)

#: Beschriftung -> Skalierungsfaktor. „2× (Druck)“ statt „192 dpi“,
#: weil die Zielgruppe mit dpi wenig anfangen kann.
AUFLOESUNGEN: dict[str, float] = {
    "1× (Bildschirm)": 1.0,
    "2× (Druck)": 2.0,
    "4× (Plakat)": 4.0,
}


@dataclass(frozen=True)
class PngEinstellungen:
    skalierung: float = 1.0
    transparent: bool = False


class PngDialog(QDialog):
    def __init__(self, eltern: QWidget | None = None) -> None:
        super().__init__(eltern)
        self.setWindowTitle("PNG exportieren")

        self.aufloesung = QComboBox()
        self.aufloesung.addItems(list(AUFLOESUNGEN))
        self.transparent = QCheckBox("Hintergrund durchsichtig lassen")

        formular = QFormLayout()
        formular.addRow("Auflösung", self.aufloesung)
        formular.addRow("", self.transparent)

        knoepfe = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        knoepfe.accepted.connect(self.accept)
        knoepfe.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(formular)
        layout.addWidget(knoepfe)

    def einstellungen(self) -> PngEinstellungen:
        return PngEinstellungen(
            skalierung=AUFLOESUNGEN[self.aufloesung.currentText()],
            transparent=self.transparent.isChecked(),
        )
