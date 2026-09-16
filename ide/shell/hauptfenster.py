"""HauptFenster: Grundgerüst des IDE-Hauptfensters.

Siehe konzept-natter.md, Abschnitt 7.1, 7.4, 7.5. Menüleiste mit den
Menütiteln aus Abschnitt 7.2 (Einträge kommen über das Aktionsregister),
Docks für Explorer/Objektinspektor/Panels, zentrale Editor-Tabs,
Statusleiste. `projekt_oeffnen`/`datei_oeffnen` sind die Grundlage für
„Projekt öffnen …“/„Öffnen …“ (M2, Schritt 5).
"""

from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor
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
from ide.debugger import DebugSitzung, fehlermeldung_aus_dap_erzeugen
from ide.designer import DesignerCanvas, formular_fuer_designer_laden
from ide.inspector import Objektinspektor
from ide.palette import Komponentenpalette
from ide.palette.palette import TYP_ROLLE
from ide.project import Projekt
from ide.run import projekt_pruefen, projekt_starten
from ide.shell.explorer import PFAD_ROLLE, ProjektExplorer
from ide.shell.quelltexteditor import QuelltextEditor
from ide.shell.schnellauswahl import SchnellAuswahl
from ide.testrunner import Testergebnis, ergebnisse_als_html, tests_ausfuehren
from ide.viewers import BildVorschau, CsvAnsicht, HtmlVorschau
from pcl.form import Form

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

        self._letzte_testergebnisse: list[Testergebnis] = []
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
                "datei.neue_test_unit",
                "Neue Test-Unit",
                menue="Datei",
                callback=self._neue_test_unit_aktion,
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
        endung = pfad.suffix.lower()
        if endung == ".pfm":
            self.designer_oeffnen(pfad)
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
