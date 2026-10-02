"""Tests für die pandas-Anbindung (Abschnitt 11.6). Siehe
Arbeitspaket M5, Schritt 3: `StringGrid.load_dataframe`/
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
    assert df.iloc[0].tolist() == ["Anna", 12]
    assert df.iloc[1].tolist() == ["Bo", 7]


def test_load_dataframe_dann_to_dataframe_gibt_zahlen_und_text_zurueck() -> None:
    formular = _Formular()
    original = pd.DataFrame(
        {"name": ["Anna", "Bo"], "punkte": [12, 7], "aktiv": [True, False]}
    )

    formular.sg_tabelle.load_dataframe(original)
    zurueck = formular.sg_tabelle.to_dataframe()

    assert zurueck.values.tolist() == [["Anna", 12, "True"], ["Bo", 7, "False"]]


def test_to_dataframe_liefert_zahlenspalten_zum_rechnen() -> None:
    """Punkt 216: alle Spalten kamen als Text zurück, `sum()` hängte
    „3“ und „4“ zu „34“ zusammen."""
    formular = _Formular()
    original = pd.DataFrame(
        {"Name": ["Anna", "Bo"], "Note": [1.5, 2.0], "Anzahl": [3, 4]}
    )

    formular.sg_tabelle.load_dataframe(original)
    df = formular.sg_tabelle.to_dataframe()

    assert formular.sg_tabelle.cells[1, 1] == "1,5"
    assert df["Anzahl"].sum() == 7
    assert pd.api.types.is_integer_dtype(df["Anzahl"])
    assert df["Note"].mean() == 1.75
    assert df["Name"].tolist() == ["Anna", "Bo"]


def test_to_dataframe_leere_zellen_sind_fehlende_werte() -> None:
    formular = _Formular()
    formular.sg_tabelle.col_count = 3
    formular.sg_tabelle.row_count = 4
    for spalte, kopf in enumerate(["ganz", "komma", "leer"]):
        formular.sg_tabelle.cells[spalte, 0] = kopf
    for zeile, (ganz, komma) in enumerate(
        [("1.000", "2,5"), ("", ""), ("5", "1")], start=1
    ):
        formular.sg_tabelle.cells[0, zeile] = ganz
        formular.sg_tabelle.cells[1, zeile] = komma

    df = formular.sg_tabelle.to_dataframe()

    assert df["ganz"].sum() == 1005
    assert df["ganz"].isna().tolist() == [False, True, False]
    assert df["komma"].sum() == 3.5
    assert df["leer"].tolist() == ["", "", ""]


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


def test_kommazahlen_erscheinen_mit_dezimalkomma(tmp_path) -> None:  # noqa: ANN001
    """Punkt 42 der offenen Punkte: eine mit `decimal=","` gelesene
    CSV zeigte im Grid „2.4“. Die ganze Zahl daneben blieb dabei nicht
    „1“, sondern wurde über `iterrows` zu „1.0“."""
    csv = tmp_path / "wetter.csv"
    csv.write_text("monat;temperatur\n1;2,4\n2;2,8\n3;5,1\n", encoding="utf-8")
    df = pd.read_csv(csv, sep=";", decimal=",")
    formular = _Formular()

    formular.sg_tabelle.load_dataframe(df)

    assert [formular.sg_tabelle.cells[1, z] for z in (1, 2, 3)] == ["2,4", "2,8", "5,1"]
    assert formular.sg_tabelle.cells[0, 1] == "1"


def test_to_dataframe_laesst_fuehrende_nullen_und_grosse_zahlen_heil() -> None:
    """Punkt 339: „01067“ und „0351123“ bleiben Text wie beim
    CSV-Import im Datenbank-Panel, „3“, „4“ bleiben Zahlen (Punkt 216),
    2,5 · 10^21 übersteht den Rundlauf, und eine ganze Zahl mit mehr
    Stellen, als ein `float` hält, kommt unverfälscht zurück."""
    formular = _Formular()
    df = pd.DataFrame({
        "plz": ["01067", "10115"],
        "tel": ["0351123", "030456"],
        "anzahl": [3, 4],
        "gross": [2.5e21, 1.0],
        "nummer": [1234567890123456789, 1],
    })

    formular.sg_tabelle.load_dataframe(df)
    zurueck = formular.sg_tabelle.to_dataframe()

    assert list(zurueck["plz"]) == ["01067", "10115"]
    assert list(zurueck["tel"]) == ["0351123", "030456"]
    assert zurueck["anzahl"].sum() == 7
    assert list(zurueck["gross"]) == [2.5e21, 1.0]
    assert list(zurueck["nummer"]) == [1234567890123456789, 1]


def test_to_dataframe_liest_den_dezimalpunkt_je_spalte() -> None:
    """Wie beim CSV-Import: neben „2.49“ ist „1.250“ 1,25."""
    formular = _Formular()
    grid = formular.sg_tabelle
    grid.col_count = 2
    grid.row_count = 4
    for zeile, (preis, tausend) in enumerate(
        [("preis", "tausend"), ("1.250", "1.000"), ("2.49", "2.500"), ("0.99", "3")]
    ):
        grid.cells[0, zeile] = preis
        grid.cells[1, zeile] = tausend

    df = grid.to_dataframe()

    assert df["preis"].tolist() == [1.25, 2.49, 0.99]
    assert df["tausend"].tolist() == [1000, 2500, 3]
