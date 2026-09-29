"""CSV-Tabellenansicht (Abschnitt 11.5): erkennt Trennzeichen und
Zeichensatz automatisch (Excel-Export: Semikolon, Windows-1252), zeigt
wahlweise als sortierbare Tabelle oder als Rohtext an, mit Filterzeile.
Ändert die Datei nie, lädt sie aber neu, sobald ein Programm sie
überschreibt.

Das Neuladen liest und zerlegt die Datei in einem Nebenfaden. Ein
Programm, das eine CSV-Datei mit einer Million Zeilen schreibt, hielt
Natter sonst bei jedem Schreiben für mehrere Sekunden an (Punkt 355).
"""

from __future__ import annotations

import codecs
import csv
import io
import threading
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import (
    QAbstractTableModel,
    QFileSystemWatcher,
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QStackedWidget,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from ide.shell.vervollstaendigung import nebenfaden_rechnet
from pcl.zahlen import zahl

# `utf-8-sig` liest auch Dateien ohne BOM und nimmt eine vorhandene
# weg. Mit `utf-8` wurde die BOM, die Excel bei „CSV UTF-8“ schreibt,
# Teil des ersten Spaltennamens (Punkt 243).
_ZEICHENSAETZE = ("utf-8-sig", "cp1252")

# Wartezeit nach dem letzten Tastendruck im Filterfeld, bevor gefiltert
# wird. Beim Tippen eines Wortes wird so einmal gefiltert und nicht für
# jeden Buchstaben.
FILTER_PAUSE_MS = 200

# Wartezeit nach dem letzten Änderungssignal der Datei, bevor neu
# geladen wird. Ein Programm, das Zeile für Zeile schreibt, löst viele
# Signale kurz nacheinander aus; geladen wird danach einmal.
NEU_LADEN_PAUSE_MS = 300

# Dasselbe für Dateien ab `GROSSE_DATEI_BYTES`. Ein Neuladen liest und
# zerlegt dann einige Sekunden lang, wenn auch im Nebenfaden; ein
# Programm, das eine große Datei in mehreren Zügen schreibt, ist nach
# dieser Pause meist fertig, und die Datei wird einmal gelesen statt
# nach jedem Zug.
NEU_LADEN_PAUSE_GROSS_MS = 1500
GROSSE_DATEI_BYTES = 5_000_000

# So viele Zeilen zeigt die Ansicht „Als Text“ höchstens. Den Text
# einer Datei mit einer Million Zeilen setzte `QPlainTextEdit` in rund
# 4 s, und so lange stand das Fenster (Punkt 355). Wie das
# Datenbank-Panel mit `HOECHSTZAHL_ZEILEN` zeigt die Ansicht dann nur
# den Anfang und sagt das in der Hinweiszeile; die Tabelle enthält
# weiter alle Zeilen.
HOECHSTZAHL_TEXTZEILEN = 50_000

# Trennt die Zellen einer Zeile im Suchtext. Ein Filtertext aus dem
# Eingabefeld enthält dieses Zeichen nicht, ein Treffer kann also nicht
# über eine Zellgrenze hinweg entstehen.
_ZELLGRENZE = "\x00"

# Womit eine Zelle beginnen muss, damit `zahl` sie überhaupt lesen
# könnte. Alles andere ist ohne den Versuch Text; bei Spalten mit
# Namen spart das je Zelle eine Ausnahme.
_ZAHL_ANFANG = frozenset("+-.,0123456789")

# Vorgabe für `parent` in `rowCount`/`columnCount`: die Tabelle hat
# keine untergeordneten Zeilen.
_OHNE_ELTERN = QModelIndex()

# Schlüssel einer Spalte: je Zeile Zahl oder Text, dazu die Nummern
# der Zeilen mit Zahl, mit Text und mit leerer Zelle.
_Schluessel = tuple[list[float | str], list[int], list[int], list[int]]


def csv_erkennen(pfad: Path) -> tuple[str, str]:
    """Liefert (Trennzeichen, Zeichensatz) für `pfad` (Abschnitt 11.5):
    UTF-8 wird zuerst versucht, `cp1252` (Windows-1252, typischer
    Excel-Export) als Ausweich bei einem Dekodierfehler; das
    Trennzeichen wird aus der ersten Zeile zwischen ";" und ","
    entschieden (";" gewinnt bei Gleichstand, wie im deutschen
    Excel-Export üblich)."""
    trennzeichen, zeichensatz, _ = _erkennen(Path(pfad).read_bytes())
    return trennzeichen, zeichensatz


def _erkennen(rohdaten: bytes) -> tuple[str, str, str]:
    """Wie `csv_erkennen`, aber für schon gelesene Bytes; liefert den
    Text dazu mit."""
    for zeichensatz in _ZEICHENSAETZE:
        try:
            text = rohdaten.decode(zeichensatz)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = rohdaten.decode("utf-8-sig", errors="replace")
        zeichensatz = "utf-8-sig"
    if zeichensatz == "utf-8-sig" and not rohdaten.startswith(codecs.BOM_UTF8):
        # Ohne BOM dasselbe wie `utf-8`, und so heißt es dann auch.
        zeichensatz = "utf-8"

    erste_zeile = text.split("\n", 1)[0]
    trennzeichen = ";" if erste_zeile.count(";") >= erste_zeile.count(",") else ","
    return trennzeichen, zeichensatz, text


def _lesefehler_beschreiben(name: str, fehler: OSError) -> str:
    """Ein Satz auf Deutsch dazu, warum sich die Datei nicht lesen
    ließ. Der Text von Windows ist zum Teil englisch und nennt den
    ganzen Pfad."""
    if isinstance(fehler, FileNotFoundError):
        grund = "Die Datei ist nicht mehr vorhanden."
    elif isinstance(fehler, PermissionError):
        grund = (
            "Der Zugriff wurde verweigert. Vielleicht hält ein anderes "
            "Programm sie gerade geöffnet."
        )
    else:
        grund = fehler.strerror or type(fehler).__name__
        if grund[-1] not in ".!?":
            grund += "."
    return f"„{name}“ lässt sich nicht lesen. {grund}"


def _zeilen_lesen(
    text: str, trennzeichen: str,
) -> tuple[list[str], list[int], str | None]:
    """Zerlegt `text` in Zeilen und Zellen.

    Die Zellen aller Zeilen stehen hintereinander in einer Liste;
    Zeile `n` reicht dort von `grenzen[n]` bis vor `grenzen[n + 1]`.
    Eine Liste je Zeile wären bei einer Million Zeilen eine Million
    Objekte, die Pythons Speicherbereinigung bei jedem vollen
    Durchgang absucht; das hielt die Oberfläche beim Neuladen jedes
    Mal bis zu 0,7 s an (Punkt 355).

    Liefert Zellen und Grenzen und, wenn sich ein Teil der Datei nicht
    als Tabelle lesen lässt, einen Satz dazu; die Zeilen vor der Stelle
    bleiben dann erhalten. Der häufigste Grund ist ein Feld, das mit
    einem Anführungszeichen beginnt, das nie geschlossen wird: dann
    gehört der ganze Rest der Datei zu diesem einen Feld. Über 128 KB
    bricht `csv.reader` dabei ab (Punkt 326), darunter liefert er das
    Feld still mit allem bis zum Dateiende (Punkt 347); beides wird
    gemeldet. `reader.line_num` stünde da schon am Ende dieses
    Feldes; genannt wird deshalb die Zeile, in der der Datensatz
    beginnt.
    """
    # `newline=""` lässt Zeilenumbrüche innerhalb von
    # Anführungszeichen für `csv.reader` unverändert.
    leser = csv.reader(
        io.StringIO(text, newline=""), delimiter=trennzeichen,
    )
    zellen: list[str] = []
    grenzen = [0]
    beginn = 1
    letzter_beginn = 1
    try:
        for zeile in leser:
            zellen.extend(zeile)
            grenzen.append(len(zellen))
            letzter_beginn = beginn
            beginn = leser.line_num + 1
    except csv.Error as fehler:
        if "field limit" in str(fehler):
            grund = _OFFENES_ANFUEHRUNGSZEICHEN
        else:
            grund = "Der Aufbau passt dort nicht zum CSV-Format."
        return zellen, grenzen, (
            f"Ab Zeile {beginn} lässt sich die Datei nicht als Tabelle "
            f"lesen. {grund}"
        )
    if len(grenzen) > 1 and _bleibt_offen(
        text, letzter_beginn, trennzeichen,
    ):
        grenzen.pop()
        del zellen[grenzen[-1]:]
        return zellen, grenzen, (
            f"Ab Zeile {letzter_beginn} lässt sich die Datei nicht als "
            f"Tabelle lesen. {_OFFENES_ANFUEHRUNGSZEICHEN}"
        )
    return zellen, grenzen, None


_ZUM_TEXT = "Als Text anzeigen"
_ZUR_TABELLE = "Als Tabelle anzeigen"

_OFFENES_ANFUEHRUNGSZEICHEN = (
    "Dort beginnt ein Feld mit einem Anführungszeichen, das nicht "
    "wieder geschlossen wird."
)

# Eine Zeile, die in keiner CSV-Datei vorkommt. Steht sie nach dem
# Lesen allein in einem Datensatz, war am Dateiende kein Feld mehr
# offen.
_SCHLUSSZEILE = "\ufdd0"


def _bleibt_offen(text: str, beginn: int, trennzeichen: str) -> bool:
    """Ob der letzte Datensatz, der in Zeile `beginn` anfängt, in einem
    Feld mit offenem Anführungszeichen endet.

    `csv.reader` meldet das ohne `strict` nicht. Mit `strict` bräche er
    auch bei harmlosen Dingen wie `"a"b` ab, die er sonst so liest, wie
    die Tabelle sie zeigt. Stattdessen wird der letzte Datensatz noch
    einmal gelesen, mit einer Schlusszeile dahinter: ist das Feld
    offen, verschwindet sie darin. Ein Feld mit Zeilenumbruch, das
    ordentlich geschlossen wird, gilt so nicht als Fehler.
    """
    # Zeile für Zeile übersprungen, nicht mit `itertools.islice`: das
    # überspringt eine Million Zeilen in einem Zug und gibt so lange
    # keinem anderen Faden Gelegenheit, Python auszuführen.
    quelle = io.StringIO(text, newline="")
    for _ in range(beginn - 1):
        quelle.readline()
    rest = quelle.read()
    datensaetze = list(csv.reader(
        io.StringIO(f"{rest}\n{_SCHLUSSZEILE}", newline=""),
        delimiter=trennzeichen,
    ))
    return datensaetze[-1:] != [[_SCHLUSSZEILE]]


def _textanfang(text: str) -> tuple[str, bool]:
    """Die ersten `HOECHSTZAHL_TEXTZEILEN` Zeilen von `text` mit
    einheitlichem Zeilenende, und ob dahinter noch etwas kommt.

    Vereinheitlicht wird nur der Anfang: `replace` über den ganzen
    Text einer großen Datei kopiert ihn zweimal. Nur eine Datei, die
    Zeilen allein mit „\\r“ trennt, wird ganz umgewandelt und danach
    gekürzt.
    """
    anfang, gekuerzt = _zeilen_abschneiden(text)
    if "\r" in anfang:
        anfang = anfang.replace("\r\n", "\n").replace("\r", "\n")
        if not gekuerzt:
            anfang, gekuerzt = _zeilen_abschneiden(anfang)
    return anfang, gekuerzt


def _zeilen_abschneiden(text: str) -> tuple[str, bool]:
    """Die ersten `HOECHSTZAHL_TEXTZEILEN` mit „\\n“ getrennten Zeilen
    von `text`, und ob dahinter noch etwas kommt."""
    ende = -1
    for _ in range(HOECHSTZAHL_TEXTZEILEN):
        ende = text.find("\n", ende + 1)
        if ende < 0:
            return text, False
    return text[:ende + 1], ende + 1 < len(text)


def _zahl_deutsch(anzahl: int) -> str:
    """`50000` als „50.000“."""
    return f"{anzahl:,}".replace(",", ".")


def _sortierschluessel(
    zellen: list[str], grenzen: list[int], spalte: int,
) -> _Schluessel:
    """Schlüssel einer Spalte zum Sortieren, für Zeilen wie aus
    `_zeilen_lesen`.

    Eine Zelle, die `pcl.zahlen.zahl` lesen kann, zählt als Zahl, mit
    Dezimalkomma wie mit Dezimalpunkt; so erkennt auch der CSV-Import
    des Datenbank-Panels seine Zahlenspalten (Punkt 288).
    """
    schluessel: list[float | str] = []
    mit_zahl: list[int] = []
    mit_text: list[int] = []
    leer: list[int] = []
    for nummer in range(len(grenzen) - 1):
        stelle = grenzen[nummer] + spalte
        zelle = zellen[stelle] if stelle < grenzen[nummer + 1] else ""
        nackt = zelle.strip()
        if not nackt:
            schluessel.append("")
            leer.append(nummer)
            continue
        if nackt[0] in _ZAHL_ANFANG:
            try:
                schluessel.append(zahl(nackt))
            except ValueError:
                pass
            else:
                mit_zahl.append(nummer)
                continue
        schluessel.append(zelle)
        mit_text.append(nummer)
    return schluessel, mit_zahl, mit_text, leer


class _Tabellendaten:
    """Die Datenzeilen einer CSV-Datei, abgelegt wie von
    `_zeilen_lesen`: alle Zellen in einer Liste, dazu die Grenzen der
    Zeilen.

    Filtern und Sortieren arbeiten auf Listen von Zeilennummern:
    `reihenfolge` ist die sortierte Folge aller Zeilen, `sichtbar`
    der Teil davon, der zum Filter passt. Es entsteht kein Objekt je
    Zelle und keins je Zeile.

    Die Klasse hat mit Qt nichts zu tun. Beim Neuladen entsteht sie
    samt Sortierung und Filter im Nebenfaden; im Faden der Oberfläche
    kommt danach nur noch das Modell darum herum dazu.
    """

    def __init__(
        self, kopf: list[str], zellen: list[str], grenzen: list[int],
    ) -> None:
        self.kopf = kopf
        self.zellen = zellen
        self.grenzen = grenzen
        self.anzahl = len(grenzen) - 1
        spalten = len(kopf)
        # Kleingeschrieben und je Zeile zusammengefügt, damit der
        # Filter je Zeile nur einen Vergleich braucht. Wie in der
        # Tabelle zählen nur die Zellen unter einer Überschrift.
        self.suchtext = [
            _ZELLGRENZE.join(
                zellen[grenzen[n]:min(grenzen[n + 1], grenzen[n] + spalten)],
            ).lower()
            for n in range(self.anzahl)
        ]
        self.reihenfolge = list(range(self.anzahl))
        self.sichtbar = self.reihenfolge
        self.filtertext = ""
        # Je Spalte die Schlüssel aus `_sortierschluessel`, erst beim
        # ersten Sortieren nach dieser Spalte berechnet und danach für
        # beide Richtungen wiederverwendet.
        self.schluessel: dict[int, _Schluessel] = {}

    def zelle(self, zeile: int, spalte: int) -> str | None:
        """Die Zelle in Datenzeile `zeile`; None, wenn die Zeile so
        viele Spalten nicht hat."""
        stelle = self.grenzen[zeile] + spalte
        if stelle < self.grenzen[zeile + 1]:
            return self.zellen[stelle]
        return None

    def sortieren(self, spalte: int, absteigend: bool) -> None:
        """Zahlen nach Wert vor Texten, leere Zellen am Ende.

        Absteigend kehrt sich die Folge aus Zahlen und Texten um, die
        leeren Zellen bleiben unten. Mit dem Zelltext als Schlüssel
        stand „100“ vor „25“ und „9“ ganz hinten (Punkt 329). Eine
        Spalte außerhalb der Tabelle stellt die Reihenfolge der Datei
        wieder her.
        """
        if 0 <= spalte < len(self.kopf):
            if spalte not in self.schluessel:
                self.schluessel[spalte] = _sortierschluessel(
                    self.zellen, self.grenzen, spalte,
                )
            schluessel, mit_zahl, mit_text, leer = self.schluessel[spalte]
            zahlen = sorted(
                mit_zahl, key=schluessel.__getitem__, reverse=absteigend,
            )
            texte = sorted(
                mit_text, key=schluessel.__getitem__, reverse=absteigend,
            )
            if absteigend:
                self.reihenfolge = texte + zahlen + leer
            else:
                self.reihenfolge = zahlen + texte + leer
        else:
            self.reihenfolge = list(range(self.anzahl))
        self.sichtbar = self._gefiltert()

    def filtern(self, text: str) -> None:
        """Behält nur Zeilen, in denen eine Zelle `text` enthält, ohne
        Beachtung der Groß- und Kleinschreibung. Leerer Text behält
        alle Zeilen."""
        self.filtertext = text.lower()
        self.sichtbar = self._gefiltert()

    def _gefiltert(self) -> list[int]:
        text = self.filtertext
        if not text:
            return self.reihenfolge
        suchtext = self.suchtext
        return [n for n in self.reihenfolge if text in suchtext[n]]


@dataclass
class _Ladung:
    """Was `_datei_lesen` aus einer Datei gewinnt. Bei einem
    Lesefehler steht nur `lesefehler` fest."""

    lesefehler: str | None = None
    groesse: int = 0
    trennzeichen: str = ";"
    zeichensatz: str = "utf-8"
    csv_fehler: str | None = None
    daten: _Tabellendaten | None = None
    rohtext: str = ""
    gekuerzt: bool = False
    # Womit `daten` schon gefiltert und sortiert sind: Filtertext,
    # Spalte (-1 für keine) und ob absteigend.
    filtertext: str = ""
    sortierung: tuple[int, bool] = (-1, False)


def _datei_lesen(
    pfad: Path, filtertext: str, sortierung: tuple[int, bool],
) -> _Ladung:
    """Liest `pfad` und bereitet die Tabelle fertig vor: zerlegt,
    gefiltert und sortiert, dazu der Anfang des Textes für die
    Rohansicht.

    Berührt kein Qt-Objekt und läuft deshalb auch im Nebenfaden.
    """
    try:
        rohdaten = pfad.read_bytes()
    except OSError as fehler:
        return _Ladung(lesefehler=_lesefehler_beschreiben(pfad.name, fehler))
    trennzeichen, zeichensatz, text = _erkennen(rohdaten)
    zellen, grenzen, csv_fehler = _zeilen_lesen(text, trennzeichen)
    rohtext, gekuerzt = _textanfang(text)
    # Die erste Zeile ist die Kopfzeile; die Datenzeilen beginnen
    # dahinter in derselben Liste.
    if len(grenzen) > 1:
        kopf, grenzen = zellen[:grenzen[1]], grenzen[1:]
    else:
        kopf = []
    daten = _Tabellendaten(kopf, zellen, grenzen)
    daten.filtern(filtertext)
    spalte, absteigend = sortierung
    if 0 <= spalte < len(kopf):
        daten.sortieren(spalte, absteigend)
    else:
        sortierung = (-1, False)
    return _Ladung(
        groesse=len(rohdaten),
        trennzeichen=trennzeichen,
        zeichensatz=zeichensatz,
        csv_fehler=csv_fehler,
        daten=daten,
        rohtext=rohtext,
        gekuerzt=gekuerzt,
        filtertext=filtertext,
        sortierung=sortierung,
    )


class _CsvModell(QAbstractTableModel):
    """Zeigt `_Tabellendaten` in einer `QTableView`. Die Tabelle fragt
    nur die Zellen ab, die gerade zu sehen sind."""

    def __init__(
        self,
        daten: _Tabellendaten,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._daten = daten

    def rowCount(
        self,
        parent: QModelIndex | QPersistentModelIndex = _OHNE_ELTERN,
    ) -> int:
        return 0 if parent.isValid() else len(self._daten.sichtbar)

    def columnCount(
        self,
        parent: QModelIndex | QPersistentModelIndex = _OHNE_ELTERN,
    ) -> int:
        return 0 if parent.isValid() else len(self._daten.kopf)

    def data(
        self,
        index: QModelIndex | QPersistentModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> str | None:
        if role != Qt.ItemDataRole.DisplayRole or not index.isValid():
            return None
        daten = self._daten
        return daten.zelle(daten.sichtbar[index.row()], index.column())

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> str | int | None:
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        daten = self._daten
        if orientation == Qt.Orientation.Horizontal:
            if 0 <= section < len(daten.kopf):
                return daten.kopf[section]
            return None
        # Links steht die Nummer der Datenzeile in der Datei, auch nach
        # Filtern und Sortieren.
        if 0 <= section < len(daten.sichtbar):
            return daten.sichtbar[section] + 1
        return None

    def sort(
        self,
        column: int,
        order: Qt.SortOrder = Qt.SortOrder.AscendingOrder,
    ) -> None:
        """Sortiert wie `_Tabellendaten.sortieren`."""
        self.beginResetModel()
        self._daten.sortieren(
            column, order == Qt.SortOrder.DescendingOrder,
        )
        self.endResetModel()

    def filtern(self, text: str) -> None:
        """Filtert wie `_Tabellendaten.filtern`."""
        self.beginResetModel()
        self._daten.filtern(text)
        self.endResetModel()


class _Bote(QObject):
    """Bringt das Ergebnis eines Neuladens aus dem Nebenfaden: laufende
    Nummer des Auftrags und die `_Ladung`. Qt stellt das Signal im
    Faden der Oberfläche zu.

    Der Nebenfaden hält nur den Boten, nie die Ansicht (Punkt 411).
    Hielt er die Ansicht selbst, sendete er nach dem Schließen des
    Reiters an ein schon gelöschtes Widget, und Python stürzte mit
    „access violation“ ab. Der Bote hat keine Eltern: er lebt, solange
    Ansicht oder Faden ihn halten, und geht nicht mit der Ansicht
    unter, während der Faden noch sendet. Die Verbindung zur Ansicht
    löst Qt beim Löschen der Ansicht von selbst.
    """

    fertig = Signal(int, object)


def _im_nebenfaden_laden(
    bote: _Bote,
    auftrag: int,
    pfad: Path,
    filtertext: str,
    sortierung: tuple[int, bool],
) -> None:
    # Ohne automatische Speicherbereinigung: eine Million Zeilen
    # sind eine Million neue Listen, und jeder volle Durchgang der
    # Bereinigung darüber hielt den Faden der Oberfläche bis zu
    # 0,9 s an. Dazu räumte sie womöglich im Nebenfaden ein altes
    # Qt-Objekt ab.
    try:
        with nebenfaden_rechnet():
            ladung = _datei_lesen(pfad, filtertext, sortierung)
    except Exception as fehler:  # noqa: BLE001
        # Ein Fehler im Nebenfaden ginge sonst ungesehen verloren,
        # und die Ansicht bliebe für immer beim Laden stehen.
        ladung = _Ladung(
            lesefehler=(
                f"„{pfad.name}“ lässt sich nicht lesen. Beim "
                f"Einlesen trat ein Fehler auf "
                f"({type(fehler).__name__})."
            ),
        )
    bote.fertig.emit(auftrag, ladung)


class CsvAnsicht(QWidget):
    """Zeigt eine CSV-Datei als sortierbare, filterbare Tabelle oder als
    Rohtext (Abschnitt 11.5)."""

    def __init__(self, pfad: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pfad = Path(pfad)
        self._delimiter, self._encoding = ";", "utf-8"
        self._rohtext: str | None = None
        self._text_gekuerzt = False
        self._modell = _CsvModell(_Tabellendaten([], [], [0]), self)

        self._tabelle = QTableView()
        self._tabelle.setModel(self._modell)
        self._text = QPlainTextEdit()
        self._text.setReadOnly(True)

        self._stapel = QStackedWidget()
        self._stapel.addWidget(self._tabelle)
        self._stapel.addWidget(self._text)

        self._filter = QLineEdit()
        self._filter.setPlaceholderText("Filtern …")
        self._filter_uhr = QTimer(self)
        self._filter_uhr.setSingleShot(True)
        self._filter_uhr.setInterval(FILTER_PAUSE_MS)
        self._filter_uhr.timeout.connect(self._filter_anwenden)
        self._filter.textChanged.connect(self._filter_uhr.start)
        # Die Beschriftung nennt die Ansicht, zu der ein Klick führt;
        # ein gedrückter Knopf mit unveränderter Beschriftung ließ
        # nicht erkennen, wie es zur Tabelle zurückgeht (Punkt 353).
        self._umschalt_knopf = QPushButton(_ZUM_TEXT)
        self._umschalt_knopf.setCheckable(True)
        self._umschalt_knopf.toggled.connect(self._ansicht_umschalten)

        # Sagt, warum die Tabelle leer oder unvollständig ist. Ohne sie
        # endete eine Datei mit offenem Anführungszeichen oder eine
        # gesperrte Datei in der allgemeinen Fehlermeldung von Natter
        # (Punkt 326).
        self._hinweis = QLabel()
        self._hinweis.setWordWrap(True)
        self._hinweis.setStyleSheet(
            "QLabel { background: #fff4c2; color: #000000;"
            " border: 1px solid #d8c060; padding: 4px; }"
        )
        self._hinweis.hide()
        # Was `_zeilen_lesen` zu einer Datei sagt, die sich nicht ganz
        # als Tabelle lesen lässt, und was beim letzten Lesen schiefging.
        # Der Lesefehler hat Vorrang; der Satz zur Tabelle bekommt je
        # nach Ansicht einen passenden Schluss.
        self._csv_fehler: str | None = None
        self._lesefehler: str | None = None

        werkzeugleiste = QHBoxLayout()
        werkzeugleiste.addWidget(self._filter)
        werkzeugleiste.addWidget(self._umschalt_knopf)

        layout = QVBoxLayout(self)
        layout.addLayout(werkzeugleiste)
        layout.addWidget(self._hinweis)
        layout.addWidget(self._stapel)

        # Ein Programm, das die Datei schreibt, während sie hier offen
        # ist, soll sein Ergebnis sehen (Punkt 330). Die Signale werden
        # gebündelt: jedes startet die Uhr neu, geladen wird erst, wenn
        # eine Weile keins mehr kam.
        self._beobachter = QFileSystemWatcher(self)
        self._neu_laden_uhr = QTimer(self)
        self._neu_laden_uhr.setSingleShot(True)
        self._neu_laden_uhr.setInterval(NEU_LADEN_PAUSE_MS)
        self._neu_laden_uhr.timeout.connect(self._neu_laden)
        self._beobachter.fileChanged.connect(self._neu_laden_uhr.start)

        # Neuladen im Nebenfaden. Es läuft höchstens einer; kommt
        # währenddessen eine weitere Änderung, ist sein Ergebnis schon
        # veraltet: es wird verworfen, und danach wird noch einmal
        # geladen. `_auftrag` zählt die Aufträge, damit auch ein
        # Ergebnis, das nach dem Schließen noch ankommt, nichts mehr
        # anrichtet.
        self._auftrag = 0
        self._faden_laeuft = False
        self._noch_einmal = False
        self._bote = _Bote()
        self._bote.fertig.connect(self._neu_geladen_einsetzen)

        # Das erste Lesen geschieht gleich hier: wer die Ansicht
        # öffnet, erwartet den Inhalt. Ohne Sortierung und Filter ist
        # das bei einer Million Zeilen rund 1 s.
        self._beobachten()
        self._einsetzen(_datei_lesen(self._pfad, "", (-1, False)))
        # Ohne Sortierspalte beginnt die Tabelle in der Reihenfolge der
        # Datei; sortiert wird erst nach einem Klick auf eine
        # Überschrift.
        self._tabelle.horizontalHeader().setSortIndicator(
            -1, Qt.SortOrder.AscendingOrder,
        )
        self._tabelle.setSortingEnabled(True)

    @property
    def delimiter(self) -> str:
        return self._delimiter

    @property
    def encoding(self) -> str:
        return self._encoding

    @property
    def tabelle(self) -> QTableView:
        return self._tabelle

    @property
    def hinweis(self) -> str:
        """Der Text der Hinweiszeile; leer, solange sie verborgen
        ist."""
        return "" if self._hinweis.isHidden() else self._hinweis.text()

    def _hinweis_zeigen(self) -> None:
        text = self._lesefehler
        als_text = self._umschalt_knopf.isChecked()
        anfang = (
            f"die ersten {_zahl_deutsch(HOECHSTZAHL_TEXTZEILEN)} Zeilen"
        )
        if text is None and self._csv_fehler is not None:
            if not als_text:
                schluss = "Die Tabelle enthält nur die Zeilen davor."
            elif self._text_gekuerzt:
                schluss = (
                    f"Zu sehen ist deshalb der Inhalt als Text, {anfang} "
                    "der Datei; die Tabelle enthält nur die Zeilen davor."
                )
            else:
                schluss = (
                    "Zu sehen ist deshalb der ganze Inhalt als Text; die "
                    "Tabelle enthält nur die Zeilen davor."
                )
            text = f"{self._csv_fehler} {schluss}"
        elif text is None and als_text and self._text_gekuerzt:
            text = (
                f"Als Text zu sehen sind nur {anfang} der Datei; die "
                "Tabelle enthält alle."
            )
        self._hinweis.setText(text or "")
        self._hinweis.setVisible(bool(text))

    def _beobachten(self) -> None:
        # Manche Programme ersetzen die Datei, statt sie zu
        # überschreiben; `QFileSystemWatcher` verliert sie dabei aus
        # dem Blick. Erneutes Hinzufügen ist folgenlos, wenn der Pfad
        # schon beobachtet wird.
        pfad = str(self._pfad)
        if pfad not in self._beobachter.files() and self._pfad.exists():
            self._beobachter.addPath(pfad)

    def _sortierung(self) -> tuple[int, bool]:
        """Spalte und Richtung, nach der die Tabelle gerade sortiert
        ist; (-1, False), wenn sie es nicht ist."""
        kopfleiste = self._tabelle.horizontalHeader()
        if not self._tabelle.isSortingEnabled():
            return -1, False
        return (
            kopfleiste.sortIndicatorSection(),
            kopfleiste.sortIndicatorOrder() == Qt.SortOrder.DescendingOrder,
        )

    def _einsetzen(self, ladung: _Ladung) -> None:
        """Setzt eine fertige `_Ladung` ein.

        Lässt sich die Datei nicht lesen, bleibt der bisherige Inhalt
        stehen, und die Hinweiszeile sagt, warum. Filtertext und
        Sortierung gelten auch für den neuen Inhalt; wurden sie
        geändert, während die Ladung entstand, wird hier nachgeholt.
        """
        if ladung.lesefehler is not None or ladung.daten is None:
            self._lesefehler = ladung.lesefehler
            self._hinweis_zeigen()
            return
        self._neu_laden_uhr.setInterval(
            NEU_LADEN_PAUSE_GROSS_MS
            if ladung.groesse >= GROSSE_DATEI_BYTES
            else NEU_LADEN_PAUSE_MS,
        )
        self._delimiter = ladung.trennzeichen
        self._encoding = ladung.zeichensatz
        self._lesefehler, self._csv_fehler = None, ladung.csv_fehler

        # Die Rohansicht wird erst beim ersten Umschalten gefüllt; ist
        # sie gerade zu sehen, bekommt sie den neuen Text gleich.
        self._rohtext = ladung.rohtext
        self._text_gekuerzt = ladung.gekuerzt
        if self._umschalt_knopf.isChecked():
            self._ansicht_umschalten(True)
        else:
            self._hinweis_zeigen()

        daten = ladung.daten
        filtertext = self._filter.text()
        if filtertext.lower() != ladung.filtertext.lower():
            daten.filtern(filtertext)
        kopfleiste = self._tabelle.horizontalHeader()
        spalte = kopfleiste.sortIndicatorSection()
        richtung = kopfleiste.sortIndicatorOrder()
        sortierung = self._sortierung()
        if not 0 <= sortierung[0] < len(daten.kopf):
            sortierung = (-1, False)
        if sortierung != ladung.sortierung:
            daten.sortieren(*sortierung)
        modell = _CsvModell(daten, self)
        alt, self._modell = self._modell, modell
        # `setModel` kann die Sortieranzeige zurücksetzen. Sie wird
        # ohne Signal wieder gesetzt, sonst sortierte die Tabelle das
        # schon sortierte Modell ein zweites Mal.
        self._tabelle.setModel(modell)
        kopfleiste.blockSignals(True)
        kopfleiste.setSortIndicator(spalte, richtung)
        kopfleiste.blockSignals(False)
        alt.deleteLater()

        # Bei einem Fehler zeigt die Ansicht den Text; die Tabelle wäre
        # unvollständig, ohne dass es ihr anzusehen ist.
        if ladung.csv_fehler is not None:
            self._umschalt_knopf.setChecked(True)

    def beim_schliessen(self) -> None:
        """Vom Hauptfenster gerufen, bevor der Reiter freigegeben wird
        (Punkt 376). Die Datei wird nicht mehr beobachtet, und ein
        Ladevorgang, der noch im Nebenfaden läuft, wird verworfen:
        sein Ergebnis trägt dann eine veraltete Auftragsnummer."""
        dateien = self._beobachter.files()
        if dateien:
            self._beobachter.removePaths(dateien)
        self._neu_laden_uhr.stop()
        self._filter_uhr.stop()
        self._auftrag += 1
        self._noch_einmal = False

    def _neu_laden(self) -> None:
        """Lädt die Datei im Nebenfaden neu. Das Fenster bleibt dabei
        bedienbar; der alte Inhalt bleibt stehen, bis der neue fertig
        ist."""
        self._neu_laden_uhr.stop()
        self._beobachten()
        if self._faden_laeuft:
            self._noch_einmal = True
            return
        self._auftrag += 1
        self._faden_laeuft = True
        self._noch_einmal = False
        threading.Thread(
            target=_im_nebenfaden_laden,
            args=(
                self._bote, self._auftrag, self._pfad,
                self._filter.text(), self._sortierung(),
            ),
            name="CsvAnsicht-Neuladen",
            daemon=True,
        ).start()

    def _neu_geladen_einsetzen(self, auftrag: int, ladung: _Ladung) -> None:
        if auftrag != self._auftrag:
            return
        self._faden_laeuft = False
        if self._noch_einmal:
            # Die Datei hat sich geändert, während sie gelesen wurde;
            # dieses Ergebnis zeigt schon einen alten Stand.
            self._neu_laden()
            return
        self._einsetzen(ladung)

    def _ansicht_umschalten(self, als_text: bool) -> None:
        if als_text and self._rohtext is not None:
            self._text.setPlainText(self._rohtext)
            self._rohtext = None
        self._stapel.setCurrentWidget(self._text if als_text else self._tabelle)
        self._umschalt_knopf.setText(
            _ZUR_TABELLE if als_text else _ZUM_TEXT,
        )
        self._hinweis_zeigen()

    def _filter_anwenden(self) -> None:
        self._filter_uhr.stop()
        self._modell.filtern(self._filter.text())
