"""Reste gestrichener Funktionen (offener Punkt 83).

`gui_db` und der MySQL-Treiber standen noch im Projekt-Schema und im
Export, `as_integer`/`as_float` meldeten Fehler auf Englisch.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ide.project import Projekt
from ide.schema import pruefen, schema_fehler
from pcl import SQLite3Connection, SQLQuery
from pcl.errors import NatterDatenError
from pcl.fehleranzeige import fehlertext

_WURZEL = Path(__file__).resolve().parents[1]
_SCHEMA = json.loads(
    (_WURZEL / "schemas" / "project.schema.json").read_text(encoding="utf-8")
)


def test_das_schema_kennt_gui_db_und_mysql_nicht_mehr() -> None:
    text = json.dumps(_SCHEMA)
    assert "gui_db" not in _SCHEMA["properties"]["type"]["enum"]
    assert "mysql" not in text
    assert "connection_ref" not in text
    with pytest.raises(schema_fehler()):
        pruefen(
            {"format": "natter-project/1", "name": "x", "type": "gui_db", "main": "main.py"},
            _SCHEMA,
        )


def test_im_code_verweist_nichts_mehr_darauf() -> None:
    treffer = []
    for ordner in ("ide", "pcl", "schemas", "templates"):
        for pfad in (_WURZEL / ordner).rglob("*"):
            if pfad.suffix not in (".py", ".json", ".template"):
                continue
            # Die eine Stelle, die alte Projektdateien beim Laden
            # angleicht, muss die alten Namen kennen.
            if pfad.name == "projekt.py":
                continue
            text = pfad.read_text(encoding="utf-8")
            for wort in ("MySQL", "mysql", "gui_db"):
                if wort in text:
                    treffer.append(f"{pfad.relative_to(_WURZEL)}: {wort}")
    assert not treffer, treffer


def test_es_gibt_keine_zugangsdaten_mehr() -> None:
    """Mit MySQL/MariaDB ist auch jedes Datenbank-Passwort entfallen
    (siehe Modulkopf von `pcl/components/data_access.py`). Den Namen
    `MySQLConnection` fängt schon die Suche oben ab, diese beiden
    nicht."""
    import pcl

    assert not hasattr(pcl, "SQLTransaction")
    assert "password" not in dir(SQLite3Connection)


def test_eine_alte_projektdatei_laesst_sich_noch_oeffnen(tmp_path: Path) -> None:
    (tmp_path / "Alt.natter").write_text(
        json.dumps(
            {
                "format": "natter-project/1",
                "name": "Alt",
                "type": "gui_db",
                "main": "main.py",
                "main_form": "u_main",
                "database": {"driver": "mysql", "connection_ref": "schule"},
            }
        ),
        encoding="utf-8",
    )

    projekt = Projekt.laden(tmp_path)

    assert projekt.typ == "gui"
    assert "database" not in projekt.daten
    projekt.speichern()
    gespeichert = json.loads((tmp_path / "Alt.natter").read_text(encoding="utf-8"))
    assert gespeichert["type"] == "gui"


def test_eine_sqlite_angabe_bleibt_ohne_zugangsdaten(tmp_path: Path) -> None:
    (tmp_path / "Alt.natter").write_text(
        json.dumps(
            {
                "format": "natter-project/1",
                "name": "Alt",
                "type": "gui",
                "main": "main.py",
                "database": {"driver": "sqlite3", "connection_ref": "x"},
            }
        ),
        encoding="utf-8",
    )

    assert Projekt.laden(tmp_path).daten["database"] == {"driver": "sqlite3"}


# --------------------------------------------- as_integer / as_float


def _feld(wert):
    db = SQLite3Connection(":memory:")
    db.execute("CREATE TABLE t (w)")
    db.execute("INSERT INTO t (w) VALUES (:w)", w=wert)
    abfrage = SQLQuery(db)
    abfrage.sql = "SELECT w FROM t"
    abfrage.open()
    return abfrage.field_by_name("w")


def test_zahlen_kommen_wie_bisher() -> None:
    assert _feld(42).as_integer == 42
    assert _feld("17").as_integer == 17
    assert _feld(2.5).as_float == 2.5
    assert _feld(None).as_integer == 0
    assert _feld(None).as_float == 0.0


def test_ein_dezimalkomma_wird_verstanden() -> None:
    assert _feld("2,5").as_float == 2.5


@pytest.mark.parametrize(
    ("wert", "art", "meldung"),
    [
        ("Anna", "as_integer", "'Anna' lässt sich nicht als ganze Zahl lesen"),
        ("2,5", "as_integer", "'2,5' lässt sich nicht als ganze Zahl lesen"),
        ("viel", "as_float", "'viel' lässt sich nicht als Kommazahl lesen"),
    ],
)
def test_ein_falscher_wert_meldet_sich_deutsch(wert, art, meldung) -> None:
    with pytest.raises(NatterDatenError, match=meldung) as fehler:
        getattr(_feld(wert), art)

    text = fehlertext(type(fehler.value), fehler.value, fehler.tb)
    assert meldung in text
    assert "invalid literal" not in text
