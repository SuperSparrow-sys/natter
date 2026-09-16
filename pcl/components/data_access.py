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
    über ``params`` (Stil ``:name``) verhindern SQL-Injection."""

    neue_attribute_erlaubt = True

    sql = Prop(str, "", kategorie="Datenbank", doc="SQL-Anweisung mit :name-Platzhaltern")

    def __init__(self, database: _Datenbankverbindung) -> None:
        self.database = database
        self.params: dict[str, Any] = {}
        self._cursor: Any = None
        self._zeile: tuple[Any, ...] | None = None
        self._spalten: list[str] = []

    def open(self) -> None:
        """Führt ``sql`` aus (SELECT) und positioniert auf den ersten
        Datensatz, falls vorhanden."""
        self._ausfuehren()
        self._zeile = self._cursor.fetchone()

    def exec_sql(self) -> None:
        """Führt ``sql`` aus (INSERT/UPDATE/DELETE). Wird erst mit
        ``transaction.commit()`` dauerhaft."""
        self._ausfuehren()

    def next(self) -> None:
        if self._cursor is None:
            raise NatterDatenbankError("SQLQuery.next() ohne vorheriges open() aufgerufen.")
        self._zeile = self._cursor.fetchone()

    @property
    def eof(self) -> bool:
        return self._zeile is None

    def field_by_name(self, name: str) -> _Feld:
        if self._zeile is None:
            raise NatterDatenbankError(
                f"field_by_name({name!r}) ohne aktuellen Datensatz aufgerufen."
            )
        try:
            index = self._spalten.index(name)
        except ValueError as fehler:
            raise NatterDatenbankError(
                f"Spalte {name!r} ist nicht vorhanden. Vorhandene Spalten: "
                f"{', '.join(self._spalten)}."
            ) from fehler
        return _Feld(self._zeile[index])

    def close(self) -> None:
        if self._cursor is not None:
            self._cursor.close()
        self._cursor = None
        self._zeile = None
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
    Schritt 5): ``dataset`` verweist auf die anzuzeigende Abfrage."""

    neue_attribute_erlaubt = True

    def __init__(self, dataset: SQLQuery | None = None) -> None:
        self.dataset = dataset
