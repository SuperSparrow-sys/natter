"""SQLdb-Komponenten (Abschnitt 10.1): Verbindung, Transaktion, Abfrage,
Datenquelle – SQLite (M5, Schritt 1) und MySQL/MariaDB über PyMySQL (M5,
Schritt 2) hinter derselben Schnittstelle.

Objektverweise zwischen den Komponenten (``SQLQuery.database``,
``SQLTransaction.database``, ``DataSource.dataset``) sind bewusst
einfache Instanzattribute statt `Prop`, weil `Prop` nur Wertetypen (Text/
Zahl/Wahrheitswert) mit sinnvollem Standardwert kennt – eine Bindung an
eine andere Komponente im Objektinspektor (wie in Lazarus per Dropdown)
ist erst mit den Data Controls in Schritt 5 nötig und wird dort eigens
gelöst.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from typing import Any

import pymysql

from pcl.db import uebersetze_platzhalter
from pcl.errors import NatterDatenbankError
from pcl.properties import Komponente, Prop


class _Datenbankverbindung(Komponente):
    """Gemeinsame Basis für `SQLite3Connection` und `MySQLConnection`:
    öffnet/schließt die eigentliche DB-API-Verbindung über die
    `connected`-Prop. `SQLQuery` kennt nur diese Schnittstelle (samt
    `_platzhalterstil`/`_treiber_fehler`) und nie `sqlite3`/`PyMySQL`
    direkt."""

    connected = Prop(
        bool,
        False,
        kategorie="Datenbank",
        doc="Verbindung öffnen (True) bzw. schließen (False)",
    )

    _platzhalterstil = "named"
    _treiber_fehler: type[Exception] = Exception

    def __init__(self) -> None:
        self._verbindung: Any = None

    @property
    def verbindung(self) -> Any:
        if self._verbindung is None:
            raise NatterDatenbankError(
                f"{type(self).__name__}: keine offene Verbindung (connected = True setzen)."
            )
        return self._verbindung

    def _neue_verbindung(self) -> Any:
        raise NotImplementedError

    def _verbindungsziel_text(self) -> str:
        raise NotImplementedError

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        if name != "connected":
            return
        if wert:
            self._verbindung_oeffnen()
        else:
            self._verbindung_schliessen()

    def _verbindung_oeffnen(self) -> None:
        try:
            self._verbindung = self._neue_verbindung()
        except self._treiber_fehler as fehler:
            # connected wurde von Prop.__set__ bereits auf True gesetzt,
            # bevor dieser Hook lief - bei Fehlschlag zurücksetzen, damit
            # `connected` nicht fälschlich True bleibt (siehe
            # Prop._speicher_name in pcl/properties.py).
            self.__dict__["_prop_connected"] = False
            raise NatterDatenbankError(
                f"Verbindung zu {self._verbindungsziel_text()} fehlgeschlagen: {fehler}"
            ) from fehler

    def _verbindung_schliessen(self) -> None:
        if self._verbindung is not None:
            self._verbindung.close()
            self._verbindung = None


class SQLite3Connection(_Datenbankverbindung):
    """Verbindung zu einer SQLite-Datenbank (entspricht
    ``TSQLite3Connection`` in Lazarus). ``database_name`` ist ein
    Dateipfad oder ``":memory:"``."""

    database_name = Prop(
        str, "", kategorie="Datenbank", doc='Pfad zur Datenbankdatei oder ":memory:"'
    )

    _platzhalterstil = "named"
    _treiber_fehler = sqlite3.Error

    def _neue_verbindung(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database_name or ":memory:")

    def _verbindungsziel_text(self) -> str:
        return repr(self.database_name or ":memory:")


class MySQLConnection(_Datenbankverbindung):
    """Verbindung zu MySQL/MariaDB über PyMySQL (entspricht
    ``TMySQLConnection``/``TSQLConnector`` in Lazarus).

    **Zurückgestellt (siehe docs/arbeitspakete/M5.md, „Stolperstein
    MariaDB“):** hier nur gegen die reine Parameter-Übersetzung und
    Fehlerbehandlung bei fehlgeschlagener Verbindung getestet, nicht
    gegen eine echte laufende MariaDB-Instanz – der dafür vorgesehene
    Homeserver-Docker-Container existiert in dieser Entwicklungsumgebung
    nicht."""

    host_name = Prop(str, "localhost", kategorie="Datenbank", doc="Servername oder IP-Adresse")
    port = Prop(int, 3306, kategorie="Datenbank", doc="TCP-Port des Servers")
    database_name = Prop(str, "", kategorie="Datenbank", doc="Name der Datenbank")
    user_name = Prop(str, "", kategorie="Datenbank", doc="Benutzername")
    password = Prop(str, "", kategorie="Datenbank", doc="Passwort")

    _platzhalterstil = "pyformat"
    _treiber_fehler = pymysql.MySQLError

    def _neue_verbindung(self) -> pymysql.connections.Connection:
        return pymysql.connect(
            host=self.host_name,
            port=self.port,
            database=self.database_name,
            user=self.user_name,
            password=self.password,
        )

    def _verbindungsziel_text(self) -> str:
        return f"{self.host_name}/{self.database_name}"


class SQLTransaction(Komponente):
    """Wirkt auf die Verbindung ihrer zugehörigen Connection (Abschnitt
    10.1: ``transaction.commit()`` / ``.rollback()``)."""

    neue_attribute_erlaubt = True

    def __init__(self, database: _Datenbankverbindung) -> None:
        self.database = database

    def commit(self) -> None:
        self.database.verbindung.commit()

    def rollback(self) -> None:
        self.database.verbindung.rollback()


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
    """Eine SQL-Abfrage oder -Anweisung (Abschnitt 10.1):
    ``open()``/``next()``/``eof``/``field_by_name()``/``close()`` für
    SELECT, ``exec_sql()`` für INSERT/UPDATE/DELETE. Benannte Parameter
    über ``params`` (Stil ``:name``) verhindern SQL-Injection.

    ``open()`` liest das gesamte Ergebnis auf einmal ein (gepuffert,
    nicht Zeile für Zeile nachgeladen) – das hält `next()`/`eof` aus
    Schritt 1 unverändert nutzbar, erlaubt zusätzlich aber
    ``first()``/``prior()``/``last()`` und wahlfreien Zugriff auf alle
    Zeilen für die Data Controls (M5, Schritt 5: `DBGrid` zeigt alle
    Zeilen gleichzeitig an, `DBNavigator` bewegt einen Datensatzzeiger
    vor und zurück)."""

    neue_attribute_erlaubt = True

    sql = Prop(str, "", kategorie="Datenbank", doc="SQL-Anweisung mit :name-Platzhaltern")

    def __init__(self, database: _Datenbankverbindung) -> None:
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
        """Führt ``sql`` aus (INSERT/UPDATE/DELETE). Wird erst mit
        ``transaction.commit()`` dauerhaft."""
        self._ausfuehren()
        self._zeilen = []
        self._index = -1

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
        """Alle gepufferten Zeilen (Abschnitt 10.1, für `DBGrid`), ohne
        den Datensatzzeiger zu bewegen."""
        return list(self._zeilen)

    def field_by_name(self, name: str) -> _Feld:
        if self.eof:
            raise NatterDatenbankError(
                f"field_by_name({name!r}) ohne aktuellen Datensatz aufgerufen."
            )
        return _Feld(self._zeilen[self._index][self._spalten_index(name)])

    def set_field(self, name: str, wert: Any) -> None:
        """Ändert ein Feld der aktuellen Zeile im Puffer (Abschnitt 10.1,
        für `DBEdit`) – wirkt nur auf den lokalen Zwischenspeicher, nicht
        auf die Datenbank; dauerhaft wird die Änderung erst durch eigenen
        SQL-Code (`sql`/`exec_sql()`) plus `transaction.commit()`."""
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
        sql = uebersetze_platzhalter(self.sql, self.database._platzhalterstil)
        try:
            cursor = self.database.verbindung.cursor()
            cursor.execute(sql, dict(self.params))
        except self.database._treiber_fehler as fehler:
            raise NatterDatenbankError(f"SQL-Fehler: {fehler}") from fehler
        self._cursor = cursor
        self._spalten = [beschreibung[0] for beschreibung in cursor.description or []]


class DataSource(Komponente):
    """Bindeglied zwischen einer `SQLQuery` und den Data Controls (M5,
    Schritt 5): ``dataset`` verweist auf die anzuzeigende Abfrage.

    **Vereinfachung, bewusst dokumentiert:** anders als `TDataSet` in
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
