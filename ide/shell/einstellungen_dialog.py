"""„Werkzeuge → Einstellungen …“ (Punkte 98 und 101).

Bewusst wenig: nur, was sonst nirgends einzustellen ist. Design,
Schriftart, Zeilenumbruch und Leerzeichen stehen schon im Menü
„Ansicht“ und werden dort gemerkt.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QSpinBox,
    QWidget,
)


class EinstellungenDialog(QDialog):
    def __init__(
        self,
        schriftgroesse: int,
        ausgabe_leeren: bool,
        parent: QWidget | None = None,
        oberflaeche: int = 10,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Einstellungen")
        self.groesse = QSpinBox()
        self.groesse.setRange(7, 32)
        self.groesse.setSuffix(" pt")
        self.groesse.setValue(schriftgroesse)
        # Vergrößert Menüs, Docks, Panels und Dialoge zusammen, etwa
        # für die Vorführung am Beamer (Punkt 302), ohne dass dafür die
        # Skalierung von Windows umgestellt werden muss.
        self.oberflaeche_groesse = QSpinBox()
        self.oberflaeche_groesse.setRange(8, 24)
        self.oberflaeche_groesse.setSuffix(" pt")
        self.oberflaeche_groesse.setValue(oberflaeche)
        self.leeren = QCheckBox("Ausgabe vor jedem Start leeren")
        self.leeren.setChecked(ausgabe_leeren)

        knoepfe = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        knoepfe.accepted.connect(self.accept)
        knoepfe.rejected.connect(self.reject)

        layout = QFormLayout(self)
        layout.addRow("Schriftgröße der Oberfläche:", self.oberflaeche_groesse)
        layout.addRow("Schriftgröße im Editor:", self.groesse)
        layout.addRow("", self.leeren)
        layout.addRow(knoepfe)

    def schriftgroesse(self) -> int:
        return self.groesse.value()

    def ausgabe_leeren(self) -> bool:
        return self.leeren.isChecked()

    def oberflaeche(self) -> int:
        return self.oberflaeche_groesse.value()
