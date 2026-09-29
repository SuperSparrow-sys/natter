"""Tests für ide/shell/hauptfenster.py: Grundgerüst. Headless. Siehe
Arbeitspaket M2, Schritt 1.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QStackedWidget, QTabWidget

from ide.inspector import Objektinspektor
from ide.shell.hauptfenster import MENUETITEL, PANEL_REITER


def test_fenstertitel(hauptfenster) -> None:
    assert hauptfenster.windowTitle() == "Natter"


def test_fenster_hat_ein_symbol(hauptfenster) -> None:
    assert not hauptfenster.windowIcon().isNull()


def test_werkzeugleiste_enthaelt_die_aktionen_mit_symbol(hauptfenster) -> None:
    erwartet = [aktion.name for aktion in hauptfenster.aktionen if aktion.symbol]

    vorhanden = [a.text() for a in hauptfenster.werkzeugleiste.actions() if not a.isSeparator()]

    assert vorhanden == erwartet
    assert "Starten ohne Debugger" in vorhanden
    # Rückgängig und Wiederholen standen einmal nur im Menü
    # „Bearbeiten": ihnen fehlte das `symbol`, und nur Aktionen mit
    # Symbol landen in der Werkzeugleiste.
    assert {"Rückgängig", "Wiederholen"} <= set(vorhanden)


def test_start_aktion_ist_durch_eine_trennlinie_von_den_dateiaktionen_abgesetzt(
    hauptfenster
) -> None:
    eintraege = hauptfenster.werkzeugleiste.actions()
    start_index = next(i for i, a in enumerate(eintraege) if a.text() == "Starten")
    assert eintraege[start_index - 1].isSeparator()


def test_werkzeugleiste_hat_eine_sichtbare_symbolgroesse(hauptfenster) -> None:
    # 18px seit dem kompakteren Chrome (Gewünscht: 
    # „die obere Leiste kann kleiner sein“) - immer noch deutlich über
    # der Grenze, ab der Symbole unkenntlich würden.
    groesse = hauptfenster.werkzeugleiste.iconSize()
    assert groesse.width() >= 16
    assert groesse.height() >= 16


def test_aktionen_mit_symbol_tragen_ein_icon(hauptfenster) -> None:
    for aktion in hauptfenster.aktionen:
        if aktion.symbol:
            assert not aktion.qaction.icon().isNull()


def test_alle_menuetitel_aus_abschnitt_7_2_vorhanden(hauptfenster) -> None:
    vorhandene_titel = [
        aktion.text().replace("&", "")
        for aktion in hauptfenster.menuBar().actions()
    ]
    assert vorhandene_titel == list(MENUETITEL)


def test_menue_liefert_das_richtige_menue_ueber_seinen_titel(hauptfenster) -> None:
    assert hauptfenster.menue("Datei").title() == "&Datei"
    assert hauptfenster.menue("Projekt").title() == "&Projekt"


def test_zentrale_editor_tabs_sind_leer_und_schliessbar(hauptfenster) -> None:
    """Seit M11 steckt in der Mitte ein Stapel aus Startbild und
    Editor-Tabs: solange nichts offen ist, steht dort, was man tun
    kann, statt einer leeren grauen Fläche."""
    assert isinstance(hauptfenster.centralWidget(), QStackedWidget)
    assert isinstance(hauptfenster.editor_tabs, QTabWidget)
    assert hauptfenster.editor_tabs.count() == 0
    assert hauptfenster.editor_tabs.tabsClosable() is True
    assert hauptfenster.mitte.currentWidget() is hauptfenster.startbild


def test_docks_an_den_richtigen_bereichen(hauptfenster) -> None:
    bereich = hauptfenster.dockWidgetArea
    assert bereich(hauptfenster.explorer_dock) == Qt.DockWidgetArea.LeftDockWidgetArea
    assert bereich(hauptfenster.inspektor_dock) == Qt.DockWidgetArea.RightDockWidgetArea
    assert bereich(hauptfenster.panels_dock) == Qt.DockWidgetArea.BottomDockWidgetArea


def test_panels_haben_alle_reiter(hauptfenster) -> None:
    reiter = [hauptfenster.panels.tabText(i) for i in range(hauptfenster.panels.count())]
    assert reiter == list(PANEL_REITER)


def test_statusleiste_zeigt_bereit(hauptfenster) -> None:
    assert hauptfenster.statusBar().currentMessage() == "bereit"


def test_oeffnen_aktionen_stehen_in_den_richtigen_menues(hauptfenster) -> None:
    datei_eintraege = [a.text() for a in hauptfenster.menue("Datei").actions()]
    projekt_eintraege = [a.text() for a in hauptfenster.menue("Projekt").actions()]
    assert "Öffnen …" in datei_eintraege
    assert "Unit öffnen …" in datei_eintraege
    assert "Projekt öffnen …" in projekt_eintraege
    # Strg+O öffnet das Projekt, wie im Handbuch (Punkt 213).
    assert hauptfenster.aktionen["projekt.oeffnen"].qaction.shortcut().toString() == "Ctrl+O"
    assert hauptfenster.aktionen["datei.oeffnen"].qaction.shortcut().toString() == ""
    assert hauptfenster.aktionen["datei.unit_oeffnen"].qaction.shortcut().toString() == "Ctrl+P"


def test_objektinspektor_haengt_im_dock(hauptfenster) -> None:
    assert isinstance(hauptfenster.objektinspektor, Objektinspektor)
    assert hauptfenster.inspektor_dock.widget() is hauptfenster.objektinspektor


def test_editor_behaelt_seine_monospace_schrift_unter_dem_ide_weiten_stylesheet(
    tmp_path, hauptfenster,
) -> None:
    """Real gefunden (gemeldet): ein bloßes
 `QuelltextEditor` ohne Eltern-Stylesheet zeigte die richtige
 Schrift, aber sobald der Editor als Tab in der echten `HauptFenster`
 hängt, gewann die allgemeine `QWidget { font-family:... }`-Regel
 aus dem IDE-weiten Stylesheet gegen `setFont` - nicht nur optisch,
 `editor.font.family`/`.pointSize` waren selbst falsch
 (Segoe UI Variable, 10pt statt Consolas, 11pt)."""
    pfad = tmp_path / "u_main.py"
    pfad.write_text("x = 1\n", encoding="utf-8")

    editor = hauptfenster.datei_oeffnen(pfad)

    assert editor.font().family() == "Consolas"
    assert editor.font().pointSize() == 11
    assert editor.font().fixedPitch() is True
