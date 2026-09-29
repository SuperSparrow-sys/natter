"""Datenbank-Panel (Abschnitt 10.2): eine SQLite-Datei öffnen,
Tabellen-/Spaltenbaum anzeigen, SQL-Abfragen ausführen und das Ergebnis
als Tabelle anzeigen; dazu „CSV in Datenbank importieren“ sowie Export
einer Tabelle als CSV oder SQL-Dump.

Seitdem gibt es hier keine Treiberauswahl und keine
Zugangsdaten mehr: Natter kennt nur noch SQLite (siehe den Modulkopf von
`pcl/components/data_access.py`). Eine Datenbankdatei braucht weder
Server noch Benutzer noch Passwort – und ein Passwortfeld, dessen Inhalt
irgendwo bleiben müsste, gibt es damit auch nicht mehr.

Das Panel arbeitet unmittelbar auf der `sqlite3`-Verbindung und nicht
über `SQLQuery`: es muss festschreiben, wann es will (Punkt 237),
eine Abfrage unterbrechen können (Punkt 239) und einen Import als
eine einzige Transaktion ausführen (Punkt 234).
"""

from __future__ import annotations

import csv
import math
import os
import re
import sqlite3
import tempfile
import time
from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import IO, Any

from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ide.pfade import dialog_startordner
from ide.viewers.csv_ansicht import csv_erkennen
from pcl import SQLite3Connection
from pcl.errors import NatterDatenbankError
from pcl.fehlerkatalog import _datenbankmeldung_eindeutschen
from pcl.zahlen import zahl

#: So viele Zeilen zeigt das Panel höchstens an. Eine rekursive
#: Abfrage ohne Abbruchbedingung liefert sonst Zeilen ohne Ende, und
#: jede Zelle wird ein eigenes Tabellenelement (Punkt 239).
HOECHSTZAHL_ZEILEN = 1000

#: Nach so vielen Sekunden bricht das Panel eine Abfrage selbst ab.
ZEITGRENZE_SEKUNDEN = 15.0

#: So viele Zeichen einer Zelle zeigt das Panel, dahinter steht „…“.
#: SQLite liefert von einem langen Text auch nur diese Zeichen und von
#: Binärdaten nur die Größe. Die Grenze von 1.000 Zeilen allein
#: begrenzte den Speicher nicht: 40 Zeilen mit je einem großen Text
#: und einem großen Binärwert belegten 3,8 GB (Punkt 257).
ZEICHEN_JE_ZELLE = 500

#: Mehr Zeichen holt das Panel für ein Ergebnis insgesamt nicht, auch
#: wenn die Zeilengrenze noch nicht erreicht ist (viele Spalten).
HOECHSTZAHL_ZEICHEN = 2_000_000

#: So viele Zeilen schreiben Import und Export am Stück. Dazwischen
#: kommt die Oberfläche zum Zug, und „Abbrechen“ wirkt (Punkt 258).
ZEILEN_JE_STAPEL = 2000


def _tabellenname_aus_dateiname(pfad: Path) -> str:
    name = Path(pfad).stem
    bereinigt = "".join(zeichen if zeichen.isalnum() else "_" for zeichen in name)
    return bereinigt or "import"


#: Eine ganze Zahl ohne führende Null. „01067“ ist eine Postleitzahl
#: oder Kennung und bleibt Text, sonst ginge die Null verloren.
_GANZZAHL = re.compile(r"[+-]?(0|[1-9]\d*)")

#: Beginnt ein Wert so, ist er eine Kennung wie „007“ oder „0341 …“,
#: auch wenn `zahl` ihn lesen könnte.
_FUEHRENDE_NULL = re.compile(r"[+-]?0\d")

#: Größer darf eine ganze Zahl in SQLite nicht werden. Längere
#: Ziffernfolgen (Kontonummern, Kennungen) bleiben Text.
_GROESSTE_GANZZAHL = 2**63 - 1


def _zahlenart(wert: str) -> str | None:
    """„INTEGER“ oder „REAL“, wenn `wert` (nicht leer, ohne Rand)
    eine ganze Zahl bzw. eine Kommazahl ist, sonst ``None``.
    Kommazahlen liest `pcl.zahlen.zahl`, also mit Dezimalkomma wie
    mit Dezimalpunkt."""
    if _GANZZAHL.fullmatch(wert):
        if abs(int(wert)) > _GROESSTE_GANZZAHL:
            return None
        return "INTEGER"
    if _FUEHRENDE_NULL.match(wert):
        return None
    try:
        zahl(wert)
    except ValueError:
        return None
    return "REAL"


def _spaltentyp(bisher: str | None, wert: str) -> str | None:
    """Der Typ einer Spalte, nachdem `wert` dazugekommen ist.
    ``None`` heißt: noch kein Wert gesehen. Leere Felder ändern
    nichts. Ganze und Kommazahlen gemischt ergeben REAL, alles
    andere TEXT."""
    if bisher == "TEXT":
        return bisher
    wert = wert.strip()
    if not wert:
        return bisher
    art = _zahlenart(wert)
    if art is None:
        return "TEXT"
    if bisher == "REAL" or art == "REAL":
        return "REAL"
    return "INTEGER"


def _umwandler(typ: str) -> Callable[[str], Any]:
    """Wandelt ein Feld für eine Spalte vom Typ `typ` um. In
    Zahlenspalten wird ein leeres Feld NULL, in Textspalten bleibt
    es der leere Text."""
    if typ == "INTEGER":
        return lambda wert: int(wert) if wert.strip() else None
    if typ == "REAL":
        return lambda wert: zahl(wert) if wert.strip() else None
    return lambda wert: wert


def bezeichner(name: str) -> str:
    """Setzt einen Tabellen- oder Spaltennamen in doppelte
    Anführungszeichen und verdoppelt jedes darin (Punkt 241). Ohne
    das Verdoppeln scheiterte eine Tabelle `a"b` schon im Baum, und
    die Kopfzeile einer CSV-Datei bestimmte mit, welche Anweisung
    ausgeführt wird."""
    return '"' + str(name).replace('"', '""') + '"'


def _sql_literal(wert: Any) -> str:
    """Ein Wert als SQL-Literal für den Dump (Punkt 242). Binärdaten
    als `X'…'`, unendliche Zahlen als `1e999`, das SQLite beim Lesen
    wieder zu unendlich macht. NaN kennt SQLite nicht, es speichert
    dafür selbst NULL."""
    if wert is None:
        return "NULL"
    if isinstance(wert, bool):
        return str(int(wert))
    if isinstance(wert, int):
        return str(wert)
    if isinstance(wert, float):
        if math.isnan(wert):
            return "NULL"
        if math.isinf(wert):
            return "1e999" if wert > 0 else "-1e999"
        return repr(wert)
    if isinstance(wert, (bytes, bytearray, memoryview)):
        return f"X'{bytes(wert).hex().upper()}'"
    escaped = str(wert).replace("'", "''")
    return f"'{escaped}'"


def _csv_wert(wert: Any) -> Any:
    """Ein Wert für den CSV-Export: Binärdaten als Hexadezimaltext
    statt als `b'…'` (Punkt 242)."""
    if wert is None:
        return ""
    if isinstance(wert, (bytes, bytearray, memoryview)):
        return bytes(wert).hex().upper()
    return wert


def _anzeigetext(wert: Any) -> str:
    """Text einer Zelle in der Ergebnistabelle - dieselbe Darstellung
    wie in den Data Controls (Punkt 246)."""
    from pcl.components.data_access import anzeigetext

    return anzeigetext(wert)


def _zahl(wert: float) -> str:
    return f"{wert:g}".replace(".", ",")


def _ganzzahl(wert: int) -> str:
    """Eine Anzahl mit Punkt als Tausendertrenner: „120.000“."""
    return f"{wert:,}".replace(",", ".")


def _gekuerzt(text: str) -> tuple[str, bool]:
    if len(text) > ZEICHEN_JE_ZELLE:
        return text[:ZEICHEN_JE_ZELLE] + "…", True
    return text, False


def _rumpf(sql: str) -> str:
    """Die Anweisung ohne Leerraum und Semikolon am Ende, damit sie
    sich in eine äußere Abfrage einsetzen lässt."""
    rumpf = sql.strip()
    while rumpf.endswith(";"):
        rumpf = rumpf[:-1].rstrip()
    return rumpf


def _beginnt_transaktion(sql: str) -> bool:
    """Wahr, wenn `sql` mit ``BEGIN`` oder ``SAVEPOINT`` beginnt."""
    worte = sql.lstrip().split(None, 1)
    return bool(worte) and worte[0].rstrip(";").upper() in (
        "BEGIN",
        "SAVEPOINT",
    )


def _doppelnamen_zuruecknehmen(spalten: list[str]) -> list[str]:
    """Nimmt die Nachsilbe „:1“, „:2“ … zurück, die SQLite in einer
    Unterabfrage an doppelte Spaltennamen hängt. Ein JOIN zweier
    Tabellen mit `id` und `name` zeigte sonst „id:1“ und „name:1“,
    Namen, die in keiner Tabelle stehen (Punkt 269). Eine echte
    Spalte „x:1“ ohne ein „x“ davor bleibt, wie sie heißt."""
    ergebnis: list[str] = []
    for name in spalten:
        basis, trenner, nummer = name.rpartition(":")
        if trenner and nummer.isdigit() and basis in ergebnis:
            name = basis
        ergebnis.append(name)
    return ergebnis


def _kurze_abfrage(rumpf: str, anzahl: int) -> str:
    """Setzt eine Abfrage mit `anzahl` Spalten in eine äußere ein, die
    je Spalte den Typ und einen kurzen Wert liefert: von einem Text
    die ersten Zeichen, von Binärdaten nur die Größe. Den langen Wert
    hält dann nur SQLite kurz im Speicher, nie das Panel. Die neuen
    Spaltennamen `s0`, `s1` … sind nötig, weil ein Ergebnis zwei
    gleichnamige oder namenlose Spalten haben darf."""
    namen = [f"s{nummer}" for nummer in range(anzahl)]
    ausdruecke = []
    for name in namen:
        ausdruecke.append(f"typeof({name})")
        ausdruecke.append(
            f"CASE typeof({name}) "
            f"WHEN 'text' THEN substr({name}, 1, {ZEICHEN_JE_ZELLE + 1}) "
            f"WHEN 'blob' THEN length({name}) ELSE {name} END"
        )
    return (
        f"WITH natter_ergebnis({', '.join(namen)}) AS (\n{rumpf}\n) "
        f"SELECT {', '.join(ausdruecke)} FROM natter_ergebnis"
    )


def _kurze_zeile(roh: tuple[Any, ...]) -> tuple[list[str], bool]:
    """Anzeigetexte einer Zeile aus `_kurze_abfrage`, dazu, ob ein
    Text gekürzt wurde."""
    from pcl.components.data_access import anzeigetext, binaertext

    texte: list[str] = []
    gekuerzt = False
    for typ, wert in zip(roh[::2], roh[1::2], strict=True):
        if typ == "blob":
            texte.append(binaertext(int(wert)))
            continue
        text, kurz = _gekuerzt(anzeigetext(wert))
        texte.append(text)
        gekuerzt = gekuerzt or kurz
    return texte, gekuerzt


def _volle_zeile(roh: tuple[Any, ...]) -> tuple[list[str], bool]:
    """Anzeigetexte einer Zeile, die SQLite vollständig geliefert hat
    (Anweisungen, die sich nicht einsetzen lassen, etwa PRAGMA)."""
    texte: list[str] = []
    gekuerzt = False
    for wert in roh:
        text, kurz = _gekuerzt(_anzeigetext(wert))
        texte.append(text)
        gekuerzt = gekuerzt or kurz
    return texte, gekuerzt


@contextmanager
def _zieldatei(ziel: Path, **oeffnen: Any) -> Iterator[IO[str]]:
    """Schreibt zuerst in eine Hilfsdatei daneben und ersetzt `ziel`
    erst, wenn alles geschrieben ist. Nach einem Abbruch oder Fehler
    bleibt so keine halbe Datei liegen (Punkt 258); eine vorhandene
    Datei gleichen Namens bleibt dann, wie sie war."""
    ziel = Path(ziel)
    griff, name = tempfile.mkstemp(
        dir=ziel.parent, prefix=f"~{ziel.stem}-", suffix=".tmp"
    )
    os.close(griff)
    zwischen = Path(name)
    try:
        with open(zwischen, "w", **oeffnen) as datei:
            yield datei
        os.replace(zwischen, ziel)
    except BaseException:
        zwischen.unlink(missing_ok=True)
        raise


def _fehlertext(fehler: BaseException) -> str:
    """Deutsche Fassung einer Meldung von `sqlite3`, soweit der
    Fehlerkatalog von `pcl` sie kennt (Punkt 240). Das Schülerprogramm
    bekommt für denselben Fehler dieselben Worte."""
    text = str(fehler)
    if isinstance(fehler, sqlite3.Error) and not text.startswith("SQL-Fehler"):
        text = f"SQL-Fehler: {text}"
    return _datenbankmeldung_eindeutschen(text)


class _Abbruch(Exception):
    """Die Abfrage wurde über den Knopf oder die Zeitgrenze
    unterbrochen."""


def transaktion_nachfragen(eltern: QWidget, text: str, frage: str) -> str:
    """Fragt, was mit einer offenen Transaktion im Datenbank-Panel
    geschehen soll, mit den Knöpfen „Festschreiben“, „Zurücknehmen“
    und „Abbrechen“. Liefert `"festschreiben"`, `"zuruecknehmen"` oder
    `"abbrechen"`.

    Gemeinsam für den Start eines Programms (Punkt 276) und für
    „Verbinden“ und „Trennen“ im Panel (Punkt 279)."""
    box = QMessageBox(eltern)
    box.setIcon(QMessageBox.Icon.Question)
    box.setWindowTitle("Offene Transaktion")
    box.setText(text)
    box.setInformativeText(frage)
    festschreiben = box.addButton(
        "Festschreiben", QMessageBox.ButtonRole.AcceptRole
    )
    zuruecknehmen = box.addButton(
        "Zurücknehmen", QMessageBox.ButtonRole.DestructiveRole
    )
    box.addButton("Abbrechen", QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(festschreiben)
    box.exec()
    gewaehlt = box.clickedButton()
    if gewaehlt is festschreiben:
        return "festschreiben"
    if gewaehlt is zuruecknehmen:
        return "zuruecknehmen"
    return "abbrechen"


#: Breiteste Spalte der Ergebnistabelle nach dem Füllen, in Pixeln.
_SPALTE_HOECHSTENS = 320


class DatenbankPanel(QWidget):
    #: Einzeln änderbar, damit Tests nicht fünfzehn Sekunden warten.
    zeitgrenze_sekunden: float = ZEITGRENZE_SEKUNDEN

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._verbindung: SQLite3Connection | None = None
        self._projektordner: Path | None = None
        self._laeuft = False
        self._abbrechen_gewuenscht = False
        self._trennen_vorgemerkt = False
        self._abfrage_start = 0.0
        self._letzte_ereignisse = 0.0
        self._abbruchgrund = ""
        self._abbruchtext = ""
        self._zeitgrenze_gilt = True
        #: Wahr, solange eine im Panel mit BEGIN oder SAVEPOINT
        #: begonnene Transaktion offen ist (Punkt 266).
        self._transaktion_offen = False

        self._sqlite_pfad = QLineEdit()
        self._sqlite_pfad.setPlaceholderText("Datenbankdatei oder :memory:")
        self._sqlite_datei_waehlen_knopf = QPushButton("Datei wählen …")
        self._sqlite_datei_waehlen_knopf.clicked.connect(self._sqlite_datei_waehlen)
        self._sqlite_widget = QWidget()
        sqlite_layout = QHBoxLayout(self._sqlite_widget)
        sqlite_layout.setContentsMargins(0, 0, 0, 0)
        sqlite_layout.addWidget(self._sqlite_pfad)
        sqlite_layout.addWidget(self._sqlite_datei_waehlen_knopf)

        self._verbinden_knopf = QPushButton("Verbinden")
        self._verbinden_knopf.clicked.connect(self._verbinden)
        # Ohne „Trennen“ blieb die Datei bis zum Beenden von Natter
        # offen, und Windows ließ sie weder löschen noch den
        # Projektordner umbenennen (Punkt 244).
        self._trennen_knopf = QPushButton("Trennen")
        self._trennen_knopf.setToolTip(
            "Die Verbindung schließen und die Datenbankdatei freigeben"
        )
        self._trennen_knopf.clicked.connect(self._trennen_geklickt)
        self._trennen_knopf.setEnabled(False)
        self._status_label = QLabel("Nicht verbunden")
        self._status_label.setWordWrap(True)

        verbindungs_zeile = QHBoxLayout()
        verbindungs_zeile.addWidget(self._sqlite_widget, 1)
        verbindungs_zeile.addWidget(self._verbinden_knopf)
        verbindungs_zeile.addWidget(self._trennen_knopf)

        self._tabellenbaum = QTreeWidget()
        self._tabellenbaum.setHeaderLabels(["Tabellen/Spalten"])
        # Breit genug für die Überschrift und übliche Namen wie
        # „kunden“ oder „geburtsdatum“. Vorher schnitt die Aufteilung
        # Tabellen- und Spaltennamen nach wenigen Buchstaben ab
        # (Punkt 303).
        self._tabellenbaum.setMinimumWidth(
            self._tabellenbaum.fontMetrics().horizontalAdvance(
                "Tabellen/Spalten"
            )
            + 48
        )

        self._sql_eingabe = QPlainTextEdit()
        self._sql_eingabe.setPlaceholderText("SELECT * FROM ...")
        self._ausfuehren_knopf = QPushButton("Ausführen")
        self._ausfuehren_knopf.clicked.connect(self._sql_ausfuehren)
        self._abbrechen_knopf = QPushButton("Abbrechen")
        self._abbrechen_knopf.setToolTip(
            "Die laufende Abfrage, den Import oder den Export abbrechen"
        )
        self._abbrechen_knopf.clicked.connect(self.abfrage_abbrechen)
        self._abbrechen_knopf.setEnabled(False)
        # Die beiden Knöpfe stehen rechts neben dem SQL-Feld statt in
        # einer eigenen Zeile darunter: die Zeile ging der
        # Ergebnistabelle ab, die auf 1280 × 800 nur noch eine
        # einzige Zeile zeigte (Punkt 303).
        ausfuehren_spalte = QVBoxLayout()
        ausfuehren_spalte.addWidget(self._ausfuehren_knopf)
        ausfuehren_spalte.addWidget(self._abbrechen_knopf)
        ausfuehren_spalte.addStretch(1)
        self._sql_eingabe.setMinimumHeight(
            self._sql_eingabe.fontMetrics().lineSpacing() * 2 + 12
        )
        ausfuehren_zeile = QHBoxLayout()
        ausfuehren_zeile.addWidget(self._sql_eingabe, 1)
        ausfuehren_zeile.addLayout(ausfuehren_spalte)
        self._ergebnis_tabelle = QTableWidget()
        # Zeilen so hoch wie die Schrift und etwas Luft. Die
        # Voreinstellung des Stils lag bei 30 Pixeln je Zeile.
        self._ergebnis_tabelle.verticalHeader().setDefaultSectionSize(
            self._ergebnis_tabelle.fontMetrics().lineSpacing() + 8
        )

        # Kurze Beschriftungen, der ganze Satz steht als Kurzhinweis
        # daneben: die drei langen Namen nebeneinander gaben dem Dock
        # eine Mindestbreite, mit der auf einem 1366-Pixel-Bildschirm
        # für die Panels daneben kaum noch etwas übrig blieb (M11,
        # Abschnitt 4).
        self._csv_importieren_knopf = QPushButton("CSV importieren …")
        self._csv_importieren_knopf.setToolTip(
            "Eine CSV-Datei als neue Tabelle in die Datenbank übernehmen"
        )
        self._csv_importieren_knopf.clicked.connect(self._csv_importieren_dialog)
        self._csv_exportieren_knopf = QPushButton("CSV exportieren …")
        self._csv_exportieren_knopf.setToolTip(
            "Die gewählte Tabelle als CSV-Datei speichern (z. B. für Excel)"
        )
        self._csv_exportieren_knopf.clicked.connect(self._csv_exportieren_dialog)
        self._sql_dump_exportieren_knopf = QPushButton("SQL-Dump …")
        self._sql_dump_exportieren_knopf.setToolTip(
            "Die gewählte Tabelle als SQL-Datei speichern – CREATE TABLE und INSERTs, "
            "mit denen sie sich anderswo wieder anlegen lässt"
        )
        self._sql_dump_exportieren_knopf.clicked.connect(self._sql_dump_exportieren_dialog)
        # Die drei Knöpfe stehen unter dem Tabellenbaum, auf den sie
        # sich beziehen. Als Zeile unter der Ergebnistabelle nahmen sie
        # ihr noch einmal eine Zeilenhöhe weg (Punkt 303).
        linke_seite = QVBoxLayout()
        linke_seite.setContentsMargins(0, 0, 0, 0)
        linke_seite.addWidget(self._tabellenbaum, 1)
        linke_seite.addWidget(self._csv_importieren_knopf)
        linke_seite.addWidget(self._csv_exportieren_knopf)
        linke_seite.addWidget(self._sql_dump_exportieren_knopf)
        linkes_widget = QWidget()
        linkes_widget.setLayout(linke_seite)

        # Die Rückmeldung („2 Zeilen.“, eine Fehlermeldung) steht
        # direkt über der Ergebnistabelle. Rechts oben neben „Trennen“
        # war sie weit weg vom SQL-Feld, auf das sie sich bezieht
        # (Punkt 303).
        rechte_seite = QVBoxLayout()
        rechte_seite.setContentsMargins(0, 0, 0, 0)
        rechte_seite.addLayout(ausfuehren_zeile, 1)
        rechte_seite.addWidget(self._status_label)
        rechte_seite.addWidget(self._ergebnis_tabelle, 4)
        rechtes_widget = QWidget()
        rechtes_widget.setLayout(rechte_seite)

        aufteilung = QSplitter()
        aufteilung.addWidget(linkes_widget)
        aufteilung.addWidget(rechtes_widget)
        aufteilung.setStretchFactor(0, 0)
        aufteilung.setStretchFactor(1, 1)
        aufteilung.setChildrenCollapsible(False)

        layout = QVBoxLayout(self)
        layout.addLayout(verbindungs_zeile)
        layout.addWidget(aufteilung)

        # Knöpfe, die während einer laufenden Abfrage ruhen: die
        # Verbindung ist dann belegt.
        self._belegte_knoepfe = (
            self._verbinden_knopf,
            self._trennen_knopf,
            self._ausfuehren_knopf,
            self._csv_importieren_knopf,
            self._csv_exportieren_knopf,
            self._sql_dump_exportieren_knopf,
            self._sqlite_datei_waehlen_knopf,
        )

    @property
    def verbindung(self) -> SQLite3Connection | None:
        return self._verbindung

    @property
    def tabellenbaum(self) -> QTreeWidget:
        return self._tabellenbaum

    @property
    def ergebnis_tabelle(self) -> QTableWidget:
        return self._ergebnis_tabelle

    @property
    def laeuft(self) -> bool:
        """Wahr, solange eine Abfrage, ein Import oder ein Export
        läuft."""
        return self._laeuft

    # -- Verbindung ----------------------------------------------------

    def projektordner_setzen(self, ordner: Path | None) -> None:
        """Beim Öffnen oder Wechseln eines Projekts: die Verbindung zum
        alten Projekt geht zu, und ein Dateiname ohne Pfad wird ab
        jetzt im neuen Projektordner gesucht (Punkt 244)."""
        self.trennen()
        self._projektordner = Path(ordner) if ordner is not None else None

    def _sqlite_datei_waehlen(self) -> None:
        pfad, _ = QFileDialog.getOpenFileName(
            self,
            "Datenbankdatei wählen",
            str(dialog_startordner(self._projektordner)),
            "SQLite-Datenbanken (*.sqlite *.sqlite3 *.db);;Alle Dateien (*)",
        )
        if pfad:
            self._sqlite_pfad.setText(pfad)

    def _pfad_aufloesen(self, text: str) -> Path:
        """Ein Dateiname ohne Pfad gilt im Projektordner, so wie ihn
        das Schülerprogramm benutzt. Vorher landete er im Arbeitsordner
        von Natter, in der installierten Fassung also im
        Programmordner."""
        pfad = Path(text).expanduser()
        if not pfad.is_absolute() and self._projektordner is not None:
            pfad = self._projektordner / pfad
        return pfad.absolute()

    def _datei_anlegen_fragen(self, pfad: Path) -> bool:
        """Eigene Methode, damit Tests die Antwort vorgeben können."""
        antwort = QMessageBox.question(
            self,
            "Datenbank anlegen",
            f"Die Datei „{pfad.name}“ gibt es in {pfad.parent} nicht.\n\n"
            "Eine neue, leere Datenbank unter diesem Namen anlegen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return antwort == QMessageBox.StandardButton.Yes

    def _verbinden(self) -> None:
        if self._laeuft:
            return
        if not self._offene_transaktion_klaeren("verbinden"):
            return
        # Die vorige Verbindung geht in jedem Fall zu, auch wenn die
        # neue scheitert (Punkt 244).
        self.trennen()
        text = self._sqlite_pfad.text().strip() or ":memory:"
        if text == ":memory:":
            ziel = text
        else:
            pfad = self._pfad_aufloesen(text)
            if not pfad.parent.is_dir():
                self._status_label.setText(
                    f"Verbindung fehlgeschlagen: den Ordner {pfad.parent} "
                    "gibt es nicht."
                )
                return
            if pfad.is_dir():
                self._status_label.setText(
                    f"Verbindung fehlgeschlagen: {pfad} ist ein Ordner."
                )
                return
            # Ein Tippfehler im Namen legte vorher still eine leere
            # Datenbank an, und das Panel meldete „Verbunden“.
            if not pfad.exists() and not self._datei_anlegen_fragen(pfad):
                self._status_label.setText("Nicht verbunden.")
                return
            ziel = str(pfad)

        verbindung = SQLite3Connection()
        verbindung.database_name = ziel
        try:
            verbindung.connected = True
            # SQLite liest die Datei erst bei der ersten Abfrage. Eine
            # umbenannte Textdatei fiel vorher erst im Tabellenbaum
            # auf, als Ausnahme aus dem Knopf heraus (Punkt 240).
            verbindung.verbindung.execute(
                "SELECT count(*) FROM sqlite_master"
            ).fetchall()
        except NatterDatenbankError as fehler:
            # Der Text von `pcl` sagt schon „Verbindung … fehlgeschlagen“.
            verbindung.connected = False
            self._status_label.setText(_fehlertext(fehler))
            return
        except sqlite3.Error as fehler:
            verbindung.connected = False
            self._status_label.setText(
                f"Verbindung fehlgeschlagen: {_fehlertext(fehler)}"
            )
            return

        self._verbindung = verbindung
        self._trennen_knopf.setEnabled(True)
        self._status_label.setText("Verbunden")
        self._tabellenbaum_aktualisieren()

    def trennen(self) -> None:
        """Schließt die Verbindung und gibt die Datei frei. Läuft gerade
        eine Abfrage, wird sie abgebrochen und die Verbindung danach
        geschlossen."""
        if self._laeuft:
            self._trennen_vorgemerkt = True
            self._abbrechen_gewuenscht = True
            return
        if self._verbindung is None:
            return
        zurueckgenommen = self.transaktion_offen
        if zurueckgenommen:
            self._zuruecknehmen(self._verbindung.verbindung)
        self._transaktion_offen = False
        self._verbindung.connected = False
        self._verbindung = None
        self._tabellenbaum.clear()
        self._ergebnis_tabelle.clear()
        self._ergebnis_tabelle.setRowCount(0)
        self._ergebnis_tabelle.setColumnCount(0)
        self._trennen_knopf.setEnabled(False)
        if zurueckgenommen:
            self._status_label.setText(
                "Nicht verbunden. Die offene Transaktion wurde "
                "zurückgenommen."
            )
        else:
            self._status_label.setText("Nicht verbunden")

    def _trennen_geklickt(self) -> None:
        """Der Knopf „Trennen“. Anders als `trennen()`, das Natter
        selbst beim Projektwechsel und beim Schließen ruft, fragt er
        bei offener Transaktion vorher nach."""
        if not self._laeuft and not self._offene_transaktion_klaeren(
            "trennen"
        ):
            return
        self.trennen()

    def _offene_transaktion_klaeren(self, vorhaben: str) -> bool:
        """Liefert, ob „Verbinden“ oder „Trennen“ (`vorhaben`)
        weitergehen darf (Punkt 279).

        Beide schließen die bisherige Verbindung, und eine offene
        Transaktion wäre damit zurückgenommen. Bis 0.3.6 geschah das
        ohne Nachfrage; nach „Verbinden“ stand in der Statuszeile nur
        „Verbunden“, und die Änderungen seit BEGIN waren verloren.
        Ohne offene Transaktion ändert sich nichts."""
        if not self.transaktion_offen:
            return True
        antwort = self._transaktion_fragen(vorhaben)
        if antwort == "festschreiben":
            return self.transaktion_festschreiben() is None
        if antwort == "zuruecknehmen":
            self.transaktion_zuruecknehmen()
            return True
        nicht = "Nicht getrennt" if vorhaben == "trennen" else "Nicht verbunden"
        self._status_label.setText(
            f"{nicht} - die Transaktion ist weiter offen. COMMIT "
            "schreibt sie fest, ROLLBACK nimmt sie zurück."
        )
        return False

    def _transaktion_fragen(self, vorhaben: str) -> str:
        """Eigene Methode, damit Tests die Antwort vorgeben können."""
        wort = vorhaben.capitalize()
        return transaktion_nachfragen(
            self,
            "Im Datenbank-Panel ist noch eine Transaktion offen. Beim "
            f"{wort} geht die bisherige Verbindung zu, und was seit "
            "BEGIN geändert wurde, wäre verloren.",
            f"Vor dem {wort} festschreiben oder zurücknehmen?",
        )

    @property
    def transaktion_offen(self) -> bool:
        """Wahr, solange eine im Panel mit ``BEGIN`` oder
        ``SAVEPOINT`` begonnene Transaktion auf ``COMMIT`` oder
        ``ROLLBACK`` wartet."""
        return self._transaktion_offen and self._verbindung is not None

    def transaktion_festschreiben(self) -> str | None:
        """Schreibt die offene Transaktion fest, wie ``COMMIT`` im
        Panel. Liefert `None` oder, wenn es scheitert, den Grund.

        Für die Nachfrage vor dem Start eines Programms und vor dem
        Schließen (Punkt 276): solange die Transaktion offen ist, hält
        das Panel die Sperre auf der Datei, und das Programm wartet
        vergeblich darauf."""
        if not self.transaktion_offen:
            return None
        if self._laeuft:
            return "Im Datenbank-Panel läuft noch eine Abfrage."
        verbindung = self._roh()
        try:
            verbindung.commit()
        except sqlite3.Error as fehler:
            grund = _fehlertext(fehler)
            self._status_label.setText(grund)
            return grund
        self._transaktion_offen = verbindung.in_transaction
        self._status_label.setText("Die Transaktion ist festgeschrieben.")
        return None

    def transaktion_zuruecknehmen(self) -> None:
        """Nimmt die offene Transaktion zurück, wie ``ROLLBACK`` im
        Panel. Die Verbindung bleibt bestehen."""
        if not self.transaktion_offen or self._laeuft:
            return
        self._zuruecknehmen(self._roh())
        self._transaktion_offen = False
        self._status_label.setText("Die Transaktion ist zurückgenommen.")

    def _roh(self) -> sqlite3.Connection:
        if self._verbindung is None:
            raise NatterDatenbankError("Keine offene Datenbankverbindung.")
        return self._verbindung.verbindung

    def _tabellenbaum_aktualisieren(self) -> None:
        self._tabellenbaum.clear()
        if self._verbindung is None:
            return
        try:
            tabellen = [
                (tabelle, self._spaltennamen(tabelle))
                for tabelle in self._tabellennamen()
            ]
        except (NatterDatenbankError, sqlite3.Error) as fehler:
            self._status_label.setText(_fehlertext(fehler))
            return
        for tabelle, spalten in tabellen:
            eintrag = QTreeWidgetItem([tabelle])
            for spalte in spalten:
                eintrag.addChild(QTreeWidgetItem([spalte]))
            self._tabellenbaum.addTopLevelItem(eintrag)
        self._tabellenbaum.expandAll()

    def _tabellennamen(self) -> list[str]:
        """Die Tabellen ohne die internen von SQLite. `sqlite_sequence`
        legt SQLite selbst an, sobald eine Tabelle `AUTOINCREMENT`
        hat; im Baum lud sie zu einem Dump ein, der sich nicht wieder
        einspielen ließ (Punkt 262)."""
        zeilen = self._roh().execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' "
            "AND name NOT LIKE 'sqlite\\_%' ESCAPE '\\' ORDER BY name"
        ).fetchall()
        return [str(zeile[0]) for zeile in zeilen]

    def _spaltennamen(self, tabelle: str) -> list[str]:
        # PRAGMA kennt keine Platzhalter für den Tabellennamen.
        zeilen = self._roh().execute(
            f"PRAGMA table_info({bezeichner(tabelle)})"
        ).fetchall()
        return [str(zeile[1]) for zeile in zeilen]

    # -- Abfragen ------------------------------------------------------

    def abfrage_abbrechen(self) -> None:
        if self._laeuft:
            self._abbrechen_gewuenscht = True

    def _fortschritt(self) -> int:
        """Läuft alle paar tausend Schritte von SQLite. Lässt die
        Oberfläche Ereignisse abarbeiten, damit Natter bedienbar
        bleibt und „Abbrechen“ ankommt, und bricht nach der Zeitgrenze
        ab. Ein Wert ungleich 0 unterbricht die Abfrage."""
        jetzt = time.monotonic()
        if jetzt - self._letzte_ereignisse >= 0.05:
            self._letzte_ereignisse = jetzt
            QApplication.processEvents()
        if self._abbrechen_gewuenscht:
            self._abbruchgrund = self._abbruchtext
            return 1
        if (
            self._zeitgrenze_gilt
            and jetzt - self._abfrage_start > self.zeitgrenze_sekunden
        ):
            grenze = self.zeitgrenze_sekunden
            einheit = "Sekunde" if grenze == 1 else "Sekunden"
            self._abbruchgrund = (
                f"Die Abfrage lief länger als {_zahl(grenze)} {einheit} "
                "und wurde abgebrochen. Eine rekursive Abfrage braucht "
                "eine Abbruchbedingung, ein großes Ergebnis ein LIMIT."
            )
            return 1
        return 0

    def _laufen_lassen(self, laeuft: bool) -> None:
        self._laeuft = laeuft
        for knopf in self._belegte_knoepfe:
            knopf.setEnabled(not laeuft)
        if not laeuft:
            self._trennen_knopf.setEnabled(self._verbindung is not None)
        self._abbrechen_knopf.setEnabled(laeuft)

    @contextmanager
    def _vorgang(
        self, text: str, abbruchtext: str, *, zeitgrenze: bool = False
    ) -> Iterator[sqlite3.Connection]:
        """Rahmen für alles, was die Verbindung länger belegt: Abfrage,
        Import und Export. Die übrigen Knöpfe ruhen, „Abbrechen“ ist
        frei, und `_fortschritt` läuft während jeder Anweisung mit.
        Eine von `_fortschritt` unterbrochene Anweisung kommt als
        `_Abbruch` heraus.

        Bis Punkt 258 lief nur „Ausführen“ so. Ein Import von 2
        Millionen Zeilen hielt Natter 15 Sekunden lang an, ohne dass
        sich etwas abbrechen ließ. Die Zeitgrenze gilt nur für
        Abfragen: ein großer Import darf länger dauern."""
        if self._laeuft:
            raise NatterDatenbankError(
                "Im Datenbank-Panel läuft schon ein Vorgang."
            )
        verbindung = self._roh()
        self._abbrechen_gewuenscht = False
        self._abbruchgrund = ""
        self._abbruchtext = abbruchtext
        self._zeitgrenze_gilt = zeitgrenze
        self._abfrage_start = self._letzte_ereignisse = time.monotonic()
        self._laufen_lassen(True)
        self._status_label.setText(text)
        verbindung.set_progress_handler(self._fortschritt, 2000)
        try:
            yield verbindung
        except sqlite3.Error as fehler:
            if self._abbruchgrund:
                raise _Abbruch(self._abbruchgrund) from fehler
            raise
        finally:
            verbindung.set_progress_handler(None, 0)
            self._laufen_lassen(False)
            if self._trennen_vorgemerkt:
                self._trennen_vorgemerkt = False
                self.trennen()

    def _zwischenstand(self, text: str) -> None:
        """Zwischen zwei Stapeln eines Imports oder Exports: zeigt den
        Stand, lässt die Oberfläche zum Zug kommen und bricht ab, wenn
        „Abbrechen“ gedrückt wurde."""
        self._status_label.setText(text)
        if self._fortschritt():
            raise _Abbruch(self._abbruchgrund)

    @staticmethod
    def _zuruecknehmen(verbindung: sqlite3.Connection) -> None:
        """Rollt eine offene Transaktion zurück. Die Aufsicht geht
        vorher ab, sonst unterbräche ein noch gesetzter Abbruchwunsch
        auch das Zurückrollen."""
        verbindung.set_progress_handler(None, 0)
        if verbindung.in_transaction:
            verbindung.rollback()

    def _abfrage(
        self, sql: str
    ) -> tuple[list[str], list[list[str]], bool, bool, int]:
        """Führt `sql` unter Aufsicht von `_fortschritt` aus. Liefert
        Spalten, höchstens `HOECHSTZAHL_ZEILEN` Zeilen als
        Anzeigetexte, ob es mehr gab, ob Werte gekürzt sind, und die
        Zahl geänderter Zeilen.

        Ein ``BEGIN`` (oder ``SAVEPOINT``) öffnet eine Transaktion,
        die bis ``COMMIT`` oder ``ROLLBACK`` offen bleibt. Vorher
        schrieb das Panel sie sofort fest, und ein ``ROLLBACK`` nach
        ``BEGIN`` und ``DELETE`` nahm nichts mehr zurück (Punkt
        266)."""
        with self._vorgang(
            "Die Abfrage läuft …",
            "Die Abfrage wurde abgebrochen.",
            zeitgrenze=True,
        ) as verbindung:
            war_offen = verbindung.in_transaction
            try:
                ergebnis = self._abfrage_lesen(verbindung, sql)
                if (
                    not war_offen
                    and verbindung.in_transaction
                    and _beginnt_transaktion(sql)
                ):
                    self._transaktion_offen = True
                # Python öffnet vor INSERT, UPDATE und DELETE selbst
                # eine Transaktion. Blieb sie offen, hielt das Panel
                # die Schreibsperre, und das Schülerprogramm scheiterte
                # mit „database is locked“ (Punkt 237).
                if (
                    verbindung.in_transaction
                    and not self._transaktion_offen
                ):
                    verbindung.commit()
            except BaseException:
                # In einer mit BEGIN begonnenen Transaktion nimmt
                # SQLite nur die gescheiterte Anweisung zurück; über
                # den Rest entscheidet ROLLBACK oder COMMIT.
                if not self._transaktion_offen:
                    self._zuruecknehmen(verbindung)
                raise
            finally:
                self._transaktion_offen = (
                    self._transaktion_offen and verbindung.in_transaction
                )
        return ergebnis

    @staticmethod
    def _ergebnisspalten(
        verbindung: sqlite3.Connection, rumpf: str
    ) -> list[str] | None:
        """Die Spaltennamen, falls sich `rumpf` als Unterabfrage
        einsetzen lässt, sonst `None` (etwa bei INSERT oder PRAGMA).
        Mit `LIMIT 0` rechnet SQLite dabei keine einzige Zeile aus."""
        if not rumpf:
            return None
        try:
            cursor = verbindung.execute(
                f"SELECT * FROM (\n{rumpf}\n) LIMIT 0"
            )
        except sqlite3.Error:
            return None
        try:
            return _doppelnamen_zuruecknehmen(
                [b[0] for b in cursor.description or []]
            )
        finally:
            cursor.close()

    def _abfrage_lesen(
        self, verbindung: sqlite3.Connection, sql: str
    ) -> tuple[list[str], list[list[str]], bool, bool, int]:
        rumpf = _rumpf(sql)
        spalten = self._ergebnisspalten(verbindung, rumpf)
        if spalten:
            cursor = verbindung.execute(_kurze_abfrage(rumpf, len(spalten)))
            umwandeln = _kurze_zeile
        else:
            cursor = verbindung.execute(sql)
            spalten = [b[0] for b in cursor.description or []]
            umwandeln = _volle_zeile
        zeilen: list[list[str]] = []
        mehr = gekuerzt = False
        zeichen = 0
        try:
            while spalten:
                roh = cursor.fetchone()
                if roh is None:
                    break
                if (
                    len(zeilen) >= HOECHSTZAHL_ZEILEN
                    or zeichen >= HOECHSTZAHL_ZEICHEN
                ):
                    mehr = True
                    break
                texte, kurz = umwandeln(roh)
                zeichen += sum(len(text) for text in texte)
                gekuerzt = gekuerzt or kurz
                zeilen.append(texte)
            geaendert = cursor.rowcount
        finally:
            # Ein offener SELECT hielte eine Lesesperre auf der Datei.
            cursor.close()
        return spalten, zeilen, mehr, gekuerzt, geaendert

    def _sql_ausfuehren(self) -> None:
        if self._laeuft:
            return
        if self._verbindung is None:
            self._status_label.setText("Nicht verbunden.")
            return
        sql = self._sql_eingabe.toPlainText()
        war_offen = self._transaktion_offen
        try:
            spalten, zeilen, mehr, gekuerzt, geaendert = self._abfrage(sql)
        except _Abbruch as abbruch:
            self._status_setzen(str(abbruch), war_offen)
            return
        except (NatterDatenbankError, sqlite3.Error) as fehler:
            self._status_setzen(_fehlertext(fehler), war_offen)
            return
        except MemoryError:
            self._status_setzen(
                "Für dieses Ergebnis reicht der Arbeitsspeicher nicht. "
                "Mit LIMIT oder weniger Spalten wird es kleiner.",
                war_offen,
            )
            return
        if self._verbindung is None:
            return
        self._ergebnis_anzeigen(spalten, zeilen)
        if not spalten:
            if geaendert >= 0:
                status = (
                    "1 Zeile geändert." if geaendert == 1
                    else f"{_ganzzahl(geaendert)} Zeilen geändert."
                )
            else:
                status = "Ausgeführt."
            self._status_setzen(status, war_offen)
            self._tabellenbaum_aktualisieren()
            return
        if mehr:
            status = (
                f"Nur die ersten {_ganzzahl(len(zeilen))} Zeilen werden "
                "angezeigt."
            )
        else:
            status = (
                "1 Zeile." if len(zeilen) == 1
                else f"{_ganzzahl(len(zeilen))} Zeilen."
            )
        if gekuerzt:
            status += (
                f" Lange Texte sind nach {ZEICHEN_JE_ZELLE} Zeichen "
                "gekürzt."
            )
        self._status_setzen(status, war_offen)
        self._tabellenbaum_aktualisieren()

    def _status_setzen(self, text: str, war_offen: bool) -> None:
        """Zeigt `text` in der Statuszeile. Solange eine mit ``BEGIN``
        begonnene Transaktion offen ist, steht das dahinter: das Panel
        hält dann die Schreibsperre auf der Datei, und ein Programm,
        das dieselbe Datei beschreibt, wartet vergeblich."""
        if self.transaktion_offen:
            text += (
                " Transaktion offen: erst COMMIT schreibt die Änderungen "
                "fest, ROLLBACK nimmt sie zurück."
            )
        elif war_offen and self._verbindung is not None:
            text += " Die Transaktion ist beendet."
        self._status_label.setText(text)

    def _ergebnis_anzeigen(
        self, spalten: list[str], zeilen: list[list[str]]
    ) -> None:
        self._ergebnis_tabelle.clear()
        self._ergebnis_tabelle.setColumnCount(len(spalten))
        self._ergebnis_tabelle.setHorizontalHeaderLabels(spalten)
        self._ergebnis_tabelle.setRowCount(len(zeilen))
        for zeile_index, zeile in enumerate(zeilen):
            for spalten_index, text in enumerate(zeile):
                self._ergebnis_tabelle.setItem(
                    zeile_index, spalten_index, QTableWidgetItem(text)
                )
        # Jede Spalte mindestens so breit wie ihr Name (Punkt 303);
        # lange Werte begrenzt `_SPALTE_HOECHSTENS`, sonst schöbe ein
        # einziger langer Text alle übrigen Spalten aus dem Bild.
        kopf = self._ergebnis_tabelle.horizontalHeader()
        metrik = kopf.fontMetrics()
        # Gemessen werden nur die ersten hundert Zeilen; bei zehntausend
        # stünde das Panel sonst sichtbar still.
        kopf.setResizeContentsPrecision(100)
        self._ergebnis_tabelle.resizeColumnsToContents()
        for spalte, name in enumerate(spalten):
            breite = max(
                kopf.sectionSize(spalte),
                metrik.horizontalAdvance(name) + 24,
            )
            kopf.resizeSection(spalte, min(breite, _SPALTE_HOECHSTENS))

    # -- CSV-Import ----------------------------------------------------

    def _csv_importieren_dialog(self) -> None:
        """„CSV importieren …“ im Panel und „Werkzeuge → CSV in
        Datenbank importieren …“.

        Jeder Fehler kommt als Meldung. Bis 0.3.5 flogen „keine
        Verbindung“ und eine zu kurze CSV-Zeile als Ausnahme aus dem
        Menüeintrag heraus, und eine gleichnamige Tabelle war ohne
        Rückfrage weg (Punkt 138).
        """
        if self._laeuft:
            return
        if self._verbindung is None:
            self._meldung(
                "Es ist keine Datenbank verbunden. Zuerst im Datenbank-Panel "
                "eine Datei wählen und auf „Verbinden“ klicken."
            )
            return
        pfad, _ = QFileDialog.getOpenFileName(
            self,
            "CSV-Datei wählen",
            str(dialog_startordner(self._projektordner)),
            "CSV (*.csv)",
        )
        if not pfad:
            return
        name = _tabellenname_aus_dateiname(Path(pfad))
        ersetzen = False
        try:
            vorhanden = name in self._tabellennamen()
        except (NatterDatenbankError, sqlite3.Error) as fehler:
            self._meldung(_fehlertext(fehler))
            return
        if vorhanden:
            antwort = self._tabelle_ersetzen_fragen(name)
            if antwort == QMessageBox.StandardButton.Cancel:
                return
            ersetzen = antwort == QMessageBox.StandardButton.Yes
        try:
            tabelle = self.csv_importieren(Path(pfad), name, ersetzen=ersetzen)
        except _Abbruch as abbruch:
            self._status_label.setText(str(abbruch))
            return
        except (NatterDatenbankError, sqlite3.Error, OSError, UnicodeError,
                csv.Error) as fehler:
            self._meldung(
                "Die CSV-Datei ließ sich nicht importieren: "
                f"{_fehlertext(fehler)}"
            )
            return
        self._status_label.setText(f"„{Path(pfad).name}“ als Tabelle „{tabelle}“ importiert.")

    def _tabelle_ersetzen_fragen(self, name: str) -> QMessageBox.StandardButton:
        """Ja ersetzt die Tabelle, Nein legt eine neue unter freiem
        Namen an. Eigene Methode, damit Tests die Antwort vorgeben
        können."""
        return QMessageBox.question(
            self,
            "Tabelle vorhanden",
            f"Die Datenbank hat schon eine Tabelle „{name}“.\n\n"
            "„Ja“ ersetzt sie mitsamt ihren Daten durch den Inhalt der "
            f"CSV-Datei, „Nein“ legt eine neue Tabelle „{self._freier_name(name)}“ an.",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.No,
        )

    def _meldung(self, text: str, titel: str = "CSV importieren") -> None:
        """Steht im Panel und kommt als Fenster: der Menüeintrag unter
        „Werkzeuge“ geht auch bei geschlossenem Panel."""
        self._status_label.setText(text)
        QMessageBox.warning(self, titel, text)

    def _freier_name(self, name: str) -> str:
        vorhanden = {n.casefold() for n in self._tabellennamen()}
        if name.casefold() not in vorhanden:
            return name
        zaehler = 2
        while f"{name}_{zaehler}".casefold() in vorhanden:
            zaehler += 1
        return f"{name}_{zaehler}"

    def csv_importieren(
        self, pfad: Path, tabellenname: str | None = None, *, ersetzen: bool = False
    ) -> str:
        """Liest `pfad` in eine neue Tabelle ein (Abschnitt 11.6: „CSV in
        Datenbank importieren“, wiederverwendet die Erkennung aus
        `ide.viewers.csv_ansicht.csv_erkennen`). Liefert den
        verwendeten Tabellennamen.

        Eine vorhandene Tabelle gleichen Namens wird nur mit
        `ersetzen=True` gelöscht; sonst bekommt die neue einen freien
        Namen (`konten_2`). Zeilen mit weniger Feldern als die
        Kopfzeile werden mit leeren Werten aufgefüllt. Hat eine Zeile
        mehr Felder, wird sie mit Zeilennummer gemeldet, und es bleibt
        nichts vom Import zurück.

        Der ganze Import ist eine Transaktion (Punkt 234): die neue
        Tabelle entsteht unter einem Hilfsnamen, erst wenn alle Zeilen
        drin sind, geht die alte weg und die neue bekommt ihren Namen.
        Scheitert irgendein Schritt, bleibt die Datenbank, wie sie
        war. Vorher wurde jede Zeile einzeln festgeschrieben, und ein
        Fehler nach dem Löschen ließ gar keine Tabelle zurück.

        Die Datei wird zeilenweise gelesen und stapelweise geschrieben;
        zwischen den Stapeln bleibt Natter bedienbar, und „Abbrechen“
        rollt alles zurück (Punkt 258). Ein Abbruch kommt als
        `_Abbruch` heraus.

        Eine Spalte, deren Felder alle ganze Zahlen sind, wird als
        INTEGER angelegt, eine mit Kommazahlen (Komma oder Punkt) als
        REAL; leere Felder werden dort NULL. Alle übrigen Spalten
        bleiben TEXT (Punkt 288). Als TEXT verglich SQLite auch mit
        einer Zahl im SQL als Text: ``menge > 50`` fand „9“, und
        „0,5“ zählte in ``sum()`` als 0. Dafür wird die Datei zweimal
        gelesen, einmal für die Typen und einmal für die Zeilen."""
        if self.transaktion_offen:
            # Der Import schreibt am Ende fest und nähme die offene
            # Transaktion dabei mit.
            raise NatterDatenbankError(
                "Im Datenbank-Panel ist noch eine Transaktion offen. "
                "Vor dem Import mit COMMIT festschreiben oder mit "
                "ROLLBACK zurücknehmen."
            )
        pfad = Path(pfad)
        delimiter, encoding = csv_erkennen(pfad)
        tabellenname = tabellenname or _tabellenname_aus_dateiname(pfad)
        with open(pfad, encoding=encoding, newline="") as datei:
            leser = csv.reader(datei, delimiter=delimiter)
            kopf = next(leser, None)
            if kopf is None:
                raise NatterDatenbankError(f"{pfad} ist leer.")
            self._spalten_pruefen(kopf)
            if not ersetzen:
                tabellenname = self._freier_name(tabellenname)
            hilfsname = self._freier_name(f"{tabellenname}_natter_import")
            with self._vorgang(
                f"„{pfad.name}“ wird importiert …",
                "Der Import wurde abgebrochen. Die Datenbank ist "
                "unverändert.",
            ) as verbindung:
                typen = self._spaltentypen(
                    pfad, delimiter, encoding, len(kopf)
                )
                self._csv_einlesen(
                    verbindung, leser, kopf, tabellenname, hilfsname,
                    ersetzen=ersetzen, dateiname=pfad.name, typen=typen,
                )
        self._tabellenbaum_aktualisieren()
        return tabellenname

    def _csv_einlesen(
        self,
        verbindung: sqlite3.Connection,
        leser: Iterable[list[str]],
        kopf: list[str],
        tabellenname: str,
        hilfsname: str,
        *,
        ersetzen: bool,
        dateiname: str,
        typen: list[str],
    ) -> None:
        spalten_sql = ", ".join(
            f"{bezeichner(spalte)} {typ}"
            for spalte, typ in zip(kopf, typen, strict=True)
        )
        umwandler = [_umwandler(typ) for typ in typen]
        platzhalter = ", ".join("?" for _ in kopf)
        einfuegen = (
            f"INSERT INTO {bezeichner(hilfsname)} VALUES ({platzhalter})"
        )
        if verbindung.in_transaction:
            verbindung.commit()
        try:
            verbindung.execute("BEGIN")
            verbindung.execute(
                f"CREATE TABLE {bezeichner(hilfsname)} ({spalten_sql})"
            )
            stapel: list[list[Any]] = []
            anzahl = 0
            for nummer, zeile in enumerate(leser, start=2):
                if len(zeile) > len(kopf):
                    raise NatterDatenbankError(
                        f"Zeile {nummer} hat {len(zeile)} Felder, die "
                        f"Kopfzeile nur {len(kopf)}. Es wurde nichts "
                        "importiert."
                    )
                if not zeile:
                    continue
                zeile = zeile + [""] * (len(kopf) - len(zeile))
                stapel.append([
                    umwandeln(wert)
                    for umwandeln, wert in zip(umwandler, zeile, strict=True)
                ])
                if len(stapel) >= ZEILEN_JE_STAPEL:
                    verbindung.executemany(einfuegen, stapel)
                    anzahl += len(stapel)
                    stapel = []
                    self._zwischenstand(
                        f"„{dateiname}“ wird importiert … "
                        f"{_ganzzahl(anzahl)} Zeilen"
                    )
            if stapel:
                verbindung.executemany(einfuegen, stapel)
            if ersetzen:
                verbindung.execute(
                    f"DROP TABLE IF EXISTS {bezeichner(tabellenname)}"
                )
            # Beim Umbenennen prüft SQLite sonst alle Ansichten und
            # Trigger. Eine Ansicht auf die eben gelöschte Tabelle zeigt
            # in diesem Moment ins Leere, und „Ersetzen“ scheiterte mit
            # „error in view …“ (Punkt 261). Im alten Verfahren bleibt
            # die Ansicht beim Namen und sieht danach die neue Tabelle.
            verbindung.execute("PRAGMA legacy_alter_table = ON")
            try:
                verbindung.execute(
                    f"ALTER TABLE {bezeichner(hilfsname)} "
                    f"RENAME TO {bezeichner(tabellenname)}"
                )
            finally:
                verbindung.execute("PRAGMA legacy_alter_table = OFF")
            verbindung.commit()
        except BaseException:
            self._zuruecknehmen(verbindung)
            raise

    def _spaltentypen(
        self, pfad: Path, delimiter: str, encoding: str, anzahl: int
    ) -> list[str]:
        """Liest `pfad` einmal ganz und liefert je Spalte INTEGER,
        REAL oder TEXT (siehe `_spaltentyp`). Eine Spalte ohne einen
        einzigen Wert bleibt TEXT. Felder hinter der letzten Spalte
        zählen nicht, die meldet erst `_csv_einlesen`."""
        typen: list[str | None] = [None] * anzahl
        with open(pfad, encoding=encoding, newline="") as datei:
            leser = csv.reader(datei, delimiter=delimiter)
            next(leser, None)
            for nummer, zeile in enumerate(leser, start=1):
                for index, wert in enumerate(zeile[:anzahl]):
                    typen[index] = _spaltentyp(typen[index], wert)
                if nummer % ZEILEN_JE_STAPEL == 0:
                    self._zwischenstand(
                        f"„{pfad.name}“ wird geprüft … "
                        f"{_ganzzahl(nummer)} Zeilen"
                    )
        return [typ or "TEXT" for typ in typen]

    @staticmethod
    def _spalten_pruefen(kopf: list[str]) -> None:
        """Leere und doppelte Spaltennamen fallen vor dem Import auf,
        nicht erst an SQLite. Groß- und Kleinschreibung zählt dabei
        nicht, SQLite unterscheidet sie in Spaltennamen auch nicht."""
        gesehen: set[str] = set()
        for nummer, spalte in enumerate(kopf, start=1):
            if not spalte.strip():
                raise NatterDatenbankError(
                    f"Spalte {nummer} der Kopfzeile hat keinen Namen. "
                    "Es wurde nichts importiert."
                )
            schluessel = spalte.casefold()
            if schluessel in gesehen:
                raise NatterDatenbankError(
                    f"Die Spalte „{spalte}“ steht zweimal in der Kopfzeile. "
                    "Es wurde nichts importiert."
                )
            gesehen.add(schluessel)

    # -- Export --------------------------------------------------------

    def _csv_exportieren_dialog(self) -> None:
        self._exportieren_dialog(
            "CSV exportieren", "CSV (*.csv)", self.tabelle_als_csv_exportieren
        )

    def _sql_dump_exportieren_dialog(self) -> None:
        self._exportieren_dialog(
            "SQL-Dump exportieren", "SQL (*.sql)",
            self.tabelle_als_sql_dump_exportieren,
        )

    def _exportieren_dialog(
        self, titel: str, filter_: str, exportieren: Callable[[str, Path], None]
    ) -> None:
        if self._laeuft:
            return
        tabelle = self._ausgewaehlte_tabelle()
        if tabelle is None:
            self._status_label.setText("Keine Tabelle im Baum ausgewählt.")
            return
        pfad, _ = QFileDialog.getSaveFileName(
            self, titel, str(dialog_startordner(self._projektordner)), filter_
        )
        if not pfad:
            return
        try:
            exportieren(tabelle, Path(pfad))
        except _Abbruch as abbruch:
            self._status_label.setText(str(abbruch))
            return
        except (NatterDatenbankError, sqlite3.Error, OSError) as fehler:
            self._meldung(self._exportfehler(fehler, Path(pfad)), titel)
            return
        self._status_label.setText(f"„{tabelle}“ nach „{Path(pfad).name}“ exportiert.")

    @staticmethod
    def _exportfehler(fehler: BaseException, ziel: Path) -> str:
        if isinstance(fehler, PermissionError):
            return (
                f"„{ziel.name}“ lässt sich nicht schreiben. Ist die Datei "
                "in einem anderen Programm geöffnet, etwa in Excel, oder "
                "fehlt im Ordner das Schreibrecht?"
            )
        if isinstance(fehler, OSError):
            return f"„{ziel.name}“ lässt sich nicht schreiben: {fehler.strerror or fehler}"
        return f"Der Export ist gescheitert: {_fehlertext(fehler)}"

    def _zeilen_lesen(
        self, cursor: sqlite3.Cursor, text: str
    ) -> Iterator[tuple[Any, ...]]:
        """Die Zeilen eines Cursors, stapelweise geholt. Vorher lasen
        beide Exporte die ganze Tabelle auf einmal in den Speicher
        (Punkt 258)."""
        anzahl = 0
        while True:
            stapel = cursor.fetchmany(ZEILEN_JE_STAPEL)
            if not stapel:
                return
            yield from stapel
            anzahl += len(stapel)
            self._zwischenstand(f"{text} {_ganzzahl(anzahl)} Zeilen")

    def tabelle_als_csv_exportieren(self, tabelle: str, ziel: Path) -> None:
        """Schreibt mit BOM (Punkt 243): ohne sie liest Excel die Datei
        beim Doppelklick als Windows-1252 und zeigt Umlaute falsch.

        Läuft wie der Import stapelweise und lässt sich abbrechen; eine
        halbe Datei bleibt dabei nicht liegen (Punkt 258)."""
        text = f"„{tabelle}“ wird exportiert …"
        with (
            self._vorgang(text, "Der Export wurde abgebrochen.") as verbindung,
            _zieldatei(ziel, encoding="utf-8-sig", newline="") as datei,
        ):
            schreiber = csv.writer(datei, delimiter=";")
            cursor = verbindung.execute(f"SELECT * FROM {bezeichner(tabelle)}")
            try:
                schreiber.writerow([b[0] for b in cursor.description or []])
                for zeile in self._zeilen_lesen(cursor, text):
                    schreiber.writerow([_csv_wert(wert) for wert in zeile])
            finally:
                cursor.close()

    def tabelle_als_sql_dump_exportieren(self, tabelle: str, ziel: Path) -> None:
        """Schreibt `CREATE TABLE` und alle Zeilen als `INSERT` in einer
        Transaktion. So lässt sich der Dump in eine leere Datenbank
        einspielen (Punkt 242); vorher fehlte die Tabellendefinition.

        Berechnete Spalten (`GENERATED ALWAYS AS …`) fehlen in den
        `INSERT`-Zeilen: SQLite lehnt einen Wert für sie ab und rechnet
        sie beim Einspielen selbst aus. Die internen Tabellen von SQLite
        lassen sich nicht exportieren (Punkt 262)."""
        if tabelle.casefold().startswith("sqlite_"):
            raise NatterDatenbankError(
                f"„{tabelle}“ ist eine interne Tabelle von SQLite. SQLite "
                "legt sie selbst an und füllt sie; ein Dump davon ließe "
                "sich nicht wieder einspielen."
            )
        text = f"„{tabelle}“ wird exportiert …"
        with self._vorgang(text, "Der Export wurde abgebrochen.") as verbindung:
            zeile = verbindung.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?",
                (tabelle,),
            ).fetchone()
            if zeile is None or not zeile[0]:
                raise NatterDatenbankError(
                    f"Die Tabelle „{tabelle}“ gibt es in der Datenbank nicht."
                )
            # Spalte 6 von `table_xinfo` ist 0 für gewöhnliche Spalten,
            # 2 und 3 für berechnete. `SELECT *` lieferte berechnete
            # mit, und das Einspielen scheiterte an ihnen.
            spalten = [
                str(info[1])
                for info in verbindung.execute(
                    f"PRAGMA table_xinfo({bezeichner(tabelle)})"
                ).fetchall()
                if info[6] == 0
            ]
            spalten_sql = ", ".join(bezeichner(spalte) for spalte in spalten)
            with _zieldatei(ziel, encoding="utf-8") as datei:
                datei.write(f"BEGIN TRANSACTION;\n{zeile[0]};\n")
                cursor = verbindung.execute(
                    f"SELECT {spalten_sql} FROM {bezeichner(tabelle)}"
                )
                try:
                    for werte in self._zeilen_lesen(cursor, text):
                        datei.write(
                            f"INSERT INTO {bezeichner(tabelle)} ({spalten_sql}) "
                            f"VALUES ({', '.join(_sql_literal(w) for w in werte)});\n"
                        )
                finally:
                    cursor.close()
                datei.write("COMMIT;\n")

    def _ausgewaehlte_tabelle(self) -> str | None:
        eintrag = self._tabellenbaum.currentItem()
        if eintrag is None:
            return None
        while eintrag.parent() is not None:
            eintrag = eintrag.parent()
        return eintrag.text(0)
