"""HauptFenster: Grundgerüst des IDE-Hauptfensters.

Siehe README.md, Abschnitt 7.1, 7.4, 7.5. Menüleiste mit den
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
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import QSettings, QSize, Qt, QTimer
from PySide6.QtGui import QActionGroup, QCloseEvent, QColor, QFont, QTextCursor
from PySide6.QtWidgets import (
    QDialog,
    QDockWidget,
    QFileDialog,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QScrollArea,
    QStackedWidget,
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
from ide.debugger.haltegruende import haltegrund_deutsch
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
from ide.papierkorb import in_den_papierkorb, papierkorb_verfuegbar
from ide.pfade import daten_ordner
from ide.project import Projekt, projekt_erzeugen
from ide.project.neu_dialog import NeuesProjektDialog
from ide.run import projekt_pruefen, projekt_starten
from ide.run.pruefung import RuffFund
from ide.schema import schema_fehler
from ide.shell.explorer import PFAD_ROLLE, ProjektExplorer
from ide.shell.hintergrund import AusgabeLeser, Hintergrundarbeit
from ide.shell.quelltexteditor import SCHRIFTART_OPTIONEN, QuelltextEditor
from ide.shell.schnellauswahl import SchnellAuswahl
from ide.shell.startbild import Startbild, beispiel_kopieren, zuletzt_merken
from ide.shell.suchen_dialog import SuchenErsetzenDialog
from ide.shell.tastenkuerzel import als_markdown as tastenkuerzel_als_markdown
from ide.shell.theme import ide_qss_erzeugen
from ide.testrunner import Testergebnis, ergebnisse_als_html, tests_ausfuehren
from ide.viewers import (
    MARKDOWN_ENDUNGEN,
    BildVorschau,
    CsvAnsicht,
    HilfeAnsicht,
    HtmlVorschau,
    MarkdownAnsicht,
    TabellenAnsicht,
    ueberschrift_lesen,
)
from pcl.form import Form
from pcl.pruefungsmodus import laeuft as pruefungsmodus_laeuft
from pcl.pruefungsmodus import restzeit_text
from pcl.pruefungsmodus import starten as pruefungsmodus_starten
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

#: Wie oft nachgesehen wird, ob das gestartete Programm inzwischen zu
#: Ende ist. Eine halbe Sekunde reicht: das Ergebnis steht danach im
#: Panel „Ausgabe“, niemand wartet darauf mit der Stoppuhr.
_LAUFZEIT_TAKT_MS = 500

#: Kurzhinweise zu den Reitern unten und zu den Docks (M11, Abschnitt 4).
#: „Aufrufstapel“ oder „Objektinspektor“ sagen einem Anfänger noch
#: nichts – und ein Fenster, dessen Zweck man raten muss, wird nicht
#: benutzt.
PANEL_HINWEISE = {
    "Meldungen": "Fehler und Hinweise aus der Prüfung vor dem Start",
    "Ausgabe": "Was das laufende Programm ausgibt (print) und was man ihm eintippt",
    "Variablen": "Die Werte, während das Programm an einem Haltepunkt steht",
    "Aufrufstapel": "Welche Methode gerade welche aufgerufen hat – von unten nach oben",
    "Tests": "Ergebnisse der Test-Units des Projekts",
}

DOCK_HINWEISE = {
    "Projekt-Explorer": "Die Formulare, Units und Diagramme des geöffneten Projekts",
    "Objektinspektor": "Eigenschaften und Ereignisse der im Designer gewählten Komponente",
    "Komponentenpalette": "Bausteine für das Formular – anklicken, dann auf das Formular klicken",
    "Datenbank": "SQLite-Datei öffnen, Abfragen und Import/Export",
    "Panels": "Meldungen, Ausgabe, Variablen, Aufrufstapel und Tests",
}

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


def _aufzaehlung(namen: list[str]) -> str:
    """„a“, „a und b“, „a, b und c“ – für Meldungen an Lernende.

    Eine Liste im Stil `['u_ampel.pfm', 'u_ampel_design.py']` roh in
    einen Satz zu setzen, liest sich wie eine Fehlermeldung; so liest es
    sich wie ein Satz.
    """
    if not namen:
        return ""
    zitiert = [f"„{name}“" for name in namen]
    if len(zitiert) == 1:
        return zitiert[0]
    return ", ".join(zitiert[:-1]) + f" und {zitiert[-1]}"

#: Zeilenumbruch für mehrzeilige Tooltips.
_UMBRUCH = chr(10)

#: Was am Panel „Meldungen“ ausser den Textzeilen Höhe braucht:
#: Docktitel, Reiterleiste, Rahmen.
_PANEL_RAHMEN = 90

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
def neue_unit_vorlage(name: str) -> str:
    """Das Gerüst, mit dem eine neue Unit entsteht.

 Bis M12 legte „Neue Unit“ eine völlig leere Datei an, und vor einer
 leeren Datei weiß niemand, wohin was gehört (Gemeldet: „es muss eine
 konkrete Abfolge geben und eine Struktur“). Drei Dinge stehen deshalb
 von Anfang an darin: wofür die Unit da ist, wo die Importe hingehören
 und wie andere Units an ihren Inhalt kommen.
 """
    return f'''\
"""{name} – wofür ist diese Unit da?

Andere Units holen sich, was hier steht, mit:
    from {name} import MeineKlasse
"""

# Importe stehen hier, oberhalb des eigenen Codes. Zum Beispiel:
# from u_ampel import Ampel


# Ab hier der eigene Code: eine Klasse oder ein paar Funktionen.
'''


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
        # Gemeldet: die obere Leiste sollte
        # insgesamt kompakter sein.
        self.werkzeugleiste.setIconSize(QSize(18, 18))

        self.editor_tabs = QTabWidget()
        self.editor_tabs.setTabsClosable(True)
        self.editor_tabs.setMovable(True)

        # Startbild statt leerer Fläche (M11, Abschnitt 4): solange
        # nichts offen ist, steht hier, was man tun kann. Ein Stapel
        # statt eines eigenen Tabs, damit `editor_tabs` derselbe bleibt
        # und kein Test und kein Aufrufer eine Sonderzählung braucht.
        self.startbild = Startbild(self._design_einstellungen)
        self.startbild.neues_projekt_gewuenscht.connect(self._neues_projekt_dialog)
        self.startbild.projekt_oeffnen_gewuenscht.connect(self._projekt_oeffnen_dialog)
        self.startbild.erste_schritte_gewuenscht.connect(self._erste_schritte_aktion)
        self.startbild.projekt_gewaehlt.connect(self.projekt_oeffnen_gemeldet)
        self.startbild.beispiel_gewaehlt.connect(self.beispiel_oeffnen)

        self.mitte = QStackedWidget()
        self.mitte.addWidget(self.startbild)
        self.mitte.addWidget(self.editor_tabs)
        self.setCentralWidget(self.mitte)
        self.editor_tabs.currentChanged.connect(self._startbild_umschalten)

        self.explorer = ProjektExplorer()
        # `itemActivated` statt `itemDoubleClicked`: Qt meldet damit den
        # Doppelklick und die Eingabetaste. Mit der Maus allein zu
        # arbeiten ist eine Annahme, keine Selbstverständlichkeit - und
        # wer den Explorer mit Tab erreicht und mit den Pfeiltasten
        # durchgeht, kam bis dahin nicht weiter (M11, Abschnitt 4).
        self.explorer.itemActivated.connect(self._bei_explorer_doppelklick)
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
        # Über *alle* Reiter, nicht über zwei namentlich genannte: sonst
        # bliebe ein später ergänzter Reiter stumm - seine Kacheln wären
        # zu sehen, ließen sich aber nicht aufs Formular legen (M15).
        for liste in self.palette.listen:
            liste.itemActivated.connect(self._bei_palette_doppelklick)
            liste.itemClicked.connect(self._bei_palette_klick)
        self.palette_dock = self._dock_erzeugen(
            "Komponentenpalette", Qt.DockWidgetArea.TopDockWidgetArea, inhalt=self.palette
        )

        self.datenbank_panel = DatenbankPanel()
        self.datenbank_dock = self._dock_erzeugen(
            "Datenbank", Qt.DockWidgetArea.BottomDockWidgetArea, inhalt=self.datenbank_panel
        )

        self.projekt: Projekt | None = None
        #: Der Ladebalken in der untersten Zeile. Entsteht erst beim
        #: ersten langen Vorgang (siehe `_fortschritt_zeigen`).
        self._fortschritt_balken: QProgressBar | None = None
        self.laufender_prozess = None
        #: Sammelt die Ausgabe eines GUI-Programms ein. Ohne
        #: Konsolenfenster gibt es keinen anderen Ort dafür.
        self._ausgabe_leser: AusgabeLeser | None = None
        #: Der eine lange Vorgang, der gerade nebenher läuft. Genau
        #: einer auf einmal: zwei gleichzeitige Exporte schrieben in
        #: dieselbe Exe, zwei `pip install` in dieselbe Umgebung.
        self._hintergrundarbeit: Hintergrundarbeit | None = None
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
        #: Funde der letzten Vorstart-Prüfung, damit ein später
        #: geöffneter Tab seine Wellenlinien auch bekommt (M11, 2.3).
        self._letzte_funde: list[RuffFund] = []
        self.meldungen_liste = QListWidget()
        self.meldungen_liste.itemClicked.connect(self._bei_meldung_geklickt)
        self.meldungen_liste.itemActivated.connect(self._bei_meldung_geklickt)
        self.variablen_baum = QTreeWidget()
        self.variablen_baum.setHeaderLabels(["Eigenschaft", "Wert"])
        # „Als Tabelle anzeigen“ (Abschnitt 11.6): Rechtsklick oder
        # Doppelklick auf eine Variable im Panel „Variablen“.
        self.variablen_baum.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.variablen_baum.customContextMenuRequested.connect(self._variablen_menue_zeigen)
        self.variablen_baum.itemActivated.connect(
            lambda eintrag, _spalte: self.variable_als_tabelle_zeigen(eintrag.text(0))
        )
        self.aufrufstapel_liste = QListWidget()
        self.aufrufstapel_liste.itemClicked.connect(self._bei_aufrufstapel_klick)
        self.aufrufstapel_liste.itemActivated.connect(self._bei_aufrufstapel_klick)
        self.tests_baum = QTreeWidget()
        self.tests_baum.setHeaderLabels(["Test", "Status", "Dauer (s)"])
        self.tests_baum.itemActivated.connect(self._bei_test_doppelklick)
        # Der Reiter „Ausgabe“ war bis hierher ein leeres graues Feld:
        # angelegt, benannt, nie gefüllt. Das Schülerprogramm läuft in
        # einem eigenen Fenster (Abschnitt 7.8), seine `print`-Zeilen
        # stehen also dort - aber wann es gestartet ist, wann es geendet
        # hat und mit welchem Exitcode, gehört laut Abschnitt 7.8
        # hierher und stand nirgends (M11, Abschnitt 5).
        self.ausgabe_liste = QListWidget()
        self._laufzeit_uhr = QTimer(self)
        self._laufzeit_uhr.setInterval(_LAUFZEIT_TAKT_MS)
        self._laufzeit_uhr.timeout.connect(self._programmende_pruefen)
        self._start_zeitpunkt: float | None = None

        panel_widgets = {
            "Meldungen": self.meldungen_liste,
            "Ausgabe": self.ausgabe_liste,
            "Variablen": self.variablen_baum,
            "Aufrufstapel": self.aufrufstapel_liste,
            "Tests": self.tests_baum,
        }
        for reiter in PANEL_REITER:
            index = self.panels.addTab(panel_widgets.get(reiter, QWidget()), reiter)
            self.panels.setTabToolTip(index, PANEL_HINWEISE.get(reiter, reiter))
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
        # ist die Einrückung die Syntax; wer sie nicht sieht, sucht
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

        # „Ansicht → Vervollständigung“ (M11, Abschnitt 2.2). Wie jede
        # Schreibhilfe abschaltbar - und der Prüfungsmodus wird sie
        # später von hier aus einschränken können.
        self.vervollstaendigung_aktion = self._menues["Ansicht"].addAction(
            "Vervollständigung"
        )
        self.vervollstaendigung_aktion.setCheckable(True)
        self.vervollstaendigung_aktion.setChecked(
            self._design_einstellungen.value(
                "editor/vervollstaendigung", True, type=bool
            )
        )
        self.vervollstaendigung_aktion.toggled.connect(
            self._vervollstaendigung_umschalten
        )

        # „Ansicht → Zeilenumbruch“ (M11, Abschnitt 2.3). Standardmäßig
        # aus: in Python trägt die Einrückung Bedeutung, und eine
        # umgebrochene Zeile sieht aus wie zwei. Wer eine lange Zeile
        # ganz sehen will, schaltet ihn dazu.
        self.zeilenumbruch_aktion = self._menues["Ansicht"].addAction(
            "Zeilenumbruch"
        )
        self.zeilenumbruch_aktion.setCheckable(True)
        self.zeilenumbruch_aktion.setChecked(
            self._design_einstellungen.value(
                "editor/zeilenumbruch", False, type=bool
            )
        )
        self.zeilenumbruch_aktion.toggled.connect(self._zeilenumbruch_umschalten)

        # „Ansicht → Leerzeichen anzeigen“ (M11, Abschnitt 2.1). Aus,
        # weil das Bild sonst unruhig wird. Gebraucht wird es an genau
        # einer Stelle, dort aber dringend: wenn eine kopierte Zeile
        # Tabulatoren mitbringt und Python mit „TabError“ abbricht,
        # ohne dass am Bildschirm irgendetwas anders aussieht.
        self.leerzeichen_aktion = self._menues["Ansicht"].addAction(
            "Leerzeichen anzeigen"
        )
        self.leerzeichen_aktion.setCheckable(True)
        self.leerzeichen_aktion.setChecked(
            self._design_einstellungen.value("editor/leerzeichen", False, type=bool)
        )
        self.leerzeichen_aktion.toggled.connect(self._leerzeichen_umschalten)

        # „Ansicht → Design“ (Gewünscht: „Hast du
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

        # „Ansicht → Schriftart“ (Gewünscht: „soll
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

        # Gemeldet: der Quelltexteditor wirkte zu
        # klein, weil Palette/Datenbank/Panels standardmäßig zu viel
        # Höhe beanspruchten. Qt verteilt neue Docks sonst ungefähr
        # gleichmäßig - hier bewusst zugunsten des Editors (Zentral-
        # Widget) eingeschränkt. Bleibt per Maus frei verschiebbar.
        self.resizeDocks([self.palette_dock], [88], Qt.Orientation.Vertical)
        self.resizeDocks(
            [self.datenbank_dock, self.panels_dock], [200, 200], Qt.Orientation.Vertical
        )

        # Auf einem 1366×768-Schulrechner bleiben nach Taskleiste und
        # Fensterrahmen rund 728 Pixel Höhe. Davon nahm das Dock
        # „Datenbank“ allein 300 - der Designer behielt 251 und schnitt
        # das Formular nach dem ersten Drittel ab; die Panels rechts
        # daneben wurden auf 317 Pixel Breite gequetscht, sodass ihre
        # Reiter nur noch mit Pfeilen erreichbar waren (M11, Abschnitt
        # 4, am Bildschirmfoto gemessen). Eine Datenbank braucht im
        # Unterricht erst, wer bei M6/M7 angekommen ist; die ersten
        # Wochen gehen ohne. Deshalb ist das Dock voreingestellt zu und
        # kommt über „Ansicht → Datenbank“ zurück - danach bleibt es
        # offen, weil die Sichtbarkeit gemerkt wird.
        self.datenbank_dock.hide()

        # Zwei Docks nebeneinander in denselben Bereich legen dürfen -
        # sonst lässt sich die Anordnung nur umsortieren, nicht
        # erweitern. Ohne das kann man etwa Explorer und
        # Objektinspektor nicht untereinander an dieselbe Seite hängen.
        # Gefahrlos, weil „Fenster → Layout zurücksetzen“ jederzeit den
        # Ausgangszustand wiederherstellt.
        self.setDockNestingEnabled(True)

        # „Fenster → Layout zurücksetzen“ (Abschnitt 7.2): merkt sich die
        # ursprüngliche Dock-/Werkzeugleisten-Anordnung, sobald alle
        # Docks platziert sind - VOR dem Wiederherstellen der zuletzt
        # gespeicherten Anordnung unten, damit „Zurücksetzen“ wirklich
        # zum echten Ausgangszustand zurückkehrt statt nur zur zuletzt
        # gespeicherten.
        self._urspruengliches_layout = self.saveState()

        # Gemeldet: ein geschlossenes Dock (z. B.
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
        # Dauerhaft rechts in der Statusleiste, solange eine Prüfung
        # läuft - eine Meldung, die nach drei Sekunden verschwindet,
        # wäre für einen Zustand falsch, der vier Stunden anhält.
        self.pruefungsanzeige = QLabel()
        self.pruefungsanzeige.setStyleSheet("padding: 0 8px; font-weight: bold;")
        self.statusBar().addPermanentWidget(self.pruefungsanzeige)
        self._statusleiste_pruefung_aktualisieren()

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
        # 7.3, Gewünscht: „Ich sehe die Buttons nicht
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
                symbol="suchen",
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
                symbol="kommentar",
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
                "hilfe.erste_schritte",
                "Erste Schritte",
                menue="Hilfe",
                callback=self._erste_schritte_aktion,
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "hilfe.tastenkuerzel",
                "Tastenkürzel-Übersicht",
                menue="Hilfe",
                callback=self._tastenkuerzel_aktion,
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
                "projekt.startdatei_zeigen",
                "Startdatei anzeigen",
                menue="Projekt",
                trennlinie_davor=True,
                callback=self._startdatei_zeigen_aktion,
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "projekt.alle_tests_ausfuehren",
                "Alle Tests ausführen",
                menue="Projekt",
                symbol="testlauf",
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
                symbol="export",
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
        self.aktionen.registrieren(
            Aktion(
                "werkzeuge.pruefungsmodus",
                "Prüfungsmodus starten …",
                menue="Werkzeuge",
                callback=self._pruefungsmodus_aktion,
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
                "werkzeuge.formular_importieren",
                "Formular importieren (.lfm) …",
                menue="Werkzeuge",
                callback=self._formular_importieren_aktion,
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
                symbol="einzelschritt",
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

        # „Ansicht → Formular und Code wechseln“ (Abschnitt 7.9). Stand
        # seit M2 als Vermerk im Explorer („folgt später“) und ist der
        # Handgriff, der beim Bauen einer Oberfläche am häufigsten
        # gebraucht wird.
        #
        # Hier auf Umschalt+F12, nicht auf F12. Das gehört im Editor
        # seit M11 zu „Zur Definition springen“, wie in VS Code - und
        # ein Tastenkürzel, das je nach Reiter etwas anderes tut, ist
        # schlimmer als eins, das man einmal neu lernt.
        #
        # Als richtige `Aktion` registriert, aber von Hand ins Menü
        # gehängt: nur als Aktion steht sie in der
        # Tastenkürzel-Übersicht und in der Befehlspalette - ein
        # Kürzel, das nirgends nachzuschlagen ist, findet niemand. Und
        # nur von Hand steht sie oben im Ansicht-Menü statt hinter
        # den Untermenüs „Design“ und „Schriftart“.
        self.aktionen.registrieren(
            Aktion(
                "ansicht.formular_code",
                "Formular und Code wechseln",
                tastenkuerzel="Shift+F12",
                callback=self._formular_code_umschalten,
            )
        )
        self.formular_code_aktion = self.aktionen["ansicht.formular_code"].qaction
        ansicht = self._menues["Ansicht"]
        ansicht.insertAction(ansicht.actions()[0], self.formular_code_aktion)
        ansicht.insertSeparator(ansicht.actions()[1])

    def _datei_oeffnen_dialog(self) -> None:
        pfad, _ = QFileDialog.getOpenFileName(self, "Öffnen")
        if pfad:
            self.oeffnen(Path(pfad))

    def _projekt_oeffnen_dialog(self) -> None:
        pfad, _ = QFileDialog.getOpenFileName(
            self, "Projekt öffnen", filter="Natter-Projekte (*.natter)"
        )
        if pfad:
            self.projekt_oeffnen_gemeldet(Path(pfad))

    def _neues_projekt_dialog(self) -> None:
        """„Projekt → Neues Projekt …“ (Abschnitt 7.2): fragt Vorlage,
        Name und Zielordner ab und legt das Projekt über
        `projekt_erzeugen()` (seit M2) tatsächlich an."""
        dialog = NeuesProjektDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        werte = dialog.werte()
        if werte is None:
            self.statusBar().showMessage(
                "Name und Ordner werden benötigt - beide Felder im Dialog ausfüllen."
            )
            return
        vorlage, projektordner, name = werte
        try:
            projekt = projekt_erzeugen(vorlage, projektordner, name)
        except (ValueError, FileExistsError) as fehler:
            self.statusBar().showMessage(
                f"Projekt konnte nicht angelegt werden: {fehler}. Einen anderen Ordner wählen, "
                f"in dem Schreibrechte bestehen."
            )
            return
        self.projekt = projekt
        self.explorer.projekt_anzeigen(projekt)
        self._projekt_startdateien_oeffnen(projekt)
        self.statusBar().showMessage(f"Projekt {projekt.name} angelegt")

    def _projekt_startdateien_oeffnen(self, projekt: Projekt) -> None:
        """Öffnet nach dem Anlegen, womit man anfängt: das Formular
 und die Unit dazu.

 Ein frisch angelegtes GUI-Projekt zeigte bis dahin gar
 nichts an - man landete in einem leeren Fenster und musste im
 Explorer erst suchen, wo das Programm hingehört. Danach ging
 über einen Doppelklick nur der Designer auf; die Datei, in die
 der Code kommt, blieb unsichtbar (Gemeldet: „wenn ich ein
 neues Projekt erstelle muss auch die u_main.py für den code
 angezeigt werden nicht nur der designer“).

 Vorn liegt am Ende der Designer: bei einem GUI-Projekt legt
 man zuerst die Oberfläche an, und die Unit steht als zweiter
 Reiter daneben. Ein Konsolenprojekt hat kein Formular - dort
 bleibt es bei der einen Datei.
 """
        unit = next(
            (pfad for pfad in projekt.units() if pfad.stem == projekt.haupt_unit), None
        )
        if unit is not None and unit.exists():
            self.datei_oeffnen(unit)

        formulare = projekt.formulare()
        if formulare:
            self.designer_oeffnen(formulare[0])

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

    def unit_erzeugen(self, name: str | None = None, *, inhalt: str | None = None) -> Path:
        """„Neue Unit“ (Abschnitt 7.2, 7.4): legt `u_neu<n>.py` an (oder
        mit gegebenem `name`), fügt sie dem Projekt-Explorer hinzu und
        öffnet sie im Editor.

        Ohne `inhalt` entsteht das Gerüst aus `neue_unit_vorlage()` -
        bis M12 war es eine leere Datei."""
        if self.projekt is None:
            raise RuntimeError("Kein Projekt offen.")

        if name is None:
            name = self._naechster_unit_name()

        pfad = self.projekt.ordner / f"{name}.py"
        if pfad.exists():
            raise FileExistsError(f"{pfad} existiert bereits.")

        pfad.write_text(
            neue_unit_vorlage(name) if inhalt is None else inhalt, encoding="utf-8"
        )
        self.explorer.projekt_anzeigen(self.projekt)
        self.datei_oeffnen(pfad)
        return pfad

    def _startdatei_zeigen_aktion(self) -> None:
        """„Projekt → Startdatei anzeigen“ – der einzige Weg zur
        `main.py`.

        Sie steht bewusst nicht im Projekt-Explorer: Natter schreibt sie
        beim Anlegen des Projekts, danach ändert sie niemand mehr. Eine
        Datei, die man nicht bearbeiten soll, gehört nicht zwischen die,
        an denen man arbeitet (M12). Wer trotzdem hineinsehen will, kommt
        über diesen Eintrag hin."""
        if self.projekt is None:
            self.statusBar().showMessage(
                "Kein Projekt offen. Zuerst über „Projekt → Öffnen …“ eines laden oder ein "
                "neues anlegen."
            )
            return
        self.oeffnen(self.projekt.haupt_datei)
        self.statusBar().showMessage(
            f"{self.projekt.haupt_datei.name} startet das Programm. Der eigene Code "
            f"gehört in die Units daneben – hier ist nichts zu ändern."
        )

    def _naechster_unit_name(self) -> str:
        # Gegen *alle* Dateien geprüft, nicht nur gegen die sichtbaren:
        # sonst könnte ein neuer Name die Startdatei oder eine erzeugte
        # Design-Datei überschreiben (M12).
        vorhandene = {p.stem for p in self.projekt.alle_python_dateien()}
        zaehler = 1
        while f"u_neu{zaehler}" in vorhandene:
            zaehler += 1
        return f"u_neu{zaehler}"

    def _neue_test_unit_aktion(self) -> None:
        """„Neue Test-Unit“ (Abschnitt 8.6): legt `test_neu<n>.py` mit
        einer `unittest`-Grundstruktur an."""
        if self.projekt is None:
            self.statusBar().showMessage(
                "Kein Projekt offen. Zuerst über „Projekt → Öffnen …“ eines laden oder ein "
                "neues anlegen."
            )
            return
        vorhandene = {p.stem for p in self.projekt.alle_python_dateien()}
        zaehler = 1
        while f"test_neu{zaehler}" in vorhandene:
            zaehler += 1
        name = f"test_neu{zaehler}"
        self.unit_erzeugen(name, inhalt=_TEST_UNIT_VORLAGE)

    # -- Test-Explorer (Abschnitt 8.6) ---------------------------------------

    def _alle_tests_ausfuehren_aktion(self) -> None:
        if self.projekt is None:
            self.statusBar().showMessage(
                "Kein Projekt offen. Zuerst über „Projekt → Öffnen …“ eines laden oder ein "
                "neues anlegen."
            )
            return
        if not self._hintergrund_frei("Der Testlauf"):
            return
        ordner = self.projekt.ordner
        self.statusBar().showMessage("Tests laufen - die IDE bleibt bedienbar.")
        self._hintergrund_starten(
            lambda _melden: tests_ausfuehren(ordner),
            self._tests_fertig,
            "Testlauf fehlgeschlagen",
        )

    def _tests_fertig(self, ergebnisse: object) -> None:
        """Die Auswertung des Testlaufs, zurück im Faden der Oberfläche."""
        self._letzte_testergebnisse = ergebnisse
        self._tests_baum_befuellen(ergebnisse)
        anzahl_fehlgeschlagen = sum(1 for e in ergebnisse if e.status != "bestanden")
        self.statusBar().showMessage(
            f"{len(ergebnisse)} {'Test' if len(ergebnisse) == 1 else 'Tests'} gelaufen, "
            f"{anzahl_fehlgeschlagen} nicht bestanden. Ein Klick auf einen Eintrag im "
            f"Test-Explorer zeigt, woran es lag."
        )
        self.panels.setCurrentWidget(self.tests_baum)

    def _testergebnisse_exportieren_aktion(self) -> None:
        """„Testergebnisse als HTML exportieren“ (Abschnitt 8.6) – nutzt
        die Ergebnisse des letzten „Alle Tests ausführen“-Laufs."""
        if not self._letzte_testergebnisse:
            self.statusBar().showMessage(
                "Noch keine Testergebnisse zum Exportieren - zuerst „Projekt → Tests "
                "ausführen“ starten."
            )
            return
        pfad, _ = QFileDialog.getSaveFileName(
            self, "Testergebnisse exportieren", filter="HTML-Datei (*.html)"
        )
        if not pfad:
            return
        titel = self.projekt.name if self.projekt is not None else "Testprotokoll"
        html = ergebnisse_als_html(self._letzte_testergebnisse, titel=titel)
        if not self.datei_schreiben_gemeldet(Path(pfad), html):
            return
        self.statusBar().showMessage(f"Testprotokoll gespeichert: {pfad}")

    def _als_exe_exportieren_aktion(self) -> None:
        """„Projekt → Als Exe exportieren …“ (Abschnitt 16;
        M8 Schritt 4, M14): baut das Projekt mit PyInstaller zu einer
        einzigen Exe.

        Läuft nebenher, nicht blockierend. Bis dahin stand die IDE
        währenddessen still: ein Export dauert für ein Schulprojekt eine
        halbe bis eine Minute, und in dieser Zeit nahm das Fenster keine
        Klicks an. Ein Ladebalken, der sich über `processEvents()` noch
        bewegt, ändert daran nichts - bedienen ließ sich das Programm
        trotzdem nicht.
        """
        if self.projekt is None:
            self.statusBar().showMessage(
                "Kein Projekt offen. Zuerst über „Projekt → Öffnen …“ eines laden oder ein "
                "neues anlegen."
            )
            return
        if not self._hintergrund_frei("Der Export"):
            return

        projekt = self.projekt
        self.statusBar().showMessage("Exe wird erstellt - die IDE bleibt bedienbar.")
        self._fortschritt_zeigen(0)
        self._hintergrund_starten(
            lambda melden: exe_exportieren(projekt, fortschritt=melden),
            self._export_fertig,
            "Exe-Export fehlgeschlagen",
        )

    def _export_fertig(self, ergebnis: object) -> None:
        """Die Nachbereitung des Exports, zurück im Faden der Oberfläche."""
        self._fortschritt_verbergen()
        if not ergebnis.erfolgreich:
            self.meldungen_liste.clear()
            self.meldungen_liste.addItems(
                ["[Exe-Export fehlgeschlagen]", *ergebnis.protokoll.splitlines()[-40:]]
            )
            self.panels.setCurrentWidget(self.meldungen_liste)
            self.statusBar().showMessage(
                "Exe-Export fehlgeschlagen. Die Ursache steht unten im Panel „Meldungen“."
            )
            return

        self.statusBar().showMessage(f"Exe erstellt: {ergebnis.ausgabe_pfad}")
        if sys.platform == "win32":
            os.startfile(ergebnis.ausgabe_pfad.parent)

    # -- Arbeit, die nebenher läuft -----------------------------------

    def _hintergrund_frei(self, was: str) -> bool:
        """Ob gerade kein anderer langer Vorgang läuft.

        Genau einer auf einmal, und zwar aus einem handfesten Grund:
        zwei gleichzeitige Exporte schrieben in dieselbe Exe, zwei
        `pip install` in dieselbe Umgebung. Wer den zweiten Vorgang
        anstößt, bekommt gesagt, worauf zu warten ist - statt dass
        stillschweigend nichts passiert.
        """
        laeuft = self._hintergrundarbeit
        if laeuft is not None and laeuft.isRunning():
            self.statusBar().showMessage(
                f"{was} wartet: es läuft schon ein Vorgang. Sobald er fertig ist, "
                f"geht es erneut."
            )
            return False
        return True

    def _hintergrund_starten(
        self,
        arbeit: Callable[[Callable[[int, str], None]], Any],
        fertig: Callable[[Any], None],
        fehlertext: str,
    ) -> Hintergrundarbeit:
        """Lässt `arbeit` in einem eigenen Faden laufen.

        Das Ergebnis kommt über ein Signal zurück und damit wieder im
        Faden der Oberfläche an - nur dort darf an Widgets geschrieben
        werden.
        """
        lauf = Hintergrundarbeit(arbeit, self)
        lauf.fortschritt.connect(self._export_fortschritt)
        lauf.fertig.connect(fertig)
        lauf.fehlgeschlagen.connect(
            lambda meldung: self._hintergrund_fehler(fehlertext, meldung)
        )
        self._hintergrundarbeit = lauf
        lauf.start()
        return lauf

    def _hintergrund_fehler(self, was: str, meldung: str) -> None:
        """Eine Ausnahme aus einem Nebenfaden.

        Sie darf die IDE nicht mitreißen: ein fehlgeschlagener Export
        ist ein Fall für die Statuszeile und das Panel „Meldungen“,
        nicht für einen Absturz.
        """
        self._fortschritt_verbergen()
        self.meldungen_liste.clear()
        self.meldungen_liste.addItem(f"[{was}] {meldung}")
        self.panels.setCurrentWidget(self.meldungen_liste)
        self.statusBar().showMessage(
            f"{was}: {meldung} Mehr steht unten im Panel „Meldungen“."
        )

    # -- Ladebalken in der Statuszeile ---------------------------------

    def _fortschritt_zeigen(self, prozent: int) -> None:
        """Blendet den Ladebalken rechts in der untersten Zeile ein.

        Er wird erst hier erzeugt und nicht beim Aufbau des Fensters:
        eine Statuszeile, in der dauerhaft ein leerer Balken steht,
        sieht nach einem hängenden Programm aus.
        """
        if self._fortschritt_balken is None:
            self._fortschritt_balken = QProgressBar()
            self._fortschritt_balken.setMaximumWidth(220)
            self._fortschritt_balken.setRange(0, 100)
            self.statusBar().addPermanentWidget(self._fortschritt_balken)
        self._fortschritt_balken.setValue(prozent)
        self._fortschritt_balken.show()

    def _fortschritt_verbergen(self) -> None:
        if self._fortschritt_balken is not None:
            self._fortschritt_balken.hide()

    def _export_fortschritt(self, prozent: int, text: str) -> None:
        """Der Fortschritt eines nebenher laufenden Vorgangs.

        Kommt über ein Signal aus `Hintergrundarbeit` und damit im
        Faden der Oberfläche an - `processEvents()` braucht es nicht
        mehr, und die Oberfläche antwortet die ganze Zeit von selbst.
        """
        self._fortschritt_zeigen(prozent)
        if text:
            self.statusBar().showMessage(text)

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
        # Deutsch auch in einer Zahlenspalte: eine Sekundenangabe mit
        # Punkt sticht in einer sonst durchgehend deutschen Oberfläche
        # hervor (Gewünscht: „Alles in Deutschem Format“).
        eintrag.setText(2, f"{ergebnis.dauer:.3f}".replace(".", ","))
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
            self.statusBar().showMessage(
                "Kein Projekt offen. Zuerst über „Projekt → Öffnen …“ eines laden oder ein "
                "neues anlegen."
            )
            return
        self.unit_erzeugen()

    def _unit_umbenennen(self, pfad: Path) -> None:
        """„⋮ → Umbenennen …“ im Projekt-Explorer: benennt die
        Datei auf der Platte um und hält
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
            self.statusBar().showMessage(
                f"„{neuer_name}“ gibt es schon - bitte einen anderen Namen wählen."
            )
            return

        try:
            pfad.rename(ziel)
        except OSError as fehler:
            self.statusBar().showMessage(
                f"Umbenennen fehlgeschlagen: {fehler}. Ist die Datei gerade in einem anderen "
                f"Programm geöffnet?"
            )
            return

        self._offenen_tab_pfad_aktualisieren(pfad, ziel)
        if self.projekt is not None:
            self.explorer.projekt_anzeigen(self.projekt)
        self.statusBar().showMessage(f"„{pfad.name}“ zu „{neuer_name}“ umbenannt.")

    def _unit_loeschen(self, pfad: Path) -> None:
        """„⋮ → Löschen …“ im Projekt-Explorer: fragt nach, schließt
        einen ggf. offenen Editor-Tab und legt die Datei in den
        Papierkorb.

        Der Papierkorb ist hier das „Rückgängig“ (M11, Abschnitt 4):
        vorher wurde endgültig gelöscht, und die Nachfrage sagte das
        auch ehrlich. In einem Klassenraum ist aber genau der Fall
        häufig, dass jemand die falsche Unit erwischt – und die Arbeit
        einer Doppelstunde ist nicht wiederzubekommen."""
        # Zu einer Unit mit Formular gehören drei Dateien, von denen
        # der Explorer nur zwei zeigt. Sie müssen zusammen gehen, sonst
        # bleibt erzeugter Code zu einem Formular liegen, das es nicht
        # mehr gibt (Grundsatz: der Rest wird im
        # Hintergrund nachgeführt, auch beim Löschen).
        betroffen = (
            self.projekt.zusammengehoerige_dateien(pfad) if self.projekt is not None else [pfad]
        )
        weitere = [p for p in betroffen if p != pfad]

        mit_papierkorb = papierkorb_verfuegbar()
        folge = (
            "Die Dateien landen im Papierkorb und lassen sich von dort zurückholen."
            if mit_papierkorb
            else "Die Dateien landen nicht im Papierkorb und lassen sich danach nicht "
            "zurückholen."
        )
        dazu = (
            f" Dazu gehört {_aufzaehlung([p.name for p in weitere])}." if weitere else ""
        )
        antwort = QMessageBox.question(
            self,
            "Unit löschen",
            f"„{pfad.name}“ wirklich löschen?{dazu} {folge}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if antwort != QMessageBox.StandardButton.Yes:
            return

        offene = {str(p) for p in betroffen}
        for index in reversed(range(self.editor_tabs.count())):
            editor = self.editor_tabs.widget(index)
            if (
                isinstance(editor, QPlainTextEdit)
                and editor.property(_PFAD_EIGENSCHAFT) in offene
            ):
                self.editor_tabs.removeTab(index)

        for datei in betroffen:
            try:
                if not in_den_papierkorb(datei):
                    datei.unlink()
            except OSError as fehler:
                self.statusBar().showMessage(
                    f"Löschen fehlgeschlagen: {fehler}. Ist die Datei gerade in einem anderen "
                    f"Programm geöffnet?"
                )
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
        dock.setToolTip(DOCK_HINWEISE.get(titel, titel))
        dock.setWidget(inhalt if inhalt is not None else QWidget())
        self.addDockWidget(bereich, dock)
        return dock

    def menue(self, titel: str):
        """Liefert das Menü mit diesem Titel (Abschnitt 7.2)."""
        return self._menues[titel]

    def _startbild_umschalten(self, *_werte: object) -> None:
        """Zeigt das Startbild, solange kein Tab offen ist."""
        leer = self.editor_tabs.count() == 0
        self.mitte.setCurrentWidget(self.startbild if leer else self.editor_tabs)

    def hilfe_zeigen(self, titel: str, markdown: str) -> HilfeAnsicht:
        """Öffnet eine Hilfeseite als eigenen Reiter – lesbar gesetzt,
        im Programm.

        Ein zweiter Aufruf mit demselben Titel holt den vorhandenen
        Reiter nach vorn, statt einen zweiten aufzumachen.
        """
        for index in range(self.editor_tabs.count()):
            widget = self.editor_tabs.widget(index)
            if isinstance(widget, HilfeAnsicht) and (
                self.editor_tabs.tabText(index) == titel
            ):
                widget.markdown_setzen(markdown)
                self.editor_tabs.setCurrentIndex(index)
                return widget

        ansicht = HilfeAnsicht()
        ansicht.markdown_setzen(markdown)
        index = self.editor_tabs.addTab(ansicht, titel)
        self.editor_tabs.setCurrentIndex(index)
        return ansicht

    def _hilfedatei_zeigen(self, dateiname: str, titel: str) -> bool:
        """Eine Hilfeseite aus `docs/`. Liefert `False`, wenn es sie
        nicht gibt; die Meldung sagt dann, wo sie liegen müsste."""
        # `daten_ordner` statt eines quellcode-relativen Pfads: in der
        # gebauten Exe liegt `docs/` im Bundle-Ordner, nicht neben dem
        # Quelltext.
        pfad = daten_ordner("docs") / dateiname
        if not pfad.exists():
            self.statusBar().showMessage(
                f"„{titel}“ ist nicht mitgekommen. Die Seite liegt in "
                f"docs/{dateiname}; eine neue Installation bringt sie mit."
            )
            return False
        self.hilfe_zeigen(titel, pfad.read_text(encoding="utf-8"))
        return True

    def _erste_schritte_aktion(self) -> bool:
        """„Erste Schritte“ – vom Startbild und aus dem Menü „Hilfe“.

        Bis M11 öffnete der Eintrag die `.md`-Datei im
        Quelltexteditor: eine Anleitung mit `##` und `*` davor, in
        einem Fenster, das nach Programmieren aussieht und in dem man
        sie versehentlich ändern kann.
        """
        return self._hilfedatei_zeigen("erste_schritte.md", "Erste Schritte")

    def _tastenkuerzel_aktion(self) -> HilfeAnsicht:
        """„Hilfe → Tastenkürzel-Übersicht“ (M11, Abschnitt 4).

        Die Kürzel gab es alle schon – sie standen nur nirgends
        zusammen. Erzeugt wird die Seite aus dem Aktionsregister: eine
        von Hand gepflegte Liste ist nach der dritten neuen Aktion
        falsch, und eine falsche Übersicht ist schlimmer als keine.
        """
        return self.hilfe_zeigen(
            "Tastenkürzel", tastenkuerzel_als_markdown(self.aktionen)
        )

    def beispiel_oeffnen(self, projektdatei: Path) -> Projekt:
        """Öffnet ein mitgeliefertes Beispielprojekt – als Kopie im
        Dokumente-Ordner.

        An Ort und Stelle zu öffnen ginge in einer installierten Natter
        nicht: die Beispiele liegen dann im Programmordner, in den eine
        Schülerin nicht schreiben darf. Und selbst wo es ginge, wäre es
        falsch – das Beispiel soll beim nächsten Mal wieder im
        Ursprungszustand dastehen.
        """
        kopie = beispiel_kopieren(Path(projektdatei))
        projekt = self.projekt_oeffnen(kopie)
        self.statusBar().showMessage(
            f"Beispiel „{projekt.name}“ nach {kopie.parent} kopiert und geöffnet."
        )
        return projekt

    def projekt_oeffnen(self, pfad: Path) -> Projekt:
        """„Projekt öffnen …“ (Abschnitt 7.2): lädt das Projekt und füllt
        den Projekt-Explorer."""
        self.projekt = Projekt.laden(Path(pfad))
        zuletzt_merken(self._design_einstellungen, Path(pfad))
        self.startbild.aufbauen()
        self.explorer.projekt_anzeigen(self.projekt)
        self.statusBar().showMessage(f"Projekt {self.projekt.name} geöffnet")
        return self.projekt

    def projekt_oeffnen_gemeldet(self, pfad: Path) -> Projekt | None:
        """`projekt_oeffnen()` mit Meldung statt Traceback – der Weg für
        alles, was von einem Klick kommt („Projekt → Öffnen …“, ein
        Eintrag unter „Zuletzt geöffnet“).

        Eine `.natter`-Datei kann fehlen, weil der USB-Stick nicht mehr
        steckt, oder beschädigt sein, weil sie jemand in einem Editor
        offen hatte. Beides flog vorher als `FileNotFoundError` bzw.
        `JSONDecodeError` aus einem Qt-Signal heraus (M11, Abschnitt 5).
        """
        try:
            return self.projekt_oeffnen(pfad)
        except FileNotFoundError:
            QMessageBox.warning(
                self,
                "Projekt nicht gefunden",
                f"„{Path(pfad).name}“ liegt nicht (mehr) unter\n{pfad}\n\n"
                "Wurde der Ordner verschoben oder der USB-Stick abgezogen?",
            )
        except (json.JSONDecodeError, schema_fehler(), KeyError) as fehler:
            QMessageBox.warning(
                self,
                "Projekt konnte nicht geöffnet werden",
                f"„{Path(pfad).name}“ ist beschädigt und lässt sich nicht lesen.\n\n"
                f"{fehler}\n\nDie Datei wird von Natter geschrieben und sollte nicht "
                "von Hand bearbeitet werden.",
            )
        except OSError as fehler:
            QMessageBox.warning(
                self,
                "Projekt konnte nicht geöffnet werden",
                f"„{Path(pfad).name}“ lässt sich nicht öffnen: {fehler}",
            )
        return None

    def datei_oeffnen(self, pfad: Path) -> QPlainTextEdit | None:
        """„Öffnen …“ (Abschnitt 7.2): öffnet eine einzelne Datei in
        einem Editor-Tab, unabhängig vom Projekt. Bereits offene Dateien
        werden nur aktiviert statt doppelt geöffnet.

        Liefert `None`, wenn die Datei sich nicht als Text lesen lässt –
        dann steht der Grund in der Statuszeile. Vorher flog der
        `UnicodeDecodeError` bis nach oben durch: bei einer `.exe` oder
        einer alten, nicht in UTF-8 gespeicherten Textdatei war
        Natter einfach weg (M11, Abschnitt 5).

        „Bereits offen“ heißt: in einem Editor offen. Ein Betrachter
        auf dieselbe Datei zählt nicht, sonst täte „Quelltext
        bearbeiten“ in der Markdown-Ansicht nichts – der Pfad stimmte,
        und der vorhandene Reiter käme nur wieder nach vorn."""
        pfad = Path(pfad)
        for index in range(self.editor_tabs.count()):
            editor = self.editor_tabs.widget(index)
            if isinstance(editor, QuelltextEditor) and (
                editor.property(_PFAD_EIGENSCHAFT) == str(pfad)
            ):
                self.editor_tabs.setCurrentIndex(index)
                return editor

        editor = QuelltextEditor(
            thema=theme_aufloesen(self._design_thema), schriftart=self._code_schriftart
        )
        editor.einzugslinien_setzen(self.einzugslinien_aktion.isChecked())
        editor.vervollstaendigung_setzen(
            self.vervollstaendigung_aktion.isChecked()
        )
        editor.zeilenumbruch_setzen(self.zeilenumbruch_aktion.isChecked())
        editor.leerzeichen_setzen(self.leerzeichen_aktion.isChecked())
        editor.definition_gesucht.connect(self._zur_definition_springen)
        try:
            inhalt = pfad.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            self.statusBar().showMessage(
                f"„{pfad.name}“ ist keine Textdatei (oder nicht in UTF-8 gespeichert) und "
                f"lässt sich deshalb nicht im Editor öffnen."
            )
            return None
        except OSError as fehler:
            self.statusBar().showMessage(
                f"„{pfad.name}“ lässt sich nicht öffnen: {fehler}. Ist die Datei gerade in "
                f"einem anderen Programm geöffnet?"
            )
            return None
        editor.setPlainText(inhalt)
        editor.setProperty(_PFAD_EIGENSCHAFT, str(pfad))
        # Ein Tab, der nach der Prüfung aufgeht, zeigt seine Funde
        # trotzdem - sonst müsste man erst neu starten, um sie zu sehen.
        editor.funde_setzen(self._funde_der_datei(str(pfad)))
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
        # Ein gescheitertes Speichern ist der schlimmste Fall von allen:
        # der Text steht noch im Fenster, die Datei auf der Platte ist
        # die alte. Der Tab bleibt deshalb als geändert markiert, wenn
        # es nicht geklappt hat (M11, Abschnitt 5).
        if not self.datei_schreiben_gemeldet(
            pfad, editor.toPlainText(), folge="Der Text steht noch im Editor."
        ):
            return
        editor.document().setModified(False)

    def datei_schreiben_gemeldet(
        self, pfad: Path, inhalt: str, *, folge: str = ""
    ) -> bool:
        """Schreibt `inhalt` nach `pfad` und meldet ein Scheitern als
        Fenster. Liefert, ob es geklappt hat.

        Überall dort benutzt, wo Natter auf Wunsch der Nutzerin etwas
        auf die Platte schreibt. Vorher stand an jeder dieser Stellen
        ein nacktes `write_text()`: ein abgezogener USB-Stick, ein
        schreibgeschützter Ordner oder eine in Word geöffnete Datei
        ergaben einen Traceback, in der gebauten Exe ohne Konsole also
        gar nichts (M11, Abschnitt 5). Bewusst ein Fenster und keine
        Zeile in der Statusleiste: eine nicht geschriebene Datei ist zu
        wichtig, um sie zu übersehen.
        """
        try:
            Path(pfad).write_text(inhalt, encoding="utf-8")
        except OSError as fehler:
            QMessageBox.warning(
                self,
                "Nicht gespeichert",
                f"„{Path(pfad).name}“ konnte nicht gespeichert werden:\n{fehler}\n\n"
                + (f"{folge}\n\n" if folge else "")
                + "Häufige Gründe: der USB-Stick ist abgezogen, die Datei ist "
                "schreibgeschützt oder in einem anderen Programm geöffnet.",
            )
            return False
        return True

    # -- Bearbeiten (Abschnitt 7.2) -------------------------------------------

    def _aktueller_editor(self) -> QPlainTextEdit | None:
        """Der aktive Editor-Tab, falls es einer ist (nicht z. B. ein
        Designer- oder CSV-/Bild-/HTML-Betrachter-Tab)."""
        widget = self.editor_tabs.currentWidget()
        return widget if isinstance(widget, QPlainTextEdit) else None

    def _bearbeiten_rueckgaengig(self) -> None:
        """„Bearbeiten → Rückgängig“ (Strg+Z) – im Editor und im
        Formular-Designer.

        Der Designer hat seinen eigenen Kommandostapel und hörte auf
        Strg+Z, solange die Zeichenfläche den Fokus hatte. Der
        Menüeintrag daneben tat in einem Designer-Tab dagegen gar
        nichts: er suchte einen Texteditor und fand keinen. Zwei Wege
        zur selben Sache, von denen einer stumm bleibt, sind schlimmer
        als einer (M11, Abschnitt 5)."""
        editor = self._aktueller_editor()
        if editor is not None:
            editor.undo()
        elif self._aktueller_canvas is not None:
            self._aktueller_canvas.rueckgaengig()

    def _bearbeiten_wiederholen(self) -> None:
        """„Bearbeiten → Wiederholen“ – siehe `_bearbeiten_rueckgaengig`."""
        editor = self._aktueller_editor()
        if editor is not None:
            editor.redo()
        elif self._aktueller_canvas is not None:
            self._aktueller_canvas.wiederholen()

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
            self.statusBar().showMessage(
                "Kein Editor-Tab aktiv. Zuerst links im Projekt-Explorer eine Quelltextdatei "
                "doppelklicken."
            )
            return
        self._suchen_dialog = SuchenErsetzenDialog(editor, self)
        self._suchen_dialog.show()
        self._suchen_dialog.raise_()
        self._suchen_dialog.activateWindow()

    def _gehe_zu_zeile_aktion(self) -> None:
        editor = self._aktueller_editor()
        if editor is None:
            self.statusBar().showMessage(
                "Kein Editor-Tab aktiv. Zuerst links im Projekt-Explorer eine Quelltextdatei "
                "doppelklicken."
            )
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
        self.objektinspektor.baum.symbole_erneuern(thema)
        self.setWindowIcon(symbol("app", thema))

    def _einzugslinien_umschalten(self, sichtbar: bool) -> None:
        """Schaltet die Einrückungslinien in allen offenen Editor-Tabs
        und merkt sich die Wahl für den nächsten Start."""
        self._design_einstellungen.setValue("editor/einzugslinien", sichtbar)
        for index in range(self.editor_tabs.count()):
            editor = self.editor_tabs.widget(index)
            if isinstance(editor, QuelltextEditor):
                editor.einzugslinien_setzen(sichtbar)

    def _zeilenumbruch_umschalten(self, an: bool) -> None:
        """Schaltet den Zeilenumbruch in allen offenen Editor-Tabs und
        merkt sich die Wahl für den nächsten Start."""
        self._design_einstellungen.setValue("editor/zeilenumbruch", an)
        for index in range(self.editor_tabs.count()):
            editor = self.editor_tabs.widget(index)
            if isinstance(editor, QuelltextEditor):
                editor.zeilenumbruch_setzen(an)

    def _leerzeichen_umschalten(self, sichtbar: bool) -> None:
        """Schaltet Leerzeichen und Tabulatoren in allen offenen
        Editor-Tabs und merkt sich die Wahl für den nächsten Start."""
        self._design_einstellungen.setValue("editor/leerzeichen", sichtbar)
        for index in range(self.editor_tabs.count()):
            editor = self.editor_tabs.widget(index)
            if isinstance(editor, QuelltextEditor):
                editor.leerzeichen_setzen(sichtbar)

    def _zur_definition_springen(self) -> str:
        """F12 im Editor: dorthin, wo der Name unter dem Cursor
        definiert wurde. Gibt die Statusmeldung zurück, damit der Weg
        prüfbar bleibt.

        Drei Fälle, und alle drei sagen etwas: gefunden (Sprung),
        gefunden, aber ausserhalb des Projekts (nur die Auskunft, wo es
        herkommt), nichts gefunden.
        """
        editor = self.editor_tabs.currentWidget()
        if not isinstance(editor, QuelltextEditor):
            return ""
        ordner = self.projekt.ordner if self.projekt is not None else None
        fundstelle = editor.definition_unter_cursor(projekt=ordner)

        if fundstelle is None:
            meldung = (
                "Zu dieser Stelle gibt es keine Definition im Projekt. Steht der "
                "Cursor auf einem Namen – und ist der Name richtig geschrieben?"
            )
        elif fundstelle.fremd:
            # Ein Sprung nach `builtins.pyi` wäre Quelltext in einer
            # Sprache, die im Unterricht nie vorkommt.
            meldung = (
                f"„{fundstelle.name}“ gehört nicht zum Projekt, sondern zu "
                f"{Path(fundstelle.pfad).stem}. Der Quelltext dazu wird nicht "
                f"geöffnet."
            )
        else:
            if fundstelle.pfad is not None:
                editor = self.datei_oeffnen(Path(fundstelle.pfad))
            if editor is None:
                return
            editor.zu_zeile_springen(fundstelle.zeile, fundstelle.spalte)
            wo = (
                Path(fundstelle.pfad).name
                if fundstelle.pfad is not None
                else "dieser Datei"
            )
            meldung = f"„{fundstelle.name}“ steht in {wo}, Zeile {fundstelle.zeile}."

        self.statusBar().showMessage(meldung)
        return meldung

    def _funde_in_editoren_zeigen(self, funde: list[RuffFund]) -> None:
        """Unterringelt die Funde der Vorstart-Prüfung dort, wo sie
        stehen – im Quelltext, mit der Meldung im Tooltip.

        Bis jetzt stand ein Fund nur in der Liste unter dem Editor. Wer
        gerade erst anfängt, schaut aber nicht nach unten, sondern auf
        die Zeile, die er eben getippt hat. Die Liste bleibt trotzdem:
        sie zeigt auch Funde aus Dateien, die gar nicht offen sind.

        Eine leere Liste räumt die Wellenlinien wieder ab – sonst stünde
        nach dem Beheben immer noch der alte Fehler im Text.
        """
        self._letzte_funde = list(funde)
        for index in range(self.editor_tabs.count()):
            editor = self.editor_tabs.widget(index)
            if isinstance(editor, QuelltextEditor):
                editor.funde_setzen(
                    self._funde_der_datei(editor.property(_PFAD_EIGENSCHAFT))
                )

    def _funde_der_datei(self, pfad: str | None) -> dict[int, str]:
        """Die Funde einer Datei, nach Zeile geordnet. Zwei Funde in
        derselben Zeile stehen untereinander, statt dass der zweite den
        ersten verdeckt."""
        zeilen: dict[int, list[str]] = {}
        for fund in self._letzte_funde:
            if pfad and str(fund.datei) == str(pfad):
                # Ohne Dateinamen: welche Datei es ist, sieht man am
                # Reiter, und im Tooltip wäre es nur eine Zeile mehr.
                text = fund.was
                if fund.pruefe:
                    text = f"{text} {fund.pruefe}"
                zeilen.setdefault(fund.zeile, []).append(text)
        return {
            zeile: _UMBRUCH.join(texte) for zeile, texte in zeilen.items()
        }

    def _pruefungsmodus_aktion(self) -> bool:
        """„Werkzeuge → Prüfungsmodus starten …“ (M11, Abschnitt 6).

        Mit Rückfrage, weil er sich vier Stunden lang nicht mehr
        abschalten lässt – und genau das ist sein Sinn. Läuft er schon,
        sagt der Eintrag nur, wie lange noch: ein zweiter Start würde
        die Zeit verlängern, was in einer Klausur niemand will.
        """
        if pruefungsmodus_laeuft():
            self.statusBar().showMessage(
                f"{restzeit_text()}. Er läuft von selbst aus; bis dahin bleiben "
                "Lösungsvorschläge und Quelltexterzeugung gesperrt."
            )
            return False

        antwort = QMessageBox.question(
            self,
            "Prüfungsmodus starten",
            "Für vier Stunden werden keine Lösungsvorschläge angezeigt, und "
            "aus Klassendiagramm und Struktogramm lässt sich kein Quelltext "
            "erzeugen.\n\n"
            "Er lässt sich bis dahin nicht abschalten und läuft danach von "
            "selbst aus. Jetzt starten?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if antwort != QMessageBox.StandardButton.Yes:
            self.statusBar().showMessage("Prüfungsmodus nicht gestartet.")
            return False

        pruefungsmodus_starten()
        self._statusleiste_pruefung_aktualisieren()
        self.statusBar().showMessage(
            f"{restzeit_text()}. Lösungsvorschläge und Quelltexterzeugung sind "
            "bis dahin gesperrt."
        )
        return True

    def _statusleiste_pruefung_aktualisieren(self) -> None:
        """Zeigt die Restzeit dauerhaft rechts in der Statusleiste. Wer
        nicht sieht, dass der Modus an ist, sucht den Fehler bei
        sich."""
        self.pruefungsanzeige.setText(restzeit_text())
        self.pruefungsanzeige.setVisible(bool(restzeit_text()))

    def _vervollstaendigung_umschalten(self, an: bool) -> None:
        """Schaltet die Vervollständigung in allen offenen Editor-Tabs
        und merkt sich die Wahl für den nächsten Start."""
        self._design_einstellungen.setValue("editor/vervollstaendigung", an)
        for index in range(self.editor_tabs.count()):
            editor = self.editor_tabs.widget(index)
            if isinstance(editor, QuelltextEditor):
                editor.vervollstaendigung_setzen(an)

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
 Start (Gewünscht: ein geschlossenes Dock
 wie „Datenbank“ soll auch beim nächsten Mal zu bleiben) – und
 beendet ein noch laufendes Schülerprogramm."""
        self._design_einstellungen.setValue("fenster/layout", self.saveState())
        self.kindprozesse_beenden()
        super().closeEvent(event)

    def kindprozesse_beenden(self) -> int:
        """Beendet ein noch laufendes Programm und eine offene
        Debugger-Sitzung. Liefert, wie viele beendet wurden.

        Gefunden beim Aufräumen nach der Funktionsprüfung: auf diesem
        Rechner warteten neunundvierzig `debugpy`-Prozesse aus
        früheren Sitzungen darauf, dass sich ein Debugger verbindet, der
        nie kommen würde. Schließt jemand Natter, während sein Programm
        läuft, bleibt es als Waise zurück – und der „Stopp“-Knopf, mit
        dem man es beenden könnte, ist mit der IDE verschwunden. Auf
        einem Schulrechner sammeln sich so über ein paar Stunden
        Unterricht Dutzende an.
        """
        beendet = 0
        if self.debug_sitzung is not None:
            self.debug_sitzung.beenden()
            self.debug_sitzung = None
            beendet += 1
        if self.laufender_prozess is not None and self.laufender_prozess.poll() is None:
            self.laufender_prozess.kill()
            beendet += 1
        self.laufender_prozess = None
        self._ausgabe_leser_beenden()
        # Sonst schlägt die Uhr weiter auf ein Fenster, das es gleich
        # nicht mehr gibt.
        self._laufzeit_uhr.stop()
        return beendet

    # -- Hilfe (Abschnitt 7.2) -------------------------------------------------

    def _komponenten_referenz_aktion(self) -> bool:
        """„Hilfe → Komponenten-Referenz“.

        Früher an Windows weitergereicht (`open_url`). Für `.md` ist
        dort meist gar nichts eingetragen: im besten Fall ging der
        Editor auf, im Normalfall passierte nichts. Jetzt dieselbe
        Ansicht wie bei „Erste Schritte“.
        """
        return self._hilfedatei_zeigen("komponenten.md", "Komponenten-Referenz")

    def _ueber_aktion(self) -> None:
        QMessageBox.about(
            self,
            "Über Natter",
            "<h3>Natter</h3><p>Eine Entwicklungsumgebung für Python – "
            "Oberfläche entwerfen, Code schreiben, Programm starten.</p>",
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
            self.statusBar().showMessage(
                "Kein Projekt offen. Zuerst über „Projekt → Öffnen …“ eines laden oder ein "
                "neues anlegen."
            )
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
            self.statusBar().showMessage(
                f"{pfad.name} gibt es schon - bitte einen anderen Namen wählen."
            )
            return

        pfad.parent.mkdir(parents=True, exist_ok=True)
        diagramm_erzeugen(typ, pfad, name.strip())
        self.explorer.projekt_anzeigen(self.projekt)
        self.diagramm_oeffnen(pfad)

    def _design_datei_abgleichen(self, pfm_pfad: Path) -> None:
        """Bringt `u_*_design.py` auf den Stand der `.pfm` beim Öffnen.

        Der Designer selbst kompiliert den erzeugten Code nur im
        Speicher. Real gefunden beim Formular-Import: das importierte
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
 (gemeldet: „scrollen … funktioniert nicht“).

 Bewusst ohne `setWidgetResizable`: die Größe eines Formulars
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

    def _formular_code_umschalten(self) -> None:
        """Springt zwischen dem Formular und seiner Unit hin und her
        (Abschnitt 7.9, Umschalt+F12).

        Es ist der meistbenutzte Handgriff überhaupt: man legt einen
        Knopf ab, schreibt seinen Code, schaut wieder aufs Formular.
        In Natter lagen beide bisher zwar als Reiter
        nebeneinander, aber man musste sie suchen – und wenn die Unit
        noch gar nicht offen war, half auch das Suchen nicht.

        Beide Richtungen führen über `oeffnen()`/`datei_oeffnen()`: ein
        schon offener Reiter kommt nach vorn, ein noch nicht offener
        geht auf.
        """
        widget = self._tab_inhalt(self.editor_tabs.currentWidget())
        canvas = self._widget_zu_canvas.get(widget)
        if canvas is not None and canvas.unit_pfad is not None:
            if canvas.unit_pfad.exists():
                self.datei_oeffnen(canvas.unit_pfad)
            else:
                self.statusBar().showMessage(
                    f"Zu „{canvas.pfm_pfad.stem}“ gibt es keine Unit "
                    f"„{canvas.unit_pfad.name}“."
                )
            return

        pfad = widget.property(_PFAD_EIGENSCHAFT) if widget is not None else None
        if pfad:
            formular = Path(pfad).with_suffix(".pfm")
            if formular.exists():
                self.designer_oeffnen(formular)
                return
            self.statusBar().showMessage(
                f"Zu „{Path(pfad).name}“ gehört kein Formular "
                f"(„{formular.name}“ gibt es nicht)."
            )
            return

        self.statusBar().showMessage(
            "Hier gibt es nichts umzuschalten - der Handgriff wirkt auf ein "
            "Formular oder auf die Unit, die dazugehört."
        )

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
            self.statusBar().showMessage(
                "Kein Formular-Designer geöffnet. Zuerst links im Projekt-Explorer ein "
                "Formular (.pfm) doppelklicken."
            )
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
        """Einfacher Klick in der Palette (Rückmeldung September
 2026: „ich möchte per Klick neue Objekte auf der GUI
 hinzufügen"): macht die Komponente „scharf" (Fadenkreuz-Cursor
 im Designer) - der nächste Klick auf das
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
            self.statusBar().showMessage(
                "Kein Formular-Designer geöffnet. Zuerst links im Projekt-Explorer ein "
                "Formular (.pfm) doppelklicken."
            )
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
        self.statusBar().showMessage(
            f"Design-Prüfung: {len(befunde)} {'Fund' if len(befunde) == 1 else 'Funde'}. Jeder "
            f"Eintrag unten im Panel „Meldungen“ sagt, was sich ändern lässt; ein Klick "
            f"markiert die Komponente."
        )

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
                "Keine Prüfung möglich: Natter läuft nicht aus einer gebauten Installation. "
                "Die Prüfung gilt nur für die ausgelieferte Natter.exe."
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

    def _formular_importieren_aktion(self) -> None:
        """„Werkzeuge → Formular importieren (.lfm) …“ (Abschnitt 15):
        `.lfm` wählen, in `.pfm` umwandeln, unter einem gewählten Pfad
        speichern, im Designer öffnen und direkt durch den Design-Prüfer
        aus M7 laufen lassen. Nicht unterstützte Komponenten/
        Eigenschaften landen als Hinweis im Importbericht (Panel
        „Meldungen“), zusammen mit den Design-Prüfer-Funden."""
        quelle, _ = QFileDialog.getOpenFileName(
            self, "Formular importieren", filter="Formulardateien (*.lfm)"
        )
        if not quelle:
            return
        try:
            lfm_objekt = parse_lfm(Path(quelle).read_text(encoding="utf-8"))
        except LfmParserError as fehler:
            self.statusBar().showMessage(
                f"Import fehlgeschlagen: {fehler}. Ist die gewählte Datei wirklich ein "
                f"Formular im .lfm-Format?"
            )
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
        if not self.datei_schreiben_gemeldet(
            Path(ziel),
            json.dumps(ergebnis.pfm, indent=2, ensure_ascii=False) + "\n",
            folge="Das importierte Formular ist damit nicht angelegt worden.",
        ):
            return

        ziel_pfad = Path(ziel)
        bild_pfade = self._import_bilder_schreiben(ergebnis, ziel_pfad)
        self._import_unit_schreiben(ergebnis, Path(quelle), ziel_pfad, bild_pfade)

        formular = self.designer_oeffnen(Path(ziel))
        canvas = self._widget_zu_canvas[formular._qwidget]
        self._design_pruefen(canvas)
        for warnung in ergebnis.warnungen:
            self.meldungen_liste.addItem(f"[Formular-Import] {warnung}")
        if ergebnis.warnungen:
            self.panels.setCurrentWidget(self.meldungen_liste)

        self.statusBar().showMessage(
            f"{Path(quelle).name} importiert: {len(ergebnis.warnungen)} "
            f"{'Hinweis' if len(ergebnis.warnungen) == 1 else 'Hinweise'} im Importbericht - "
            f"dort steht, was von Hand nachzutragen ist."
        )

    def _import_bilder_schreiben(
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

    def _import_unit_schreiben(
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
            for methodenname, quell_name in ergebnis.handler_quellen.items()
            if methodenname and quell_name in ruempfe
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
            self.statusBar().showMessage(
                f"Paketliste nicht lesbar: {fehler}. Besteht eine Verbindung zum Netz?"
            )
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
        if not self._hintergrund_frei("Die Installation"):
            return

        self.statusBar().showMessage(
            f"{name} wird installiert - das kann je nach Netz dauern, die IDE bleibt "
            f"bedienbar."
        )
        self._hintergrund_starten(
            lambda _melden: paket_installieren(name),
            lambda _ergebnis: self.statusBar().showMessage(f"{name} installiert."),
            f"Installation von {name} fehlgeschlagen",
        )

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
            self.statusBar().showMessage(
                f"Paketliste exportieren fehlgeschlagen: {fehler}. Bestehen Schreibrechte im "
                f"gewählten Ordner?"
            )
            return
        self.statusBar().showMessage(f"Paketliste exportiert nach {pfad}.")

    def _bei_explorer_doppelklick(self, eintrag, spalte: int) -> None:
        pfad = eintrag.data(0, PFAD_ROLLE)
        if pfad is None:
            return
        self.oeffnen(Path(pfad))

    def oeffnen(self, pfad: Path) -> None:
        """Öffnet `pfad` in der Ansicht, die dazu passt – Designer,
        Diagramm-Editor, Betrachter oder Quelltexteditor.

        Der eine Weg dorthin, für den Projekt-Explorer wie für
        „Datei → Öffnen …“. Vorher hatte nur der Explorer diese
        Unterscheidung: über „Öffnen …“ landete eine `.pfm` als roher
        JSON-Text im Editor, ein Diagramm ebenso, und ein PNG brachte
        Natter mit einem `UnicodeDecodeError` zum Absturz. Zwei Wege zur
        selben Sache, die sich verschieden verhalten, sind schlimmer als
        einer (M11, Abschnitt 5).
        """
        pfad = Path(pfad)
        endung = pfad.suffix.lower()
        if endung in (".pfm", ".pdiag"):
            # Eine von Hand verbogene oder abgeschnittene Beschreibung
            # flog vorher als `JSONDecodeError` bzw.
            # `schema_fehler()` bis nach oben durch - in der
            # gebauten Exe hieße das: Natter ist weg (M11, Abschnitt 5).
            try:
                if endung == ".pfm":
                    self.designer_oeffnen(pfad)
                else:
                    self.diagramm_oeffnen(pfad)
            except (json.JSONDecodeError, schema_fehler(), KeyError) as fehler:
                self.statusBar().showMessage(
                    f"„{pfad.name}“ lässt sich nicht öffnen: die Datei ist beschädigt "
                    f"({fehler}). Sie wird von Natter geschrieben und sollte nicht von "
                    f"Hand bearbeitet werden."
                )
            except OSError as fehler:
                self.statusBar().showMessage(
                    f"„{pfad.name}“ lässt sich nicht öffnen: {fehler}"
                )
            return
        if endung == ".csv":
            self.datei_ansicht_oeffnen(pfad, lambda: CsvAnsicht(pfad))
        elif endung in _BILD_ENDUNGEN:
            self.datei_ansicht_oeffnen(pfad, lambda: BildVorschau(pfad))
        elif endung in _HTML_ENDUNGEN:
            self.datei_ansicht_oeffnen(pfad, lambda: HtmlVorschau(pfad))
        elif endung in MARKDOWN_ENDUNGEN:
            # Bis landete jede `.md` im Quelltexteditor:
            # `## Überschrift` und Tabellen aus Strichen, in einem
            # Fenster mit Zeilennummern und Syntaxhervorhebung. Für die
            # vier eingebauten Hilfeseiten war das seit M11 gelöst, für
            # eine selbst geöffnete Datei nicht (Abschnitt 11.6).
            self.datei_ansicht_oeffnen(
                pfad, lambda: self._markdown_ansicht(pfad), self._markdown_titel(pfad)
            )
        else:
            self.datei_oeffnen(pfad)

    def _markdown_titel(self, pfad: Path) -> str:
        """Die Überschrift der Datei als Reiterbeschriftung.

        Sonst stünde beim Klick auf „Quelltext bearbeiten“ zweimal
        „README.md“ nebeneinander, ohne Unterschied.
        """
        try:
            text = pfad.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return pfad.name
        return ueberschrift_lesen(text) or pfad.name

    def _markdown_ansicht(self, pfad: Path) -> MarkdownAnsicht:
        """Eine Markdown-Ansicht, deren Verweise in Natter aufgehen.

        Ein Klick auf `u_main.py` oder `docs/komponenten.md` im Text
        führt über `oeffnen()` in die Ansicht, die dazu passt - nicht an
        Windows vorbei in irgendein fremdes Programm.
        """
        ansicht = MarkdownAnsicht(pfad)
        ansicht.datei_angefordert.connect(self.oeffnen)
        ansicht.bearbeiten_angefordert.connect(self.datei_oeffnen)
        return ansicht

    def datei_ansicht_oeffnen(self, pfad: Path, fabrik, titel: str | None = None) -> QWidget:
        """Öffnet eine CSV-/Bild-/HTML-Datei in ihrem passenden
        Betrachter-Tab (Abschnitt 11.4, 11.5, 11.3) statt im
        Quelltexteditor. Bereits offene Betrachter werden nur aktiviert
        statt erneut geöffnet, wie bei `datei_oeffnen()`.

        Ein Editor auf dieselbe Datei zählt dabei nicht: wer eine
        `.md` im Editor offen hat und sie aus dem Explorer anklickt,
        will sie gesetzt sehen. Beide Reiter nebeneinander sind hier
        gewollt – die Ansicht lädt sich neu, sobald im Editor
        gespeichert wird."""
        pfad = Path(pfad)
        for index in range(self.editor_tabs.count()):
            widget = self.editor_tabs.widget(index)
            if not isinstance(widget, QuelltextEditor) and (
                widget.property(_PFAD_EIGENSCHAFT) == str(pfad)
            ):
                self.editor_tabs.setCurrentIndex(index)
                return widget

        widget = fabrik()
        widget.setProperty(_PFAD_EIGENSCHAFT, str(pfad))
        index = self.editor_tabs.addTab(widget, titel or pfad.name)
        self.editor_tabs.setCurrentIndex(index)
        return widget

    def _projekt_starten_aktion(self) -> None:
        """„Starten ohne Debugger“ (Strg+F5, Abschnitt 7.8). Standardmäßig
        nur eine laufende Instanz pro Projekt (Abschnitt 7.8); ein
        erneuter Start bei bereits laufendem Programm wird abgelehnt statt
        eine weitere Instanz zu starten. Vor dem Start prüft Ruff das
        Projekt (Abschnitt 8.2); bei Funden wird nicht gestartet."""
        if self.projekt is None:
            self.statusBar().showMessage(
                "Kein Projekt offen. Zuerst über „Projekt → Öffnen …“ eines laden oder ein "
                "neues anlegen."
            )
            return
        if self.laufender_prozess is not None and self.laufender_prozess.poll() is None:
            self.statusBar().showMessage(
                f"{self.projekt.name} läuft bereits - zuerst über „Start → Stopp“ beenden."
            )
            return

        if self._vorstart_pruefung_blockiert():
            return

        self.laufender_prozess = projekt_starten(self.projekt)
        self._ausgabe_leser_starten()
        self._start_zeitpunkt = time.monotonic()
        self.ausgabe_zeile(f"{self.projekt.name} gestartet ({self.projekt.haupt_datei.name})")
        self.panels.setCurrentWidget(self.ausgabe_liste)
        self._laufzeit_uhr.start()
        self.statusBar().showMessage(f"{self.projekt.name} gestartet")

    def _vorstart_pruefung_blockiert(self) -> bool:
        """Die Prüfung vor dem Start (Abschnitt 8.2). Liefert, ob der
        Start deshalb unterbleibt.

        Bis M12 verhinderte jeder Fund den Start. Wer `import random`
        schreibt, bevor er `random` benutzt – also so, wie man es lernt –,
        bekam sein Programm nicht gestartet, obwohl es einwandfrei
        gelaufen wäre. Ungenutzter Import und ungenutzte Variable sind
        Unordnung, kein Fehler; sie stehen jetzt als Hinweis im Panel,
        und das Programm läuft. Ein Syntaxfehler oder ein unbekannter
        Name verhindert den Start weiterhin: dort stürzt das Programm
        ohnehin ab, und die Meldung vorher sagt mehr als der Absturz
        danach."""
        funde = projekt_pruefen(self.projekt)
        self.meldungen_liste.clear()
        self._funde_in_editoren_zeigen(funde)
        if not funde:
            return False

        self.meldungen_liste.addItems([str(fund) for fund in funde])
        self.panels.setCurrentWidget(self.meldungen_liste)

        blockierend = [fund for fund in funde if fund.blockiert]
        if blockierend:
            anzahl = len(blockierend)
            self.statusBar().showMessage(
                f"{anzahl} {'Fund' if anzahl == 1 else 'Funde'} vor dem Start - nicht "
                f"gestartet. Jeder Eintrag unten im Panel „Meldungen“ nennt Datei und "
                f"Zeile; ein Klick führt dorthin."
            )
            return True

        anzahl = len(funde)
        self.statusBar().showMessage(
            f"{anzahl} {'Hinweis' if anzahl == 1 else 'Hinweise'} unten im Panel "
            f"„Meldungen“ - das Programm läuft trotzdem."
        )
        return False

    def _ausgabe_leser_starten(self) -> None:
        """Hängt den Leser an die Ausgabe des gestarteten Programms.

        Ein GUI-Programm läuft ohne Konsolenfenster; was es schreibt,
        ginge sonst in ein Rohr, aus dem niemand liest - und ein volles
        Rohr hält das Programm an, sobald es genug geschrieben hat. Ein
        Konsolenprojekt hat sein eigenes Fenster und braucht den Leser
        nicht.
        """
        self._ausgabe_leser_beenden()
        prozess = self.laufender_prozess
        if prozess is None or prozess.stdout is None:
            return
        leser = AusgabeLeser(prozess, self)
        leser.zeile.connect(self.ausgabe_zeile)
        self._ausgabe_leser = leser
        leser.start()

    def _ausgabe_leser_beenden(self) -> None:
        """Wartet kurz auf den Leser, statt ihn stehenzulassen.

        Beim Beenden des Programms geht sein Rohr zu, und der Leser
        kommt von selbst zum Ende - das dauert aber einen Augenblick.
        """
        leser = self._ausgabe_leser
        self._ausgabe_leser = None
        if leser is not None and leser.isRunning():
            leser.wait(1000)

    def ausgabe_zeile(self, text: str) -> None:
        """Eine Zeile im Panel „Ausgabe“, mit der Uhrzeit davor."""
        self.ausgabe_liste.addItem(f"{time.strftime('%H:%M:%S')}  {text}")
        self.ausgabe_liste.scrollToBottom()

    def _programmende_pruefen(self) -> None:
        """Sieht nach, ob das gestartete Programm inzwischen zu Ende ist.

        Nötig, weil das Programm als eigener Prozess in einem eigenen
        Fenster läuft (Abschnitt 7.8) und sich nicht von selbst
        zurückmeldet."""
        if self.laufender_prozess is None:
            self._laufzeit_uhr.stop()
            return
        code = self.laufender_prozess.poll()
        if code is None:
            return
        self._laufzeit_uhr.stop()
        self.programmende_melden(code)
        self.laufender_prozess = None

    def programmende_melden(self, code: int) -> None:
        """Exitcode und Laufzeit ins Panel „Ausgabe“ (Abschnitt 7.8).

        Ein Exitcode ungleich 0 heißt, dass das Programm mit einem
        Fehler geendet ist. Das steht dabei, weil „Code 1“ allein
        niemandem etwas sagt – die Fehlermeldung selbst steht im
        Konsolenfenster des Programms, das offen bleibt."""
        dauer = ""
        if self._start_zeitpunkt is not None:
            sekunden = time.monotonic() - self._start_zeitpunkt
            dauer = f" nach {sekunden:.1f} s".replace(".", ",")
        self._start_zeitpunkt = None
        if code == 0:
            self.ausgabe_zeile(f"Programm beendet (Code 0){dauer}")
            return
        self.ausgabe_zeile(
            f"Programm beendet (Code {code}){dauer} – Code {code} heißt: mit einem Fehler "
            f"geendet. Die Fehlermeldung steht im Fenster des Programms, es bleibt dafür "
            f"offen."
        )

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
            self.statusBar().showMessage(
                "Kein Projekt offen. Zuerst über „Projekt → Öffnen …“ eines laden oder ein "
                "neues anlegen."
            )
            return
        if self.debug_sitzung is not None:
            self.statusBar().showMessage(
                f"{self.projekt.name} läuft bereits (Debugger) - zuerst über „Start → Stopp“ "
                f"beenden."
            )
            return

        if self._vorstart_pruefung_blockiert():
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
        self.statusBar().showMessage(f"Angehalten: {haltegrund_deutsch(grund)}")
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
        self._katalogmeldung_anzeigen(meldung.als_text())
        self._zu_wo_springen(meldung.wo)

    def _katalogmeldung_anzeigen(self, text: str) -> None:
        """Eine Fehlerkatalog-Meldung in der Festbreitenschrift.

        Die Meldung enthält die Zeile aus dem Quelltext und darunter
        eine Zeile mit ^^^, die auf die Stelle zeigt. In der
        Proportionalschrift der Liste standen die Zeichen irgendwo -
        die Markierung war damit wertlos. Nur diese Einträge bekommen
        die Schrift; ein deutscher Satz liest sich proportional besser.
        """
        eintrag = QListWidgetItem(text)
        eintrag.setFont(QFont(self._code_schriftart))
        self.meldungen_liste.addItem(eintrag)
        self.panels.setCurrentWidget(self.meldungen_liste)
        self._panel_hoehe_sichern(text.count(_UMBRUCH) + 1)

    def _panel_hoehe_sichern(self, zeilen: int) -> None:
        """Macht das Panel hoch genug für eine Meldung aus `zeilen`
        Zeilen - aber höchstens bis zur Hälfte des Fensters.

        Eine Katalogmeldung ist sechs Zeilen lang; das Panel steht
        standardmäßig auf einer Höhe, in der davon zweieinhalb zu sehen
        waren. Ausgerechnet der Teil „Was“ und „Prüfe“ stand unter der
        Kante. Kleiner zieht es niemandem etwas zusammen: die Höhe wird
        nur vergrößert, nie verkleinert.
        """
        benoetigt = zeilen * self.meldungen_liste.fontMetrics().lineSpacing() + _PANEL_RAHMEN
        obergrenze = max(_PANEL_RAHMEN, self.height() // 2)
        ziel = min(benoetigt, obergrenze)
        if self.panels_dock.height() < ziel:
            self.resizeDocks([self.panels_dock], [ziel], Qt.Orientation.Vertical)

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
        if editor is None:
            return
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        cursor.movePosition(cursor.MoveOperation.Down, cursor.MoveMode.MoveAnchor, zeile - 1)
        editor.setTextCursor(cursor)

    def _debugger_beendet(self, exitcode: int) -> None:
        self.statusBar().showMessage(
            f"Debugger beendet, das Programm endete mit Rückgabewert {exitcode}. 0 heißt: ohne "
            f"Fehler."
        )
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
        if editor is None:
            return
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

    def variablen_kontextmenue_fuer(self, punkt) -> QMenu | None:
        """Das Menü im Panel „Variablen“: „Als Tabelle anzeigen“ für
        DataFrames, Listen und Dictionaries (Abschnitt 11.6). `None` im
        Leeren, wo es nichts zu zeigen gäbe.

        Getrennt vom Anzeigen, damit der Rundlauf in
        `tests/test_ide_funktionspruefung.py` jeden Eintrag auslösen
        kann, ohne ein Menü zu öffnen, das auf einen Klick wartet.
        """
        eintrag = self.variablen_baum.itemAt(punkt)
        if eintrag is None:
            return None
        menue = QMenu(self.variablen_baum)
        aktion = menue.addAction("Als Tabelle anzeigen")
        aktion.triggered.connect(
            lambda *_: self.variable_als_tabelle_zeigen(eintrag.text(0))
        )
        return menue

    def _variablen_menue_zeigen(self, punkt) -> None:
        menue = self.variablen_kontextmenue_fuer(punkt)
        if menue is not None:
            menue.exec(self.variablen_baum.viewport().mapToGlobal(punkt))

    def variable_als_tabelle_zeigen(self, name: str) -> None:
        """Lässt `name` im angehaltenen Schülerprogramm auswerten und
        zeigt das Ergebnis als Tabelle (Abschnitt 11.6). Die Antwort
        kommt asynchron über das Signal `ausgewertet` in
        `_debugger_tabelle_bereit()`."""
        if self.debug_sitzung is None or not self._letzter_aufrufstapel:
            self.statusBar().showMessage(
                "Keine Tabelle möglich: Das Programm ist gerade nicht angehalten. Zuerst einen "
                "Haltepunkt setzen und mit F5 starten."
            )
            return
        try:
            # `debugpy` blendet im Variablen-Panel Sammelzeilen wie
            # „special variables“ ein. Beim Bildschirmfoto gesehen: ein
            # Doppelklick darauf schickte diesen Text als Ausdruck an den
            # Debugger - Syntaxfehler im Panel „Meldungen“ statt einer
            # verständlichen Antwort.
            compile(name, "<variable>", "eval")
        except SyntaxError:
            self.statusBar().showMessage(
                f"{name!r} ist keine Variable, die sich auswerten lässt. Im Panel „Variablen“ "
                f"eine Zeile mit einem echten Variablennamen wählen."
            )
            return
        self._tabellen_variable = name
        self.debug_sitzung.auswerten(tabellen_ausdruck(name), self._letzter_aufrufstapel[0]["id"])

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
        """„Start → Stopp“ (Umschalt+F5).

        Beendet beides: eine Debugger-Sitzung und ein mit Strg+F5
        gestartetes Programm. Vorher hing der Eintrag allein am
        Debugger – wer sein Programm mit Strg+F5 gestartet hatte, bekam
        von Natter sogar den Rat, es „über Start → Stopp“ zu beenden,
        und dort passierte dann nichts (M11, Abschnitt 5).
        """
        gestoppt = []
        if self.debug_sitzung is not None:
            self.debug_sitzung.beenden()
            self.debug_sitzung = None
            self._aktueller_thread_id = None
            gestoppt.append("Debugger")
        if self.laufender_prozess is not None and self.laufender_prozess.poll() is None:
            self.laufender_prozess.kill()
            self._laufzeit_uhr.stop()
            self.ausgabe_zeile("Programm über „Start → Stopp“ beendet")
            self._start_zeitpunkt = None
            self.laufender_prozess = None
            gestoppt.append("Programm")
        if not gestoppt:
            self.statusBar().showMessage("Es läuft gerade nichts, was sich stoppen ließe.")
            return
        self.statusBar().showMessage(f"{' und '.join(gestoppt)} gestoppt")

    def _debugger_einzelschritt_aktion(self) -> None:
        if self.debug_sitzung is not None and self._aktueller_thread_id is not None:
            self.debug_sitzung.einzelschritt(self._aktueller_thread_id)

    def _debugger_prozedurschritt_aktion(self) -> None:
        if self.debug_sitzung is not None and self._aktueller_thread_id is not None:
            self.debug_sitzung.prozedurschritt(self._aktueller_thread_id)

    def _debugger_ruecksprung_aktion(self) -> None:
        if self.debug_sitzung is not None and self._aktueller_thread_id is not None:
            self.debug_sitzung.bis_ruecksprung(self._aktueller_thread_id)
