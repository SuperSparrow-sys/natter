"""Tests für ide/shell/hauptfenster.py: Grundgerüst. Headless. Siehe
docs/arbeitspakete/M2.md, Schritt 1.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTabWidget

from ide.shell.hauptfenster import MENUETITEL, PANEL_REITER, HauptFenster


def test_fenstertitel() -> None:
    fenster = HauptFenster()
    assert fenster.windowTitle() == "Natter"


def test_alle_menuetitel_aus_abschnitt_7_2_vorhanden() -> None:
    fenster = HauptFenster()
    vorhandene_titel = [aktion.text() for aktion in fenster.menuBar().actions()]
    assert vorhandene_titel == list(MENUETITEL)


def test_menue_liefert_das_richtige_menue_ueber_seinen_titel() -> None:
    fenster = HauptFenster()
    assert fenster.menue("Datei").title() == "Datei"
    assert fenster.menue("Projekt").title() == "Projekt"


def test_zentrale_editor_tabs_sind_leer_und_schliessbar() -> None:
    fenster = HauptFenster()
    assert isinstance(fenster.centralWidget(), QTabWidget)
    assert fenster.editor_tabs.count() == 0
    assert fenster.editor_tabs.tabsClosable() is True


def test_docks_an_den_richtigen_bereichen() -> None:
    fenster = HauptFenster()
    assert fenster.dockWidgetArea(fenster.explorer_dock) == Qt.DockWidgetArea.LeftDockWidgetArea
    assert fenster.dockWidgetArea(fenster.inspektor_dock) == Qt.DockWidgetArea.RightDockWidgetArea
    assert fenster.dockWidgetArea(fenster.panels_dock) == Qt.DockWidgetArea.BottomDockWidgetArea


def test_panels_haben_alle_reiter() -> None:
    fenster = HauptFenster()
    reiter = [fenster.panels.tabText(i) for i in range(fenster.panels.count())]
    assert reiter == list(PANEL_REITER)


def test_statusleiste_zeigt_bereit() -> None:
    fenster = HauptFenster()
    assert fenster.statusBar().currentMessage() == "bereit"
