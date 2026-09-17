"""DiagrammFenster: eigenes Fenster für den Diagramm-Editor
(Abschnitt 13.1, 13.2).

Bewusst ein eigenständiges `QMainWindow` **ohne** Elternfenster, damit
Windows einen eigenen Taskleisten-Eintrag vergibt und das Fenster
unabhängig vom Hauptfenster verschoben werden kann (z. B. auf einen
zweiten Bildschirm) – kein Dock und kein Tab in der IDE
(Nutzer-Entscheidung September 2026, siehe docs/arbeitspakete/M9.md).

Stand M9, Schritt 1: Grundgerüst mit Menüs, Statusleiste und leerer
Zeichenfläche. Die Menüeinträge aus Abschnitt 13.2 sind vollständig
angelegt, aber nur die bereits umgesetzten sind aktiv – der Rest ist
ausgegraut, statt ein Verhalten vorzutäuschen, das noch nicht existiert
(Zeichenfläche/Formen folgen in Schritt 2).
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QFileDialog, QLabel, QMainWindow, QMenu, QWidget

from ide.assets import symbol
from ide.diagramm.datei import Diagramm
from ide.diagramm.neu import TYP_BESCHRIFTUNGEN
from ide.shell.theme import ide_qss_erzeugen

#: Menüaufbau aus Abschnitt 13.2. `True` = in diesem Schritt bereits
#: umgesetzt und aktiv, `False` = angelegt, aber ausgegraut.
_MENUES: dict[str, tuple[tuple[str, bool], ...]] = {
    "Datei": (
        ("Speichern", True),
        ("Speichern unter …", True),
        ("Exportieren …", False),
        ("Drucken …", False),
        ("Schließen", True),
    ),
    "Bearbeiten": (
        ("Rückgängig", False),
        ("Wiederholen", False),
        ("Ausschneiden", False),
        ("Kopieren", False),
        ("Einfügen", False),
        ("Duplizieren", False),
        ("Löschen", False),
        ("Alles auswählen", False),
    ),
    "Ansicht": (
        ("Zoom vergrößern", False),
        ("Zoom verkleinern", False),
        ("Raster", False),
        ("Lineale", False),
        ("Hilfslinien", False),
        ("Minimap", False),
        ("Seitenränder", False),
    ),
    "Anordnen": (
        ("Ausrichten", False),
        ("Verteilen", False),
        ("Gleiche Größe", False),
        ("In den Vordergrund", False),
        ("In den Hintergrund", False),
        ("Gruppieren", False),
    ),
    "Format": (
        ("Stilvorlage …", False),
        ("Füllung …", False),
        ("Linie …", False),
        ("Schrift …", False),
        ("Stil übertragen", False),
    ),
    "Hilfe": (("Über den Diagramm-Editor", True),),
}


class DiagrammFenster(QMainWindow):
    def __init__(self, diagramm: Diagramm) -> None:
        super().__init__()
        self.diagramm = diagramm
        self.setWindowIcon(symbol("app"))
        self._titel_setzen()

        # Gleiche Einstellungen wie die IDE (Abschnitt 13.1: „Gleiches
        # Theme … wie die IDE“), gleicher QSettings-Zugriff wie
        # `HauptFenster` - dadurch wirkt „Ansicht → Design“ der IDE auch
        # auf neu geöffnete Diagrammfenster.
        einstellungen = QSettings(
            QSettings.Format.IniFormat, QSettings.Scope.UserScope, "Natter", "Natter-IDE"
        )
        self.setStyleSheet(
            ide_qss_erzeugen(
                einstellungen.value("design/thema", "system"),
                code_schriftart=einstellungen.value("editor/schriftart", "Consolas"),
            )
        )

        self._menues: dict[str, QMenu] = {}
        self.aktionen: dict[str, object] = {}
        self._menues_aufbauen()

        # Platzhalter bis Schritt 2 (Zeichenfläche mit Formen).
        self.zeichenflaeche: QWidget = QLabel(
            f"{TYP_BESCHRIFTUNGEN.get(diagramm.typ, diagramm.typ)}: {diagramm.name}"
        )
        self.zeichenflaeche.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCentralWidget(self.zeichenflaeche)

        self._statusleiste_aktualisieren()
        self.resize(1100, 750)

    # -- Aufbau ---------------------------------------------------------

    def _menues_aufbauen(self) -> None:
        for menue_name, eintraege in _MENUES.items():
            menue = self.menuBar().addMenu(menue_name)
            self._menues[menue_name] = menue
            for beschriftung, aktiv in eintraege:
                aktion = menue.addAction(beschriftung)
                aktion.setEnabled(aktiv)
                self.aktionen[f"{menue_name}/{beschriftung}"] = aktion

        self.aktionen["Datei/Speichern"].triggered.connect(self.speichern)
        self.aktionen["Datei/Speichern unter …"].triggered.connect(self.speichern_unter)
        self.aktionen["Datei/Schließen"].triggered.connect(self.close)

    def menue(self, name: str) -> QMenu:
        return self._menues[name]

    def _titel_setzen(self) -> None:
        self.setWindowTitle(f"{self.diagramm.pfad.name} – Diagramm-Editor – Natter")

    def _statusleiste_aktualisieren(self) -> None:
        """Statusleiste nach Abschnitt 13.2 (Auswahl, Raster, Einrasten,
        Seitenformat, Stilvorlage). Auswahl/Raster/Einrasten zeigen
        vorerst den Ausgangszustand – sie bekommen mit der Zeichenfläche
        in Schritt 2 echte Werte."""
        seite = self.diagramm.daten["page"]
        ausrichtung = "quer" if seite["orientation"] == "landscape" else "hoch"
        self.statusBar().showMessage(
            f"0 Formen  │  Raster 8 px  │  Einrasten ein  │  "
            f"{seite['size']} {ausrichtung}  │  Stil: {self.diagramm.stil}"
        )

    # -- Datei ----------------------------------------------------------

    def speichern(self) -> None:
        self.diagramm.speichern()
        self.statusBar().showMessage(f"{self.diagramm.pfad.name} gespeichert", 3000)

    def speichern_unter(self, pfad: Path | None = None) -> Path | None:
        """Speichert unter einem neuen Pfad. `pfad=None` fragt über einen
        Dateidialog (in Tests wird der Pfad direkt übergeben)."""
        if pfad is None:
            gewaehlt, _ = QFileDialog.getSaveFileName(
                self, "Diagramm speichern unter", str(self.diagramm.pfad), "Diagramm (*.pdiag)"
            )
            if not gewaehlt:
                return None
            pfad = Path(gewaehlt)

        self.diagramm.speichern(Path(pfad))
        self._titel_setzen()
        return self.diagramm.pfad
