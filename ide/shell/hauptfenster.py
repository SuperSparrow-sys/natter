"""HauptFenster: Grundgerüst des IDE-Hauptfensters.

Siehe konzept-natter.md, Abschnitt 7.1. Reines Grundgerüst (M2, Schritt
1): Menüleiste mit den Menütiteln aus Abschnitt 7.2 (noch ohne Einträge –
die kommen mit dem Aktionsregister, Schritt 2), Docks für Explorer/
Objektinspektor/Panels, zentrale Editor-Tabs, Statusleiste.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget, QMainWindow, QTabWidget, QWidget

MENUETITEL = (
    "Datei",
    "Bearbeiten",
    "Suchen",
    "Ansicht",
    "Quelltext",
    "Projekt",
    "Start",
    "Pakete",
    "Werkzeuge",
    "Fenster",
    "Hilfe",
)

PANEL_REITER = ("Meldungen", "Ausgabe", "Variablen", "Aufrufstapel")


class HauptFenster(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Natter")

        self._menues: dict[str, object] = {}
        for titel in MENUETITEL:
            self._menues[titel] = self.menuBar().addMenu(titel)

        self.editor_tabs = QTabWidget()
        self.editor_tabs.setTabsClosable(True)
        self.editor_tabs.setMovable(True)
        self.setCentralWidget(self.editor_tabs)

        self.explorer_dock = self._dock_erzeugen(
            "Projekt-Explorer", Qt.DockWidgetArea.LeftDockWidgetArea
        )
        self.inspektor_dock = self._dock_erzeugen(
            "Objektinspektor", Qt.DockWidgetArea.RightDockWidgetArea
        )

        self.panels = QTabWidget()
        for reiter in PANEL_REITER:
            self.panels.addTab(QWidget(), reiter)
        self.panels_dock = self._dock_erzeugen(
            "Panels", Qt.DockWidgetArea.BottomDockWidgetArea, inhalt=self.panels
        )

        self.statusBar().showMessage("bereit")

    def _dock_erzeugen(
        self, titel: str, bereich: Qt.DockWidgetArea, inhalt: QWidget | None = None
    ) -> QDockWidget:
        dock = QDockWidget(titel, self)
        dock.setWidget(inhalt if inhalt is not None else QWidget())
        self.addDockWidget(bereich, dock)
        return dock

    def menue(self, titel: str):
        """Liefert das Menü mit diesem Titel (Abschnitt 7.2)."""
        return self._menues[titel]
