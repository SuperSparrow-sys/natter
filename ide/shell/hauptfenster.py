"""HauptFenster: Grundgerüst des IDE-Hauptfensters.

Siehe konzept-natter.md, Abschnitt 7.1, 7.4, 7.5. Menüleiste mit den
Menütiteln aus Abschnitt 7.2 (Einträge kommen über das Aktionsregister),
Docks für Explorer/Objektinspektor/Panels, zentrale Editor-Tabs,
Statusleiste. `projekt_oeffnen`/`datei_oeffnen` sind die Grundlage für
„Projekt öffnen …“/„Öffnen …“ (M2, Schritt 5).
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDockWidget,
    QFileDialog,
    QMainWindow,
    QPlainTextEdit,
    QTabWidget,
    QWidget,
)

from ide.actions import Aktion, Aktionsregister
from ide.project import Projekt
from ide.run import projekt_starten
from ide.shell.explorer import PFAD_ROLLE, ProjektExplorer
from ide.shell.schnellauswahl import SchnellAuswahl

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

        self._menues: dict[str, object] = {}
        for titel in MENUETITEL:
            self._menues[titel] = self.menuBar().addMenu(titel)

        self.editor_tabs = QTabWidget()
        self.editor_tabs.setTabsClosable(True)
        self.editor_tabs.setMovable(True)
        self.setCentralWidget(self.editor_tabs)

        self.explorer = ProjektExplorer()
        self.explorer.itemDoubleClicked.connect(self._bei_explorer_doppelklick)
        self.explorer_dock = self._dock_erzeugen(
            "Projekt-Explorer", Qt.DockWidgetArea.LeftDockWidgetArea, inhalt=self.explorer
        )
        self.inspektor_dock = self._dock_erzeugen(
            "Objektinspektor", Qt.DockWidgetArea.RightDockWidgetArea
        )

        self.projekt: Projekt | None = None
        self.laufender_prozess = None

        self.panels = QTabWidget()
        for reiter in PANEL_REITER:
            self.panels.addTab(QWidget(), reiter)
        self.panels_dock = self._dock_erzeugen(
            "Panels", Qt.DockWidgetArea.BottomDockWidgetArea, inhalt=self.panels
        )

        self.statusBar().showMessage("bereit")

        self.aktionen = Aktionsregister()
        self.aktionen.registrieren(
            Aktion(
                "datei.oeffnen",
                "Öffnen …",
                menue="Datei",
                tastenkuerzel="Ctrl+O",
                callback=self._datei_oeffnen_dialog,
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "projekt.oeffnen",
                "Projekt öffnen …",
                menue="Projekt",
                callback=self._projekt_oeffnen_dialog,
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "datei.speichern",
                "Speichern",
                menue="Datei",
                tastenkuerzel="Ctrl+S",
                callback=self._aktuelle_datei_speichern,
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
                "datei.neue_unit",
                "Neue Unit",
                menue="Datei",
                tastenkuerzel="Ctrl+N",
                callback=self._neue_unit_aktion,
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "start.ohne_debugger",
                "Starten ohne Debugger",
                menue="Start",
                tastenkuerzel="Ctrl+F5",
                callback=self._projekt_starten_aktion,
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

        editor = QPlainTextEdit()
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
        """„Speichern“ (Strg+S, Abschnitt 7.2, 7.9)."""
        index = self.editor_tabs.currentIndex()
        if index == -1:
            return
        editor = self.editor_tabs.widget(index)
        pfad = Path(editor.property(_PFAD_EIGENSCHAFT))
        pfad.write_text(editor.toPlainText(), encoding="utf-8")
        editor.document().setModified(False)

    def _bei_explorer_doppelklick(self, eintrag, spalte: int) -> None:
        pfad = eintrag.data(0, PFAD_ROLLE)
        if pfad is not None:
            self.datei_oeffnen(Path(pfad))

    def _projekt_starten_aktion(self) -> None:
        """„Starten ohne Debugger“ (Strg+F5, Abschnitt 7.8). Standardmäßig
        nur eine laufende Instanz pro Projekt (Abschnitt 7.8); ein
        erneuter Start bei bereits laufendem Programm wird abgelehnt statt
        eine weitere Instanz zu starten."""
        if self.projekt is None:
            self.statusBar().showMessage("Kein Projekt offen.")
            return
        if self.laufender_prozess is not None and self.laufender_prozess.poll() is None:
            self.statusBar().showMessage(f"{self.projekt.name} läuft bereits.")
            return
        self.laufender_prozess = projekt_starten(self.projekt)
        self.statusBar().showMessage(f"{self.projekt.name} gestartet")
