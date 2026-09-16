"""HauptFenster: Grundgerüst des IDE-Hauptfensters.

Siehe konzept-natter.md, Abschnitt 7.1, 7.4, 7.5. Menüleiste mit den
Menütiteln aus Abschnitt 7.2 (Einträge kommen über das Aktionsregister),
Docks für Explorer/Objektinspektor/Panels, zentrale Editor-Tabs,
Statusleiste. `projekt_oeffnen`/`datei_oeffnen` sind die Grundlage für
„Projekt öffnen …“/„Öffnen …“ (M2, Schritt 5).
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QDialog,
    QDockWidget,
    QFileDialog,
    QListWidget,
    QMainWindow,
    QPlainTextEdit,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
)

from ide.actions import Aktion, Aktionsregister
from ide.assets import symbol
from ide.debugger import DebugSitzung
from ide.designer import DesignerCanvas, formular_fuer_designer_laden
from ide.inspector import Objektinspektor
from ide.palette import Komponentenpalette
from ide.palette.palette import TYP_ROLLE
from ide.project import Projekt
from ide.run import projekt_pruefen, projekt_starten
from ide.shell.explorer import PFAD_ROLLE, ProjektExplorer
from ide.shell.quelltexteditor import QuelltextEditor
from ide.shell.schnellauswahl import SchnellAuswahl
from pcl.form import Form

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

# Name der dynamischen QWidget-Eigenschaft, die den Dateipfad eines
# Editor-Tabs trägt (nicht zu verwechseln mit PFAD_ROLLE, das ist die
# Qt.ItemDataRole für Explorer-Einträge).
_PFAD_EIGENSCHAFT = "pfad"


class HauptFenster(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Natter")
        self.setWindowIcon(symbol("app"))

        self._menues: dict[str, object] = {}
        for titel in MENUETITEL:
            self._menues[titel] = self.menuBar().addMenu(titel)

        self.werkzeugleiste = self.addToolBar("Haupt-Werkzeugleiste")
        self.werkzeugleiste.setMovable(False)
        self.werkzeugleiste.setIconSize(QSize(22, 22))

        self.editor_tabs = QTabWidget()
        self.editor_tabs.setTabsClosable(True)
        self.editor_tabs.setMovable(True)
        self.setCentralWidget(self.editor_tabs)

        self.explorer = ProjektExplorer()
        self.explorer.itemDoubleClicked.connect(self._bei_explorer_doppelklick)
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
        self.palette_dock = self._dock_erzeugen(
            "Komponentenpalette", Qt.DockWidgetArea.TopDockWidgetArea, inhalt=self.palette
        )

        self.projekt: Projekt | None = None
        self.laufender_prozess = None
        self._offene_canvases: list[DesignerCanvas] = []
        self._pfad_zu_formular: dict[str, Form] = {}
        self._widget_zu_canvas: dict[QWidget, DesignerCanvas] = {}
        self._aktueller_canvas: DesignerCanvas | None = None
        self.editor_tabs.currentChanged.connect(self._bei_tab_wechsel)

        self.panels = QTabWidget()
        self.meldungen_liste = QListWidget()
        self.variablen_baum = QTreeWidget()
        self.variablen_baum.setHeaderLabels(["Eigenschaft", "Wert"])
        self.aufrufstapel_liste = QListWidget()
        panel_widgets = {
            "Meldungen": self.meldungen_liste,
            "Variablen": self.variablen_baum,
            "Aufrufstapel": self.aufrufstapel_liste,
        }
        for reiter in PANEL_REITER:
            self.panels.addTab(panel_widgets.get(reiter, QWidget()), reiter)
        self.panels_dock = self._dock_erzeugen(
            "Panels", Qt.DockWidgetArea.BottomDockWidgetArea, inhalt=self.panels
        )

        self.debug_sitzung: DebugSitzung | None = None
        self._aktueller_thread_id: int | None = None

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
        self.aktionen.registrieren(
            Aktion(
                "projekt.oeffnen",
                "Projekt öffnen …",
                menue="Projekt",
                symbol="projekt_oeffnen",
                callback=self._projekt_oeffnen_dialog,
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

    def unit_erzeugen(self, name: str | None = None) -> Path:
        """„Neue Unit“ (Abschnitt 7.2, 7.4): legt `u_neu<n>.py` an (oder
        mit gegebenem `name`), fügt sie dem Projekt-Explorer hinzu und
        öffnet sie im Editor."""
        if self.projekt is None:
            raise RuntimeError("Kein Projekt offen.")

        if name is None:
            name = self._naechster_unit_name()

        pfad = self.projekt.ordner / f"{name}.py"
        if pfad.exists():
            raise FileExistsError(f"{pfad} existiert bereits.")

        pfad.write_text("", encoding="utf-8")
        self.explorer.projekt_anzeigen(self.projekt)
        self.datei_oeffnen(pfad)
        return pfad

    def _naechster_unit_name(self) -> str:
        vorhandene = {p.stem for p in self.projekt.units()}
        zaehler = 1
        while f"u_neu{zaehler}" in vorhandene:
            zaehler += 1
        return f"u_neu{zaehler}"

    def _neue_unit_aktion(self) -> None:
        if self.projekt is None:
            self.statusBar().showMessage("Kein Projekt offen.")
            return
        self.unit_erzeugen()

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

        editor = QuelltextEditor()
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

    def designer_oeffnen(self, pfad: Path) -> Form:
        """Öffnet eine `.pfm`-Datei im Formular-Designer statt als
        Rohtext (Abschnitt 4.2, 7.7): der Designer rendert echte
        `pcl`-Komponenten, kein Nachbau. Bereits offene Formulare werden
        nur aktiviert statt erneut geladen."""
        pfad = Path(pfad)
        schluessel = str(pfad)
        if schluessel in self._pfad_zu_formular:
            formular = self._pfad_zu_formular[schluessel]
            index = self.editor_tabs.indexOf(formular._qwidget)
            if index != -1:
                self.editor_tabs.setCurrentIndex(index)
            return formular

        formular = formular_fuer_designer_laden(pfad)
        canvas = DesignerCanvas(formular, pfm_pfad=pfad)
        canvas.auswahl_beobachten(self._designer_auswahl_geaendert)
        self._offene_canvases.append(canvas)
        self._pfad_zu_formular[schluessel] = formular
        self._widget_zu_canvas[formular._qwidget] = canvas

        index = self.editor_tabs.addTab(formular._qwidget, f"{pfad.stem} (Designer)")
        self.editor_tabs.setCurrentIndex(index)
        self.objektinspektor.formular_anzeigen(formular)
        return formular

    def _bei_tab_wechsel(self, index: int) -> None:
        widget = self.editor_tabs.widget(index)
        self._aktueller_canvas = self._widget_zu_canvas.get(widget)

    def _bei_palette_doppelklick(self, eintrag) -> None:
        """Doppelklick in der Palette platziert die Komponente mittig im
        aktiven Formular-Designer (Abschnitt 7.3)."""
        if self._aktueller_canvas is None:
            self.statusBar().showMessage("Kein Formular-Designer geöffnet.")
            return
        typ = eintrag.data(TYP_ROLLE)
        formular = self._aktueller_canvas.formular
        self._aktueller_canvas.komponente_platzieren(
            typ, formular.width // 2, formular.height // 2
        )

    def _designer_auswahl_geaendert(self, komponente) -> None:
        self.objektinspektor.eigenschaften_tabelle.komponente_anzeigen(komponente)
        self.objektinspektor.ereignisse_tabelle.anzeigen(komponente, self.objektinspektor.formular)

    def _bei_explorer_doppelklick(self, eintrag, spalte: int) -> None:
        pfad = eintrag.data(0, PFAD_ROLLE)
        if pfad is None:
            return
        pfad = Path(pfad)
        if pfad.suffix == ".pfm":
            self.designer_oeffnen(pfad)
        else:
            self.datei_oeffnen(pfad)

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
        self.debug_sitzung.starten(
            self.projekt.haupt_datei,
            arbeitsordner=self.projekt.ordner,
            anfangs_breakpoints=self._offene_breakpoints(),
        )
        self.statusBar().showMessage(f"{self.projekt.name} gestartet (mit Debugger)")

    def _debugger_angehalten(self, ereignis: dict) -> None:
        self._aktueller_thread_id = ereignis.get("threadId")
        grund = ereignis.get("reason", "?")
        self.statusBar().showMessage(f"Angehalten ({grund})")
        if self._aktueller_thread_id is not None:
            self.debug_sitzung.aufrufstapel_lesen(self._aktueller_thread_id)

    def _debugger_beendet(self, exitcode: int) -> None:
        self.statusBar().showMessage(f"Debugger beendet (Exitcode {exitcode})")
        self.debug_sitzung = None
        self._aktueller_thread_id = None
        self.variablen_baum.clear()
        self.aufrufstapel_liste.clear()

    def _debugger_fehler(self, meldung: str) -> None:
        self.meldungen_liste.addItem(meldung)
        self.panels.setCurrentWidget(self.meldungen_liste)

    def _debugger_aufrufstapel_bereit(self, stapel: list[dict]) -> None:
        self.aufrufstapel_liste.clear()
        for frame in stapel:
            quelle = frame.get("source", {}).get("path", "")
            name = Path(quelle).name if quelle else "?"
            self.aufrufstapel_liste.addItem(f"{name}, Zeile {frame['line']}, in {frame['name']}")
        if stapel and self.debug_sitzung is not None:
            self.debug_sitzung.bereiche_lesen(stapel[0]["id"])

    def _debugger_bereiche_bereit(self, bereiche: list[dict]) -> None:
        if not bereiche or self.debug_sitzung is None:
            return
        lokale = next((b for b in bereiche if b["name"] == "Locals"), bereiche[0])
        self.debug_sitzung.variablen_lesen(lokale["variablesReference"])

    def _debugger_variablen_bereit(self, variablen: list[dict]) -> None:
        self.variablen_baum.clear()
        for variable in variablen:
            QTreeWidgetItem(self.variablen_baum, [variable["name"], str(variable.get("value"))])

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
