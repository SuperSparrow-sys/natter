"""Objektinspektor: Komponentenbaum + Reiter Eigenschaften/Ereignisse.

Siehe konzept-natter.md, Abschnitt 7.6.
"""

from __future__ import annotations

from PySide6.QtWidgets import QTabWidget, QVBoxLayout, QWidget

from ide.inspector.eigenschaften_tabelle import EigenschaftenTabelle
from ide.inspector.ereignisse_tabelle import EreignisseTabelle
from ide.inspector.komponentenbaum import KOMPONENTE_ROLLE, Komponentenbaum
from pcl.form import Form


class Objektinspektor(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._formular: Form | None = None

        self.baum = Komponentenbaum()
        self.baum.currentItemChanged.connect(self._bei_auswahl)

        self.eigenschaften_tabelle = EigenschaftenTabelle()
        self.ereignisse_tabelle = EreignisseTabelle()

        self.reiter = QTabWidget()
        self.reiter.addTab(self.eigenschaften_tabelle, "Eigenschaften")
        self.reiter.addTab(self.ereignisse_tabelle, "Ereignisse")

        layout = QVBoxLayout(self)
        layout.addWidget(self.baum, 1)
        layout.addWidget(self.reiter, 2)

    def formular_anzeigen(self, formular: Form) -> None:
        self._formular = formular
        self.baum.formular_anzeigen(formular)
        if self.baum.topLevelItemCount() > 0:
            self.baum.setCurrentItem(self.baum.topLevelItem(0))

    def _bei_auswahl(self, aktuell, vorherig) -> None:
        if aktuell is None:
            return
        komponente = aktuell.data(0, KOMPONENTE_ROLLE)
        self.eigenschaften_tabelle.komponente_anzeigen(komponente)
        self.ereignisse_tabelle.anzeigen(komponente, self._formular)
