"""Tests für die Datenbank-Komponenten (Abschnitt 10.1). Läuft gegen
echtes `sqlite3` aus der Standardbibliothek, kein Mock, in aller Regel
gegen `:memory:`.

Zwei Teile, entsprechend den zwei Wegen in
`pcl/components/data_access.py`: zuerst der kurze Weg
(`query`/`query_one`/`execute`), der seit September 2026 der Normalweg
ist, danach `SQLQuery` mit Datensatzzeiger als Unterbau der Data
Controls.
"""

from __future__ import annotations

import pytest

from pcl import DataSource, SQLite3Connection, SQLQuery
from pcl.errors import NatterDatenbankError


def _verbunden() -> SQLite3Connection:
    verbindung = SQLite3Connection()
    verbindung.connected = True
    return verbindung


def _mit_konten() -> SQLite3Connection:
    db = SQLite3Connection(":memory:")
    db.execute("CREATE TABLE konto (nummer INTEGER PRIMARY KEY, inhaber TEXT, stand REAL)")
    db.execute("INSERT INTO konto (inhaber, stand) VALUES (:wer, :was)", wer="Anna", was=120.5)
    db.execute("INSERT INTO konto (inhaber, stand) VALUES (:wer, :was)", wer="Bert", was=12.0)
    return db


# -- Verbindung ---------------------------------------------------------


def test_konstruktor_mit_dateinamen_oeffnet_die_verbindung_sofort() -> None:
    """Der kurze Weg: `SQLite3Connection("datei.sqlite")` statt drei
    Zeilen Aufbau."""
    db = SQLite3Connection(":memory:")
    assert db.connected is True
    assert db.database_name == ":memory:"
    assert db.verbindung is not None


def test_konstruktor_ohne_argument_laesst_die_verbindung_zu() -> None:
    """Der ausführliche Weg bleibt bestehen - er wird gebraucht, wenn
    die Verbindung erst später aufgebaut werden soll."""
    db = SQLite3Connection()
    assert db.connected is False
    db.database_name = ":memory:"
    db.connected = True
    assert db.verbindung is not None


def test_konstruktor_nimmt_auch_einen_pfad(tmp_path) -> None:
    db = SQLite3Connection(tmp_path / "konten.sqlite")
    assert db.connected is True
    assert (tmp_path / "konten.sqlite").exists()


def test_connected_false_schliesst_die_verbindung() -> None:
    db = _verbunden()
    db.connected = False
    with pytest.raises(NatterDatenbankError):
        _ = db.verbindung


def test_zugriff_ohne_verbindung_nennt_beide_wege() -> None:
    """Die Meldung muss sagen, was zu tun ist - für Lernende ist
    „keine offene Verbindung" allein keine Hilfe."""
    db = SQLite3Connection()
    with pytest.raises(NatterDatenbankError) as fehler:
        _ = db.verbindung
    text = str(fehler.value)
    assert 'SQLite3Connection("daten.sqlite")' in text
    assert "connected = True" in text


def test_verbindung_zu_ungueltigem_pfad_loest_natter_fehler_aus(tmp_path) -> None:
    db = SQLite3Connection()
    db.database_name = str(tmp_path / "nicht" / "vorhanden" / "db.sqlite")
    with pytest.raises(NatterDatenbankError):
        db.connected = True
    assert db.connected is False


def test_es_gibt_keine_mysql_verbindung_mehr() -> None:
    """September 2026: MySQL/MariaDB ist ersatzlos entfallen, damit es
    in Natter überhaupt kein Datenbank-Passwort mehr gibt (siehe
    Modulkopf von `pcl/components/data_access.py`)."""
    import pcl

    assert not hasattr(pcl, "MySQLConnection")
    assert not hasattr(pcl, "SQLTransaction")
    assert "password" not in dir(SQLite3Connection)


# -- Der kurze Weg: query / query_one / execute -------------------------


def test_query_liefert_die_zeilen_als_dicts() -> None:
    db = _mit_konten()
    zeilen = db.query("SELECT inhaber, stand FROM konto ORDER BY nummer")
    assert zeilen == [
        {"inhaber": "Anna", "stand": 120.5},
        {"inhaber": "Bert", "stand": 12.0},
    ]


def test_query_ohne_treffer_liefert_eine_leere_liste() -> None:
    db = _mit_konten()
    assert db.query("SELECT * FROM konto WHERE stand > 1000") == []


def test_query_nimmt_parameter_als_schluesselwortargumente() -> None:
    db = _mit_konten()
    zeilen = db.query("SELECT inhaber FROM konto WHERE stand >= :grenze", grenze=100)
    assert zeilen == [{"inhaber": "Anna"}]


def test_query_one_liefert_die_erste_zeile() -> None:
    db = _mit_konten()
    assert db.query_one("SELECT inhaber FROM konto ORDER BY nummer") == {"inhaber": "Anna"}


def test_query_one_ohne_treffer_liefert_none() -> None:
    db = _mit_konten()
    assert db.query_one("SELECT * FROM konto WHERE nummer = :n", n=999) is None


def test_execute_liefert_die_anzahl_betroffener_zeilen() -> None:
    db = _mit_konten()
    assert db.execute("UPDATE konto SET stand = 0") == 2
    assert db.execute("DELETE FROM konto WHERE stand > 500") == 0


def test_execute_schreibt_sofort_fest(tmp_path) -> None:
    """Auto-Commit, der eigentliche Grund, warum `SQLTransaction`
    entfallen konnte: eine zweite Verbindung auf dieselbe Datei muss die
    Daten sehen, ohne dass jemand `commit()` gerufen hat."""
    pfad = tmp_path / "konten.sqlite"
    erste = SQLite3Connection(pfad)
    erste.execute("CREATE TABLE t (x INTEGER)")
    erste.execute("INSERT INTO t (x) VALUES (:x)", x=7)

    zweite = SQLite3Connection(pfad)
    assert zweite.query("SELECT x FROM t") == [{"x": 7}]


def test_rollback_verwirft_was_noch_nicht_festgeschrieben_ist() -> None:
    db = _mit_konten()
    db.verbindung.execute("INSERT INTO konto (inhaber, stand) VALUES ('Cem', 1)")
    db.rollback()
    assert db.query_one("SELECT COUNT(*) AS anzahl FROM konto") == {"anzahl": 2}


def test_commit_behaelt_was_an_der_verbindung_geaendert_wurde() -> None:
    db = _mit_konten()
    db.verbindung.execute("INSERT INTO konto (inhaber, stand) VALUES ('Cem', 1)")
    db.commit()
    db.rollback()
    assert db.query_one("SELECT COUNT(*) AS anzahl FROM konto") == {"anzahl": 3}


def test_parameter_verhindern_sql_injection() -> None:
    """Der Punkt, den der Lehrgang eigens erklärt - er muss auf dem
    kurzen Weg genauso gelten wie vorher."""
    db = _mit_konten()
    zeilen = db.query(
        "SELECT * FROM konto WHERE inhaber = :wer", wer="x' OR '1'='1"
    )
    assert zeilen == []


def test_sql_fehler_wird_zu_einem_natter_fehler() -> None:
    db = _mit_konten()
    with pytest.raises(NatterDatenbankError, match="SQL-Fehler"):
        db.query("SELECT * FROM nicht_vorhanden")


def test_unbekannte_spalte_faellt_beim_zugriff_auf_die_zeile_auf() -> None:
    db = _mit_konten()
    zeile = db.query_one("SELECT inhaber FROM konto")
    with pytest.raises(KeyError):
        _ = zeile["stand"]


# -- SQLQuery: der Unterbau der Data Controls ---------------------------


def test_sqlquery_liest_und_schreibt_weiterhin() -> None:
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


def test_sqlquery_eof_und_next_durchlaufen_alle_zeilen() -> None:
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


def test_sqlquery_exec_sql_schreibt_ohne_transaktion_fest(tmp_path) -> None:
    """`SQLTransaction` ist weg - `exec_sql()` muss selbst festschreiben,
    sonst stünde jedes Data-Control-Beispiel ohne Daten da."""
    pfad = tmp_path / "t.sqlite"
    erste = SQLite3Connection(pfad)
    anlegen = SQLQuery(erste)
    anlegen.sql = "CREATE TABLE t (n INTEGER)"
    anlegen.exec_sql()
    einfuegen = SQLQuery(erste)
    einfuegen.sql = "INSERT INTO t (n) VALUES (5)"
    einfuegen.exec_sql()

    zweite = SQLite3Connection(pfad)
    assert zweite.query("SELECT n FROM t") == [{"n": 5}]


def test_sqlquery_field_by_name_mit_unbekannter_spalte_nennt_die_vorhandenen() -> None:
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


def test_sqlquery_sql_fehler_loest_natter_datenbank_error_aus() -> None:
    verbindung = _verbunden()
    abfrage = SQLQuery(verbindung)
    abfrage.sql = "SELECT * FROM nicht_vorhanden"

    with pytest.raises(NatterDatenbankError, match="SQL-Fehler"):
        abfrage.open()


def test_data_source_verweist_auf_ein_query_objekt() -> None:
    verbindung = _verbunden()
    abfrage = SQLQuery(verbindung)
    quelle = DataSource(abfrage)
    assert quelle.dataset is abfrage
