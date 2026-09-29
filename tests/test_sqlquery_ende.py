"""`SQLQuery.next()` bleibt einen Schritt hinter dem letzten
Datensatz stehen (Punkt 130)."""

from pcl import SQLite3Connection, SQLQuery


def _abfrage_mit_drei_zeilen() -> SQLQuery:
    verbindung = SQLite3Connection(":memory:")
    verbindung.execute("CREATE TABLE t (name TEXT)")
    for name in ("Anna", "Ben", "Cem"):
        verbindung.execute("INSERT INTO t VALUES (:name)", name=name)
    abfrage = SQLQuery(verbindung)
    abfrage.sql = "SELECT name FROM t ORDER BY name"
    abfrage.open()
    return abfrage


def test_prior_nach_zweimal_next_hinter_dem_ende_findet_den_letzten() -> None:
    abfrage = _abfrage_mit_drei_zeilen()
    abfrage.last()
    abfrage.next()
    abfrage.next()
    assert abfrage.eof
    assert abfrage.record_index == 3
    abfrage.prior()
    assert not abfrage.eof
    assert abfrage.field_by_name("name").as_string == "Cem"


def test_schleife_mit_next_endet_weiter_mit_eof() -> None:
    abfrage = _abfrage_mit_drei_zeilen()
    namen = []
    while not abfrage.eof:
        namen.append(abfrage.field_by_name("name").as_string)
        abfrage.next()
    assert namen == ["Anna", "Ben", "Cem"]
