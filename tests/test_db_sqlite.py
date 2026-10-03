"""Tests für die Datenbank-Komponenten (Abschnitt 10.1). Läuft gegen
echtes `sqlite3` aus der Standardbibliothek, kein Mock, in aller Regel
gegen `:memory:`.

Zwei Teile, entsprechend den zwei Wegen in
`pcl/components/data_access.py`: zuerst der kurze Weg
(`query`/`query_one`/`execute`), der seither der Normalweg
ist, danach `SQLQuery` mit Datensatzzeiger als Unterbau der Data
Controls.
"""

from __future__ import annotations

import os
import sqlite3
import stat
from contextlib import closing

import pytest

from pcl import DataSource, SQLite3Connection, SQLQuery
from pcl.errors import NatterDatenbankError
from pcl.fehlerkatalog import _datenbankmeldung_eindeutschen


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


def test_query_mit_insert_schreibt_fest(tmp_path) -> None:
    """Punkt 238: `query()` mit einer schreibenden Anweisung ließ die
    Transaktion offen; eine zweite Verbindung sah die Zeile nicht und
    konnte nicht schreiben."""
    pfad = tmp_path / "daten.sqlite"
    erste = SQLite3Connection(pfad)
    erste.execute("CREATE TABLE x (n INTEGER)")
    erste.query("INSERT INTO x VALUES (1)")

    assert not erste.verbindung.in_transaction
    zweite = SQLite3Connection(pfad)
    assert zweite.query("SELECT n FROM x") == [{"n": 1}]


def test_gescheitertes_execute_laesst_keine_transaktion_offen(
    tmp_path,
) -> None:
    """Punkt 238: nach `UNIQUE constraint failed` blieb die Transaktion
    offen und mit ihr die Schreibsperre auf der Datei."""
    pfad = tmp_path / "daten.sqlite"
    erste = SQLite3Connection(pfad)
    erste.execute("CREATE TABLE x (n INTEGER UNIQUE)")
    erste.execute("INSERT INTO x VALUES (1)")
    with pytest.raises(NatterDatenbankError, match="UNIQUE"):
        erste.execute("INSERT INTO x VALUES (1)")

    assert not erste.verbindung.in_transaction
    zweite = SQLite3Connection(pfad)
    zweite.verbindung.execute("PRAGMA busy_timeout = 0")
    assert zweite.execute("INSERT INTO x VALUES (2)") == 1


def test_zu_grosse_zahl_laesst_keine_transaktion_offen(tmp_path) -> None:
    """Eine Zahl über 64 Bit scheitert beim Binden mit `OverflowError`,
    nicht mit einer `sqlite3.Error`. Danach blieb die Transaktion offen,
    und alles Weitere ging beim Schließen verloren."""
    pfad = tmp_path / "daten.sqlite"
    erste = SQLite3Connection(pfad)
    erste.execute("CREATE TABLE x (w TEXT, s INTEGER)")
    with pytest.raises(NatterDatenbankError, match="zu groß"):
        erste.execute("INSERT INTO x VALUES (:w, :s)", w="gross", s=2**70)

    assert not erste.verbindung.in_transaction
    erste.execute("INSERT INTO x VALUES ('danach', 1)")
    erste.connected = False
    zweite = SQLite3Connection(pfad)
    zweite.verbindung.execute("PRAGMA busy_timeout = 0")
    assert zweite.query("SELECT w FROM x") == [{"w": "danach"}]


def test_gescheitertes_execute_laesst_eine_eigene_transaktion_stehen() -> None:
    """Wer an der Verbindung selbst eine Transaktion begonnen hat,
    entscheidet selbst über `commit()` oder `rollback()`."""
    db = _mit_konten()
    db.verbindung.execute(
        "INSERT INTO konto (inhaber, stand) VALUES ('Cem', 1)"
    )
    with pytest.raises(NatterDatenbankError):
        db.execute("INSERT INTO nicht_vorhanden VALUES (1)")
    db.commit()
    assert db.query_one("SELECT COUNT(*) AS anzahl FROM konto") == {"anzahl": 3}


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


@pytest.mark.parametrize("weg", ["open", "to_dataframe"])
def test_sqlquery_mit_insert_schreibt_fest(tmp_path, weg: str) -> None:
    """Punkt 287: `open()` und `to_dataframe()` mit einer schreibenden
    Anweisung ließen die Transaktion offen; eine zweite Verbindung sah
    die Zeile nicht und bekam beim Schreiben „database is locked“."""
    pfad = tmp_path / "t.sqlite"
    erste = SQLite3Connection(pfad)
    erste.execute("CREATE TABLE t (n INTEGER)")
    abfrage = SQLQuery(erste)
    abfrage.sql = "INSERT INTO t (n) VALUES (5)"
    getattr(abfrage, weg)()

    assert not erste.verbindung.in_transaction
    zweite = SQLite3Connection(pfad)
    assert zweite.query("SELECT n FROM t") == [{"n": 5}]
    zweite.execute("INSERT INTO t (n) VALUES (6)")
    zweite.connected = False
    erste.connected = False


@pytest.mark.parametrize("weg", ["open", "to_dataframe"])
def test_sqlquery_laesst_eine_begonnene_transaktion_offen(
    tmp_path, weg: str
) -> None:
    """Nach ``BEGIN`` schreiben `open()` und `to_dataframe()` nicht
    fest; `rollback()` nimmt das INSERT zurück."""
    pfad = tmp_path / "t.sqlite"
    db = SQLite3Connection(pfad)
    db.execute("CREATE TABLE t (n INTEGER)")
    db.execute("BEGIN")
    abfrage = SQLQuery(db)
    abfrage.sql = "INSERT INTO t (n) VALUES (5)"
    getattr(abfrage, weg)()

    assert db.verbindung.in_transaction
    db.rollback()
    assert db.query("SELECT n FROM t") == []
    db.connected = False


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


# -- Zusammengehörende Anweisungen (Punkt 259) --------------------------


def _konten_in_datei(pfad) -> SQLite3Connection:  # noqa: ANN001
    db = SQLite3Connection(pfad)
    db.execute("CREATE TABLE konto (nr INTEGER PRIMARY KEY, stand INTEGER)")
    db.execute("INSERT INTO konto VALUES (1, 100), (2, 0)")
    return db


def _staende_von_aussen(pfad) -> list[tuple[int, int]]:  # noqa: ANN001
    with closing(sqlite3.connect(pfad)) as pruefung:
        return pruefung.execute(
            "SELECT nr, stand FROM konto ORDER BY nr"
        ).fetchall()


@pytest.mark.parametrize("weg", ["execute", "exec_sql"])
def test_rollback_nach_begin_nimmt_beide_anweisungen_zurueck(
    tmp_path, weg: str
) -> None:
    pfad = tmp_path / "bank.sqlite"
    db = _konten_in_datei(pfad)

    db.execute("BEGIN")
    for sql in (
        "UPDATE konto SET stand = stand - 50 WHERE nr = 1",
        "UPDATE konto SET stand = stand + 50 WHERE nr = 2",
    ):
        if weg == "execute":
            db.execute(sql)
        else:
            abfrage = SQLQuery(db)
            abfrage.sql = sql
            abfrage.exec_sql()
    assert db.verbindung.in_transaction
    db.rollback()

    assert db.query("SELECT stand FROM konto ORDER BY nr") == [
        {"stand": 100}, {"stand": 0},
    ]
    db.connected = False
    assert _staende_von_aussen(pfad) == [(1, 100), (2, 0)]


def test_commit_nach_begin_schreibt_beide_anweisungen_fest(tmp_path) -> None:
    pfad = tmp_path / "bank.sqlite"
    db = _konten_in_datei(pfad)

    db.execute("BEGIN")
    db.execute("UPDATE konto SET stand = stand - 50 WHERE nr = 1")
    db.execute("UPDATE konto SET stand = stand + 50 WHERE nr = 2")
    assert _staende_von_aussen(pfad) == [(1, 100), (2, 0)]
    db.commit()

    assert not db.verbindung.in_transaction
    assert _staende_von_aussen(pfad) == [(1, 50), (2, 50)]


# -- Späte Fehler und neue Meldungen (Punkt 263) -------------------------


@pytest.mark.parametrize("weg", ["query", "open", "to_dataframe"])
def test_fehler_erst_in_der_zweiten_zeile_kommt_deutsch_an(weg: str) -> None:
    db = SQLite3Connection(":memory:")
    db.execute("CREATE TABLE t (nr INTEGER, x TEXT)")
    db.execute("INSERT INTO t VALUES (1, '[1, 2]'), (2, '{kaputt')")
    sql = "SELECT json(x) AS j FROM t"

    with pytest.raises(NatterDatenbankError) as fehler:
        if weg == "query":
            db.query(sql)
        else:
            abfrage = SQLQuery(db)
            abfrage.sql = sql
            if weg == "open":
                abfrage.open()
            else:
                abfrage.to_dataframe()

    meldung = _datenbankmeldung_eindeutschen(str(fehler.value))
    assert meldung == "SQL-Fehler: ein Wert ist kein gültiges JSON"
    assert not db.verbindung.in_transaction


def test_schreiben_in_eine_schreibgeschuetzte_datei_kommt_deutsch_an(
    tmp_path,
) -> None:
    pfad = tmp_path / "material.sqlite"
    anlegen = SQLite3Connection(pfad)
    anlegen.execute("CREATE TABLE t (n INTEGER)")
    anlegen.connected = False
    os.chmod(pfad, stat.S_IREAD)
    try:
        db = SQLite3Connection(pfad)
        with pytest.raises(NatterDatenbankError) as fehler:
            db.execute("INSERT INTO t VALUES (1)")
        assert not db.verbindung.in_transaction
        db.connected = False
    finally:
        os.chmod(pfad, stat.S_IREAD | stat.S_IWRITE)

    meldung = _datenbankmeldung_eindeutschen(str(fehler.value))
    assert "schreibgeschützt" in meldung
    assert "readonly" not in meldung


@pytest.mark.parametrize(
    ("treiber", "deutsch"),
    [
        ("interrupted", "unterbrochen"),
        ("disk I/O error", "nicht lesen oder schreiben"),
        ("database disk image is malformed", "beschädigt"),
        ("integer overflow", "zu groß für eine ganze Zahl"),
    ],
)
def test_weitere_treibermeldungen_stehen_im_katalog(
    treiber: str, deutsch: str
) -> None:
    meldung = _datenbankmeldung_eindeutschen(f"SQL-Fehler: {treiber}")
    assert deutsch in meldung
    assert treiber not in meldung


# -- Tippfehler im Dateinamen (Punkt 427) -------------------------------


_ANDERE_DATEI = "Wahrscheinlich ist eine andere Datenbankdatei gemeint"


@pytest.mark.parametrize(
    ("fall", "hinweis"),
    [
        # Die Datei gibt es nicht, sie entsteht erst beim Verbinden.
        ("tippfehler", "vorher nicht"),
        # Die Datei gibt es schon, aber ohne eine einzige Tabelle.
        ("leere_datei", "keine einzige Tabelle"),
        # Die Datei hat Tabellen, nur die gesuchte fehlt: dann ist
        # eher der Tabellenname falsch als die Datei.
        ("andere_tabelle", None),
    ],
)
def test_fehlende_tabelle_nennt_die_datei(
    tmp_path, fall: str, hinweis: str | None
) -> None:
    richtig = SQLite3Connection(tmp_path / "konten.sqlite")
    richtig.execute("CREATE TABLE konto (nr INTEGER)")
    richtig.connected = False
    pfad = tmp_path / "konton.sqlite"
    if fall == "leere_datei":
        pfad.touch()
    elif fall == "andere_tabelle":
        with closing(sqlite3.connect(pfad)) as vorher:
            vorher.execute("CREATE TABLE kunde (nr INTEGER)")

    db = SQLite3Connection(pfad)
    with pytest.raises(NatterDatenbankError) as fehler:
        db.query("SELECT * FROM konto")
    db.connected = False

    meldung = _datenbankmeldung_eindeutschen(str(fehler.value))
    assert f"„{pfad}“" in meldung
    assert "eine Tabelle namens „konto“ gibt es" in meldung
    if hinweis is None:
        assert _ANDERE_DATEI not in meldung
    else:
        assert hinweis in meldung
        assert _ANDERE_DATEI in meldung


def test_fehlende_tabelle_im_arbeitsspeicher_nennt_keine_datei() -> None:
    db = SQLite3Connection(":memory:")
    with pytest.raises(NatterDatenbankError) as fehler:
        db.query("SELECT * FROM konto")
    meldung = _datenbankmeldung_eindeutschen(str(fehler.value))
    assert meldung == (
        "SQL-Fehler: eine Tabelle namens „konto“ gibt es in der "
        "Datenbank nicht"
    )


def test_werte_als_tupel_bekommen_einen_hinweis_auf_namen() -> None:
    """Punkt 486: ``execute("… (?)", (1,))`` wie in `sqlite3` endete in
    „nimmt 2 Angaben entgegen, übergeben wurden 3“."""
    db = SQLite3Connection(":memory:")
    db.execute("CREATE TABLE t (n INTEGER)")

    for aufruf in (db.execute, db.query, db.query_one):
        with pytest.raises(NatterDatenbankError, match=":name"):
            aufruf("SELECT * FROM t WHERE n = ?", (1,))


@pytest.mark.parametrize(
    ("sql", "deutsch"),
    [
        ("SELECT * FROM t WHERE a = 'Meier", "Anführungszeichen"),
        ("SELECT sum(a) FROM t WHERE sum(a) > 1", "HAVING"),
        ("SELECT (SELECT a, b FROM t)", "liefert 2 Spalten"),
        ("SELECT a FROM t GROUP BY sum(a)", "GROUP BY"),
        ("SELECT 1 UNION SELECT 1, 2", "verschieden viele"),
        ("SELECT * FROM t ORDER BY 3", "erlaubt sind die Nummern 1 bis 2"),
        ("SELECT abs(1, 2)", "Anzahl Werte"),
        ("CREATE TABLE sqlite_x (a)", "vorbehalten"),
    ],
)
def test_haeufige_sqlite_fehler_kommen_deutsch_an(sql: str, deutsch: str) -> None:
    """Punkt 566: diese Meldungen kamen englisch an."""
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE t (a, b)")
    with pytest.raises(sqlite3.Error) as fehler:
        db.execute(sql)
    db.close()

    meldung = _datenbankmeldung_eindeutschen(str(fehler.value))

    assert deutsch in meldung
    assert meldung != str(fehler.value)


@pytest.mark.parametrize(
    "treiber", ["database or disk is full", "too many columns on t"]
)
def test_volle_platte_und_zu_viele_spalten(treiber: str) -> None:
    meldung = _datenbankmeldung_eindeutschen(treiber)
    assert treiber not in meldung
