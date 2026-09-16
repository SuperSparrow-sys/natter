"""Tests für den SQLdb-Kern gegen SQLite (Abschnitt 10.1). Siehe
docs/arbeitspakete/M5.md, Schritt 1. Läuft gegen echtes `sqlite3`
(Standardbibliothek, kein Mock), immer `:memory:`.
"""

from __future__ import annotations

import pytest

from pcl import DataSource, SQLite3Connection, SQLQuery, SQLTransaction
from pcl.db import uebersetze_platzhalter
from pcl.errors import NatterDatenbankError


def test_uebersetze_platzhalter_named_bleibt_unveraendert() -> None:
    sql = "SELECT * FROM kunden WHERE ort = :ort AND aktiv = :aktiv"
    assert uebersetze_platzhalter(sql, "named") == sql


def test_uebersetze_platzhalter_pyformat_ersetzt_doppelpunkt_namen() -> None:
    sql = "SELECT * FROM kunden WHERE ort = :ort AND aktiv = :aktiv"
    erwartet = "SELECT * FROM kunden WHERE ort = %(ort)s AND aktiv = %(aktiv)s"
    assert uebersetze_platzhalter(sql, "pyformat") == erwartet


def test_uebersetze_platzhalter_mit_unbekanntem_stil_loest_value_error_aus() -> None:
    with pytest.raises(ValueError, match="Platzhalterstil"):
        uebersetze_platzhalter("SELECT 1", "qmark")


def _verbunden() -> SQLite3Connection:
    verbindung = SQLite3Connection()
    verbindung.connected = True
    return verbindung


def test_connected_oeffnet_und_schliesst_die_verbindung() -> None:
    verbindung = SQLite3Connection()
    assert verbindung.connected is False

    verbindung.connected = True
    assert verbindung.verbindung is not None

    verbindung.connected = False
    with pytest.raises(NatterDatenbankError):
        _ = verbindung.verbindung


def test_zugriff_ohne_verbindung_liefert_verstaendlichen_fehler() -> None:
    verbindung = SQLite3Connection()
    with pytest.raises(NatterDatenbankError, match="connected = True"):
        _ = verbindung.verbindung


def test_tabelle_anlegen_und_daten_einfuegen_und_lesen() -> None:
    verbindung = _verbunden()
    anlegen = SQLQuery(verbindung)
    anlegen.sql = "CREATE TABLE kunden (id INTEGER PRIMARY KEY, name TEXT, ort TEXT)"
    anlegen.exec_sql()

    einfuegen = SQLQuery(verbindung)
    einfuegen.sql = "INSERT INTO kunden (name, ort) VALUES (:name, :ort)"
    einfuegen.params["name"] = "Anna"
    einfuegen.params["ort"] = "Köln"
    einfuegen.exec_sql()

    lesen = SQLQuery(verbindung)
    lesen.sql = "SELECT * FROM kunden WHERE ort = :ort"
    lesen.params["ort"] = "Köln"
    lesen.open()

    assert lesen.eof is False
    assert lesen.field_by_name("name").as_string == "Anna"
    lesen.next()
    assert lesen.eof is True
    lesen.close()


def test_eof_und_next_durchlaufen_alle_zeilen() -> None:
    verbindung = _verbunden()
    anlegen = SQLQuery(verbindung)
    anlegen.sql = "CREATE TABLE t (n INTEGER)"
    anlegen.exec_sql()
    for wert in (1, 2, 3):
        einfuegen = SQLQuery(verbindung)
        einfuegen.sql = "INSERT INTO t (n) VALUES (:n)"
        einfuegen.params["n"] = wert
        einfuegen.exec_sql()

    lesen = SQLQuery(verbindung)
    lesen.sql = "SELECT n FROM t ORDER BY n"
    lesen.open()
    gelesen = []
    while not lesen.eof:
        gelesen.append(lesen.field_by_name("n").as_integer)
        lesen.next()
    assert gelesen == [1, 2, 3]


def test_field_by_name_mit_unbekannter_spalte_loest_natter_fehler_aus() -> None:
    verbindung = _verbunden()
    anlegen = SQLQuery(verbindung)
    anlegen.sql = "CREATE TABLE t (n INTEGER)"
    anlegen.exec_sql()
    einfuegen = SQLQuery(verbindung)
    einfuegen.sql = "INSERT INTO t (n) VALUES (1)"
    einfuegen.exec_sql()

    lesen = SQLQuery(verbindung)
    lesen.sql = "SELECT n FROM t"
    lesen.open()

    with pytest.raises(NatterDatenbankError, match="nicht vorhanden"):
        lesen.field_by_name("unbekannt")


def test_transaction_rollback_macht_aenderung_rueckgaengig() -> None:
    verbindung = _verbunden()
    anlegen = SQLQuery(verbindung)
    anlegen.sql = "CREATE TABLE t (n INTEGER)"
    anlegen.exec_sql()
    verbindung.verbindung.commit()

    transaktion = SQLTransaction(verbindung)
    einfuegen = SQLQuery(verbindung)
    einfuegen.sql = "INSERT INTO t (n) VALUES (1)"
    einfuegen.exec_sql()
    transaktion.rollback()

    lesen = SQLQuery(verbindung)
    lesen.sql = "SELECT COUNT(*) AS anzahl FROM t"
    lesen.open()
    assert lesen.field_by_name("anzahl").as_integer == 0


def test_transaction_commit_behaelt_aenderung() -> None:
    verbindung = _verbunden()
    anlegen = SQLQuery(verbindung)
    anlegen.sql = "CREATE TABLE t (n INTEGER)"
    anlegen.exec_sql()
    verbindung.verbindung.commit()

    transaktion = SQLTransaction(verbindung)
    einfuegen = SQLQuery(verbindung)
    einfuegen.sql = "INSERT INTO t (n) VALUES (1)"
    einfuegen.exec_sql()
    transaktion.commit()

    lesen = SQLQuery(verbindung)
    lesen.sql = "SELECT COUNT(*) AS anzahl FROM t"
    lesen.open()
    assert lesen.field_by_name("anzahl").as_integer == 1


def test_sql_fehler_loest_natter_datenbank_error_statt_roher_sqlite3_ausnahme() -> None:
    verbindung = _verbunden()
    abfrage = SQLQuery(verbindung)
    abfrage.sql = "SELECT * FROM nicht_vorhanden"

    with pytest.raises(NatterDatenbankError, match="SQL-Fehler"):
        abfrage.open()


def test_benannte_parameter_verhindern_sql_injection() -> None:
    verbindung = _verbunden()
    anlegen = SQLQuery(verbindung)
    anlegen.sql = "CREATE TABLE kunden (name TEXT)"
    anlegen.exec_sql()
    einfuegen = SQLQuery(verbindung)
    einfuegen.sql = "INSERT INTO kunden (name) VALUES (:name)"
    einfuegen.params["name"] = "Anna"
    einfuegen.exec_sql()

    bösartig = "x' OR '1'='1"
    lesen = SQLQuery(verbindung)
    lesen.sql = "SELECT * FROM kunden WHERE name = :name"
    lesen.params["name"] = bösartig
    lesen.open()
    assert lesen.eof is True


def test_data_source_verweist_auf_ein_query_objekt() -> None:
    verbindung = _verbunden()
    abfrage = SQLQuery(verbindung)
    quelle = DataSource(abfrage)
    assert quelle.dataset is abfrage


def test_datenbankverbindung_zu_ungueltiger_datei_loest_natter_fehler_aus(
    tmp_path,
) -> None:
    verbindung = SQLite3Connection()
    verbindung.database_name = str(tmp_path / "nicht" / "vorhanden" / "db.sqlite")
    with pytest.raises(NatterDatenbankError):
        verbindung.connected = True
    assert verbindung.connected is False
