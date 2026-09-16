"""Tests für die pandas-Anbindung (Abschnitt 11.6). Siehe
docs/arbeitspakete/M5.md, Schritt 3: `StringGrid.load_dataframe`/
`.to_dataframe()`, `SQLQuery.to_dataframe()`. Headless, gegen echtes
pandas und echtes `:memory:`-SQLite.
"""

from __future__ import annotations

import pandas as pd

from pcl import Form, SQLite3Connection, SQLQuery, StringGrid


class _Formular(Form):
    def create_components(self) -> None:
        self.sg_tabelle = StringGrid(self)


def test_load_dataframe_zeigt_spaltenkoepfe_und_werte() -> None:
    formular = _Formular()
    df = pd.DataFrame({"name": ["Anna", "Bo"], "punkte": [12, 7]})

    formular.sg_tabelle.load_dataframe(df)

    assert formular.sg_tabelle.row_count == 3  # Kopfzeile + 2 Datenzeilen
    assert formular.sg_tabelle.col_count == 2
    assert formular.sg_tabelle.cells[0, 0] == "name"
    assert formular.sg_tabelle.cells[1, 0] == "punkte"
    assert formular.sg_tabelle.cells[0, 1] == "Anna"
    assert formular.sg_tabelle.cells[1, 2] == "7"


def test_load_dataframe_zeigt_fehlende_werte_als_leerstring() -> None:
    formular = _Formular()
    df = pd.DataFrame({"wert": [1.0, None]})

    formular.sg_tabelle.load_dataframe(df)

    assert formular.sg_tabelle.cells[0, 2] == ""


def test_to_dataframe_liest_das_grid_zurueck() -> None:
    formular = _Formular()
    formular.sg_tabelle.row_count = 3
    formular.sg_tabelle.col_count = 2
    formular.sg_tabelle.cells[0, 0] = "name"
    formular.sg_tabelle.cells[1, 0] = "punkte"
    formular.sg_tabelle.cells[0, 1] = "Anna"
    formular.sg_tabelle.cells[1, 1] = "12"
    formular.sg_tabelle.cells[0, 2] = "Bo"
    formular.sg_tabelle.cells[1, 2] = "7"

    df = formular.sg_tabelle.to_dataframe()

    assert list(df.columns) == ["name", "punkte"]
    assert df.iloc[0].tolist() == ["Anna", "12"]
    assert df.iloc[1].tolist() == ["Bo", "7"]


def test_load_dataframe_dann_to_dataframe_ist_auf_textebene_verlustfrei() -> None:
    formular = _Formular()
    original = pd.DataFrame(
        {"name": ["Anna", "Bo"], "punkte": [12, 7], "aktiv": [True, False]}
    )

    formular.sg_tabelle.load_dataframe(original)
    zurueck = formular.sg_tabelle.to_dataframe()

    erwartet = original.astype(str).values.tolist()
    tatsaechlich = zurueck.values.tolist()
    assert tatsaechlich == erwartet


def test_load_dataframe_mit_leerem_dataframe_ergibt_nur_die_kopfzeile() -> None:
    formular = _Formular()
    df = pd.DataFrame({"name": [], "punkte": []})

    formular.sg_tabelle.load_dataframe(df)

    assert formular.sg_tabelle.row_count == 1
    assert formular.sg_tabelle.cells[0, 0] == "name"


def test_sqlquery_to_dataframe_liefert_alle_zeilen() -> None:
    verbindung = SQLite3Connection()
    verbindung.connected = True
    anlegen = SQLQuery(verbindung)
    anlegen.sql = "CREATE TABLE kunden (name TEXT, ort TEXT)"
    anlegen.exec_sql()
    for name, ort in (("Anna", "Köln"), ("Bo", "Bonn")):
        einfuegen = SQLQuery(verbindung)
        einfuegen.sql = "INSERT INTO kunden (name, ort) VALUES (:name, :ort)"
        einfuegen.params["name"] = name
        einfuegen.params["ort"] = ort
        einfuegen.exec_sql()

    abfrage = SQLQuery(verbindung)
    abfrage.sql = "SELECT name, ort FROM kunden ORDER BY name"
    df = abfrage.to_dataframe()

    assert list(df.columns) == ["name", "ort"]
    assert df.values.tolist() == [["Anna", "Köln"], ["Bo", "Bonn"]]
