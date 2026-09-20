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

Warum nur SQLite. Früher gab es hier zusätzlich
`MySQLConnection` über PyMySQL, mit `host_name`, `port`, `user_name` und
`password`. Das Passwort war ein `Prop` und wäre damit im Klartext in
der `.pfm` gelandet, sobald eine Verbindung als Symbol auf dem Formular
liegt – in einer Datei also, die Lernende abgeben und herumtragen. Auf
den Vorschlag, das durch einen Schlüsselspeicher abzusichern, kam vom
Nutzer die Gegenrichtung: „nimm das passwort raus und mache die
datenbank abfrage einfacher. das wird zu kompliziert oder?" Eine
Datenbankdatei neben dem Programm läuft ohne Server, ohne Netz und ohne
Zugangsdaten auf jedem Schulrechner; mehr braucht der Unterricht nicht.
Seither kennt Natter überhaupt kein Datenbank-Passwort mehr.

Warum keine `SQLTransaction` mehr. `query`/`execute` schreiben
sofort fest (Auto-Commit). Eine eigene Komponente, die man nur anlegt,
um `commit` darauf zu rufen, erklärt sich nicht von selbst – wer
mehrere Anweisungen zusammenfassen will, findet `commit` und
`rollback` an der Verbindung.

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
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pcl.errors import NatterDatenbankError
from pcl.properties import Komponente, Prop


class SQLite3Connection(Komponente):
    """Verbindung zu einer SQLite-Datenbank (entspricht
    ``TSQLite3Connection`` in Lazarus). ``database_name`` ist ein
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

    def query(self, sql: str, **parameter: Any) -> list[dict[str, Any]]:
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
        """
        cursor = self._ausfuehren(sql, parameter)
        spalten = [beschreibung[0] for beschreibung in cursor.description or []]
        zeilen = [dict(zip(spalten, zeile, strict=True)) for zeile in cursor.fetchall()]
        cursor.close()
        return zeilen

    def query_one(self, sql: str, **parameter: Any) -> dict[str, Any] | None:
        """Wie `query()`, liefert aber nur die erste Zeile – oder
        ``None``, wenn die Abfrage nichts findet::

            konto = db.query_one("SELECT * FROM konto WHERE nummer = :nr", nr=7)
            if konto is None:
                self.l_meldung.caption = "Kein Konto mit dieser Nummer."
        """
        zeilen = self.query(sql, **parameter)
        return zeilen[0] if zeilen else None

    def execute(self, sql: str, **parameter: Any) -> int:
        """Führt eine schreibende Anweisung aus (INSERT, UPDATE, DELETE,
        CREATE TABLE) und schreibt sie sofort fest. Liefert die Anzahl
        der betroffenen Zeilen::

            db.execute("INSERT INTO konto (inhaber) VALUES (:wer)", wer=name)
            gelöscht = db.execute("DELETE FROM konto WHERE stand = 0")
        """
        cursor = self._ausfuehren(sql, parameter)
        anzahl = cursor.rowcount
        cursor.close()
        self.verbindung.commit()
        return max(anzahl, 0)

    def commit(self) -> None:
        """Schreibt offene Änderungen fest. Wird nur gebraucht, wenn
        jemand bewusst an der Verbindung selbst gearbeitet hat –
        `execute()` schreibt von sich aus fest."""
        self.verbindung.commit()

    def rollback(self) -> None:
        """Verwirft offene Änderungen."""
        self.verbindung.rollback()

    # -- Innenleben ----------------------------------------------------

    def _ausfuehren(self, sql: str, parameter: dict[str, Any]) -> sqlite3.Cursor:
        try:
            cursor = self.verbindung.cursor()
            cursor.execute(sql, parameter)
        except sqlite3.Error as fehler:
            raise NatterDatenbankError(f"SQL-Fehler: {fehler}") from fehler
        return cursor

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        if name != "connected":
            return
        if wert:
            self._verbindung_oeffnen()
        else:
            self._verbindung_schliessen()

    def _verbindung_oeffnen(self) -> None:
        try:
            self._verbindung = sqlite3.connect(self.database_name or ":memory:")
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

    def _verbindung_schliessen(self) -> None:
        if self._verbindung is not None:
            self._verbindung.close()
            self._verbindung = None


class _Feld:
    """Ergebnis von ``SQLQuery.field_by_name()`` (entspricht ``TField``):
    ein einzelner Zellenwert des aktuellen Datensatzes, typisiert
    abrufbar."""

    def __init__(self, wert: Any) -> None:
        self._wert = wert

    @property
    def value(self) -> Any:
        return self._wert

    @property
    def as_string(self) -> str:
        return "" if self._wert is None else str(self._wert)

    @property
    def as_integer(self) -> int:
        return 0 if self._wert is None else int(self._wert)

    @property
    def as_float(self) -> float:
        return 0.0 if self._wert is None else float(self._wert)

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

    def open(self) -> None:
        """Führt ``sql`` aus (SELECT), liest alle Zeilen und
        positioniert auf den ersten Datensatz, falls vorhanden."""
        self._ausfuehren()
        self._zeilen = self._cursor.fetchall()
        self._index = 0 if self._zeilen else -1

    def exec_sql(self) -> None:
        """Führt ``sql`` aus (INSERT/UPDATE/DELETE) und schreibt die
        Änderung sofort fest."""
        self._ausfuehren()
        self._zeilen = []
        self._index = -1
        self.database.verbindung.commit()

    def next(self) -> None:
        if self._cursor is None:
            raise NatterDatenbankError("SQLQuery.next() ohne vorheriges open() aufgerufen.")
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

    def to_dataframe(self) -> Any:
        """Führt ``sql`` aus (SELECT) und liefert das vollständige
        Ergebnis als pandas-`DataFrame` (Abschnitt 11.6)."""
        import pandas as pd

        self._ausfuehren()
        zeilen = self._cursor.fetchall()
        spalten = list(self._spalten)
        self.close()
        return pd.DataFrame(zeilen, columns=spalten)

    def _ausfuehren(self) -> None:
        cursor = self.database._ausfuehren(self.sql, dict(self.params))
        self._cursor = cursor
        self._spalten = [beschreibung[0] for beschreibung in cursor.description or []]


class DataSource(Komponente):
    """Bindeglied zwischen einer `SQLQuery` und den Data Controls:
    ``dataset`` verweist auf die anzuzeigende Abfrage.

    Vereinfachung, bewusst dokumentiert: anders als `TDataSet` in
    Lazarus, das gebundene Controls automatisch benachrichtigt, ruft hier
    `aktualisieren()` die Benachrichtigung bewusst explizit aus – von
    `DBNavigator` intern nach jeder Navigation, sonst nach eigenem
    `query.open()`/`query.set_field()` selbst aufzurufen."""

    neue_attribute_erlaubt = True

    def __init__(self, dataset: SQLQuery | None = None) -> None:
        self.dataset = dataset
        self._listener: list[Callable[[], None]] = []

    def aktualisieren(self) -> None:
        """Benachrichtigt alle gebundenen Data Controls, ihre Anzeige
        anhand des aktuellen Zustands von `dataset` zu erneuern."""
        for aufruf in self._listener:
            aufruf()

    def _registrieren(self, aufruf: Callable[[], None]) -> None:
        self._listener.append(aufruf)
