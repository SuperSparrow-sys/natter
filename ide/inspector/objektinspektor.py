"""Objektinspektor: Komponentenbaum + Reiter Eigenschaften/Ereignisse.

Siehe konzept-natter.md, Abschnitt 7.6.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QTabWidget, QVBoxLayout, QWidget

from ide.inspector.eigenschaften_tabelle import EigenschaftenTabelle
from ide.inspector.ereignisse_tabelle import EreignisseTabelle
from ide.inspector.komponentenbaum import KOMPONENTE_ROLLE, Komponentenbaum
from pcl.form import Form


class Objektinspektor(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._formular: Form | None = None
        self._canvas: Any = None

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

    @property
    def formular(self) -> Form | None:
        return self._formular

    def formular_anzeigen(self, formular: Form, canvas: Any = None) -> None:
        """`canvas` (der zugehörige `DesignerCanvas`, Abschnitt 7.7) wird
        nur für die Zeile „name“ im Eigenschaften-Reiter gebraucht –
        Umbenennen läuft über `canvas.komponente_umbenennen()` (Undo,
        `.pfm`-Aktualisierung). Ohne `canvas` bleibt die Zeile weg."""
        self._formular = formular
        self._canvas = canvas
        self.baum.formular_anzeigen(formular)
        if self.baum.topLevelItemCount() > 0:
            self.baum.setCurrentItem(self.baum.topLevelItem(0))

    def _bei_auswahl(self, aktuell, vorherig) -> None:
        if aktuell is None:
            return
        komponente = aktuell.data(0, KOMPONENTE_ROLLE)
        self._eigenschaften_anzeigen(komponente)

    def _eigenschaften_anzeigen(self, komponente: Any) -> None:
        name = self._canvas.name_von(komponente) if self._canvas is not None else None
        name_setzen = (
            (lambda neuer_name: self._canvas.komponente_umbenennen(komponente, neuer_name))
            if self._canvas is not None
            else None
        )
        bei_aenderung = self._canvas.eigenschaft_uebernehmen if self._canvas is not None else None
        self.eigenschaften_tabelle.komponente_anzeigen(
            komponente, name=name, name_setzen=name_setzen, bei_aenderung=bei_aenderung
        )
        # Dieselbe Meldung wie bei den Eigenschaften: eine hier gewählte
        # Verknüpfung muss in die `.pfm` und den erzeugten Code, sonst
        # tut der Knopf im gestarteten Programm nichts (M12).
        self.ereignisse_tabelle.anzeigen(
            komponente, self._formular, bei_aenderung=bei_aenderung
        )
