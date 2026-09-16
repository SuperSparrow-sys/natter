"""Tests für ide/shell/hauptfenster.py: Grundgerüst. Headless. Siehe
docs/arbeitspakete/M2.md, Schritt 1.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTabWidget

from ide.inspector import Objektinspektor
from ide.shell.hauptfenster import MENUETITEL, PANEL_REITER, HauptFenster


def test_fenstertitel() -> None:
    fenster = HauptFenster()
    assert fenster.windowTitle() == "Natter"


def test_fenster_hat_ein_symbol() -> None:
    fenster = HauptFenster()
    assert not fenster.windowIcon().isNull()


def test_werkzeugleiste_enthaelt_die_aktionen_mit_symbol() -> None:
    fenster = HauptFenster()
    erwartet = [aktion.name for aktion in fenster.aktionen if aktion.symbol]

    vorhanden = [aktion.text() for aktion in fenster.werkzeugleiste.actions()]

    assert vorhanden == erwartet
    assert "Starten ohne Debugger" in vorhanden


def test_aktionen_mit_symbol_tragen_ein_icon() -> None:
    fenster = HauptFenster()
    for aktion in fenster.aktionen:
        if aktion.symbol:
            assert not aktion.qaction.icon().isNull()


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


def test_oeffnen_aktionen_stehen_in_den_richtigen_menues() -> None:
    fenster = HauptFenster()
    datei_eintraege = [a.text() for a in fenster.menue("Datei").actions()]
    projekt_eintraege = [a.text() for a in fenster.menue("Projekt").actions()]
    assert "Öffnen …" in datei_eintraege
    assert "Unit öffnen …" in datei_eintraege
    assert "Projekt öffnen …" in projekt_eintraege
    assert fenster.aktionen["datei.oeffnen"].qaction.shortcut().toString() == "Ctrl+O"
    assert fenster.aktionen["datei.unit_oeffnen"].qaction.shortcut().toString() == "Ctrl+P"


def test_objektinspektor_haengt_im_dock() -> None:
    fenster = HauptFenster()
    assert isinstance(fenster.objektinspektor, Objektinspektor)
    assert fenster.inspektor_dock.widget() is fenster.objektinspektor
