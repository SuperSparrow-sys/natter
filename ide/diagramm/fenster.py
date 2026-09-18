"""DiagrammFenster: eigenes Fenster für den Diagramm-Editor
(Abschnitt 13.1, 13.2).

Bewusst ein eigenständiges `QMainWindow` **ohne** Elternfenster, damit
Windows einen eigenen Taskleisten-Eintrag vergibt und das Fenster
unabhängig vom Hauptfenster verschoben werden kann (z. B. auf einen
zweiten Bildschirm) – kein Dock und kein Tab in der IDE
(Nutzer-Entscheidung September 2026, siehe docs/arbeitspakete/M9.md).

Stand M9, Schritt 6: Formen- und Verbindungs-Palette links,
Zeichenfläche in der Mitte, Eigenschaften-Bereich rechts. Die
Menüeinträge aus Abschnitt 13.2 sind vollständig angelegt, aber nur
die bereits umgesetzten sind aktiv – der Rest ist ausgegraut, statt
ein Verhalten vorzutäuschen, das noch nicht existiert.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QActionGroup
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QMainWindow,
    QMenu,
    QWidget,
)

from ide.assets import symbol
from ide.diagramm.canvas import DiagrammCanvas
from ide.diagramm.datei import Diagramm
from ide.diagramm.eigenschaften import EigenschaftenPanel
from ide.diagramm.formen import formen_fuer
from ide.diagramm.kommandos import WerteKommando
from ide.diagramm.palette import FormenPalette
from ide.diagramm.stil import BESCHRIFTUNGEN
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
        ("Rückgängig", True),
        ("Wiederholen", True),
        ("Ausschneiden", False),
        ("Kopieren", False),
        ("Einfügen", False),
        ("Duplizieren", True),
        ("Löschen", True),
        ("Alles auswählen", False),
    ),
    "Ansicht": (
        ("Zoom vergrößern", False),
        ("Zoom verkleinern", False),
        ("Raster", True),
        ("Lineale", False),
        ("Hilfslinien", False),
        ("Minimap", False),
        ("Seitenränder", True),
        ("Layout-Hinweise", True),
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
        ("Stilvorlage …", True),
        ("Füllung …", False),
        ("Linie …", False),
        ("Schrift …", False),
        ("Stil übertragen", True),
    ),
    "Hilfe": (("Über den Diagramm-Editor", True),),
}


class DiagrammFenster(QMainWindow):
    def __init__(self, diagramm: Diagramm) -> None:
        super().__init__()
        self.diagramm = diagramm
        self._geaendert = False
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

        # Erst die Bereiche, dann die Menüs: die Ansicht-Schalter lesen
        # ihren Anfangszustand von der Zeichenfläche ab.
        self._bereiche_aufbauen()
        self._menues: dict[str, QMenu] = {}
        self.aktionen: dict[str, object] = {}
        self._menues_aufbauen()
        self._statusleiste_aktualisieren()
        self.resize(1100, 750)

    def _bereiche_aufbauen(self) -> None:
        """Aufteilung nach Abschnitt 13.2: Formen links, Zeichenfläche in
        der Mitte, Eigenschaften rechts."""
        self.zeichenflaeche = DiagrammCanvas(self.diagramm)
        self.zeichenflaeche.auswahl_geaendert.connect(self._bei_auswahl)
        self.zeichenflaeche.geaendert.connect(self._bei_aenderung)
        self.setCentralWidget(self.zeichenflaeche)

        if formen_fuer(self.diagramm.typ):
            self.palette = FormenPalette(self.diagramm.typ)
            self.palette.form_gewaehlt.connect(self.zeichenflaeche.platzierungsmodus_setzen)
            self.palette.verbindung_gewaehlt.connect(
                self.zeichenflaeche.verbindungsmodus_setzen
            )
            self.palette_dock = self._dock(
                "Formen", self.palette, Qt.DockWidgetArea.LeftDockWidgetArea
            )
        else:
            # Struktogramm/Entscheidungstabelle arbeiten nicht mit frei
            # platzierten Formen (Abschnitt 13.5) - sie bekommen ihre
            # eigenen Bedienelemente in Schritt 9/10.
            self.palette = None
            self.palette_dock = None

        self.eigenschaften = EigenschaftenPanel(self.zeichenflaeche)
        self.eigenschaften_dock = self._dock(
            "Eigenschaften", self.eigenschaften, Qt.DockWidgetArea.RightDockWidgetArea
        )

    def _dock(self, titel: str, inhalt: QWidget, bereich: Qt.DockWidgetArea) -> QDockWidget:
        dock = QDockWidget(titel, self)
        dock.setObjectName(titel)
        dock.setWidget(inhalt)
        self.addDockWidget(bereich, dock)
        return dock

    def _stil_uebertragen(self) -> None:
        """„Format → Stil übertragen“ (Abschnitt 13.3): erster Aufruf
        merkt sich die Vorlage, der zweite überträgt sie auf die dann
        ausgewählte Form."""
        aktuell = self.zeichenflaeche.ausgewaehlte_form
        if aktuell is None:
            self.statusBar().showMessage("Keine Form ausgewählt.", 3000)
            return
        vorlage = getattr(self, "_stil_vorlage", None)
        if vorlage is None or vorlage is aktuell:
            self._stil_vorlage = aktuell
            name = (aktuell.get("text") or {}).get("name") or aktuell["kind"]
            self.statusBar().showMessage(
                f"Stil von „{name}“ gemerkt – jetzt Zielform auswählen und erneut aufrufen.",
                5000,
            )
            return

        self.eigenschaften.stil_uebertragen(vorlage, aktuell)
        self._stil_vorlage = None
        self.statusBar().showMessage("Stil übertragen.", 3000)

    def _bei_auswahl(self, form: dict | None) -> None:
        self.eigenschaften.aktualisieren()
        self._statusleiste_aktualisieren()

    def _bei_aenderung(self) -> None:
        self.eigenschaften.aktualisieren()
        self._geaendert = True
        self._titel_setzen()
        self._statusleiste_aktualisieren()

    # -- Aufbau ---------------------------------------------------------

    def _menues_aufbauen(self) -> None:
        for menue_name, eintraege in _MENUES.items():
            menue = self.menuBar().addMenu(menue_name)
            self._menues[menue_name] = menue
            for beschriftung, aktiv in eintraege:
                aktion = menue.addAction(beschriftung)
                aktion.setEnabled(aktiv)
                self.aktionen[f"{menue_name}/{beschriftung}"] = aktion

        self._stilvorlagen_menue_aufbauen()
        self._ansicht_schalter_aufbauen()

        self.aktionen["Datei/Speichern"].triggered.connect(self.speichern)
        self.aktionen["Datei/Speichern unter …"].triggered.connect(self.speichern_unter)
        self.aktionen["Datei/Schließen"].triggered.connect(self.close)

        # Tastenkürzel doppelt zur Zeichenfläche: dort greifen sie nur
        # bei Fokus auf der Fläche, über das Menü immer im Fenster.
        for pfad, kuerzel, rueckruf in (
            ("Bearbeiten/Rückgängig", "Ctrl+Z", lambda: self.zeichenflaeche.rueckgaengig()),
            ("Bearbeiten/Wiederholen", "Ctrl+Shift+Z", lambda: self.zeichenflaeche.wiederholen()),
            ("Bearbeiten/Duplizieren", "Ctrl+D", lambda: self.zeichenflaeche.duplizieren()),
            ("Bearbeiten/Löschen", "Del", lambda: self.zeichenflaeche.loeschen()),
            ("Datei/Speichern", "Ctrl+S", None),
            ("Format/Stil übertragen", "Ctrl+Shift+V", self._stil_uebertragen),
        ):
            aktion = self.aktionen[pfad]
            aktion.setShortcut(kuerzel)
            if rueckruf is not None:
                aktion.triggered.connect(rueckruf)

    def _stilvorlagen_menue_aufbauen(self) -> None:
        """„Format → Stilvorlage“ als Untermenü mit den drei Vorlagen aus
        Abschnitt 13.6. Bewusst pro Diagramm und **unabhängig vom
        IDE-Theme**: ein im dunklen Theme gezeichnetes Diagramm soll
        trotzdem als Schwarz-Weiß-Abgabe gedruckt werden können."""
        eintrag = self.aktionen["Format/Stilvorlage …"]
        untermenue = QMenu("Stilvorlage", self)
        gruppe = QActionGroup(self)
        gruppe.setExclusive(True)

        self.stil_aktionen: dict[str, object] = {}
        for name, beschriftung in BESCHRIFTUNGEN.items():
            aktion = untermenue.addAction(beschriftung)
            aktion.setCheckable(True)
            aktion.setChecked(name == self.diagramm.stil)
            aktion.triggered.connect(lambda _=False, n=name: self.stil_setzen(n))
            gruppe.addAction(aktion)
            self.stil_aktionen[name] = aktion

        eintrag.setMenu(untermenue)

    def stil_setzen(self, name: str) -> None:
        """Stilvorlage des ganzen Diagramms wechseln – rückgängig machbar
        wie jede andere Änderung."""
        if name == self.diagramm.stil:
            return
        self.zeichenflaeche.kommandos.ausfuehren(
            WerteKommando(self.diagramm.daten, {"style": name})
        )
        self.stil_aktionen[name].setChecked(True)
        self.zeichenflaeche.update()
        self._bei_aenderung()

    def _ansicht_schalter_aufbauen(self) -> None:
        """Raster, Seitenränder und Layout-Hinweise sind Ein/Aus-Schalter.
        Die Hinweise lassen sich wie beim Design-Prüfer (M7) abschalten –
        sie melden nur, blockieren nie."""
        for pfad, attribut in (
            ("Ansicht/Raster", "raster_sichtbar"),
            ("Ansicht/Seitenränder", "seitenrand_sichtbar"),
            ("Ansicht/Layout-Hinweise", "hinweise_sichtbar"),
        ):
            aktion = self.aktionen[pfad]
            aktion.setCheckable(True)
            aktion.setChecked(getattr(self.zeichenflaeche, attribut, True))
            aktion.toggled.connect(
                lambda an, a=attribut: self._ansicht_umschalten(a, an)
            )

    def _ansicht_umschalten(self, attribut: str, an: bool) -> None:
        setattr(self.zeichenflaeche, attribut, an)
        self.zeichenflaeche.hinweise_aktualisieren()
        self.zeichenflaeche.update()
        self._statusleiste_aktualisieren()

    def menue(self, name: str) -> QMenu:
        return self._menues[name]

    def _titel_setzen(self) -> None:
        markierung = "*" if self._geaendert else ""
        self.setWindowTitle(
            f"{markierung}{self.diagramm.pfad.name} – Diagramm-Editor – Natter"
        )

    def _statusleiste_aktualisieren(self) -> None:
        """Statusleiste nach Abschnitt 13.2 (Auswahl, Raster, Einrasten,
        Seitenformat, Stilvorlage)."""
        seite = self.diagramm.daten["page"]
        ausrichtung = "quer" if seite["orientation"] == "landscape" else "hoch"
        anzahl = len(self.diagramm.daten.get("shapes", []))
        ausgewaehlt = getattr(self.zeichenflaeche, "ausgewaehlte_form", None)
        auswahl = (
            f"{(ausgewaehlt.get('text') or {}).get('name', ausgewaehlt['kind'])} ausgewählt"
            if ausgewaehlt
            else f"{anzahl} Formen"
        )
        hinweise = getattr(self.zeichenflaeche, "hinweise", [])
        hinweis_text = (
            f"  │  {len(hinweise)} Layout-Hinweis" + ("e" if len(hinweise) != 1 else "")
            if hinweise
            else ""
        )
        self.statusBar().showMessage(
            f"{auswahl}  │  Raster 8 px  │  Einrasten ein  │  "
            f"{seite['size']} {ausrichtung}  │  Stil: {self.diagramm.stil}{hinweis_text}"
        )
        # Die Meldungen selbst als Tooltip: eine Form kann außerhalb des
        # sichtbaren Ausschnitts liegen, dann wäre ihr Warnrahmen allein
        # nicht zu sehen und die Zahl in der Statusleiste nicht zu
        # erklären.
        self.statusBar().setToolTip(
            "\n".join(hinweis.meldung for hinweis in hinweise) if hinweise else ""
        )

    # -- Datei ----------------------------------------------------------

    def speichern(self) -> None:
        self.diagramm.speichern()
        self._geaendert = False
        self._titel_setzen()
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
        self._geaendert = False
        self._titel_setzen()
        return self.diagramm.pfad
