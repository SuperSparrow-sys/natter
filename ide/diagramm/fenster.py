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

from PySide6.QtCore import QSettings, QSize, Qt
from PySide6.QtGui import QActionGroup, QPageLayout, QPainter
from PySide6.QtPrintSupport import QPrinter, QPrintPreviewDialog
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QFileDialog,
    QMainWindow,
    QMenu,
    QScrollArea,
    QWidget,
)

from ide.assets import symbol
from ide.diagramm.bloecke import alle_bloecke
from ide.diagramm.canvas import DiagrammCanvas
from ide.diagramm.codefenster import CodeFenster, CodeOptionenDialog, in_datei_schreiben
from ide.diagramm.datei import Diagramm
from ide.diagramm.eigenschaften import EigenschaftenPanel
from ide.diagramm.export import (
    als_pdf,
    als_png,
    als_svg,
    auf_seite_zeichnen,
    in_zwischenablage,
)
from ide.diagramm.exportdialog import PngDialog, PngEinstellungen
from ide.diagramm.formen import formen_fuer
from ide.diagramm.klassen_code import diagramm_als_python
from ide.diagramm.kommandos import WerteKommando
from ide.diagramm.palette import FormenPalette
from ide.diagramm.stil import BESCHRIFTUNGEN
from ide.diagramm.struktogramm import BLOCK_BESCHRIFTUNGEN
from ide.diagramm.struktogramm_canvas import StruktogrammCanvas
from ide.diagramm.struktogramm_code import als_python as struktogramm_als_python
from ide.diagramm.struktogramm_palette import BlockPalette
from ide.diagramm.tabelle import regelanzahl
from ide.diagramm.tabelle_canvas import TabellenCanvas
from ide.diagramm.uml_modell import formname
from ide.pruefungsmodus import GESPERRT_HINWEIS, restzeit_text
from ide.pruefungsmodus import laeuft as pruefungsmodus_laeuft
from ide.shell.theme import ide_qss_erzeugen

#: Menüaufbau aus Abschnitt 13.2. `True` = in diesem Schritt bereits
#: umgesetzt und aktiv, `False` = angelegt, aber ausgegraut.
_MENUES: dict[str, tuple[tuple[str, bool], ...]] = {
    "Datei": (
        ("Speichern", True),
        ("Speichern unter …", True),
        ("Exportieren …", True),
        ("Drucken …", True),
        ("Schließen", True),
    ),
    "Bearbeiten": (
        ("Rückgängig", True),
        ("Wiederholen", True),
        ("Ausschneiden", True),
        ("Als Bild kopieren", True),
        ("Kopieren", True),
        ("Einfügen", True),
        ("Duplizieren", True),
        ("Löschen", True),
        ("Alles auswählen", True),
    ),
    "Ansicht": (
        ("Zoom vergrößern", True),
        ("Zoom verkleinern", True),
        ("Alles anzeigen", True),
        ("Zoom 100 %", True),
        ("Raster", True),
        ("Lineale", False),
        ("Hilfslinien", False),
        ("Minimap", False),
        ("Seitenränder", True),
        ("Layout-Hinweise", True),
    ),
    "Anordnen": (
        ("Ausrichten", True),
        ("Verteilen", True),
        ("Gleiche Größe", True),
        ("In den Vordergrund", True),
        ("In den Hintergrund", True),
        ("Gruppieren", True),
        ("Gruppierung aufheben", True),
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

#: Einträge, die kein Befehl sind, sondern ein Untermenü aufmachen
#: (Teilschritt 3b). Die Werte sind (Beschriftung, Argument) – das
#: Argument geht unverändert an `ausrichten()`, `verteilen()` bzw.
#: `gleiche_groesse()` der Zeichenfläche.
_UNTERMENUES: dict[str, tuple[tuple[str, str], ...]] = {
    "Anordnen/Ausrichten": (
        ("Linksbündig", "links"),
        ("Rechtsbündig", "rechts"),
        ("Oben", "oben"),
        ("Unten", "unten"),
        ("Senkrecht mittig", "senkrechte_mitte"),
        ("Waagerecht mittig", "waagerechte_mitte"),
    ),
    "Anordnen/Verteilen": (
        ("Waagerecht", "waagerecht"),
        ("Senkrecht", "senkrecht"),
    ),
    "Anordnen/Gleiche Größe": (
        ("Breite", "breite"),
        ("Höhe", "hoehe"),
        ("Breite und Höhe", "beide"),
    ),
}

#: Werkzeugleiste des Diagramm-Editors (M11, Abschnitt 1): die Befehle,
#: die man beim Zeichnen dauernd braucht. Jeder Eintrag ist der Pfad
#: einer Aktion, die es **schon im Menü gibt** – die Leiste hängt
#: dieselbe `QAction` noch einmal auf, statt den Befehl ein zweites Mal
#: zu verdrahten (Abschnitt 7.3: „eine Aktion = Menüeintrag +
#: Werkzeugleisten-Button … nur einmal implementiert“). `None` ist eine
#: Trennlinie.
_WERKZEUGLEISTE: tuple[tuple[str, str] | None, ...] = (
    ("Datei/Speichern", "speichern"),
    None,
    ("Bearbeiten/Rückgängig", "rueckgaengig"),
    ("Bearbeiten/Wiederholen", "wiederholen"),
    ("Bearbeiten/Löschen", "loeschen"),
    None,
    ("Ansicht/Zoom vergrößern", "zoom_groesser"),
    ("Ansicht/Zoom verkleinern", "zoom_kleiner"),
    ("Ansicht/Alles anzeigen", "alles_anzeigen"),
    ("Ansicht/Raster", "raster"),
)

#: Zusatzmenü, das nur die Entscheidungstabelle bekommt
#: (Abschnitt 13.5: Spalten und Zeilen hinzufügen/entfernen/verschieben).
_TABELLENMENUE = (
    "Bedingung hinzufügen",
    "Aktion hinzufügen",
    "Zeile entfernen",
    "Regel hinzufügen",
    "Regel entfernen",
    "Regel nach links",
    "Regel nach rechts",
)


class DiagrammFenster(QMainWindow):
    def __init__(self, diagramm: Diagramm) -> None:
        super().__init__()
        self.diagramm = diagramm
        self._geaendert = False
        self._drucker: QPrinter | None = None
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
        """Aufteilung nach Abschnitt 13.2: Palette links, Zeichenfläche
        in der Mitte, Eigenschaften rechts. Welche Fläche und welche
        Palette das sind, hängt am Diagrammtyp – ein Struktogramm hat
        keine frei platzierten Formen, sondern einen Blockbaum
        (Abschnitt 13.5)."""
        if self.diagramm.typ == "struktogramm":
            self.zeichenflaeche = StruktogrammCanvas(self.diagramm)
            self.palette = BlockPalette()
            self.palette.block_gewaehlt.connect(self.zeichenflaeche.einfuegemodus_setzen)
            self.eigenschaften = None
        elif self.diagramm.typ == "entscheidungstabelle":
            # Eine Tabelle wird direkt in sich bearbeitet - eine Palette
            # gaebe es nichts hineinzuziehen (Abschnitt 13.5).
            self.zeichenflaeche = TabellenCanvas(self.diagramm)
            self.palette = None
            self.eigenschaften = None
        else:
            self.zeichenflaeche = DiagrammCanvas(self.diagramm)
            self.palette = (
                FormenPalette(self.diagramm.typ) if formen_fuer(self.diagramm.typ) else None
            )
            if self.palette is not None:
                self.palette.form_gewaehlt.connect(
                    self.zeichenflaeche.platzierungsmodus_setzen
                )
                self.palette.verbindung_gewaehlt.connect(
                    self.zeichenflaeche.verbindungsmodus_setzen
                )
            self.eigenschaften = EigenschaftenPanel(self.zeichenflaeche)

        self.zeichenflaeche.auswahl_geaendert.connect(self._bei_auswahl)
        self.zeichenflaeche.geaendert.connect(self._bei_aenderung)
        if hasattr(self.zeichenflaeche, "zoom_geaendert"):
            self.zeichenflaeche.zoom_geaendert.connect(
                lambda _: self._statusleiste_aktualisieren()
            )

        # Die Zeichenfläche steckt in einem Rollbereich: ein A4-Blatt ist
        # breiter als die meisten Fenster, und ein Struktogramm wächst
        # nach unten aus jedem Fenster heraus. Ohne ihn war alles
        # außerhalb des sichtbaren Ausschnitts schlicht nicht erreichbar
        # (vom Nutzer gemeldet). `setWidgetResizable(True)` zusammen mit
        # der Mindestgröße der Fläche heißt: passt der Inhalt, füllt die
        # Fläche das Fenster; passt er nicht, erscheinen Rollbalken.
        self.rollbereich = QScrollArea()
        self.rollbereich.setWidget(self.zeichenflaeche)
        self.rollbereich.setWidgetResizable(True)
        self.rollbereich.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCentralWidget(self.rollbereich)

        # Ein Struktogramm hat keine "Formen", sondern Bloecke - der
        # Titel des Docks soll das auch sagen.
        palettentitel = "Blöcke" if self.diagramm.typ == "struktogramm" else "Formen"

        self.palette_dock = (
            self._dock(palettentitel, self.palette, Qt.DockWidgetArea.LeftDockWidgetArea)
            if self.palette is not None
            else None
        )
        self.eigenschaften_dock = (
            self._dock(
                "Eigenschaften", self.eigenschaften, Qt.DockWidgetArea.RightDockWidgetArea
            )
            if self.eigenschaften is not None
            else None
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
        aktuell = getattr(self.zeichenflaeche, "ausgewaehlte_form", None)
        if aktuell is None:
            self.statusBar().showMessage("Keine Form ausgewählt.", 3000)
            return
        vorlage = getattr(self, "_stil_vorlage", None)
        if vorlage is None or vorlage is aktuell:
            self._stil_vorlage = aktuell
            name = formname(aktuell) or aktuell["kind"]
            self.statusBar().showMessage(
                f"Stil von „{name}“ gemerkt – jetzt Zielform auswählen und erneut aufrufen.",
                5000,
            )
            return

        self.eigenschaften.stil_uebertragen(vorlage, aktuell)
        self._stil_vorlage = None
        self.statusBar().showMessage("Stil übertragen.", 3000)

    def _bei_auswahl(self, form: dict | None) -> None:
        if self.eigenschaften is not None:
            self.eigenschaften.aktualisieren()
        self._statusleiste_aktualisieren()

    def _bei_aenderung(self) -> None:
        if self.eigenschaften is not None:
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
                pfad = f"{menue_name}/{beschriftung}"
                if pfad in _UNTERMENUES:
                    self._untermenue_aufbauen(menue, pfad, aktiv)
                    continue
                aktion = menue.addAction(beschriftung)
                aktion.setEnabled(aktiv)
                self.aktionen[pfad] = aktion

        if self.diagramm.typ == "entscheidungstabelle":
            self._tabellenmenue_aufbauen()
        if self.diagramm.typ in ("class", "struktogramm"):
            self._quelltextmenue_aufbauen()
        self._stilvorlagen_menue_aufbauen()
        self._ansicht_schalter_aufbauen()

        # Achtung: `QAction.triggered` schickt immer ein `checked`-Flag
        # mit. Eine Methode, deren erster Parameter optional ist, bekommt
        # dadurch `False` statt `None` hineingereicht – `exportieren`
        # stürzte real mit „argument should be a str or an os.PathLike
        # object … not 'bool'“ ab. Deshalb hier überall ein Lambda ohne
        # Parameter, das dieses Flag verschluckt.
        self.aktionen["Datei/Speichern"].triggered.connect(lambda: self.speichern())
        self.aktionen["Datei/Speichern unter …"].triggered.connect(
            lambda: self.speichern_unter()
        )
        self.aktionen["Datei/Exportieren …"].triggered.connect(lambda: self.exportieren())
        self.aktionen["Datei/Drucken …"].triggered.connect(lambda: self.drucken())
        self.aktionen["Datei/Schließen"].triggered.connect(lambda: self.close())
        self.aktionen["Bearbeiten/Als Bild kopieren"].triggered.connect(
            self.als_bild_kopieren
        )

        # Tastenkürzel doppelt zur Zeichenfläche: dort greifen sie nur
        # bei Fokus auf der Fläche, über das Menü immer im Fenster.
        for pfad, kuerzel, rueckruf in (
            ("Bearbeiten/Rückgängig", "Ctrl+Z", lambda: self.zeichenflaeche.rueckgaengig()),
            ("Bearbeiten/Wiederholen", "Ctrl+Shift+Z", lambda: self.zeichenflaeche.wiederholen()),
            ("Bearbeiten/Duplizieren", "Ctrl+D", lambda: self.zeichenflaeche.duplizieren()),
            ("Bearbeiten/Löschen", "Del", lambda: self.zeichenflaeche.loeschen()),
            ("Datei/Speichern", "Ctrl+S", None),
            ("Format/Stil übertragen", "Ctrl+Shift+V", self._stil_uebertragen),
            ("Ansicht/Zoom vergrößern", "Ctrl++", lambda: self._zoomen(1.25)),
            ("Ansicht/Zoom verkleinern", "Ctrl+-", lambda: self._zoomen(1 / 1.25)),
            ("Ansicht/Alles anzeigen", "Ctrl+0", self.alles_anzeigen),
            ("Ansicht/Zoom 100 %", "Ctrl+1", lambda: self._zoom_setzen(1.0)),
        ):
            aktion = self.aktionen[pfad]
            aktion.setShortcut(kuerzel)
            if rueckruf is not None:
                aktion.triggered.connect(rueckruf)

        self._anordnen_verdrahten()
        self._menue_an_typ_anpassen()
        self._werkzeugleiste_aufbauen()

    def _werkzeugleiste_aufbauen(self) -> None:
        """Werkzeugleiste aus `_WERKZEUGLEISTE`.

        Bewusst dieselbe Machart wie die Leiste der Haupt-IDE
        (`ide/shell/hauptfenster.py`): 18 px Symbole, nicht verschiebbar,
        und jeder Knopf ist **dieselbe** `QAction` wie der Menüeintrag.
        Dadurch erbt er Tastenkürzel, Ein/Aus-Zustand und – beim Raster –
        auch das Häkchen, ohne dass irgendetwas zweimal dasteht. Was der
        Diagrammtyp nicht kann, ist im Menü ausgegraut und damit auch
        hier (`_menue_an_typ_anpassen` läuft vorher).
        """
        self.werkzeugleiste = self.addToolBar("Werkzeugleiste")
        self.werkzeugleiste.setObjectName("Werkzeugleiste")
        self.werkzeugleiste.setMovable(False)
        self.werkzeugleiste.setIconSize(QSize(18, 18))
        for eintrag in _WERKZEUGLEISTE:
            if eintrag is None:
                self.werkzeugleiste.addSeparator()
                continue
            pfad, symbolname = eintrag
            aktion = self.aktionen[pfad]
            aktion.setIcon(symbol(symbolname))
            self.werkzeugleiste.addAction(aktion)

    def _untermenue_aufbauen(self, menue, pfad: str, aktiv: bool) -> None:
        """Baut ein Untermenü wie „Anordnen → Ausrichten".

        Die Einzelbefehle bekommen denselben Pfad mit angehängtem
        Argument (`Anordnen/Ausrichten/links`) – so findet sie der Test,
        der jeden aktiven Menüeintrag auslöst, genau wie jede andere
        Aktion auch.
        """
        name = pfad.split("/", 1)[1]
        untermenue = menue.addMenu(name)
        untermenue.setEnabled(aktiv)
        self._menues[pfad] = untermenue
        for beschriftung, argument in _UNTERMENUES[pfad]:
            aktion = untermenue.addAction(beschriftung)
            aktion.setEnabled(aktiv)
            self.aktionen[f"{pfad}/{argument}"] = aktion

    def _anordnen_verdrahten(self) -> None:
        """Verbindet Bearbeiten und Anordnen mit der Zeichenfläche.

        Alles über parameterlose Lambdas: `QAction.triggered` schickt
        immer ein `checked`-Flag mit, das sonst als erstes Argument
        ankäme (in M9 real abgestürzt).
        """
        flaeche = self.zeichenflaeche
        if not hasattr(flaeche, "ausrichten"):
            # Struktogramm und Entscheidungstabelle kennen keine Formen
            for pfad, aktion in self.aktionen.items():
                if pfad.startswith("Anordnen/") or pfad in (
                    "Bearbeiten/Ausschneiden",
                    "Bearbeiten/Kopieren",
                    "Bearbeiten/Einfügen",
                    "Bearbeiten/Alles auswählen",
                ):
                    aktion.setEnabled(False)
            for pfad, untermenue in self._menues.items():
                if pfad.startswith("Anordnen/"):
                    untermenue.setEnabled(False)
            return

        for pfad, kuerzel, rueckruf in (
            ("Bearbeiten/Ausschneiden", "Ctrl+X", flaeche.ausschneiden),
            ("Bearbeiten/Kopieren", "Ctrl+C", flaeche.kopieren),
            ("Bearbeiten/Einfügen", "Ctrl+V", flaeche.einfuegen),
            ("Bearbeiten/Alles auswählen", "Ctrl+A", flaeche.alles_auswaehlen),
            ("Anordnen/In den Vordergrund", "Ctrl+Shift+Up", flaeche.nach_vorne),
            ("Anordnen/In den Hintergrund", "Ctrl+Shift+Down", flaeche.nach_hinten),
            ("Anordnen/Gruppieren", "Ctrl+G", flaeche.gruppieren),
            (
                "Anordnen/Gruppierung aufheben",
                "Ctrl+Shift+G",
                flaeche.gruppierung_aufheben,
            ),
        ):
            aktion = self.aktionen[pfad]
            aktion.setShortcut(kuerzel)
            aktion.triggered.connect(lambda *_, f=rueckruf: f())

        for pfad, methode in (
            ("Anordnen/Ausrichten", flaeche.ausrichten),
            ("Anordnen/Verteilen", flaeche.verteilen),
            ("Anordnen/Gleiche Größe", flaeche.gleiche_groesse),
        ):
            for _, argument in _UNTERMENUES[pfad]:
                self.aktionen[f"{pfad}/{argument}"].triggered.connect(
                    lambda *_, f=methode, a=argument: f(a)
                )

    def _menue_an_typ_anpassen(self) -> None:
        """Was die Zeichenflaeche dieses Diagrammtyps nicht kann, wird
        ausgegraut statt vorgetaeuscht – ein Struktogramm kennt keine
        Formen, also auch kein Duplizieren, keine Hilfslinien und kein
        Uebertragen von Fuellfarben (Abschnitt 13.5)."""
        for pfad, faehigkeit in (
            ("Ansicht/Zoom vergrößern", "zoom_setzen"),
            ("Ansicht/Zoom verkleinern", "zoom_setzen"),
            ("Ansicht/Alles anzeigen", "alles_anzeigen"),
            ("Ansicht/Zoom 100 %", "zoom_setzen"),
            ("Bearbeiten/Duplizieren", "duplizieren"),
            ("Format/Stil übertragen", "ausgewaehlte_form"),
            ("Ansicht/Raster", "raster_sichtbar"),
            ("Ansicht/Seitenränder", "seitenrand_sichtbar"),
            ("Ansicht/Layout-Hinweise", "hinweise_sichtbar"),
        ):
            if not hasattr(self.zeichenflaeche, faehigkeit):
                self.aktionen[pfad].setEnabled(False)

    def _tabellenmenue_aufbauen(self) -> None:
        """Eigenes Menü „Tabelle“ – eine Entscheidungstabelle wird nicht
        über eine Palette gefüllt, sondern über Zeilen und Spalten."""
        # Vor "Hilfe" einhaengen - "Hilfe" gehoert ans Ende der
        # Menueleiste, nicht mittendrin (im Screenshot aufgefallen).
        menue = QMenu("Tabelle", self)
        self.menuBar().insertMenu(self._menues["Hilfe"].menuAction(), menue)
        self._menues["Tabelle"] = menue
        flaeche = self.zeichenflaeche
        rueckrufe = {
            "Bedingung hinzufügen": lambda: flaeche.zeile_hinzufuegen("conditions"),
            "Aktion hinzufügen": lambda: flaeche.zeile_hinzufuegen("actions"),
            "Zeile entfernen": flaeche.loeschen,
            "Regel hinzufügen": lambda: flaeche.regel_hinzufuegen(),
            "Regel entfernen": lambda: flaeche.regel_entfernen(),
            "Regel nach links": lambda: self._regel_verschieben(-1),
            "Regel nach rechts": lambda: self._regel_verschieben(1),
        }
        for beschriftung in _TABELLENMENUE:
            aktion = menue.addAction(beschriftung)
            aktion.triggered.connect(rueckrufe[beschriftung])
            self.aktionen[f"Tabelle/{beschriftung}"] = aktion

    def _regel_verschieben(self, richtung: int) -> None:
        zelle = self.zeichenflaeche.ausgewaehlte_zelle
        if zelle is None or zelle.spalte < 0:
            self.statusBar().showMessage("Keine Regel ausgewählt.", 3000)
            return
        self.zeichenflaeche.regel_verschieben(zelle.spalte, zelle.spalte + richtung)

    # -- Zoom ------------------------------------------------------------

    def _zoomen(self, faktor: float) -> None:
        if hasattr(self.zeichenflaeche, "zoom_aendern"):
            self.zeichenflaeche.zoom_aendern(faktor)

    def _zoom_setzen(self, wert: float) -> None:
        if hasattr(self.zeichenflaeche, "zoom_setzen"):
            self.zeichenflaeche.zoom_setzen(wert)

    def alles_anzeigen(self) -> None:
        """„Ansicht → Alles anzeigen“ (Strg+0): so weit herauszoomen, dass
        alles ins Sichtfenster passt."""
        if not hasattr(self.zeichenflaeche, "alles_anzeigen"):
            return
        sicht = self.rollbereich.viewport()
        self.zeichenflaeche.alles_anzeigen(sicht.width(), sicht.height())

    def _quelltextmenue_aufbauen(self) -> None:
        """„Quelltext → Erzeugen …“ (M9 Schritte 13 und 14). Vor „Hilfe“,
        das gehört ans Ende der Leiste."""
        menue = QMenu("Quelltext", self)
        self.menuBar().insertMenu(self._menues["Hilfe"].menuAction(), menue)
        self._menues["Quelltext"] = menue
        aktion = menue.addAction("Erzeugen …")
        # Im Pruefungsmodus gesperrt (M11, Abschnitt 6): aus einem
        # Klassendiagramm oder einem Struktogramm Python erzeugen zu
        # lassen waere in einer Leistungssituation die halbe Aufgabe.
        # Sichtbar bleibt der Eintrag trotzdem - ein spurlos
        # verschwundener Menueeintrag waere verwirrender als ein
        # erklaerter.
        if pruefungsmodus_laeuft():
            aktion.setEnabled(False)
            aktion.setToolTip(GESPERRT_HINWEIS)
            menue.setToolTipsVisible(True)
        # Nicht Strg+G: das gehört seit Teilschritt 3b dem Gruppieren,
        # und Strg+G zum Gruppieren kennt jedes Zeichenprogramm. Zwei
        # aktive Aktionen auf derselben Taste lösen in Qt gar nichts
        # mehr aus („Ambiguous shortcut overload“).
        aktion.setShortcut("Ctrl+Shift+E")
        aktion.triggered.connect(lambda: self.quelltext_erzeugen())
        self.aktionen["Quelltext/Erzeugen …"] = aktion

    def quelltext_code(self, umfang: str = "alles") -> str:
        """Der erzeugte Quelltext – ohne jede Oberfläche, damit sich das
        einzeln prüfen lässt."""
        auswahl = None
        if umfang == "auswahl":
            auswahl = getattr(self.zeichenflaeche, "ausgewaehlte_form", None) or getattr(
                self.zeichenflaeche, "ausgewaehlter_block", None
            )
        if self.diagramm.typ == "struktogramm":
            return struktogramm_als_python(self.diagramm.daten, auswahl).text
        return diagramm_als_python(self.diagramm.daten, auswahl)

    def quelltext_erzeugen(
        self, ziel: str | None = None, umfang: str | None = None, pfad: Path | None = None
    ):
        """„Quelltext → Erzeugen …“. Ohne Angaben fragt ein Dialog nach
        Ziel und Umfang; in Tests werden beide direkt übergeben."""
        if ziel is None or umfang is None:
            dialog = CodeOptionenDialog(
                self,
                "Umfang" if self.diagramm.typ == "class" else "Ausschnitt",
            )
            if dialog.exec() != CodeOptionenDialog.DialogCode.Accepted:
                return None
            ziel, umfang = dialog.merken()

        quelltext = self.quelltext_code(umfang)
        if not quelltext.strip():
            self.statusBar().showMessage("Nichts zu erzeugen.", 3000)
            return None

        if ziel == "datei":
            vorschlag = pfad or (
                self.diagramm.pfad.parent.parent
                / "units"
                / f"u_{self.diagramm.pfad.stem.lower()}.py"
            )
            geschrieben = in_datei_schreiben(
                quelltext, vorschlag, self, fragen=pfad is None
            )
            if geschrieben is not None:
                self.statusBar().showMessage(f"Geschrieben: {geschrieben.name}", 4000)
            return geschrieben

        fenster = CodeFenster(quelltext, f"Quelltext – {self.diagramm.pfad.stem}", self)
        if pfad is None:
            fenster.exec()
        return fenster

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
            if not hasattr(self.zeichenflaeche, attribut):
                continue
            aktion = self.aktionen[pfad]
            aktion.setCheckable(True)
            aktion.setChecked(getattr(self.zeichenflaeche, attribut))
            aktion.toggled.connect(
                lambda an, a=attribut: self._ansicht_umschalten(a, an)
            )

    def _ansicht_umschalten(self, attribut: str, an: bool) -> None:
        setattr(self.zeichenflaeche, attribut, an)
        if hasattr(self.zeichenflaeche, "hinweise_aktualisieren"):
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

    def _auswahltext(self) -> str:
        """Linker Teil der Statusleiste – beim Klassendiagramm die Form,
        beim Struktogramm der Block."""
        if self.diagramm.typ == "entscheidungstabelle":
            zeilen = len(self.diagramm.daten.get("conditions") or []) + len(
                self.diagramm.daten.get("actions") or []
            )
            return f"{zeilen} Zeilen  │  {regelanzahl(self.diagramm.daten)} Regeln"

        if self.diagramm.typ == "struktogramm":
            block = self.zeichenflaeche.ausgewaehlter_block
            if block is not None:
                return f"{BLOCK_BESCHRIFTUNGEN.get(block.get('kind'), 'Block')} ausgewählt"
            anzahl = len(alle_bloecke(self.diagramm.daten)) - 1  # ohne die Wurzel
            return f"{anzahl} Blöcke"

        auswahl = getattr(self.zeichenflaeche, "auswahl", ())
        if len(auswahl) > 1:
            return f"{len(auswahl)} Formen ausgewählt"
        ausgewaehlt = getattr(self.zeichenflaeche, "ausgewaehlte_form", None)
        if ausgewaehlt:
            return f"{formname(ausgewaehlt) or ausgewaehlt['kind']} ausgewählt"
        return f"{len(self.diagramm.daten.get('shapes', []))} Formen"

    def _statusleiste_aktualisieren(self) -> None:
        """Statusleiste nach Abschnitt 13.2 (Auswahl, Raster, Einrasten,
        Seitenformat, Stilvorlage)."""
        seite = self.diagramm.daten["page"]
        ausrichtung = "quer" if seite["orientation"] == "landscape" else "hoch"
        auswahl = self._auswahltext()
        hinweise = getattr(self.zeichenflaeche, "hinweise", [])
        hinweis_text = (
            f"  │  {len(hinweise)} Layout-Hinweis" + ("e" if len(hinweise) != 1 else "")
            if hinweise
            else ""
        )
        raster = (
            "Raster 8 px  │  Einrasten ein  │  "
            if hasattr(self.zeichenflaeche, "raster_sichtbar")
            else ""
        )
        pruefung = restzeit_text()
        pruefungsteil = f"  │  {pruefung}" if pruefung else ""
        zoom = getattr(self.zeichenflaeche, "zoom", None)
        if zoom is not None:
            raster += f"Zoom {round(zoom * 100)} %  │  "
        self.statusBar().showMessage(
            f"{auswahl}  │  {raster}"
            f"{seite['size']} {ausrichtung}  │  Stil: {self.diagramm.stil}"
            f"{hinweis_text}{pruefungsteil}"
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

    # -- Export und Drucken ---------------------------------------------

    def exportieren(
        self, pfad: Path | None = None, png: PngEinstellungen | None = None
    ) -> Path | None:
        """„Datei → Exportieren …“ (Abschnitt 13.2). Das Format ergibt
        sich aus der gewählten Endung – ein Dialog weniger als eine
        eigene Formatauswahl. Nur bei PNG folgt eine Rückfrage nach
        Auflösung und Hintergrund; SVG und PDF sind auflösungsfrei. In
        Tests werden Pfad und Einstellungen direkt übergeben."""
        gefragt = pfad is not None
        if pfad is None:
            gewaehlt, _ = QFileDialog.getSaveFileName(
                self,
                "Diagramm exportieren",
                str(self.diagramm.pfad.with_suffix(".png")),
                "Bild (*.png);;Vektorgrafik (*.svg);;PDF (*.pdf)",
            )
            if not gewaehlt:
                return None
            pfad = Path(gewaehlt)

        pfad = Path(pfad)
        endung = pfad.suffix.lower()
        if endung not in (".png", ".svg", ".pdf"):
            self.statusBar().showMessage(
                f"Unbekanntes Exportformat „{pfad.suffix}“ – bitte .png, .svg oder .pdf.",
                5000,
            )
            return None

        if endung == ".png":
            if png is None and not gefragt:
                dialog = PngDialog(self)
                if dialog.exec() != PngDialog.DialogCode.Accepted:
                    return None
                png = dialog.einstellungen()
            png = png or PngEinstellungen()
            als_png(self.diagramm.daten, pfad, png.skalierung, png.transparent)
        elif endung == ".svg":
            als_svg(self.diagramm.daten, pfad)
        else:
            als_pdf(self.diagramm.daten, pfad)

        self.statusBar().showMessage(f"Exportiert nach {pfad.name}", 3000)
        return pfad

    def als_bild_kopieren(self) -> None:
        """Diagramm in die Zwischenablage, zum Einfügen in Word o. Ä.
        (Abschnitt 13.2)."""
        in_zwischenablage(self.diagramm.daten)
        self.statusBar().showMessage("Diagramm in die Zwischenablage kopiert.", 3000)

    def drucken(self, drucker: QPrinter | None = None) -> None:
        """„Datei → Drucken …“ mit Seitenvorschau (Abschnitt 13.2). Der
        Vorschaudialog zeichnet über denselben Rückruf wie der echte
        Druck, es kann also nichts auseinanderlaufen."""
        if drucker is None:
            vorschau = QPrintPreviewDialog(self._drucker_vorbereiten(), self)
            vorschau.setWindowTitle(f"Druckvorschau – {self.diagramm.pfad.name}")
            vorschau.paintRequested.connect(self._auf_drucker_zeichnen)
            vorschau.exec()
            return
        self._auf_drucker_zeichnen(drucker)

    def _drucker_vorbereiten(self) -> QPrinter:
        """Der **erste** `QPrinter` eines Prozesses lässt Windows alle
        Drucker samt Treibern durchsuchen; mit einem nicht erreichbaren
        Netzwerkdrucker dauert das real gemessen fast eine Minute, in
        der die Oberfläche steht. Deshalb: Sanduhr und eine Meldung,
        damit niemand denkt, Natter sei abgestürzt – und den fertigen
        Drucker merken, sodass jeder weitere Aufruf sofort kommt."""
        if getattr(self, "_drucker", None) is None:
            self.statusBar().showMessage("Drucker werden gesucht …")
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            QApplication.processEvents()
            try:
                self._drucker = QPrinter(QPrinter.PrinterMode.HighResolution)
            finally:
                QApplication.restoreOverrideCursor()
                self.statusBar().clearMessage()
                self._statusleiste_aktualisieren()

        seite = self.diagramm.daten.get("page") or {}
        self._drucker.setPageOrientation(
            QPageLayout.Orientation.Landscape
            if seite.get("orientation") == "landscape"
            else QPageLayout.Orientation.Portrait
        )
        return self._drucker

    def _auf_drucker_zeichnen(self, drucker: QPrinter) -> None:
        maler = QPainter(drucker)
        bereich = drucker.pageRect(QPrinter.Unit.DevicePixel)
        auf_seite_zeichnen(maler, self.diagramm.daten, bereich.width(), bereich.height())
        maler.end()
