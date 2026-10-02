"""HauptFenster: Grundgerüst des IDE-Hauptfensters.

Siehe README.md, Abschnitt 7.1, 7.4, 7.5. Menüleiste mit den
Menütiteln aus Abschnitt 7.2 (Einträge kommen über das Aktionsregister),
Docks für Explorer/Objektinspektor/Panels, zentrale Editor-Tabs,
Statusleiste. `projekt_oeffnen`/`datei_oeffnen` sind die Grundlage für
„Projekt öffnen …“/„Öffnen …“ (M2, Schritt 5).
"""

from __future__ import annotations

import contextlib
import json
import keyword
import os
import re
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import QByteArray, QEvent, QRect, QSettings, QSize, Qt, QTimer
from PySide6.QtGui import (
    QActionGroup,
    QCloseEvent,
    QColor,
    QCursor,
    QFont,
    QFontMetrics,
    QGuiApplication,
    QResizeEvent,
    QSessionManager,
    QTextCursor,
)
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDockWidget,
    QFileDialog,
    QHBoxLayout,
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
    QSizePolicy,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ide import dateistand
from ide.actions import Aktion, Aktionsregister
from ide.assets import symbol
from ide.atomar import atomar_schreiben, ordner_beschreibbar
from ide.codegen.design import PfmBeschaedigt, design_code_erzeugen, pfm_pruefen
from ide.database import DatenbankPanel
from ide.database.panel import transaktion_nachfragen
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
from ide.export.signatur import (
    WIEDER_FRAGEN,
    ZERT_NAME,
    abgelehnt_vermerk,
    rueckfrage_wieder_zulassen,
)
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
from ide.integritaet.start_pruefung import installation_pruefen, programmordner
from ide.lint import pruefen
from ide.palette import Komponentenpalette
from ide.palette.palette import TYP_ROLLE
from ide.papierkorb import in_den_papierkorb, papierkorb_verfuegbar
from ide.pfade import (
    beispielkopien_ordner,
    daten_ordner,
    dialog_startordner,
    einheitlicher_pfad,
    natter_ordner,
    vorlaeufig_entpackt,
)
from ide.project import Projekt, projekt_erzeugen, sicherung, sperre
from ide.project.neu_dialog import NeuesProjektDialog
from ide.project.projekt import ProjektdateiUngueltig, dateien_im_ordner
from ide.project.sicherung import ist_sicherung
from ide.prozess import Auftrag, auftrag_von, prozessbaum_beenden
from ide.run import erste_zeile_der_haupt_unit, projekt_pruefen, projekt_starten
from ide.run.ladeanzeige import (
    endmarke_zu,
    hat_sichtbares_fenster,
    lademarke_anlegen,
    lademarke_entfernen,
    lademarke_gesetzt,
)
from ide.run.pruefung import RuffFund
from ide.schema import (
    fehler_beschreiben,
    json_datei_lesen,
    schema_fehler,
)
from ide.shell import abmeldegrund
from ide.shell.explorer import PFAD_ROLLE, ProjektExplorer
from ide.shell.haltepunkte_ablage import (
    haltepunkte_laden,
    haltepunkte_speichern,
)
from ide.shell.hintergrund import (
    ZEILEN_GRENZE,
    AusgabeLeser,
    Hintergrundarbeit,
)
from ide.shell.quelltexteditor import SCHRIFTART_OPTIONEN, QuelltextEditor
from ide.shell.schnellauswahl import SchnellAuswahl
from ide.shell.startbild import (
    DateiGesperrt,
    RueckwegGescheitert,
    Startbild,
    aufgabe_kopieren,
    aufgabe_original,
    aufgabe_stand_merken,
    aufgabe_zuruecksetzen,
    beispiel_kopieren,
    beispiel_nach_inhalt,
    beispiel_original,
    beispiel_zuruecksetzen,
    beispielprojekte,
    ist_beispiel_original,
    neuer_aufgabenstand,
    vorhandene_aufgabenkopie,
    vorher_ordner,
    zuletzt_merken,
)
from ide.shell.suchen_dialog import SuchenErsetzenDialog
from ide.shell.tastenkuerzel import als_markdown as tastenkuerzel_als_markdown
from ide.shell.theme import basis_schriftgroesse, ide_qss_erzeugen
from ide.shell.vervollstaendigung import aufwaermen as vervollstaendigung_aufwaermen
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
from pcl.pruefungsmodus import GESPERRT_HINWEIS, restzeit_text
from pcl.pruefungsmodus import laeuft as pruefungsmodus_laeuft
from pcl.pruefungsmodus import starten as pruefungsmodus_starten
from pcl.theme import VORGABE_VARIABLE, theme_aufloesen

_BILD_ENDUNGEN = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp", ".svg"}
_HTML_ENDUNGEN = {".html", ".htm"}

#: Schlüssel in den Einstellungen: der Ordner, in dem zuletzt in einem
#: Datei-Dialog etwas gewählt wurde (Punkt 408).
_LETZTER_ORDNER = "dialoge/letzter_ordner"

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

#: Die Menütitel mit Zugriffstaste: Alt und der unterstrichene
#: Buchstabe öffnen das Menü, wie unter Windows üblich (Punkt 439).
#: Innerhalb der Menüleiste kommt kein Buchstabe zweimal vor.
#: `_menues` und `menue()` kennen die Titel ohne `&`.
MENUE_ZUGRIFF = {
    "Datei": "&Datei",
    "Bearbeiten": "&Bearbeiten",
    "Suchen": "&Suchen",
    "Ansicht": "&Ansicht",
    "Quelltext": "&Quelltext",
    "Projekt": "&Projekt",
    "Start": "S&tart",
    "Pakete": "Pa&kete",
    "Werkzeuge": "&Werkzeuge",
    "Fenster": "&Fenster",
    "Hilfe": "&Hilfe",
}

#: Gruppenzeilen, die debugpy unter die Variablen mischt.
_DEBUGPY_GRUPPEN = frozenset(
    {
        "special variables",
        "function variables",
        "class variables",
        "protected variables",
    }
)

PANEL_REITER = ("Meldungen", "Ausgabe", "Variablen", "Überwachen", "Aufrufstapel", "Tests")

#: Wie oft nachgesehen wird, ob das gestartete Programm inzwischen zu
#: Ende ist. Eine halbe Sekunde reicht: das Ergebnis steht danach im
#: Panel „Ausgabe“, niemand wartet darauf mit der Stoppuhr.
_LAUFZEIT_TAKT_MS = 500

#: So oft übernimmt das Panel „Ausgabe“ die inzwischen gelesenen
#: Zeilen eines Programms. Einzeln übernommen hielten ein paar
#: tausend `print()` Natter minutenlang an (Punkt 267); gebündelt
#: alle 50 ms sieht es trotzdem aus, als käme jede Zeile sofort.
_AUSGABE_TAKT_MS = 50

#: Höchstens so viele Zeilen hält das Panel „Ausgabe“. Darüber fallen
#: die ältesten weg, und eine Zeile ganz oben sagt, wie viele es waren.
#: Eine Endlosschleife mit `print()` füllte den Speicher sonst ohne
#: Ende.
AUSGABE_GRENZE = 5000

#: So steht eine offene Transaktion im Datenbank-Panel in der
#: Nachfrage vor dem Schließen, zwischen den ungespeicherten Dateien
#: (Punkt 276).
TRANSAKTION_EINTRAG = "Offene Transaktion im Datenbank-Panel"

#: Rolle der Hinweiszeile über weggefallene Ausgabezeilen; ihr Wert
#: ist die Zahl der weggefallenen Zeilen.
_WEGGEFALLEN_ROLLE = Qt.ItemDataRole.UserRole + 20

#: Takt der Ladeanzeige nach dem Start (Punkt 271). Eine Abfrage der
#: Fenster kostet wenige Millisekunden; viermal in der Sekunde reicht,
#: damit die Anzeige mit dem Fenster verschwindet.
_LADE_TAKT_MS = 250

#: So oft wird ungespeicherter Text in die Sicherung des Projekts
#: geschrieben (Punkt 344). Stürzt der Rechner ab oder fällt der Strom
#: aus, fehlen höchstens die letzten zwei Minuten.
_SICHERUNG_TAKT_MS = 2 * 60 * 1000

#: Nach so vielen Sekunden ohne Fenster und ohne Ausgabe gibt die
#: Ladeanzeige auf. Das Programm läuft dann zwar, zeigt aber nichts -
#: etwa, weil es auf etwas wartet oder kein Fenster öffnet. Eine
#: Anzeige, die ewig weiterzählt, sagt dann nichts Richtiges mehr.
_LADE_GRENZE_S = 120

#: Kurzhinweise zu den Reitern unten und zu den Docks (M11, Abschnitt 4).
#: „Aufrufstapel“ oder „Objektinspektor“ sagen einem Anfänger noch
#: nichts – und ein Fenster, dessen Zweck man raten muss, wird nicht
#: benutzt.
PANEL_HINWEISE = {
    "Meldungen": "Fehler und Hinweise aus der Prüfung vor dem Start",
    # „bei einem Programm mit Oberfläche": ein Konsolenprojekt
    # startet mit einem eigenen Fenster und ohne Rohr, seine
    # Zeilen stehen dort. Der Hinweis versprach das bis
    # September 2026 für jedes Programm.
    "Ausgabe": "Start und Ende - bei einem Programm mit Oberfläche auch, was es ausgibt",
    "Variablen": "Die Werte, während das Programm an einem Haltepunkt steht",
    "Überwachen": "Selbst gewählte Ausdrücke, bei jedem Halt neu ausgerechnet",
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

#: Mindesthöhe des Inhalts jedes Docks in Pixeln (Punkt 299).
_DOCK_MINDESTHOEHE = 60

#: Unter dieser Fensterhöhe in logischen Pixeln gilt die Höhe als
#: knapp, und der Objektinspektor bekommt die ganze rechte Seite
#: (Punkt 437). 1366 × 768 bei 100 % lässt einem maximierten Fenster
#: rund 690, 1920 × 1080 bei 100 % rund 1000.
KNAPPE_FENSTERHOEHE = 700


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
# betroffene Komponente im Designer markiert (Abschnitt 14).
_MELDUNG_ROLLE = Qt.ItemDataRole.UserRole
# Für Funde der Prüfung vor dem Start: (pfad, zeile, spalte), damit ein
# Klick die Datei öffnet und an die Stelle springt (Punkt 189).
_FUND_ROLLE = Qt.ItemDataRole.UserRole + 1
# Wahr an jedem Eintrag, den die Design-Prüfung geschrieben hat. Die
# nächste Design-Prüfung ersetzt nur diese Einträge; Funde der
# Prüfung vor dem Start bleiben stehen (Punkt 292).
_DESIGN_ROLLE = Qt.ItemDataRole.UserRole + 2
# Wahr am Eintrag `WIEDER_FRAGEN` nach einem Export ohne Signatur; ein
# Klick darauf lässt die Rückfrage zum Zertifikat wieder zu
# (Punkt 352).
_WIEDER_FRAGEN_ROLLE = Qt.ItemDataRole.UserRole + 3

#: Wie lange der Export höchstens auf das Schließen der Ankündigung
#: wartet, bevor er das Zertifikat anlegt (Punkt 350). Sieht niemand
#: hin, fragt Windows danach trotzdem, und für seine Frage gilt die
#: Grenze aus `ide/export/signatur.py`.
_ANKUENDIGUNG_GEDULD = 300


def _auf_breite_umbrechen(
    text: str, metrik: QFontMetrics, breite: int
) -> str:
    """Bricht `text` an Leerzeichen so um, dass keine Zeile in der
    Schrift `metrik` breiter als `breite` Punkte wird. Ein einzelnes
    Wort, das länger ist, bleibt ganz."""
    zeilen: list[str] = []
    zeile = ""
    for wort in text.split():
        probe = f"{zeile} {wort}" if zeile else wort
        if zeile and metrik.horizontalAdvance(probe) > breite:
            zeilen.append(zeile)
            zeile = wort
        else:
            zeile = probe
    if zeile:
        zeilen.append(zeile)
    return "\n".join(zeilen)

# Wie viele Funde die letzte Design-Prüfung eines Designers hatte.
_DESIGN_FUNDE_EIGENSCHAFT = "natter_design_funde"

# Was die Design-Prüfung während der Arbeit im Designer nicht meldet.
# Die Namen und Beschriftungen, die der Designer beim Platzieren
# selbst vergibt, sind noch nicht falsch; sie werden erst über
# „Werkzeuge → Design prüfen“ angemerkt (Punkte 292 und 301).
_NACH_JEDER_AENDERUNG_STILL = frozenset(
    {"namenskonvention.standardname", "namenskonvention.standardtext"}
)


def _ausgabe_kuerzen(text: str) -> str:
    """Kürzt eine Zeile für das Panel „Ausgabe“ auf `ZEILEN_GRENZE`
    Zeichen und sagt dahinter, wie lang sie war (Punkt 275).

    Die Liste misst und zeichnet jede sichtbare Zeile in voller Länge;
    eine Zeile mit Millionen Zeichen hielt Natter bei jedem Neuzeichnen
    für Sekunden an. Was der Leser liefert, ist schon höchstens so
    lang; gekürzt werden hier Zeilen, die auf anderem Weg ins Panel
    kommen.
    """
    if len(text) <= ZEILEN_GRENZE:
        return text
    laenge = f"{len(text):,}".replace(",", ".")
    return f"{text[:ZEILEN_GRENZE]} … (gekürzt, {laenge} Zeichen)"


def _gleiche_datei(a: str | Path, b: str | Path) -> bool:
    """Ob zwei Pfade dieselbe Datei meinen. Windows unterscheidet
    weder Groß- und Kleinschreibung noch die Richtung der
    Schrägstriche."""
    return os.path.normcase(os.path.abspath(a)) == os.path.normcase(
        os.path.abspath(b)
    )


def _dateiname_fehler(name: str) -> str | None:
    """Warum `name` nicht als Dateiname taugt, oder `None`.

    Gemeinsam für „Umbenennen …“ und „Neues Diagramm …“ (Punkte 221
    und 232): Windows lehnt diese Zeichen, einen Punkt oder ein
    Leerzeichen am Ende und die Gerätenamen ab, und ein Rückstrich
    oder Schrägstrich führte aus dem Ordner heraus.
    """
    from ide.project.neu import _RESERVIERTE_NAMEN, _VERBOTENE_ZEICHEN

    if (
        any(z in _VERBOTENE_ZEICHEN or ord(z) < 32 for z in name)
        or name.endswith((".", " "))
        or name.split(".")[0].strip().upper() in _RESERVIERTE_NAMEN
    ):
        return (
            f"„{name}“ taugt nicht als Dateiname. Nicht erlaubt sind "
            'die Zeichen < > : " / \\ | ? * und ein Punkt oder '
            "Leerzeichen am Ende."
        )
    return None


def _stand_merken(editor: QPlainTextEdit) -> None:
    """Hält fest, in welchem Stand die Datei des Editors jetzt auf der
    Platte liegt (Punkt 286)."""
    editor.setProperty(
        dateistand.EIGENSCHAFT,
        dateistand.kennung(editor.property(_PFAD_EIGENSCHAFT)),
    )


def _von_aussen_geaendert(editor: QPlainTextEdit) -> bool:
    return dateistand.von_aussen_geaendert(
        editor.property(dateistand.EIGENSCHAFT),
        editor.property(_PFAD_EIGENSCHAFT),
    )


def _eigenes_konto(besitzer: sperre.Besitzer) -> bool:
    """Ob eine Sperre aus dem Konto stammt, in dem Natter gerade
    läuft. Eine Sperrdatei ohne Konto zählt als fremd."""
    return bool(besitzer.konto) and (
        besitzer.konto.casefold() == sperre.kontoname().casefold()
    )


def _besitzer_text(besitzer: sperre.Besitzer) -> str:
    """„am Rechner „PC-R12“ im Konto „mueller.anna““."""
    wer = f"am Rechner „{besitzer.rechner}“"
    if besitzer.konto:
        wer += f" im Konto „{besitzer.konto}“"
    return wer


#: Wie `_ort_zum_oeffnen` zu seinem Pfad kam, wenn es eine Kopie ist.
_KOPIE_ARTEN = ("kopiert", "vorhanden", "erneuert")


def _fehlende_dateien(projekt: Projekt) -> list[str]:
    """Die Namen der Startdatei und der Haupt-Unit von `projekt`,
    soweit sie im Projektordner fehlen (Punkt 391)."""
    namen = [projekt.haupt_datei.name]
    if projekt.haupt_unit:
        namen.append(f"{projekt.haupt_unit}.py")
    return [name for name in namen if not (projekt.ordner / name).is_file()]


def _oeffnen_fehler() -> tuple[type[BaseException], ...]:
    """Die Ausnahmen, bei denen sich ein Projekt nicht öffnen ließ und
    eine Meldung statt eines Tracebacks kommt. Als Funktion, weil
    `schema_fehler()` erst beim Aufruf `jsonschema` lädt."""
    return (
        json.JSONDecodeError, UnicodeDecodeError, schema_fehler(),
        KeyError, ProjektdateiUngueltig, OSError,
    )


def _ist_projekt_in(projekt: Projekt | None, pfad: Path) -> bool:
    """Ob `projekt` das Projekt in `pfad` ist (Projektdatei oder
    Ordner). `projekt_oeffnen` gibt nach einem abgebrochenen Wechsel
    das bisherige Projekt zurück; eine Meldung zum neuen wäre dann
    falsch (Punkt 341)."""
    if projekt is None:
        return False
    ordner = pfad if pfad.suffix.lower() != ".natter" else pfad.parent
    return projekt.ordner.resolve() == Path(ordner).resolve()


def _projektdatei_zu(pfad: Path) -> Path:
    """Die `.natter`-Datei zu `pfad`, der wie bei `Projekt.laden` auch
    der Projektordner sein darf."""
    if pfad.is_dir():
        kandidaten = sorted(pfad.glob("*.natter"))
        if kandidaten:
            return kandidaten[0]
    return pfad


def _beispiel_projektordner(pfad: Path) -> Path | None:
    """Der Ordner des mitgelieferten Beispiels oder seiner
    Arbeitskopie, in dem `pfad` liegt, oder `None` für alles andere.

    `pfad` kann die Projektdatei sein, der Projektordner oder eine
    Datei darin, auch in einem Unterordner wie `bilder`. Gesucht wird
    deshalb von `pfad` aufwärts nach einem Ordner mit Projektdatei.

    Eine Kopie mit umbenannter Projektdatei und eine einzeln
    herauskopierte Unit erkennt der Vergleich mit dem Inhalt der
    Beispiele (Punkt 251). Er gilt nur für Projektordner und für
    `pfad` selbst: ein Ordner weiter oben, in dem zufällig eine
    kopierte Unit liegt, sperrt nicht alles darunter.
    """
    pfad = Path(pfad)
    kandidaten = [pfad.parent] if pfad.suffix == ".natter" else [pfad]
    kandidaten += list(kandidaten[0].parents)
    for ordner in kandidaten:
        if ist_beispiel_original(ordner):
            if next(iter(ordner.glob("*.natter")), None) is not None:
                return ordner
        elif beispiel_original(ordner) is not None:
            return ordner
        elif (
            ordner.is_dir()
            and next(iter(ordner.glob("*.natter")), None) is not None
            and beispiel_nach_inhalt(ordner) is not None
        ):
            return ordner
    if ist_beispiel_original(pfad):
        return pfad.parent
    if pfad.is_file() and beispiel_nach_inhalt(pfad) is not None:
        return pfad.parent
    return None


def abgabe_name(projektname: str) -> str:
    """Name für eine Abgabe als ZIP: `Aufgabe3 - mueller.anna - PC-R12`
    (Punkte 323 und 396).

    Eine Klasse bekommt dieselbe Aufgabe unter demselben
    Projektnamen. Hießen alle Abgaben `Aufgabe3.zip` und entpackten
    sich nach `Aufgabe3\\`, ersetzte im Abgabeordner eine die andere,
    und nach dem Einsammeln war nicht zu erkennen, welche zu wem
    gehört. Genommen wird der Anmeldename aus Windows (`USERNAME`),
    nicht der ausgeschriebene Name wie im Quelltext-PDF: er ist kurz,
    enthält kein Komma und ist bei eigenen Konten in der Klasse
    eindeutig.

    Dahinter steht immer der Rechnername (`COMPUTERNAME`). Manche
    Schulen arbeiten mit einem Konto für alle, etwa „gast“ oder
    „Klasse8b“; ohne den Rechner hießen dort alle dreißig Abgaben
    gleich, und jede ersetzte die vorige. Ob ein Konto gemeinsam
    benutzt wird, lässt sich nicht erkennen, und eine Liste üblicher
    Namen fände „Klasse8b“ nicht. Zeichen, die in Dateinamen nicht
    erlaubt sind, werden zu `_`. Fehlt ein Teil, bleibt er weg."""
    import getpass

    try:
        konto = getpass.getuser()
    except (OSError, KeyError, ImportError):
        konto = ""
    teile = [projektname]
    for roh in (konto, sperre.rechnername()):
        teil = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", roh).strip(" .")
        if teil:
            teile.append(teil)
    return " - ".join(teile)


class ZipDateiUnlesbar(OSError):
    """Eine Datei des Projekts ließ sich für die ZIP nicht lesen,
    meist weil ein anderes Programm sie gesperrt hält (Punkt 343).

    `pfad` ist die Datei selbst; die Meldung nennt sie, und nicht die
    ZIP, die an ihr gescheitert ist."""

    def __init__(self, pfad: Path) -> None:
        super().__init__(f"{pfad} ließ sich nicht lesen")
        self.pfad = pfad


class ZipVorigeBeschaedigt(OSError):
    """Die neue ZIP ließ sich nicht schreiben, und die vorige gleichen
    Namens ließ sich danach nicht zurückschreiben (Punkt 372). Am Ziel
    liegt dann keine vollständige Abgabe mehr; die Meldung muss das
    sagen, statt eine unveränderte ältere ZIP anzunehmen."""

    def __init__(self, pfad: Path) -> None:
        super().__init__(f"{pfad} ist nicht mehr vollständig")
        self.pfad = pfad


class ZipAbgebrochen(OSError):
    """Natter wurde geschlossen, bevor die ZIP fertig gepackt war, und
    hat nicht länger gewartet (Punkt 394). Am Ziel liegt dann nichts
    Neues."""

    def __init__(self, pfad: Path) -> None:
        super().__init__(f"{pfad} wurde nicht fertig")
        self.pfad = pfad


#: Dateien mit diesen Endungen sind schon gepackt und kommen
#: unverändert in die Abgabe-ZIP (`ZIP_STORED`). Noch einmal gepackt
#: werden sie kaum kleiner, das Packen kostet aber viel Zeit: 100
#: Fotos zu 1 MB brauchten mit `ZIP_DEFLATED` 8 bis 14 Sekunden,
#: unverändert abgelegt gut eine (Punkt 388). DOCX, XLSX und PPTX
#: sind selbst ZIP-Archive.
_SCHON_GEPACKT = frozenset({
    ".jpg", ".jpeg", ".png", ".gif", ".webp",
    ".mp3", ".ogg", ".mp4",
    ".zip", ".7z", ".gz",
    ".pdf", ".docx", ".xlsx", ".pptx",
})


def _zip_art(pfad: Path) -> int:
    """Wie `pfad` in die Abgabe-ZIP kommt: unverändert, wenn die
    Datei schon gepackt ist, sonst gepackt."""
    import zipfile

    if pfad.suffix.lower() in _SCHON_GEPACKT:
        return zipfile.ZIP_STORED
    return zipfile.ZIP_DEFLATED


def zip_schreiben(
    ordner: Path,
    oben: str,
    ziel: Path,
    melden: Callable[[int, str], None] | None = None,
) -> int:
    """Schreibt den Projektordner `ordner` als ZIP nach `ziel`, alle
    Dateien unter dem Ordner `oben`. Liefert die Zahl der Dateien.

    Rührt kein Widget an und läuft deshalb auch in einem Nebenfaden
    (Punkt 388). `melden(prozent, text)` bekommt den Fortschritt.
    Versteckte Dateien und Ordner (etwa `.natter-quelle`) und
    Zwischenablagen wie `__pycache__`, `build` und `dist` bleiben
    draußen.

    Gebaut wird die ZIP zuerst im Temp-Ordner und erst vollständig
    ans Ziel kopiert. Lässt sich unterwegs eine Datei nicht lesen,
    etwa eine CSV, die Excel gesperrt hält, entsteht am Ziel nichts,
    und es kommt `ZipDateiUnlesbar` mit dieser Datei. Bis 0.3.x
    blieb eine leere ZIP am Ziel liegen, die wie eine Abgabe aussah
    (Punkt 343).

    Am Ziel wird nur eine Datei angelegt und beschrieben, nicht
    umbenannt. In einem Einsammelordner dürfen Schülerinnen oft
    Dateien anlegen, aber weder löschen noch umbenennen; eine
    Zwischendatei neben dem Ziel ließ sich dort nicht an seine
    Stelle setzen und blieb sichtbar liegen (Punkt 363).

    Liegt am Ziel schon eine ZIP, etwa von einer früheren Abgabe,
    wird sie vorher in den Temp-Ordner kopiert. Scheitert das
    Schreiben der neuen, kommt die alte von dort zurück; eine
    abgeschnittene Datei am Ziel hätte sonst die vollständige
    frühere Abgabe ersetzt (Punkt 372). Lässt sich auch die alte
    nicht zurückschreiben, kommt `ZipVorigeBeschaedigt`."""
    import contextlib
    import shutil
    import tempfile
    import zipfile

    ziel = Path(ziel)
    # Verknüpfungen und Junctions bleiben draußen: über sie kämen
    # Dateien von außerhalb des Projekts in die Abgabe (Punkt 252).
    dateien = []
    for pfad in sorted(dateien_im_ordner(ordner)):
        teile = pfad.relative_to(ordner).parts
        if any(
            t.startswith(".") or t in ("__pycache__", "build", "dist")
            for t in teile
        ):
            continue
        if not pfad.is_file() or pfad.resolve() == ziel.resolve():
            continue
        # Die Sicherung ungespeicherter Änderungen ist kein Teil der
        # Abgabe; abgegeben wird, was gespeichert ist (Punkt 344).
        if ist_sicherung(pfad):
            continue
        dateien.append((pfad, teile))
    griff, name = tempfile.mkstemp(prefix="natter_abgabe_", suffix=".zip")
    os.close(griff)
    zwischen = Path(name)
    sicherung: Path | None = None
    anzahl = 0
    gemeldet = -1
    try:
        with zipfile.ZipFile(zwischen, "w", zipfile.ZIP_DEFLATED) as archiv:
            for pfad, teile in dateien:
                try:
                    archiv.write(
                        pfad,
                        Path(oben, *teile).as_posix(),
                        compress_type=_zip_art(pfad),
                    )
                except OSError as fehler:
                    # Nur das Öffnen der Quelle meldet ihren Namen;
                    # ein Fehler beim Schreiben der ZIP nennt keinen
                    # oder die Zwischendatei.
                    if fehler.filename and Path(fehler.filename) == pfad:
                        raise ZipDateiUnlesbar(pfad) from fehler
                    raise
                anzahl += 1
                # Neun Zehntel für das Packen, der Rest für das
                # Kopieren ans Ziel. Gemeldet wird nur, wenn sich die
                # Zahl ändert, nicht bei jeder von 3.000 Dateien.
                prozent = 90 * anzahl // len(dateien)
                if melden is not None and prozent != gemeldet:
                    gemeldet = prozent
                    melden(prozent, f"{ziel.name} wird gespeichert …")
        angelegt = not ziel.exists()
        if not angelegt:
            # Die Sicherung liegt im Temp-Ordner und nicht neben dem
            # Ziel: dort könnte sie in einem Ordner nur zum Anlegen
            # nicht wieder gelöscht werden (Punkt 363). Lässt sich die
            # alte ZIP nicht lesen, bricht es hier ab, bevor sie
            # angefasst ist.
            griff, name = tempfile.mkstemp(
                prefix="natter_abgabe_alt_", suffix=".zip"
            )
            os.close(griff)
            sicherung = Path(name)
            shutil.copyfile(ziel, sicherung)
        geleert = False
        try:
            with open(zwischen, "rb") as quelle, open(ziel, "wb") as aus:
                geleert = True
                shutil.copyfileobj(quelle, aus)
        except BaseException:
            # Eine halb geschriebene ZIP soll nicht wie eine Abgabe
            # aussehen. Wo Löschen nicht erlaubt ist, bleibt sie
            # liegen; die Meldung sagt dann, dass keine ZIP
            # gespeichert wurde.
            if angelegt:
                with contextlib.suppress(OSError):
                    ziel.unlink(missing_ok=True)
            elif geleert:
                try:
                    with (
                        open(sicherung, "rb") as quelle,
                        open(ziel, "wb") as aus,
                    ):
                        shutil.copyfileobj(quelle, aus)
                except OSError as fehler:
                    raise ZipVorigeBeschaedigt(ziel) from fehler
            raise
    finally:
        with contextlib.suppress(OSError):
            zwischen.unlink(missing_ok=True)
        if sicherung is not None:
            with contextlib.suppress(OSError):
                sicherung.unlink(missing_ok=True)
    return anzahl


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


def neues_formular_vorlage(unit: str, klasse: str) -> str:
    """Gerüst der Unit eines weiteren Formulars (Punkt 58).

    Anders als bei `u_main.py` öffnet sich dieses Fenster nicht von
    selbst: ein anderes Formular muss es öffnen. Wie das geht, steht
    deshalb gleich oben.
    """
    feld = unit.removeprefix("u_")
    return f'''\
# Ein weiteres Fenster des Programms. Es öffnet sich nicht von selbst,
# sondern aus einem anderen Formular heraus, zum Beispiel in der
# Klick-Methode eines Knopfes in u_main.py:
#
#     from {unit} import {klasse}
#
#     def b_oeffnen_click(self, sender):
#         self.{feld} = {klasse}()
#         self.{feld}.show()
#
# Das Fenster bleibt offen, bis es geschlossen wird. Das "self." vor
# {feld} merkt es sich, damit u_main.py später noch darauf zugreifen
# kann, etwa auf das, was darin eingetragen wurde.
#
# Geschlossen wird es mit self.close().

from {unit}_design import {klasse}Design


class {klasse}({klasse}Design):
    pass
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


#: Was unter den globalen Namen keine Variable im Sinn des Unterrichts
#: ist: eingebundene Module, Funktionen, Klassen.
_KEINE_VARIABLEN = frozenset({"module", "function", "type", "builtin_function_or_method"})


def _bilder_in_pfm_eintragen(pfm: dict, bild_pfade: dict[str, str]) -> None:
    """Trägt bei jeder Komponente mit Bild aus dem Import `picture` ein,
    auch in verschachtelten Behältern."""

    def durchgehen(kinder: list[dict]) -> None:
        for kind in kinder:
            if kind.get("name") in bild_pfade:
                kind.setdefault("properties", {})["picture"] = bild_pfade[kind["name"]]
            durchgehen(kind.get("children", []))

    durchgehen(pfm.get("children", []))


def _auswertung_als_text(ergebnis) -> str:  # noqa: ANN001
    """Antwort des Debuggers auf eine Auswertung als Text für die
    Anzeige; ein Fehler (etwa ein noch unbekannter Name) als kurzer
    deutscher Satz."""
    if isinstance(ergebnis, dict):
        if "fehler" in ergebnis:
            return "(lässt sich hier nicht ausrechnen)"
        return str(ergebnis.get("result", ""))
    return str(ergebnis)


def _designvorgabe_setzen(thema: str) -> None:
    """Gibt das Design von Natter an Formulare und Programme weiter.

    Ein Formular mit `theme = "system"` richtet sich danach - im
    Designer, weil es im Prozess von Natter läuft, und im gestarteten
    Programm, weil es die Umgebung erbt. Steht Natter selbst auf
    „System", gibt es nichts vorzugeben, und alle folgen Windows.
    """
    if thema in ("light", "dark"):
        os.environ[VORGABE_VARIABLE] = thema
    else:
        os.environ.pop(VORGABE_VARIABLE, None)


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
        # Wo der bisherige Stand einer eben ersetzten Kopie liegt
        # (`_kopie_zuruecksetzen`, Punkt 380).
        self._aufgehoben: Path | None = None
        self._design_thema = self._design_einstellungen.value("design/thema", "system")
        _designvorgabe_setzen(self._design_thema)
        self._code_schriftart = self._design_einstellungen.value(
            "editor/schriftart", "Consolas"
        )
        self._stil_anwenden()

        self._menues: dict[str, object] = {}
        for titel in MENUETITEL:
            self._menues[titel] = self.menuBar().addMenu(
                MENUE_ZUGRIFF[titel]
            )

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
        self.startbild.zurueck_gewuenscht.connect(self._zurueck_zur_arbeit)

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
        #: Ob die rechten Ecken gerade dem Objektinspektor gehören,
        #: siehe `_aufteilung_nach_hoehe` (Punkt 437).
        self._knappe_hoehe = False

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
        #: Das Auftragsobjekt des zuletzt gestarteten Programms. Es
        #: bleibt über das Ende des Programms hinaus bestehen, damit
        #: „Stopp“ auch noch erreicht, was das Programm gestartet hat
        #: und was es überlebt (Punkt 281). Frei wird es mit „Stopp“,
        #: beim nächsten Start und beim Schließen von Natter.
        self._programm_auftrag: Auftrag | None = None
        #: Sammelt die Ausgabe eines GUI-Programms ein. Ohne
        #: Konsolenfenster gibt es keinen anderen Ort dafür.
        self._ausgabe_leser: AusgabeLeser | None = None
        #: Der eine lange Vorgang, der gerade nebenher läuft. Genau
        #: einer auf einmal: zwei gleichzeitige Exporte schrieben in
        #: dieselbe Exe, zwei `pip install` in dieselbe Umgebung.
        self._hintergrundarbeit: Hintergrundarbeit | None = None
        #: Die zuletzt gestartete Abgabe-ZIP und das Zeichen, sie
        #: abzubrechen. Beim Schließen wartet `_zip_abwarten` darauf.
        self._zip_lauf: tuple[Hintergrundarbeit, threading.Event] | None = (
            None
        )
        #: Ob das Fenster gerade auf eine ZIP wartet, um zu schließen.
        self._schliesst_nach_zip = False
        self._offene_canvases: list[DesignerCanvas] = []
        self._pfad_zu_formular: dict[str, Form] = {}
        # Diagramme sind eigene Fenster (Abschnitt 13.1), keine Tabs -
        # deshalb eine eigene Verwaltung statt `editor_tabs`.
        self._offene_diagramme: dict[str, DiagrammFenster] = {}
        self._widget_zu_canvas: dict[QWidget, DesignerCanvas] = {}
        self._aktueller_canvas: DesignerCanvas | None = None
        #: Haltepunkte und Bedingungen von Dateien, deren Reiter
        #: geschlossen wurde, je Pfad (Punkt 419). Sie gelten beim
        #: Start weiter und kommen beim Öffnen zurück in den Editor.
        #: Beim Wechsel oder Schließen des Projekts und beim Beenden
        #: gehen sie mit denen der offenen Reiter in die Einstellungen
        #: (`_haltepunkte_ablegen`), beim Öffnen kommen sie von dort.
        self._gemerkte_haltepunkte: dict[
            str, tuple[set[int], dict[int, str]]
        ] = {}
        #: Die `.natter`-Datei des offenen Projekts. Unter ihrem Pfad
        #: stehen die Haltepunkte in den Einstellungen.
        self._projekt_datei: Path | None = None
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
        # „Variable", nicht „Eigenschaft": hier stehen die Variablen
        # des angehaltenen Programms, und gefüllt wird die Spalte auch
        # aus `variable["name"]`. „Eigenschaft" ist die Beschriftung
        # des Objektinspektors und war von dort übernommen.
        self.variablen_baum.setHeaderLabels(["Variable", "Wert"])
        # „Als Tabelle anzeigen“ (Abschnitt 11.6): Rechtsklick oder
        # Doppelklick auf eine Variable im Panel „Variablen“.
        self.variablen_baum.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.variablen_baum.customContextMenuRequested.connect(self._variablen_menue_zeigen)
        self.variablen_baum.itemActivated.connect(
            lambda eintrag, _spalte: self.variable_als_tabelle_zeigen(eintrag.text(0))
        )
        # Aufklappen von Listen und Objekten (Punkt 99): die Kinder
        # werden erst beim Aufklappen beim Debugger erfragt.
        self.variablen_baum.itemExpanded.connect(self._variable_aufgeklappt)
        self._variablen_zu_laden: dict[str, QTreeWidgetItem] = {}
        self._ueberwachen_aufbauen()
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
        # Kopieren und Leeren über die rechte Maustaste (Punkt 98).
        self.ausgabe_liste.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.ausgabe_liste.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.ausgabe_liste.customContextMenuRequested.connect(
            lambda punkt: self.ausgabe_kontextmenue().exec(
                self.ausgabe_liste.viewport().mapToGlobal(punkt)
            )
        )
        # Alle Zeilen gleich hoch: sonst misst die Liste bei jedem
        # Scrollen ans Ende die Höhe jedes Eintrags neu, und 3.000
        # Zeilen kosteten zweieinhalb Minuten statt einer
        # Viertelsekunde (Punkt 267).
        self.ausgabe_liste.setUniformItemSizes(True)
        #: Holt die Ausgabe des laufenden Programms im Takt ab und
        #: übernimmt sie gebündelt (Punkt 267).
        self._ausgabe_uhr = QTimer(self)
        self._ausgabe_uhr.setInterval(_AUSGABE_TAKT_MS)
        self._ausgabe_uhr.timeout.connect(self._ausgabe_abholen)
        self._laufzeit_uhr = QTimer(self)
        self._laufzeit_uhr.setInterval(_LAUFZEIT_TAKT_MS)
        self._laufzeit_uhr.timeout.connect(self._programmende_pruefen)
        self._start_zeitpunkt: float | None = None
        #: Die Ladeanzeige zwischen Start und erstem Fenster
        #: (Punkt 271). Entsteht beim ersten Start.
        self._lade_anzeige: QWidget | None = None
        self._lade_text: QLabel | None = None
        # Hält die Zeit in der Sperrdatei des offenen Projekts frisch;
        # an einem anderen Rechner zählt sie nur, solange sie jung ist
        # (Punkt 322).
        self._sperre_uhr = QTimer(self)
        self._sperre_uhr.setInterval(sperre.ERNEUERN_MS)
        self._sperre_uhr.timeout.connect(self._sperre_erneuern)
        self._sperre_uhr.start()
        # Sichert ungespeicherte Änderungen des offenen Projekts in
        # regelmäßigen Abständen (Punkt 344). In der Sicherungsdatei
        # hat jedes Fenster einen eigenen Anteil, gekennzeichnet mit
        # `_sicherung_herkunft`, und fasst nur diesen an (Punkte 400
        # und 406). `_sicherung_eigen` sagt, ob dieses Fenster im
        # offenen Projekt schon einen Anteil geschrieben haben kann;
        # sonst liest es die Datei nach dem Speichern gar nicht erst.
        self._sicherung_herkunft = sicherung.herkunft_anlegen()
        self._sicherung_eigen = False
        self._sicherung_uhr = QTimer(self)
        self._sicherung_uhr.setInterval(_SICHERUNG_TAKT_MS)
        self._sicherung_uhr.timeout.connect(self._sicherung_uhr_schlaegt)
        self._sicherung_uhr.start()
        # Beim Abmelden und Herunterfahren ruft Qt 6 kein `closeEvent`
        # auf, sondern sendet nur diese beiden Signale (Punkt 338).
        self._sitzung_verbunden = False
        anwendung = QGuiApplication.instance()
        if anwendung is not None:
            anwendung.commitDataRequest.connect(self._sitzungsende_klaeren)
            anwendung.aboutToQuit.connect(self._beim_beenden_aufraeumen)
            self._sitzung_verbunden = True
        self._lade_uhr = QTimer(self)
        self._lade_uhr.setInterval(_LADE_TAKT_MS)
        self._lade_uhr.timeout.connect(self._ladeanzeige_pruefen)
        self._lade_beginn: float | None = None
        self._lade_prozess: Callable[[], subprocess.Popen | None] | None = None
        self._lademarke: Path | None = None
        #: Die Endmarke des laufenden Konsolenprogramms
        #: (`ide.run.ladeanzeige.endmarke_zu`) und ob ihr Ende schon
        #: im Panel „Ausgabe“ steht.
        self._endmarke: Path | None = None
        self._ende_gemeldet = False

        panel_widgets = {
            "Meldungen": self.meldungen_liste,
            "Ausgabe": self.ausgabe_liste,
            "Variablen": self.variablen_baum,
            "Überwachen": self.ueberwachen_panel,
            "Aufrufstapel": self.aufrufstapel_liste,
            "Tests": self.tests_baum,
        }
        self._panel_schrift_anpassen()
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
            # Über das Menü geöffnet, kommt ein Dock an seinen Platz im
            # Fenster zurück. Das gemerkte Layout kann es schwebend
            # enthalten, und „Ansicht → Datenbank“ öffnete dann ein
            # loses Fenster irgendwo über dem Editor. Wer es schwebend
            # haben will, zieht es danach wieder heraus.
            dock.toggleViewAction().triggered.connect(
                lambda an, d=dock: an and d.isFloating() and d.setFloating(False)
            )

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
        # Einmal jetzt, im Hintergrund: der erste Vorschlag kostete
        # sonst ein bis zwei Sekunden, in denen der Editor stillstand.
        if self.vervollstaendigung_aktion.isChecked() and not pruefungsmodus_laeuft():
            vervollstaendigung_aufwaermen()

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
        # „Datenbank“ liegt als Reiter bei den Panels und hat damit die
        # volle Breite. Daneben gelegt blieben ihm auf 1280 × 800 rund
        # 490 × 300 Pixel: eine einzige Ergebniszeile und abgeschnittene
        # Tabellennamen (Punkt 303).
        self.tabifyDockWidget(self.panels_dock, self.datenbank_dock)
        self.resizeDocks([self.panels_dock], [200], Qt.Orientation.Vertical)
        self.datenbank_dock.toggleViewAction().triggered.connect(
            lambda an: an and self._datenbank_nach_vorn()
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
        # Namen der Docks, die `_formular_docks_anpassen` für ein
        # Konsolenprojekt verborgen hat (Punkt 348).
        verborgen = self._design_einstellungen.value(
            "fenster/fuer_konsole_verborgen", []
        )
        if isinstance(verborgen, str):
            verborgen = [verborgen]
        self._fuer_konsole_verborgen: set[str] = set(verborgen or [])

        self._letzte_testergebnisse: list[Testergebnis] = []
        self.debug_sitzung: DebugSitzung | None = None
        self._aktueller_thread_id: int | None = None
        #: Faden des Schülerprogramms, auch wenn es gerade läuft - für
        #: „Pause“ (Punkt 56). `_aktueller_thread_id` gibt es nur
        #: während eines Halts.
        self._faden_id: int | None = None
        self._letzter_aufrufstapel: list[dict] = []
        #: Name der Variablen, für die gerade „Als Tabelle anzeigen“
        #: läuft (Abschnitt 11.6) - `None`, wenn keine Anfrage offen ist.
        self._tabellen_variable: str | None = None
        #: Grund des letzten Halts ("breakpoint"/"step"/"exception"),
        #: entscheidet, welches Panel danach nach vorne kommt.
        self._letzter_haltegrund: str = ""
        #: Wodurch der nächste Halt ausgelöst wird, wenn Natter es
        #: besser weiß als debugpy: (Grund laut debugpy, Text). Der
        #: vorübergehende Haltepunkt für F11 vor dem Start meldet sich
        #: als „breakpoint“, F10 als „step“ wie F11 - in der
        #: Statusleiste stand dann ein Haltepunkt, den es nicht gibt,
        #: und „Einzelschritt“ nach einem Prozedurschritt.
        self._erwarteter_halt: tuple[str, str] | None = None
        #: Zuletzt geöffnete Tabellenansicht; hält das Fenster am Leben
        #: (ein `QDialog` ohne Verweis wird sonst sofort eingesammelt).
        self.letzte_tabellen_ansicht: TabellenAnsicht | None = None

        self.statusBar().showMessage("bereit")
        # Dauerhaft rechts in der Statusleiste, solange eine Prüfung
        # läuft - eine Meldung, die nach drei Sekunden verschwindet,
        # wäre für einen Zustand falsch, der vier Stunden anhält.
        self.pruefungsanzeige = QLabel()
        # Rot hinterlegt statt nur fett: fett in der Textfarbe der
        # Statusleiste sah aus wie eine gewöhnliche Meldung, und wer
        # nicht sieht, dass der Modus an ist, sucht den Fehler bei
        # sich. Weiße Schrift auf diesem Rot trägt in beiden Themen -
        # ein Rot, das zum hellen Thema passt, verschwindet im
        # dunklen. Das Wort „Prüfungsmodus" steht weiter daneben: auf
        # die Farbe allein ist in einer Klasse kein Verlass.
        self.pruefungsanzeige.setStyleSheet(
            "QLabel { background-color: #c42b1c; color: #ffffff;"
            " padding: 1px 8px; border-radius: 3px; font-weight: bold; }"
        )
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
                "datei.alle_speichern",
                "Alle speichern",
                menue="Datei",
                tastenkuerzel="Ctrl+Shift+S",
                callback=self._alle_speichern_aktion,
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
        # Die Befehle des Designers standen nur im Kontextmenü einer
        # Komponente; in der Menüleiste und in „Befehl suchen …“ fehlten
        # sie (Punkt 465). Ohne Tastenkürzel: Strg+D und Entf gehören
        # im Editor anderen Befehlen, der Designer fängt sie selbst ab.
        for aktion_id, name, callback in (
            ("bearbeiten.duplizieren", "Duplizieren", self._designer_duplizieren),
            ("bearbeiten.loeschen", "Löschen", self._designer_loeschen),
            (
                "bearbeiten.anordnen",
                "Ausrichten, Raster und Tab-Reihenfolge …",
                self._designer_anordnen,
            ),
        ):
            self.aktionen.registrieren(
                Aktion(
                    aktion_id,
                    name,
                    menue="Bearbeiten",
                    trennlinie_davor=aktion_id == "bearbeiten.duplizieren",
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
                "suchen.weitersuchen",
                "Weitersuchen",
                menue="Suchen",
                tastenkuerzel="F3",
                callback=self._weitersuchen_aktion,
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "suchen.zuruecksuchen",
                "Zurücksuchen",
                menue="Suchen",
                tastenkuerzel="Shift+F3",
                callback=lambda: self._weitersuchen_aktion(rueckwaerts=True),
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "suchen.in_dateien",
                "In allen Dateien suchen …",
                menue="Suchen",
                tastenkuerzel="Ctrl+Shift+F",
                callback=self._in_dateien_suchen_aktion,
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "suchen.zurueck",
                "Zurück zur vorigen Stelle",
                menue="Suchen",
                tastenkuerzel="Alt+Left",
                callback=self._zurueck_aktion,
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "suchen.gehe_zu_zeile",
                "Zu Zeile springen …",
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
                "quelltext.alles_zuklappen",
                "Alles zuklappen",
                menue="Quelltext",
                trennlinie_davor=True,
                callback=lambda: self._falten_aktion(zu=True),
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "quelltext.alles_aufklappen",
                "Alles aufklappen",
                menue="Quelltext",
                callback=lambda: self._falten_aktion(zu=False),
            )
        )
        for kennung, name, taste, schritt in (
            ("ansicht.schrift_groesser", "Schrift größer", "Ctrl++", 1),
            ("ansicht.schrift_kleiner", "Schrift kleiner", "Ctrl+-", -1),
            ("ansicht.schrift_normal", "Normale Schriftgröße", "Ctrl+0", 0),
        ):
            self.aktionen.registrieren(
                Aktion(
                    kennung,
                    name,
                    menue="Ansicht",
                    tastenkuerzel=taste,
                    callback=lambda *_, s=schritt: self._schriftgroesse_aktion(s),
                )
            )
        self.aktionen.registrieren(
            Aktion(
                "werkzeuge.einstellungen",
                "Einstellungen …",
                menue="Werkzeuge",
                callback=self._einstellungen_aktion,
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "fenster.reiter_schliessen",
                "Reiter schließen",
                menue="Fenster",
                tastenkuerzel="Ctrl+W",
                callback=self._reiter_schliessen_aktion,
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "fenster.naechster_tab",
                "Nächster Reiter",
                menue="Fenster",
                tastenkuerzel="Ctrl+Tab",
                callback=self._naechster_tab_aktion,
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "fenster.vorheriger_tab",
                "Vorheriger Reiter",
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
                "ansicht.startseite",
                "Startseite",
                menue="Ansicht",
                callback=self._startseite_aktion,
            )
        )
        # F1 war keiner Aktion zugeordnet, obwohl es unter Windows die
        # übliche Hilfetaste ist (Punkt 438).
        self.aktionen.registrieren(
            Aktion(
                "hilfe.zur_auswahl",
                "Hilfe zur Auswahl",
                menue="Hilfe",
                tastenkuerzel="F1",
                callback=self._hilfe_zur_auswahl_aktion,
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
                "hilfe.handbuch",
                "Handbuch",
                menue="Hilfe",
                callback=self._handbuch_aktion,
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "hilfe.befehl_suchen",
                "Befehl suchen …",
                menue="Hilfe",
                tastenkuerzel="Ctrl+Shift+P",
                callback=self._befehl_suchen_aktion,
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
                # Strg+O öffnet das Projekt, nicht eine einzelne Datei:
                # so steht es im Handbuch, und so kennt man es aus
                # anderen Entwicklungsumgebungen (Punkt 213).
                tastenkuerzel="Ctrl+O",
                symbol="projekt_oeffnen",
                trennlinie_davor=True,
                callback=self._projekt_oeffnen_dialog,
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "projekt.schliessen",
                "Projekt schließen",
                menue="Projekt",
                callback=self.projekt_schliessen,
            )
        )
        # Stand bis Punkt 371 im Untermenü „Datei → Beispielprojekte“.
        # Das ist im Prüfungsmodus als Ganzes gesperrt, und gerade in
        # einer Klausur ließ sich die Kopie einer Aufgabe dann nicht
        # mehr zurücksetzen. Ob der Eintrag geht, regelt
        # `_zuruecksetzen_pruefen`.
        self._beispiel_zuruecksetzen_eintrag = self.aktionen.registrieren(
            Aktion(
                "projekt.auf_original_zuruecksetzen",
                "Auf Original zurücksetzen …",
                menue="Projekt",
                callback=lambda: self.beispiel_zuruecksetzen_nachfragen(),
            )
        ).qaction
        self._beispiel_zuruecksetzen_eintrag.setStatusTip(
            "Ersetzt die Kopie des geöffneten Beispiels oder der "
            "geöffneten Aufgabe durch das Original"
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
                "projekt.ordner_oeffnen",
                "Projektordner öffnen",
                menue="Projekt",
                callback=self._projektordner_oeffnen_aktion,
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "projekt.als_zip",
                "Als ZIP speichern …",
                menue="Projekt",
                callback=self._als_zip_aktion,
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "projekt.quelltext_als_pdf",
                "Quelltext als PDF …",
                menue="Projekt",
                callback=self._quelltext_als_pdf_aktion,
            )
        )
        self.aktionen.registrieren(
            Aktion(
                "datei.neues_formular",
                "Neues Formular …",
                menue="Datei",
                callback=self._neues_formular_aktion,
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
                symbol="stopp",
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
        # Der Kurzhinweis sagt, worin sich die beiden Schritte
        # unterscheiden; der Name allein sagt es nicht.
        for kennung, unterschied in (
            ("start.einzelschritt", "springt in Funktionen hinein"),
            ("start.prozedurschritt", "führt Funktionsaufrufe als einen Schritt aus"),
        ):
            qaktion = self.aktionen[kennung].qaction
            qaktion.setToolTip(f"{qaktion.toolTip()} - {unterschied}")
        self.aktionen.registrieren(
            Aktion(
                "start.bis_cursor",
                "Ausführen bis Cursor",
                menue="Start",
                tastenkuerzel="F4",
                callback=self._debugger_bis_cursor_aktion,
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

        # „Datei → Beispielprojekte“ (Vorgabe: die Seite für die
        # Beispielprojekte gehört „unter Datei oben in der Kopfzeile
        # mit allen aufgelisteten Projekten. nicht in der normalen
        # Oberfläche“). Vorher standen sie als Abschnitt auf dem
        # Startbild - dort nahmen sie den meisten Platz ein und waren
        # nach dem ersten Projekt nicht mehr erreichbar, weil das
        # Startbild verschwand.
        #
        # Bewusst keine eigene `Aktion`-Hülle: die Einträge stehen
        # nicht fest, sondern kommen aus dem mitgelieferten Ordner.
        # Und bewusst erst hier, nach `an_hauptfenster_anhaengen`:
        # davor stünde das Untermenü über „Neue Unit“ und
        # „Öffnen …“, also vor den Dingen, die man täglich braucht.
        beispiel_menue = self._menues["Datei"].addMenu("Beispielprojekte")
        for pfad in beispielprojekte():
            eintrag = beispiel_menue.addAction(pfad.parent.name)
            eintrag.setStatusTip(
                "Wird nach Dokumente\\Natter\\Beispielprojekte kopiert und dort geöffnet"
            )
            eintrag.triggered.connect(lambda _geklickt=False, p=pfad: self.beispiel_oeffnen(p))
        if beispiel_menue.isEmpty():
            beispiel_menue.setEnabled(False)
        self._zuruecksetzen_pruefen()
        self._beispiel_menue = beispiel_menue
        self._beispielmenue_pruefen()

        # „Zuletzt geöffnet“ (Punkt 106): dieselbe Liste wie auf der
        # Startseite, aber auch erreichbar, wenn schon ein Projekt offen
        # ist. Aufgebaut beim Aufklappen, damit sie immer stimmt.
        self._zuletzt_menue = self._menues["Datei"].addMenu("Zuletzt geöffnet")
        self._zuletzt_menue.aboutToShow.connect(self._zuletzt_menue_aufbauen)
        self._zuletzt_menue_aufbauen()

        # „Beenden“ ganz unten im Menü Datei, nach den Beispielen - wie
        # in jedem Windows-Programm. Deshalb erst hier und von Hand
        # eingehängt statt über `an_hauptfenster_anhaengen`.
        beenden = self.aktionen.registrieren(
            Aktion("datei.beenden", "Beenden", callback=lambda: self.close())
        )
        beenden.menue = "Datei"
        self._menues["Datei"].addSeparator()
        self._menues["Datei"].addAction(beenden.qaction)
        self._vervollstaendigung_pruefen()

        # Der Prüfungsmodus läuft von selbst aus, auch bei offenem
        # Fenster. Die Uhr führt Restzeit und Sperren nach (Punkt 151).
        self._pruefung_lief = pruefungsmodus_laeuft()
        self._pruefungsuhr = QTimer(self)
        self._pruefungsuhr.setInterval(30_000)
        self._pruefungsuhr.timeout.connect(self._pruefungsmodus_nachfuehren)
        self._pruefungsuhr.start()

        # Der Zustand der Start-Einträge hängt am Debugger und ändert
        # sich damit im Betrieb. Er wird an jeder Stelle nachgeführt,
        # an der sich etwas ändert, und zusätzlich beim Aufklappen des
        # Menüs: ein einzelner vergessener Aufruf wäre sonst ein
        # stiller Rückfall in den Zustand, in dem fünf Einträge
        # anklickbar waren und nichts taten.
        self._startaktionen_pruefen()
        self._menues["Start"].aboutToShow.connect(self._startaktionen_pruefen)
        self._bearbeitenaktionen_pruefen()
        self._menues["Bearbeiten"].aboutToShow.connect(self._bearbeitenaktionen_pruefen)
        self.editor_tabs.currentChanged.connect(self._bearbeitenaktionen_pruefen)

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
                # Das Menü steht dabei, damit Übersicht und
                # Befehlspalette den Eintrag unter „Ansicht“ führen
                # (Punkt 466). Eingehängt wird er trotzdem von Hand,
                # als erster Eintrag: `an_hauptfenster_anhaengen` ist
                # an dieser Stelle schon gelaufen.
                menue="Ansicht",
                tastenkuerzel="Shift+F12",
                callback=self._formular_code_umschalten,
            )
        )
        self.formular_code_aktion = self.aktionen["ansicht.formular_code"].qaction
        ansicht = self._menues["Ansicht"]
        ansicht.insertAction(ansicht.actions()[0], self.formular_code_aktion)
        ansicht.insertSeparator(ansicht.actions()[1])

    def _dialog_startordner(self) -> str:
        """Wo „Öffnen …“ und die übrigen Datei-Dialoge beginnen: im
        offenen Projekt, sonst im zuletzt in einem Dialog gewählten
        Ordner, sonst neben dem zuletzt geöffneten Projekt, sonst in
        `natter_ordner()` (Punkt 408)."""
        from ide.shell.startbild import zuletzt_geoeffnet

        kandidaten: list[Path | str | None] = []
        if self.projekt is not None:
            kandidaten.append(self.projekt.ordner)
        kandidaten.append(
            self._design_einstellungen.value(_LETZTER_ORDNER, "") or None
        )
        zuletzt = zuletzt_geoeffnet(self._design_einstellungen)
        if zuletzt:
            kandidaten.append(zuletzt[0].parent.parent)
        return str(dialog_startordner(*kandidaten))

    def _dialog_ordner_merken(self, pfad: str) -> None:
        self._design_einstellungen.setValue(
            _LETZTER_ORDNER, str(Path(pfad).parent)
        )

    def _datei_oeffnen_dialog(self) -> None:
        pfad, _ = QFileDialog.getOpenFileName(
            self, "Öffnen", self._dialog_startordner()
        )
        if pfad:
            self._dialog_ordner_merken(pfad)
            self.oeffnen(Path(pfad))

    def _projekt_oeffnen_dialog(self) -> None:
        pfad, _ = QFileDialog.getOpenFileName(
            self,
            "Projekt öffnen",
            self._dialog_startordner(),
            "Natter-Projekte (*.natter)",
        )
        if pfad:
            # Gemerkt wird der Ordner über dem Projekt: von dort aus
            # lässt sich beim nächsten Mal ein anderes wählen.
            self._dialog_ordner_merken(str(Path(pfad).parent))
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
        # Vor dem Anlegen, nicht danach: wer bei der Nachfrage
        # abbricht, soll kein halb geöffnetes neues Projekt haben.
        if not self._vorheriges_projekt_schliessen():
            return
        try:
            projekt = projekt_erzeugen(vorlage, projektordner, name)
        except ValueError as fehler:
            self.statusBar().showMessage(
                f"Projekt konnte nicht angelegt werden: {fehler}"
            )
            return
        except FileExistsError:
            # Den Fall fängt schon der Dialog ab; hier landet nur, wer
            # den Ordner in der Zwischenzeit angelegt hat.
            self.statusBar().showMessage(
                f"Projekt konnte nicht angelegt werden: „{name}“ gibt "
                f"es in diesem Ordner schon. Einen anderen Namen wählen."
            )
            return
        except OSError as fehler:
            # Ohne diesen Zweig endete ein Name, den Windows nicht als
            # Ordner annimmt, in der Absturzmeldung.
            grund = (fehler.strerror or str(fehler)).rstrip(".")
            self.statusBar().showMessage(
                f"Projekt konnte nicht angelegt werden: {grund}. Einen "
                f"anderen Namen oder einen Ordner wählen, in dem "
                f"Schreibrechte bestehen."
            )
            return
        # Über `projekt_oeffnen`, damit das neue Projekt unter
        # „Zuletzt geöffnet“ steht (Punkt 153). Bis 0.3.5 setzte diese
        # Methode `self.projekt` selbst, und wer sein Projekt in der
        # nächsten Stunde suchte, fand es dort nicht.
        datei = projekt.ordner / f"{projekt.name}.natter"
        projekt = self.projekt_oeffnen(datei if datei.exists() else projekt.ordner)
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
            # Wie beim Öffnen einer einzelnen `.pfm`: eine beschädigte
            # soll das Projekt nicht mit der allgemeinen Fehlermeldung
            # abbrechen, die Unit ist dann trotzdem offen.
            try:
                self.designer_oeffnen(formulare[0])
            except (
                json.JSONDecodeError, UnicodeDecodeError, schema_fehler(),
                KeyError, PfmBeschaedigt,
            ) as fehler:
                self.statusBar().showMessage(
                    f"„{formulare[0].name}“ lässt sich nicht öffnen, die "
                    f"Datei ist beschädigt. {fehler_beschreiben(fehler)}"
                )

    def projekt_dateien(self) -> list[Path]:
        """Alle Units und Formulare des offenen Projekts, für „Unit
        öffnen …“ (Abschnitt 7.4). Leer, wenn kein Projekt offen ist."""
        if self.projekt is None:
            return []
        return sorted(self.projekt.units() + self.projekt.formulare())

    def _befehl_suchen_aktion(self) -> None:
        """„Hilfe → Befehl suchen …“ (Strg+Umschalt+P, Punkt 82)."""
        from ide.shell.befehlspalette import Befehlspalette

        self._startaktionen_pruefen()
        self._bearbeitenaktionen_pruefen()
        dialog = Befehlspalette(
            (a for a in self.aktionen if a.id != "hilfe.befehl_suchen"), self
        )
        self.letzte_befehlspalette = dialog
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.gewaehlte_aktion is not None:
            dialog.gewaehlte_aktion.qaction.trigger()

    def _unit_oeffnen_dialog(self) -> None:
        """„Unit öffnen …“ (Strg+P, Abschnitt 7.4, 7.9)."""
        dateien = self.projekt_dateien()
        if not dateien:
            return
        dialog = SchnellAuswahl(dateien, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.ausgewaehlte_datei is not None:
            self.datei_oeffnen(dialog.ausgewaehlte_datei)

    def unit_erzeugen(
        self, name: str | None = None, *, inhalt: str | None = None
    ) -> Path | None:
        """„Neue Unit“ (Abschnitt 7.2, 7.4): legt `u_neu<n>.py` an (oder
        mit gegebenem `name`), fügt sie dem Projekt-Explorer hinzu und
        öffnet sie im Editor.

        Ohne `inhalt` entsteht das Gerüst aus `neue_unit_vorlage()` -
        bis M12 war es eine leere Datei.

        Lässt sich die Datei nicht schreiben, meldet das
        `datei_schreiben_gemeldet` wie beim Speichern, und zurück kommt
        `None` (Punkt 417). Bis 0.4.2 flog der `PermissionError` aus
        dem Menü heraus und endete in der Absturzmeldung."""
        if self.projekt is None:
            raise RuntimeError("Kein Projekt offen.")

        if name is None:
            name = self._naechster_unit_name()

        pfad = self.projekt.ordner / f"{name}.py"
        if pfad.exists():
            raise FileExistsError(f"{pfad} existiert bereits.")

        if not self.datei_schreiben_gemeldet(
            pfad,
            neue_unit_vorlage(name) if inhalt is None else inhalt,
            folge=f"Die Unit {name} wurde nicht angelegt.",
        ):
            return None
        self.explorer.projekt_anzeigen(self.projekt)
        self.datei_oeffnen(pfad)
        return pfad

    def _neues_formular_aktion(self) -> None:
        """„Datei → Neues Formular …“ (Punkt 58)."""
        if self.projekt is None:
            self.statusBar().showMessage(self._kein_projekt_text())
            return
        if self.projekt.typ == "console":
            self.statusBar().showMessage(
                "Ein Konsolenprogramm hat keine Fenster. Formulare gibt es nur in einem "
                "Projekt mit grafischer Oberfläche."
            )
            return
        vorschlag = self._naechster_formularname()[0]
        name, ok = QInputDialog.getText(
            self, "Neues Formular", "Name der Unit (beginnt mit u_):", text=vorschlag
        )
        if not ok or not name.strip():
            return
        try:
            self.formular_erzeugen(name.strip())
        except (ValueError, FileExistsError) as fehler:
            self.statusBar().showMessage(str(fehler))

    def _naechster_formularname(self) -> tuple[str, str]:
        """(Unit, Klasse) für das nächste Formular: `u_form2`/`Form2`,
        `u_form3`/`Form3` … - geprüft gegen alle Dateien und alle
        Klassennamen der vorhandenen Formulare."""
        vorhandene = {p.stem for p in self.projekt.alle_python_dateien()}
        vorhandene |= {p.stem for p in self.projekt.formulare()}
        klassen = set()
        for pfm in self.projekt.formulare():
            try:
                klassen.add(json_datei_lesen(pfm).get("class"))
            except (OSError, ValueError):
                continue
        nummer = 2
        while f"u_form{nummer}" in vorhandene or f"Form{nummer}" in klassen:
            nummer += 1
        return f"u_form{nummer}", f"Form{nummer}"

    def formular_erzeugen(self, unit: str) -> Path | None:
        """Legt `<unit>.pfm`, `<unit>.py` und `<unit>_design.py` an,
        zeigt sie im Explorer und öffnet das Formular im Designer.

        Die Klasse heißt wie die nächste freie Nummer (`Form2`), die
        Unit wie angegeben. Zurück kommt der Pfad der `.pfm`.

        Scheitert eine der drei Dateien beim Schreiben, meldet das
        `datei_schreiben_gemeldet` wie beim Speichern, die schon
        geschriebenen werden wieder entfernt, und zurück kommt `None`
        (Punkt 417). Vorher blieb dann etwa eine `.pfm` ohne Unit
        liegen."""
        if self.projekt is None:
            raise RuntimeError("Kein Projekt offen.")
        if unit.endswith((".py", ".pfm")):
            unit = unit.rsplit(".", 1)[0]
        if not unit.isidentifier() or not unit.startswith("u_"):
            raise ValueError(
                f"„{unit}“ taugt nicht als Name: erlaubt sind Buchstaben, Ziffern und "
                f"Unterstrich, am Anfang „u_“, etwa u_einstellungen."
            )
        # Windows unterscheidet in Dateinamen nicht zwischen Groß- und
        # Kleinschreibung: „u_Main“ träfe die vorhandene u_main.py.
        # Deshalb wird ohne Rücksicht darauf verglichen und zusätzlich
        # jede der drei Dateien auf dem Datenträger geprüft.
        vorhandene = {
            p.stem.casefold() for p in self.projekt.alle_python_dateien()
        }
        vorhandene |= {p.stem.casefold() for p in self.projekt.formulare()}
        ordner = self.projekt.ordner
        ziele = [
            ordner / f"{unit}.pfm",
            ordner / f"{unit}.py",
            ordner / f"{unit}_design.py",
        ]
        if (
            unit.casefold() in vorhandene
            or f"{unit}_design".casefold() in vorhandene
            or any(z.exists() for z in ziele)
        ):
            raise FileExistsError(f"„{unit}“ gibt es schon - bitte einen anderen Namen wählen.")
        klasse = self._naechster_formularname()[1]

        pfm_pfad = ordner / f"{unit}.pfm"
        pfm = {
            "format": "pfm/1",
            "class": klasse,
            "type": "Form",
            "properties": {
                "caption": klasse,
                "width": 480,
                "height": 360,
                "theme": "system",
            },
            "children": [],
        }
        dateien = [
            (
                pfm_pfad,
                json.dumps(pfm, indent=2, ensure_ascii=False) + "\n",
            ),
            (ordner / f"{unit}.py", neues_formular_vorlage(unit, klasse)),
            (
                ordner / f"{unit}_design.py",
                design_code_erzeugen(pfm, pfm_pfad.name),
            ),
        ]
        geschrieben: list[Path] = []
        for pfad, inhalt in dateien:
            if not self.datei_schreiben_gemeldet(
                pfad, inhalt,
                folge=f"Das Formular {klasse} wurde nicht angelegt.",
            ):
                for alt in geschrieben:
                    with contextlib.suppress(OSError):
                        alt.unlink(missing_ok=True)
                return None
            geschrieben.append(pfad)
        self.explorer.projekt_anzeigen(self.projekt)
        self.designer_oeffnen(pfm_pfad)
        self.statusBar().showMessage(
            f"Formular {klasse} in {unit}.py angelegt. Wie es sich öffnen lässt, steht oben "
            f"in {unit}.py."
        )
        return pfm_pfad

    def _startdatei_zeigen_aktion(self) -> None:
        """„Projekt → Startdatei anzeigen“ – der einzige Weg zur
        `main.py`.

        Sie steht bewusst nicht im Projekt-Explorer: Natter schreibt sie
        beim Anlegen des Projekts, danach ändert sie niemand mehr. Eine
        Datei, die man nicht bearbeiten soll, gehört nicht zwischen die,
        an denen man arbeitet (M12). Wer trotzdem hineinsehen will, kommt
        über diesen Eintrag hin."""
        if self.projekt is None:
            self.statusBar().showMessage(self._kein_projekt_text())
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
            self.statusBar().showMessage(self._kein_projekt_text())
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
            self.statusBar().showMessage(self._kein_projekt_text())
            return
        if not self._hintergrund_frei("Der Testlauf"):
            return
        # Wie beim Starten: getestet wird, was auf der Platte steht
        # (Punkt 86).
        if not self.alle_speichern():
            return
        ordner = self.projekt.ordner
        self.statusBar().showMessage("Tests laufen - die IDE bleibt bedienbar.")
        self._hintergrund_starten(
            lambda _melden: tests_ausfuehren(
                ordner, prozess_gestartet=self._hintergrund_prozess_melden
            ),
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
                "Noch keine Testergebnisse zum Exportieren - zuerst „Projekt → Alle "
                "Tests ausführen“ starten."
            )
            return
        pfad, _ = QFileDialog.getSaveFileName(
            self,
            "Testergebnisse exportieren",
            self._dialog_startordner(),
            "HTML-Datei (*.html)",
        )
        if not pfad:
            return
        titel = self.projekt.name if self.projekt is not None else "Testprotokoll"
        html = ergebnisse_als_html(self._letzte_testergebnisse, titel=titel)
        if not self.datei_schreiben_gemeldet(Path(pfad), html):
            return
        self.statusBar().showMessage(f"Testprotokoll gespeichert: {pfad}")

    def _quelltext_als_pdf_aktion(self) -> None:
        """„Projekt → Quelltext als PDF …": das ganze Projekt zum
        Abgeben.

        Kein Hintergrundlauf: ein Schülerprojekt hat eine Handvoll
        Dateien, und das Schreiben dauert keine Sekunde. Im
        Prüfungsmodus bleibt der Eintrag offen - wer seinen eigenen
        Code ausgibt, verschafft sich keinen Vorteil.
        """
        if self.projekt is None:
            self.statusBar().showMessage(self._kein_projekt_text())
            return
        if not self.projekt.units():
            self.statusBar().showMessage(
                "Das Projekt hat keine Unit, die sich ausgeben ließe."
            )
            return
        # Ausgegeben wird der Stand im Editor, wie beim Starten und beim
        # Exe-Export (Punkt 155). Bis 0.3.5 las das PDF die Dateien von
        # der Platte, und wer vor der Abgabe Strg+S vergaß, gab den
        # alten Stand ab.
        if not self.alle_speichern():
            return

        vorschlag = self.projekt.ordner / f"{self.projekt.name} Quelltext.pdf"
        pfad, _ = QFileDialog.getSaveFileName(
            self, "Quelltext als PDF speichern", str(vorschlag), "PDF-Dateien (*.pdf)"
        )
        if not pfad:
            return

        from ide.export.quelltext_pdf import quelltext_als_pdf

        try:
            ziel = quelltext_als_pdf(self.projekt, Path(pfad))
        except OSError as fehler:
            self.statusBar().showMessage(
                f"Das PDF ließ sich nicht schreiben: {fehler}. Einen anderen Ordner "
                f"wählen, in dem Schreibrechte bestehen."
            )
            return
        except ValueError as fehler:
            # Eine Unit, die nicht als UTF-8 gespeichert ist.
            QMessageBox.warning(self, "Quelltext als PDF", str(fehler))
            return

        anzahl = len(self.projekt.units())
        wort = "Datei" if anzahl == 1 else "Dateien"
        self.statusBar().showMessage(f"{anzahl} {wort} geschrieben nach {ziel}")

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
            self.statusBar().showMessage(self._kein_projekt_text())
            return
        if not self._hintergrund_frei("Der Export"):
            return
        # Exportiert wird, was auf der Platte steht (Punkt 86).
        if not self.alle_speichern():
            return

        projekt = self.projekt
        self.statusBar().showMessage("Exe wird erstellt - die IDE bleibt bedienbar.")
        self._fortschritt_zeigen(0)
        self._hintergrund_starten(
            lambda melden: exe_exportieren(
                projekt,
                fortschritt=melden,
                prozess_gestartet=self._hintergrund_prozess_melden,
                vor_dem_anlegen=self._zertifikat_ankuendigen_lassen,
            ),
            self._export_fertig,
            "Exe-Export fehlgeschlagen",
        )

    def _zertifikat_ankuendigen_lassen(self) -> None:
        """Aus dem Faden des Exports, bevor Natter das Zertifikat
        anlegt: zeigt die Ankündigung im Faden der Oberfläche und
        wartet, bis sie gelesen ist (Punkt 350)."""
        lauf = self._hintergrundarbeit
        if lauf is not None:
            lauf.im_vordergrund(
                self._zertifikat_ankuendigen, _ANKUENDIGUNG_GEDULD
            )

    def _zertifikat_ankuendigen(self) -> None:
        """Sagt vor der Sicherheitswarnung von Windows, dass sie gleich
        kommt, woher sie stammt und was „Ja“ und „Nein“ bewirken.

        Ohne Ankündigung erschien die Warnung mitten im Export, während
        in Natter nur ein Ladebalken lief. Eine Schülerin hält sie dann
        eher für einen Angriff, und auf eine unerwartete Warnung
        antworten die meisten mit „Nein“ (Punkt 350)."""
        QMessageBox.information(
            self,
            "Zertifikat für die Exe",
            "Gleich fragt Windows mit einer Sicherheitswarnung, ob ein "
            f"Zertifikat von „{ZERT_NAME}“ installiert werden soll. "
            "Die Frage kommt von Natter.\n\n"
            "Mit dem Zertifikat signiert Natter die Exe, und Windows "
            "nennt dann einen Herausgeber statt „Unbekannter "
            "Herausgeber“. Das Zertifikat gilt nur für dieses "
            "Benutzerkonto und verlässt den Rechner nicht.\n\n"
            "„Ja“ trägt es ein, und die Frage kommt in diesem Konto "
            "nicht wieder. „Nein“ schadet nicht: die Exe entsteht "
            "trotzdem, nur ohne Signatur.",
        )

    def _export_fertig(self, ergebnis: object) -> None:
        """Die Nachbereitung des Exports, zurück im Faden der Oberfläche.

        Ohne Signatur kommt der Grund ganz und umbrochen ins Panel
        „Meldungen“, die Statuszeile sagt nur, dass er dort steht.
        Bis 0.3.x hing er an der Statuszeile und endete am
        Fensterrand, im Panel stand er als eine einzige Zeile hinter
        neun englischen Zeilen von PyInstaller (Punkt 351). Nach einem
        Erfolg sagen die niemandem etwas und bleiben draußen."""
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

        # Die letzte Zeile des Protokolls sagt, ob signiert wurde.
        # Ohne Signatur gilt das Programm Windows als von einem
        # unbekannten Herausgeber, und das soll dastehen, bevor
        # jemand es weitergibt.
        letzte = ergebnis.protokoll.strip().splitlines()
        signaturzeile = letzte[-1] if letzte else ""
        if "Signiert" in signaturzeile:
            self.statusBar().showMessage(
                f"Exe erstellt: {ergebnis.ausgabe_pfad}"
            )
        else:
            self._ohne_signatur_melden(
                ergebnis.ausgabe_pfad, signaturzeile
            )
        if sys.platform == "win32":
            os.startfile(ergebnis.ausgabe_pfad.parent)

    def _ohne_signatur_melden(self, exe: Path, grund: str) -> None:
        """Schreibt Pfad und Grund einer Exe ohne Signatur ins Panel
        „Meldungen“, auf die Breite des Panels umbrochen (Punkt 351).

        Hat jemand die Rückfrage von Windows verneint, folgt der
        Eintrag `WIEDER_FRAGEN`; ein Klick darauf hebt den Vermerk auf
        (Punkt 352). Bis dahin ging das nur über eine Datei im
        ausgeblendeten Ordner `AppData`."""
        liste = self.meldungen_liste
        liste.clear()
        self.panels.setCurrentWidget(liste)
        metrik = liste.fontMetrics()
        # Abzug für Rand und Einzug des Eintrags; ohne ihn reichte die
        # letzte Zeile um ein paar Punkte unter die Bildlaufleiste.
        breite = max(
            200,
            liste.viewport().width() - 2 * metrik.horizontalAdvance("M") - 8,
        )
        texte = [
            f"[Exe-Export] Exe erstellt: {exe}",
            grund or "Ohne Signatur.",
        ]
        zeilen = 0
        for text in texte:
            umbrochen = _auf_breite_umbrechen(text, metrik, breite)
            zeilen += umbrochen.count("\n") + 1
            liste.addItem(umbrochen)
        if abgelehnt_vermerk().exists():
            eintrag = QListWidgetItem(WIEDER_FRAGEN)
            eintrag.setData(_WIEDER_FRAGEN_ROLLE, True)
            schrift = eintrag.font()
            schrift.setUnderline(True)
            eintrag.setFont(schrift)
            eintrag.setForeground(liste.palette().link())
            eintrag.setToolTip(
                "Hebt den Vermerk über das „Nein“ auf. Der nächste "
                "Export legt das Zertifikat wieder an, und Windows "
                "fragt erneut."
            )
            liste.addItem(eintrag)
            zeilen += 1
        self._panel_hoehe_sichern(zeilen)
        self.statusBar().showMessage(
            "Exe erstellt, ohne Signatur - der Grund steht im Panel "
            "„Meldungen“."
        )

    def _rueckfrage_wieder_zulassen(self, eintrag: QListWidgetItem) -> None:
        """Klick auf `WIEDER_FRAGEN` im Panel „Meldungen“ (Punkt 352)."""
        rueckfrage_wieder_zulassen()
        zeile = self.meldungen_liste.row(eintrag)
        if zeile >= 0:
            self.meldungen_liste.takeItem(zeile)
        self.statusBar().showMessage(
            "Der nächste Export fragt wieder nach dem Zertifikat."
        )

    def _beispielmenue_pruefen(self) -> None:
        """Sperrt „Datei → Beispielprojekte" im Prüfungsmodus.

        Die Beispiele enthalten ausformulierte Lösungen zu genau den
        Themen, die geprüft werden. Gesperrt und nicht verschwunden:
        wer den Eintrag sucht, soll sehen, dass es ihn gibt und dass er
        gerade nicht geht - ein Menü, das sich von Stunde zu Stunde
        ändert, verwirrt mehr, als es schützt.
        """
        menue = getattr(self, "_beispiel_menue", None)
        if menue is None:
            return
        laeuft = pruefungsmodus_laeuft()
        menue.setEnabled(not laeuft and not menue.isEmpty())
        menue.setTitle(
            "Beispielprojekte (im Prüfungsmodus gesperrt)"
            if laeuft
            else "Beispielprojekte"
        )

    def _vervollstaendigung_pruefen(self) -> None:
        """Sperrt „Ansicht → Vervollständigung" im Prüfungsmodus.

        Der Editor fragt den Prüfungsmodus bei jedem Vorschlag selbst
        ab; der Menüeintrag zeigt nur an, warum gerade keiner kommt.
        Gesperrt und nicht verschwunden, aus demselben Grund wie bei den
        Beispielprojekten.
        """
        aktion = getattr(self, "vervollstaendigung_aktion", None)
        if aktion is None:
            return
        laeuft = pruefungsmodus_laeuft()
        aktion.setEnabled(not laeuft)
        aktion.setText(
            "Vervollständigung (im Prüfungsmodus aus)" if laeuft else "Vervollständigung"
        )

    def _startaktionen_pruefen(self) -> None:
        """Graut aus, was gerade nicht geht.

        Ohne offenes Projekt und ohne laufendes Programm waren alle
        acht Einträge unter „Start" anklickbar, und fünf davon taten
        beim Anklicken nachweislich nichts - kein Hinweis, keine
        Statuszeile. Der Knopf sah aus, als wäre er kaputt.

        Ausgegraut ist eine Auskunft: „geht jetzt nicht" statt „geht
        nicht". „Starten" und „Stopp" bleiben anklickbar, weil sie
        etwas Besseres können, als grau dazustehen - sie sagen, was
        stattdessen zu tun ist („Kein Projekt offen. Zuerst über
        „Projekt → Projekt öffnen …" eines laden").
        """
        laeuft = self.debug_sitzung is not None
        angehalten = laeuft and self._aktueller_thread_id is not None
        # „Pause“ gilt, solange das Programm läuft und nicht schon hält -
        # auch in einer Endlosschleife, die nie an einem Haltepunkt
        # vorbeikam (Punkt 56). Die Schrittbefehle gelten nur im Halt.
        self.aktionen["start.pause"].qaction.setEnabled(
            laeuft and not angehalten and self._faden_id is not None
        )
        for kennung in ("start.fortsetzen", "start.ruecksprung"):
            self.aktionen[kennung].qaction.setEnabled(angehalten)
        # „Ausführen bis Cursor“ startet das Programm auch, wenn noch
        # keins läuft; nur während es frei läuft, hat es keinen Sinn.
        # Einzelschritt und Prozedurschritt ebenso: ohne laufendes
        # Programm starten sie es und halten in der ersten Zeile
        # (Punkt 295). Bis dahin waren sie vor dem Start grau, und F11
        # tat nichts, genau beim ersten Versuch mit dem Debugger.
        for kennung in (
            "start.bis_cursor",
            "start.einzelschritt",
            "start.prozedurschritt",
        ):
            self.aktionen[kennung].qaction.setEnabled(not laeuft or angehalten)

    def _bearbeitenaktionen_pruefen(self) -> None:
        """Graut aus, was ohne offenen Reiter nichts bewirkt.

        Dieselbe Regel wie unter „Start": alle sechs Einträge unter
        „Bearbeiten" waren anklickbar, auch wenn gar nichts offen
        war, und alle sechs taten dann nichts. Rückgängig und
        Wiederholen wirken auch im Designer und hängen deshalb an
        seiner Zeichenfläche mit; die übrigen vier brauchen einen
        Texteditor.

        Geprüft wird der offene Reiter und nicht der Tastaturfokus:
        wer in den Projekt-Explorer klickt, soll seine Änderung
        trotzdem zurücknehmen können.
        """
        editor = self._aktueller_editor() is not None
        flaeche = self._aktueller_canvas is not None
        for kennung, moeglich in (
            ("bearbeiten.rueckgaengig", editor or flaeche),
            ("bearbeiten.wiederholen", editor or flaeche),
            # Seit Punkt 73 auch im Designer: dort mit Komponenten.
            ("bearbeiten.ausschneiden", editor or flaeche),
            ("bearbeiten.kopieren", editor or flaeche),
            ("bearbeiten.einfuegen", editor or flaeche),
            ("bearbeiten.alles_auswaehlen", editor or flaeche),
            ("bearbeiten.duplizieren", flaeche),
            ("bearbeiten.loeschen", flaeche),
            ("bearbeiten.anordnen", flaeche),
        ):
            self.aktionen[kennung].qaction.setEnabled(moeglich)

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
        lauf.vordergrund.connect(self._im_vordergrund_ausfuehren)
        lauf.fehlgeschlagen.connect(
            lambda meldung: self._hintergrund_fehler(fehlertext, meldung)
        )
        self._hintergrundarbeit = lauf
        lauf.start()
        return lauf

    def _im_vordergrund_ausfuehren(self, aufgabe: Callable[[], None]) -> None:
        """Führt eine Aufgabe aus `Hintergrundarbeit.im_vordergrund`
        aus. Als Methode des Fensters verbunden, damit Qt sie im
        Faden der Oberfläche zustellt."""
        aufgabe()

    def _hintergrund_prozess_melden(self, prozess: subprocess.Popen) -> None:
        """Nimmt einen Prozess entgegen, den ein Vorgang im Nebenfaden
        gestartet hat, und meldet ihn bei der laufenden
        Hintergrundarbeit an. Beim Schließen des Fensters beendet
        `_hintergrund_abbrechen` ihn samt Kindern (Punkt 254)."""
        lauf = self._hintergrundarbeit
        if lauf is not None:
            lauf.prozess_melden(prozess)

    def _hintergrund_abbrechen(self) -> None:
        """Bricht einen laufenden Vorgang beim Schließen ab.

        Bis 0.3.6 ging das Fenster zu, während der Faden noch lief. Qt
        beendete Natter dann mit einem Fehlercode, weil ein laufender
        `QThread` zerstört wurde, und der Prozess eines Testlaufs mit
        Endlosschleife rechnete ohne Elternteil weiter; die Zeitgrenze
        von 60 Sekunden gehörte zum Faden, den es nicht mehr gab.

        Gefragt wird nicht: ein halb gelaufener Test oder ein halb
        gebauter Export lässt sich jederzeit neu starten. Auf eine
        Abgabe-ZIP wartet vorher `_zip_abwarten` (Punkt 394). Die Signale
        werden vorher gelöst, damit kein Ergebnis mehr in ein Fenster
        schreibt, das gerade zugeht. Gewartet wird ohne Grenze: ein
        Faden, der beim Beenden noch läuft, bringt Natter zum Absturz.
        Nach dem Beenden der Prozesse kehrt die Arbeit sofort zurück;
        nur eine Paketinstallation läuft noch bis zum Ende von `pip`,
        und dafür ist das Fenster schon unsichtbar.
        """
        lauf = self._hintergrundarbeit
        if lauf is None or not lauf.isRunning():
            return
        for signal in (
            lauf.fortschritt, lauf.fertig, lauf.fehlgeschlagen,
            lauf.vordergrund,
        ):
            try:
                signal.disconnect()
            except (RuntimeError, TypeError):
                pass
        lauf.abbrechen()
        self.hide()
        lauf.wait()

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
        if not self._hintergrund_frei("Der Testlauf"):
            return
        # Wie „Alle Tests ausführen“: erst speichern, dann nebenher
        # laufen lassen. Ein Test mit Endlosschleife hielt sonst das
        # Fenster bis zum Zeitlimit an, und getestet wurde der alte
        # Stand auf der Platte (Punkt 185).
        if not self.alle_speichern():
            return
        ordner = self.projekt.ordner
        self.statusBar().showMessage(
            f"Test {test_id} läuft - die IDE bleibt bedienbar."
        )
        self._hintergrund_starten(
            lambda _melden: tests_ausfuehren(
                ordner,
                ziel=test_id,
                prozess_gestartet=self._hintergrund_prozess_melden,
            ),
            lambda ergebnisse: self._einzeltest_fertig(test_id, ergebnisse),
            "Testlauf fehlgeschlagen",
        )

    def _test_eintrag_finden(self, test_id: str) -> QTreeWidgetItem | None:
        """Der Baumeintrag mit dieser Test-ID, falls es ihn noch gibt.

        Nach einem Lauf im Hintergrund wird neu gesucht: in der
        Zwischenzeit kann „Alle Tests ausführen“ den Baum neu
        aufgebaut haben."""
        stapel = [
            self.tests_baum.topLevelItem(i)
            for i in range(self.tests_baum.topLevelItemCount())
        ]
        while stapel:
            eintrag = stapel.pop()
            if eintrag.data(0, _TEST_ID_ROLLE) == test_id:
                return eintrag
            stapel.extend(eintrag.child(i) for i in range(eintrag.childCount()))
        return None

    def _einzeltest_fertig(
        self, test_id: str, ergebnisse: list[Testergebnis]
    ) -> None:
        """Die Auswertung eines Doppelklicks, zurück im Faden der
        Oberfläche."""
        eintrag = self._test_eintrag_finden(test_id)
        if eintrag is None:
            return
        nicht_bestanden = sum(1 for e in ergebnisse if e.status != "bestanden")
        self.statusBar().showMessage(
            f"{test_id}: {len(ergebnisse)} gelaufen, {nicht_bestanden} "
            f"nicht bestanden."
        )
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
            self.statusBar().showMessage(self._kein_projekt_text())
            return
        self.unit_erzeugen()

    def _unit_umbenennen(self, pfad: Path) -> None:
        """„⋮ → Umbenennen …“ im Projekt-Explorer: benennt die
        Datei auf der Platte um und hält
 einen ggf. offenen Editor-Tab dabei synchron.

        Ein Diagramm und die Unit eines Formulars gehen weiter an
        `_diagramm_umbenennen` bzw. `_formular_umbenennen` (Punkt 221).
        """
        if pfad.suffix == ".pdiag":
            self._diagramm_umbenennen(pfad)
            return
        if pfad.suffix == ".pfm" or pfad.with_suffix(".pfm").exists():
            self._formular_umbenennen(pfad.with_suffix(".pfm"))
            return
        neuer_name, ok = QInputDialog.getText(
            self, "Unit umbenennen", "Neuer Dateiname:", text=pfad.name
        )
        neuer_name = neuer_name.strip()
        if not ok or not neuer_name or neuer_name == pfad.name:
            return
        if not neuer_name.endswith(".py"):
            neuer_name += ".py"
        # Nur Namen, unter denen sich die Unit importieren lässt, und
        # keiner auf „_design“: solche Dateien gelten als erzeugt und
        # verschwinden aus dem Explorer (Punkt 154). „Neues Formular …“
        # lehnt dieselben Namen ab.
        stamm = neuer_name[: -len(".py")]
        if not stamm.isidentifier() or keyword.iskeyword(stamm):
            self._umbenennen_ablehnen(
                f"„{stamm}“ taugt nicht als Name einer Unit: erlaubt sind "
                "Buchstaben, Ziffern und Unterstrich, ohne Leerzeichen und "
                "nicht mit einer Ziffer am Anfang, etwa u_konto2."
            )
            return
        if stamm.endswith("_design"):
            self._umbenennen_ablehnen(
                f"„{stamm}“ endet auf „_design“. So heißen die Dateien, die "
                "Natter aus dem Designer erzeugt; eine Unit mit diesem Namen "
                "wäre im Projekt-Explorer nicht mehr zu sehen."
            )
            return
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
        angepasst = self._importe_nachfuehren(pfad.stem, stamm)
        if self.projekt is not None:
            self.explorer.projekt_anzeigen(self.projekt)
        meldung = f"„{pfad.name}“ zu „{neuer_name}“ umbenannt."
        if angepasst:
            meldung += f" Import angepasst in {_aufzaehlung(angepasst)}."
        self.statusBar().showMessage(meldung)

    def _umbenennen_ablehnen(
        self, text: str, titel: str = "Unit umbenennen"
    ) -> None:
        QMessageBox.warning(self, titel, text)
        self.statusBar().showMessage(text)

    def _ist_hauptformular(self, pfad: Path) -> bool:
        """Ob `pfad` zu dem Formular gehört, das `main.py` startet."""
        return (
            self.projekt is not None
            and self.projekt.typ != "console"
            and Path(pfad).stem == self.projekt.haupt_unit
        )

    def _formular_umbenennen(self, pfm: Path) -> None:
        """„⋮ → Umbenennen …“ an einem Formular oder seiner Unit
        (Punkt 221).

        `.pfm`, Unit und `_design.py` heißen immer gleich; nur so
        findet eins zum anderen. Umbenannt werden deshalb alle drei,
        dazu `from u_alt import …` und `from u_alt_design import …` in
        den Dateien des Projekts. Der Name der Klasse bleibt, wie er
        ist. Die `_design.py` wird unter dem neuen Namen aus der
        `.pfm` neu erzeugt, statt sie umzubenennen: ihre erste Zeile
        nennt die `.pfm`, aus der sie stammt."""
        titel = "Formular umbenennen"
        alt = pfm.stem
        if self.projekt is None:
            return
        if self._ist_hauptformular(pfm):
            self._umbenennen_ablehnen(
                f"„{alt}“ ist das Hauptformular; main.py startet es "
                "unter diesem Namen.",
                titel,
            )
            return
        eingabe, ok = QInputDialog.getText(
            self, titel, "Neuer Name der Unit (beginnt mit u_):", text=alt
        )
        neu = eingabe.strip()
        if neu.endswith((".py", ".pfm")):
            neu = neu.rsplit(".", 1)[0]
        if not ok or not neu or neu == alt:
            return
        # Dieselben Regeln wie bei „Neues Formular …“ und „Unit
        # umbenennen …“.
        if (
            not neu.isidentifier()
            or keyword.iskeyword(neu)
            or not neu.startswith("u_")
        ):
            self._umbenennen_ablehnen(
                f"„{neu}“ taugt nicht als Name: erlaubt sind Buchstaben, "
                "Ziffern und Unterstrich, am Anfang „u_“, etwa "
                "u_einstellungen.",
                titel,
            )
            return
        if neu.endswith("_design"):
            self._umbenennen_ablehnen(
                f"„{neu}“ endet auf „_design“. So heißen die Dateien, die "
                "Natter aus dem Designer erzeugt.",
                titel,
            )
            return
        ordner = pfm.parent
        unit = ordner / f"{alt}.py"
        design = ordner / f"{alt}_design.py"
        eigene = {alt.casefold(), f"{alt}_design".casefold()}
        # Windows unterscheidet in Dateinamen nicht zwischen Groß- und
        # Kleinschreibung; verglichen wird deshalb ohne Rücksicht
        # darauf. Die eigenen drei Dateien zählen nicht mit, sonst
        # ließe sich u_zweit nicht in u_Zweit umbenennen.
        vorhandene = {
            p.stem.casefold() for p in self.projekt.alle_python_dateien()
        }
        vorhandene |= {p.stem.casefold() for p in self.projekt.formulare()}
        vorhandene -= eigene
        ziel_pfm = ordner / f"{neu}.pfm"
        ziel_unit = ordner / f"{neu}.py"
        if (
            neu.casefold() in vorhandene
            or f"{neu}_design".casefold() in vorhandene
            or any(
                z.exists() and z.stem.casefold() not in eigene
                for z in (ziel_pfm, ziel_unit, ordner / f"{neu}_design.py")
            )
        ):
            self._umbenennen_ablehnen(
                f"„{neu}“ gibt es schon - bitte einen anderen Namen wählen.",
                titel,
            )
            return

        # Der Designer schreibt bei jeder Änderung in seine `.pfm`.
        # Offen bliebe er auf den alten Namen gerichtet und legte die
        # alten Dateien wieder an (vgl. Punkt 139). Er geht zu und
        # unter dem neuen Namen wieder auf; zu verlieren gibt es
        # dabei nichts, weil er nichts ungespeichert hält. Ein
        # Reiter mit der erzeugten Datei geht ebenfalls zu.
        pfm_weg = pfm.resolve()
        design_weg = design.resolve()
        designer_offen = any(
            self._reiter_pfad(i) == pfm_weg
            for i in range(self.editor_tabs.count())
        )
        self._reiter_schliessen_wenn(
            lambda datei: datei in (pfm_weg, design_weg)
        )

        try:
            pfm.rename(ziel_pfm)
            try:
                if unit.exists():
                    unit.rename(ziel_unit)
            except OSError:
                ziel_pfm.rename(pfm)
                raise
        except OSError as fehler:
            self.statusBar().showMessage(
                f"Umbenennen fehlgeschlagen: {fehler}. Ist eine der Dateien "
                "gerade in einem anderen Programm geöffnet?"
            )
            return
        try:
            design.unlink(missing_ok=True)
        except OSError:
            pass
        self._design_datei_abgleichen(ziel_pfm)

        self._offenen_tab_pfad_aktualisieren(unit, ziel_unit)
        angepasst = self._importe_nachfuehren(alt, neu)
        for name in self._importe_nachfuehren(f"{alt}_design", f"{neu}_design"):
            if name not in angepasst:
                angepasst.append(name)
        self.explorer.projekt_anzeigen(self.projekt)
        if designer_offen:
            self.designer_oeffnen(ziel_pfm)
        meldung = f"Formular „{alt}“ in „{neu}“ umbenannt."
        if angepasst:
            meldung += f" Import angepasst in {_aufzaehlung(angepasst)}."
        self.statusBar().showMessage(meldung)

    def _diagramm_fenster_zu(self, pfad: Path) -> tuple[bool, bool]:
        """Schließt das Fenster eines offenen Diagramms, wie „Datei →
        Schließen“ es täte, samt Frage nach ungespeicherten Änderungen.

        Zurück kommt (war offen, ist zu). Wer die Frage abbricht,
        behält das Fenster, und das zweite ist `False`."""
        ziel = Path(pfad).resolve()
        for schluessel, fenster in list(self._offene_diagramme.items()):
            if Path(schluessel).resolve() != ziel:
                continue
            if not fenster.close():
                return True, False
            self._offene_diagramme.pop(schluessel, None)
            fenster.deleteLater()
            return True, True
        return False, True

    def _diagramm_umbenennen(self, pfad: Path) -> None:
        """„⋮ → Umbenennen …“ an einem Diagramm (Punkt 221). Ein offenes
        Diagrammfenster geht zu, mit der üblichen Frage nach dem
        Speichern, und unter dem neuen Namen wieder auf."""
        titel = "Diagramm umbenennen"
        eingabe, ok = QInputDialog.getText(
            self, titel, "Neuer Name des Diagramms:", text=pfad.stem
        )
        neu = eingabe.strip()
        if neu.lower().endswith(".pdiag"):
            neu = neu[: -len(".pdiag")].strip()
        if not ok or not neu or neu == pfad.stem:
            return
        fehler = _dateiname_fehler(neu)
        if fehler is not None:
            self._umbenennen_ablehnen(fehler, titel)
            return
        ziel = pfad.parent / f"{neu}.pdiag"
        andere = {
            p.stem.casefold()
            for p in pfad.parent.glob("*.pdiag")
            if p.stem.casefold() != pfad.stem.casefold()
        }
        if neu.casefold() in andere:
            self._umbenennen_ablehnen(
                f"„{neu}“ gibt es schon - bitte einen anderen Namen wählen.",
                titel,
            )
            return

        war_offen, zu = self._diagramm_fenster_zu(pfad)
        if not zu:
            return
        try:
            pfad.rename(ziel)
        except OSError as fehler:
            self.statusBar().showMessage(
                f"Umbenennen fehlgeschlagen: {fehler}. Ist die Datei gerade "
                "in einem anderen Programm geöffnet?"
            )
            return
        if self.projekt is not None:
            self.explorer.projekt_anzeigen(self.projekt)
        if war_offen:
            self.diagramm_oeffnen(ziel)
        self.statusBar().showMessage(
            f"„{pfad.name}“ zu „{ziel.name}“ umbenannt."
        )

    def _diagramm_loeschen(self, pfad: Path) -> None:
        """„⋮ → Löschen …“ an einem Diagramm (Punkt 221): fragt nach,
        schließt ein offenes Fenster ohne weitere Frage und legt die
        Datei in den Papierkorb."""
        mit_papierkorb = papierkorb_verfuegbar(pfad)
        folge = (
            "Die Datei landet im Papierkorb und lässt sich von dort "
            "zurückholen."
            if mit_papierkorb
            else "Dieses Laufwerk hat keinen Papierkorb: die Datei wird "
            "endgültig gelöscht und lässt sich nicht zurückholen."
        )
        if not self._loeschen_bestaetigt(
            "Diagramm löschen",
            f"Das Diagramm „{pfad.stem}“ wirklich löschen? {folge}",
            mit_papierkorb,
        ):
            return
        ziel = pfad.resolve()
        for schluessel, fenster in list(self._offene_diagramme.items()):
            if Path(schluessel).resolve() == ziel:
                # Gelöscht wird ohnehin; die Frage nach dem Speichern
                # wäre hier eine zweite, widersprüchliche.
                fenster._geaendert = False
                fenster.close()
                self._offene_diagramme.pop(schluessel, None)
                fenster.deleteLater()
        try:
            if not self._datei_loeschen(pfad, mit_papierkorb):
                return
        except OSError as fehler:
            self.statusBar().showMessage(
                f"Löschen fehlgeschlagen: {fehler}. Ist die Datei gerade in "
                "einem anderen Programm geöffnet?"
            )
            return
        if self.projekt is not None:
            self.explorer.projekt_anzeigen(self.projekt)
        self.statusBar().showMessage(f"„{pfad.name}“ gelöscht.")

    def _importe_nachfuehren(self, alt: str, neu: str) -> list[str]:
        """Schreibt `from alt import …` und `import alt` in den anderen
        Dateien des Projekts auf den neuen Namen um und liefert deren
        Namen.

        Bis 0.3.5 blieb `from u_konto import Konto` stehen, und das
        Programm startete nach dem Umbenennen nicht mehr. `import alt`
        wird zu `import neu as alt`, damit `alt.etwas` im Code
        weiter stimmt. Eine offene Datei wird im Editor geändert,
        damit ungespeicherte Arbeit darin nicht überschrieben wird;
        war sie vorher gespeichert, wird sie es danach wieder.
        """
        if self.projekt is None:
            return []
        name = re.escape(alt)
        # Auch eine auskommentierte Zeile `# from alt import …`: die
        # Vorlage eines weiteren Formulars zeigt oben so, wie es sich
        # öffnen lässt (Punkt 221).
        muster = [
            (
                re.compile(rf"^(\s*(?:#\s*)?from\s+){name}(\s+import\b)", re.M),
                rf"\g<1>{neu}\g<2>",
            ),
            (
                re.compile(rf"^(\s*import\s+){name}(\s+as\b)", re.M),
                rf"\g<1>{neu}\g<2>",
            ),
            (
                re.compile(rf"^(\s*import\s+){name}(?=[ \t]*(#.*)?$)", re.M),
                rf"\g<1>{neu} as {alt}",
            ),
        ]
        angepasst: list[str] = []
        for datei in self.projekt.alle_python_dateien():
            # Erzeugte Dateien schreibt nur der Generator.
            if datei.stem.endswith("_design"):
                continue
            editor = next(
                (
                    e
                    for e in (
                        self._tab_inhalt(self.editor_tabs.widget(i))
                        for i in range(self.editor_tabs.count())
                    )
                    if isinstance(e, QPlainTextEdit)
                    and e.property(_PFAD_EIGENSCHAFT) == str(datei)
                ),
                None,
            )
            text = self._aktueller_text_von(datei)
            neuer_text = text
            for regel, ersatz in muster:
                neuer_text = regel.sub(ersatz, neuer_text)
            if neuer_text == text:
                continue
            if editor is None:
                if not self.datei_schreiben_gemeldet(datei, neuer_text):
                    continue
            else:
                war_gespeichert = not editor.document().isModified()
                cursor = QTextCursor(editor.document())
                cursor.select(QTextCursor.SelectionType.Document)
                cursor.insertText(neuer_text)
                if war_gespeichert:
                    self._editor_speichern(editor)
            angepasst.append(datei.name)
        return angepasst

    def _loeschen_bestaetigt(
        self, titel: str, text: str, mit_papierkorb: bool
    ) -> bool:
        """Die Nachfrage vor dem Löschen. Ohne Papierkorb ist „Nein“
        vorausgewählt, damit ein schnelles Enter nichts endgültig löscht
        (Punkt 273)."""
        knoepfe = QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        if mit_papierkorb:
            antwort = QMessageBox.question(self, titel, text, knoepfe)
        else:
            antwort = QMessageBox.question(
                self, titel, text, knoepfe, QMessageBox.StandardButton.No
            )
        return antwort == QMessageBox.StandardButton.Yes

    def _datei_loeschen(self, datei: Path, mit_papierkorb: bool) -> bool:
        """Legt `datei` in den Papierkorb oder löscht sie endgültig, je
        nachdem, was die Nachfrage zugesagt hat. Liefert `False` und
        meldet es, wenn der zugesagte Papierkorb die Datei nicht
        angenommen hat; gelöscht ist dann nichts.

        Bis 0.3.6 wurde in diesem Fall ohne weitere Frage endgültig
        gelöscht, obwohl die Nachfrage den Papierkorb versprochen hatte
        (Punkt 273).
        """
        if not mit_papierkorb:
            datei.unlink()
            return True
        if in_den_papierkorb(datei):
            return True
        self.statusBar().showMessage(
            f"„{datei.name}“ ließ sich nicht in den Papierkorb legen und "
            "wurde nicht gelöscht."
        )
        return False

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
        if pfad.suffix == ".pdiag":
            self._diagramm_loeschen(pfad)
            return
        ist_formular = pfad.with_suffix(".pfm").exists()
        if ist_formular and self._ist_hauptformular(pfad):
            # Punkt 221: ohne das Hauptformular startet main.py nicht
            # mehr. Der Explorer bietet hier gar kein Menü an; das ist
            # die zweite Sicherung.
            self.statusBar().showMessage(
                f"„{pfad.stem}“ ist das Hauptformular und lässt sich nicht "
                "löschen; main.py startet es."
            )
            return
        if ist_formular:
            # Vom Formular-Eintrag kommt die `.pfm`; gefragt wird aber
            # nach der Unit, wie von der Unit aus.
            unit = pfad.with_suffix(".py")
            if unit.exists():
                pfad = unit
        betroffen = (
            self.projekt.zusammengehoerige_dateien(pfad) if self.projekt is not None else [pfad]
        )
        weitere = [p for p in betroffen if p != pfad]

        mit_papierkorb = papierkorb_verfuegbar(pfad)
        folge = (
            "Die Dateien landen im Papierkorb und lassen sich von dort zurückholen."
            if mit_papierkorb
            else "Dieses Laufwerk hat keinen Papierkorb: die Dateien werden "
            "endgültig gelöscht und lassen sich nicht zurückholen."
        )
        dazu = (
            f" Dazu gehört {_aufzaehlung([p.name for p in weitere])}." if weitere else ""
        )
        if not self._loeschen_bestaetigt(
            "Formular löschen" if ist_formular else "Unit löschen",
            f"„{pfad.name}“ wirklich löschen?{dazu} {folge}",
            mit_papierkorb,
        ):
            return

        # Auch der Designer-Reiter muss zu (Punkt 139). Er blieb bis
        # 0.3.5 offen, und die nächste Änderung darin schrieb `.pfm`
        # und `_design.py` wieder auf die Platte, die Unit aber nicht.
        weg = {p.resolve() for p in betroffen}
        self._reiter_schliessen_wenn(lambda datei: datei in weg)

        for datei in betroffen:
            try:
                if not self._datei_loeschen(datei, mit_papierkorb):
                    return
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

    def _datenbank_nach_vorn(self) -> None:
        """Nach „Ansicht → Datenbank“: der Reiter kommt nach vorn, und
        das Dock bekommt genug Höhe für ein paar Ergebniszeilen
        (Punkt 303). Kleiner gezogen wird es danach nur von Hand."""
        self.datenbank_dock.raise_()
        # Rund 360 Pixel reichen für fünf Ergebniszeilen; der Designer
        # oder Editor darüber behält mindestens 130.
        mitte = self.centralWidget().height() + self.datenbank_dock.height()
        ziel = max(self.datenbank_dock.height(), min(360, mitte - 130))
        self.resizeDocks(
            [self.datenbank_dock], [ziel], Qt.Orientation.Vertical
        )

    def _dock_erzeugen(
        self, titel: str, bereich: Qt.DockWidgetArea, inhalt: QWidget | None = None
    ) -> QDockWidget:
        dock = QDockWidget(titel, self)
        dock.setObjectName(titel)  # von QMainWindow.saveState()/restoreState() benötigt
        dock.setToolTip(DOCK_HINWEISE.get(titel, titel))
        inhalt = inhalt if inhalt is not None else QWidget()
        # Eine feste, kleine Mindesthöhe statt der aus dem Inhalt
        # berechneten: Objektinspektor, Palette und Panels verlangten
        # zusammen 560 Pixel Höhe, mehr als bei 150 % Skalierung auf
        # 1366 × 768 übrig bleiben (rund 480). Das Fenster ragte dann
        # unter die Taskleiste (Punkt 299). Enger zusammenschieben
        # lässt sich ein Dock jetzt nur noch von Hand. Die Palette oben
        # behält ihre Höhe, sonst werden ihre Symbole abgeschnitten.
        if bereich != Qt.DockWidgetArea.TopDockWidgetArea:
            inhalt.setMinimumHeight(
                min(_DOCK_MINDESTHOEHE, inhalt.minimumSizeHint().height())
            )
        dock.setWidget(inhalt)
        self.addDockWidget(bereich, dock)
        return dock

    def _formular_docks_anpassen(self) -> None:
        """Blendet Palette und Objektinspektor in einem Konsolenprojekt
        aus, solange kein Designer offen ist (Punkt 348).

        Dort gibt es kein Formular, auf das sich eine Komponente legen
        ließe, und nichts, dessen Eigenschaften der Inspektor zeigen
        könnte. Bei 150 % auf 1280 × 800 blieb dem Editor neben den
        beiden ein Zehntel des Fensters. Wieder gezeigt wird nur, was
        hier verborgen wurde: ein Dock, das jemand selbst über
        „Ansicht“ geschlossen hat, bleibt zu. Welche das sind, wird
        gemerkt, denn die Sichtbarkeit steht auch im gespeicherten
        Layout: nach einem Neustart im Konsolenprojekt kämen die Docks
        sonst beim nächsten GUI-Projekt nicht wieder.
        """
        ohne_formular = (
            self.projekt is not None
            and self.projekt.typ == "console"
            and not self._offene_canvases
        )
        for dock in (self.palette_dock, self.inspektor_dock):
            name = dock.objectName()
            if ohne_formular and not dock.isHidden():
                dock.hide()
                self._fuer_konsole_verborgen.add(name)
            elif not ohne_formular and name in self._fuer_konsole_verborgen:
                dock.show()
                self._fuer_konsole_verborgen.discard(name)
        self._design_einstellungen.setValue(
            "fenster/fuer_konsole_verborgen",
            sorted(self._fuer_konsole_verborgen),
        )

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802 - Qt-Name
        super().resizeEvent(event)
        self._aufteilung_nach_hoehe()

    def _aufteilung_nach_hoehe(self) -> None:
        """Bei wenig Höhe bekommt der Objektinspektor die ganze rechte
        Seite (Punkt 437).

        Palette oben und Panels unten liefen sonst über die volle
        Breite und nahmen dem Inspektor ihre Höhe weg: bei 1280 × 800
        mit 150 % blieb unter „Eigenschaft | Wert“ keine einzige Zeile,
        bei 1366 × 768 mit 125 % waren es zwei. Gehören die beiden
        rechten Ecken dem rechten Dockbereich, enden Palette und Panels
        am Inspektor, und er reicht von der Werkzeugleiste bis zur
        Statuszeile. Punkt 348 blendet beide Docks nur in
        Konsolenprojekten aus; hier werden sie gebraucht und bleiben.

        Auf einem großen Bildschirm bleibt alles, wie es war."""
        knapp = self.height() < KNAPPE_FENSTERHOEHE
        if knapp == self._knappe_hoehe:
            return
        self._knappe_hoehe = knapp
        rechts = Qt.DockWidgetArea.RightDockWidgetArea
        self.setCorner(
            Qt.Corner.TopRightCorner,
            rechts if knapp else Qt.DockWidgetArea.TopDockWidgetArea,
        )
        self.setCorner(
            Qt.Corner.BottomRightCorner,
            rechts if knapp else Qt.DockWidgetArea.BottomDockWidgetArea,
        )
        self.objektinspektor.knapp_setzen(knapp)

    def menue(self, titel: str):
        """Liefert das Menü mit diesem Titel (Abschnitt 7.2)."""
        return self._menues[titel]

    def _startbild_umschalten(self, *_werte: object) -> None:
        """Zeigt das Startbild, solange kein Reiter offen ist."""
        leer = self.editor_tabs.count() == 0
        self.mitte.setCurrentWidget(self.startbild if leer else self.editor_tabs)

    def _startseite_aktion(self) -> None:
        """„Ansicht → Startseite“.

        Bis dahin gab es keinen Weg dorthin zurück: das Startbild
        erschien nur, solange kein einziger Reiter offen war. Wer ein
        anderes Projekt öffnen wollte, musste erst jede Datei
        schließen - oder den Weg über „Projekt → Projekt öffnen …“
        kennen und auf die Liste der zuletzt geöffneten verzichten.

        Die Reiter bleiben dabei offen; das Startbild legt sich nur
        davor. Zurück geht es über den ersten Knopf dort oder über
        denselben Menüeintrag.
        """
        if self.mitte.currentWidget() is self.startbild and self.editor_tabs.count():
            self._zurueck_zur_arbeit()
            return
        self.startbild.offenes_projekt = self.projekt.name if self.projekt else None
        # Neu aufbauen, damit „Zuletzt geöffnet“ den heutigen Stand
        # zeigt und der Rückkehr-Knopf den richtigen Namen trägt.
        self.startbild.aufbauen()
        self.mitte.setCurrentWidget(self.startbild)
        self.statusBar().showMessage(
            "Startseite. Über „Ansicht → Startseite“ geht es zurück zur Arbeit."
        )

    def _zurueck_zur_arbeit(self) -> None:
        """Zurück zu den geöffneten Dateien, ohne etwas zu schließen."""
        if self.editor_tabs.count() == 0:
            self.statusBar().showMessage(
                "Es ist keine Datei offen - im Projekt-Explorer links eine auswählen."
            )
            return
        self.mitte.setCurrentWidget(self.editor_tabs)
        self.statusBar().showMessage("")

    def hilfe_zeigen(
        self, titel: str, markdown: str, inhaltsverzeichnis: bool = False
    ) -> HilfeAnsicht:
        """Öffnet eine Hilfeseite als eigenen Reiter – lesbar gesetzt,
        im Programm. Lange Seiten bekommen oben ein Inhaltsverzeichnis
        (Punkt 438).

        Ein zweiter Aufruf mit demselben Titel holt den vorhandenen
        Reiter nach vorn, statt einen zweiten aufzumachen.
        """
        for index in range(self.editor_tabs.count()):
            widget = self.editor_tabs.widget(index)
            if isinstance(widget, HilfeAnsicht) and (
                self.editor_tabs.tabText(index) == titel
            ):
                widget.markdown_setzen(markdown, inhaltsverzeichnis)
                self.editor_tabs.setCurrentIndex(index)
                return widget

        ansicht = HilfeAnsicht()
        ansicht.dunkel = theme_aufloesen(self._design_thema) == "dark"
        ansicht.markdown_setzen(markdown, inhaltsverzeichnis)
        index = self.editor_tabs.addTab(ansicht, titel)
        self.editor_tabs.setCurrentIndex(index)
        self._panel_schrift_anpassen()
        return ansicht

    def _hilfedatei_zeigen(
        self, dateiname: str, titel: str, inhaltsverzeichnis: bool = False
    ) -> bool:
        """Eine Hilfeseite aus `docs/`. Liefert `False`, wenn es sie
        nicht gibt; die Meldung sagt dann, wo sie liegen müsste."""
        # `daten_ordner` statt eines eigenen relativen Pfads: wo die
        # mitgelieferten Ordner liegen, steht an einer einzigen Stelle.
        pfad = daten_ordner("docs") / dateiname
        if not pfad.exists():
            self.statusBar().showMessage(
                f"„{titel}“ ist nicht mitgekommen. Die Seite liegt in "
                f"docs/{dateiname}; eine neue Installation bringt sie mit."
            )
            return False
        self.hilfe_zeigen(
            titel, pfad.read_text(encoding="utf-8"), inhaltsverzeichnis
        )
        return True

    def _erste_schritte_aktion(self) -> bool:
        """„Erste Schritte“ – vom Startbild und aus dem Menü „Hilfe“.

        Bis M11 öffnete der Eintrag die `.md`-Datei im
        Quelltexteditor: eine Anleitung mit `##` und `*` davor, in
        einem Fenster, das nach Programmieren aussieht und in dem man
        sie versehentlich ändern kann.
        """
        return self._hilfedatei_zeigen("erste_schritte.md", "Erste Schritte")

    def _handbuch_aktion(self) -> bool:
        """„Hilfe → Handbuch“ (Punkt 307).

        Das Handbuch lag vorher nur als HTML im Paket für Lehrkräfte.
        Wer vor der Klasse nachsehen wollte, wie der Prüfungsmodus
        oder das Zurücksetzen eines Beispiels geht, fand es in Natter
        nicht."""
        return self._hilfedatei_zeigen("handbuch.md", "Handbuch", True)

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

    def _beispiel_gesperrt(self, pfad: Path) -> bool:
        """Ob `pfad` im Prüfungsmodus nicht geöffnet werden darf, weil
        es ein mitgeliefertes Beispiel oder eine Arbeitskopie davon
        ist. Die Beispiele enthalten ausgearbeitete Lösungen; gesperrt
        war bis dahin nur das Menü, „Projekt öffnen …“ führte weiter
        hinein. Meldet die Sperre gleich selbst.

        `pfad` darf auch eine einzelne Datei darin sein: über
        „Datei → Öffnen …“ ließ sich sonst jede Unit eines Beispiels
        für sich öffnen (Punkt 211)."""
        if not pruefungsmodus_laeuft():
            return False
        ordner = _beispiel_projektordner(Path(pfad))
        if ordner is None:
            return False
        QMessageBox.information(
            self,
            "Beispielprojekt gesperrt",
            f"„{ordner.name}“ ist ein mitgeliefertes Beispielprojekt "
            f"oder eine Kopie davon.\n\n{GESPERRT_HINWEIS}",
        )
        self.statusBar().showMessage(
            f"Beispielprojekte: {GESPERRT_HINWEIS}"
        )
        return True

    def beispiel_oeffnen(self, projektdatei: Path) -> Projekt | None:
        """Öffnet ein mitgeliefertes Beispielprojekt – als Kopie im
        Dokumente-Ordner.

        An Ort und Stelle zu öffnen ginge in einer installierten Natter
        nicht: die Beispiele liegen dann im Programmordner, in den eine
        Schülerin nicht schreiben darf. Und selbst wo es ginge, wäre es
        falsch – das Beispiel soll beim nächsten Mal wieder im
        Ursprungszustand dastehen.

        Lässt sich die Kopie nicht anlegen, kommt eine Meldung mit dem
        Zielordner und den üblichen Gründen, und zurück kommt `None`
        (Punkt 320). Vorher ging der `OSError` über den Menüeintrag
        bis in die Absturzmeldung, und die Startseite meldete ihn als
        fehlende Projektdatei, obwohl das Original da war.
        """
        if self._beispiel_gesperrt(Path(projektdatei)):
            return None
        try:
            kopie = self._beim_kopieren(
                f"Das Beispiel „{Path(projektdatei).stem}“ wird kopiert …",
                lambda: beispiel_kopieren(Path(projektdatei)),
            )
        except OSError as fehler:
            self._kopie_nicht_angelegt_melden(
                "Beispiel nicht geöffnet",
                "Beispiele öffnet Natter als Arbeitskopie. Die Kopie ließ "
                "sich nicht anlegen in",
                beispielkopien_ordner(), fehler,
            )
            return None
        projekt = self.projekt_oeffnen(kopie)
        if projekt is None or projekt.ordner.resolve() != kopie.parent.resolve():
            # Bei der Nachfrage zum vorigen Projekt abgebrochen.
            return projekt
        self.statusBar().showMessage(
            f"Beispiel „{projekt.name}“ nach {kopie.parent} kopiert und geöffnet."
        )
        return projekt

    def _kopie_nicht_angelegt_melden(
        self, titel: str, satz: str, ziel: Path,
        fehler: BaseException | None = None,
    ) -> None:
        """Meldung, wenn eine Arbeitskopie unter „Dokumente“ scheitert
        (Punkte 320, 321).

        Der Text von Windows („[WinError 3] …“) bleibt draußen: er
        nennt einen Pfad, aber nicht, was Natter dort wollte. Hält ein
        anderes Programm eine Datei der Vorlage offen (`DateiGesperrt`),
        nennt die Meldung sie (Punkt 395); eine halbe Kopie bleibt dann
        nicht liegen."""
        if isinstance(fehler, DateiGesperrt):
            self.statusBar().showMessage(
                f"Nicht kopiert: {fehler.pfad.name} ließ sich nicht lesen."
            )
            QMessageBox.warning(
                self,
                titel,
                f"„{fehler.pfad.name}“ in\n{fehler.pfad.parent}\nließ "
                "sich nicht kopieren. Vermutlich ist die Datei gerade in "
                "einem anderen Programm geöffnet, etwa in Excel.\n\n"
                f"In\n{ziel}\nist keine Kopie entstanden. Nach dem "
                "Schließen der Datei dort lässt sich das Projekt noch "
                "einmal öffnen.",
            )
            return
        QMessageBox.warning(
            self,
            titel,
            f"{satz}\n{ziel}\n\n"
            "Mögliche Gründe: Das Netzlaufwerk mit „Dokumente“ ist nicht "
            "verbunden, das Konto darf dort nicht schreiben, oder der "
            "Speicherplatz ist voll.",
        )

    def projekt_oeffnen(
        self, pfad: Path, *, sperrhinweis: bool = True
    ) -> Projekt | None:
        """„Projekt öffnen …“ (Abschnitt 7.2): lädt das Projekt und füllt
        den Projekt-Explorer.

        Reiter und Diagrammfenster des vorigen Projekts gehen dabei
        zu, nach derselben Nachfrage wie beim Beenden (Punkt 152). Wird
        sie abgebrochen, bleibt das vorige Projekt offen, und zurück
        kommt dieses. Ohne `sperrhinweis` bleibt der Hinweis auf eine
        fremde Sperre aus; `projekt_oeffnen_gemeldet` hat dann schon
        danach gefragt."""
        neu = Projekt.laden(Path(pfad))
        dasselbe = self.projekt is not None and (
            self.projekt.ordner.resolve() == neu.ordner.resolve()
        )
        if not self._vorheriges_projekt_schliessen(neu.ordner):
            self.statusBar().showMessage("Das Projekt wurde nicht gewechselt.")
            return self.projekt
        if self.projekt is not None:
            sperre.freigeben(self.projekt.ordner)
        if not dasselbe:
            self._sicherung_eigen = False
            self._haltepunkte_ablegen()
            self._gemerkte_haltepunkte.clear()
        anderes_fenster = sperre.anderer_besitzer(neu.ordner)
        # Die Sperre eines anderen Fensters bleibt stehen; die
        # Originale der Beispiele öffnet Natter nie zum Bearbeiten.
        if anderes_fenster is None and not ist_beispiel_original(neu.ordner):
            sperre.sperren(neu.ordner)
        self.projekt = neu
        self._projekt_datei = _projektdatei_zu(Path(pfad))
        if not dasselbe:
            self._gemerkte_haltepunkte = haltepunkte_laden(
                self._design_einstellungen, self._projekt_datei, neu.ordner
            )
        # Gibt die Datenbankdatei des alten Projekts frei; ein
        # Dateiname ohne Pfad gilt ab jetzt im neuen Projektordner
        # (Punkt 244).
        self.datenbank_panel.projektordner_setzen(neu.ordner)
        zuletzt_merken(self._design_einstellungen, Path(pfad))
        self.startbild.aufbauen()
        self.explorer.projekt_anzeigen(self.projekt)
        self._formular_docks_anpassen()
        self.statusBar().showMessage(f"Projekt {self.projekt.name} geöffnet")
        self._zuruecksetzen_pruefen()
        # Angeboten wird auch bei einer fremden Sperre: welcher Anteil
        # der Sicherung zu einem noch laufenden Fenster gehört,
        # entscheidet `_sicherung_anbieten` je Anteil (Punkt 400).
        if not dasselbe and not ist_beispiel_original(neu.ordner):
            self._sicherung_anbieten()
        if anderes_fenster is not None and sperrhinweis:
            self._projekt_schon_offen_melden(
                self.projekt.name, anderes_fenster
            )
        return self.projekt

    def projekt_schliessen(self) -> bool:
        """„Projekt → Projekt schließen“ (Punkt 306).

        Am Stundenende kommt die nächste Klasse an denselben Rechner,
        und vorher ließ sich das Projekt der Vorgängerin nur loswerden,
        indem ein anderes geöffnet oder Natter beendet wurde. Gefragt
        wird wie beim Wechsel; danach sind Reiter und Diagrammfenster
        des Projekts zu, Explorer und Objektinspektor leer, und die
        Startseite steht vorn. `False`, wenn die Nachfrage abgebrochen
        wurde oder kein Projekt offen war."""
        if self.projekt is None:
            self.statusBar().showMessage("Es ist kein Projekt offen.")
            return False
        if not self._vorheriges_projekt_schliessen():
            self.statusBar().showMessage("Das Projekt bleibt offen.")
            return False
        name = self.projekt.name
        self.kindprozesse_beenden()
        sperre.freigeben(self.projekt.ordner)
        self._haltepunkte_ablegen()
        self.projekt = None
        self._projekt_datei = None
        self._sicherung_eigen = False
        self._gemerkte_haltepunkte.clear()
        self.datenbank_panel.projektordner_setzen(None)
        self.explorer.leeren()
        self.objektinspektor.leeren()
        self._formular_docks_anpassen()
        self._zuruecksetzen_pruefen()
        self.startbild.offenes_projekt = None
        self.startbild.aufbauen()
        self.mitte.setCurrentWidget(self.startbild)
        self.statusBar().showMessage(f"Projekt {name} geschlossen.")
        return True

    def _kein_projekt_text(self) -> str:
        """Die Meldung, wenn ein Befehl ein offenes Projekt braucht.

        Der Menüweg kommt aus der Beschriftung der Aktion (Punkt 310).
        Dreizehn Meldungen nannten „Projekt → Öffnen …“, der Eintrag
        heißt aber „Projekt öffnen …“, und unter „Datei“ steht ein
        „Öffnen …“ für einzelne Dateien."""
        eintrag = self.aktionen["projekt.oeffnen"].qaction.text()
        return (
            f"Kein Projekt offen. Zuerst über „Projekt → {eintrag}“ eines "
            "laden oder ein neues anlegen."
        )

    def _projekt_schon_offen_melden(
        self, name: str, besitzer: sperre.Besitzer | None = None
    ) -> None:
        """Hinweis, dass das Projekt in einem anderen Natter-Fenster
        offen ist (Punkt 286), auch an einem anderen Rechner
        (Punkt 322). Eigene Methode, damit Tests ihn abfangen können.

        Stammt die Sperre aus dem eigenen Konto, ist es fast immer ein
        Rechner, an dem Natter nicht beendet wurde (Punkt 345). Ein Rat
        zur Kopie führte dann zu zwei Fassungen des eigenen Projekts.
        Bei einem fremden Konto bietet `projekt_oeffnen_gemeldet` die
        Kopie vorher mit einem Knopf an (Punkte 342, 349). Hierher
        kommt eine fremde Sperre nur, wo diese Frage nicht gestellt
        wurde, etwa nach „Nur ansehen“. Der Hinweis rät deshalb zu
        keiner Kopie; bis Punkt 384 tat er es, und der Weg dorthin
        führte wieder hierher."""
        if (
            besitzer is not None and besitzer.anderer_rechner
            and _eigenes_konto(besitzer)
        ):
            QMessageBox.information(
                self,
                "Projekt war an einem anderen Rechner geöffnet",
                f"Das Projekt „{name}“ war zuletzt am Rechner "
                f"„{besitzer.rechner}“ im selben Konto geöffnet. "
                "Vermutlich wurde Natter dort nicht beendet, etwa weil "
                "der Rechner ausgeschaltet wurde oder abgestürzt ist.\n\n"
                "Ist das Projekt dort nicht mehr offen, lässt sich hier "
                "ohne Weiteres weiterarbeiten. Ist es dort noch offen, "
                "überschreibt beim Speichern der eine Rechner die "
                "Änderungen des anderen. Nach einer halben Stunde ohne "
                "Natter an jenem Rechner entfällt dieser Hinweis.",
            )
            return
        if besitzer is not None and besitzer.anderer_rechner:
            QMessageBox.information(
                self,
                "Projekt ist schon geöffnet",
                f"Das Projekt „{name}“ ist bereits "
                f"{_besitzer_text(besitzer)} geöffnet.\n\n"
                "Beide Sitzungen schreiben in dieselben Dateien, und "
                "wer zuletzt speichert, überschreibt die Änderungen der "
                "anderen. Am sichersten wird hier erst gespeichert, "
                "wenn das Projekt dort geschlossen ist.",
            )
            return
        QMessageBox.information(
            self,
            "Projekt ist schon geöffnet",
            f"Das Projekt „{name}“ ist bereits in einem anderen "
            "Natter-Fenster geöffnet.\n\nWerden dieselben Dateien in "
            "beiden Fenstern bearbeitet, überschreibt das eine Fenster "
            "beim Speichern die Änderungen des anderen. Natter fragt "
            "dann zwar nach, sicherer ist es aber, nur in einem Fenster "
            "zu arbeiten und das andere zu schließen.",
        )

    def _sperre_erneuern(self) -> None:
        if self.projekt is not None:
            sperre.erneuern(self.projekt.ordner)

    def _vorheriges_projekt_schliessen(self, neuer_ordner: Path | None = None) -> bool:
        """Schließt Reiter und Diagrammfenster des offenen Projekts.
        `False`, wenn die Nachfrage abgebrochen wurde oder das
        Speichern scheiterte; dann bleibt alles offen.

        Bis 0.3.5 blieben sie beim Wechsel stehen. Danach standen zwei
        Reiter „u_main.py“ nebeneinander, F5 startete das neue
        Projekt, und was im alten Reiter geschrieben wurde, kam im
        Programm nie an. Dateien außerhalb des Projektordners und
        Hilfeseiten bleiben offen, sie gehören zu keinem Projekt.
        """
        # Die Verbindung im Datenbank-Panel geht beim Öffnen in jedem
        # Fall zu (`projektordner_setzen`), auch wenn dasselbe Projekt
        # noch einmal geöffnet wird. Nach einer offenen Transaktion
        # wird deshalb auch dann gefragt (Punkt 276).
        self.designer_nachschreiben()
        if self.projekt is None:
            return self._vor_dem_schliessen_klaeren([], lambda: True)
        alt = self.projekt.ordner.resolve()
        if neuer_ordner is not None and Path(neuer_ordner).resolve() == alt:
            return self._vor_dem_schliessen_klaeren([], lambda: True)

        def im_alten(pfad: Path) -> bool:
            return Path(pfad).resolve().is_relative_to(alt)

        if not self._ungespeichertes_klaeren(alt):
            return False

        self._reiter_schliessen_wenn(im_alten)
        self._diagramme_schliessen_wenn(im_alten)
        # Gespeichert oder verworfen: im Projekt ist nichts mehr
        # ungespeichert, und die Sicherung wird nicht mehr gebraucht
        # (Punkt 344).
        self._sicherung_entfernen()
        return True

    def _ungespeichertes_klaeren(self, ordner: Path) -> bool:
        """Fragt nach den ungespeicherten Editoren und Diagrammen mit
        Dateien aus `ordner` und speichert sie auf Wunsch, in einer
        Nachfrage mit einer offenen Transaktion im Datenbank-Panel.
        Liefert, ob es weitergehen darf: nach „Speichern“, wenn alles
        gespeichert wurde, und nach „Verwerfen“."""
        ordner = Path(ordner).resolve()

        def darin(pfad: Path) -> bool:
            return Path(pfad).resolve().is_relative_to(ordner)

        editoren = [
            e
            for e in self._ungespeicherte_editoren()
            if darin(e.property(_PFAD_EIGENSCHAFT))
        ]
        diagramme = [
            f for f in self._ungespeicherte_diagramme() if darin(f.diagramm.pfad)
        ]
        namen = [Path(e.property(_PFAD_EIGENSCHAFT)).name for e in editoren]
        namen += [f.diagramm.pfad.name for f in diagramme]

        def speichern() -> bool:
            for editor in editoren:
                if not self._editor_speichern(editor):
                    return False
            return all(fenster.speichern() for fenster in diagramme)

        return self._vor_dem_schliessen_klaeren(namen, speichern)

    def _diagramme_schliessen_wenn(self, passt) -> None:  # noqa: ANN001
        """Schließt jedes Diagrammfenster, dessen Datei `passt`, ohne
        nach dem Speichern zu fragen, wie `_reiter_schliessen_wenn`
        für die Reiter."""
        for schluessel, fenster in list(self._offene_diagramme.items()):
            if passt(Path(schluessel)):
                del self._offene_diagramme[schluessel]
                fenster._geaendert = False
                fenster.close()
                fenster.deleteLater()

    def _zuruecksetzen_pruefen(self) -> None:
        """„Projekt → Auf Original zurücksetzen …" ist nur bei der Kopie
        eines Beispiels oder einer Aufgabe bedienbar (Punkt 346). Bei
        einem eigenen Projekt gäbe es nichts, worauf zurückgesetzt
        werden könnte. Im Prüfungsmodus geht es nur bei einer Aufgabe
        (Punkt 371): das Original eines Beispiels ist eine Lösung."""
        eintrag = getattr(self, "_beispiel_zuruecksetzen_eintrag", None)
        if eintrag is None:
            return
        eintrag.setEnabled(self._zuruecksetzen_moeglich())

    def _zuruecksetzen_moeglich(self) -> bool:
        """Ob das offene Projekt die Kopie einer Aufgabe oder eines
        Beispiels ist. Im Prüfungsmodus zählt eine Kopie nicht, deren
        `.natter-quelle` in den Ordner der Beispiele zeigt (Punkt
        403); die Datei lässt sich von Hand schreiben. Nachgesehen
        wird hier nur am Text des Pfads, weil das bei jedem Öffnen
        geschieht; den Inhalt vergleicht erst das Zurücksetzen."""
        projekt = getattr(self, "projekt", None)
        if projekt is None:
            return False
        aufgabe = aufgabe_original(projekt.ordner)
        beispiel = beispiel_original(projekt.ordner) is not None
        if pruefungsmodus_laeuft():
            return aufgabe is not None and not beispiel and not (
                ist_beispiel_original(aufgabe, aufloesen=False)
            )
        return aufgabe is not None or beispiel

    def beispiel_zuruecksetzen_nachfragen(self, *, bestaetigt: bool = False) -> bool:
        """Setzt das geöffnete Beispiel nach einer Rückfrage auf das
        Original zurück. `bestaetigt` überspringt die Rückfrage für
        Tests.

        Ungespeicherte Änderungen klärt danach eine gemeinsame
        Nachfrage für alle Dateien, wie beim Projektwechsel
        (`_kopie_zuruecksetzen`, Punkt 405). Bei der Kopie einer
        Aufgabe kommt der bisherige Stand in einen Ordner daneben
        (Punkt 380), nach „Speichern“ samt dem eben gespeicherten Text.

        Im Prüfungsmodus wird eine Kopie nicht zurückgesetzt, deren
        Quelle ein Beispiel ist (Punkt 403).
        """
        if not self._zuruecksetzen_moeglich():
            return False
        ordner = self.projekt.ordner
        aufgabe = aufgabe_original(ordner)
        if aufgabe is not None and not any(aufgabe.glob("*.natter")):
            # Vor der Rückfrage und vor dem Schließen der Reiter: ohne
            # die Aufgabe bliebe von der Kopie nichts übrig.
            QMessageBox.warning(
                self,
                "Aufgabe nicht erreichbar",
                f"Die Aufgabe liegt nicht mehr unter\n{aufgabe}\n\n"
                "Möglicherweise ist das Netzlaufwerk nicht verbunden. "
                "Die Kopie bleibt unverändert.",
            )
            return False
        if (
            aufgabe is not None and pruefungsmodus_laeuft()
            and self._beispiel_gesperrt(aufgabe)
        ):
            return False

        if not bestaetigt:
            if aufgabe is not None:
                frage = (
                    f"„{self.projekt.name}“ auf den Stand der Aufgabe "
                    f"zurücksetzen?\n\nDie Aufgabe wird noch einmal aus\n"
                    f"{aufgabe}\nkopiert. Der bisherige Stand dieser "
                    "Kopie kommt in den Ordner "
                    f"„{vorher_ordner(ordner).name}“ daneben."
                )
            else:
                frage = (
                    f"„{self.projekt.name}“ auf den Auslieferungszustand "
                    "zurücksetzen?\n\nAlle Änderungen an diesem Beispiel "
                    "gehen dabei verloren."
                )
            antwort = QMessageBox.question(
                self,
                "Auf Original zurücksetzen",
                frage,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if antwort != QMessageBox.StandardButton.Yes:
                return False

        projektdatei = self._kopie_zuruecksetzen(ordner)
        if projektdatei is None:
            return False
        self.projekt_oeffnen(projektdatei)
        if aufgabe is None:
            meldung = (
                f"„{self.projekt.name}“ steht wieder im "
                "Auslieferungszustand."
            )
        else:
            meldung = (
                f"„{self.projekt.name}“ steht wieder auf dem Stand der "
                "Aufgabe." + self._aufgehoben_satz()
            )
        self.statusBar().showMessage(meldung)
        return True

    def _aufgehoben_satz(self) -> str:
        """Der Satz, wo der bisherige Stand einer eben ersetzten Kopie
        liegt, oder nichts."""
        if self._aufgehoben is None:
            return ""
        return f" Der bisherige Stand liegt in „{self._aufgehoben.name}“."

    def _kopie_zuruecksetzen(self, ordner: Path) -> Path | None:
        """Setzt die Kopie einer Aufgabe oder eines Beispiels in
        `ordner` zurück und gibt ihre Projektdatei zurück, `None` nach
        einer Meldung. Der eine Weg für „Auf Original zurücksetzen …“
        und „Kopie ersetzen“ (Punkt 362).

        Ist die Kopie gerade offen, gehen vorher ihre Reiter und
        Diagrammfenster zu, das laufende Programm wird beendet, und das
        Datenbank-Panel trennt die Verbindung; alle halten sonst
        Dateien der Kopie offen oder schrieben später ihren alten
        Stand zurück. Hält ein anderes Programm eine Datei, nennt die
        Meldung sie, und die Kopie bleibt unverändert
        (`DateiGesperrt`). Kam danach nicht jede alte Datei zurück,
        nennt die Meldung den Ordner, in dem die übrigen liegen
        (`RueckwegGescheitert`).

        Vor dem Schließen kommt bei ungespeicherten Änderungen die
        Nachfrage wie beim Projektwechsel; nach „Abbrechen“ bleibt
        alles offen, und zurück kommt `None`. Bis Punkt 405 gingen die
        Reiter ohne Frage zu: der ungespeicherte Text war weg, samt
        seiner Sicherung, auch wenn das Zurücksetzen danach
        scheiterte. Scheitert es jetzt, gehen die Reiter der Kopie
        wieder auf, mit dem Stand, der eben gespeichert wurde.

        Bei einer Aufgabe steht danach in `_aufgehoben`, wo der
        bisherige Inhalt der Kopie liegt (Punkt 380); die Meldung
        danach nennt den Ordner."""
        ordner = Path(ordner)
        ist_aufgabe = aufgabe_original(ordner) is not None
        self._aufgehoben = None
        offen: list[Path] = []
        if _ist_projekt_in(self.projekt, ordner):
            self.designer_nachschreiben()
            if not self._ungespeichertes_klaeren(ordner):
                self.statusBar().showMessage(
                    f"„{ordner.name}“ wurde nicht zurückgesetzt."
                )
                return None
            offen = self._reiter_im_ordner(ordner)
            self._fenster_im_ordner_schliessen(ordner)
            self.kindprozesse_beenden()
            self.datenbank_panel.trennen()
        try:
            if not ist_aufgabe:
                return self._beim_kopieren(
                    f"„{ordner.name}“ wird auf das Original "
                    "zurückgesetzt …",
                    lambda: beispiel_zuruecksetzen(ordner),
                )
            projektdatei, self._aufgehoben = self._beim_kopieren(
                f"„{ordner.name}“ wird neu aus der Aufgabe kopiert …",
                lambda: aufgabe_zuruecksetzen(ordner),
            )
            return projektdatei
        except ValueError:
            # Im Prüfungsmodus eine Kopie, deren Quelle ein Beispiel
            # ist (Punkt 403).
            QMessageBox.information(
                self,
                "Beispielprojekt gesperrt",
                f"Die Quelle von „{ordner.name}“ ist ein "
                f"mitgeliefertes Beispielprojekt.\n\n{GESPERRT_HINWEIS}",
            )
        except RueckwegGescheitert as fehler:
            name = fehler.pfad.relative_to(ordner)
            self.statusBar().showMessage(
                f"Nicht zurückgesetzt: {name} ließ sich nicht ersetzen."
            )
            QMessageBox.warning(
                self,
                "Nicht zurückgesetzt",
                f"„{name}“ ließ sich nicht ersetzen, und danach kamen "
                "nicht alle bisherigen Dateien in die Kopie zurück. Die "
                "fehlenden liegen noch in\n"
                f"{fehler.ablage}\n\nVon dort lassen sie sich zurück "
                f"nach\n{ordner}\nkopieren. Vermutlich hielt ein anderes "
                "Programm die Dateien kurz offen, etwa ein Virenscanner.",
            )
        except DateiGesperrt as fehler:
            name = fehler.pfad.relative_to(ordner)
            self.statusBar().showMessage(
                f"Nicht zurückgesetzt: {name} ließ sich nicht ersetzen."
            )
            QMessageBox.warning(
                self,
                "Nicht zurückgesetzt",
                f"„{name}“ ließ sich nicht ersetzen. Vermutlich ist die "
                "Datei gerade in einem anderen Programm geöffnet, etwa "
                "in Excel.\n\nDie Kopie in\n"
                f"{ordner}\nist unverändert. Nach dem Schließen der "
                "Datei dort lässt sie sich noch einmal zurücksetzen.",
            )
        except OSError:
            self._kopie_nicht_angelegt_melden(
                "Nicht zurückgesetzt",
                "Die Aufgabe ließ sich nicht noch einmal kopieren nach"
                if ist_aufgabe else
                "Das Beispiel ließ sich nicht noch einmal kopieren nach",
                ordner,
            )
        self._reiter_wieder_oeffnen(offen)
        return None

    def _reiter_im_ordner(self, ordner: Path) -> list[Path]:
        """Die Dateien der Reiter und Diagrammfenster mit Dateien aus
        `ordner`, in der Reihenfolge der Reiter."""
        ordner = Path(ordner).resolve()
        dateien = [
            pfad
            for index in range(self.editor_tabs.count())
            if (pfad := self._reiter_pfad(index)) is not None
            and pfad.is_relative_to(ordner)
        ]
        dateien += [
            Path(schluessel).resolve()
            for schluessel in self._offene_diagramme
            if Path(schluessel).resolve().is_relative_to(ordner)
        ]
        return dateien

    def _reiter_wieder_oeffnen(self, dateien: list[Path]) -> None:
        """Öffnet `dateien` wieder, nachdem das Zurücksetzen der Kopie
        gescheitert ist (Punkt 405). Die Kopie ist dann unverändert,
        und was ungespeichert war, wurde vorher gespeichert oder auf
        Wunsch verworfen."""
        for datei in dateien:
            if datei.is_file():
                self.oeffnen(datei)

    def _fenster_im_ordner_schliessen(self, ordner: Path) -> None:
        """Schließt alle Reiter und Diagrammfenster mit Dateien aus
        `ordner`, ohne nach dem Speichern zu fragen.

        Bis Punkt 374 blieben beim Zurücksetzen die Diagrammfenster
        offen. Die Nachfrage beim Beenden nannte dann ein geändertes
        Diagramm, und „Speichern“ schrieb den alten Stand in die eben
        zurückgesetzte Kopie."""
        ordner = Path(ordner).resolve()
        self._reiter_schliessen_wenn(lambda datei: datei.is_relative_to(ordner))
        self._diagramme_schliessen_wenn(
            lambda datei: datei.resolve().is_relative_to(ordner)
        )

    def _reiter_pfad(self, index: int) -> Path | None:
        """Die Datei hinter einem Reiter: beim Editor und bei einem
        Betrachter aus der Eigenschaft, beim Designer aus
        `_pfad_zu_formular`. `None` bei Reitern ohne Datei."""
        widget = self.editor_tabs.widget(index)
        inhalt = self._tab_inhalt(widget)
        pfad = widget.property(_PFAD_EIGENSCHAFT) if widget is not None else None
        if not pfad and inhalt is not None:
            pfad = inhalt.property(_PFAD_EIGENSCHAFT)
        if not pfad:
            for schluessel, formular in self._pfad_zu_formular.items():
                if formular._qwidget is inhalt:
                    pfad = schluessel
        return Path(pfad).resolve() if pfad else None

    def _reiter_schliessen_wenn(self, passt) -> None:  # noqa: ANN001
        """Schließt jeden Reiter, dessen Datei `passt`, ohne nach dem
        Speichern zu fragen. Wer das aufruft, hat vorher selbst
        gefragt oder gespeichert."""
        for index in reversed(range(self.editor_tabs.count())):
            pfad = self._reiter_pfad(index)
            if pfad is None or not passt(pfad):
                continue
            inhalt = self._tab_inhalt(self.editor_tabs.widget(index))
            if isinstance(inhalt, QPlainTextEdit):
                inhalt.document().setModified(False)
            self._tab_schliessen(index)

    def projekt_oeffnen_gemeldet(self, pfad: Path) -> Projekt | None:
        """`projekt_oeffnen()` mit Meldung statt Traceback – der Weg für
        alles, was von einem Klick kommt („Projekt → Projekt öffnen …“, ein
        Eintrag unter „Zuletzt geöffnet“).

        Eine `.natter`-Datei kann fehlen, weil der USB-Stick nicht mehr
        steckt, oder beschädigt sein, weil sie jemand in einem Editor
        offen hatte. Beides flog vorher als `FileNotFoundError` bzw.
        `JSONDecodeError` aus einem Qt-Signal heraus (M11, Abschnitt 5).

        Ein mitgeliefertes Original wird dabei nie an Ort und Stelle
        geöffnet, sondern als Kopie - auf demselben Weg wie über
        „Datei → Beispielprojekte". „Zuletzt geöffnet" führte sonst
        direkt ins Original, und jede Änderung landete im Beispiel
        selbst.
        """
        if self._beispiel_gesperrt(Path(pfad)):
            return None
        try:
            if ist_beispiel_original(pfad):
                return self.beispiel_oeffnen(pfad)
            ort = self._ort_zum_oeffnen(Path(pfad))
            if ort is None:
                return None
            ziel, art = ort
            if art in _KOPIE_ARTEN:
                quelle = Path(pfad) if Path(pfad).is_dir() else Path(pfad).parent
                return self._in_kopie_wechseln(ziel, art, quelle)
            projekt = self.projekt_oeffnen(ziel, sperrhinweis=art != "gesperrt")
            if art == "ansehen" and _ist_projekt_in(projekt, ziel):
                self.statusBar().showMessage(
                    f"Projekt {projekt.name} nur zum Ansehen geöffnet: in "
                    f"{projekt.ordner} darf Natter nicht schreiben."
                )
            elif art == "hier" and _ist_projekt_in(projekt, ziel):
                self._eigene_kopie_nennen()
            return projekt
        except _oeffnen_fehler() as fehler:
            self._oeffnen_fehler_melden(Path(pfad), fehler)
        return None

    def _oeffnen_fehler_melden(
        self, pfad: Path, fehler: BaseException,
    ) -> None:
        """Die Meldung zu einem Projekt, das sich nicht öffnen ließ;
        gemeinsam für `projekt_oeffnen_gemeldet` und den Wechsel in
        die Kopie nach einem gescheiterten Speichern (Punkt 378)."""
        if isinstance(fehler, FileNotFoundError):
            QMessageBox.warning(
                self,
                "Projekt nicht gefunden",
                f"„{Path(pfad).name}“ liegt nicht (mehr) unter\n{pfad}\n\n"
                "Wurde der Ordner verschoben oder der USB-Stick abgezogen?",
            )
        elif not isinstance(fehler, OSError):
            # Der Grund auf Deutsch; der Text aus `json` oder
            # `jsonschema` ist englisch (Punkt 280).
            QMessageBox.warning(
                self,
                "Projekt konnte nicht geöffnet werden",
                f"„{Path(pfad).name}“ ist beschädigt und lässt sich nicht lesen.\n\n"
                f"{fehler_beschreiben(fehler)}\n\nDie Datei wird von Natter "
                "geschrieben und sollte nicht von Hand bearbeitet werden.",
            )
        elif isinstance(fehler, PermissionError):
            # Bis Punkt 385 stand hier der Text von Python, englisch
            # und mit doppelten Backslashes im Pfad.
            QMessageBox.warning(
                self,
                "Projekt konnte nicht geöffnet werden",
                f"„{Path(pfad).name}“ in\n{Path(pfad).parent}\nlässt "
                "sich nicht lesen. Entweder fehlt diesem Konto das "
                "Leserecht für die Datei, etwa in einem Ordner, der nur "
                "zum Abgeben gedacht ist, oder ein anderes Programm hält "
                "sie gerade offen.\n\nDas Leserecht vergibt, wer den "
                "Ordner verwaltet, meist die Lehrkraft.",
            )
        else:
            QMessageBox.warning(
                self,
                "Projekt konnte nicht geöffnet werden",
                f"„{Path(pfad).name}“ in\n{Path(pfad).parent}\nlässt "
                "sich nicht öffnen. Vielleicht ist das Laufwerk gerade "
                "nicht erreichbar; nach einem Augenblick lässt es sich "
                "noch einmal versuchen.",
            )

    def _ort_zum_oeffnen(self, pfad: Path) -> tuple[Path, str] | None:
        """Der Pfad, der geöffnet werden soll, und wie es dazu kam:
        `pfad` selbst („hier“, „ansehen“, „gesperrt“) oder eine Kopie
        unter „Dokumente\\Natter“ („kopiert“, „vorhanden“, „erneuert“).
        `None`, wenn die Kopie scheiterte.

        Ein Projektordner geht dort auf, wo er liegt, gleich wer ihn
        angelegt, kopiert oder ausgeteilt hat. Die eigene Kopie bietet
        Natter nur an, wo sich am Ort nicht arbeiten lässt: in einem
        Ordner ohne Schreibrecht (Punkt 321), bei einem Projekt, das
        ein anderes Konto an einem anderen Rechner offen hat (Punkte
        342, 349), und in einem Ordner, in den der Explorer eine
        ZIP-Datei nur vorläufig entpackt hat (Punkte 391, 402). Fehlen dort
        Startdatei oder Haupt-Unit, kommt statt der Frage eine Meldung,
        und zurück kommt `None`. Was die Knöpfe tun, steht in der Frage
        (Punkt 341).

        Bis 0.4.0 galt außerdem jedes Projekt als verteilte Aufgabe,
        dessen Ordner einem anderen Konto gehörte oder das außerhalb
        von „Dokumente“, Desktop und USB-Stick lag (Punkte 361, 379).
        Nach einem Serverumzug, auf einem NAS und nach dem Austeilen
        durch eine Schulsoftware traf das eigene Projekte, und die
        Arbeit landete in einer Kopie, die niemand suchte (Punkte 390,
        392, 393). Aufgaben werden stattdessen über einen Ordner nur
        zum Lesen verteilt.

        Eine Antwort auf die Frage merkt sich Natter nicht. Nur wer
        eine Kopie trotz geänderter Aufgabe behält, wird zu diesem
        Stand der Aufgabe nicht wieder gefragt (Punkt 380)."""
        ordner = pfad if pfad.is_dir() else pfad.parent
        projektdatei = (
            next(iter(sorted(pfad.glob("*.natter"))), None)
            if pfad.is_dir() else pfad
        )
        if projektdatei is None or not projektdatei.is_file():
            return pfad, "hier"
        aus_zip = vorlaeufig_entpackt(ordner)
        besitzer = sperre.anderer_besitzer(ordner)
        gesperrt = (
            besitzer is not None and besitzer.anderer_rechner
            and not _eigenes_konto(besitzer)
        )
        beschreibbar = ordner_beschreibbar(ordner)
        if beschreibbar and not gesperrt and not aus_zip:
            return pfad, "hier"
        # Eine beschädigte Projektdatei meldet `projekt_oeffnen_gemeldet`
        # gleich, statt sie erst zu kopieren.
        projekt = Projekt.laden(projektdatei)
        if aus_zip and _fehlende_dateien(projekt):
            self._nicht_entpackt_melden(projekt)
            return None
        ziel = natter_ordner()
        name = projektdatei.stem
        vorhanden = vorhandene_aufgabenkopie(projektdatei, ziel)
        if not beschreibbar:
            art, nein = "ansehen", "Nur ansehen"
            titel = "Ordner ohne Schreibrecht"
            text = (
                f"In den Ordner\n{ordner}\ndarf Natter nicht schreiben, "
                "etwa weil er auf einer Freigabe nur zum Lesen liegt. "
                "Änderungen an diesem Projekt ließen sich dort nicht "
                "speichern."
            )
            folge = (
                "„Nur ansehen“ öffnet das Projekt an seinem Ort; "
                "speichern lässt es sich dort nicht."
            )
        elif gesperrt:
            art, nein = "gesperrt", "Trotzdem hier öffnen"
            titel = "Projekt ist schon geöffnet"
            text = (
                f"Das Projekt „{name}“ ist bereits "
                f"{_besitzer_text(besitzer)} geöffnet. Beide Sitzungen "
                "schreiben in dieselben Dateien, und wer zuletzt "
                "speichert, überschreibt die Änderungen der anderen."
            )
            folge = (
                "„Trotzdem hier öffnen“ öffnet das Projekt an seinem "
                "Ort, in denselben Dateien wie die andere Sitzung."
            )
        else:
            art, nein = "hier", "Hier öffnen"
            titel = "Projekt aus einer ZIP-Datei"
            text = (
                f"Das Projekt „{name}“ liegt in einem Ordner, in den "
                f"eine ZIP-Datei nur vorläufig entpackt wurde:\n"
                f"{ordner}\nDas geschieht, wenn eine Datei im Explorer "
                "oder in einem Packprogramm wie 7-Zip direkt in der "
                "ZIP-Datei geöffnet wird. Der Ordner wird wieder "
                "aufgeräumt, und an vielen Schulrechnern "
                "wird er beim Abmelden geleert. Was dort gespeichert "
                "wird, ist danach weg."
            )
            folge = "„Hier öffnen“ öffnet das Projekt an seinem Ort."
        if vorhanden is not None:
            titel = "Eigene Kopie vorhanden"
            text = f"Von „{name}“ gibt es schon eine eigene Kopie. {text}"
        text += "\n\n" + self._kopie_folge(
            vorhanden, ziel, self._ungespeichert_in(ordner)
        )
        stand = (
            neuer_aufgabenstand(vorhanden.parent)
            if vorhanden is not None else None
        )
        if stand is not None:
            # Eine Frage statt zwei (Punkt 380): vorher folgte auf
            # „Eigene Kopie vorhanden“ noch „Aufgabe wurde geändert“,
            # bei jedem Öffnen wieder.
            wahl = self._geaenderte_aufgabe_fragen(
                vorhanden.parent, f"{text} {folge}", nein
            )
            if wahl == "original":
                return pfad, art
            return self._kopie_holen(
                projektdatei, ersetzen=wahl == "ersetzen", stand=stand
            )
        if not self._kopie_anbieten(titel, f"{text} {folge}", nein):
            return pfad, art
        return self._kopie_holen(projektdatei, ersetzen=False)

    def _nicht_entpackt_melden(self, projekt: Projekt) -> None:
        """Meldung zu einem Projekt in einem vorläufig entpackten
        Ordner, dem die Startdatei oder die Haupt-Unit fehlt (Punkt
        391). So sieht es aus, wenn jemand im Explorer die `.natter`
        direkt in der ZIP-Datei doppelklickt: Windows entpackt dann nur
        sie. Vorher ging ein solches Projekt ohne Hinweis auf, und erst
        das Starten scheiterte."""
        namen = [f"„{name}“" for name in _fehlende_dateien(projekt)]
        fehlt = (
            namen[0] if len(namen) == 1
            else f"{', '.join(namen[:-1])} und {namen[-1]}"
        )
        self.statusBar().showMessage(
            f"Projekt {projekt.name} nicht geöffnet: es fehlt {fehlt}."
        )
        QMessageBox.warning(
            self,
            "ZIP-Datei nicht entpackt",
            f"Vom Projekt „{projekt.name}“ liegt in\n{projekt.ordner}\n"
            f"nur ein Teil der Dateien; es fehlt {fehlt}. So sieht es "
            "aus, wenn eine Datei im Explorer oder in einem "
            "Packprogramm wie 7-Zip direkt in einer ZIP-Datei geöffnet "
            "wird: dann kommt nur diese eine heraus."
            "\n\nDie ZIP-Datei zuerst vollständig entpacken, im Explorer "
            "mit „Alle extrahieren …“, und dann die Projektdatei im "
            "entpackten Ordner öffnen.",
        )

    @staticmethod
    def _kopie_folge(
        vorhanden: Path | None, ziel: Path, ungespeichert: bool
    ) -> str:
        """Der Satz zum Knopf „Eigene Kopie öffnen“: was er tut und
        was aus dem ungespeicherten Text in den Editoren wird. Eine
        vorhandene Kopie behält ihre Dateien (Punkt 365)."""
        if vorhanden is None:
            text = (
                f"„Eigene Kopie öffnen“ kopiert das Projekt nach\n{ziel}"
                "\nund öffnet die Kopie"
            )
            if ungespeichert:
                return (
                    f"{text}; der ungespeicherte Text aus den Editoren "
                    "kommt mit."
                )
            return f"{text}."
        text = (
            "„Eigene Kopie öffnen“ öffnet die eigene Kopie in\n"
            f"{vorhanden.parent}\nmit dem Stand vom letzten Mal"
        )
        if ungespeichert:
            return (
                f"{text}. Der ungespeicherte Text aus den Editoren "
                "erscheint dort als Änderung, die noch nicht "
                "gespeichert ist; die Dateien der Kopie bleiben, wie "
                "sie sind."
            )
        return f"{text}."

    def _ungespeichert_in(self, ordner: Path) -> bool:
        """Ob ein Editor mit ungespeichertem Text eine Datei aus
        `ordner` zeigt."""
        ordner = Path(ordner).resolve()
        return any(
            Path(editor.property(_PFAD_EIGENSCHAFT)).resolve()
            .is_relative_to(ordner)
            for editor in self._ungespeicherte_editoren()
        )

    def _kopie_anbieten(
        self, titel: str, text: str, nein: str, *, warnung: bool = False
    ) -> bool:
        """Frage mit den Knöpfen „Eigene Kopie öffnen“ und `nein`.
        Eigene Methode, damit Tests die Antwort vorgeben können."""
        fenster = QMessageBox(
            QMessageBox.Icon.Warning if warnung else QMessageBox.Icon.Question,
            titel, text, parent=self,
        )
        kopie = fenster.addButton(
            "Eigene Kopie öffnen", QMessageBox.ButtonRole.AcceptRole
        )
        fenster.addButton(nein, QMessageBox.ButtonRole.RejectRole)
        fenster.setDefaultButton(kopie)
        fenster.exec()
        return fenster.clickedButton() is kopie

    def _geaenderte_aufgabe_fragen(
        self, kopie: Path, text: str = "", nein: str | None = None
    ) -> str:
        """Fragt, was mit der Kopie in `kopie` geschehen soll, nachdem
        die Aufgabe geändert wurde (Punkt 346): „behalten“, „ersetzen“
        oder, nur mit dem Knopf `nein`, „original“. Eigene Methode,
        damit Tests die Antwort vorgeben können.

        Beim Öffnen einer Aufgabe ist das die einzige Frage; `text`
        bringt dann mit, was sonst in der Frage nach der Kopie stünde
        (Punkt 380). Vorher kamen beide nacheinander, und nach
        „Kopie ersetzen“ war der alte Stand gelöscht. Jetzt kommt er in
        einen Ordner daneben, und die Frage nennt ihn. Vorgewählt ist
        „Eigene Kopie öffnen“, das nichts verändert."""
        if not text:
            text = (
                "„Eigene Kopie öffnen“ öffnet die eigene Kopie in\n"
                f"{kopie}\nmit dem Stand vom letzten Mal."
            )
        text = (
            "Die Aufgabe wurde geändert, nachdem die eigene Kopie "
            f"angelegt wurde.\n\n{text}\n\n„Kopie ersetzen“ kopiert die "
            "Aufgabe neu. Der bisherige Stand der Kopie kommt dabei in "
            f"den Ordner „{vorher_ordner(kopie).name}“ daneben. Nach "
            "„Eigene Kopie öffnen“ fragt Natter zu diesem Stand der "
            "Aufgabe nicht noch einmal."
        )
        fenster = QMessageBox(
            QMessageBox.Icon.Question, "Aufgabe wurde geändert", text,
            parent=self,
        )
        behalten = fenster.addButton(
            "Eigene Kopie öffnen", QMessageBox.ButtonRole.AcceptRole
        )
        ersetzen = fenster.addButton(
            "Kopie ersetzen", QMessageBox.ButtonRole.DestructiveRole
        )
        original = None
        if nein is not None:
            original = fenster.addButton(
                nein, QMessageBox.ButtonRole.RejectRole
            )
        fenster.setDefaultButton(behalten)
        fenster.exec()
        geklickt = fenster.clickedButton()
        if geklickt is ersetzen:
            return "ersetzen"
        if original is not None and geklickt is original:
            return "original"
        return "behalten"

    def _kopie_holen(
        self, projektdatei: Path, *, ersetzen: bool | None = None,
        stand: str | None = None,
    ) -> tuple[Path, str] | None:
        """Die eigene Kopie der Aufgabe `projektdatei` unter
        „Dokumente\\Natter“: eine vorhandene (Punkt 340), eine auf den
        neuen Stand der Aufgabe gebrachte (Punkt 346) oder eine neue.
        `None`, wenn sie sich nicht anlegen ließ.

        `ersetzen` ist die schon gegebene Antwort auf die Frage nach
        einer geänderten Aufgabe, `stand` dazu der neue Fingerabdruck
        aus `neuer_aufgabenstand` (`None` für eine unveränderte
        Aufgabe). Mit `ersetzen=None` sieht `_kopie_holen` selbst nach
        und fragt, falls nötig. Wer die Kopie behält, wird zu diesem
        Stand der Aufgabe nicht wieder gefragt (`aufgabe_stand_merken`,
        Punkt 380)."""
        ziel = natter_ordner()
        try:
            vorhanden = vorhandene_aufgabenkopie(projektdatei, ziel)
            if vorhanden is None:
                return self._beim_kopieren(
                    f"„{projektdatei.stem}“ wird nach {ziel} kopiert …",
                    lambda: aufgabe_kopieren(projektdatei, ziel),
                ), "kopiert"
        except OSError as fehler:
            self._kopie_nicht_angelegt_melden(
                "Projekt nicht kopiert",
                "Die Kopie des Projekts ließ sich nicht anlegen in",
                ziel, fehler,
            )
            return None
        if ersetzen is None:
            stand = neuer_aufgabenstand(vorhanden.parent)
            ersetzen = stand is not None and (
                self._geaenderte_aufgabe_fragen(vorhanden.parent)
                == "ersetzen"
            )
        if not ersetzen:
            if stand is not None:
                try:
                    aufgabe_stand_merken(vorhanden.parent, stand)
                except OSError:
                    pass  # Dann kommt die Frage beim nächsten Mal wieder.
            return vorhanden, "vorhanden"
        erneuert = self._kopie_zuruecksetzen(vorhanden.parent)
        return (erneuert, "erneuert") if erneuert is not None else None

    def _beim_kopieren(self, meldung: str, arbeit: Callable[[], Any]) -> Any:
        """Führt `arbeit` aus und zeigt solange den Wartezeiger und
        `meldung` in der Statuszeile (Punkt 398).

        Eine Aufgabe mit einigen tausend Dateien zu kopieren dauert
        mehrere Sekunden, über ein Netzlaufwerk länger, und das Fenster
        stand in der Zeit ohne jeden Hinweis still. Ein Nebenfaden
        ließe in einen halb kopierten Ordner speichern; für die paar
        Dutzend Dateien einer Aufgabe im Unterricht lohnt er nicht.
        `repaint` zeichnet die Statuszeile sofort, ohne dass Natter
        zwischendurch Klicks annimmt. Steht die Meldung danach noch
        da, etwa nach einem Fehler, verschwindet sie."""
        leiste = self.statusBar()
        leiste.showMessage(meldung)
        leiste.repaint()
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            return arbeit()
        finally:
            QApplication.restoreOverrideCursor()
            if leiste.currentMessage() == meldung:
                leiste.clearMessage()

    def _in_kopie_wechseln(
        self, kopie: Path, art: str, quelle: Path
    ) -> Projekt | None:
        """Öffnet die Kopie `kopie` und nimmt den ungespeicherten Text
        aller Editoren mit Dateien aus `quelle` mit (Punkt 341).

        Wer eine Aufgabe erst nur zum Ansehen geöffnet und darin
        geschrieben hat, kam vorher nicht mehr in die Kopie: beim
        Wechsel fragte Natter nach dem Speichern, das Speichern
        scheiterte am Ordner ohne Schreibrecht, und der Wechsel brach
        ab. Die Statuszeile meldet nur, was geschehen ist.

        In eine gerade angelegte Kopie wird der Text geschrieben. Eine
        vorhandene Kopie enthält die Arbeit vom letzten Mal; bis Punkt
        365 ersetzte der Text aus dem Original sie ohne Rückfrage. Dort
        kommt er jetzt nur in den Editor, als Änderung, die noch nicht
        gespeichert ist: die Dateien der Kopie bleiben unberührt, und
        ein Rückgängig stellt ihren Stand im Editor wieder her."""
        quelle = Path(quelle).resolve()
        mitgenommen = []
        vorgelegt: list[tuple[Path, str]] = []
        editoren = []
        for editor in self._ungespeicherte_editoren():
            datei = Path(editor.property(_PFAD_EIGENSCHAFT)).resolve()
            if not datei.is_relative_to(quelle):
                continue
            ziel = kopie.parent / datei.relative_to(quelle)
            text = editor.toPlainText()
            if art == "vorhanden" and ziel.exists():
                vorgelegt.append((ziel, text))
            elif not self.datei_schreiben_gemeldet(ziel, text):
                return self.projekt
            else:
                mitgenommen.append(ziel)
            editoren.append(editor)
        # Sonst fragte der Projektwechsel nach dem Speichern im
        # Original, und das scheiterte am fehlenden Schreibrecht.
        for editor in editoren:
            editor.document().setModified(False)
        try:
            projekt = self.projekt_oeffnen(kopie)
        except BaseException:
            # Die Projektdatei der Kopie ließ sich nicht lesen (Punkt
            # 373). Bei einer vorhandenen Kopie steht der Text nur
            # noch im Editor; als unverändert markiert, ginge er beim
            # Schließen ohne Nachfrage verloren.
            for editor in editoren:
                editor.document().setModified(True)
            raise
        if not _ist_projekt_in(projekt, kopie):
            # Abgebrochen: die Reiter bleiben offen und sollen weiter
            # als geändert gelten.
            for editor in editoren:
                editor.document().setModified(True)
            return projekt
        for ziel in mitgenommen:
            self.datei_oeffnen(ziel)
        im_editor = False
        for ziel, text in vorgelegt:
            editor = self.datei_oeffnen(ziel)
            if editor is None:
                continue
            if editor.toPlainText() == text:
                # Steht schon so in der Kopie, etwa nach einem
                # abgebrochenen ersten Wechsel.
                mitgenommen.append(ziel)
                continue
            # Über den Cursor und nicht `setPlainText`: so bleibt der
            # Stand der Kopie ein Rückgängig entfernt.
            cursor = QTextCursor(editor.document())
            cursor.beginEditBlock()
            cursor.select(QTextCursor.SelectionType.Document)
            cursor.insertText(text)
            cursor.endEditBlock()
            im_editor = True
        meldung = {
            "kopiert": f"Projekt nach {projekt.ordner} kopiert und geöffnet.",
            "vorhanden": (
                f"Die eigene Kopie in {projekt.ordner} ist geöffnet, mit "
                "dem Stand vom letzten Mal."
            ),
            "erneuert": (
                "Die Aufgabe wurde neu kopiert und geöffnet."
                + self._aufgehoben_satz()
            ),
        }[art]
        if im_editor:
            # Ohne den Pfad und mit dem Rückweg vorn: die Statuszeile
            # bricht nicht um, und bei 1280 Punkten Breite fehlte
            # vorher genau der Satz zu Rückgängig (Punkt 386). Wo die
            # Kopie liegt, nannte schon die Frage davor.
            meldung = (
                "Eigene Kopie geöffnet. Rückgängig holt ihren Stand vom "
                "letzten Mal zurück; der Text aus dem Original im Editor "
                "ist noch nicht gespeichert."
            )
        elif mitgenommen:
            meldung += " Die ungespeicherten Änderungen stehen in der Kopie."
        self.statusBar().showMessage(meldung)
        return projekt

    def _kopie_nach_speicherfehler(self) -> None:
        """Legt nach „Eigene Kopie öffnen“ in der Meldung zum
        gescheiterten Speichern die Kopie an und wechselt hinein."""
        if self.projekt is None:
            return
        quelle = self.projekt.ordner
        projektdatei = next(iter(sorted(quelle.glob("*.natter"))), None)
        if projektdatei is None:
            return
        geholt = self._kopie_holen(projektdatei)
        if geholt is None:
            return
        try:
            self._in_kopie_wechseln(geholt[0], geholt[1], quelle)
        except _oeffnen_fehler() as fehler:
            self._oeffnen_fehler_melden(geholt[0], fehler)

    def _eigene_kopie_des_projekts(self) -> Path | None:
        """Die Projektdatei einer schon angelegten eigenen Kopie des
        offenen Projekts, oder `None`."""
        if self.projekt is None:
            return None
        projektdatei = next(
            iter(sorted(self.projekt.ordner.glob("*.natter"))), None
        )
        if projektdatei is None:
            return None
        try:
            return vorhandene_aufgabenkopie(projektdatei, natter_ordner())
        except OSError:
            return None

    def _eigene_kopie_nennen(self) -> None:
        """Nennt in der Statuszeile eine eigene Kopie des eben an
        seinem Ort geöffneten Projekts unter „Dokumente\\Natter“
        (Punkt 401).

        Bis 0.3.6 legte Natter eine solche Kopie auch von einer
        Aufgabe in einem beschreibbaren Klassenordner an, und darin
        steckt die Arbeit der bisherigen Stunden. Seit 0.4.0 geht die
        Aufgabe dort ohne Frage am Ort auf, und die Kopie sah niemand
        mehr. Eine Frage beim Öffnen kommt dafür nicht (Punkt 390);
        die Zeile nennt nur den Ort."""
        kopie = self._eigene_kopie_des_projekts()
        if kopie is None:
            return
        self.statusBar().showMessage(
            f"Projekt {self.projekt.name} an seinem Ort geöffnet. Eine "
            f"eigene Kopie davon liegt unter {kopie.parent}."
        )

    def _kopie_bei_speicherfehler(self, pfad: Path) -> bool:
        """Ob beim Scheitern des Speicherns von `pfad` die eigene Kopie
        angeboten wird: die Datei gehört zum offenen Projekt, und in
        dessen Ordner darf Natter nicht schreiben (Punkt 341)."""
        if self.projekt is None:
            return False
        ordner = self.projekt.ordner.resolve()
        return (
            Path(pfad).resolve().is_relative_to(ordner)
            and any(ordner.glob("*.natter"))
            and not ist_beispiel_original(ordner)
            and not ordner_beschreibbar(ordner)
        )

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
        # Hier und nicht nur in `oeffnen`: „Unit öffnen …“ (Strg+P) und
        # der Sprung aus der Suche kommen direkt hierher (Punkt 228).
        if self._beispiel_gesperrt(pfad):
            return None
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
        editor.kommentar_gewuenscht.connect(self._kommentar_umschalten_aktion)
        editor.cursorPositionChanged.connect(self._cursor_anzeige_aktualisieren)
        editor.schriftgroesse_setzen(self.editor_schriftgroesse())
        editor.schriftgroesse_geaendert.connect(self._editor_schriftgroesse_merken)
        editor.breakpoints_geaendert.connect(
            lambda e=editor: self._breakpoints_weitergeben(e)
        )
        editor.wert_gefragt.connect(self._wert_unter_maus_erfragen)
        editor.debugger_haelt = self._aktueller_thread_id is not None
        try:
            inhalt = pfad.read_text(encoding="utf-8-sig")
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
        gemerkt = self._gemerkte_haltepunkte_nehmen(pfad)
        if gemerkt is not None:
            editor.haltepunkte_setzen(*gemerkt)
        _stand_merken(editor)
        # Ein Tab, der nach der Prüfung aufgeht, zeigt seine Funde
        # trotzdem - sonst müsste man erst neu starten, um sie zu sehen.
        editor.funde_setzen(self._funde_der_datei(str(pfad)))
        editor.document().modificationChanged.connect(
            lambda geaendert, editor=editor: self._aenderung_markieren(editor, geaendert)
        )
        index = self.editor_tabs.addTab(editor, pfad.name)
        self.editor_tabs.setCurrentIndex(index)
        return editor

    def _designer_speichern(self, canvas: DesignerCanvas) -> bool:
        """Schreibt ein Formular erneut, dessen letzte Änderung nicht in
        die `.pfm` kam. Scheitert es wieder, meldet der Designer das
        noch einmal."""
        canvas.jetzt_schreiben()
        if not canvas.ungespeichert:
            return True
        canvas._schreibfehler_gemeldet = False
        canvas.ueberschreiben_abgelehnt = False
        gespeichert = canvas.speichern()
        self._designer_titel_auffrischen(canvas)
        return gespeichert

    def _designer_titel_auffrischen(self, canvas: DesignerCanvas) -> None:
        """Kennzeichnet einen Designer-Reiter wie einen geänderten
        Text-Reiter, solange seine Änderungen nicht in der `.pfm`
        stehen (Punkt 235)."""
        index = self._tab_index(canvas.formular._qwidget)
        if index == -1 or canvas.pfm_pfad is None:
            return
        titel = f"{canvas.pfm_pfad.stem} (Designer)"
        self.editor_tabs.setTabText(
            index, f"{titel} ●" if canvas.ungespeichert else titel
        )

    def _aenderung_markieren(self, editor: QPlainTextEdit, geaendert: bool) -> None:
        if not geaendert:
            # Gespeichert oder bis zum Stand der Datei zurückgenommen.
            self._sicherung_aufraeumen()
        index = self.editor_tabs.indexOf(editor)
        if index == -1:
            return
        basisname = Path(editor.property(_PFAD_EIGENSCHAFT)).name
        self.editor_tabs.setTabText(index, f"{basisname} ●" if geaendert else basisname)

    def _reiter_schliessen_fragen(self) -> QMessageBox.StandardButton:
        """Eigene Methode, damit Tests die Antwort vorgeben können."""
        return QMessageBox.question(
            self,
            "Ungespeicherte Änderungen",
            "Änderungen vor dem Schließen speichern?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
        )

    def _aktuelle_datei_speichern(self) -> bool:
        """„Speichern“ (Strg+S, Abschnitt 7.2, 7.9). Ein Designer-Reiter
        schreibt jede Änderung kurz danach von sich aus in die `.pfm`
        (Punkt 312); hier schreibt er eine noch wartende Änderung
        sofort und zählt sonst nur, wenn das zuletzt gescheitert ist
        (Punkt 235)."""
        index = self.editor_tabs.currentIndex()
        if index == -1:
            return False
        editor = self.editor_tabs.widget(index)
        canvas = self._widget_zu_canvas.get(self._tab_inhalt(editor))
        if canvas is not None:
            return self._designer_speichern(canvas)
        if not isinstance(editor, QPlainTextEdit):
            return False
        return self._editor_speichern(editor)

    def _editor_speichern(self, editor: QPlainTextEdit) -> bool:
        """Schreibt den Text eines Editors in seine Datei. Liefert, ob
        es geklappt hat.

        Hat sich die Datei seit dem Öffnen oder dem letzten Speichern
        auf der Platte geändert, etwa in einem zweiten Natter-Fenster
        auf demselben Projekt, wird vorher gefragt (Punkt 286). Bis
        0.3.6 schrieb Natter einfach darüber, und die andere Änderung
        war ohne Nachfrage verloren."""
        pfad = Path(editor.property(_PFAD_EIGENSCHAFT))
        if _von_aussen_geaendert(editor):
            antwort = self._von_aussen_geaendert_fragen(pfad.name)
            if antwort == "neu_laden":
                self._editor_neu_laden(editor)
                return False
            if antwort != "ueberschreiben":
                self.statusBar().showMessage(
                    f"„{pfad.name}“ wurde nicht gespeichert."
                )
                return False
        # Ein gescheitertes Speichern ist der schlimmste Fall von allen:
        # der Text steht noch im Fenster, die Datei auf der Platte ist
        # die alte. Der Tab bleibt deshalb als geändert markiert, wenn
        # es nicht geklappt hat (M11, Abschnitt 5).
        if not self.datei_schreiben_gemeldet(
            pfad, editor.toPlainText(), folge="Der Text steht noch im Editor."
        ):
            return False
        editor.document().setModified(False)
        _stand_merken(editor)
        return True

    def _von_aussen_geaendert_fragen(self, name: str) -> str:
        """Fragt, was mit einer Datei geschehen soll, die sich seit dem
        Öffnen auf der Platte geändert hat. Liefert die Antwort als
        Kennwort, wie `_editor_speichern` es prüft. Eigene Methode, damit Tests die
        Antwort vorgeben können."""
        fenster = QMessageBox(
            QMessageBox.Icon.Warning,
            "Datei wurde geändert",
            f"„{name}“ wurde seit dem Öffnen außerhalb dieses Fensters "
            "geändert, zum Beispiel in einem zweiten Natter-Fenster.\n\n"
            "„Überschreiben“ speichert den Text aus diesem Editor, die "
            "andere Änderung geht dabei verloren. „Neu laden“ holt den "
            "Stand von der Platte in den Editor, die Änderungen in "
            "diesem Editor gehen verloren, lassen sich aber mit "
            "Strg+Z zurückholen.",
            parent=self,
        )
        ueberschreiben = fenster.addButton(
            "Überschreiben", QMessageBox.ButtonRole.AcceptRole
        )
        neu_laden = fenster.addButton(
            "Neu laden", QMessageBox.ButtonRole.DestructiveRole
        )
        abbrechen = fenster.addButton(QMessageBox.StandardButton.Cancel)
        fenster.setDefaultButton(abbrechen)
        fenster.exec()
        if fenster.clickedButton() is ueberschreiben:
            return "ueberschreiben"
        if fenster.clickedButton() is neu_laden:
            return "neu_laden"
        return "abbrechen"

    def _editor_neu_laden(self, editor: QPlainTextEdit) -> bool:
        """Holt den Stand von der Platte in den Editor, als einen
        Bearbeitungsschritt, den Strg+Z zurücknimmt."""
        from ide.designer.canvas import editortext_ersetzen

        pfad = Path(editor.property(_PFAD_EIGENSCHAFT))
        try:
            inhalt = pfad.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError) as fehler:
            self.statusBar().showMessage(
                f"„{pfad.name}“ lässt sich nicht neu laden: {fehler}"
            )
            return False
        editortext_ersetzen(editor, inhalt)
        editor.document().setModified(False)
        _stand_merken(editor)
        return True

    def _von_aussen_geaenderte_neu_laden(self) -> None:
        """Lädt jede Datei neu, die sich auf der Platte geändert hat
        und im Editor keine ungespeicherten Änderungen hat. Läuft, wenn
        das Fenster wieder in den Vordergrund kommt (Punkt 286)."""
        for index in range(self.editor_tabs.count()):
            editor = self._tab_inhalt(self.editor_tabs.widget(index))
            if (
                isinstance(editor, QPlainTextEdit)
                and editor.property(_PFAD_EIGENSCHAFT)
                and not editor.document().isModified()
                and _von_aussen_geaendert(editor)
            ):
                self._editor_neu_laden(editor)

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if (
            event.type() == QEvent.Type.ActivationChange
            and self.isActiveWindow()
        ):
            self._von_aussen_geaenderte_neu_laden()

    def _ungespeicherte_editoren(self) -> list[QPlainTextEdit]:
        editoren = []
        for index in range(self.editor_tabs.count()):
            widget = self._tab_inhalt(self.editor_tabs.widget(index))
            if (
                isinstance(widget, QPlainTextEdit)
                and widget.document().isModified()
                and widget.property(_PFAD_EIGENSCHAFT)
            ):
                editoren.append(widget)
        return editoren

    def designer_nachschreiben(self) -> None:
        """Schreibt in jedem offenen Designer eine Änderung, die noch
        auf ihren Schreibzeitpunkt wartet (Punkt 312). Läuft vor allem,
        was `.pfm` oder `_design.py` von der Platte liest oder einen
        Designer schließt. Einen Fehler beim Schreiben meldet der
        Designer selbst."""
        for canvas in list(self._offene_canvases):
            canvas.jetzt_schreiben()

    def alle_speichern(self) -> bool:
        """Speichert jede geänderte Datei. `False`, wenn eine sich
        nicht schreiben ließ - sie bleibt dann als geändert markiert,
        und die Meldung dazu hat `datei_schreiben_gemeldet` schon
        gezeigt."""
        self.designer_nachschreiben()
        alles_gut = True
        for editor in self._ungespeicherte_editoren():
            if not self._editor_speichern(editor):
                alles_gut = False
        # Offene Diagramme gehören dazu (Punkt 111).
        for fenster in self._ungespeicherte_diagramme():
            if not fenster.speichern():
                alles_gut = False
        self._sicherung_aufraeumen()
        return alles_gut

    def _ungespeicherte_diagramme(self) -> list:
        return [f for f in self._offene_diagramme.values() if f.geaendert]

    def _alle_speichern_aktion(self) -> None:
        """„Datei → Alle speichern“ (Strg+Umschalt+S, Punkt 85)."""
        anzahl = len(self._ungespeicherte_editoren()) + len(self._ungespeicherte_diagramme())
        if anzahl == 0:
            self.statusBar().showMessage("Es gibt nichts zu speichern, alles ist gespeichert.")
            return
        if self.alle_speichern():
            self.statusBar().showMessage(
                "1 Datei gespeichert." if anzahl == 1 else f"{anzahl} Dateien gespeichert."
            )

    def _vor_dem_schliessen_fragen(self, namen: list[str]) -> QMessageBox.StandardButton:
        """Eigene Methode, damit Tests die Antwort vorgeben können,
        ohne dass ein Fenster auf einen Klick wartet.

        Steht `TRANSAKTION_EINTRAG` in `namen`, gilt „Speichern“ auch
        für die offene Transaktion im Datenbank-Panel und „Verwerfen“
        nimmt sie zurück (Punkt 276)."""
        liste = "\n".join(f"  {name}" for name in namen)
        if TRANSAKTION_EINTRAG in namen:
            text = (
                f"Noch nicht gespeichert oder festgeschrieben:\n\n"
                f"{liste}\n\n"
                "Vor dem Schließen speichern und die Transaktion "
                "festschreiben? „Verwerfen“ nimmt die Transaktion "
                "zurück."
            )
        else:
            text = (
                f"Diese Dateien haben ungespeicherte Änderungen:\n\n"
                f"{liste}\n\nVor dem Schließen speichern?"
            )
        return QMessageBox.question(
            self,
            "Ungespeicherte Änderungen",
            text,
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )

    def _vor_dem_schliessen_klaeren(
        self, namen: list[str], speichern: Callable[[], bool]
    ) -> bool:
        """Fragt nach ungespeicherten Dateien `namen` und einer offenen
        Transaktion im Datenbank-Panel, alles in einer Nachfrage.
        Liefert, ob das Schließen weitergehen darf.

        Bis 0.3.6 nahm das Schließen die Transaktion wortlos zurück;
        der Hinweis darauf stand in der Statuszeile eines Fensters, das
        im selben Augenblick zuging (Punkt 276)."""
        transaktion = self.datenbank_panel.transaktion_offen
        namen = [*namen, TRANSAKTION_EINTRAG] if transaktion else namen
        if not namen:
            return True
        antwort = self._vor_dem_schliessen_fragen(namen)
        if antwort == QMessageBox.StandardButton.Cancel:
            return False
        if antwort == QMessageBox.StandardButton.Save:
            if not speichern():
                return False
            if transaktion:
                return self._transaktion_festschreiben_gemeldet()
        elif transaktion:
            self.datenbank_panel.transaktion_zuruecknehmen()
        return True

    def _transaktion_festschreiben_gemeldet(self) -> bool:
        """Schreibt die offene Transaktion im Datenbank-Panel fest und
        meldet ein Scheitern als Fenster. Liefert, ob es geklappt hat."""
        grund = self.datenbank_panel.transaktion_festschreiben()
        if grund is None:
            return True
        QMessageBox.warning(
            self,
            "Nicht festgeschrieben",
            "Die Transaktion im Datenbank-Panel ließ sich nicht "
            f"festschreiben:\n{grund}",
        )
        return False

    def _transaktion_vor_dem_start_fragen(self) -> str:
        """Fragt, was mit der offenen Transaktion im Datenbank-Panel
        geschehen soll. Liefert `"festschreiben"`, `"zuruecknehmen"`
        oder `"abbrechen"`. Eigene Methode, damit Tests die Antwort vorgeben
        können."""
        return transaktion_nachfragen(
            self,
            "Im Datenbank-Panel ist noch eine Transaktion offen. Solange "
            "sie offen ist, bleibt die Datenbankdatei gesperrt, und das "
            "Programm kann sie nicht beschreiben.",
            "Vor dem Start festschreiben oder zurücknehmen?",
        )

    def _transaktion_vor_dem_start_klaeren(self) -> bool:
        """Liefert, ob der Start weitergehen darf (Punkt 276).

        Eine im Datenbank-Panel offene Transaktion hält die Sperre auf
        der Datei. Das gestartete Programm sah bis 0.3.6 die Änderungen
        darin nicht, wartete bei jedem Schreiben fünf Sekunden und
        scheiterte dann mit „database is locked“ - gesperrt von Natter
        selbst, was die Meldung nicht verrät."""
        if not self.datenbank_panel.transaktion_offen:
            return True
        antwort = self._transaktion_vor_dem_start_fragen()
        if antwort == "festschreiben":
            return self._transaktion_festschreiben_gemeldet()
        if antwort == "zuruecknehmen":
            self.datenbank_panel.transaktion_zuruecknehmen()
            return True
        self.statusBar().showMessage(
            "Nicht gestartet - im Datenbank-Panel ist noch eine "
            "Transaktion offen."
        )
        return False

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
            atomar_schreiben(Path(pfad), inhalt, encoding="utf-8")
        except PermissionError:
            # Ohne den Text von Windows: er nennt die Zwischendatei aus
            # `atomar_schreiben`, die niemand kennt, und ist zum Teil
            # englisch (Punkt 321).
            if self._kopie_bei_speicherfehler(Path(pfad)):
                # Punkt 341: statt nur die Gründe aufzuzählen, gleich
                # den Weg an einen beschreibbaren Ort anbieten. Der
                # Wechsel läuft erst nach dem Speichern, das hier
                # scheiterte; es kann mitten in einem anderen Wechsel
                # oder im Schließen des Fensters stecken.
                if self._kopie_anbieten(
                    "Nicht gespeichert",
                    f"„{Path(pfad).name}“ konnte nicht gespeichert werden: "
                    f"In den Ordner\n{self.projekt.ordner}\ndarf Natter "
                    "nicht schreiben.\n\n"
                    + (f"{folge}\n\n" if folge else "")
                    + self._kopie_folge(
                        self._eigene_kopie_des_projekts(),
                        natter_ordner(), True,
                    ),
                    "Schließen",
                    warnung=True,
                ):
                    QTimer.singleShot(0, self._kopie_nach_speicherfehler)
                return False
            QMessageBox.warning(
                self,
                "Nicht gespeichert",
                f"„{Path(pfad).name}“ konnte nicht gespeichert werden: "
                f"Das Schreiben in\n{Path(pfad).parent}\nwurde verweigert."
                "\n\n"
                + (f"{folge}\n\n" if folge else "")
                + "Häufige Gründe: der Ordner hat kein Schreibrecht, etwa "
                "eine Freigabe nur zum Lesen; die Datei ist "
                "schreibgeschützt oder in einem anderen Programm geöffnet.",
            )
            return False
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

    def _falten_aktion(self, *, zu: bool) -> None:
        """„Quelltext → Alles zuklappen / aufklappen“ (Punkt 76)."""
        editor = self._aktueller_editor()
        if not isinstance(editor, QuelltextEditor):
            self.statusBar().showMessage("Zuklappen geht nur in einer geöffneten Python-Datei.")
            return
        if zu:
            editor.alles_falten()
        else:
            editor.alles_entfalten()

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
        elif self._aktueller_canvas is not None:
            self._aktueller_canvas.ausschneiden()

    def _bearbeiten_kopieren(self) -> None:
        editor = self._aktueller_editor()
        if editor is not None:
            editor.copy()
        elif self._aktueller_canvas is not None:
            self._aktueller_canvas.kopieren()

    def _bearbeiten_einfuegen(self) -> None:
        editor = self._aktueller_editor()
        if editor is not None:
            editor.paste()
        elif self._aktueller_canvas is not None and not self._aktueller_canvas.einfuegen():
            self.statusBar().showMessage(
                "In der Zwischenablage liegen keine Komponenten. Zuerst im Designer "
                "welche auswählen und kopieren."
            )

    def _designer_duplizieren(self) -> None:
        if self._aktueller_canvas is not None:
            self._aktueller_canvas.duplizieren()

    def _designer_loeschen(self) -> None:
        if self._aktueller_canvas is not None:
            self._aktueller_canvas.loeschen()

    def _designer_anordnen(self) -> None:
        """Zeigt das Menü der gewählten Komponente mit Ausrichten,
        Raster und Tab-Reihenfolge an ihrer Stelle - dieselben Einträge
        wie bei der rechten Maustaste."""
        canvas = self._aktueller_canvas
        if canvas is None:
            return
        komponente = canvas.ausgewaehlte_komponente or canvas.formular
        widget = komponente._qwidget
        menue = canvas.kontextmenue_fuer(komponente)
        menue.popup(widget.mapToGlobal(widget.rect().center()))

    def _bearbeiten_alles_auswaehlen(self) -> None:
        editor = self._aktueller_editor()
        if editor is not None:
            editor.selectAll()
        elif self._aktueller_canvas is not None:
            self._aktueller_canvas.alles_auswaehlen()

    # -- Suchen (Abschnitt 7.2) -----------------------------------------------

    def _suchen_aktion(self) -> None:
        hilfe = self.editor_tabs.currentWidget()
        if isinstance(hilfe, HilfeAnsicht):
            # Strg+F in einer Hilfeseite sucht in der Seite (Punkt 438).
            hilfe.suche_zeigen()
            return
        editor = self._aktueller_editor()
        if editor is None:
            self.statusBar().showMessage(
                "Kein Quelltext-Reiter vorn. Zuerst links im "
                "Projekt-Explorer eine Quelltextdatei doppelklicken."
            )
            return
        # Derselbe Dialog wie beim letzten Mal: Suchtext und Schalter
        # bleiben stehen (Punkt 102). Eine Markierung im Editor wird zum
        # neuen Suchtext.
        dialog = getattr(self, "_suchen_dialog", None)
        if dialog is None:
            dialog = SuchenErsetzenDialog(editor, self)
            self._suchen_dialog = dialog
        dialog.editor_setzen(editor)
        dialog.markierung_uebernehmen()
        self._suchen_dialog.show()
        self._suchen_dialog.raise_()
        self._suchen_dialog.activateWindow()

    def _in_dateien_suchen_aktion(self) -> None:
        """„Suchen → In allen Dateien suchen …“ (Strg+Umschalt+F)."""
        from ide.shell.in_dateien_suchen import InDateienSuchen

        if self.projekt is None:
            self.statusBar().showMessage(self._kein_projekt_text())
            return
        dialog = InDateienSuchen(
            sorted(self.projekt.units()),
            self._aktueller_text_von,
            self.datei_an_zeile_oeffnen,
            self,
        )
        editor = self._aktueller_editor()
        if editor is not None:
            markiert = editor.textCursor().selectedText()
            if markiert and "\u2029" not in markiert:
                dialog.suchfeld.setText(markiert)
        self.letzter_dateisuche_dialog = dialog
        dialog.show()

    def _aktueller_text_von(self, pfad: Path) -> str:
        """Der Text einer Datei, wie er gerade im Editor steht - sonst
        wie auf der Platte."""
        for index in range(self.editor_tabs.count()):
            widget = self._tab_inhalt(self.editor_tabs.widget(index))
            if isinstance(widget, QPlainTextEdit) and widget.property(_PFAD_EIGENSCHAFT) == str(
                pfad
            ):
                return widget.toPlainText()
        try:
            return pfad.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError):
            return ""

    def datei_an_zeile_oeffnen(self, pfad: Path, zeile: int) -> None:
        """Sprung aus der Suche in allen Dateien - Alt+Links führt
        zurück."""
        self.sprung_merken()
        self._datei_an_zeile(pfad, zeile)

    def _datei_an_zeile(self, pfad: Path, zeile: int) -> None:
        editor = self.datei_oeffnen(pfad)
        if not isinstance(editor, QPlainTextEdit):
            return
        block = editor.document().findBlockByNumber(zeile - 1)
        cursor = editor.textCursor()
        cursor.setPosition(block.position())
        editor.setTextCursor(cursor)
        editor.ensureCursorVisible()
        editor.setFocus()

    def _weitersuchen_aktion(self, rueckwaerts: bool = False) -> None:
        """„Suchen → Weitersuchen“ (F3, Punkt 85): der nächste Treffer
        des zuletzt gesuchten Textes, ohne den Dialog wieder zu öffnen.
        Wurde noch nichts gesucht, öffnet sich der Suchdialog."""
        hilfe = self.editor_tabs.currentWidget()
        if isinstance(hilfe, HilfeAnsicht) and hilfe.suchfeld.text():
            hilfe.weitersuchen(rueckwaerts=rueckwaerts)
            return
        editor = self._aktueller_editor()
        dialog = getattr(self, "_suchen_dialog", None)
        if editor is None or dialog is None or not dialog.suchfeld.text():
            self._suchen_aktion()
            return
        dialog.editor_setzen(editor)
        if not dialog.suchen(rueckwaerts=rueckwaerts):
            self.statusBar().showMessage(f"„{dialog.suchfeld.text()}“ kommt nicht vor.")

    def _gehe_zu_zeile_aktion(self) -> None:
        editor = self._aktueller_editor()
        if editor is None:
            self.statusBar().showMessage(
                "Kein Quelltext-Reiter vorn. Zuerst links im "
                "Projekt-Explorer eine Quelltextdatei doppelklicken."
            )
            return
        maximum = editor.document().blockCount()
        zeile, ok = QInputDialog.getInt(self, "Zu Zeile springen", "Zeile:", 1, 1, maximum)
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
        markiert = cursor.hasSelection()
        spalte = cursor.positionInBlock()

        erster = dokument.findBlockByNumber(start_block)
        letzter = dokument.findBlockByNumber(end_block)
        ersetz_cursor = QTextCursor(dokument)
        ersetz_cursor.beginEditBlock()
        ersetz_cursor.setPosition(erster.position())
        ersetz_cursor.setPosition(
            letzter.position() + letzter.length() - 1, QTextCursor.MoveMode.KeepAnchor
        )
        ersetz_cursor.insertText("\n".join(neue_zeilen))
        ersetz_cursor.endEditBlock()

        # Punkt 220: die umgeschalteten Zeilen bleiben markiert wie
        # nach Tab und Umschalt+Tab, damit ein zweites Strg+# alle
        # wieder einkommentiert und nicht nur die letzte Zeile. Ohne
        # Markierung bleibt die Schreibmarke an ihrer Stelle im Code
        # und rückt nur um das eingefügte oder entfernte `# ` mit.
        erster = dokument.findBlockByNumber(start_block)
        letzter = dokument.findBlockByNumber(end_block)
        neuer_cursor = QTextCursor(dokument)
        if markiert:
            neuer_cursor.setPosition(erster.position())
            neuer_cursor.setPosition(
                letzter.position() + letzter.length() - 1,
                QTextCursor.MoveMode.KeepAnchor,
            )
        else:
            versatz = len(neue_zeilen[0]) - len(zeilen[0])
            spalte = max(0, min(spalte + versatz, erster.length() - 1))
            neuer_cursor.setPosition(erster.position() + spalte)
        editor.setTextCursor(neuer_cursor)

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
        _designvorgabe_setzen(thema)
        self._stil_anwenden()
        self._design_einstellungen.setValue("design/thema", thema)

        # Offene Formulare im Designer. Ein `Form` legt sein Stylesheet
        # beim Erzeugen fest, und ohne diesen Schritt blieb die
        # Vorschau im alten Design stehen, bis der Tab neu geöffnet
        # wurde - Natter war hell, das Formular darin dunkel.
        for canvas in self._offene_canvases:
            canvas.formular._stylesheet_aktualisieren()

        aufgeloest = theme_aufloesen(thema)
        for index in range(self.editor_tabs.count()):
            editor = self.editor_tabs.widget(index)
            if isinstance(editor, QuelltextEditor):
                editor.thema_setzen(aufgeloest)
            elif isinstance(editor, HilfeAnsicht):
                editor.thema_setzen(aufgeloest == "dark")

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

    # -- Navigation (Punkt 106) ---------------------------------------

    def _zuletzt_menue_aufbauen(self) -> None:
        """Füllt „Datei → Zuletzt geöffnet“.

        Im Prüfungsmodus gesperrt wie die Beispielprojekte (Punkt
        145): die Rückfrage beim Einschalten sagt, dass die zuletzt
        geöffneten Projekte dann nicht erreichbar sind, und auf der
        Startseite fehlten sie auch; nur dieses Menü öffnete sie
        weiter. Geöffnet wird über `projekt_oeffnen_gemeldet`, damit
        eine beschädigte Projektdatei eine Meldung ergibt und ein
        mitgeliefertes Original nur als Kopie aufgeht.
        """
        from ide.shell.startbild import zuletzt_geoeffnet

        self._zuletzt_menue.clear()
        if pruefungsmodus_laeuft():
            self._zuletzt_menue.setTitle("Zuletzt geöffnet (im Prüfungsmodus gesperrt)")
            self._zuletzt_menue.setEnabled(False)
            return
        self._zuletzt_menue.setTitle("Zuletzt geöffnet")
        for pfad in zuletzt_geoeffnet(self._design_einstellungen):
            eintrag = self._zuletzt_menue.addAction(pfad.stem)
            eintrag.setStatusTip(str(pfad))
            eintrag.triggered.connect(
                lambda *_, p=pfad: self._zuletzt_geoeffnetes_oeffnen(p)
            )
        self._zuletzt_menue.setEnabled(not self._zuletzt_menue.isEmpty())

    def _zuletzt_geoeffnetes_oeffnen(self, pfad: Path) -> Projekt | None:
        """Ein Eintrag unter „Zuletzt geöffnet“. Der Prüfungsmodus wird
        hier noch einmal abgefragt: das Menü kann aufgeklappt worden
        sein, bevor er begann."""
        if pruefungsmodus_laeuft():
            self.statusBar().showMessage(
                "Im Prüfungsmodus sind die zuletzt geöffneten Projekte gesperrt."
            )
            return None
        return self.projekt_oeffnen_gemeldet(pfad)

    def _reiter_schliessen_aktion(self) -> None:
        """„Fenster → Reiter schließen“ (Strg+W): wie das „×“ am Reiter,
        mit derselben Nachfrage bei ungespeicherten Änderungen."""
        index = self.editor_tabs.currentIndex()
        if index == -1:
            self.statusBar().showMessage("Es ist kein Reiter offen.")
            return
        self._tab_schliessen(index)

    def sprung_merken(self) -> None:
        """Merkt sich Datei und Zeile vor einem Sprung (F12, Treffer
        einer Suche in allen Dateien), damit Alt+Links dorthin
        zurückführt."""
        editor = self._aktueller_editor()
        pfad = editor.property(_PFAD_EIGENSCHAFT) if editor is not None else None
        if not pfad:
            return
        stelle = (Path(pfad), editor.textCursor().blockNumber() + 1)
        verlauf = self.__dict__.setdefault("_sprungverlauf", [])
        if not verlauf or verlauf[-1] != stelle:
            verlauf.append(stelle)
        del verlauf[:-50]

    def _zurueck_aktion(self) -> None:
        """„Suchen → Zurück zur vorigen Stelle“ (Alt+Links)."""
        verlauf = self.__dict__.get("_sprungverlauf", [])
        while verlauf:
            pfad, zeile = verlauf.pop()
            if pfad.exists():
                self._datei_an_zeile(pfad, zeile)
                return
        self.statusBar().showMessage("Es gibt keine vorige Stelle, zu der es zurückginge.")

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
            self.sprung_merken()
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
            if pfad and _gleiche_datei(fund.datei, pfad):
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
            "erzeugen. Die zuletzt geöffneten Projekte und die "
            "Beispielprojekte sind in dieser Zeit nicht erreichbar.\n\n"
            "Er lässt sich bis dahin nicht abschalten und läuft danach von "
            "selbst aus. Jetzt starten?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if antwort != QMessageBox.StandardButton.Yes:
            self.statusBar().showMessage("Prüfungsmodus nicht gestartet.")
            return False

        pruefungsmodus_starten()
        # Ohne diesen Aufruf bliebe die Liste „Zuletzt geöffnet"
        # stehen und das Beispielmenü offen, bis jemand das Fenster
        # wechselt - also genau so lange, wie es darauf ankommt.
        self._pruefungsmodus_nachfuehren()
        self.statusBar().showMessage(
            f"{restzeit_text()}. Lösungsvorschläge und Quelltexterzeugung sind "
            "bis dahin gesperrt."
        )
        return True

    def _beispiele_im_modus_schliessen(self) -> None:
        """Schließt im Prüfungsmodus ein offenes Beispielprojekt oder
        seine Arbeitskopie samt Reitern und Diagrammfenstern, dazu
        jede einzeln geöffnete Datei daraus (Punkt 228).

        Bis 0.3.6 blieb ein Beispiel, das beim Einschalten offen war,
        ganz bedienbar: „Unit öffnen …“, die Suche in allen Dateien,
        die offenen Reiter und F5 zeigten die Lösungen weiter, obwohl
        die Rückfrage beim Einschalten sagt, die Beispiele seien in
        dieser Zeit nicht erreichbar. Geänderte Dateien werden vorher
        gespeichert; verloren geht dabei nichts.
        """

        def im_beispiel(pfad: Path) -> bool:
            return _beispiel_projektordner(Path(pfad)) is not None

        for editor in self._ungespeicherte_editoren():
            pfad = Path(editor.property(_PFAD_EIGENSCHAFT))
            if im_beispiel(pfad) and self.datei_schreiben_gemeldet(
                pfad, editor.toPlainText(), folge="Der Reiter wird trotzdem geschlossen."
            ):
                editor.document().setModified(False)
        geschlossen = False
        for schluessel, fenster in list(self._offene_diagramme.items()):
            if not im_beispiel(Path(schluessel)):
                continue
            if fenster._geaendert:
                fenster.speichern()
            del self._offene_diagramme[schluessel]
            fenster._geaendert = False
            fenster.close()
            fenster.deleteLater()
            geschlossen = True
        vorher = self.editor_tabs.count()
        self._reiter_schliessen_wenn(im_beispiel)
        geschlossen = geschlossen or self.editor_tabs.count() != vorher
        if self.projekt is not None and im_beispiel(self.projekt.ordner):
            sperre.freigeben(self.projekt.ordner)
            self._haltepunkte_ablegen()
            self.projekt = None
            self._projekt_datei = None
            self._gemerkte_haltepunkte.clear()
            self.explorer.leeren()
            self._zuruecksetzen_pruefen()
            geschlossen = True
        if geschlossen:
            self.statusBar().showMessage(
                f"Beispielprojekt geschlossen. {GESPERRT_HINWEIS}"
            )

    def _pruefungsmodus_nachfuehren(self) -> None:
        """Bringt Restzeit, Beispielmenü, „Zuletzt geöffnet“, die
        Vervollständigung und die Startseite auf den Stand des
        Prüfungsmodus.

        Läuft beim Einschalten und danach jede halbe Minute über
        `_pruefungsuhr` (Punkt 151). Bis 0.3.5 wurde das nur beim
        Aufbau des Fensters und beim Einschalten gesetzt: die Restzeit
        zählte nicht herunter, und nach dem Ablauf blieben Anzeige und
        gesperrte Menüs bis zum nächsten Start von Natter stehen.
        """
        laeuft = pruefungsmodus_laeuft()
        if laeuft:
            self._beispiele_im_modus_schliessen()
        self._statusleiste_pruefung_aktualisieren()
        self._beispielmenue_pruefen()
        self._zuruecksetzen_pruefen()
        self._vervollstaendigung_pruefen()
        if hasattr(self, "_zuletzt_menue"):
            self._zuletzt_menue_aufbauen()
        # Offene Diagrammfenster haben ein eigenes Menü mit
        # „Quelltext → Erzeugen …“ (Punkt 188).
        for fenster in list(getattr(self, "_offene_diagramme", {}).values()):
            try:
                fenster.pruefungsmodus_nachfuehren()
            except RuntimeError:
                # Schon von Qt gelöscht, der Eintrag geht gleich weg.
                pass
        # Die Startseite nur neu aufbauen, wenn der Modus an- oder
        # ausgegangen ist. Sonst ersetzte die Uhr alle halbe Minute
        # ihre Knöpfe, auch unter dem Mauszeiger.
        if laeuft != getattr(self, "_pruefung_lief", None):
            self._pruefung_lief = laeuft
            self.startbild.aufbauen()

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
        self._stil_anwenden()
        self._design_einstellungen.setValue("editor/schriftart", schriftart)

        for index in range(self.editor_tabs.count()):
            editor = self.editor_tabs.widget(index)
            if isinstance(editor, QuelltextEditor):
                editor.schriftart_setzen(schriftart)

    def fensterlage_herstellen(self) -> None:
        """Größe, Lage und Maximiert-Zustand vom letzten Mal, beim
        ersten Start ein maximiertes Fenster (Punkt 299).

        Ohne Vorgabe gab Qt dem Fenster höchstens zwei Drittel des
        Bildschirms; auf einem Beamer mit 1280 × 800 blieben so rund
        850 × 560 Pixel, und die Startseite war zwischen den Docks
        eingeklemmt. Wird vor `show()` aufgerufen (`ide/main.py`).

        Stand das Fenster zuletzt auf einem Bildschirm, der nicht mehr
        angeschlossen ist - etwa am Beamer, der inzwischen abgesteckt
        ist -, öffnet es maximiert auf dem Hauptbildschirm."""
        gespeichert = self._design_einstellungen.value("fenster/geometrie")
        if (
            isinstance(gespeichert, (bytes, bytearray, QByteArray))
            and self.restoreGeometry(QByteArray(gespeichert))
            and self._auf_einem_bildschirm()
        ):
            return
        bildschirm = QGuiApplication.primaryScreen()
        if bildschirm is not None:
            # Die Größe, die das Fenster nach „Verkleinern“ hat: 90 %
            # der freien Fläche, mittig.
            flaeche = bildschirm.availableGeometry()
            breite = flaeche.width() * 9 // 10
            hoehe = flaeche.height() * 9 // 10
            self.setGeometry(
                flaeche.x() + (flaeche.width() - breite) // 2,
                flaeche.y() + (flaeche.height() - hoehe) // 2,
                breite,
                hoehe,
            )
        self.setWindowState(
            self.windowState() | Qt.WindowState.WindowMaximized
        )

    def _auf_einem_bildschirm(self) -> bool:
        """Ob die Titelleiste des Fensters auf einem der angeschlossenen
        Bildschirme liegt - sonst ließe es sich nicht mehr greifen."""
        rahmen = self.normalGeometry()
        if not rahmen.isValid():
            rahmen = self.geometry()
        titel = QRect(rahmen.x(), rahmen.y(), rahmen.width(), 30)
        return any(
            b.availableGeometry().intersects(titel)
            for b in QGuiApplication.screens()
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        """Merkt sich Größe/Sichtbarkeit aller Docks für den nächsten
 Start (Gewünscht: ein geschlossenes Dock
 wie „Datenbank“ soll auch beim nächsten Mal zu bleiben) – und
 beendet ein noch laufendes Schülerprogramm.

        Vorher wird nach ungespeicherten Änderungen gefragt (Punkt 84).
        Beim Schließen eines einzelnen Reiters gab es die Frage schon,
        beim Schließen des ganzen Fensters gingen die Änderungen bis
        0.3.5 ohne ein Wort verloren. Eine offene Transaktion im
        Datenbank-Panel steht in derselben Nachfrage (Punkt 276). Läuft
        noch ein Programm, kommt davor die Frage, ob es enden soll
        (Punkt 433)."""
        if self._schliesst_nach_zip:
            # Schon unterwegs: das Fenster wartet auf die ZIP und
            # schließt danach ohnehin.
            event.ignore()
            return
        # Zuerst das laufende Programm, dann das Speichern: wer hier
        # abbricht, soll nicht vorher schon gespeichert haben.
        if self._programm_laeuft() and not self._laufendes_programm_fragen():
            event.ignore()
            return
        self.designer_nachschreiben()
        if not self._vor_dem_schliessen_klaeren(
            self._ungespeicherte_namen(), self.alle_speichern
        ):
            event.ignore()
            return
        self._sicherung_entfernen()
        self._beim_beenden_aufraeumen()
        super().closeEvent(event)

    def _laufendes_programm_fragen(self) -> bool:
        """Fragt beim Schließen, ob das laufende Programm mit Natter
        enden soll. Liefert, ob geschlossen werden darf. Eigene
        Methode, damit Tests die Antwort vorgeben können.

        Bis 0.4.2 endete das Programm ohne Nachfrage. Liegen Natter
        und das Programm übereinander, trifft ein Klick leicht das
        Kreuz des falschen Fensters, und was im Programm eingegeben
        war, ist weg (Punkt 433). Beim Ende der Windows-Sitzung kommt
        die Frage nicht: dort läuft `closeEvent` nicht, und
        `_beim_beenden_aufraeumen` beendet das Programm wie bisher.

        Vorgewählt ist „Abbrechen“, denn die Frage kommt meist nach
        einem Klick, der nicht Natter galt."""
        box = QMessageBox(
            QMessageBox.Icon.Question,
            "Programm läuft noch",
            "Das Programm läuft noch. Beenden und Natter schließen?",
            parent=self,
        )
        beenden = box.addButton(
            "Beenden und schließen", QMessageBox.ButtonRole.AcceptRole
        )
        abbrechen = box.addButton(
            "Abbrechen", QMessageBox.ButtonRole.RejectRole
        )
        box.setDefaultButton(abbrechen)
        box.setEscapeButton(abbrechen)
        box.exec()
        return box.clickedButton() is beenden

    def _ungespeicherte_namen(self) -> list[str]:
        """Die Dateinamen aller geänderten Editoren und Diagramme, wie
        sie in der Nachfrage vor dem Schließen stehen."""
        namen = [
            Path(editor.property(_PFAD_EIGENSCHAFT)).name
            for editor in self._ungespeicherte_editoren()
        ]
        namen += [f.diagramm.pfad.name for f in self._ungespeicherte_diagramme()]
        return namen

    def _beim_beenden_aufraeumen(self) -> None:
        """Was beim Schließen des Fensters und beim Ende der
        Windows-Sitzung gleichermaßen geschehen muss: Sperrdatei
        freigeben, Fensterlage merken, laufende Programme und Vorgänge
        beenden, die Datenbank trennen.

        Hängt auch an `aboutToQuit`. Beim Abmelden läuft `closeEvent`
        nicht (Punkt 338), und ohne diesen Weg blieben die Sperrdatei
        und ein laufendes Schülerprogramm zurück. Nach dem ersten
        Durchlauf werden die Signale der Anwendung gelöst, damit ein
        geschlossenes Fenster beim Beenden nicht ein zweites Mal
        aufräumt."""
        self._zip_abwarten()
        self._sitzung_loesen()
        # Die Sicherung bleibt hier, wie sie ist. Endet die Sitzung,
        # während die Frage noch offen ist, etwa nach „Trotzdem
        # abmelden“, ist sie das Einzige, was vom Text bleibt. Ab
        # jetzt bietet ein anderes Fenster den Anteil dieses Fensters
        # beim Öffnen an.
        self._sicherung_uhr.stop()
        sicherung.fenster_geschlossen(self._sicherung_herkunft)
        # Die Frage ist beantwortet; die Diagrammfenster schließen mit,
        # ohne noch einmal selbst zu fragen.
        for fenster in list(self._offene_diagramme.values()):
            fenster._geaendert = False
            fenster.close()
        if self.projekt is not None:
            sperre.freigeben(self.projekt.ordner)
        self._haltepunkte_ablegen()
        self._design_einstellungen.setValue("fenster/layout", self.saveState())
        self._design_einstellungen.setValue(
            "fenster/geometrie", self.saveGeometry()
        )
        self._hintergrund_abbrechen()
        self.kindprozesse_beenden()
        self.datenbank_panel.trennen()

    def _sitzung_loesen(self) -> None:
        if not self._sitzung_verbunden:
            return
        self._sitzung_verbunden = False
        anwendung = QGuiApplication.instance()
        if anwendung is None:
            return
        anwendung.commitDataRequest.disconnect(self._sitzungsende_klaeren)
        anwendung.aboutToQuit.disconnect(self._beim_beenden_aufraeumen)

    def _sitzungsende_klaeren(self, manager: QSessionManager) -> None:
        """Antwort auf `commitDataRequest`, das Qt beim Abmelden und
        Herunterfahren sendet (Punkt 338).

        Darf Natter nachfragen, kommt dieselbe Frage wie beim
        Schließen des Fensters; „Abbrechen“ hält das Abmelden auf, und
        Windows nennt Natter dann als Programm, das es verhindert.
        Aufgeräumt wird hier noch nicht: bricht ein anderes Programm
        das Abmelden ab, bleibt Natter offen und arbeitet weiter. Das
        Aufräumen folgt erst mit `aboutToQuit`.

        Darf Natter nicht nachfragen, wird gespeichert, wie es der
        vorgewählte Knopf „Speichern“ der Frage täte. Die offene
        Transaktion im Datenbank-Panel wird dagegen zurückgenommen:
        Daten in der Datenbank ändern sich nur mit Zustimmung, der Text
        im Editor ginge ohne Speichern ganz verloren.

        Solange die Frage offen ist, nennt Natter Windows den Grund
        (Punkt 344). Windows zeigt ihn auf seiner Seite mit dem Knopf
        „Trotzdem abmelden“; ohne ihn stand dort nur der Name des
        Fensters, und nichts deutete darauf hin, dass der Knopf den
        ungespeicherten Text kostet.

        Vor der Frage kommt jeder ungespeicherte Editor und jedes
        geänderte Diagramm des Projekts in die Sicherung. Beendet
        Windows Natter, während die Frage offen ist, bietet Natter den
        Text beim nächsten Öffnen des Projekts wieder an. Nach
        „Speichern“ oder „Verwerfen“ wird die Sicherung wieder
        entfernt."""
        self.designer_nachschreiben()
        self._sicherung_schreiben()
        if manager.allowsInteraction():
            namen = self._ungespeicherte_namen()
            kennung = int(self.winId()) if namen else 0
            if namen:
                abmeldegrund.grund_nennen(kennung)
            try:
                weiter = self._vor_dem_schliessen_klaeren(
                    namen, self.alle_speichern
                )
            finally:
                if namen:
                    abmeldegrund.grund_entfernen(kennung)
            manager.release()
            if weiter:
                self._sicherung_entfernen()
            else:
                manager.cancel()
            return
        self._ohne_rueckfrage_speichern()
        self._sicherung_aufraeumen()
        if self.datenbank_panel.transaktion_offen:
            self.datenbank_panel.transaktion_zuruecknehmen()

    def _ohne_rueckfrage_speichern(self) -> None:
        """Speichert jede geänderte Datei, ohne ein Fenster zu zeigen.
        Eine Datei, die sich nicht schreiben lässt, bleibt als geändert
        markiert; eine Meldung dazu könnte beim Sitzungsende niemand
        mehr lesen."""
        for editor in self._ungespeicherte_editoren():
            pfad = Path(editor.property(_PFAD_EIGENSCHAFT))
            try:
                atomar_schreiben(pfad, editor.toPlainText(), encoding="utf-8")
            except OSError:
                continue
            editor.document().setModified(False)
            _stand_merken(editor)
        for fenster in self._ungespeicherte_diagramme():
            try:
                fenster.diagramm.speichern()
            except OSError:
                continue
            fenster._geaendert = False

    # -- Sicherung ungespeicherter Änderungen (Punkt 344) ---------------

    def _sicherung_pfad(self) -> Path | None:
        if self.projekt is None:
            return None
        return sicherung.pfad_fuer(self.projekt.ordner, self.projekt.name)

    def _sicherung_eintraege(self) -> list[sicherung.Eintrag]:
        """Jeder ungespeicherte Editor und jedes geänderte Diagramm im
        Ordner des offenen Projekts, in der Reihenfolge der Reiter.

        Als Stand zählt bei einem Editor der, in dem er seine Datei
        zuletzt gelesen oder geschrieben hat: auf ihm beruht der Text.
        Ein Diagrammfenster merkt sich keinen; dort gilt der Stand der
        Datei beim Sichern."""
        if self.projekt is None:
            return []
        ordner = self.projekt.ordner.resolve()
        eintraege = []

        def relativ(pfad: Path) -> str | None:
            try:
                return Path(pfad).resolve().relative_to(ordner).as_posix()
            except ValueError:
                return None

        for editor in self._ungespeicherte_editoren():
            pfad = Path(editor.property(_PFAD_EIGENSCHAFT))
            name = relativ(pfad)
            if name is None:
                continue
            stand = editor.property(dateistand.EIGENSCHAFT) or ""
            eintraege.append(sicherung.Eintrag(
                name, "text", editor.toPlainText(),
                stand or dateistand.kennung(pfad),
            ))
        for fenster in self._ungespeicherte_diagramme():
            pfad = fenster.diagramm.pfad
            name = relativ(pfad)
            if name is None:
                continue
            text = json.dumps(
                fenster.diagramm.daten, indent=2, ensure_ascii=False
            ) + "\n"
            eintraege.append(sicherung.Eintrag(
                name, "diagram", text, dateistand.kennung(pfad)
            ))
        return eintraege

    def _sicherung_schreiben(self) -> bool:
        """Schreibt die Sicherung des offenen Projekts oder entfernt
        sie, wenn nichts mehr ungespeichert ist. `False`, wenn sie sich
        nicht schreiben ließ; eine Meldung zeigt diese Methode nie, sie
        läuft auch beim Abmelden.

        Geschrieben wird nur der Anteil dieses Fensters; was andere
        Fenster gesichert haben, bleibt stehen (Punkte 400 und 406)."""
        pfad = self._sicherung_pfad()
        if pfad is None:
            return True
        eintraege = self._sicherung_eintraege()
        if not eintraege:
            self._sicherung_entfernen()
            return True
        try:
            sicherung.anteil_ersetzen(
                pfad, self._sicherung_herkunft, eintraege
            )
        except OSError:
            return False
        self._sicherung_eigen = True
        return True

    def _sicherung_entfernen(self) -> None:
        """Entfernt den Anteil dieses Fensters aus der Sicherung des
        offenen Projekts. Die Anteile anderer Natter-Fenster, in denen
        das Projekt ebenfalls offen ist oder war, bleiben stehen."""
        pfad = self._sicherung_pfad()
        if pfad is None or not self._sicherung_eigen:
            return
        try:
            sicherung.anteil_ersetzen(pfad, self._sicherung_herkunft, [])
        except OSError:
            # Der Anteil bleibt stehen und wird beim nächsten Öffnen
            # angeboten; ein Fenster deswegen hülfe niemandem.
            pass
        self._sicherung_eigen = False

    def _sicherung_aufraeumen(self) -> None:
        """Nach dem Speichern oder Verwerfen: ist nichts mehr
        ungespeichert, verschwindet die Sicherung, sonst hält sie nur
        noch den Rest. Ohne eigene Sicherung geschieht nichts."""
        if self._sicherung_eigen:
            self._sicherung_schreiben()

    def _sicherung_uhr_schlaegt(self) -> None:
        if not self._sicherung_schreiben():
            self.statusBar().showMessage(
                "Die Sicherung ungespeicherter Änderungen ließ sich "
                "nicht in den Projektordner schreiben.",
                10000,
            )

    def _sicherung_anbieten(self) -> None:
        """Bietet beim Öffnen des Projekts eine vorhandene Sicherung
        an. Eine Datei, deren gesicherter Inhalt ohnehin auf der Platte
        steht, fehlt in der Frage; bleibt keine übrig, verschwindet die
        Sicherung ohne Frage.

        Angeboten werden nur die Anteile, deren Fenster nicht mehr
        läuft (`sicherung.laeuft`). Die übrigen gehören zu einem
        Natter, in dem das Projekt noch offen ist, und bleiben
        unberührt. Nennen zwei Anteile dieselbe Datei, gilt der
        jüngere. Nach der Antwort verschwinden die angebotenen Anteile;
        was wiederhergestellt wurde, steht dann im Anteil dieses
        Fensters."""
        pfad = self._sicherung_pfad()
        if pfad is None or not pfad.is_file():
            return
        try:
            gesichert = sicherung.lesen(pfad)
        except (OSError, ValueError, schema_fehler()) as fehler:
            self._sicherung_unlesbar_melden(pfad, fehler_beschreiben(fehler))
            return
        ordner = self.projekt.ordner
        angeboten = sorted(
            (
                anteil for anteil in gesichert.anteile
                if not sicherung.laeuft(anteil.herkunft, ordner)
            ),
            key=lambda anteil: anteil.zeit.timestamp(),
        )
        if not angeboten:
            return
        weg = [anteil.herkunft for anteil in angeboten]
        je_pfad = {
            eintrag.pfad: eintrag
            for anteil in angeboten for eintrag in anteil.eintraege
        }
        offen = []
        for eintrag in je_pfad.values():
            ziel = ordner / eintrag.pfad
            try:
                auf_der_platte = ziel.read_text(encoding="utf-8-sig")
            except (OSError, UnicodeDecodeError):
                # Eine inzwischen gelöschte Datei öffnet kein Editor
                # mehr; ihr Text lässt sich nicht als Änderung
                # zurückgeben.
                continue
            if auf_der_platte == eintrag.text:
                continue
            seither = bool(eintrag.stand) and dateistand.von_aussen_geaendert(
                eintrag.stand, ziel
            )
            offen.append((eintrag, ziel, seither))
        if not offen:
            sicherung.anteile_entfernen(pfad, weg)
            return
        text = sicherung.frage_text(
            self.projekt.name, angeboten[-1].zeit,
            [(e.pfad, seither) for e, _ziel, seither in offen],
        )
        if not self._sicherung_wiederherstellen_fragen(text):
            sicherung.anteile_entfernen(pfad, weg)
            self.statusBar().showMessage("Die Sicherung wurde verworfen.")
            return
        for eintrag, ziel, _seither in offen:
            self._gesichert_oeffnen(eintrag, ziel)
        # Der wiederhergestellte Text kommt in den Anteil dieses
        # Fensters, bevor die angebotenen Anteile gehen; er folgt ab
        # jetzt den Editoren. Lässt er sich nicht schreiben, bleiben
        # die alten Anteile stehen.
        if self._sicherung_schreiben():
            sicherung.anteile_entfernen(pfad, weg)
        self.statusBar().showMessage(
            "Die gesicherten Änderungen sind wiederhergestellt und noch "
            "nicht gespeichert."
        )

    def _gesichert_oeffnen(
        self, eintrag: sicherung.Eintrag, ziel: Path
    ) -> None:
        """Öffnet `ziel` und setzt den gesicherten Inhalt als
        ungespeicherte Änderung ein.

        Beim Editor ist das ein einziger Bearbeitungsschritt: Strg+Z
        holt den Stand der Datei zurück, und danach gilt der Editor
        wieder als unverändert. Der Stand aus der Sicherung wird zum
        Stand des Editors; wurde die Datei seither geändert, fragt
        „Speichern“ vorher nach (Punkt 286)."""
        if eintrag.art == "diagram":
            try:
                diagramm = Diagramm.aus_daten(ziel, json.loads(eintrag.text))
            except (ValueError, schema_fehler()):
                return
            fenster = self.diagramm_oeffnen(ziel, diagramm)
            fenster._geaendert = True
            fenster._titel_setzen()
            return
        editor = self.datei_oeffnen(ziel)
        if editor is None:
            return
        cursor = QTextCursor(editor.document())
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.beginEditBlock()
        cursor.insertText(eintrag.text)
        cursor.endEditBlock()
        cursor.setPosition(0)
        editor.setTextCursor(cursor)
        if eintrag.stand:
            editor.setProperty(dateistand.EIGENSCHAFT, eintrag.stand)

    def _sicherung_wiederherstellen_fragen(self, text: str) -> bool:
        """Fragt, ob die Sicherung wiederhergestellt werden soll.
        Eigene Methode, damit Tests die Antwort vorgeben können.
        Vorgewählt ist „Wiederherstellen“, und auch Escape und das
        Schließen der Frage verlieren nichts."""
        frage = QMessageBox(self)
        frage.setIcon(QMessageBox.Icon.Question)
        frage.setWindowTitle("Ungespeicherte Änderungen gefunden")
        frage.setText(text)
        wiederherstellen = frage.addButton(
            "Wiederherstellen", QMessageBox.ButtonRole.AcceptRole
        )
        frage.addButton("Verwerfen", QMessageBox.ButtonRole.DestructiveRole)
        frage.setDefaultButton(wiederherstellen)
        frage.setEscapeButton(wiederherstellen)
        frage.exec()
        return frage.clickedButton() is wiederherstellen

    def _sicherung_unlesbar_melden(self, pfad: Path, grund: str) -> None:
        """Eigene Methode, damit Tests den Hinweis abfangen können."""
        QMessageBox.warning(
            self,
            "Sicherung nicht lesbar",
            f"Die Sicherung ungespeicherter Änderungen „{pfad.name}“ "
            f"lässt sich nicht lesen. {grund}\n\nDie Datei bleibt "
            "unverändert im Projektordner liegen, bis Natter wieder "
            "etwas sichert.",
        )

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
            self._startaktionen_pruefen()
            beendet += 1
        if self.laufender_prozess is not None and self.laufender_prozess.poll() is None:
            # Samt allem, was das Programm selbst gestartet hat
            # (Punkt 278); `kill()` träfe unter Windows nur den einen
            # Prozess.
            prozessbaum_beenden(self.laufender_prozess)
            beendet += 1
        elif self._programm_auftrag_beenden():
            beendet += 1
        self._programm_auftrag_beenden()
        self.laufender_prozess = None
        self._ausgabe_leser_beenden()
        # Sonst schlägt die Uhr weiter auf ein Fenster, das es gleich
        # nicht mehr gibt.
        self._laufzeit_uhr.stop()
        self._ladeanzeige_beenden()
        return beendet

    # -- Hilfe (Abschnitt 7.2) -------------------------------------------------

    def _komponenten_referenz_aktion(self) -> bool:
        """„Hilfe → Komponenten-Referenz“.

        Früher an Windows weitergereicht (`open_url`). Für `.md` ist
        dort meist gar nichts eingetragen: im besten Fall ging der
        Editor auf, im Normalfall passierte nichts. Jetzt dieselbe
        Ansicht wie bei „Erste Schritte“.
        """
        return self._hilfedatei_zeigen(
            "komponenten.md", "Komponenten-Referenz", True
        )

    def _hilfe_zur_auswahl_aktion(self) -> None:
        """F1 (Punkt 438): die Komponenten-Referenz an der Stelle der
        Komponente, die im Designer gewählt ist oder deren Klasse im
        Editor unter dem Cursor steht. Sonst das Handbuch."""
        klassen = self._klassen_zur_auswahl()
        if not klassen:
            # Nicht das Handbuch von oben: dort steht zuerst, wie die
            # Systembetreuung Natter einrichtet (Punkt 461).
            if self._handbuch_aktion():
                ansicht = self.editor_tabs.currentWidget()
                if isinstance(ansicht, HilfeAnsicht):
                    ansicht.zu_abschnitt("3. Was Natter kann")
            return
        if not self._komponenten_referenz_aktion():
            return
        ansicht = self.editor_tabs.currentWidget()
        if isinstance(ansicht, HilfeAnsicht):
            for name in klassen:
                if ansicht.zu_abschnitt(name):
                    return

    def _klassen_zur_auswahl(self) -> list[str]:
        """Die Klassennamen, unter denen F1 in der Referenz sucht: bei
        einer Komponente im Designer ihre Klasse und deren Oberklassen
        (ein eigenes Formular findet so „Form“), im Editor der Name
        unter dem Cursor, wenn `pcl` eine Klasse dieses Namens hat."""
        import pcl

        canvas = self._aktueller_canvas
        if canvas is not None and canvas.ausgewaehlte_komponente is not None:
            return [
                klasse.__name__
                for klasse in type(canvas.ausgewaehlte_komponente).__mro__
            ]
        editor = self._aktueller_editor()
        if editor is None:
            return []
        cursor = editor.textCursor()
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        wort = cursor.selectedText()
        if wort and isinstance(getattr(pcl, wort, None), type):
            return [wort]
        # `self.b_ok.caption`: Klassennamen stehen kaum je in der Unit,
        # wohl aber Komponentennamen und ihre Eigenschaften. F1 auf
        # `b_ok` oder `caption` führt zur Klasse der Komponente.
        zeile = cursor.block().text()
        spalte = cursor.selectionStart() - cursor.block().position()
        for treffer in re.finditer(r"self\.(\w+)(?:\.(\w+))?", zeile):
            if treffer.start(1) <= spalte <= treffer.end(2 if treffer.group(2) else 1):
                typ = self._komponententyp(treffer.group(1))
                if typ is not None:
                    return [typ]
        return []

    def _komponententyp(self, name: str) -> str | None:
        """Der Typ der Komponente `name` aus den Formularen des
        Projekts, etwa „Button“ für `b_ok`."""
        if self.projekt is None:
            return None

        def suchen(knoten: dict) -> str | None:
            for kind in knoten.get("children") or []:
                if not isinstance(kind, dict):
                    continue
                if kind.get("name") == name:
                    return kind.get("type")
                gefunden = suchen(kind)
                if gefunden:
                    return gefunden
            return None

        for formular in self.projekt.formulare():
            try:
                daten = json.loads(formular.read_text(encoding="utf-8-sig"))
            except (OSError, ValueError):
                continue
            if isinstance(daten, dict):
                typ = suchen(daten)
                if typ:
                    return typ
        return None

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
        canvas.aenderung_beobachten(
            lambda: self._komponentenbaum_auffrischen(canvas)
        )
        canvas.aenderung_beobachten(
            lambda: self._designer_titel_auffrischen(canvas)
        )
        canvas.bild_beobachten(self._designer_bild_abgelegt)
        canvas.methode_beobachten(self._zur_methode_springen)
        self._offene_canvases.append(canvas)
        self._pfad_zu_formular[schluessel] = formular
        self._widget_zu_canvas[formular._qwidget] = canvas
        self._formular_docks_anpassen()

        index = self.editor_tabs.addTab(
            self._designer_rollbereich(formular._qwidget), f"{pfad.stem} (Designer)"
        )
        self.editor_tabs.setCurrentIndex(index)
        self.objektinspektor.formular_anzeigen(formular, canvas)
        return formular

    def diagramm_oeffnen(
        self, pfad: Path, diagramm: Diagramm | None = None
    ) -> DiagrammFenster:
        """Öffnet eine `.pdiag`-Datei im Diagramm-Editor (Abschnitt 13.1):
        eigenes Fenster mit eigenem Taskleisten-Eintrag, kein Tab.
        Bereits offene Diagramme werden nach vorne geholt.

        Hat sich die Datei inzwischen geändert und das offene Fenster
        keine ungespeicherte Arbeit, wird sie neu geladen (Punkt 52).
        Bis 0.3.5 zeigte das Fenster weiter den alten Stand, und
        „Quelltext → Erzeugen …“ arbeitete damit. Mit ungespeicherten
        Änderungen bleibt das Fenster, wie es ist; die Arbeit darin
        wiegt mehr als die Datei.

        Ein neues Fenster zeigt `diagramm` statt der Datei, wenn es
        angegeben ist; so kommt der Inhalt aus der Sicherung
        ungespeicherter Änderungen zurück (Punkt 344).
        """
        pfad = Path(pfad)
        schluessel = str(pfad)
        vorhanden = self._offene_diagramme.get(schluessel)
        if vorhanden is not None:
            neu_geladen = None
            if not vorhanden._geaendert:
                try:
                    neu_geladen = Diagramm.laden(pfad)
                except (OSError, ValueError, schema_fehler()):
                    # Eine gerade kaputte Datei ersetzt kein
                    # funktionierendes Fenster.
                    neu_geladen = None
            if neu_geladen is None or neu_geladen.daten == vorhanden.diagramm.daten:
                vorhanden.show()
                vorhanden.raise_()
                vorhanden.activateWindow()
                return vorhanden
            del self._offene_diagramme[schluessel]
            vorhanden.close()
            vorhanden.deleteLater()
            fenster = DiagrammFenster(neu_geladen)
        else:
            fenster = DiagrammFenster(diagramm or Diagramm.laden(pfad))
        # Eine aus dem Diagramm erzeugte Klasse soll dort auftauchen,
        # wo der Schüler sie sucht: links im Explorer und offen im
        # Editor. Der Diagramm-Editor kennt das Hauptfenster nicht, er
        # meldet nur, was er geschrieben hat.
        fenster.datei_geschrieben.connect(self._erzeugte_datei_uebernehmen)
        fenster.handbuch_zeigen = self._handbuch_bei_den_diagrammen
        # Nur austragen, wenn noch dieses Fenster eingetragen ist. Nach
        # dem Neuladen steht unter demselben Pfad schon das neue.
        fenster.destroyed.connect(
            lambda *_, alt=fenster: self._offene_diagramme.get(schluessel) is alt
            and self._offene_diagramme.pop(schluessel)
        )
        self._offene_diagramme[schluessel] = fenster
        fenster.show()
        return fenster

    def _handbuch_bei_den_diagrammen(self) -> None:
        """F1 im Diagramm-Editor (Punkt 463): das Handbuch beim
        Abschnitt „Modellieren“, mit dem Hauptfenster nach vorn."""
        if not self._handbuch_aktion():
            return
        ansicht = self.editor_tabs.currentWidget()
        if isinstance(ansicht, HilfeAnsicht):
            ansicht.zu_abschnitt("3.4 Modellieren")
        self.raise_()
        self.activateWindow()

    def _zur_methode_springen(
        self, unit: Path, klassenname: str, methode: str, parameter: tuple
    ) -> None:
        """Doppelklick auf eine Komponente: Unit öffnen, Cursor in die
        Methode (Punkt 37). Bis 0.3.3 legte Natter die Methode nur in
        der Datei an; die Unit blieb zu, obwohl Handbuch und
        Tastenübersicht „anlegen und hinspringen“ versprechen.

        Ist die Unit schon offen, fehlt dem Editor die gerade in die
        Datei geschriebene Methode. Ohne eigene Änderungen wird er neu
        geladen; mit ungespeicherten Änderungen wird die Methode
        genauso in seinen Text eingefügt - sonst ginge sie beim nächsten
        Speichern verloren.

        Eingefügt wird in beiden Fällen als ein Bearbeitungsschritt des
        Editors. `setPlainText` leerte den Rückgängig-Verlauf; danach
        ließ sich keine der vorherigen Änderungen mehr zurücknehmen
        (Punkt 248).
        """
        from libcst import ParserSyntaxError

        from ide.codegen.ereignis import handler_methode_einfuegen
        from ide.designer.canvas import editortext_ersetzen

        editor = None
        for index in range(self.editor_tabs.count()):
            kandidat = self.editor_tabs.widget(index)
            if isinstance(kandidat, QuelltextEditor) and (
                kandidat.property(_PFAD_EIGENSCHAFT) == str(unit)
            ):
                editor = kandidat
        if editor is not None:
            text = editor.toPlainText()
            if not re.search(rf"^\s*def {re.escape(methode)}\(", text, re.M):
                neu: str | None
                if editor.document().isModified():
                    # Der Designer prüft den Editortext vorher; kommt
                    # trotzdem ein Syntaxfehler an, bleibt der Editor,
                    # wie er ist, statt in der allgemeinen
                    # Fehlermeldung zu enden.
                    try:
                        neu = handler_methode_einfuegen(
                            text, klassenname, methode, parameter
                        )
                    except ParserSyntaxError:
                        neu = None
                else:
                    neu = unit.read_text(encoding="utf-8-sig")
                # Behält den Stand von „geändert“ bei: eine ungespeicherte
                # Unit bleibt ungespeichert, eine gespeicherte stimmt
                # danach wieder mit der Datei überein.
                if neu is not None:
                    editortext_ersetzen(editor, neu)
        editor = self.datei_oeffnen(unit)
        if editor is None:
            return
        text = editor.toPlainText()
        if not re.search(rf"^\s*def {re.escape(methode)}\(", text, re.M):
            # Die Verknüpfung steht in der .pfm, die Methode fehlt aber
            # auch in der Datei, etwa nach Strg+Z im Editor und
            # anschließendem Speichern. Ein Doppelklick auf die
            # Komponente legt sie dann neu an, wie es die Meldung vor
            # dem Start verspricht (Punkt 290). Bis dahin tat er nichts.
            # Eine Unit mit Syntaxfehler lässt sich nicht umschreiben;
            # die Prüfung vor dem Start nennt ihn.
            try:
                neu = handler_methode_einfuegen(
                    text, klassenname, methode, parameter
                )
            except ParserSyntaxError:
                neu = None
            if neu is not None:
                editortext_ersetzen(editor, neu)
                editor.document().setModified(True)
        zeilen = editor.toPlainText().split("\n")
        treffer = next(
            (i for i, z in enumerate(zeilen) if re.match(rf"\s*def {re.escape(methode)}\(", z)),
            None,
        )
        if treffer is None:
            return
        # Erste Zeile des Rumpfs: hinter die Einrückung, dort wird
        # geschrieben; ein vorhandenes `pass` wird markiert, damit das
        # erste Tippen es ersetzt.
        ziel = min(treffer + 1, len(zeilen) - 1)
        while ziel < len(zeilen) - 1 and zeilen[ziel].strip().startswith("#"):
            ziel += 1
        # Über den Textblock und nicht mit „Zeile nach unten“: das zählt
        # bei eingeschaltetem Zeilenumbruch sichtbare Zeilen, und in der
        # Projektvorlage mit ihren langen Kommentaren landete der
        # Cursor in 0.3.4 mitten in einem Kommentar.
        einrueckung = len(zeilen[ziel]) - len(zeilen[ziel].lstrip())
        cursor = editor.textCursor()
        cursor.setPosition(
            editor.document().findBlockByNumber(ziel).position() + einrueckung
        )
        if zeilen[ziel].strip() == "pass":
            cursor.movePosition(cursor.MoveOperation.EndOfBlock, cursor.MoveMode.KeepAnchor)
        editor.setTextCursor(cursor)
        editor.ensureCursorVisible()
        editor.setFocus()
        self.statusBar().showMessage(f"Methode {methode} in {unit.name}.")

    def _erzeugte_datei_uebernehmen(self, pfad: Path) -> None:
        """Holt eine vom Diagramm-Editor geschriebene Datei herein.

        Liegt sie im offenen Projekt, gehört sie in den Explorer - er
        liest seine Liste bei jedem Aufruf frisch von der Platte.
        Liegt sie woanders, bekommt sie nur einen Reiter: der Explorer
        zeigt das Projekt und nicht irgendeinen Ordner.
        """
        pfad = Path(pfad)
        if self.projekt is not None and pfad.parent == self.projekt.ordner:
            self.explorer.projekt_anzeigen(self.projekt)
        self.datei_oeffnen(pfad)
        self.statusBar().showMessage(f"{pfad.name} erzeugt und geöffnet.")

    def _neues_diagramm_aktion(self) -> None:
        """„Datei → Neues Diagramm …“ (Abschnitt 13.1): legt eine
        `.pdiag` im Ordner `diagramme/` des offenen Projekts an und
        öffnet sie im Diagramm-Editor."""
        if self.projekt is None:
            self.statusBar().showMessage(self._kein_projekt_text())
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
        name = name.strip()
        if name.lower().endswith(".pdiag"):
            name = name[: -len(".pdiag")].strip()
        if not bestaetigt or not name:
            return
        # Dieselbe Prüfung wie beim Umbenennen (Punkt 232). Ohne sie
        # legte „..\..\ausserhalb“ die Datei außerhalb des Projekts an,
        # und ein Doppelpunkt ergab einen `OSError` aus dem Menü heraus.
        fehler = _dateiname_fehler(name)
        if fehler is not None:
            self._umbenennen_ablehnen(fehler, "Neues Diagramm")
            return

        pfad = self.projekt.diagramm_ordner / f"{name}.pdiag"
        if pfad.exists():
            self.statusBar().showMessage(
                f"{pfad.name} gibt es schon - bitte einen anderen Namen wählen."
            )
            return

        try:
            pfad.parent.mkdir(parents=True, exist_ok=True)
            diagramm_erzeugen(typ, pfad, name)
        except OSError as fehler_os:
            self.statusBar().showMessage(
                f"Das Diagramm ließ sich nicht anlegen: {fehler_os}"
            )
            return
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
            json_datei_lesen(pfm_pfad), pfm_pfad.name
        )
        if not ziel.exists() or ziel.read_text(encoding="utf-8") != quelltext:
            atomar_schreiben(ziel, quelltext, encoding="utf-8")

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
                # Über `oeffnen`, damit eine beschädigte `.pfm` eine
                # Meldung ergibt statt einer Ausnahme (Punkt 226).
                self.oeffnen(formular)
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
        self._cursor_anzeige_aktualisieren()

    def _cursor_anzeige_aktualisieren(self) -> None:
        """„Zeile 17, Spalte 5“ rechts in der Statusleiste (Punkt 89).
        Meldungen nennen Zeilennummern; wo der Cursor steht, war bis
        0.3.5 nirgends zu sehen. Ohne Editor vorn bleibt das Feld leer."""
        anzeige = getattr(self, "cursor_anzeige", None)
        if anzeige is None:
            anzeige = QLabel()
            anzeige.setContentsMargins(8, 0, 8, 0)
            self.statusBar().addPermanentWidget(anzeige)
            self.cursor_anzeige = anzeige
        editor = self._aktueller_editor()
        if editor is None:
            anzeige.setText("")
            return
        cursor = editor.textCursor()
        anzeige.setText(
            f"Zeile {cursor.blockNumber() + 1}, Spalte {cursor.positionInBlock() + 1}"
        )

    def _tab_schliessen(self, index: int) -> None:
        """„×“ auf einem Editor-/Designer-Tab (Abschnitt 7.9): bislang war
        `tabCloseRequested` gar nicht verbunden – der Knopf tat nichts.
        Fragt bei ungespeicherten Textänderungen nach. Designer-Tabs
        schreiben laufend automatisch in die `.pfm` zurück; gefragt
        wird dort nur, wenn das zuletzt gescheitert ist (Punkt 235)."""
        widget = self._tab_inhalt(self.editor_tabs.widget(index))
        if widget is None:
            return
        designer = self._widget_zu_canvas.get(widget)
        if designer is not None:
            designer.jetzt_schreiben()
        if (
            isinstance(widget, QPlainTextEdit) and widget.document().isModified()
        ) or (designer is not None and designer.ungespeichert):
            antwort = self._reiter_schliessen_fragen()
            if antwort == QMessageBox.StandardButton.Cancel:
                return
            # Scheitert das Speichern, bleibt der Reiter offen (Punkt 112):
            # bis 0.3.5 ging er trotz der Warnung zu, und der Text war weg.
            if antwort == QMessageBox.StandardButton.Save:
                self.editor_tabs.setCurrentIndex(index)
                if not self._aktuelle_datei_speichern():
                    return

        canvas = self._widget_zu_canvas.pop(widget, None)
        if canvas is not None:
            if canvas in self._offene_canvases:
                self._offene_canvases.remove(canvas)
            for schluessel, formular in list(self._pfad_zu_formular.items()):
                if formular._qwidget is widget:
                    del self._pfad_zu_formular[schluessel]
            if self._aktueller_canvas is canvas:
                self._aktueller_canvas = None
            # Ein geschlossener Designer schreibt nichts mehr. Sonst
            # legte ein verspätetes Ereignis `.pfm` und `_design.py`
            # einer gerade gelöschten Unit wieder an (Punkt 139).
            canvas.pfm_pfad = None
            # Der Filter für Escape hängt an der ganzen Anwendung und
            # überlebte sonst den Designer.
            canvas.platzierungsmodus_setzen(None)
            if self.objektinspektor.formular is canvas.formular:
                self.objektinspektor.leeren()
            self._formular_docks_anpassen()

        if isinstance(widget, QuelltextEditor):
            self._haltepunkte_merken(widget)
        seite = self.editor_tabs.widget(index)
        self.editor_tabs.removeTab(index)
        self._reiter_freigeben(seite, widget)
        # Nach „Verwerfen“ ist der Text des Reiters auch in der
        # Sicherung nicht mehr gefragt (Punkt 344).
        self._sicherung_aufraeumen()

    def _haltepunkte_merken(self, editor: QuelltextEditor) -> None:
        """Hebt die Haltepunkte eines Editors auf, dessen Reiter gleich
        zugeht (Punkt 419). Bis 0.4.2 standen sie nur im Editor, und
        mit dem Reiter waren sie fort: F5 hielt nicht mehr an, und die
        wieder geöffnete Datei hatte keinen Haltepunkt.

        Gemerkt wird der Stand beim Schließen, mit den Zeilen, zu denen
        die Haltepunkte beim Bearbeiten gewandert sind."""
        pfad = editor.property(_PFAD_EIGENSCHAFT)
        if not pfad:
            return
        if editor.breakpoints:
            self._gemerkte_haltepunkte[str(pfad)] = (
                set(editor.breakpoints), dict(editor.bedingungen)
            )
        else:
            self._gemerkte_haltepunkte.pop(str(pfad), None)

    def _gemerkte_haltepunkte_nehmen(
        self, pfad: Path
    ) -> tuple[set[int], dict[int, str]] | None:
        """Nimmt die gemerkten Haltepunkte von `pfad` heraus. Ein Pfad
        aus den Einstellungen kann anders geschrieben sein als der, mit
        dem die Datei jetzt geöffnet wird, etwa mit einem Laufwerk statt
        des Netzpfads; verglichen wird deshalb auch aufgelöst."""
        gemerkt = self._gemerkte_haltepunkte.pop(str(pfad), None)
        if gemerkt is not None:
            return gemerkt
        ziel = einheitlicher_pfad(pfad)
        for schluessel in list(self._gemerkte_haltepunkte):
            if einheitlicher_pfad(schluessel) == ziel:
                return self._gemerkte_haltepunkte.pop(schluessel)
        return None

    def _haltepunkte_ablegen(self) -> None:
        """Schreibt die Haltepunkte des offenen Projekts in die
        Einstellungen (Punkt 419): die geschlossener Reiter und die der
        offenen, die dem gemerkten Stand derselben Datei vorgehen.

        Bis 0.4.2 gingen sie mit dem Projekt verloren. Sie stehen je
        Benutzer in den Einstellungen und nicht im Projektordner, weil
        der zwischen Lehrkraft und Klasse kopiert wird."""
        if self.projekt is None or self._projekt_datei is None:
            return
        stand = dict(self._gemerkte_haltepunkte)
        for index in range(self.editor_tabs.count()):
            editor = self.editor_tabs.widget(index)
            if not isinstance(editor, QuelltextEditor):
                continue
            pfad = editor.property(_PFAD_EIGENSCHAFT)
            if pfad:
                stand[str(pfad)] = (
                    set(editor.breakpoints), dict(editor.bedingungen)
                )
        try:
            haltepunkte_speichern(
                self._design_einstellungen,
                self._projekt_datei,
                self.projekt.ordner,
                stand,
            )
        except OSError:
            # Ein nicht mehr erreichbarer Pfad soll weder das Schließen
            # noch das Beenden aufhalten.
            pass

    def _reiter_freigeben(self, seite: QWidget, inhalt: QWidget) -> None:
        """Gibt die Seite eines geschlossenen Reiters frei (Punkt 376).

        `removeTab` nimmt die Seite nur aus der Leiste; sie blieb bis
        0.3.x als verborgenes Kind des Hauptfensters bestehen, mit
        allem, was sie hielt. Eine CSV-Ansicht beobachtete ihre Datei
        weiter und las sie bei jeder Änderung neu ein, und jede
        geschlossene Tabelle belegte weiter ihren Speicher.

        Eine Ansicht, die vorher etwas anhalten muss (Uhren,
        Dateibeobachter, einen Ladevorgang im Nebenfaden), hat dafür
        eine Methode `beim_schliessen`. Der Suchdialog kann noch auf
        den geschlossenen Editor zeigen; er wechselt zum Editor, der
        jetzt vorn ist, oder geht zu."""
        beim_schliessen = getattr(inhalt, "beim_schliessen", None)
        if callable(beim_schliessen):
            beim_schliessen()
        dialog = getattr(self, "_suchen_dialog", None)
        if dialog is not None and dialog._editor is inhalt:
            vorn = self._aktueller_editor()
            if vorn is not None:
                dialog.editor_setzen(vorn)
            else:
                dialog.hide()
        seite.deleteLater()

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
        self.objektinspektor.baum.komponente_markieren(komponente)

    def _komponentenbaum_auffrischen(self, canvas: DesignerCanvas) -> None:
        """Nach jeder Änderung im Designer: der Komponentenbaum zeigt,
        was jetzt auf dem Formular liegt. Nur, wenn der Objektinspektor
        gerade dieses Formular zeigt."""
        if self.objektinspektor.formular is canvas.formular:
            self.objektinspektor.baum.auffrischen(
                canvas.ausgewaehlte_komponente
            )

    def _designer_bild_abgelegt(self, relativer_pfad: str) -> None:
        """Nach Drag & Drop einer Bilddatei in den Designer (Abschnitt
        11.4): nennt den Pfad im Projekt. Das Bild steht als `picture`
        in der `.pfm` und erscheint im gestarteten Programm von selbst
        (Punkt 57)."""
        self.statusBar().showMessage(
            f"Bild nach {relativer_pfad} übernommen und mit dem Formular gespeichert."
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
            self._design_pruefen(canvas, automatisch=True)

    def _design_pruefen(
        self, canvas: DesignerCanvas, *, automatisch: bool = False
    ) -> None:
        pfm = pfm_aus_formular(canvas.formular)
        abgeschaltet = set(self._design_pruefer_abgeschaltete_regeln)
        if automatisch:
            abgeschaltet |= _NACH_JEDER_AENDERUNG_STILL
        befunde = pruefen(pfm, abgeschaltete_regeln=abgeschaltet)
        # Nur die Einträge der letzten Design-Prüfung ersetzen. Bis
        # Punkt 292 leerte jedes Verschieben eines Knopfs das ganze
        # Panel, auch die Funde der Prüfung vor dem Start.
        for zeile in reversed(range(self.meldungen_liste.count())):
            if self.meldungen_liste.item(zeile).data(_DESIGN_ROLLE):
                self.meldungen_liste.takeItem(zeile)
        pruefung = pruefungsmodus_laeuft()
        for befund in befunde:
            eintrag = QListWidgetItem(
                f"[{befund.kategorie}] {befund.anzeige(pruefung)}"
            )
            eintrag.setData(_DESIGN_ROLLE, True)
            if befund.komponente is not None:
                eintrag.setData(_MELDUNG_ROLLE, (canvas, befund.komponente))
            self.meldungen_liste.addItem(eintrag)
        if befunde:
            self.panels.setCurrentWidget(self.meldungen_liste)
        # Die Prüfung nach jeder Änderung meldet sich in der
        # Statusleiste nur mit Funden oder wenn sich deren Zahl
        # geändert hat. Bis 0.4.2 stand nach jedem Verschieben
        # „0 Funde“ dort, samt einem Satz über Einträge, die es nicht
        # gab, und verdrängte die Meldung davor (Punkt 434).
        vorher = canvas.property(_DESIGN_FUNDE_EIGENSCHAFT) or 0
        canvas.setProperty(_DESIGN_FUNDE_EIGENSCHAFT, len(befunde))
        if befunde:
            self.statusBar().showMessage(
                f"Design-Prüfung: {len(befunde)} "
                f"{'Fund' if len(befunde) == 1 else 'Funde'}. Jeder "
                f"Eintrag unten im Panel „Meldungen“ sagt, was sich "
                f"ändern lässt; ein Klick markiert die Komponente."
            )
        elif not automatisch or vorher:
            self.statusBar().showMessage("Design-Prüfung: keine Funde.")

    def _bei_meldung_geklickt(self, eintrag: QListWidgetItem) -> None:
        """Klick auf eine Meldung.

        Ein Fund der Prüfung vor dem Start öffnet seine Datei und setzt
        den Cursor in die Fundzeile, auch wenn die Datei noch nicht
        offen war. Ein Design-Prüfer-Befund markiert die betroffene
        Komponente im Designer (Abschnitt 14)."""
        if eintrag.data(_WIEDER_FRAGEN_ROLLE):
            self._rueckfrage_wieder_zulassen(eintrag)
            return
        fund = eintrag.data(_FUND_ROLLE)
        if fund is not None:
            self._zu_fund_springen(*fund)
            return
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

    def _zu_fund_springen(self, pfad: str, zeile: int, spalte: int) -> None:
        """Öffnet die Datei eines Fundes und springt an seine Stelle.
        Ruff zählt die Spalte ab 1, der Editor ab 0."""
        datei = Path(pfad)
        if not datei.is_file():
            self.statusBar().showMessage(
                f"{datei.name} gibt es nicht mehr - die Prüfung vor dem "
                f"Start neu laufen lassen."
            )
            return
        self.sprung_merken()
        editor = self.datei_oeffnen(datei)
        if isinstance(editor, QuelltextEditor):
            editor.zu_zeile_springen(zeile, max(0, spalte - 1))
            editor.setFocus()

    def _umgebung_pruefen_aktion(self) -> None:
        """„Werkzeuge → Umgebung prüfen“ (Abschnitt 17.8): vollständige
        Prüfung aller Programmdateien gegen das signierte
        Prüfsummen-Manifest – im Unterschied zur schnellen Prüfung der
        Kerndateien bei jedem Start. Jede betroffene Datei erscheint
        einzeln im Panel „Meldungen“.

        Die Prüfung liest rund 30 000 Dateien (2,4 s) und läuft deshalb
        nebenher; bis 0.3.3 nahm das Fenster so lange keine Klicks an.
        Im Entwicklungsbaum gibt es nichts zu prüfen - dort bleibt es bei
        der sofortigen Meldung."""
        if programmordner() is None:
            self.statusBar().showMessage(
                "Keine Prüfung möglich: Natter läuft nicht aus einer gebauten Installation. "
                "Die Prüfung gilt nur für die ausgelieferte Natter.exe."
            )
            return
        if not self._hintergrund_frei("Umgebung prüfen"):
            return
        self.statusBar().showMessage("Umgebung wird geprüft …")
        self._hintergrund_starten(
            lambda _melden: installation_pruefen(vollstaendig=True),
            self._umgebung_geprueft,
            "Umgebung prüfen",
        )

    def _umgebung_geprueft(self, ergebnis) -> None:  # noqa: ANN001
        self._fortschritt_verbergen()
        if ergebnis is None:
            return
        hinweise = getattr(ergebnis, "hinweise", [])
        if ergebnis.in_ordnung and not hinweise:
            self.statusBar().showMessage("Umgebung geprüft: alle Programmdateien unverändert.")
            return

        self.meldungen_liste.clear()
        # Abweichende Bibliotheken sind nur ein Hinweis: `pip` darf
        # sie beim Nachinstallieren anheben (Punkt 230).
        for hinweis in hinweise:
            self.meldungen_liste.addItem(f"[Umgebung, Hinweis] {hinweis}")
        if ergebnis.in_ordnung:
            self.panels.setCurrentWidget(self.meldungen_liste)
            self.statusBar().showMessage(
                "Umgebung geprüft: Natters eigene Dateien sind unverändert; "
                "Hinweise zu mitgelieferten Bibliotheken unter „Meldungen“."
            )
            return
        if ergebnis.manifest_fehler:
            self.meldungen_liste.addItem(f"[Umgebung] {ergebnis.manifest_fehler}")
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
            self,
            "Formular importieren",
            self._dialog_startordner(),
            "Formulardateien (*.lfm)",
        )
        if not quelle:
            return
        self._dialog_ordner_merken(quelle)
        try:
            lfm_objekt = parse_lfm(Path(quelle).read_text(encoding="utf-8-sig"))
        except LfmParserError as fehler:
            self.statusBar().showMessage(
                f"Import fehlgeschlagen: {fehler}. Ist die gewählte Datei wirklich ein "
                f"Formular im .lfm-Format?"
            )
            return
        ergebnis = lfm_zu_pfm(lfm_objekt)
        # Namen aus der `.lfm` gehen in den Quelltext ein, den der
        # Designer ausführt. Eine Datei, in der statt eines Namens
        # eine Anweisung steht, wird abgelehnt, bevor etwas davon
        # geschrieben oder ausgeführt wird (Punkt 226).
        try:
            pfm_pruefen(ergebnis.pfm)
        except (PfmBeschaedigt, schema_fehler()) as fehler:
            self.statusBar().showMessage(
                f"Import fehlgeschlagen: „{Path(quelle).name}“ ist beschädigt. "
                f"{fehler_beschreiben(fehler)}"
            )
            return

        ziel, _ = QFileDialog.getSaveFileName(
            self,
            "Formular speichern unter",
            str(
                Path(self._dialog_startordner())
                / Path(quelle).with_suffix(".pfm").name
            ),
            filter="Natter-Formulare (*.pfm)",
        )
        if not ziel:
            return
        ziel_pfad = Path(ziel)
        # Die Bilder zuerst: sie stehen seit Punkt 57 als `picture` in der
        # `.pfm` und damit auch in der Designer-Vorschau. Bis dahin lud
        # eine Zeile im Code sie erst im gestarteten Programm.
        bild_pfade = self._import_bilder_schreiben(ergebnis, ziel_pfad)
        _bilder_in_pfm_eintragen(ergebnis.pfm, bild_pfade)
        if not self.datei_schreiben_gemeldet(
            ziel_pfad,
            json.dumps(ergebnis.pfm, indent=2, ensure_ascii=False) + "\n",
            folge="Das importierte Formular ist damit nicht angelegt worden.",
        ):
            return

        self._import_unit_schreiben(ergebnis, Path(quelle), ziel_pfad, {})
        # Formular und Unit sind jetzt Dateien im Projekt. Bis 0.3.3
        # erschienen sie im Projekt-Explorer erst nach erneutem Öffnen
        # des Projekts.
        if self.projekt is not None:
            self.explorer.projekt_anzeigen(self.projekt)

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
        atomar_schreiben(unit_pfad, quelltext, encoding="utf-8")

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
        fehlertext = f"Installation von {name} fehlgeschlagen"

        def arbeit(_melden: Callable[[int, str], None]) -> object:
            # Der Fehler kommt als Ergebnis zurück statt als Ausnahme:
            # so steht in der Statuszeile nur der deutsche Satz, und
            # die Ausgabe von `pip` folgt im Panel „Meldungen“
            # (Punkt 424).
            try:
                return paket_installieren(name)
            except PaketFehler as fehler:
                return fehler

        def fertig(ergebnis: object) -> None:
            if isinstance(ergebnis, PaketFehler):
                self._hintergrund_fehler(fehlertext, str(ergebnis))
                roh = ergebnis.rohausgabe.splitlines()
                if roh:
                    self.meldungen_liste.addItem("Ausgabe von pip:")
                    self.meldungen_liste.addItems(roh)
                return
            self.statusBar().showMessage(f"{name} installiert.")

        self._hintergrund_starten(arbeit, fertig, fehlertext)

    def _paketliste_exportieren_aktion(self) -> None:
        """„Pakete → Paketliste exportieren …“: `pip freeze` in eine
        `requirements.txt`."""
        pfad, _ = QFileDialog.getSaveFileName(
            self,
            "Paketliste exportieren",
            str(Path(self._dialog_startordner()) / "requirements.txt"),
            "Text (*.txt)",
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

    def _projektordner_oeffnen_aktion(self) -> None:
        """„Projekt → Projektordner öffnen“ im Windows-Explorer
        (Punkt 104)."""
        if self.projekt is None:
            self.statusBar().showMessage(self._kein_projekt_text())
            return
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.projekt.ordner)))

    def projekt_als_zip(self, ziel: Path) -> int | None:
        """Schreibt das Projekt als ZIP, zum Abgeben oder Mitnehmen
        (Punkt 104). Vorher wird gespeichert. Liefert die Zahl der
        Dateien. Wie die ZIP entsteht, steht bei `zip_schreiben`.

        Ließ sich eine geänderte Datei nicht speichern, entsteht keine
        ZIP, und das Ergebnis ist `None`: abgegeben würde sonst ein
        älterer Stand, als im Editor steht (Punkt 210). Die Meldung
        dazu kommt schon von `alle_speichern()`.

        Der Ordner in der ZIP heißt wie `abgabe_name()`, mit dem
        Anmeldenamen, damit eingesammelte Abgaben nebeneinander
        entpackt werden können (Punkt 323).

        Läuft im Faden des Aufrufers. Das Menü nimmt dafür einen
        Nebenfaden (`_als_zip_aktion`)."""
        if not self.alle_speichern():
            return None
        ordner = self.projekt.ordner
        return zip_schreiben(ordner, abgabe_name(ordner.name), Path(ziel))

    def _als_zip_aktion(self) -> None:
        """„Projekt → Als ZIP speichern …“.

        Gespeichert wird vorher im Faden der Oberfläche, die ZIP
        entsteht nebenher. Bei einem Projekt mit 100 MB Fotos stand
        Natter sonst mehrere Sekunden still (Punkt 388)."""
        if self.projekt is None:
            self.statusBar().showMessage(self._kein_projekt_text())
            return
        if not self._hintergrund_frei("Als ZIP speichern"):
            return
        vorschlag = (
            self.projekt.ordner.parent
            / f"{abgabe_name(self.projekt.ordner.name)}.zip"
        )
        ziel, _ = QFileDialog.getSaveFileName(
            self, "Projekt als ZIP speichern", str(vorschlag), "ZIP-Archiv (*.zip)"
        )
        if not ziel:
            return
        if not self.alle_speichern():
            self.statusBar().showMessage(
                "Keine ZIP geschrieben: nicht alle Dateien ließen sich speichern."
            )
            return
        ordner = self.projekt.ordner
        oben = abgabe_name(ordner.name)
        ziel = Path(ziel)
        abbruch = threading.Event()

        def packen(melden: Callable[[int, str], None]) -> tuple:
            def melden_oder_aufhoeren(prozent: int, text: str) -> None:
                # Gerufen nach jeder gepackten Datei. Am Ziel ist in
                # dieser Zeit noch nichts angelegt, und die
                # Zwischendatei im Temp-Ordner räumt `zip_schreiben`
                # selbst weg (Punkt 394).
                if abbruch.is_set():
                    raise ZipAbgebrochen(ziel)
                melden(prozent, text)

            # Ein Fehler kommt als Ergebnis zurück und nicht über
            # `fehlgeschlagen`: dort käme nur sein Text an, und die
            # Meldung hängt an der Art des Fehlers.
            try:
                ergebnis = zip_schreiben(
                    ordner, oben, ziel, melden_oder_aufhoeren
                )
            except OSError as fehler:
                ergebnis = fehler
            return ordner, ziel, ergebnis

        self._fortschritt_zeigen(0)
        self.statusBar().showMessage(f"{ziel.name} wird gespeichert …")
        lauf = self._hintergrund_starten(
            packen, self._als_zip_fertig, "Als ZIP speichern fehlgeschlagen"
        )
        self._zip_lauf = (lauf, abbruch)

    def _als_zip_fertig(self, ergebnis: tuple) -> None:
        """Meldet das Ergebnis von `_als_zip_aktion`, zurück im Faden
        der Oberfläche."""
        self._zip_lauf = None
        self._fortschritt_verbergen()
        ordner, ziel, anzahl = ergebnis
        # Ein Fenster statt der Statuszeile: eine Abgabe, die nicht
        # entstanden ist, darf am Stundenende nicht übersehen werden.
        # Der Text von Windows bleibt draußen; er ist englisch und
        # nennt bei einem Lesefehler nicht, was zu tun ist (Punkt 343).
        if isinstance(anzahl, ZipDateiUnlesbar):
            name = anzahl.pfad.relative_to(ordner)
            self.statusBar().showMessage(
                f"Keine ZIP gespeichert: {name} ließ sich nicht lesen."
            )
            QMessageBox.warning(
                self,
                "Keine ZIP gespeichert",
                f"„{name}“ ließ sich nicht lesen. Vermutlich ist die "
                "Datei gerade in einem anderen Programm geöffnet, etwa "
                "in Excel.\n\nNach dem Schließen der Datei dort lässt "
                "sich die ZIP noch einmal speichern. Angelegt wurde "
                "keine ZIP.",
            )
            return
        if isinstance(anzahl, ZipVorigeBeschaedigt):
            self.statusBar().showMessage("Keine ZIP gespeichert.")
            QMessageBox.warning(
                self,
                "Keine ZIP gespeichert",
                f"„{ziel.name}“ ließ sich nicht schreiben in\n"
                f"{ziel.parent}\n\nDie ältere ZIP gleichen Namens "
                "ließ sich danach nicht wiederherstellen und ist nicht "
                "mehr vollständig. Eine neue Abgabe lässt sich an "
                "einem anderen Ort speichern, etwa auf einem anderen "
                "Laufwerk.",
            )
            return
        if isinstance(anzahl, ZipAbgebrochen):
            self.statusBar().showMessage("Keine ZIP gespeichert.")
            QMessageBox.warning(
                self,
                "Keine ZIP gespeichert",
                f"„{ziel.name}“ war nach {self._ZIP_GEDULD:.0f} "
                "Sekunden noch nicht fertig, als Natter geschlossen "
                "wurde. Angelegt wurde keine ZIP.\n\nNach dem nächsten "
                "Start lässt sich die ZIP noch einmal speichern.",
            )
            return
        if isinstance(anzahl, OSError):
            self.statusBar().showMessage("Keine ZIP gespeichert.")
            QMessageBox.warning(
                self,
                "Keine ZIP gespeichert",
                f"„{ziel.name}“ ließ sich nicht schreiben in\n"
                f"{ziel.parent}\n\nHäufige Gründe: der Ordner hat "
                "kein Schreibrecht, der USB-Stick ist abgezogen, oder "
                "eine ältere ZIP gleichen Namens ist in einem anderen "
                "Programm geöffnet.",
            )
            return
        self.statusBar().showMessage(f"{anzahl} Dateien in {ziel.name} gespeichert.")
        if self._schliesst_nach_zip:
            # Die Statuszeile verschwindet gleich mit dem Fenster.
            QMessageBox.information(
                self,
                "ZIP gespeichert",
                f"„{ziel.name}“ ist vollständig gespeichert in\n"
                f"{ziel.parent}\n\n{anzahl} Dateien.",
            )

    #: Wie lange Natter beim Schließen höchstens auf eine Abgabe-ZIP
    #: wartet, bevor es sie abbricht (Punkt 394).
    _ZIP_GEDULD = 60.0

    def _zip_abwarten(self) -> None:
        """Wartet beim Schließen auf eine Abgabe-ZIP, die noch
        entsteht, und zeigt ihr Ergebnis (Punkt 394).

        `_hintergrund_abbrechen` löst die Signale, bevor es auf den
        Faden wartet; ohne diesen Schritt lief `_als_zip_fertig` nie.
        Wer am Stundenende abgibt und gleich schließt, erfuhr dann
        weder von einer gescheiterten Abgabe noch von einer
        gelungenen. Das Fenster bleibt deshalb offen, bis die ZIP
        fertig ist, und die Meldung kommt wie ohne Schließen, bei
        Erfolg zusätzlich in einem Fenster.

        Länger als `_ZIP_GEDULD` Sekunden wartet Natter nicht. Danach
        hört das Packen nach der laufenden Datei auf; angelegt wird
        am Ziel dann nichts, und die Meldung sagt das. Eingaben an
        das Fenster bleiben während des Wartens liegen."""
        zip_lauf = self._zip_lauf
        if zip_lauf is None:
            return
        lauf, abbruch = zip_lauf
        from PySide6.QtCore import QEventLoop

        self._schliesst_nach_zip = True
        try:
            self.statusBar().showMessage(
                "Natter schließt, sobald die ZIP gespeichert ist …"
            )
            ende = time.monotonic() + self._ZIP_GEDULD
            nur_signale = QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents
            while not lauf.wait(50):
                QApplication.processEvents(nur_signale)
                if time.monotonic() > ende:
                    abbruch.set()
            # Das Ergebnis wurde vor dem Ende des Fadens als Signal
            # abgeschickt und wird hier zugestellt.
            QApplication.processEvents(nur_signale)
        finally:
            self._schliesst_nach_zip = False
            self._zip_lauf = None

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
        if endung == ".natter":
            # Eine Projektdatei ist kein Text zum Bearbeiten: im Editor
            # stand sonst ihr JSON, und Speichern überschrieb, was nur
            # Natter schreiben soll (Punkt 213).
            self.projekt_oeffnen_gemeldet(pfad)
            return
        if self._beispiel_gesperrt(pfad):
            return
        if ist_beispiel_original(pfad):
            kopie = self._in_der_arbeitskopie(pfad)
            if kopie is None:
                return
            pfad = kopie
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
            except (
                json.JSONDecodeError, UnicodeDecodeError, schema_fehler(),
                KeyError, PfmBeschaedigt,
            ) as fehler:
                self.statusBar().showMessage(
                    f"„{pfad.name}“ lässt sich nicht öffnen, die Datei ist "
                    f"beschädigt. {fehler_beschreiben(fehler)} Sie wird von "
                    "Natter geschrieben und sollte nicht von Hand bearbeitet "
                    "werden."
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
            # Mit dem Projektordner reichen Bilder und Verweise einer
            # Unterseite wie `seiten/kontakt.html` bis `../bilder/`
            # und zurück zur Startseite (Punkt 382).
            self.datei_ansicht_oeffnen(
                pfad,
                lambda: HtmlVorschau(
                    pfad, projektordner=self._offener_projektordner()
                ),
            )
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

    def _in_der_arbeitskopie(self, pfad: Path) -> Path | None:
        """Dieselbe Datei in der Arbeitskopie des Beispiels, in dem
        `pfad` liegt; die Kopie wird dazu angelegt, wenn es sie noch
        nicht gibt.

        Ein Original wird nie an Ort und Stelle geöffnet, auch nicht
        als einzelne Datei: der Designer schreibt jede Änderung von
        sich aus zurück, und in einer installierten Natter liegt das
        Original im Programmordner (Punkt 211)."""
        ordner = _beispiel_projektordner(pfad)
        projektdatei = (
            next(iter(ordner.glob("*.natter")), None) if ordner else None
        )
        if projektdatei is None:
            self.statusBar().showMessage(
                f"„{pfad.name}“ gehört zu den mitgelieferten Beispielen "
                "und lässt sich nur über „Datei → Beispielprojekte“ öffnen."
            )
            return None
        try:
            kopie = beispiel_kopieren(projektdatei).parent
        except (OSError, ValueError) as fehler:
            self.statusBar().showMessage(
                f"Die Arbeitskopie des Beispiels ließ sich nicht anlegen: "
                f"{fehler}"
            )
            return None
        ziel = kopie / pfad.resolve().relative_to(ordner.resolve())
        self.statusBar().showMessage(
            f"Geöffnet wird die Arbeitskopie des Beispiels in {kopie}."
        )
        return ziel

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

    def _offener_projektordner(self) -> Path | None:
        """Der Ordner des geöffneten Projekts, sonst `None`. Ob eine
        Datei darin liegt, entscheidet die Ansicht selbst."""
        return self.projekt.ordner if self.projekt is not None else None

    def _markdown_ansicht(self, pfad: Path) -> MarkdownAnsicht:
        """Eine Markdown-Ansicht, deren Verweise in Natter aufgehen.

        Ein Klick auf `u_main.py` oder `docs/komponenten.md` im Text
        führt über `oeffnen()` in die Ansicht, die dazu passt - nicht an
        Windows vorbei in irgendein fremdes Programm.
        """
        ansicht = MarkdownAnsicht(
            pfad, projektordner=self._offener_projektordner()
        )
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
            if not self._einzelne_datei_starten():
                self.statusBar().showMessage(self._kein_projekt_text())
            return
        if self._laedt_noch():
            return
        if self._laeuft_schon():
            return

        if self._vorstart_pruefung_blockiert():
            return

        self._ausgabe_leser_beenden()
        if self.ausgabe_vor_start_leeren():
            self.ausgabe_liste.clear()
        lademarke = self._lademarke_fuer(self.projekt)
        self._endmarke_entfernen()
        self._endmarke = endmarke_zu(lademarke)
        # Was vom vorigen Lauf noch übrig ist, endet jetzt.
        self._programm_auftrag_beenden()
        self.laufender_prozess = projekt_starten(self.projekt, lademarke=lademarke)
        self._programm_auftrag = auftrag_von(self.laufender_prozess)
        self._ausgabe_leser_starten()
        self._start_zeitpunkt = time.monotonic()
        self.ausgabe_zeile(f"{self.projekt.name} gestartet ({self.projekt.haupt_datei.name})")
        self.panels.setCurrentWidget(self.ausgabe_liste)
        self._laufzeit_uhr.start()
        if any(self._offene_breakpoints().values()):
            # Das schlichte grüne Dreieck wird im Unterricht als
            # „Start“ gelesen; ein gesetzter Haltepunkt schien dann
            # kaputt (Punkt 464).
            hinweis = (
                "Ohne Debugger gestartet: Haltepunkte wirken nur mit "
                "„Start → Starten“ (F5)."
            )
            self.ausgabe_zeile(hinweis)
            self.statusBar().showMessage(f"{self.projekt.name} gestartet. {hinweis}")
        else:
            self.statusBar().showMessage(f"{self.projekt.name} gestartet")
        prozess = self.laufender_prozess
        self._ladeanzeige_starten(lambda: prozess, lademarke)

    def _programm_laeuft(self) -> bool:
        """Läuft ein Programm aus Natter heraus, mit oder ohne
        Debugger?"""
        return self.debug_sitzung is not None or (
            self.laufender_prozess is not None
            and self.laufender_prozess.poll() is None
        )

    def _laeuft_schon(self) -> bool:
        """Beim Start: läuft schon ein Programm, mit oder ohne Debugger?
        Dann startet kein zweites, und die Statusleiste sagt, wie das
        erste endet.

        Bis 0.4.2 sah jeder Startweg nur nach seinem eigenen Programm:
        F5 prüfte die Debugger-Sitzung, Strg+F5 den Prozess. Wer erst
        Strg+F5 und dann F5 drückte, hatte zwei Fenster desselben
        Programms (Punkt 429)."""
        self._wartendes_fenster_schliessen()
        laeuft = self._programm_laeuft()
        if laeuft:
            name = self.projekt.name if self.projekt is not None else "Das Programm"
            self.statusBar().showMessage(
                f"{name} läuft bereits - zuerst über „Start → Stopp“ beenden."
            )
        return laeuft

    def _einzelne_datei_starten(self, *, mit_debugger: bool = False) -> bool:
        """Startet die `.py`-Datei im aktiven Reiter, wenn kein Projekt
        offen ist, als Konsolenprogramm. Liefert, ob es eine solche
        Datei gab.

        Eine Aufgabe kommt oft als einzelne Datei vom Tauschlaufwerk.
        Sie ließ sich öffnen, F5 und Strg+F5 meldeten aber nur „Kein
        Projekt offen“, und ein Projekt dazu gab es nicht (Punkt 454).
        Das Projekt dafür entsteht nur im Speicher: im Ordner der
        Lehrkraft wird nichts angelegt. Den Debugger und die Prüfung
        vor dem Start gibt es nur in einem Projekt."""
        editor = self._aktueller_editor()
        pfad = editor.property(_PFAD_EIGENSCHAFT) if editor is not None else None
        if not pfad or not str(pfad).lower().endswith(".py"):
            return False
        datei = Path(pfad)
        if self._laedt_noch() or self._laeuft_schon():
            return True
        if editor.document().isModified() and not self._editor_speichern(editor):
            return True
        projekt = Projekt(
            ordner=datei.parent,
            daten={
                "format": "natter-project/1",
                "name": datei.stem,
                "type": "console",
                "main": datei.name,
            },
        )
        self._ausgabe_leser_beenden()
        if self.ausgabe_vor_start_leeren():
            self.ausgabe_liste.clear()
        lademarke = self._lademarke_fuer(projekt)
        self._endmarke_entfernen()
        self._endmarke = endmarke_zu(lademarke)
        self._programm_auftrag_beenden()
        self.laufender_prozess = projekt_starten(projekt, lademarke=lademarke)
        self._programm_auftrag = auftrag_von(self.laufender_prozess)
        self._start_zeitpunkt = time.monotonic()
        self.ausgabe_zeile(f"{datei.name} gestartet")
        self.panels.setCurrentWidget(self.ausgabe_liste)
        self._laufzeit_uhr.start()
        self.statusBar().showMessage(
            f"{datei.name} läuft ohne Debugger - den gibt es nur in einem "
            "Projekt."
            if mit_debugger
            else f"{datei.name} gestartet"
        )
        prozess = self.laufender_prozess
        self._ladeanzeige_starten(lambda: prozess, lademarke)
        self._startaktionen_pruefen()
        return True

    def _programm_wartet_nur_noch(self) -> bool:
        """Ob das Konsolenprogramm fertig ist und sein Fenster nur noch
        auf die Eingabetaste wartet."""
        return self._endmarke is not None and self._endmarke.exists()

    def _wartendes_fenster_schliessen(self) -> None:
        """Schließt das Fenster eines fertigen Konsolenprogramms, das
        nur noch auf die Eingabetaste wartet. Der nächste Start soll
        nicht daran scheitern: wer den Code ändert und neu startet,
        drückt vorher nicht im alten Fenster die Eingabetaste
        (Punkt 455)."""
        if not self._programm_wartet_nur_noch():
            return
        if self.debug_sitzung is not None:
            self.debug_sitzung.beenden()
            self.debug_sitzung = None
            self._aktueller_thread_id = None
            self._faden_id = None
        if self.laufender_prozess is not None:
            prozessbaum_beenden(self.laufender_prozess)
            self._ausgabe_leser_beenden()
            self.laufender_prozess = None
        self._laufzeit_uhr.stop()
        self._endmarke_entfernen()
        self._startaktionen_pruefen()

    def _endmarke_entfernen(self) -> None:
        if self._endmarke is not None:
            try:
                self._endmarke.unlink(missing_ok=True)
            except OSError:
                pass
        self._endmarke = None
        self._ende_gemeldet = False

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
        danach.

        Vorher werden alle geänderten Dateien gespeichert (Punkt 86).
        Gestartet wird die Datei auf der Platte; bis 0.3.5 lief deshalb
        der Stand vor der letzten Änderung, wenn Strg+S vergessen war.
        Lässt sich eine Datei nicht schreiben, unterbleibt der Start.

        Eine offene Transaktion im Datenbank-Panel wird vorher
        festgeschrieben oder zurückgenommen, je nach Antwort auf die
        Nachfrage; ohne Antwort unterbleibt der Start (Punkt 276)."""
        if not self._transaktion_vor_dem_start_klaeren():
            return True
        if not self.alle_speichern():
            return True
        funde = projekt_pruefen(self.projekt)
        self.meldungen_liste.clear()
        self._funde_in_editoren_zeigen(funde)
        if not funde:
            return False

        for fund in funde:
            eintrag = QListWidgetItem(str(fund))
            eintrag.setData(
                _FUND_ROLLE, (str(fund.datei), fund.zeile, fund.spalte)
            )
            eintrag.setToolTip(fund.regel)
            self.meldungen_liste.addItem(eintrag)
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
        leser = AusgabeLeser(prozess, grenze=AUSGABE_GRENZE)
        self._ausgabe_leser = leser
        leser.start()
        self._ausgabe_uhr.start()

    def _ausgabe_leser_beenden(self) -> None:
        """Wartet kurz auf den Leser, statt ihn stehenzulassen, und
        übernimmt, was er noch gelesen hat.

        Beim Beenden des Programms geht sein Rohr zu, und der Leser
        kommt von selbst zum Ende - das dauert aber einen Augenblick.
        Hält ein Prozess, den das Programm gestartet hat und der es
        überlebt, das Rohr noch offen, liest der Leser weiter, bis
        auch dieser Prozess zu Ende ist. Er läuft dann ohne Verbindung
        zum Fenster als Daemon-Faden weiter und hält Natter nicht auf
        (Punkt 278).
        """
        leser = self._ausgabe_leser
        if leser is not None and leser.laeuft():
            leser.wait(1000)
        self._ausgabe_abholen()
        self._ausgabe_leser = None
        self._ausgabe_uhr.stop()

    def _ausgabe_abholen(self) -> None:
        """Übernimmt die Zeilen, die der Leser seit dem letzten Takt
        gelesen hat, auf einmal ins Panel (Punkt 267)."""
        leser = self._ausgabe_leser
        if leser is None:
            self._ausgabe_uhr.stop()
            return
        fertig = leser.ist_fertig()
        zeilen, verdraengt = leser.abholen()
        self._ausgabe_zeilen_anhaengen(zeilen, verdraengt)
        if fertig:
            self._ausgabe_uhr.stop()

    def _ausgabe_zeilen_anhaengen(
        self, zeilen: list[str], verdraengt: int = 0
    ) -> None:
        """Hängt `zeilen` mit der Uhrzeit davor ans Panel „Ausgabe“.

        Gescrollt wird nur, wenn die Liste schon unten stand: wer
        weiter oben etwas nachliest, wird nicht bei jeder neuen Zeile
        wieder ans Ende gerissen. Mehr als `AUSGABE_GRENZE` Zeilen
        hält das Panel nicht; die ältesten fallen weg, und die erste
        Zeile sagt, wie viele es insgesamt waren. `verdraengt` sind
        Zeilen, die schon im Leser keinen Platz mehr hatten. Eine
        Zeile über `ZEILEN_GRENZE` Zeichen erscheint gekürzt
        (`_ausgabe_kuerzen`).
        """
        if not zeilen and not verdraengt:
            return
        liste = self.ausgabe_liste
        leiste = liste.verticalScrollBar()
        war_unten = leiste.value() >= leiste.maximum() - 2
        uhrzeit = time.strftime("%H:%M:%S")
        liste.addItems(
            [f"{uhrzeit}  {_ausgabe_kuerzen(text)}" for text in zeilen]
        )

        hinweis = liste.item(0)
        if hinweis is not None and hinweis.data(_WEGGEFALLEN_ROLLE) is None:
            hinweis = None
        weggefallen = verdraengt
        if hinweis is not None:
            weggefallen += int(hinweis.data(_WEGGEFALLEN_ROLLE))
        erste = 0 if hinweis is None else 1
        ueberschuss = liste.count() - erste - (AUSGABE_GRENZE - 1)
        if ueberschuss > 0:
            liste.model().removeRows(erste, ueberschuss)
            weggefallen += ueberschuss
        if weggefallen:
            if hinweis is None:
                hinweis = QListWidgetItem()
                liste.insertItem(0, hinweis)
            anzahl = f"{weggefallen:,}".replace(",", ".")
            grenze = f"{AUSGABE_GRENZE:,}".replace(",", ".")
            wort = "Zeile" if weggefallen == 1 else "Zeilen"
            hinweis.setText(
                f"… {anzahl} ältere {wort} weggefallen - das Panel "
                f"hält höchstens {grenze} Zeilen."
            )
            hinweis.setData(_WEGGEFALLEN_ROLLE, weggefallen)
        if war_unten:
            liste.scrollToBottom()

    # -- Ladeanzeige nach dem Start (Punkt 271) ------------------------

    def _lademarke_fuer(self, projekt: Projekt) -> Path | None:
        """Eine Marke für die erste Ausgabe. Nur ein Konsolenprogramm
        braucht sie; bei einem Programm mit Fenster zählt das Fenster.
        """
        lademarke_entfernen(self._lademarke)
        self._lademarke = None
        if projekt.typ != "console":
            return None
        return lademarke_anlegen()

    def _ladeanzeige_starten(
        self,
        prozess: Callable[[], subprocess.Popen | None],
        lademarke: Path | None,
    ) -> None:
        """Zeigt in der Statusleiste, dass das Programm noch lädt, bis
        es ein Fenster zeigt, etwas ausgibt oder endet.

        `prozess` liefert den gestarteten Prozess. Unter dem Debugger
        entsteht er erst in einem Nebenfaden und ist in den ersten
        Augenblicken noch `None`.
        """
        if self._lade_anzeige is None:
            anzeige = QWidget()
            # Nur so breit wie Balken und Text. Mit der üblichen
            # Größenregel bekam der Behälter den ganzen freien Platz
            # der Leiste, der Text stand in der Mitte, und „Zeile N,
            # Spalte M“ sprang beim Laden nach links (Punkt 413).
            anzeige.setSizePolicy(
                QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred,
            )
            zeile = QHBoxLayout(anzeige)
            zeile.setContentsMargins(0, 0, 0, 0)
            balken = QProgressBar()
            # Minimum und Maximum 0: ein Balken, der hin- und herläuft,
            # weil niemand weiß, wie lange es noch dauert.
            balken.setRange(0, 0)
            balken.setMaximumWidth(120)
            balken.setMaximumHeight(14)
            balken.setTextVisible(False)
            self._lade_text = QLabel()
            zeile.addWidget(balken)
            zeile.addWidget(self._lade_text)
            self.statusBar().addPermanentWidget(anzeige)
            self._lade_anzeige = anzeige
        self._lade_prozess = prozess
        self._lademarke = lademarke
        self._lade_beginn = time.monotonic()
        self._ladeanzeige_text_setzen(0)
        self._lade_anzeige.show()
        self._lade_uhr.start()

    def _ladeanzeige_text_setzen(self, sekunden: int) -> None:
        if self._lade_text is not None:
            self._lade_text.setText(f"Programm wird geladen … {sekunden} s")

    def laedt_programm(self) -> bool:
        """Läuft die Ladeanzeige gerade?"""
        return self._lade_beginn is not None

    def _laedt_noch(self) -> bool:
        """Beim Start: lädt das vorige Programm noch? Dann startet es
        nicht ein zweites Mal, und die Statusleiste sagt, warum nichts
        passiert. Wer ungeduldig ein zweites Mal F5 drückte, hatte bis
        0.3.6 zwei Programme."""
        if self._lade_beginn is None:
            return False
        sekunden = int(time.monotonic() - self._lade_beginn)
        name = self.projekt.name if self.projekt is not None else "Das Programm"
        self.statusBar().showMessage(
            f"{name} läuft bereits und wird noch geladen ({sekunden} s) - "
            f"ein zweiter Start ist nicht nötig. Abbrechen über „Start → Stopp“."
        )
        if self._lade_anzeige is not None:
            self._lade_anzeige.show()
        return True

    def _ladeanzeige_pruefen(self) -> None:
        """Ein Takt der Ladeanzeige: Zeit weiterzählen und nachsehen,
        ob das Programm inzwischen sichtbar ist. Kostet einen Blick
        auf die Fensterliste und wartet nie auf das Programm."""
        if self._lade_beginn is None or self._lade_prozess is None:
            self._ladeanzeige_beenden()
            return
        if self.debug_sitzung is None and self.laufender_prozess is None:
            self._ladeanzeige_beenden()
            return
        sekunden = int(time.monotonic() - self._lade_beginn)
        self._ladeanzeige_text_setzen(sekunden)
        if lademarke_gesetzt(self._lademarke):
            self._ladeanzeige_beenden()
            return
        prozess = self._lade_prozess()
        if prozess is not None and (
            prozess.poll() is not None or hat_sichtbares_fenster(prozess.pid)
        ):
            self._ladeanzeige_beenden()
            return
        if sekunden >= _LADE_GRENZE_S:
            self._ladeanzeige_beenden()
            self.statusBar().showMessage(
                f"Das Programm läuft seit {sekunden} s, hat aber noch kein "
                f"Fenster gezeigt und nichts ausgegeben."
            )

    def _ladeanzeige_beenden(self) -> None:
        """Blendet die Anzeige aus und entfernt die Markendatei.

        Den Pfad der Marke behält das Fenster, bis das Programm zu
        Ende ist oder das nächste startet (Punkt 314). Endet die
        Anzeige wegen der Zeitgrenze, an einem Haltepunkt oder über
        ein Fenster, legt die Hülle die Datei bei der ersten Ausgabe
        trotzdem noch an; bis 0.3.6 war der Pfad dann schon vergessen,
        und die Datei blieb im Temp-Ordner liegen. Jeder Weg, auf dem
        das Programm endet, ruft diese Methode deshalb nach dem Ende
        noch einmal auf."""
        self._lade_uhr.stop()
        self._lade_beginn = None
        self._lade_prozess = None
        lademarke_entfernen(self._lademarke)
        if self._lade_anzeige is not None:
            self._lade_anzeige.hide()

    # -- Einstellungen (Punkte 98 und 101) -------------------------------

    def editor_schriftgroesse(self) -> int:
        from ide.shell.quelltexteditor import _CODE_SCHRIFTGROESSE

        wert = self._design_einstellungen.value("editor/schriftgroesse", _CODE_SCHRIFTGROESSE)
        try:
            return int(wert)
        except (TypeError, ValueError):
            return _CODE_SCHRIFTGROESSE

    def _editor_schriftgroesse_merken(self, groesse: int) -> None:
        """Gilt für alle offenen Editoren und beim nächsten Start. Bis
        0.3.5 galt Strg+Mausrad nur für den einen Editor und war nach
        dem Neustart vergessen."""
        self._design_einstellungen.setValue("editor/schriftgroesse", groesse)
        for index in range(self.editor_tabs.count()):
            widget = self._tab_inhalt(self.editor_tabs.widget(index))
            if isinstance(widget, QuelltextEditor):
                widget.schriftgroesse_setzen(groesse)
        self._panel_schrift_anpassen()

    def oberflaeche_schriftgroesse(self) -> int:
        """Schriftgröße der ganzen Oberfläche in Punkt (Punkt 302)."""
        wert = self._design_einstellungen.value(
            "oberflaeche/schriftgroesse", basis_schriftgroesse()
        )
        try:
            return max(7, min(32, int(wert)))
        except (TypeError, ValueError):
            return basis_schriftgroesse()

    def _stil_anwenden(self) -> None:
        """Setzt das Stylesheet aus Design, Editor-Schrift und
        Schriftgröße der Oberfläche."""
        self.setStyleSheet(
            ide_qss_erzeugen(
                self._design_thema,
                code_schriftart=self._code_schriftart,
                basis_pt=self.oberflaeche_schriftgroesse(),
            )
        )

    def _panel_schrift_anpassen(self) -> None:
        """„Meldungen“ und „Ausgabe“ wachsen mit Strg++ mit (Punkt 302).

        Wer am Beamer ein Programm vorführt, zeigt dessen Ausgabe
        vorne mit; bis 0.3.x blieb sie in der kleinsten Schrift im
        Fenster stehen, während der Quelltext größer wurde. Beide
        Listen stehen deshalb um so viele Punkte über der Schrift der
        Oberfläche, wie der Editor über seiner Grundgröße steht."""
        from ide.shell.quelltexteditor import _CODE_SCHRIFTGROESSE

        abstand = self.editor_schriftgroesse() - _CODE_SCHRIFTGROESSE
        groesse = max(7, self.oberflaeche_schriftgroesse() + abstand)
        for liste in (self.ausgabe_liste, self.meldungen_liste):
            liste.setStyleSheet(f"QListWidget {{ font-size: {groesse}pt; }}")
        # Ebenso die Panels des Debuggers und offene Hilfeseiten: wer
        # am Beamer eine Schleife im Debugger vorführt oder „Erste
        # Schritte“ zeigt, bekam sonst genau die Teile nicht größer,
        # auf die die Klasse schaut (Punkt 467).
        for baum in (
            self.variablen_baum, getattr(self, "ueberwachen_baum", None)
        ):
            if baum is not None:
                baum.setStyleSheet(f"QTreeWidget {{ font-size: {groesse}pt; }}")
        self.aufrufstapel_liste.setStyleSheet(
            f"QListWidget {{ font-size: {groesse}pt; }}"
        )
        for index in range(self.editor_tabs.count()):
            ansicht = self.editor_tabs.widget(index)
            if isinstance(ansicht, HilfeAnsicht):
                ansicht.setStyleSheet(
                    f"HilfeAnsicht {{ font-size: {groesse}pt; }}"
                )

    def _schriftgroesse_aktion(self, schritt: int) -> None:
        """„Ansicht → Schrift größer/kleiner/normal“ (Strg+Plus,
        Strg+Minus, Strg+0)."""
        from ide.shell.quelltexteditor import _CODE_SCHRIFTGROESSE

        groesse = _CODE_SCHRIFTGROESSE if schritt == 0 else self.editor_schriftgroesse() + schritt
        groesse = max(7, min(32, groesse))
        self._editor_schriftgroesse_merken(groesse)
        self.statusBar().showMessage(
            f"Schriftgröße im Editor: {groesse} pt "
            f"(Panels und Hilfeseiten wachsen mit)"
        )

    def ausgabe_vor_start_leeren(self) -> bool:
        wert = self._design_einstellungen.value("ausgabe/vor_start_leeren", True)
        return wert not in (False, "false", "0", 0)

    def _einstellungen_aktion(self) -> None:
        """„Werkzeuge → Einstellungen …“."""
        from ide.shell.einstellungen_dialog import EinstellungenDialog

        dialog = EinstellungenDialog(
            self.editor_schriftgroesse(),
            self.ausgabe_vor_start_leeren(),
            self,
            oberflaeche=self.oberflaeche_schriftgroesse(),
        )
        self.letzter_einstellungen_dialog = dialog
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.einstellungen_uebernehmen(
                dialog.schriftgroesse(),
                dialog.ausgabe_leeren(),
                oberflaeche=dialog.oberflaeche(),
            )

    def einstellungen_uebernehmen(
        self,
        schriftgroesse: int,
        ausgabe_leeren: bool,
        oberflaeche: int | None = None,
    ) -> None:
        if oberflaeche is not None:
            # Die ganze Oberfläche auf einmal, für den Beamer
            # (Punkt 302): Menüs, Docks, Panels und Dialoge.
            self._design_einstellungen.setValue(
                "oberflaeche/schriftgroesse", oberflaeche
            )
            self._stil_anwenden()
        self._editor_schriftgroesse_merken(schriftgroesse)
        self._design_einstellungen.setValue("ausgabe/vor_start_leeren", ausgabe_leeren)

    def ausgabe_kontextmenue(self) -> QMenu:
        """Rechte Maustaste im Panel „Ausgabe“: Kopieren ohne die
        Uhrzeit davor und Leeren (Punkt 98)."""
        menue = QMenu(self)
        markiert = self.ausgabe_liste.selectedItems()
        kopieren = menue.addAction("Markierte Zeilen kopieren")
        kopieren.setEnabled(bool(markiert))
        kopieren.triggered.connect(lambda *_: self._ausgabe_kopieren(nur_markierte=True))
        menue.addAction("Alles kopieren").triggered.connect(
            lambda *_: self._ausgabe_kopieren(nur_markierte=False)
        )
        menue.addSeparator()
        menue.addAction("Leeren").triggered.connect(lambda *_: self.ausgabe_liste.clear())
        return menue

    def _ausgabe_kopieren(self, *, nur_markierte: bool) -> str:
        eintraege = (
            self.ausgabe_liste.selectedItems()
            if nur_markierte
            else [self.ausgabe_liste.item(i) for i in range(self.ausgabe_liste.count())]
        )
        zeilen = [re.sub(r"^\d\d:\d\d:\d\d  ", "", e.text()) for e in eintraege]
        text = "\n".join(zeilen)
        QApplication.clipboard().setText(text)
        return text

    def ausgabe_zeile(self, text: str) -> None:
        """Eine Zeile im Panel „Ausgabe“, mit der Uhrzeit davor.

        Was das Programm bis hierher ausgegeben hat, kommt vorher ins
        Panel; sonst stünde „Programm beendet“ über seinen letzten
        Zeilen."""
        if self._ausgabe_leser is not None:
            self._ausgabe_abholen()
        self._ausgabe_zeilen_anhaengen([text])

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
            if self._programm_wartet_nur_noch() and not self._ende_gemeldet:
                self._ende_gemeldet = True
                self.ausgabe_zeile(
                    "Programm beendet - das Konsolenfenster wartet auf die "
                    "Eingabetaste. Ein neuer Start schließt es."
                )
            return
        self._laufzeit_uhr.stop()
        self.programmende_melden(code)
        self.laufender_prozess = None

    def _programm_auftrag_beenden(self) -> bool:
        """Beendet, was im Auftragsobjekt des letzten Programms noch
        läuft, und gibt es frei. Liefert, ob dabei noch etwas lief."""
        auftrag, self._programm_auftrag = self._programm_auftrag, None
        if auftrag is None:
            return False
        lief = auftrag.laeuft_noch()
        auftrag.beenden()
        return lief

    def programmende_melden(self, code: int) -> None:
        """Exitcode und Laufzeit ins Panel „Ausgabe“ (Abschnitt 7.8).

        Ein Exitcode ungleich 0 heißt, dass das Programm mit einem
        Fehler geendet ist. Das steht dabei, weil „Code 1“ allein
        niemandem etwas sagt. Wo die Fehlermeldung steht, hängt von
        der Art des Programms ab: ein Konsolenprogramm lässt sein
        Fenster dafür offen, ein Programm mit Fenster hat sie in einem
        Meldungsfenster gezeigt, das beim Erscheinen dieser Zeile
        schon geschlossen ist. Bis 0.3.4 hieß es in beiden Fällen, das
        Fenster bleibe offen."""
        self._ladeanzeige_beenden()
        dauer = ""
        if self._start_zeitpunkt is not None:
            sekunden = time.monotonic() - self._start_zeitpunkt
            dauer = f" nach {sekunden:.1f} s".replace(".", ",")
        self._start_zeitpunkt = None
        if code == 0:
            self.ausgabe_zeile(f"Programm beendet (Code 0){dauer}")
            return
        # Ohne Projekt lief eine einzelne Datei, und die immer als
        # Konsolenprogramm (Punkt 454).
        konsole = self.projekt is None or self.projekt.typ == "console"
        wo = (
            "Die Fehlermeldung steht im Konsolenfenster des Programms, es "
            "bleibt dafür offen."
            if konsole
            else "Die Fehlermeldung hat das Programm vor dem Beenden in "
            "einem eigenen Fenster gezeigt."
        )
        self.ausgabe_zeile(
            f"Programm beendet (Code {code}){dauer} – Code {code} heißt: mit einem Fehler "
            f"geendet. {wo}"
        )

    # -- Debugger (F5, Abschnitt 7.8/8.1) ------------------------------------

    def _breakpoints_weitergeben(self, editor: QuelltextEditor) -> None:
        """Ein Haltepunkt, der während des Debuggens gesetzt, entfernt
        oder mit seiner Zeile verschoben wird, gilt sofort (Punkt 118).
        Bis 0.3.5 bekam debugpy nur die Haltepunkte vom Start."""
        pfad = editor.property(_PFAD_EIGENSCHAFT)
        if self.debug_sitzung is not None and pfad:
            self.debug_sitzung.breakpoints_setzen(
                Path(pfad), sorted(editor.breakpoints), dict(editor.bedingungen)
            )

    def _offene_bedingungen(self) -> dict[Path, dict[int, str]]:
        gemerkt = self._gemerkte_haltepunkte
        ergebnis: dict[Path, dict[int, str]] = {
            Path(pfad): dict(bedingungen)
            for pfad, (_zeilen, bedingungen) in gemerkt.items()
            if bedingungen
        }
        for index in range(self.editor_tabs.count()):
            editor = self.editor_tabs.widget(index)
            if isinstance(editor, QuelltextEditor) and editor.bedingungen:
                pfad = editor.property(_PFAD_EIGENSCHAFT)
                if pfad:
                    ergebnis[Path(pfad)] = dict(editor.bedingungen)
        return ergebnis

    # -- Variablen, Überwachen, Werte unter der Maus (Punkte 99, 100) ---

    def _ueberwachen_aufbauen(self) -> None:
        from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QPushButton, QVBoxLayout

        self.ueberwachen_panel = QWidget()
        self.ueberwachen_eingabe = QLineEdit()
        self.ueberwachen_eingabe.setPlaceholderText(
            "Ausdruck, etwa  summe / anzahl  oder  len(liste)"
        )
        self.ueberwachen_eingabe.returnPressed.connect(self._ausdruck_hinzufuegen)
        knopf = QPushButton("Hinzufügen")
        knopf.clicked.connect(self._ausdruck_hinzufuegen)
        self.ueberwachen_baum = QTreeWidget()
        self.ueberwachen_baum.setHeaderLabels(["Ausdruck", "Wert"])
        self.ueberwachen_baum.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.ueberwachen_baum.customContextMenuRequested.connect(
            lambda punkt: self._ueberwachen_menue(punkt)
        )
        zeile = QHBoxLayout()
        zeile.addWidget(self.ueberwachen_eingabe, 1)
        zeile.addWidget(knopf)
        layout = QVBoxLayout(self.ueberwachen_panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(zeile)
        layout.addWidget(self.ueberwachen_baum)

    def ausdruck_ueberwachen(self, ausdruck: str) -> None:
        ausdruck = ausdruck.strip()
        if not ausdruck:
            return
        QTreeWidgetItem(self.ueberwachen_baum, [ausdruck, ""])
        self._ueberwachte_auswerten()

    def _ausdruck_hinzufuegen(self) -> None:
        self.ausdruck_ueberwachen(self.ueberwachen_eingabe.text())
        self.ueberwachen_eingabe.clear()

    def _ueberwachen_menue(self, punkt) -> None:  # noqa: ANN001
        eintrag = self.ueberwachen_baum.itemAt(punkt)
        if eintrag is None:
            return
        menue = QMenu(self)
        menue.addAction("Entfernen").triggered.connect(
            lambda *_: self.ueberwachen_baum.takeTopLevelItem(
                self.ueberwachen_baum.indexOfTopLevelItem(eintrag)
            )
        )
        menue.exec(self.ueberwachen_baum.viewport().mapToGlobal(punkt))

    def _aktueller_frame(self) -> int | None:
        stapel = getattr(self, "_letzter_aufrufstapel", None) or []
        if self.debug_sitzung is None or self._aktueller_thread_id is None or not stapel:
            return None
        return stapel[0]["id"]

    def _ueberwachte_auswerten(self) -> None:
        frame = self._aktueller_frame()
        for i in range(self.ueberwachen_baum.topLevelItemCount()):
            eintrag = self.ueberwachen_baum.topLevelItem(i)
            if frame is None:
                eintrag.setText(1, "")
                continue
            self.debug_sitzung.auswerten_fuer(eintrag.text(0), frame, f"ueberwachen:{i}")

    def _wert_unter_maus_erfragen(self, name: str, punkt) -> None:  # noqa: ANN001
        frame = self._aktueller_frame()
        if frame is None:
            return
        self._hinweis_punkt = punkt
        self.debug_sitzung.auswerten_fuer(name, frame, f"hinweis:{name}")

    def _variable_aufgeklappt(self, eintrag: QTreeWidgetItem) -> None:
        referenz = eintrag.data(0, Qt.ItemDataRole.UserRole)
        if not referenz or self.debug_sitzung is None or eintrag.data(1, Qt.ItemDataRole.UserRole):
            return
        eintrag.setData(1, Qt.ItemDataRole.UserRole, True)
        schluessel = f"kind:{id(eintrag)}"
        self._variablen_zu_laden[schluessel] = eintrag
        self.debug_sitzung.variablen_lesen_fuer(referenz, schluessel)

    def _variablen_eintraege(self, eltern, variablen: list[dict]) -> None:  # noqa: ANN001
        """Einträge im Panel „Variablen“; wer Kinder hat (Listen,
        Objekte), bekommt einen Pfeil zum Aufklappen."""
        for variable in variablen:
            if variable.get("name") in _DEBUGPY_GRUPPEN:
                continue
            eintrag = QTreeWidgetItem(eltern, [variable["name"], str(variable.get("value"))])
            referenz = variable.get("variablesReference") or 0
            if referenz:
                eintrag.setData(0, Qt.ItemDataRole.UserRole, referenz)
                eintrag.setChildIndicatorPolicy(
                    QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator
                )

    def _debugger_antwort(self, zweck: str, ergebnis) -> None:  # noqa: ANN001
        if zweck == "global":
            eintraege = [
                v for v in (ergebnis if isinstance(ergebnis, list) else [])
                if not v.get("name", "").startswith("__")
                and v.get("type") not in _KEINE_VARIABLEN
                and v.get("name") not in _DEBUGPY_GRUPPEN
            ]
            if not eintraege:
                return
            gruppe = QTreeWidgetItem(self.variablen_baum, ["Globale Variablen", ""])
            self._variablen_eintraege(gruppe, eintraege)
        elif zweck.startswith("kind:"):
            eintrag = self._variablen_zu_laden.pop(zweck, None)
            if eintrag is not None and isinstance(ergebnis, list):
                self._variablen_eintraege(eintrag, ergebnis)
                if eintrag.childCount() == 0:
                    eintrag.setChildIndicatorPolicy(
                        QTreeWidgetItem.ChildIndicatorPolicy.DontShowIndicator
                    )
        elif zweck.startswith("ueberwachen:"):
            index = int(zweck.split(":", 1)[1])
            eintrag = self.ueberwachen_baum.topLevelItem(index)
            if eintrag is not None:
                eintrag.setText(1, _auswertung_als_text(ergebnis))
        elif zweck.startswith("hinweis:"):
            name = zweck.split(":", 1)[1]
            if isinstance(ergebnis, dict) and "fehler" not in ergebnis:
                from PySide6.QtWidgets import QToolTip

                QToolTip.showText(
                    getattr(self, "_hinweis_punkt", QCursor.pos()),
                    f"{name} = {ergebnis.get('result', '')}",
                )
            self.letzter_hinweis = (name, _auswertung_als_text(ergebnis))

    def _offene_breakpoints(self) -> dict[Path, list[int]]:
        """Breakpoints aus allen offenen `QuelltextEditor`-Tabs, gebündelt
        nach Datei – für `DebugSitzung.starten(..., anfangs_breakpoints=...)`.

        Dazu kommen die Haltepunkte geschlossener Reiter aus
        `_gemerkte_haltepunkte` (Punkt 419)."""
        gemerkt = self._gemerkte_haltepunkte
        ergebnis: dict[Path, list[int]] = {
            Path(pfad): sorted(zeilen)
            for pfad, (zeilen, _bedingungen) in gemerkt.items()
        }
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
        übernommen.

        Ohne Parameter: `QAction.triggered` reicht sonst sein
        `checked`-Flag als ersten Wert hinein."""
        self._mit_debugger_starten()

    def _mit_debugger_starten(self, halten_bei: tuple[Path, int] | None = None) -> None:
        """Start mit Debugger; `halten_bei` für „Ausführen bis Cursor“."""
        if self.projekt is None:
            if not self._einzelne_datei_starten(mit_debugger=True):
                self.statusBar().showMessage(self._kein_projekt_text())
            return
        if self._laedt_noch():
            return
        if self._laeuft_schon():
            return

        if self._vorstart_pruefung_blockiert():
            return

        self.variablen_baum.clear()
        self.aufrufstapel_liste.clear()
        self._aktueller_thread_id = None
        self._faden_id = None

        self.debug_sitzung = DebugSitzung(self)
        self._startaktionen_pruefen()
        self.debug_sitzung.faden_bekannt.connect(self._debugger_faden_bekannt)
        self.debug_sitzung.antwort.connect(self._debugger_antwort)
        self.debug_sitzung.angehalten.connect(self._debugger_angehalten)
        self.debug_sitzung.beendet.connect(self._debugger_beendet)
        self.debug_sitzung.fehler.connect(self._debugger_fehler)
        self.debug_sitzung.aufrufstapel_bereit.connect(self._debugger_aufrufstapel_bereit)
        self.debug_sitzung.bereiche_bereit.connect(self._debugger_bereiche_bereit)
        self.debug_sitzung.variablen_bereit.connect(self._debugger_variablen_bereit)
        self.debug_sitzung.exceptioninfo_bereit.connect(self._debugger_exceptioninfo_bereit)
        self.debug_sitzung.ausgewertet.connect(self._debugger_tabelle_bereit)
        lademarke = self._lademarke_fuer(self.projekt)
        self._endmarke_entfernen()
        self._endmarke = endmarke_zu(lademarke)
        self.debug_sitzung.client.lademarke = lademarke
        self.debug_sitzung.starten(
            self.projekt.haupt_datei,
            arbeitsordner=self.projekt.ordner,
            anfangs_breakpoints=self._offene_breakpoints(),
            halten_bei=halten_bei,
            anfangs_bedingungen=self._offene_bedingungen(),
            konsole_titel=(
                f"Natter – {self.projekt.name}" if self.projekt.typ == "console" else None
            ),
        )
        self.statusBar().showMessage(f"{self.projekt.name} gestartet (mit Debugger)")
        sitzung = self.debug_sitzung
        self._ladeanzeige_starten(
            lambda: sitzung.client.prozess if self.debug_sitzung is sitzung else None,
            lademarke,
        )

    def _debugger_faden_bekannt(self, faden_id: int) -> None:
        if self._faden_id is None:
            self._faden_id = faden_id
            self._startaktionen_pruefen()

    def _editoren_halt_melden(self, haelt: bool) -> None:
        for index in range(self.editor_tabs.count()):
            widget = self._tab_inhalt(self.editor_tabs.widget(index))
            if isinstance(widget, QuelltextEditor):
                widget.debugger_haelt = haelt

    def _debugger_angehalten(self, ereignis: dict) -> None:
        # Ein Haltepunkt vor dem ersten Fenster: das Programm lädt
        # nicht mehr, es wartet auf den nächsten Schritt.
        self._ladeanzeige_beenden()
        self._editoren_halt_melden(True)
        self._aktueller_thread_id = ereignis.get("threadId")
        if self._aktueller_thread_id is not None:
            self._faden_id = self._aktueller_thread_id
        self._startaktionen_pruefen()
        grund = ereignis.get("reason", "?")
        self._letzter_haltegrund = grund
        text = haltegrund_deutsch(grund)
        if self._erwarteter_halt is not None and self._erwarteter_halt[0] == grund:
            text = self._erwarteter_halt[1]
        self._erwarteter_halt = None
        self.statusBar().showMessage(f"Angehalten: {text}")
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
        waren. Ausgerechnet der Teil „Was“ und „Zu prüfen“ stand unter der
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
        self._ladeanzeige_beenden()
        self._aktueller_thread_id = None
        self._faden_id = None
        self._startaktionen_pruefen()
        self._letzter_aufrufstapel = []
        self.variablen_baum.clear()
        self.aufrufstapel_liste.clear()

    def _debugger_fehler(self, meldung: str) -> None:
        self._ladeanzeige_beenden()
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
        # Die globalen Variablen als eigener Zweig (Punkt 99). Auf der
        # obersten Ebene eines Programms sind lokale und globale
        # dieselben; dann entfällt der Zweig.
        globale = next((b for b in bereiche if b["name"] == "Globals"), None)
        if globale is not None and globale is not lokale and self._aktueller_frame_ist_funktion():
            self.debug_sitzung.variablen_lesen_fuer(globale["variablesReference"], "global")

    def _aktueller_frame_ist_funktion(self) -> bool:
        stapel = getattr(self, "_letzter_aufrufstapel", None) or []
        return bool(stapel) and stapel[0].get("name") != "<module>"

    def _debugger_variablen_bereit(self, variablen: list[dict]) -> None:
        self.variablen_baum.clear()
        self._variablen_zu_laden.clear()
        # debugpy stellt Gruppen wie „special variables“ und „function
        # variables“ an den Anfang: englisch, ohne Wert und für eine
        # Schülerin ohne Bedeutung. Die Tabelle begann bis 0.3.3 mit
        # dieser Zeile.
        variablen = [
            v for v in variablen if v.get("name") not in _DEBUGPY_GRUPPEN
        ]
        self._variablen_eintraege(self.variablen_baum, variablen)
        self._ueberwachte_auswerten()
        # Beim Bildschirmfoto gefunden: das Programm stand am
        # Breakpoint, die Variablen waren geladen - sichtbar blieb aber
        # das Panel „Meldungen“. „Als Tabelle anzeigen“ (und überhaupt
        # der Blick auf die Variablen) war nur nach einem
        # Reiterwechsel von Hand erreichbar. Nach einer unbehandelten
        # Ausnahme behält „Meldungen“ den Vorrang, dort steht die
        # Fehlermeldung aus dem Fehlerkatalog.
        if variablen and self._letzter_haltegrund != "exception":
            self.panels.setCurrentWidget(self.variablen_baum)
            # In der Grundaufteilung war nur eine Zeile zu sehen.
            self._panel_hoehe_sichern(min(len(variablen), 8) + 1)

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
        if self.debug_sitzung is not None and self._faden_id is not None:
            self.debug_sitzung.pausieren(self._faden_id)

    def _weiterlaufen(self) -> int | None:
        """Faden für einen Befehl, der das Programm weiterlaufen lässt,
        und ab jetzt „läuft“: bis zum nächsten Halt gelten die
        Schrittbefehle nicht mehr, „Pause“ schon. Bis 0.3.5 blieben die
        Schrittbefehle nach „Fortsetzen“ freigegeben."""
        faden = self._aktueller_thread_id
        if self.debug_sitzung is None or faden is None:
            return None
        self._editoren_halt_melden(False)
        self._aktueller_thread_id = None
        self._startaktionen_pruefen()
        return faden

    def _debugger_fortsetzen_aktion(self) -> None:
        faden = self._weiterlaufen()
        if faden is not None:
            self.debug_sitzung.fortsetzen(faden)

    def _debugger_bis_cursor_aktion(self) -> None:
        """„Start → Ausführen bis Cursor“ (F4, Punkt 78): läuft bis zur
        Zeile, in der der Cursor steht. Läuft noch kein Programm, wird
        es mit dem Debugger gestartet."""
        editor = self._aktueller_editor()
        pfad = editor.property(_PFAD_EIGENSCHAFT) if editor is not None else None
        if not pfad or not str(pfad).endswith(".py"):
            self.statusBar().showMessage(
                "„Ausführen bis Cursor“ braucht einen Cursor in einer Python-Datei des "
                "Projekts."
            )
            return
        zeile = editor.textCursor().blockNumber() + 1
        if self.debug_sitzung is None:
            self._mit_debugger_starten(halten_bei=(Path(pfad), zeile))
            return
        faden = self._weiterlaufen()
        if faden is not None:
            self.debug_sitzung.bis_cursor(Path(pfad), zeile, faden)

    def _debugger_stoppen_aktion(self) -> None:
        """„Start → Stopp“ (Umschalt+F5).

        Beendet beides: eine Debugger-Sitzung und ein mit Strg+F5
        gestartetes Programm. Vorher hing der Eintrag allein am
        Debugger – wer sein Programm mit Strg+F5 gestartet hatte, bekam
        von Natter sogar den Rat, es „über Start → Stopp“ zu beenden,
        und dort passierte dann nichts (M11, Abschnitt 5).
        """
        gestoppt = []
        self._ladeanzeige_beenden()
        if self.debug_sitzung is not None:
            self.debug_sitzung.beenden()
            self.debug_sitzung = None
            self._aktueller_thread_id = None
            self._faden_id = None
            self._startaktionen_pruefen()
            gestoppt.append("Debugger")
        if self.laufender_prozess is not None and self.laufender_prozess.poll() is None:
            prozessbaum_beenden(self.laufender_prozess)
            self._laufzeit_uhr.stop()
            # Was das Programm noch geschrieben hat, steht über der
            # Zeile zum Stopp.
            self._ausgabe_leser_beenden()
            self.ausgabe_zeile("Programm über „Start → Stopp“ beendet")
            self._start_zeitpunkt = None
            self.laufender_prozess = None
            gestoppt.append("Programm")
        elif self._programm_auftrag_beenden():
            # Das Programm ist schon zu Ende, aber ein Prozess, den es
            # gestartet hat, lief noch (Punkt 281).
            self.ausgabe_zeile(
                "Vom Programm gestartete Prozesse über „Start → Stopp“ beendet"
            )
            gestoppt.append("Programm")
        self._programm_auftrag_beenden()
        # Noch einmal nach dem Beenden: bis dahin konnte das Programm
        # die Markendatei noch anlegen.
        self._ladeanzeige_beenden()
        if not gestoppt:
            self.statusBar().showMessage("Es läuft gerade nichts, was sich stoppen ließe.")
            return
        self.statusBar().showMessage(f"{' und '.join(gestoppt)} gestoppt")

    def _debugger_einzelschritt_aktion(self) -> None:
        if self.debug_sitzung is None:
            self._schrittweise_starten("Einzelschritt")
            return
        faden = self._weiterlaufen()
        if faden is not None:
            self._erwarteter_halt = ("step", "nach einem Einzelschritt")
            self.debug_sitzung.einzelschritt(faden)

    def _debugger_prozedurschritt_aktion(self) -> None:
        if self.debug_sitzung is None:
            self._schrittweise_starten("Prozedurschritt")
            return
        faden = self._weiterlaufen()
        if faden is not None:
            self._erwarteter_halt = ("step", "nach einem Prozedurschritt")
            self.debug_sitzung.prozedurschritt(faden)

    def _schrittweise_starten(self, befehl: str) -> None:
        """F11 oder F10 ohne laufendes Programm (Punkt 295): startet es
        mit dem Debugger und hält in der ersten Zeile der Haupt-Unit.

        Bei einem Konsolenprojekt ist das die erste Zeile in `main()`,
        nicht `main.py`: dort ist nichts zu verfolgen, und die
        Anweisungen davor legen nur Funktionen an. Ohne Haupt-Unit oder
        ohne ausführbare Zeile darin hält das Programm in der ersten
        Zeile der Startdatei."""
        if self.projekt is None:
            self._mit_debugger_starten()
            return
        ziel = erste_zeile_der_haupt_unit(self.projekt)
        self._mit_debugger_starten(halten_bei=ziel)
        self._erwarteter_halt = ("breakpoint", "gleich zu Beginn des Programms")
        if self.debug_sitzung is not None:
            self.statusBar().showMessage(
                f"{befehl}: {self.projekt.name} läuft mit dem Debugger bis "
                f"{ziel[0].name}, Zeile {ziel[1]}. Mit F11 geht es Zeile "
                "für Zeile weiter, mit F10 über Aufrufe hinweg."
            )

    def _debugger_ruecksprung_aktion(self) -> None:
        faden = self._weiterlaufen()
        if faden is not None:
            self._erwarteter_halt = (
                "step", "nach der Rückkehr aus der Funktion"
            )
            self.debug_sitzung.bis_ruecksprung(faden)
