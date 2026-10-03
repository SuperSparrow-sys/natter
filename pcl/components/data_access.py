"""Datenbank-Komponenten (Abschnitt 10.1): Verbindung, Abfrage,
Datenquelle – ausschließlich SQLite.

Der kurze Weg ist der Normalweg. Eine Abfrage ist eine Zeile:

 self.db = SQLite3Connection("konten.sqlite")
 for zeile in self.db.query("SELECT inhaber, stand FROM konto"):
 print(zeile["inhaber"], zeile["stand"])

Schreibende Anweisungen genauso, mit ``:name``-Platzhaltern als
Schlüsselwortargumente – der Schutz vor SQL-Injection, den der Lehrgang
eigens erklärt, bleibt damit derselbe:

 self.db.execute("INSERT INTO konto (inhaber) VALUES (wer)", wer=name)

Warum nur SQLite. Ein Datenbankserver bräuchte Zugangsdaten, und ein
Passwort als Eigenschaft landete im Klartext in der `.pfm` - in einer
Datei, die Lernende abgeben und herumtragen. Eine Datenbankdatei neben
dem Programm läuft ohne Server, ohne Netz und ohne Zugangsdaten auf
jedem Schulrechner; mehr braucht der Unterricht nicht. Natter kennt
deshalb kein Datenbank-Passwort.

Warum keine `SQLTransaction` mehr. `query`/`execute` schreiben
sofort fest (Auto-Commit). Eine eigene Komponente, die man nur anlegt,
um `commit` darauf zu rufen, erklärt sich nicht von selbst. Wo mehrere
Anweisungen zusammengehören, fasst ein ``with``-Block sie zu einer
Transaktion zusammen:

    with self.db.transaction():
        self.db.execute("UPDATE konto SET stand = stand - 50 WHERE nr = 1")
        self.db.execute("UPDATE konto SET stand = stand + 50 WHERE nr = 2")

Innerhalb der Transaktion schreiben `query` und `execute` nichts fest
(Punkt 259). Endet der Block ohne Fehler, wird alles festgeschrieben,
endet er mit irgendeiner Ausnahme, wird alles zurückgenommen.
``execute("BEGIN")`` mit `commit()` und `rollback()` geht weiterhin.

`SQLQuery` und `DataSource` bleiben als Unterbau der Data Controls
(`DBGrid` und Geschwister in `data_controls.py`): die brauchen einen
Datensatzzeiger, den eine Liste von `dict`s nicht hat. Im Lehrgang und
in der Komponenten-Referenz steht dafür der kurze Weg.

Objektverweise zwischen den Komponenten (``SQLQuery.database``,
``DataSource.dataset``) sind bewusst einfache Instanzattribute statt
`Prop`, weil `Prop` nur Wertetypen (Text/Zahl/Wahrheitswert) mit
sinnvollem Standardwert kennt.
"""

from __future__ import annotations

import sqlite3
import sys
import weakref
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from pcl.errors import NatterDatenbankError, NatterDatenError
from pcl.properties import Komponente, Prop
from pcl.zahlen import text as zahl_text


def anzeigetext(wert: Any) -> str:
    """Ein Zellenwert aus der Datenbank, wie er in einer Anzeige
    erscheint: ein leeres Feld (`NULL`) als leerer Text, eine Kommazahl
    mit Dezimalkomma, Binärdaten als Hinweis mit ihrer Größe statt
    als Bytefolge. Gemeinsam für alle Data Controls, damit keines
    „None“ oder „1.5“ zeigt (Punkt 246)."""
    if wert is None:
        return ""
    if isinstance(wert, (bytes, bytearray, memoryview)):
        return binaertext(len(bytes(wert)))
    if isinstance(wert, float):
        return zahl_text(wert)
    return str(wert)


def binaertext(anzahl: int) -> str:
    """Der Hinweis, der in einer Anzeige für Binärdaten steht, etwa
    „(Binärdaten, 4 Bytes)“. Eigene Funktion, weil das
    Datenbank-Panel nur die Größe holt und nicht die Bytes selbst."""
    einheit = "Byte" if anzahl == 1 else "Bytes"
    return f"(Binärdaten, {anzahl} {einheit})"


def _abschliessen(verbindung: sqlite3.Connection, name: str) -> None:
    """Schließt eine `sqlite3`-Verbindung. Ist dabei noch eine
    Transaktion offen, wird sie zurückgenommen, und eine Meldung sagt
    das. Läuft auch beim Programmende für jede Verbindung, die das
    Programm offen gelassen hat: vorher gingen die Änderungen einer
    vergessenen Transaktion dort ohne ein Wort verloren (Punkt
    265)."""
    try:
        offen = verbindung.in_transaction
    except sqlite3.Error:
        return
    try:
        if offen:
            verbindung.rollback()
            print(
                f"Hinweis zur Datenbank „{name}“: Beim Schließen der "
                "Verbindung war noch eine Transaktion offen. Die "
                "Änderungen darin wurden verworfen. Festgeschrieben wird "
                "nur, was commit() oder ein fehlerfrei beendeter "
                "with-Block mit transaction() schreibt.",
                file=sys.stderr,
            )
        verbindung.close()
    except sqlite3.Error:
        pass


def _ohne_tupel(methode: str, werte: tuple[Any, ...]) -> None:
    """Werte kommen mit Namen, nicht als Tupel wie in `sqlite3`
    (Punkt 486). Die übliche Schreibweise aus Anleitungen,
    ``execute("… VALUES (?)", (name,))``, endete sonst in „nimmt 2
    Angaben entgegen, übergeben wurden 3“, und niemand erfuhr, wie es
    richtig geht."""
    if werte:
        raise NatterDatenbankError(
            f"SQLite3Connection.{methode}: Werte werden hier nicht als "
            "Tupel übergeben, sondern mit Namen: im SQL-Text als "
            "Platzhalter „:name“ und beim Aufruf als name=wert."
        )


class SQLite3Connection(Komponente):
    """Verbindung zu einer SQLite-Datenbank. ``database_name`` ist ein
    Dateipfad oder ``":memory:"``.

    Der kurze Weg öffnet im Konstruktor::

        self.db = SQLite3Connection("konten.sqlite")

    Der ausführliche steht daneben und tut dasselbe – er wird gebraucht,
    wenn die Verbindung erst später aufgebaut werden soll::

        self.db = SQLite3Connection()
        self.db.database_name = "konten.sqlite"
        self.db.connected = True
    """

    database_name = Prop(
        str, "", kategorie="Datenbank", doc='Pfad zur Datenbankdatei oder ":memory:"'
    )
    connected = Prop(
        bool,
        False,
        kategorie="Datenbank",
        doc="Verbindung öffnen (True) bzw. schließen (False)",
    )

    def __init__(self, database_name: str | Path | None = None) -> None:
        # Muss vor jeder Prop-Zuweisung stehen: `connected = True` ruft
        # `_bei_prop_aenderung` auf, und das greift auf `_verbindung` zu.
        self._verbindung: sqlite3.Connection | None = None
        self._abschluss: weakref.finalize | None = None
        #: Ob die Datei beim Verbinden erst angelegt wurde. Eine
        #: Abfrage, die dann an einer fehlenden Tabelle scheitert, weist
        #: auf einen falsch geschriebenen Dateinamen hin (Punkt 427).
        self._neu_angelegt = False
        if database_name is not None:
            self.database_name = str(database_name)
            self.connected = True

    @property
    def verbindung(self) -> sqlite3.Connection:
        """Die offene `sqlite3`-Verbindung. Wer nur Daten lesen oder
        schreiben will, braucht sie nicht – dafür gibt es `query()` und
        `execute()`."""
        if self._verbindung is None:
            raise NatterDatenbankError(
                "SQLite3Connection: keine offene Verbindung. Entweder den "
                'Dateinamen gleich mitgeben – SQLite3Connection("daten.sqlite") '
                "– oder connected = True setzen."
            )
        return self._verbindung

    # -- Der kurze Weg -------------------------------------------------

    def query(
        self, sql: str, *werte: Any, **parameter: Any
    ) -> list[dict[str, Any]]:
        """Führt eine SELECT-Anweisung aus und liefert alle Zeilen als
        Liste von `dict`s::

            for zeile in db.query("SELECT inhaber, stand FROM konto"):
                print(zeile["inhaber"])

        Werte gehören nie in den SQL-Text, sondern als
        ``:name``-Platzhalter hinein und als Schlüsselwortargument
        hierher::

            db.query("SELECT * FROM konto WHERE stand >= :grenze", grenze=100)

        Ein `dict` und keine eigene Zeilenklasse: `dict` kennen Lernende
        an dieser Stelle längst, eine neue Vokabel wäre hier nichts wert.

        Steht hier doch eine schreibende Anweisung, wird sie wie bei
        `execute()` festgeschrieben.
        """
        _ohne_tupel("query", werte)
        war_offen = self.verbindung.in_transaction
        cursor = self._ausfuehren(sql, parameter)
        spalten = [beschreibung[0] for beschreibung in cursor.description or []]
        zeilen = [
            dict(zip(spalten, zeile, strict=True))
            for zeile in self._zeilen_holen(cursor, war_offen)
        ]
        # Ein INSERT über `query()` statt `execute()` öffnet eine
        # Transaktion, die sonst niemand schließt: die Zeile wäre nur
        # im eigenen Programm sichtbar, beim Programmende verloren, und
        # die Datei bliebe für alle anderen gesperrt (Punkt 238). Hat
        # erst diese Anweisung die Transaktion geöffnet, wird sie
        # deshalb festgeschrieben wie bei `execute()`.
        self._festschreiben_falls_eigen(sql, war_offen)
        return zeilen

    def query_one(
        self, sql: str, *werte: Any, **parameter: Any
    ) -> dict[str, Any] | None:
        """Wie `query()`, liefert aber nur die erste Zeile – oder
        ``None``, wenn die Abfrage nichts findet::

            konto = db.query_one("SELECT * FROM konto WHERE nummer = :nr", nr=7)
            if konto is None:
                self.l_meldung.caption = "Kein Konto mit dieser Nummer."
        """
        _ohne_tupel("query_one", werte)
        zeilen = self.query(sql, **parameter)
        return zeilen[0] if zeilen else None

    def execute(self, sql: str, *werte: Any, **parameter: Any) -> int:
        """Führt eine schreibende Anweisung aus (INSERT, UPDATE, DELETE,
        CREATE TABLE) und schreibt sie sofort fest. Liefert die Anzahl
        der betroffenen Zeilen::

            db.execute("INSERT INTO konto (inhaber) VALUES (:wer)", wer=name)
            gelöscht = db.execute("DELETE FROM konto WHERE stand = 0")

        Nach einem ``db.execute("BEGIN")`` schreibt `execute()` nicht
        fest; das tut dann erst `commit()`, und `rollback()` nimmt
        alles seit dem ``BEGIN`` zurück.
        """
        _ohne_tupel("execute", werte)
        war_offen = self.verbindung.in_transaction
        cursor = self._ausfuehren(sql, parameter)
        anzahl = cursor.rowcount
        cursor.close()
        # Vorher wurde hier in jedem Fall festgeschrieben, auch mitten
        # in einer ausdrücklich begonnenen Transaktion: nach „BEGIN“,
        # einer Abbuchung und `rollback()` stand die Abbuchung schon in
        # der Datei (Punkt 259).
        self._festschreiben_falls_eigen(sql, war_offen)
        return max(anzahl, 0)

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """Fasst mehrere Anweisungen zu einer Transaktion zusammen::

            with db.transaction():
                db.execute("UPDATE konto SET stand = stand - 50 WHERE nr = 1")
                db.execute("UPDATE konto SET stand = stand + 50 WHERE nr = 2")

        Endet der Block ohne Fehler, schreibt er alles fest. Endet er
        mit einer Ausnahme, gleich welcher, nimmt er alles zurück und
        reicht die Ausnahme weiter. Vorher stand in der Dokumentation
        ein ``try``, das nur `NatterDatenbankError` fing: ein
        `ValueError` aus einer Eingabe dazwischen ließ die Transaktion
        bis zum Programmende offen, jeder weitere Klick scheiterte an
        ``BEGIN``, und alles danach ging beim Beenden verloren (Punkt
        265)."""
        self.execute("BEGIN")
        try:
            yield
        except BaseException:
            if self.verbindung.in_transaction:
                self.verbindung.rollback()
            raise
        try:
            self.verbindung.commit()
        except sqlite3.Error as fehler:
            if self.verbindung.in_transaction:
                self.verbindung.rollback()
            raise NatterDatenbankError(f"SQL-Fehler: {fehler}") from fehler

    def commit(self) -> None:
        """Schreibt offene Änderungen fest, etwa alles seit einem
        ``execute("BEGIN")``. Außerhalb einer solchen Transaktion
        schreibt `execute()` von sich aus fest."""
        try:
            self.verbindung.commit()
        except sqlite3.Error as fehler:
            raise NatterDatenbankError(f"SQL-Fehler: {fehler}") from fehler

    def rollback(self) -> None:
        """Verwirft offene Änderungen, etwa alles seit einem
        ``execute("BEGIN")``."""
        try:
            self.verbindung.rollback()
        except sqlite3.Error as fehler:
            raise NatterDatenbankError(f"SQL-Fehler: {fehler}") from fehler

    # -- Innenleben ----------------------------------------------------

    def _festschreiben_falls_eigen(self, sql: str, war_offen: bool) -> None:
        """Schreibt fest, wenn erst die eben ausgeführte Anweisung die
        Transaktion geöffnet hat. Ein ausdrückliches ``BEGIN`` (oder
        ``SAVEPOINT``) öffnet sie auch, soll sie aber gerade offen
        halten."""
        verbindung = self.verbindung
        if war_offen or not verbindung.in_transaction:
            return
        worte = sql.lstrip().split(None, 1)
        if worte and worte[0].rstrip(";").upper() in ("BEGIN", "SAVEPOINT"):
            return
        try:
            verbindung.commit()
        except sqlite3.Error as fehler:
            # Scheitert das Festschreiben (die Datei ist gesperrt oder
            # schreibgeschützt), bliebe sonst die Transaktion offen.
            if verbindung.in_transaction:
                verbindung.rollback()
            raise NatterDatenbankError(f"SQL-Fehler: {fehler}") from fehler

    def _zeilen_holen(
        self, cursor: sqlite3.Cursor, war_offen: bool
    ) -> list[tuple[Any, ...]]:
        """Holt alle Zeilen eines ausgeführten Cursors. Manche Fehler
        bemerkt SQLite erst beim Holen weiterer Zeilen, etwa ungültiges
        JSON in der zweiten Zeile oder einen Überlauf in ``sum()``.
        Sie kamen vorher als rohe `sqlite3`-Ausnahme mit englischem
        Text im Schülerprogramm an (Punkt 263)."""
        verbindung = self.verbindung
        try:
            return cursor.fetchall()
        except sqlite3.Error as fehler:
            if not war_offen and verbindung.in_transaction:
                verbindung.rollback()
            raise NatterDatenbankError(f"SQL-Fehler: {fehler}") from fehler
        finally:
            cursor.close()

    def _ausfuehren(self, sql: str, parameter: dict[str, Any]) -> sqlite3.Cursor:
        verbindung = self.verbindung
        war_offen = verbindung.in_transaction
        try:
            cursor = verbindung.cursor()
            cursor.execute(sql, parameter)
        except sqlite3.Error as fehler:
            # Scheitert eine schreibende Anweisung (etwa an UNIQUE),
            # bleibt die Transaktion offen, die Python vor ihr selbst
            # begonnen hat, und mit ihr die Schreibsperre auf der Datei
            # (Punkt 238). Zurückgerollt wird nur, was diese Anweisung
            # geöffnet hat; eine vorher ausdrücklich begonnene
            # Transaktion bleibt für `commit()`/`rollback()` stehen.
            if not war_offen and verbindung.in_transaction:
                verbindung.rollback()
            if "no such table" in str(fehler):
                raise NatterDatenbankError(
                    self._meldung_fehlende_tabelle(fehler)
                ) from fehler
            raise NatterDatenbankError(f"SQL-Fehler: {fehler}") from fehler
        except OverflowError as fehler:
            # Eine Zahl über 64 Bit scheitert erst beim Binden des
            # Platzhalters, nachdem Python die Transaktion schon
            # geöffnet hat - und ist keine `sqlite3.Error`. Ohne das
            # Zurückrollen hier blieb die Transaktion offen, und jede
            # weitere Anweisung galt als Teil von ihr und ging beim
            # Programmende verloren.
            if not war_offen and verbindung.in_transaction:
                verbindung.rollback()
            raise NatterDatenbankError(
                "Die Zahl ist zu groß für eine Datenbankspalte "
                "(höchstens 9.223.372.036.854.775.807). Größere Zahlen "
                "lassen sich als Text speichern, etwa mit str(zahl)."
            ) from fehler
        except BaseException:
            if not war_offen and verbindung.in_transaction:
                verbindung.rollback()
            raise
        return cursor

    def _meldung_fehlende_tabelle(self, fehler: sqlite3.Error) -> str:
        """Meldung für eine Abfrage, deren Tabelle es nicht gibt, mit
        dem Namen der Datenbankdatei. `sqlite3.connect` legt eine
        fehlende Datei stillschweigend an. Bei einem Tippfehler im
        Dateinamen ging die Abfrage deshalb an eine neue, leere Datei,
        und die Meldung lenkte auf den Tabellennamen, der in der
        richtigen Datei stimmte (Punkt 427)."""
        name = self.database_name
        if not name or name == ":memory:":
            return f"SQL-Fehler: {fehler}"
        meldung = f"SQL-Fehler in der Datei „{name}“: {fehler}."
        try:
            (anzahl,) = self.verbindung.execute(
                "SELECT count(*) FROM sqlite_master WHERE type = 'table'"
            ).fetchone()
        except sqlite3.Error:
            anzahl = None
        if self._neu_angelegt:
            grund = (
                "Die Datei gab es vorher nicht, sie wurde beim Verbinden "
                "neu angelegt."
            )
        elif anzahl == 0:
            grund = "Die Datei enthält keine einzige Tabelle."
        else:
            return meldung
        return (
            f"{meldung} {grund} Wahrscheinlich ist eine andere "
            "Datenbankdatei gemeint. Ist der Dateiname richtig "
            "geschrieben?"
        )

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        if name != "connected":
            return
        if wert:
            self._verbindung_oeffnen()
        else:
            self._verbindung_schliessen()

    def _verbindung_oeffnen(self) -> None:
        ziel = self.database_name or ":memory:"
        self._neu_angelegt = (
            ziel != ":memory:" and not Path(ziel).exists()
        )
        try:
            self._verbindung = sqlite3.connect(ziel)
        except sqlite3.Error as fehler:
            # connected wurde von Prop.__set__ bereits auf True gesetzt,
            # bevor dieser Hook lief - bei Fehlschlag zurücksetzen, damit
            # `connected` nicht fälschlich True bleibt (siehe
            # Prop._speicher_name in pcl/properties.py).
            self.__dict__["_prop_connected"] = False
            ziel = repr(self.database_name or ":memory:")
            raise NatterDatenbankError(
                f"Verbindung zu {ziel} fehlgeschlagen: {fehler}"
            ) from fehler
        self._abschluss = weakref.finalize(
            self, _abschliessen, self._verbindung, Path(ziel).name
        )

    def _verbindung_schliessen(self) -> None:
        if self._abschluss is not None:
            self._abschluss()
            self._abschluss = None
        self._verbindung = None


class _Feld:
    """Ergebnis von ``SQLQuery.field_by_name()``:
    ein einzelner Zellenwert des aktuellen Datensatzes, typisiert
    abrufbar."""

    def __init__(self, wert: Any) -> None:
        self._wert = wert

    @property
    def value(self) -> Any:
        return self._wert

    @property
    def as_string(self) -> str:
        """Der Wert als Text, wie ihn die Data Controls zeigen: ein
        leeres Feld als "", eine Kommazahl mit Dezimalkomma."""
        return anzeigetext(self._wert)

    @property
    def as_integer(self) -> int:
        """Der Wert als ganze Zahl, ein leeres Feld als 0."""
        if self._wert is None:
            return 0
        try:
            if isinstance(self._wert, str):
                return int(self._wert.strip())
            return int(self._wert)
        except (TypeError, ValueError):
            raise NatterDatenError(
                f"Der Wert {self._wert!r} lässt sich nicht als ganze Zahl lesen."
            ) from None

    @property
    def as_float(self) -> float:
        """Der Wert als Kommazahl, ein leeres Feld als 0,0.

        Ein Text mit Dezimalkomma („2,5“) wird verstanden: so steht
        eine Zahl in einer Tabelle, die jemand mit deutscher
        Einstellung gefüllt hat.
        """
        if self._wert is None:
            return 0.0
        try:
            if isinstance(self._wert, str):
                return float(self._wert.strip().replace(",", "."))
            return float(self._wert)
        except (TypeError, ValueError):
            raise NatterDatenError(
                f"Der Wert {self._wert!r} lässt sich nicht als Kommazahl lesen."
            ) from None

    def __repr__(self) -> str:
        return f"_Feld({self._wert!r})"


class SQLQuery(Komponente):
    """Eine Abfrage mit Datensatzzeiger – der Unterbau der Data
    Controls (`DBGrid`, `DBEdit`, `DBNavigator`).

    Für gewöhnlichen Schülercode ist das nicht der Weg: dafür gibt es
    `SQLite3Connection.query()`, das in einer Zeile dasselbe tut. `SQLQuery`
    wird gebraucht, wo ein `DBNavigator` einen Zeiger vor- und
    zurückbewegen können muss – das kann eine Liste von `dict`s nicht.

    ``open()`` liest das gesamte Ergebnis auf einmal ein (gepuffert),
    ``exec_sql()`` führt schreibende Anweisungen aus und schreibt sie
    sofort fest.
    """

    neue_attribute_erlaubt = True

    sql = Prop(str, "", kategorie="Datenbank", doc="SQL-Anweisung mit :name-Platzhaltern")

    def __init__(self, database: SQLite3Connection) -> None:
        self.database = database
        self.params: dict[str, Any] = {}
        self._cursor: Any = None
        self._zeilen: list[tuple[Any, ...]] = []
        self._index: int = -1
        self._spalten: list[str] = []
        #: Zählt jede Änderung an den gepufferten Zeilen. Ein `DBGrid`
        #: erkennt daran, ob es sich neu füllen muss oder ob nur der
        #: Datensatzzeiger gewandert ist (Punkt 260).
        self._stand = 0

    def open(self) -> None:
        """Führt ``sql`` aus (SELECT), liest alle Zeilen und
        positioniert auf den ersten Datensatz, falls vorhanden.

        Steht hier doch eine schreibende Anweisung, wird sie wie bei
        `exec_sql()` festgeschrieben."""
        war_offen = self.database.verbindung.in_transaction
        self._ausfuehren()
        self._zeilen = self.database._zeilen_holen(self._cursor, war_offen)
        self._index = 0 if self._zeilen else -1
        self._stand += 1
        # Ein INSERT über `open()` statt `exec_sql()` öffnet sonst eine
        # Transaktion, die niemand schließt: die Zeile erscheint im
        # eigenen DBGrid, geht beim Programmende aber verloren, und
        # die Datei bleibt für alle anderen gesperrt (Punkt 287, wie
        # Punkt 238 für `query()`).
        self.database._festschreiben_falls_eigen(self.sql, war_offen)

    def exec_sql(self) -> None:
        """Führt ``sql`` aus (INSERT/UPDATE/DELETE) und schreibt die
        Änderung sofort fest, außer innerhalb einer mit ``BEGIN``
        begonnenen Transaktion (siehe `SQLite3Connection.execute`)."""
        war_offen = self.database.verbindung.in_transaction
        self._ausfuehren()
        self._zeilen = []
        self._index = -1
        self._stand += 1
        self.database._festschreiben_falls_eigen(self.sql, war_offen)

    def next(self) -> None:
        if self._cursor is None:
            raise NatterDatenbankError("SQLQuery.next() ohne vorheriges open() aufgerufen.")
        # Einen Schritt hinter den letzten Datensatz darf der Zeiger:
        # dort steht `eof` auf wahr, und die übliche Schleife
        # ``while not q.eof: ...; q.next()`` endet. Weiter nicht, sonst
        # käme `prior()` danach nicht mehr auf den letzten zurück.
        if self._index < len(self._zeilen):
            self._index += 1

    def prior(self) -> None:
        if self._cursor is None:
            raise NatterDatenbankError("SQLQuery.prior() ohne vorheriges open() aufgerufen.")
        if self._index > 0:
            self._index -= 1

    def first(self) -> None:
        if self._cursor is None:
            raise NatterDatenbankError("SQLQuery.first() ohne vorheriges open() aufgerufen.")
        self._index = 0 if self._zeilen else -1

    def last(self) -> None:
        if self._cursor is None:
            raise NatterDatenbankError("SQLQuery.last() ohne vorheriges open() aufgerufen.")
        self._index = len(self._zeilen) - 1 if self._zeilen else -1

    def _zeiger_setzen(self, index: int) -> None:
        """Setzt den Datensatzzeiger auf eine Zeile - für ein `DBGrid`,
        in dem jemand eine Zeile anklickt."""
        if 0 <= index < len(self._zeilen):
            self._index = index

    @property
    def eof(self) -> bool:
        return self._index < 0 or self._index >= len(self._zeilen)

    @property
    def record_count(self) -> int:
        return len(self._zeilen)

    @property
    def record_index(self) -> int:
        return self._index

    @property
    def column_names(self) -> list[str]:
        return list(self._spalten)

    def all_rows(self) -> list[tuple[Any, ...]]:
        """Alle gepufferten Zeilen (für `DBGrid`), ohne den
        Datensatzzeiger zu bewegen."""
        return list(self._zeilen)

    def field_by_name(self, name: str) -> _Feld:
        if self.eof:
            raise NatterDatenbankError(
                f"field_by_name({name!r}) ohne aktuellen Datensatz aufgerufen."
            )
        return _Feld(self._zeilen[self._index][self._spalten_index(name)])

    def set_field(self, name: str, wert: Any) -> None:
        """Ändert ein Feld der aktuellen Zeile im Puffer (für `DBEdit`) –
        wirkt nur auf den lokalen Zwischenspeicher, nicht auf die
        Datenbank; dauerhaft wird die Änderung erst durch eigenen
        SQL-Code (`sql`/`exec_sql()`)."""
        if self.eof:
            raise NatterDatenbankError(f"set_field({name!r}) ohne aktuellen Datensatz aufgerufen.")
        index = self._spalten_index(name)
        zeile = list(self._zeilen[self._index])
        zeile[index] = wert
        self._zeilen[self._index] = tuple(zeile)
        self._stand += 1

    def _spalten_index(self, name: str) -> int:
        try:
            return self._spalten.index(name)
        except ValueError as fehler:
            raise NatterDatenbankError(
                f"Spalte {name!r} ist nicht vorhanden. Vorhandene Spalten: "
                f"{', '.join(self._spalten)}."
            ) from fehler

    def close(self) -> None:
        if self._cursor is not None:
            self._cursor.close()
        self._cursor = None
        self._zeilen = []
        self._index = -1
        self._spalten = []
        self._stand += 1

    def to_dataframe(self) -> Any:
        """Führt ``sql`` aus (SELECT) und liefert das vollständige
        Ergebnis als pandas-`DataFrame` (Abschnitt 11.6). Eine
        schreibende Anweisung wird wie bei `open()` festgeschrieben.

        Gelesen wird mit einem eigenen Cursor. Puffer, Spalten und
        Datensatzzeiger der Abfrage bleiben, wie sie sind: vorher rief
        die Methode am Ende `close()` auf, und `DBGrid`, `DBText` und
        `DBNavigator` an derselben Abfrage reagierten danach auf nichts
        mehr, ohne dass es eine Meldung gab (Punkt 426)."""
        import pandas as pd

        war_offen = self.database.verbindung.in_transaction
        cursor = self.database._ausfuehren(self.sql, dict(self.params))
        spalten = [beschreibung[0] for beschreibung in cursor.description or []]
        zeilen = self.database._zeilen_holen(cursor, war_offen)
        self.database._festschreiben_falls_eigen(self.sql, war_offen)
        return pd.DataFrame(zeilen, columns=spalten)

    def _ausfuehren(self) -> None:
        cursor = self.database._ausfuehren(self.sql, dict(self.params))
        self._cursor = cursor
        self._spalten = [beschreibung[0] for beschreibung in cursor.description or []]


class DataSource(Komponente):
    """Bindeglied zwischen einer `SQLQuery` und den Data Controls:
    ``dataset`` verweist auf die anzuzeigende Abfrage.

    Vereinfachung, bewusst dokumentiert: die gebundenen Controls
    erfahren nichts von selbst, `aktualisieren()` löst die
    Benachrichtigung ausdrücklich aus – von
    `DBNavigator` intern nach jeder Navigation, sonst nach eigenem
    `query.open()`/`query.set_field()` selbst aufzurufen."""

    neue_attribute_erlaubt = True

    def __init__(self, dataset: SQLQuery | None = None) -> None:
        self.dataset = dataset
        # Schwache Verweise auf die Methoden der Data Controls. Ein
        # starker Verweis hielt jedes Steuerelement fest, auch wenn
        # sein Formular längst geschlossen war: ein Programm, das je
        # Datensatz ein Detailfenster öffnet, behielt alle im Speicher
        # und aktualisierte sie bei jeder Navigation mit (Punkt 245).
        self._listener: list[Callable[[], Callable[[], None] | None]] = []

    def aktualisieren(self) -> None:
        """Benachrichtigt alle gebundenen Data Controls, ihre Anzeige
        anhand des aktuellen Zustands von `dataset` zu erneuern."""
        for aufruf in self._lebende_listener():
            aufruf()

    def _lebende_listener(self) -> list[Callable[[], None]]:
        """Die noch erreichbaren Aufrufe; verwaiste Einträge fallen
        dabei aus der Liste."""
        lebend = []
        verweise = []
        for verweis in self._listener:
            aufruf = verweis()
            if aufruf is not None:
                lebend.append(aufruf)
                verweise.append(verweis)
        self._listener = verweise
        return lebend

    def _registrieren(self, aufruf: Callable[[], None]) -> None:
        if aufruf in self._lebende_listener():
            return
        if hasattr(aufruf, "__self__"):
            self._listener.append(weakref.WeakMethod(aufruf))
        else:
            self._listener.append(lambda: aufruf)

    def _abmelden(self, aufruf: Callable[[], None]) -> None:
        """Gegenstück zu `_registrieren`: ein Steuerelement, das eine
        andere Quelle bekommt oder zerstört wird, meldet sich ab."""
        self._listener = [
            verweis
            for verweis in self._listener
            if verweis() not in (None, aufruf)
        ]
