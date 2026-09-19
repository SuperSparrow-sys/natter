"""HauptFenster: Grundgerüst des IDE-Hauptfensters.

Siehe konzept-natter.md, Abschnitt 7.1, 7.4, 7.5. Menüleiste mit den
Menütiteln aus Abschnitt 7.2 (Einträge kommen über das Aktionsregister),
Docks für Explorer/Objektinspektor/Panels, zentrale Editor-Tabs,
Statusleiste. `projekt_oeffnen`/`datei_oeffnen` sind die Grundlage für
„Projekt öffnen …“/„Öffnen …“ (M2, Schritt 5).
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from PySide6.QtCore import QSettings, QSize, Qt
from PySide6.QtGui import QActionGroup, QCloseEvent, QColor, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDockWidget,
    QFileDialog,
    QInputDialog,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ide.actions import Aktion, Aktionsregister
from ide.assets import symbol
from ide.codegen.design import design_code_erzeugen
from ide.database import DatenbankPanel
from ide.debugger import (
    DebugSitzung,
    TabellenFehler,
    fehlermeldung_aus_dap_erzeugen,
    tabelle_aus_antwort,
    tabellen_ausdruck,
)
from ide.designer import DesignerCanvas, formular_fuer_designer_laden
from ide.designer.pfm_schreiben import pfm_aus_formular
from ide.diagramm import (
    MVP_TYPEN,
    TYP_BESCHRIFTUNGEN,
    Diagramm,
    DiagrammFenster,
    diagramm_erzeugen,
)
from ide.env import PaketFehler, installierte_pakete, paket_installieren, paketliste_exportieren
from ide.export import exe_exportieren
from ide.import_lfm import (
    LfmImportErgebnis,
    LfmParserError,
    lfm_zu_pfm,
    parse_lfm,
    pas_text_lesen,
    prozedur_ruempfe_lesen,
    unit_quelltext_erzeugen,
)
from ide.inspector import Objektinspektor
from ide.integritaet.start_pruefung import installation_pruefen
from ide.lint import pruefen
from ide.palette import Komponentenpalette
from ide.palette.palette import TYP_ROLLE
from ide.project import Projekt, projekt_erzeugen
from ide.project.neu_dialog import NeuesProjektDialog
from ide.run import projekt_pruefen, projekt_starten
from ide.shell.explorer import PFAD_ROLLE, ProjektExplorer
from ide.shell.quelltexteditor import SCHRIFTART_OPTIONEN, QuelltextEditor
from ide.shell.schnellauswahl import SchnellAuswahl
from ide.shell.suchen_dialog import SuchenErsetzenDialog
from ide.shell.theme import ide_qss_erzeugen
from ide.testrunner import Testergebnis, ergebnisse_als_html, tests_ausfuehren
from ide.viewers import BildVorschau, CsvAnsicht, HtmlVorschau, TabellenAnsicht
from pcl import open_url
from pcl.form import Form
from pcl.theme import theme_aufloesen

_BILD_ENDUNGEN = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp", ".svg"}
_HTML_ENDUNGEN = {".html", ".htm"}

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

PANEL_REITER = ("Meldungen", "Ausgabe", "Variablen", "Aufrufstapel", "Tests")

_TEST_ID_ROLLE = Qt.ItemDataRole.UserRole
_STATUS_FARBE = {
    "bestanden": "#1e8e3e",
    "fehlgeschlagen": "#c0392b",
    "fehler": "#c0392b",
}

# Name der dynamischen QWidget-Eigenschaft, die den Dateipfad eines
# Editor-Tabs trägt (nicht zu verwechseln mit PFAD_ROLLE, das ist die
# Qt.ItemDataRole für Explorer-Einträge).
_PFAD_EIGENSCHAFT = "pfad"

# Qt.ItemDataRole für Einträge in meldungen_liste: trägt (canvas,
# komponenten_name) für Design-Prüfer-Befunde, damit ein Klick die
# betroffene Komponente im Designer markiert (Abschnitt 14). Ruff-Funde
# (reiner Text über addItems()) tragen hier nichts.
_MELDUNG_ROLLE = Qt.ItemDataRole.UserRole


def _kommentar_umschalten_zeilen(zeilen: list[str]) -> list[str]:
    """Reine Logik für „Quelltext → Kommentar umschalten“ (Abschnitt 7.2,
    wie VS Codes Strg+#): entfernt `# ` (oder `#` ohne Leerzeichen) von
    jeder nicht-leeren Zeile, wenn ALLE nicht-leeren Zeilen bereits so
    beginnen – sonst wird bei jeder nicht-leeren Zeile `# ` ergänzt.
    Leere Zeilen bleiben unverändert und zählen nicht mit."""
    inhaltszeilen = [z for z in zeilen if z.strip()]
    alle_kommentiert = bool(inhaltszeilen) and all(
        z.lstrip().startswith("#") for z in inhaltszeilen
    )
    ergebnis = []
    for zeile in zeilen:
        if not zeile.strip():
            ergebnis.append(zeile)
            continue
        rest = zeile.lstrip()
        einzug = zeile[: len(zeile) - len(rest)]
        if alle_kommentiert:
            if rest.startswith("# "):
                rest = rest[2:]
            elif rest.startswith("#"):
                rest = rest[1:]
            ergebnis.append(einzug + rest)
        else:
            ergebnis.append(einzug + "# " + rest)
    return ergebnis


# Vorlage „Test-Unit“ im Neu-Dialog (Abschnitt 8.6): unittest, reines
# Python wie bei jeder anderen Unit.
_TEST_UNIT_VORLAGE = '''\
"""Tests. Ausführen über „Projekt → Alle Tests ausführen“ oder das
Panel „Tests“."""

import unittest


class MeinTest(unittest.TestCase):
    def test_beispiel(self) -> None:
        self.assertEqual(1 + 1, 2)


if __name__ == "__main__":
    unittest.main()
'''


class HauptFenster(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Natter")
        self.setWindowIcon(symbol("app"))
        # Explizit IniFormat statt der Windows-Registry (Standard beim
        # organisation/application-Konstruktor): passt zur portablen,
        # installationsfreien Natter-Philosophie (Abschnitt 17) und lässt
        # sich in Tests über `QSettings.setPath()` sauber umleiten - der
        # organisation/application-Konstruktor ignoriert
        # `setDefaultFormat()` unter Windows.
        self._design_einstellungen = QSettings(
            QSettings.Format.IniFormat, QSettings.Scope.UserScope, "Natter", "Natter-IDE"
        )
        self._design_thema = self._design_einstellungen.value("design/thema", "system")
        self._code_schriftart = self._design_einstellungen.value(
            "editor/schriftart", "Consolas"
        )
        self.setStyleSheet(
            ide_qss_erzeugen(self._design_thema, code_schriftart=self._code_schriftart)
        )

        self._menues: dict[str, object] = {}
        for titel in MENUETITEL:
            self._menues[titel] = self.menuBar().addMenu(titel)

        self.werkzeugleiste = self.addToolBar("Haupt-Werkzeugleiste")
        self.werkzeugleiste.setObjectName("Haupt-Werkzeugleiste")
        self.werkzeugleiste.setMovable(False)
        # Nutzer-Feedback (September 2026): die obere Leiste sollte
        # insgesamt kompakter sein, wie in Lazarus/VS Code.
        self.werkzeugleiste.setIconSize(QSize(18, 18))

        self.editor_tabs = QTabWidget()
        self.editor_tabs.setTabsClosable(True)
        self.editor_tabs.setMovable(True)
        self.setCentralWidget(self.editor_tabs)

        self.explorer = ProjektExplorer()
        self.explorer.itemDoubleClicked.connect(self._bei_explorer_doppelklick)
        self.explorer.umbenennen_angefordert.connect(self._unit_umbenennen)
        self.explorer.loeschen_angefordert.connect(self._unit_loeschen)
        self.explorer_dock = self._dock_erzeugen(
            "Projekt-Explorer", Qt.DockWidgetArea.LeftDockWidgetArea, inhalt=self.explorer
        )
        self.objektinspektor = Objektinspektor()
        self.inspektor_dock = self._dock_erzeugen(
            "Objektinspektor", Qt.DockWidgetArea.RightDockWidgetArea, inhalt=self.objektinspektor
        )

        self.palette = Komponentenpalette()
        self.palette.standard_liste.itemDoubleClicked.connect(self._bei_palette_doppelklick)
        self.palette.zusaetzlich_liste.itemDoubleClicked.connect(self._bei_palette_doppelklick)
        self.palette.standard_liste.itemClicked.connect(self._bei_palette_klick)
        self.palette.zusaetzlich_liste.itemClicked.connect(self._bei_palette_klick)
        self.palette_dock = self._dock_erzeugen(
            "Komponentenpalette", Qt.DockWidgetArea.TopDockWidgetArea, inhalt=self.palette
        )

        self.datenbank_panel = DatenbankPanel()
        self.datenbank_dock = self._dock_erzeugen(
            "Datenbank", Qt.DockWidgetArea.BottomDockWidgetArea, inhalt=self.datenbank_panel
        )

        self.projekt: Projekt | None = None
        self.laufender_prozess = None
        self._offene_canvases: list[DesignerCanvas] = []
        self._pfad_zu_formular: dict[str, Form] = {}
        # Diagramme sind eigene Fenster (Abschnitt 13.1), keine Tabs -
        # deshalb eine eigene Verwaltung statt `editor_tabs`.
        self._offene_diagramme: dict[str, DiagrammFenster] = {}
        self._widget_zu_canvas: dict[QWidget, DesignerCanvas] = {}
        self._aktueller_canvas: DesignerCanvas | None = None
        self.editor_tabs.currentChanged.connect(self._bei_tab_wechsel)
        self.editor_tabs.tabCloseRequested.connect(self._tab_schliessen)

        self._design_pruefer_abgeschaltete_regeln: set[str] = set()

        self.panels = QTabWidget()
        self.meldungen_liste = QListWidget()
        self.meldungen_liste.itemClicked.connect(self._bei_meldung_geklickt)
        self.variablen_baum = QTreeWidget()
        self.variablen_baum.setHeaderLabels(["Eigenschaft", "Wert"])
        # „Als Tabelle anzeigen“ (Abschnitt 11.6): Rechtsklick oder
        # Doppelklick auf eine Variable im Panel „Variablen“.
        self.variablen_baum.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.variablen_baum.customContextMenuRequested.connect(self._variablen_menue_zeigen)
        self.variablen_baum.itemDoubleClicked.connect(
            lambda eintrag, _spalte: self.variable_als_tabelle_zeigen(eintrag.text(0))
        )
        self.aufrufstapel_liste = QListWidget()
        self.aufrufstapel_liste.itemClicked.connect(self._bei_aufrufstapel_klick)
        self.tests_baum = QTreeWidget()
        self.tests_baum.setHeaderLabels(["Test", "Status", "Dauer (s)"])
        self.tests_baum.itemDoubleClicked.connect(self._bei_test_doppelklick)
        panel_widgets = {
            "Meldungen": self.meldungen_liste,
            "Variablen": self.variablen_baum,
            "Aufrufstapel": self.aufrufstapel_liste,
            "Tests": self.tests_baum,
        }
        for reiter in PANEL_REITER:
            self.panels.addTab(panel_widgets.get(reiter, QWidget()), reiter)
        self.panels_dock = self._dock_erzeugen(
            "Panels", Qt.DockWidgetArea.BottomDockWidgetArea, inhalt=self.panels
        )

        # Menü „Ansicht“ (Abschnitt 7.2): jedes Dock lässt sich hier
        # wieder einblenden, nachdem es (z. B. über sein eigenes
        # Schließen-Symbol) geschlossen wurde. `toggleViewAction()` ist
        # eine fertige, ankreuzbare Qt-Aktion, die automatisch mit der
        # tatsächlichen Sichtbarkeit des Docks synchron bleibt - dafür
        # bewusst keine eigene `Aktion`-Hülle aus dem Aktionsregister.
        for dock in (
            self.explorer_dock,
            self.inspektor_dock,
            self.palette_dock,
            self.datenbank_dock,
            self.panels_dock,
        ):
            self._menues["Ansicht"].addAction(dock.toggleViewAction())

        # „Ansicht → Einrückungslinien“ (M11, Abschnitt 2.1). Bei Python
        # **ist** die Einrückung die Syntax; wer sie nicht sieht, sucht
        # seinen Fehler an der falschen Stelle. Abschaltbar bleibt sie
        # trotzdem, wie jede Anzeigehilfe in Natter.
        self.einzugslinien_aktion = self._menues["Ansicht"].addAction(
            "Einrückungslinien"
        )
        self.einzugslinien_aktion.setCheckable(True)
        self.einzugslinien_aktion.setChecked(
            self._design_einstellungen.value("editor/einzugslinien", True, type=bool)
        )
        self.einzugslinien_aktion.toggled.connect(self._einzugslinien_umschalten)

        # „Ansicht → Design“ (Nutzer-Feedback, September 2026: „Hast du
        # den Darkmode schon implementiert?“) – Hell/Dunkel/System,
        # gemerkt über QSettings. Bewusst keine eigene `Aktion`-Hülle
        # (wie bei den Dock-Umschaltern oben): eine sich gegenseitig
        # ausschließende Dreiergruppe passt nicht ins einfache
        # Menü-Callback-Schema des Aktionsregisters.
        design_menue = self._menues["Ansicht"].addMenu("Design")
        design_gruppe = QActionGroup(self)
        design_gruppe.setExclusive(True)
        for wert, beschriftung in (
            ("system", "System (automatisch)"),
            ("light", "Hell"),
            ("dark", "Dunkel"),
        ):
            aktion = design_menue.addAction(beschriftung)
            aktion.setCheckable(True)
            aktion.setChecked(wert == self._design_thema)
            aktion.triggered.connect(lambda checked, wert=wert: self._design_wechseln(wert))
            design_gruppe.addAction(aktion)

        # „Ansicht → Schriftart“ (Nutzer-Feedback September 2026: „soll
        # bei Ansicht eine Auswahl der Schriftarten zum Auswählen“).
        # Gleiches Muster wie „Design“ direkt darüber.
        schriftart_menue = self._menues["Ansicht"].addMenu("Schriftart")
        schriftart_gruppe = QActionGroup(self)
        schriftart_gruppe.setExclusive(True)
        for schrift in SCHRIFTART_OPTIONEN:
            aktion = schriftart_menue.addAction(schrift)
            aktion.setCheckable(True)
            aktion.setChecked(schrift == self._code_schriftart)
            aktion.triggered.connect(
                lambda checked, schrift=schrift: self._code_schriftart_wechseln(schrift)
            )
            schriftart_gruppe.addAction(aktion)

        # Nutzer-Feedback (September 2026): der Quelltexteditor wirkte zu
        # klein, weil Palette/Datenbank/Panels standardmäßig zu viel
        # Höhe beanspruchten. Qt verteilt neue Docks sonst ungefähr
        # gleichmäßig - hier bewusst zugunsten des Editors (Zentral-
        # Widget) eingeschränkt. Bleibt per Maus frei verschiebbar.
        self.resizeDocks([self.palette_dock], [88], Qt.Orientation.Vertical)
        self.resizeDocks(
            [self.datenbank_dock, self.panels_dock], [200, 200], Qt.Orientation.Vertical
        )

        # „Fenster → Layout zurücksetzen“ (Abschnitt 7.2): merkt sich die
        # ursprüngliche Dock-/Werkzeugleisten-Anordnung, sobald alle
        # Docks platziert sind - VOR dem Wiederherstellen der zuletzt
        # gespeicherten Anordnung unten, damit „Zurücksetzen“ wirklich
        # zum echten Ausgangszustand zurückkehrt statt nur zur zuletzt
        # gespeicherten.
        self._urspruengliches_layout = self.saveState()

        # Nutzer-Feedback (September 2026): ein geschlossenes Dock (z. B.
        # „Datenbank“) soll beim nächsten Start auch geschlossen bleiben
        # - Größe/Sichtbarkeit aller Docks wird deshalb gemerkt.
        gespeichertes_layout = self._design_einstellungen.value("fenster/layout")
        if gespeichertes_layout is not None:
            self.restoreState(gespeichertes_layout)

        self._letzte_testergebnisse: list[Testergebnis] = []
        self.debug_sitzung: DebugSitzung | None = None
        self._aktueller_thread_id: int | None = None
        self._letzter_aufrufstapel: list[dict] = []
        #: Name der Variablen, für die gerade „Als Tabelle anzeigen“
        #: läuft (Abschnitt 11.6) - `None`, wenn keine Anfrage offen ist.
        self._tabellen_variable: str | None = None
        #: Grund des letzten Halts ("breakpoint"/"step"/"exception"),
        #: entscheidet, welches Panel danach nach vorne kommt.
        self._letzter_haltegrund: str = ""
        #: Zuletzt geöffnete Tabellenansicht; hält das Fenster am Leben
        #: (ein `QDialog` ohne Verweis wird sonst sofort eingesammelt).
        self.letzte_tabellen_ansicht: TabellenAnsicht | None = None

        self.statusBar().showMessage("bereit")

        self.aktionen = Aktionsregister()
        self.aktionen.registrieren(
            Aktion(
                "datei.neue_unit",
                "Neue Unit",
                menue="Datei",
                tastenkuerzel="Ctrl+N",
                symbol="neu",
                callback=self._neue_unit_aktion,
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "datei.oeffnen",
                "Öffnen …",
                menue="Datei",
                tastenkuerzel="Ctrl+O",
                symbol="oeffnen",
                callback=self._datei_oeffnen_dialog,
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "datei.speichern",
                "Speichern",
                menue="Datei",
                tastenkuerzel="Ctrl+S",
                symbol="speichern",
                callback=self._aktuelle_datei_speichern,
            )
        )
        # Rückgängig/Wiederholen tragen als einzige Bearbeiten-Aktionen ein
        # Symbol und erscheinen damit auch in der Werkzeugleiste (Abschnitt
        # 7.3, Nutzer-Feedback September 2026: „Ich sehe die Buttons nicht
        # zum rückgängig machen“ - sie gab es bis dahin nur im Menü).
        for aktion_id, name, tastenkuerzel, symbol_name, callback in (
            (
                "bearbeiten.rueckgaengig",
                "Rückgängig",
                "Ctrl+Z",
                "rueckgaengig",
                self._bearbeiten_rueckgaengig,
            ),
            (
                "bearbeiten.wiederholen",
                "Wiederholen",
                "Ctrl+Y",
                "wiederholen",
                self._bearbeiten_wiederholen,
            ),
            (
                "bearbeiten.ausschneiden",
                "Ausschneiden",
                "Ctrl+X",
                "",
                self._bearbeiten_ausschneiden,
            ),
            ("bearbeiten.kopieren", "Kopieren", "Ctrl+C", "", self._bearbeiten_kopieren),
            ("bearbeiten.einfuegen", "Einfügen", "Ctrl+V", "", self._bearbeiten_einfuegen),
            (
                "bearbeiten.alles_auswaehlen",
                "Alles auswählen",
                "Ctrl+A",
                "",
                self._bearbeiten_alles_auswaehlen,
            ),
        ):
            self.aktionen.registrieren(
                Aktion(
                    aktion_id,
                    name,
                    menue="Bearbeiten",
                    tastenkuerzel=tastenkuerzel,
                    symbol=symbol_name,
                    trennlinie_davor=aktion_id == "bearbeiten.rueckgaengig",
                    callback=callback,
                )
            )
        self.aktionen.registrieren(
            Aktion(
                "suchen.suchen",
                "Suchen …",
                menue="Suchen",
                tastenkuerzel="Ctrl+F",
                callback=self._suchen_aktion,
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "suchen.gehe_zu_zeile",
                "Gehe zu Zeile …",
                menue="Suchen",
                tastenkuerzel="Ctrl+G",
                callback=self._gehe_zu_zeile_aktion,
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "quelltext.kommentar_umschalten",
                "Kommentar umschalten",
                menue="Quelltext",
                tastenkuerzel="Ctrl+#",
                callback=self._kommentar_umschalten_aktion,
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "fenster.naechster_tab",
                "Nächster Tab",
                menue="Fenster",
                tastenkuerzel="Ctrl+Tab",
                callback=self._naechster_tab_aktion,
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "fenster.vorheriger_tab",
                "Vorheriger Tab",
                menue="Fenster",
                tastenkuerzel="Ctrl+Shift+Tab",
                callback=self._vorheriger_tab_aktion,
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "fenster.layout_zuruecksetzen",
                "Layout zurücksetzen",
                menue="Fenster",
                callback=self._layout_zuruecksetzen_aktion,
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "hilfe.komponenten_referenz",
                "Komponenten-Referenz",
                menue="Hilfe",
                callback=self._komponenten_referenz_aktion,
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "hilfe.ueber",
                "Über Natter",
                menue="Hilfe",
                callback=self._ueber_aktion,
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "projekt.neu",
                "Neues Projekt …",
                menue="Projekt",
                callback=self._neues_projekt_dialog,
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "projekt.oeffnen",
                "Projekt öffnen …",
                menue="Projekt",
                symbol="projekt_oeffnen",
                trennlinie_davor=True,
                callback=self._projekt_oeffnen_dialog,
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "projekt.alle_tests_ausfuehren",
                "Alle Tests ausführen",
                menue="Projekt",
                callback=self._alle_tests_ausfuehren_aktion,
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "projekt.testergebnisse_exportieren",
                "Testergebnisse als HTML exportieren …",
                menue="Projekt",
                callback=self._testergebnisse_exportieren_aktion,
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "projekt.als_exe_exportieren",
                "Als Exe exportieren …",
                menue="Projekt",
                callback=self._als_exe_exportieren_aktion,
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "datei.neue_test_unit",
                "Neue Test-Unit",
                menue="Datei",
                callback=self._neue_test_unit_aktion,
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "datei.neues_diagramm",
                "Neues Diagramm …",
                menue="Datei",
                callback=self._neues_diagramm_aktion,
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "werkzeuge.csv_in_datenbank_importieren",
                "CSV in Datenbank importieren …",
                menue="Werkzeuge",
                callback=self.datenbank_panel._csv_importieren_dialog,
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "werkzeuge.design_pruefen",
                "Design prüfen",
                menue="Werkzeuge",
                callback=self._design_pruefen_aktion,
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "werkzeuge.umgebung_pruefen",
                "Umgebung prüfen",
                menue="Werkzeuge",
                callback=self._umgebung_pruefen_aktion,
            )
        )
        self._design_pruefung_automatisch_aktion = self.aktionen.registrieren(
            Aktion(
                "werkzeuge.design_pruefung_automatisch",
                "Design-Prüfung beim Speichern automatisch",
                menue="Werkzeuge",
                callback=lambda: None,
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "werkzeuge.lazarus_formular_importieren",
                "Lazarus-Formular importieren …",
                menue="Werkzeuge",
                callback=self._lazarus_formular_importieren_aktion,
            )
        )
        self._design_pruefung_automatisch_aktion.qaction.setCheckable(True)
        self._design_pruefung_automatisch_aktion.qaction.setChecked(True)
        self.aktionen.registrieren(
            Aktion(
                "pakete.anzeigen",
                "Paketverwaltung anzeigen",
                menue="Pakete",
                callback=self._pakete_anzeigen_aktion,
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "pakete.installieren",
                "Paket installieren …",
                menue="Pakete",
                callback=self._paket_installieren_aktion,
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "pakete.liste_exportieren",
                "Paketliste exportieren …",
                menue="Pakete",
                callback=self._paketliste_exportieren_aktion,
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "datei.unit_oeffnen",
                "Unit öffnen …",
                menue="Datei",
                tastenkuerzel="Ctrl+P",
                callback=self._unit_oeffnen_dialog,
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "start.mit_debugger",
                "Starten",
                menue="Start",
                tastenkuerzel="F5",
                symbol="start_debug",
                trennlinie_davor=True,
                callback=self._projekt_mit_debugger_starten_aktion,
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "start.ohne_debugger",
                "Starten ohne Debugger",
                menue="Start",
                tastenkuerzel="Ctrl+F5",
                symbol="start",
                callback=self._projekt_starten_aktion,
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "start.pause",
                "Pause",
                menue="Start",
                callback=self._debugger_pausieren_aktion,
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "start.fortsetzen",
                "Fortsetzen",
                menue="Start",
                callback=self._debugger_fortsetzen_aktion,
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "start.stopp",
                "Stopp",
                menue="Start",
                tastenkuerzel="Shift+F5",
                callback=self._debugger_stoppen_aktion,
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "start.einzelschritt",
                "Einzelschritt",
                menue="Start",
                tastenkuerzel="F11",
                callback=self._debugger_einzelschritt_aktion,
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "start.prozedurschritt",
                "Prozedurschritt",
                menue="Start",
                tastenkuerzel="F10",
                callback=self._debugger_prozedurschritt_aktion,
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "start.ruecksprung",
                "Ausführen bis Rücksprung",
                menue="Start",
                tastenkuerzel="Shift+F11",
                callback=self._debugger_ruecksprung_aktion,
            )
        )
        self.aktionen.an_hauptfenster_anhaengen(self)

    def _datei_oeffnen_dialog(self) -> None:
        pfad, _ = QFileDialog.getOpenFileName(self, "Öffnen")
        if pfad:
            self.datei_oeffnen(Path(pfad))

    def _projekt_oeffnen_dialog(self) -> None:
        pfad, _ = QFileDialog.getOpenFileName(
            self, "Projekt öffnen", filter="Natter-Projekte (*.natter)"
        )
        if pfad:
            self.projekt_oeffnen(Path(pfad))

    def _neues_projekt_dialog(self) -> None:
        """„Projekt → Neues Projekt …“ (Abschnitt 7.2): fragt Vorlage,
        Name und Zielordner ab und legt das Projekt über
        `projekt_erzeugen()` (seit M2) tatsächlich an."""
        dialog = NeuesProjektDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        werte = dialog.werte()
        if werte is None:
            self.statusBar().showMessage("Name und Ordner werden benötigt.")
            return
        vorlage, projektordner, name = werte
        try:
            projekt = projekt_erzeugen(vorlage, projektordner, name)
        except (ValueError, FileExistsError) as fehler:
            self.statusBar().showMessage(f"Projekt konnte nicht angelegt werden: {fehler}")
            return
        self.projekt = projekt
        self.explorer.projekt_anzeigen(projekt)
        self.statusBar().showMessage(f"Projekt {projekt.name} angelegt")

    def projekt_dateien(self) -> list[Path]:
        """Alle Units und Formulare des offenen Projekts, für „Unit
        öffnen …“ (Abschnitt 7.4). Leer, wenn kein Projekt offen ist."""
        if self.projekt is None:
            return []
        return sorted(self.projekt.units() + self.projekt.formulare())

    def _unit_oeffnen_dialog(self) -> None:
        """„Unit öffnen …“ (Strg+P, Abschnitt 7.4, 7.9)."""
        dateien = self.projekt_dateien()
        if not dateien:
            return
        dialog = SchnellAuswahl(dateien, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.ausgewaehlte_datei is not None:
            self.datei_oeffnen(dialog.ausgewaehlte_datei)

    def unit_erzeugen(self, name: str | None = None, *, inhalt: str = "") -> Path:
        """„Neue Unit“ (Abschnitt 7.2, 7.4): legt `u_neu<n>.py` an (oder
        mit gegebenem `name`/`inhalt`), fügt sie dem Projekt-Explorer hinzu
        und öffnet sie im Editor."""
        if self.projekt is None:
            raise RuntimeError("Kein Projekt offen.")

        if name is None:
            name = self._naechster_unit_name()

        pfad = self.projekt.ordner / f"{name}.py"
        if pfad.exists():
            raise FileExistsError(f"{pfad} existiert bereits.")

        pfad.write_text(inhalt, encoding="utf-8")
        self.explorer.projekt_anzeigen(self.projekt)
        self.datei_oeffnen(pfad)
        return pfad

    def _naechster_unit_name(self) -> str:
        vorhandene = {p.stem for p in self.projekt.units()}
        zaehler = 1
        while f"u_neu{zaehler}" in vorhandene:
            zaehler += 1
        return f"u_neu{zaehler}"

    def _neue_test_unit_aktion(self) -> None:
        """„Neue Test-Unit“ (Abschnitt 8.6): legt `test_neu<n>.py` mit
        einer `unittest`-Grundstruktur an."""
        if self.projekt is None:
            self.statusBar().showMessage("Kein Projekt offen.")
            return
        vorhandene = {p.stem for p in self.projekt.units()}
        zaehler = 1
        while f"test_neu{zaehler}" in vorhandene:
            zaehler += 1
        name = f"test_neu{zaehler}"
        self.unit_erzeugen(name, inhalt=_TEST_UNIT_VORLAGE)

    # -- Test-Explorer (Abschnitt 8.6) ---------------------------------------

    def _alle_tests_ausfuehren_aktion(self) -> None:
        if self.projekt is None:
            self.statusBar().showMessage("Kein Projekt offen.")
            return
        ergebnisse = tests_ausfuehren(self.projekt.ordner)
        self._letzte_testergebnisse = ergebnisse
        self._tests_baum_befuellen(ergebnisse)
        anzahl_fehlgeschlagen = sum(1 for e in ergebnisse if e.status != "bestanden")
        self.statusBar().showMessage(
            f"{len(ergebnisse)} Test(s), {anzahl_fehlgeschlagen} nicht bestanden"
        )
        self.panels.setCurrentWidget(self.tests_baum)

    def _testergebnisse_exportieren_aktion(self) -> None:
        """„Testergebnisse als HTML exportieren“ (Abschnitt 8.6) – nutzt
        die Ergebnisse des letzten „Alle Tests ausführen“-Laufs."""
        if not self._letzte_testergebnisse:
            self.statusBar().showMessage("Noch keine Testergebnisse zum Exportieren.")
            return
        pfad, _ = QFileDialog.getSaveFileName(
            self, "Testergebnisse exportieren", filter="HTML-Datei (*.html)"
        )
        if not pfad:
            return
        titel = self.projekt.name if self.projekt is not None else "Testprotokoll"
        html = ergebnisse_als_html(self._letzte_testergebnisse, titel=titel)
        Path(pfad).write_text(html, encoding="utf-8")
        self.statusBar().showMessage(f"Testprotokoll gespeichert: {pfad}")

    def _als_exe_exportieren_aktion(self) -> None:
        """„Projekt → Als Exe exportieren …“ (Abschnitt 16, 17;
        M8 Schritt 4): baut das Projekt mit PyInstaller. Läuft
        blockierend, wie „Alle Tests ausführen“ – ein Export dauert für
        ein Schulprojekt typischerweise 15-40 Sekunden."""
        if self.projekt is None:
            self.statusBar().showMessage("Kein Projekt offen.")
            return

        self.statusBar().showMessage("Exe wird erstellt … (kann etwas dauern)")
        QApplication.processEvents()

        ergebnis = exe_exportieren(self.projekt)

        if not ergebnis.erfolgreich:
            self.meldungen_liste.clear()
            self.meldungen_liste.addItems(
                ["[Exe-Export fehlgeschlagen]", *ergebnis.protokoll.splitlines()[-40:]]
            )
            self.panels.setCurrentWidget(self.meldungen_liste)
            self.statusBar().showMessage("Exe-Export fehlgeschlagen, siehe Meldungen.")
            return

        self.statusBar().showMessage(f"Exe erstellt: {ergebnis.ausgabe_pfad}")
        if sys.platform == "win32":
            os.startfile(ergebnis.ausgabe_pfad.parent)

    def _tests_baum_befuellen(self, ergebnisse: list[Testergebnis]) -> None:
        self.tests_baum.clear()
        baum: dict[str, dict[str, list[Testergebnis]]] = {}
        for ergebnis in ergebnisse:
            teile = ergebnis.id.split(".")
            modul = teile[0] if teile else ergebnis.id
            klasse = teile[1] if len(teile) > 1 else ""
            baum.setdefault(modul, {}).setdefault(klasse, []).append(ergebnis)

        for modul, klassen in sorted(baum.items()):
            modul_eintrag = QTreeWidgetItem(self.tests_baum, [modul])
            modul_eintrag.setData(0, _TEST_ID_ROLLE, modul)
            for klasse, tests in sorted(klassen.items()):
                if klasse:
                    klassen_eintrag = QTreeWidgetItem(modul_eintrag, [klasse])
                    klassen_eintrag.setData(0, _TEST_ID_ROLLE, f"{modul}.{klasse}")
                else:
                    klassen_eintrag = modul_eintrag
                for ergebnis in tests:
                    self._test_eintrag_erzeugen(klassen_eintrag, ergebnis)
        self.tests_baum.expandAll()
        self.tests_baum.resizeColumnToContents(0)

    def _test_eintrag_erzeugen(self, eltern: QTreeWidgetItem, ergebnis: Testergebnis) -> None:
        methode = ergebnis.id.rsplit(".", 1)[-1]
        eintrag = QTreeWidgetItem(eltern, [methode])
        eintrag.setData(0, _TEST_ID_ROLLE, ergebnis.id)
        self._test_eintrag_aktualisieren(eintrag, ergebnis)

    def _bei_test_doppelklick(self, eintrag: QTreeWidgetItem, _spalte: int) -> None:
        """Doppelklick führt den Test/die Datei/die Klasse unter diesem
        Baumeintrag erneut aus (Abschnitt 8.6: „Einzelnen Test, eine
        Datei oder alle Tests ausführen“) und aktualisiert nur die
        betroffenen Blatt-Einträge, ohne den ganzen Baum neu aufzubauen."""
        test_id = eintrag.data(0, _TEST_ID_ROLLE)
        if test_id is None or self.projekt is None:
            return
        ergebnisse = tests_ausfuehren(self.projekt.ordner, ziel=test_id)
        blaetter = self._blatt_eintraege_sammeln(eintrag)
        for ergebnis in ergebnisse:
            ziel_eintrag = blaetter.get(ergebnis.id, eintrag if eintrag.childCount() == 0 else None)
            if ziel_eintrag is not None:
                self._test_eintrag_aktualisieren(ziel_eintrag, ergebnis)

    def _blatt_eintraege_sammeln(self, eintrag: QTreeWidgetItem) -> dict[str, QTreeWidgetItem]:
        """Test-ID → Baumeintrag für alle Blätter (Testmethoden) unter
        `eintrag` (auch `eintrag` selbst, falls es schon ein Blatt ist)."""
        if eintrag.childCount() == 0:
            test_id = eintrag.data(0, _TEST_ID_ROLLE)
            return {test_id: eintrag} if test_id else {}
        ergebnis: dict[str, QTreeWidgetItem] = {}
        for i in range(eintrag.childCount()):
            ergebnis.update(self._blatt_eintraege_sammeln(eintrag.child(i)))
        return ergebnis

    def _test_eintrag_aktualisieren(self, eintrag: QTreeWidgetItem, ergebnis: Testergebnis) -> None:
        eintrag.setText(1, ergebnis.status)
        eintrag.setText(2, f"{ergebnis.dauer:.3f}")
        farbe = QColor(_STATUS_FARBE.get(ergebnis.status, "#000000"))
        for spalte in range(3):
            eintrag.setForeground(spalte, farbe)
        if ergebnis.status == "fehlgeschlagen" and ergebnis.soll is not None:
            eintrag.setToolTip(1, f"Soll: {ergebnis.soll} · Ist: {ergebnis.ist}")
        elif ergebnis.nachricht:
            eintrag.setToolTip(1, ergebnis.nachricht)
        else:
            eintrag.setToolTip(1, "")

    def _neue_unit_aktion(self) -> None:
        if self.projekt is None:
            self.statusBar().showMessage("Kein Projekt offen.")
            return
        self.unit_erzeugen()

    def _unit_umbenennen(self, pfad: Path) -> None:
        """„⋮ → Umbenennen …“ im Projekt-Explorer (Nutzer-Feedback,
        September 2026): benennt die Datei auf der Platte um und hält
        einen ggf. offenen Editor-Tab dabei synchron."""
        neuer_name, ok = QInputDialog.getText(
            self, "Unit umbenennen", "Neuer Dateiname:", text=pfad.name
        )
        if not ok or not neuer_name or neuer_name == pfad.name:
            return
        if not neuer_name.endswith(".py"):
            neuer_name += ".py"
        ziel = pfad.parent / neuer_name
        if ziel.exists():
            self.statusBar().showMessage(f"„{neuer_name}“ existiert bereits.")
            return

        try:
            pfad.rename(ziel)
        except OSError as fehler:
            self.statusBar().showMessage(f"Umbenennen fehlgeschlagen: {fehler}")
            return

        self._offenen_tab_pfad_aktualisieren(pfad, ziel)
        if self.projekt is not None:
            self.explorer.projekt_anzeigen(self.projekt)
        self.statusBar().showMessage(f"„{pfad.name}“ zu „{neuer_name}“ umbenannt.")

    def _unit_loeschen(self, pfad: Path) -> None:
        """„⋮ → Löschen …“ im Projekt-Explorer: fragt nach, schließt
        einen ggf. offenen Editor-Tab und löscht die Datei."""
        antwort = QMessageBox.question(
            self,
            "Unit löschen",
            f"„{pfad.name}“ wirklich unwiderruflich löschen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if antwort != QMessageBox.StandardButton.Yes:
            return

        for index in range(self.editor_tabs.count()):
            editor = self.editor_tabs.widget(index)
            if (
                isinstance(editor, QPlainTextEdit)
                and editor.property(_PFAD_EIGENSCHAFT) == str(pfad)
            ):
                self.editor_tabs.removeTab(index)
                break

        try:
            pfad.unlink()
        except OSError as fehler:
            self.statusBar().showMessage(f"Löschen fehlgeschlagen: {fehler}")
            return

        if self.projekt is not None:
            self.explorer.projekt_anzeigen(self.projekt)
        self.statusBar().showMessage(f"„{pfad.name}“ gelöscht.")

    def _offenen_tab_pfad_aktualisieren(self, alt: Path, neu: Path) -> None:
        for index in range(self.editor_tabs.count()):
            editor = self.editor_tabs.widget(index)
            if (
                isinstance(editor, QPlainTextEdit)
                and editor.property(_PFAD_EIGENSCHAFT) == str(alt)
            ):
                editor.setProperty(_PFAD_EIGENSCHAFT, str(neu))
                self.editor_tabs.setTabText(index, neu.name)
                break

    def _dock_erzeugen(
        self, titel: str, bereich: Qt.DockWidgetArea, inhalt: QWidget | None = None
    ) -> QDockWidget:
        dock = QDockWidget(titel, self)
        dock.setObjectName(titel)  # von QMainWindow.saveState()/restoreState() benötigt
        dock.setWidget(inhalt if inhalt is not None else QWidget())
        self.addDockWidget(bereich, dock)
        return dock

    def menue(self, titel: str):
        """Liefert das Menü mit diesem Titel (Abschnitt 7.2)."""
        return self._menues[titel]

    def projekt_oeffnen(self, pfad: Path) -> Projekt:
        """„Projekt öffnen …“ (Abschnitt 7.2): lädt das Projekt und füllt
        den Projekt-Explorer."""
        self.projekt = Projekt.laden(Path(pfad))
        self.explorer.projekt_anzeigen(self.projekt)
        self.statusBar().showMessage(f"Projekt {self.projekt.name} geöffnet")
        return self.projekt

    def datei_oeffnen(self, pfad: Path) -> QPlainTextEdit:
        """„Öffnen …“ (Abschnitt 7.2): öffnet eine einzelne Datei in
        einem Editor-Tab, unabhängig vom Projekt. Bereits offene Dateien
        werden nur aktiviert statt doppelt geöffnet."""
        pfad = Path(pfad)
        for index in range(self.editor_tabs.count()):
            editor = self.editor_tabs.widget(index)
            if editor.property(_PFAD_EIGENSCHAFT) == str(pfad):
                self.editor_tabs.setCurrentIndex(index)
                return editor

        editor = QuelltextEditor(
            thema=theme_aufloesen(self._design_thema), schriftart=self._code_schriftart
        )
        editor.einzugslinien_setzen(self.einzugslinien_aktion.isChecked())
        editor.setPlainText(pfad.read_text(encoding="utf-8"))
        editor.setProperty(_PFAD_EIGENSCHAFT, str(pfad))
        editor.document().modificationChanged.connect(
            lambda geaendert, editor=editor: self._aenderung_markieren(editor, geaendert)
        )
        index = self.editor_tabs.addTab(editor, pfad.name)
        self.editor_tabs.setCurrentIndex(index)
        return editor

    def _aenderung_markieren(self, editor: QPlainTextEdit, geaendert: bool) -> None:
        index = self.editor_tabs.indexOf(editor)
        if index == -1:
            return
        basisname = Path(editor.property(_PFAD_EIGENSCHAFT)).name
        self.editor_tabs.setTabText(index, f"{basisname} ●" if geaendert else basisname)

    def _aktuelle_datei_speichern(self) -> None:
        """„Speichern“ (Strg+S, Abschnitt 7.2, 7.9). Wirkt nur auf
        Text-Editor-Tabs; ein Designer-Tab hat hier (noch) nichts zu
        speichern (Eigenschaftsänderungen im Designer landen erst mit
        dem Kommando-Pattern aus Schritt 5 zurück in der `.pfm`)."""
        index = self.editor_tabs.currentIndex()
        if index == -1:
            return
        editor = self.editor_tabs.widget(index)
        if not isinstance(editor, QPlainTextEdit):
            return
        pfad = Path(editor.property(_PFAD_EIGENSCHAFT))
        pfad.write_text(editor.toPlainText(), encoding="utf-8")
        editor.document().setModified(False)

    # -- Bearbeiten (Abschnitt 7.2) -------------------------------------------

    def _aktueller_editor(self) -> QPlainTextEdit | None:
        """Der aktive Editor-Tab, falls es einer ist (nicht z. B. ein
        Designer- oder CSV-/Bild-/HTML-Betrachter-Tab)."""
        widget = self.editor_tabs.currentWidget()
        return widget if isinstance(widget, QPlainTextEdit) else None

    def _bearbeiten_rueckgaengig(self) -> None:
        editor = self._aktueller_editor()
        if editor is not None:
            editor.undo()

    def _bearbeiten_wiederholen(self) -> None:
        editor = self._aktueller_editor()
        if editor is not None:
            editor.redo()

    def _bearbeiten_ausschneiden(self) -> None:
        editor = self._aktueller_editor()
        if editor is not None:
            editor.cut()

    def _bearbeiten_kopieren(self) -> None:
        editor = self._aktueller_editor()
        if editor is not None:
            editor.copy()

    def _bearbeiten_einfuegen(self) -> None:
        editor = self._aktueller_editor()
        if editor is not None:
            editor.paste()

    def _bearbeiten_alles_auswaehlen(self) -> None:
        editor = self._aktueller_editor()
        if editor is not None:
            editor.selectAll()

    # -- Suchen (Abschnitt 7.2) -----------------------------------------------

    def _suchen_aktion(self) -> None:
        editor = self._aktueller_editor()
        if editor is None:
            self.statusBar().showMessage("Kein Editor-Tab aktiv.")
            return
        self._suchen_dialog = SuchenErsetzenDialog(editor, self)
        self._suchen_dialog.show()
        self._suchen_dialog.raise_()
        self._suchen_dialog.activateWindow()

    def _gehe_zu_zeile_aktion(self) -> None:
        editor = self._aktueller_editor()
        if editor is None:
            self.statusBar().showMessage("Kein Editor-Tab aktiv.")
            return
        maximum = editor.document().blockCount()
        zeile, ok = QInputDialog.getInt(self, "Gehe zu Zeile", "Zeile:", 1, 1, maximum)
        if not ok:
            return
        block = editor.document().findBlockByNumber(zeile - 1)
        cursor = editor.textCursor()
        cursor.setPosition(block.position())
        editor.setTextCursor(cursor)
        editor.ensureCursorVisible()
        editor.setFocus()

    # -- Quelltext (Abschnitt 7.2) ---------------------------------------------

    def _kommentar_umschalten_aktion(self) -> None:
        """„Quelltext → Kommentar umschalten“ (Strg+#, wie in VS Code auf
        deutschen Tastaturen): kommentiert die aktuelle Zeile bzw. jede
        Zeile der Auswahl mit `# ` aus oder ein."""
        editor = self._aktueller_editor()
        if editor is None:
            return
        cursor = editor.textCursor()
        dokument = editor.document()
        start_block = dokument.findBlock(cursor.selectionStart()).blockNumber()
        ende_position = cursor.selectionEnd()
        if cursor.hasSelection() and ende_position > cursor.selectionStart():
            ende_position -= 1  # Zeilenumbruch am Selektionsende nicht mitzählen
        end_block = dokument.findBlock(ende_position).blockNumber()

        zeilen = [dokument.findBlockByNumber(n).text() for n in range(start_block, end_block + 1)]
        neue_zeilen = _kommentar_umschalten_zeilen(zeilen)

        erster = dokument.findBlockByNumber(start_block)
        letzter = dokument.findBlockByNumber(end_block)
        ersetz_cursor = QTextCursor(dokument)
        ersetz_cursor.setPosition(erster.position())
        ersetz_cursor.setPosition(
            letzter.position() + letzter.length() - 1, QTextCursor.MoveMode.KeepAnchor
        )
        ersetz_cursor.insertText("\n".join(neue_zeilen))

    # -- Fenster (Abschnitt 7.2) -----------------------------------------------

    def _naechster_tab_aktion(self) -> None:
        anzahl = self.editor_tabs.count()
        if anzahl:
            self.editor_tabs.setCurrentIndex((self.editor_tabs.currentIndex() + 1) % anzahl)

    def _vorheriger_tab_aktion(self) -> None:
        anzahl = self.editor_tabs.count()
        if anzahl:
            self.editor_tabs.setCurrentIndex((self.editor_tabs.currentIndex() - 1) % anzahl)

    def _layout_zuruecksetzen_aktion(self) -> None:
        if self._urspruengliches_layout is not None:
            self.restoreState(self._urspruengliches_layout)

    def _design_wechseln(self, thema: str) -> None:
        """„Ansicht → Design → Hell/Dunkel/System“: wendet das IDE-Theme
        sofort an (inkl. bereits offener Editor-Tabs, Abschnitt 7.5) und
        merkt sich die Wahl für den nächsten Start."""
        self._design_thema = thema
        self.setStyleSheet(ide_qss_erzeugen(thema, code_schriftart=self._code_schriftart))
        self._design_einstellungen.setValue("design/thema", thema)

        aufgeloest = theme_aufloesen(thema)
        for index in range(self.editor_tabs.count()):
            editor = self.editor_tabs.widget(index)
            if isinstance(editor, QuelltextEditor):
                editor.thema_setzen(aufgeloest)

        # Symbole neu laden: ein `QIcon` merkt sich seine Farben. Ohne
        # das behielt die Werkzeugleiste nach dem Umschalten die alten
        # Farben, bis Natter neu gestartet wurde.
        self.aktionen.symbole_erneuern(thema)
        self.palette.symbole_erneuern(thema)
        self.setWindowIcon(symbol("app", thema))

    def _einzugslinien_umschalten(self, sichtbar: bool) -> None:
        """Schaltet die Einrückungslinien in allen offenen Editor-Tabs
        und merkt sich die Wahl für den nächsten Start."""
        self._design_einstellungen.setValue("editor/einzugslinien", sichtbar)
        for index in range(self.editor_tabs.count()):
            editor = self.editor_tabs.widget(index)
            if isinstance(editor, QuelltextEditor):
                editor.einzugslinien_setzen(sichtbar)

    def _code_schriftart_wechseln(self, schriftart: str) -> None:
        """„Ansicht → Schriftart“: wendet die gewählte Editor-Schrift
        sofort an (auch auf bereits offene Editor-Tabs) und merkt sich
        die Wahl für den nächsten Start."""
        self._code_schriftart = schriftart
        self.setStyleSheet(ide_qss_erzeugen(self._design_thema, code_schriftart=schriftart))
        self._design_einstellungen.setValue("editor/schriftart", schriftart)

        for index in range(self.editor_tabs.count()):
            editor = self.editor_tabs.widget(index)
            if isinstance(editor, QuelltextEditor):
                editor.schriftart_setzen(schriftart)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Merkt sich Größe/Sichtbarkeit aller Docks für den nächsten
        Start (Nutzer-Feedback September 2026: ein geschlossenes Dock
        wie „Datenbank“ soll auch beim nächsten Mal zu bleiben)."""
        self._design_einstellungen.setValue("fenster/layout", self.saveState())
        super().closeEvent(event)

    # -- Hilfe (Abschnitt 7.2) -------------------------------------------------

    def _komponenten_referenz_aktion(self) -> None:
        pfad = Path(__file__).resolve().parent.parent.parent / "docs" / "komponenten.md"
        if not pfad.exists():
            self.statusBar().showMessage("Komponenten-Referenz nicht gefunden.")
            return
        open_url(str(pfad))

    def _ueber_aktion(self) -> None:
        QMessageBox.about(
            self,
            "Über Natter",
            "<h3>Natter</h3><p>Eine Lazarus-artige IDE für Python – "
            "Umstieg von Pascal/Lazarus auf Python.</p>",
        )

    def designer_oeffnen(self, pfad: Path) -> Form:
        """Öffnet eine `.pfm`-Datei im Formular-Designer statt als
        Rohtext (Abschnitt 4.2, 7.7): der Designer rendert echte
        `pcl`-Komponenten, kein Nachbau. Bereits offene Formulare werden
        nur aktiviert statt erneut geladen."""
        pfad = Path(pfad)
        schluessel = str(pfad)
        if schluessel in self._pfad_zu_formular:
            formular = self._pfad_zu_formular[schluessel]
            index = self._tab_index(formular._qwidget)
            if index != -1:
                self.editor_tabs.setCurrentIndex(index)
            return formular

        formular = formular_fuer_designer_laden(pfad)
        canvas = DesignerCanvas(formular, pfm_pfad=pfad)
        self._design_datei_abgleichen(pfad)
        canvas.auswahl_beobachten(self._designer_auswahl_geaendert)
        canvas.aenderung_beobachten(lambda: self._design_pruefen_automatisch(canvas))
        canvas.bild_beobachten(self._designer_bild_abgelegt)
        self._offene_canvases.append(canvas)
        self._pfad_zu_formular[schluessel] = formular
        self._widget_zu_canvas[formular._qwidget] = canvas

        index = self.editor_tabs.addTab(
            self._designer_rollbereich(formular._qwidget), f"{pfad.stem} (Designer)"
        )
        self.editor_tabs.setCurrentIndex(index)
        self.objektinspektor.formular_anzeigen(formular, canvas)
        return formular

    def diagramm_oeffnen(self, pfad: Path) -> DiagrammFenster:
        """Öffnet eine `.pdiag`-Datei im Diagramm-Editor (Abschnitt 13.1):
        eigenes Fenster mit eigenem Taskleisten-Eintrag, kein Tab.
        Bereits offene Diagramme werden nur nach vorne geholt."""
        pfad = Path(pfad)
        schluessel = str(pfad)
        vorhanden = self._offene_diagramme.get(schluessel)
        if vorhanden is not None:
            vorhanden.show()
            vorhanden.raise_()
            vorhanden.activateWindow()
            return vorhanden

        fenster = DiagrammFenster(Diagramm.laden(pfad))
        fenster.destroyed.connect(lambda *_: self._offene_diagramme.pop(schluessel, None))
        self._offene_diagramme[schluessel] = fenster
        fenster.show()
        return fenster

    def _neues_diagramm_aktion(self) -> None:
        """„Datei → Neues Diagramm …“ (Abschnitt 13.1): legt eine
        `.pdiag` im Ordner `diagramme/` des offenen Projekts an und
        öffnet sie im Diagramm-Editor."""
        if self.projekt is None:
            self.statusBar().showMessage("Kein Projekt offen.")
            return

        beschriftungen = [TYP_BESCHRIFTUNGEN[typ] for typ in MVP_TYPEN]
        beschriftung, bestaetigt = QInputDialog.getItem(
            self, "Neues Diagramm", "Diagrammtyp:", beschriftungen, 0, False
        )
        if not bestaetigt:
            return
        typ = MVP_TYPEN[beschriftungen.index(beschriftung)]

        name, bestaetigt = QInputDialog.getText(
            self, "Neues Diagramm", "Name:", text=self.projekt.name.lower()
        )
        if not bestaetigt or not name.strip():
            return

        pfad = self.projekt.diagramm_ordner / f"{name.strip()}.pdiag"
        if pfad.exists():
            self.statusBar().showMessage(f"{pfad.name} gibt es schon.")
            return

        pfad.parent.mkdir(parents=True, exist_ok=True)
        diagramm_erzeugen(typ, pfad, name.strip())
        self.explorer.projekt_anzeigen(self.projekt)
        self.diagramm_oeffnen(pfad)

    def _design_datei_abgleichen(self, pfm_pfad: Path) -> None:
        """Bringt `u_*_design.py` auf den Stand der `.pfm` beim Öffnen.

        Der Designer selbst kompiliert den erzeugten Code nur im
        Speicher. Real gefunden beim Lazarus-Import: das importierte
        Formular erschien vollständig im Designer, aber die `.pfm` war
        die einzige Datei, die geschrieben wurde - `u_main_design.py`
        blieb das leere Vorlagenformular, das gestartete Programm zeigte
        also weiter ein leeres Fenster. Dasselbe gilt für jede von außen
        geänderte `.pfm`."""
        ziel = pfm_pfad.parent / f"{pfm_pfad.stem}_design.py"
        quelltext = design_code_erzeugen(
            json.loads(pfm_pfad.read_text(encoding="utf-8")), pfm_pfad.name
        )
        if not ziel.exists() or ziel.read_text(encoding="utf-8") != quelltext:
            ziel.write_text(quelltext, encoding="utf-8")

    def _designer_rollbereich(self, formular_widget: QWidget) -> QScrollArea:
        """Ein Designer-Tab steckt in einem Rollbereich, damit sich auch
        ein Formular bedienen lässt, das größer ist als das Fenster
        (vom Nutzer gemeldet: „scrollen … funktioniert nicht“).

        Bewusst **ohne** `setWidgetResizable`: die Größe eines Formulars
        ist eine Eigenschaft, die der Nutzer gesetzt hat – sie darf sich
        nicht danach richten, wie groß das IDE-Fenster gerade ist."""
        rollbereich = QScrollArea()
        rollbereich.setWidget(formular_widget)
        rollbereich.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        return rollbereich

    def _tab_inhalt(self, widget: QWidget | None) -> QWidget | None:
        """Der eigentliche Inhalt eines Tabs – bei Designer-Tabs das
        Formular im Rollbereich, sonst das Widget selbst."""
        if isinstance(widget, QScrollArea):
            return widget.widget()
        return widget

    def _tab_index(self, inhalt: QWidget) -> int:
        """Wie `QTabWidget.indexOf`, aber es findet auch ein Formular,
        das in einem Rollbereich steckt."""
        for index in range(self.editor_tabs.count()):
            if self._tab_inhalt(self.editor_tabs.widget(index)) is inhalt:
                return index
        return -1

    def _bei_tab_wechsel(self, index: int) -> None:
        widget = self._tab_inhalt(self.editor_tabs.widget(index))
        self._aktueller_canvas = self._widget_zu_canvas.get(widget)

    def _tab_schliessen(self, index: int) -> None:
        """„×“ auf einem Editor-/Designer-Tab (Abschnitt 7.9): bislang war
        `tabCloseRequested` gar nicht verbunden – der Knopf tat nichts.
        Fragt bei ungespeicherten Textänderungen nach; Designer-Tabs
        schreiben laufend automatisch in die `.pfm` zurück und haben
        daher nichts zu bestätigen."""
        widget = self._tab_inhalt(self.editor_tabs.widget(index))
        if widget is None:
            return
        if isinstance(widget, QPlainTextEdit) and widget.document().isModified():
            antwort = QMessageBox.question(
                self,
                "Ungespeicherte Änderungen",
                "Änderungen vor dem Schließen speichern?",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
            )
            if antwort == QMessageBox.StandardButton.Cancel:
                return
            if antwort == QMessageBox.StandardButton.Save:
                self.editor_tabs.setCurrentIndex(index)
                self._aktuelle_datei_speichern()

        canvas = self._widget_zu_canvas.pop(widget, None)
        if canvas is not None:
            if canvas in self._offene_canvases:
                self._offene_canvases.remove(canvas)
            for schluessel, formular in list(self._pfad_zu_formular.items()):
                if formular._qwidget is widget:
                    del self._pfad_zu_formular[schluessel]
            if self._aktueller_canvas is canvas:
                self._aktueller_canvas = None

        self.editor_tabs.removeTab(index)

    def _bei_palette_doppelklick(self, eintrag) -> None:
        """Doppelklick in der Palette platziert die Komponente mittig im
        aktiven Formular-Designer (Abschnitt 7.3)."""
        if self._aktueller_canvas is None:
            self.statusBar().showMessage("Kein Formular-Designer geöffnet.")
            return
        typ = eintrag.data(TYP_ROLLE)
        formular = self._aktueller_canvas.formular
        # Ein vorheriger einfacher Klick (siehe _bei_palette_klick) hat
        # ggf. bereits einen Platzierungsmodus scharf gemacht - der
        # Doppelklick platziert hier sofort selbst, also wieder abbrechen.
        self._aktueller_canvas.platzierungsmodus_setzen(None)
        self._aktueller_canvas.komponente_platzieren(
            typ, formular.width // 2, formular.height // 2
        )

    def _bei_palette_klick(self, eintrag) -> None:
        """Einfacher Klick in der Palette (Nutzer-Feedback September
        2026: „ich möchte per Klick neue Objekte auf der GUI
        hinzufügen"): macht die Komponente „scharf" (Fadenkreuz-Cursor
        im Designer, wie in Lazarus) - der nächste Klick auf das
        Formular platziert sie genau dort, automatisch in `.pfm` und den
        generierten Code übernommen (`_nach_aenderung`)."""
        if self._aktueller_canvas is None:
            return
        typ = eintrag.data(TYP_ROLLE)
        self._aktueller_canvas.platzierungsmodus_setzen(typ)

    def _designer_auswahl_geaendert(self, komponente) -> None:
        self.objektinspektor._eigenschaften_anzeigen(komponente)

    def _designer_bild_abgelegt(self, relativer_pfad: str) -> None:
        """Nach Drag & Drop einer Bilddatei in den Designer (Abschnitt
        11.4): nennt den Pfad im Projekt und die Codezeile, mit der das
        laufende Programm das Bild lädt – die `.pfm` speichert die
        Eigenschaft `picture` noch nicht."""
        self.statusBar().showMessage(
            f"Bild nach {relativer_pfad} übernommen. Im Code laden mit: "
            f'picture.load_from_file("{relativer_pfad}")'
        )

    # -- Design-Prüfer (Abschnitt 14) ----------------------------------------

    def _design_pruefen_aktion(self) -> None:
        """„Werkzeuge → Design prüfen“: prüft das im Designer aktive
        Formular (nicht das ganze Projekt auf einmal)."""
        if self._aktueller_canvas is None:
            self.statusBar().showMessage("Kein Formular-Designer geöffnet.")
            return
        self._design_pruefen(self._aktueller_canvas)

    def _design_pruefen_automatisch(self, canvas: DesignerCanvas) -> None:
        if self._design_pruefung_automatisch_aktion.qaction.isChecked():
            self._design_pruefen(canvas)

    def _design_pruefen(self, canvas: DesignerCanvas) -> None:
        pfm = pfm_aus_formular(canvas.formular)
        befunde = pruefen(pfm, abgeschaltete_regeln=self._design_pruefer_abgeschaltete_regeln)
        self.meldungen_liste.clear()
        for befund in befunde:
            eintrag = QListWidgetItem(f"[{befund.kategorie}] {befund.meldung}")
            if befund.komponente is not None:
                eintrag.setData(_MELDUNG_ROLLE, (canvas, befund.komponente))
            self.meldungen_liste.addItem(eintrag)
        if befunde:
            self.panels.setCurrentWidget(self.meldungen_liste)
        self.statusBar().showMessage(f"Design-Prüfung: {len(befunde)} Fund(e).")

    def _bei_meldung_geklickt(self, eintrag: QListWidgetItem) -> None:
        """Klick auf einen Design-Prüfer-Befund markiert die betroffene
        Komponente im Designer (Abschnitt 14). Ruff-Funde tragen keine
        Daten unter `_MELDUNG_ROLLE` und werden hier ignoriert."""
        daten = eintrag.data(_MELDUNG_ROLLE)
        if daten is None:
            return
        canvas, komponenten_name = daten
        komponente = getattr(canvas.formular, komponenten_name, None)
        if komponente is not None:
            index = self._tab_index(canvas.formular._qwidget)
            if index != -1:
                self.editor_tabs.setCurrentIndex(index)
            canvas._auswaehlen(komponente)

    def _umgebung_pruefen_aktion(self) -> None:
        """„Werkzeuge → Umgebung prüfen“ (Abschnitt 17.8): vollständige
        Prüfung aller Programmdateien gegen das signierte
        Prüfsummen-Manifest – im Unterschied zur schnellen Prüfung der
        Kerndateien bei jedem Start. Jede betroffene Datei erscheint
        einzeln im Panel „Meldungen“."""
        ergebnis = installation_pruefen(vollstaendig=True)
        if ergebnis is None:
            self.statusBar().showMessage(
                "Keine Prüfung möglich: Natter läuft nicht aus einer gebauten Installation."
            )
            return
        if ergebnis.in_ordnung:
            self.statusBar().showMessage("Umgebung geprüft: alle Programmdateien unverändert.")
            return

        self.meldungen_liste.clear()
        for datei in ergebnis.betroffene_dateien:
            self.meldungen_liste.addItem(f"[Umgebung] {datei}")
        self.panels.setCurrentWidget(self.meldungen_liste)
        self.statusBar().showMessage(ergebnis.als_meldung())

    def _lazarus_formular_importieren_aktion(self) -> None:
        """„Werkzeuge → Lazarus-Formular importieren …“ (Abschnitt 15):
        `.lfm` wählen, in `.pfm` umwandeln, unter einem gewählten Pfad
        speichern, im Designer öffnen und direkt durch den Design-Prüfer
        aus M7 laufen lassen. Nicht unterstützte Komponenten/
        Eigenschaften landen als Hinweis im Importbericht (Panel
        „Meldungen“), zusammen mit den Design-Prüfer-Funden."""
        quelle, _ = QFileDialog.getOpenFileName(
            self, "Lazarus-Formular importieren", filter="Lazarus-Formulare (*.lfm)"
        )
        if not quelle:
            return
        try:
            lfm_objekt = parse_lfm(Path(quelle).read_text(encoding="utf-8"))
        except LfmParserError as fehler:
            self.statusBar().showMessage(f"Import fehlgeschlagen: {fehler}")
            return
        ergebnis = lfm_zu_pfm(lfm_objekt)

        ziel, _ = QFileDialog.getSaveFileName(
            self,
            "Formular speichern unter",
            str(Path(quelle).with_suffix(".pfm").name),
            filter="Natter-Formulare (*.pfm)",
        )
        if not ziel:
            return
        Path(ziel).write_text(
            json.dumps(ergebnis.pfm, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

        ziel_pfad = Path(ziel)
        bild_pfade = self._lazarus_bilder_schreiben(ergebnis, ziel_pfad)
        self._lazarus_unit_schreiben(ergebnis, Path(quelle), ziel_pfad, bild_pfade)

        formular = self.designer_oeffnen(Path(ziel))
        canvas = self._widget_zu_canvas[formular._qwidget]
        self._design_pruefen(canvas)
        for warnung in ergebnis.warnungen:
            self.meldungen_liste.addItem(f"[Lazarus-Import] {warnung}")
        if ergebnis.warnungen:
            self.panels.setCurrentWidget(self.meldungen_liste)

        self.statusBar().showMessage(
            f"{Path(quelle).name} importiert: {len(ergebnis.warnungen)} Hinweis(e) im "
            "Importbericht."
        )

    def _lazarus_bilder_schreiben(
        self, ergebnis: LfmImportErgebnis, ziel_pfad: Path
    ) -> dict[str, str]:
        """Schreibt die aus `Picture.Data` ausgepackten Bilder nach
        `assets/` neben die neue `.pfm` (Abschnitt 11.4: „Kopie nach
        `assets/`“) und liefert je Komponente den Pfad, mit dem das
        laufende Programm sie lädt (`assets/i_cookie.jpg`)."""
        if not ergebnis.bilder:
            return {}
        assets = ziel_pfad.parent / "assets"
        assets.mkdir(parents=True, exist_ok=True)
        bild_pfade: dict[str, str] = {}
        for komponente, bild in ergebnis.bilder.items():
            dateiname = f"{komponente}{bild.endung}"
            try:
                (assets / dateiname).write_bytes(bild.daten)
            except OSError as fehler:
                ergebnis.warnungen.append(f"{komponente}: Bild nicht schreibbar - {fehler}")
                continue
            bild_pfade[komponente] = f"assets/{dateiname}"
            ergebnis.warnungen.append(
                f"{komponente}: Bild aus Picture.Data nach assets/{dateiname} "
                f"geschrieben ({len(bild.daten)} Byte, {bild.klassenname})."
            )
        if bild_pfade:
            ergebnis.warnungen.append(
                "Bilder erscheinen erst im gestarteten Programm, noch nicht in der "
                "Designer-Vorschau: die .pfm kennt die Eigenschaft `picture` noch nicht."
            )
        return bild_pfade

    def _lazarus_unit_schreiben(
        self,
        ergebnis: LfmImportErgebnis,
        quelle: Path,
        ziel_pfad: Path,
        bild_pfade: dict[str, str],
    ) -> None:
        """Legt die Formular-Unit (`u_main.py`) zum Import an: je
        Ereignis-Handler eine leere Python-Methode, darüber der
        Pascal-Rumpf aus der gleichnamigen `.pas` als Kommentar
        (Abschnitt 15). Eine bereits vorhandene Unit wird nicht
        überschrieben."""
        unit_pfad = ziel_pfad.with_suffix(".py")
        if unit_pfad.exists():
            ergebnis.warnungen.append(
                f"{unit_pfad.name} ist schon vorhanden und wurde nicht überschrieben - "
                "die Pascal-Rümpfe stehen deshalb nirgends."
            )
            return

        pas_pfad = quelle.with_suffix(".pas")
        ruempfe: dict[str, list[str]] = {}
        if pas_pfad.exists():
            try:
                pas_text = pas_text_lesen(pas_pfad)
            except OSError as fehler:
                ergebnis.warnungen.append(f"{pas_pfad.name} nicht lesbar - {fehler}")
                pas_text = ""
            ruempfe = prozedur_ruempfe_lesen(pas_text) if pas_text else {}
        else:
            ergebnis.warnungen.append(
                f"{pas_pfad.name} nicht gefunden - die Ereignis-Methoden bleiben leer."
            )

        quelltext = unit_quelltext_erzeugen(
            ergebnis.pfm,
            design_modul=f"{ziel_pfad.stem}_design",
            pascal_ruempfe=ruempfe,
            handler_quellen=ergebnis.handler_quellen,
            pas_dateiname=pas_pfad.name,
            bild_pfade=bild_pfade,
        )
        unit_pfad.write_text(quelltext, encoding="utf-8")

        uebernommen = sum(
            1
            for methodenname, lazarus_name in ergebnis.handler_quellen.items()
            if methodenname and lazarus_name in ruempfe
        )
        ergebnis.warnungen.append(
            f"{unit_pfad.name} angelegt: {uebernommen} Pascal-Rumpf/-Rümpfe als "
            "Kommentar übernommen."
        )

    # -- Paketverwaltung (Abschnitt 7.2, 18: ide/env/) -----------------------

    def _pakete_anzeigen_aktion(self) -> None:
        """„Pakete → Paketverwaltung anzeigen“: Liste der installierten
        Pakete des aktuell aktiven Python-Interpreters."""
        try:
            pakete = installierte_pakete()
        except (OSError, PaketFehler) as fehler:
            self.statusBar().showMessage(f"Paketliste nicht lesbar: {fehler}")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Paketverwaltung")
        tabelle = QTableWidget(len(pakete), 2)
        tabelle.setHorizontalHeaderLabels(["Paket", "Version"])
        for zeile, paket in enumerate(pakete):
            tabelle.setItem(zeile, 0, QTableWidgetItem(paket.name))
            tabelle.setItem(zeile, 1, QTableWidgetItem(paket.version))
        layout = QVBoxLayout(dialog)
        layout.addWidget(tabelle)
        dialog.resize(400, 500)
        dialog.exec()

    def _paket_installieren_aktion(self) -> None:
        """„Pakete → Paket installieren …“: Name abfragen, per `pip`
        installieren, Ergebnis in der Statuszeile anzeigen."""
        name, ok = QInputDialog.getText(self, "Paket installieren", "Paketname:")
        if not ok or not name:
            return
        try:
            paket_installieren(name)
        except PaketFehler as fehler:
            self.statusBar().showMessage(f"Installation fehlgeschlagen: {fehler}")
            return
        self.statusBar().showMessage(f"{name} installiert.")

    def _paketliste_exportieren_aktion(self) -> None:
        """„Pakete → Paketliste exportieren …“: `pip freeze` in eine
        `requirements.txt`."""
        pfad, _ = QFileDialog.getSaveFileName(
            self, "Paketliste exportieren", "requirements.txt", "Text (*.txt)"
        )
        if not pfad:
            return
        try:
            paketliste_exportieren(pfad)
        except (OSError, PaketFehler) as fehler:
            self.statusBar().showMessage(f"Paketliste exportieren fehlgeschlagen: {fehler}")
            return
        self.statusBar().showMessage(f"Paketliste exportiert nach {pfad}.")

    def _bei_explorer_doppelklick(self, eintrag, spalte: int) -> None:
        pfad = eintrag.data(0, PFAD_ROLLE)
        if pfad is None:
            return
        pfad = Path(pfad)
        endung = pfad.suffix.lower()
        if endung == ".pfm":
            self.designer_oeffnen(pfad)
        elif endung == ".pdiag":
            self.diagramm_oeffnen(pfad)
        elif endung == ".csv":
            self.datei_ansicht_oeffnen(pfad, lambda: CsvAnsicht(pfad))
        elif endung in _BILD_ENDUNGEN:
            self.datei_ansicht_oeffnen(pfad, lambda: BildVorschau(pfad))
        elif endung in _HTML_ENDUNGEN:
            self.datei_ansicht_oeffnen(pfad, lambda: HtmlVorschau(pfad))
        else:
            self.datei_oeffnen(pfad)

    def datei_ansicht_oeffnen(self, pfad: Path, fabrik) -> QWidget:
        """Öffnet eine CSV-/Bild-/HTML-Datei in ihrem passenden
        Betrachter-Tab (Abschnitt 11.4, 11.5, 11.3) statt im
        Quelltexteditor. Bereits offene Betrachter werden nur aktiviert
        statt erneut geöffnet, wie bei `datei_oeffnen()`."""
        pfad = Path(pfad)
        for index in range(self.editor_tabs.count()):
            widget = self.editor_tabs.widget(index)
            if widget.property(_PFAD_EIGENSCHAFT) == str(pfad):
                self.editor_tabs.setCurrentIndex(index)
                return widget

        widget = fabrik()
        widget.setProperty(_PFAD_EIGENSCHAFT, str(pfad))
        index = self.editor_tabs.addTab(widget, pfad.name)
        self.editor_tabs.setCurrentIndex(index)
        return widget

    def _projekt_starten_aktion(self) -> None:
        """„Starten ohne Debugger“ (Strg+F5, Abschnitt 7.8). Standardmäßig
        nur eine laufende Instanz pro Projekt (Abschnitt 7.8); ein
        erneuter Start bei bereits laufendem Programm wird abgelehnt statt
        eine weitere Instanz zu starten. Vor dem Start prüft Ruff das
        Projekt (Abschnitt 8.2); bei Funden wird nicht gestartet."""
        if self.projekt is None:
            self.statusBar().showMessage("Kein Projekt offen.")
            return
        if self.laufender_prozess is not None and self.laufender_prozess.poll() is None:
            self.statusBar().showMessage(f"{self.projekt.name} läuft bereits.")
            return

        funde = projekt_pruefen(self.projekt)
        self.meldungen_liste.clear()
        if funde:
            self.meldungen_liste.addItems([str(fund) for fund in funde])
            self.panels.setCurrentWidget(self.meldungen_liste)
            self.statusBar().showMessage(
                f"{len(funde)} Fund(e) vor dem Start - nicht gestartet."
            )
            return

        self.laufender_prozess = projekt_starten(self.projekt)
        self.statusBar().showMessage(f"{self.projekt.name} gestartet")

    # -- Debugger (F5, Abschnitt 7.8/8.1) ------------------------------------

    def _offene_breakpoints(self) -> dict[Path, list[int]]:
        """Breakpoints aus allen offenen `QuelltextEditor`-Tabs, gebündelt
        nach Datei – für `DebugSitzung.starten(..., anfangs_breakpoints=...)`."""
        ergebnis: dict[Path, list[int]] = {}
        for index in range(self.editor_tabs.count()):
            editor = self.editor_tabs.widget(index)
            if isinstance(editor, QuelltextEditor) and editor.breakpoints:
                pfad = editor.property(_PFAD_EIGENSCHAFT)
                if pfad:
                    ergebnis[Path(pfad)] = sorted(editor.breakpoints)
        return ergebnis

    def _projekt_mit_debugger_starten_aktion(self) -> None:
        """„Starten“ (F5, Abschnitt 7.8): wie „Starten ohne Debugger“, aber
        mit `DebugSitzung` – Breakpoints aus den offenen Editor-Tabs werden
        übernommen."""
        if self.projekt is None:
            self.statusBar().showMessage("Kein Projekt offen.")
            return
        if self.debug_sitzung is not None:
            self.statusBar().showMessage(f"{self.projekt.name} läuft bereits (Debugger).")
            return

        funde = projekt_pruefen(self.projekt)
        self.meldungen_liste.clear()
        if funde:
            self.meldungen_liste.addItems([str(fund) for fund in funde])
            self.panels.setCurrentWidget(self.meldungen_liste)
            self.statusBar().showMessage(
                f"{len(funde)} Fund(e) vor dem Start - nicht gestartet."
            )
            return

        self.variablen_baum.clear()
        self.aufrufstapel_liste.clear()
        self._aktueller_thread_id = None

        self.debug_sitzung = DebugSitzung(self)
        self.debug_sitzung.angehalten.connect(self._debugger_angehalten)
        self.debug_sitzung.beendet.connect(self._debugger_beendet)
        self.debug_sitzung.fehler.connect(self._debugger_fehler)
        self.debug_sitzung.aufrufstapel_bereit.connect(self._debugger_aufrufstapel_bereit)
        self.debug_sitzung.bereiche_bereit.connect(self._debugger_bereiche_bereit)
        self.debug_sitzung.variablen_bereit.connect(self._debugger_variablen_bereit)
        self.debug_sitzung.exceptioninfo_bereit.connect(self._debugger_exceptioninfo_bereit)
        self.debug_sitzung.ausgewertet.connect(self._debugger_tabelle_bereit)
        self.debug_sitzung.starten(
            self.projekt.haupt_datei,
            arbeitsordner=self.projekt.ordner,
            anfangs_breakpoints=self._offene_breakpoints(),
        )
        self.statusBar().showMessage(f"{self.projekt.name} gestartet (mit Debugger)")

    def _debugger_angehalten(self, ereignis: dict) -> None:
        self._aktueller_thread_id = ereignis.get("threadId")
        grund = ereignis.get("reason", "?")
        self._letzter_haltegrund = grund
        self.statusBar().showMessage(f"Angehalten ({grund})")
        if self._aktueller_thread_id is None or self.debug_sitzung is None:
            return
        self.debug_sitzung.aufrufstapel_lesen(self._aktueller_thread_id)
        if grund == "exception":
            self.debug_sitzung.exceptioninfo_lesen(self._aktueller_thread_id)

    def _debugger_exceptioninfo_bereit(self, exception_info: dict) -> None:
        """Unbehandelte Ausnahme im laufenden Schülerprogramm: Fehler-
        katalog-Meldung im Panel „Meldungen“, Editor springt zur
        Fehlerzeile (Abschnitt 8.1)."""
        meldung = fehlermeldung_aus_dap_erzeugen(exception_info)
        if meldung is None:
            return
        self.meldungen_liste.addItem(meldung.als_text())
        self.panels.setCurrentWidget(self.meldungen_liste)
        self._zu_wo_springen(meldung.wo)

    def _zu_wo_springen(self, wo: str) -> None:
        """Öffnet die Datei aus einer Fehlermeldungs-`wo`-Zeile
        („datei.py, Zeile N, in methode“) im aktiven Projektordner und
        springt zur genannten Zeile."""
        if self.projekt is None:
            return
        dateiname = wo.split(",", 1)[0].strip()
        zeilen_treffer = re.search(r"Zeile (\d+)", wo)
        if not zeilen_treffer:
            return
        zeile = int(zeilen_treffer.group(1))
        pfad = self.projekt.ordner / dateiname
        if not pfad.exists():
            return
        editor = self.datei_oeffnen(pfad)
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        cursor.movePosition(cursor.MoveOperation.Down, cursor.MoveMode.MoveAnchor, zeile - 1)
        editor.setTextCursor(cursor)

    def _debugger_beendet(self, exitcode: int) -> None:
        self.statusBar().showMessage(f"Debugger beendet (Exitcode {exitcode})")
        self.debug_sitzung = None
        self._aktueller_thread_id = None
        self._letzter_aufrufstapel = []
        self.variablen_baum.clear()
        self.aufrufstapel_liste.clear()

    def _debugger_fehler(self, meldung: str) -> None:
        self.meldungen_liste.addItem(meldung)
        self.panels.setCurrentWidget(self.meldungen_liste)

    def _debugger_aufrufstapel_bereit(self, stapel: list[dict]) -> None:
        """Beim Anhalten (Breakpoint/Einzelschritt/Pause, Abschnitt 8.1):
        füllt das Panel „Aufrufstapel“ UND springt im Editor zur
        aktuellen Zeile des obersten Frames - vorher passierte das nur
        bei einer unbehandelten Ausnahme (`_debugger_exceptioninfo_bereit`),
        bei einem normalen Halt blieb der Cursor an seiner alten Stelle
        stehen (beim Durchspielen der Bedienung gefunden)."""
        self._letzter_aufrufstapel = stapel
        self.aufrufstapel_liste.clear()
        for frame in stapel:
            quelle = frame.get("source", {}).get("path", "")
            name = Path(quelle).name if quelle else "?"
            self.aufrufstapel_liste.addItem(f"{name}, Zeile {frame['line']}, in {frame['name']}")
        if stapel and self.debug_sitzung is not None:
            self.debug_sitzung.bereiche_lesen(stapel[0]["id"])
            self._zu_frame_springen(stapel[0])

    def _bei_aufrufstapel_klick(self, eintrag: QListWidgetItem) -> None:
        index = self.aufrufstapel_liste.row(eintrag)
        if 0 <= index < len(self._letzter_aufrufstapel):
            self._zu_frame_springen(self._letzter_aufrufstapel[index])

    def _zu_frame_springen(self, frame: dict) -> None:
        """Öffnet die Quelldatei eines DAP-Stapelrahmens (`aufrufstapel_
        lesen()`) und springt zur angegebenen Zeile."""
        quelle = frame.get("source", {}).get("path", "")
        if not quelle:
            return
        pfad = Path(quelle)
        if not pfad.exists():
            return
        editor = self.datei_oeffnen(pfad)
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        cursor.movePosition(
            cursor.MoveOperation.Down, cursor.MoveMode.MoveAnchor, frame["line"] - 1
        )
        editor.setTextCursor(cursor)
        editor.ensureCursorVisible()

    def _debugger_bereiche_bereit(self, bereiche: list[dict]) -> None:
        if not bereiche or self.debug_sitzung is None:
            return
        lokale = next((b for b in bereiche if b["name"] == "Locals"), bereiche[0])
        self.debug_sitzung.variablen_lesen(lokale["variablesReference"])

    def _debugger_variablen_bereit(self, variablen: list[dict]) -> None:
        self.variablen_baum.clear()
        for variable in variablen:
            QTreeWidgetItem(self.variablen_baum, [variable["name"], str(variable.get("value"))])
        # Beim Bildschirmfoto gefunden: das Programm stand am
        # Breakpoint, die Variablen waren geladen - sichtbar blieb aber
        # das Panel „Meldungen“. „Als Tabelle anzeigen“ (und überhaupt
        # der Blick auf die Variablen) war nur nach einem
        # Reiterwechsel von Hand erreichbar. Nach einer unbehandelten
        # Ausnahme behält „Meldungen“ den Vorrang, dort steht die
        # Fehlermeldung aus dem Fehlerkatalog.
        if variablen and self._letzter_haltegrund != "exception":
            self.panels.setCurrentWidget(self.variablen_baum)

    # -- „Als Tabelle anzeigen“ (Abschnitt 11.6) -----------------------------

    def _variablen_menue_zeigen(self, punkt) -> None:
        """Kontextmenü im Panel „Variablen“: „Als Tabelle anzeigen“ für
        DataFrames, Listen und Dictionaries (Abschnitt 11.6)."""
        eintrag = self.variablen_baum.itemAt(punkt)
        if eintrag is None:
            return
        menue = QMenu(self.variablen_baum)
        aktion = menue.addAction("Als Tabelle anzeigen")
        aktion.triggered.connect(lambda: self.variable_als_tabelle_zeigen(eintrag.text(0)))
        menue.exec(self.variablen_baum.viewport().mapToGlobal(punkt))

    def variable_als_tabelle_zeigen(self, name: str) -> None:
        """Lässt `name` im angehaltenen Schülerprogramm auswerten und
        zeigt das Ergebnis als Tabelle (Abschnitt 11.6). Die Antwort
        kommt asynchron über das Signal `ausgewertet` in
        `_debugger_tabelle_bereit()`."""
        if self.debug_sitzung is None or not self._letzter_aufrufstapel:
            self.statusBar().showMessage("Kein angehaltenes Programm - keine Tabelle möglich.")
            return
        try:
            # `debugpy` blendet im Variablen-Panel Sammelzeilen wie
            # „special variables“ ein. Beim Bildschirmfoto gesehen: ein
            # Doppelklick darauf schickte diesen Text als Ausdruck an den
            # Debugger - Syntaxfehler im Panel „Meldungen“ statt einer
            # verständlichen Antwort.
            compile(name, "<variable>", "eval")
        except SyntaxError:
            self.statusBar().showMessage(f"{name!r} ist keine Variable, die sich auswerten lässt.")
            return
        self._tabellen_variable = name
        self.debug_sitzung.auswerten(
            tabellen_ausdruck(name), self._letzter_aufrufstapel[0]["id"]
        )

    def _debugger_tabelle_bereit(self, antwort: dict) -> None:
        """Antwort auf `variable_als_tabelle_zeigen()` (DAP `evaluate`).
        Andere Auswertungen (überwachte Ausdrücke) gehen hier nicht
        verloren: ohne offene Tabellen-Anfrage tut die Methode nichts."""
        name = self._tabellen_variable
        self._tabellen_variable = None
        if name is None:
            return
        try:
            tabelle = tabelle_aus_antwort(str(antwort.get("result", "")))
        except TabellenFehler as fehler:
            self.statusBar().showMessage(str(fehler))
            return
        fenster = TabellenAnsicht(name, tabelle, self)
        self.letzte_tabellen_ansicht = fenster
        fenster.show()

    def _debugger_pausieren_aktion(self) -> None:
        if self.debug_sitzung is not None and self._aktueller_thread_id is not None:
            self.debug_sitzung.pausieren(self._aktueller_thread_id)

    def _debugger_fortsetzen_aktion(self) -> None:
        if self.debug_sitzung is not None and self._aktueller_thread_id is not None:
            self.debug_sitzung.fortsetzen(self._aktueller_thread_id)

    def _debugger_stoppen_aktion(self) -> None:
        if self.debug_sitzung is not None:
            self.debug_sitzung.beenden()
            self.debug_sitzung = None
            self._aktueller_thread_id = None
            self.statusBar().showMessage("Debugger gestoppt")

    def _debugger_einzelschritt_aktion(self) -> None:
        if self.debug_sitzung is not None and self._aktueller_thread_id is not None:
            self.debug_sitzung.einzelschritt(self._aktueller_thread_id)

    def _debugger_prozedurschritt_aktion(self) -> None:
        if self.debug_sitzung is not None and self._aktueller_thread_id is not None:
            self.debug_sitzung.prozedurschritt(self._aktueller_thread_id)

    def _debugger_ruecksprung_aktion(self) -> None:
        if self.debug_sitzung is not None and self._aktueller_thread_id is not None:
            self.debug_sitzung.bis_ruecksprung(self._aktueller_thread_id)
