"""Tests für Daten und Regression in der Chart-Komponente (M10, Punkt 3
und 5). Headless, gegen echtes matplotlib, echtes pandas und eine echte
SQLite-Datenbank im Arbeitsspeicher.

CSV-Dateien entstehen immer in `tmp_path`, nie in `beispielprojekte/`
(AGENTS.md).

Am Ende stehen zwei Pixelprüfungen. Beide Fehler, die sie absichern, sind
in der Sichtprüfung gerenderter Bilder aufgefallen und in keinem
Objektbaum-Test zu sehen gewesen.
"""

from __future__ import annotations

import pytest

from pcl import Chart, Form, SQLite3Connection, StringGrid
from pcl.components.chart import _farbpalette
from pcl.errors import NatterDatenDateiError, NatterDatenError

_SERIENFARBE = _farbpalette("system")[0]


class _Formular(Form):
    def create_components(self) -> None:
        self.ch_diagramm = Chart(self)
        self.sg_tabelle = StringGrid(self)


@pytest.fixture
def formular() -> _Formular:
    # Das Formular muss am Leben bleiben: fällt die letzte Referenz weg,
    # räumt Python es weg und Qt löscht das QWidget des Diagramms mit.
    return _Formular()


@pytest.fixture
def diagramm(formular: _Formular) -> Chart:
    return formular.ch_diagramm


@pytest.fixture
def verkauf_csv(tmp_path):
    """Deutsche Tabelle, wie sie aus Excel kommt: Semikolon als
    Trennzeichen, Komma als Dezimalzeichen."""
    pfad = tmp_path / "verkauf.csv"
    pfad.write_text(
        "monat;umsatz\n1;1200,50\n2;1400,25\n3;1650,00\n4;1810,75\n5;2100,10\n",
        encoding="utf-8",
    )
    return pfad


def _pixel_in(diagramm: Chart, farbe: str) -> int:
    """Wie viele Pixel des wirklich gerenderten Diagramms genau diese
    Farbe tragen (wie in tests/test_chart_arten.py)."""
    widget = diagramm._qwidget
    widget.resize(diagramm.width, diagramm.height)
    diagramm._figure.canvas.draw()
    bild = widget.grab().toImage()
    return sum(
        bild.pixelColor(x, y).name() == farbe
        for x in range(bild.width())
        for y in range(bild.height())
    )


# -- load_csv ------------------------------------------------------------


def test_load_csv_zeichnet_die_spalten_und_merkt_sich_den_dataframe(diagramm, verkauf_csv) -> None:
    diagramm.load_csv(str(verkauf_csv), "monat", "umsatz")

    assert list(diagramm.dataframe.columns) == ["monat", "umsatz"]
    assert len(diagramm.dataframe) == 5
    # kind ist "bar": ein Balken je Zeile.
    assert len(diagramm._achse.patches) == 5


def test_load_csv_erkennt_semikolon_und_dezimalkomma_von_allein(diagramm, verkauf_csv) -> None:
    # Ohne beides wären die Umsätze Text und es gäbe kein Diagramm.
    diagramm.kind = "line"
    diagramm.load_csv(str(verkauf_csv), "monat", "umsatz")

    (linie,) = diagramm._achse.lines
    assert list(linie.get_ydata()) == pytest.approx([1200.50, 1400.25, 1650.00, 1810.75, 2100.10])


def test_load_csv_nimmt_auch_spaltennummern(diagramm, verkauf_csv) -> None:
    diagramm.kind = "line"
    diagramm.load_csv(str(verkauf_csv), 0, 1)

    (linie,) = diagramm._achse.lines
    assert list(linie.get_xdata()) == pytest.approx([1, 2, 3, 4, 5])


def test_load_csv_liest_auch_englische_dateien(diagramm, tmp_path) -> None:
    pfad = tmp_path / "sales.csv"
    pfad.write_text("month,sales\n1,10.5\n2,20.25\n3,30.75\n", encoding="utf-8")

    diagramm.kind = "line"
    diagramm.load_csv(str(pfad), "month", "sales")

    (linie,) = diagramm._achse.lines
    assert list(linie.get_ydata()) == pytest.approx([10.5, 20.25, 30.75])


def test_load_csv_ersetzt_die_beispieldaten_des_designers(diagramm, verkauf_csv) -> None:
    assert diagramm._beispiel_sichtbar is True

    diagramm.load_csv(str(verkauf_csv), "monat", "umsatz")

    assert diagramm._beispiel_sichtbar is False


def test_zweites_load_csv_haengt_nichts_an(diagramm, verkauf_csv) -> None:
    diagramm.load_csv(str(verkauf_csv), "monat", "umsatz")
    diagramm.load_csv(str(verkauf_csv), "monat", "umsatz")

    assert len(diagramm._achse.patches) == 5


def test_kind_bestimmt_die_art_der_geladenen_daten(diagramm, verkauf_csv) -> None:
    diagramm.kind = "scatter"
    diagramm.load_csv(str(verkauf_csv), "monat", "umsatz")

    (punktwolke,) = diagramm._achse.collections
    assert punktwolke.get_offsets().shape == (5, 2)


# -- load_query ----------------------------------------------------------


@pytest.fixture
def verbindung():
    """Echte SQLite-Datenbank im Arbeitsspeicher (AGENTS.md: erst gegen
    virtuelle Abbildungen testen)."""
    verbindung = SQLite3Connection()
    verbindung.database_name = ":memory:"
    verbindung.connected = True
    zeiger = verbindung.verbindung.cursor()
    zeiger.execute("CREATE TABLE verkauf (region TEXT, umsatz REAL)")
    zeiger.executemany(
        "INSERT INTO verkauf VALUES (?, ?)",
        [("Nord", 1200.0), ("Süd", 900.0), ("Ost", 1500.0)],
    )
    verbindung.verbindung.commit()
    yield verbindung
    verbindung.connected = False


def test_load_query_fuellt_aus_der_datenbank(diagramm, verbindung) -> None:
    diagramm.load_query(verbindung, "SELECT region, umsatz FROM verkauf")

    assert list(diagramm.dataframe.columns) == ["region", "umsatz"]
    assert len(diagramm._achse.patches) == 3


def test_load_query_nimmt_ohne_angabe_die_ersten_beiden_spalten(diagramm, verbindung) -> None:
    diagramm.load_query(verbindung, "SELECT region, umsatz FROM verkauf")

    assert diagramm._x_spalte == "region"
    assert diagramm._y_spalte == "umsatz"


def test_load_query_meldet_eine_unbekannte_spalte_auf_deutsch(diagramm, verbindung) -> None:
    with pytest.raises(NatterDatenError, match="Die Spalte „ertrag“ gibt es"):
        diagramm.load_query(verbindung, "SELECT region, umsatz FROM verkauf", y="ertrag")


# -- load_grid -----------------------------------------------------------


def _tabelle_fuellen(
    grid: StringGrid, kopf: tuple[str, str], zeilen: list[tuple[str, str]]
) -> None:
    grid.col_count = 2
    grid.row_count = len(zeilen) + 1
    grid.cells[0, 0], grid.cells[1, 0] = kopf
    for nummer, (links, rechts) in enumerate(zeilen, start=1):
        grid.cells[0, nummer] = links
        grid.cells[1, nummer] = rechts


def test_load_grid_uebernimmt_die_tabelle_des_formulars(formular) -> None:
    _tabelle_fuellen(
        formular.sg_tabelle,
        ("groesse", "schuh"),
        [("160", "38"), ("170", "41"), ("180", "44")],
    )

    formular.ch_diagramm.kind = "scatter"
    formular.ch_diagramm.load_grid(formular.sg_tabelle)

    (punktwolke,) = formular.ch_diagramm._achse.collections
    assert punktwolke.get_offsets().shape == (3, 2)


def test_load_grid_liest_zahlen_aus_den_textzellen(formular) -> None:
    _tabelle_fuellen(
        formular.sg_tabelle,
        ("groesse", "schuh"),
        [("160", "38"), ("170", "41"), ("180", "44")],
    )

    formular.ch_diagramm.kind = "line"
    formular.ch_diagramm.load_grid(formular.sg_tabelle)

    (linie,) = formular.ch_diagramm._achse.lines
    assert list(linie.get_ydata()) == pytest.approx([38, 41, 44])


def test_load_grid_meldet_eine_spalte_ohne_zahlen_auf_deutsch(formular) -> None:
    _tabelle_fuellen(
        formular.sg_tabelle,
        ("name", "note"),
        [("Anna", "gut"), ("Ben", "mittel"), ("Cem", "schlecht")],
    )

    with pytest.raises(NatterDatenError, match="enthält nicht nur Zahlen"):
        formular.ch_diagramm.load_grid(formular.sg_tabelle)


# -- Fehlerfälle beim Laden ----------------------------------------------


def test_fehlende_datei_ergibt_eine_deutsche_meldung(diagramm, tmp_path) -> None:
    fehlend = tmp_path / "gibtsnicht.csv"

    with pytest.raises(NatterDatenDateiError, match="wurde nicht gefunden") as fehler:
        diagramm.load_csv(str(fehlend), 0, 1)

    # Das Arbeitsverzeichnis gehört dazu - ein relativer Pfad ist der
    # häufigste Grund, warum eine vorhandene Datei nicht gefunden wird.
    assert "Arbeitsverzeichnis" in str(fehler.value)


def test_fehlende_datei_ist_auch_ein_natter_datenfehler(diagramm, tmp_path) -> None:
    # Damit ein `except NatterDatenError` alle Datenfehler auf einmal
    # abfängt, ohne dass Schüler zwei Namen kennen müssen.
    with pytest.raises(NatterDatenError):
        diagramm.load_csv(str(tmp_path / "gibtsnicht.csv"), 0, 1)


def test_unbekannte_spalte_nennt_die_vorhandenen(diagramm, verkauf_csv) -> None:
    with pytest.raises(NatterDatenError) as fehler:
        diagramm.load_csv(str(verkauf_csv), "monat", "ertrag")

    assert "Die Spalte „ertrag“ gibt es" in str(fehler.value)
    assert "monat, umsatz" in str(fehler.value)


def test_unbekannte_spaltennummer_nennt_den_gueltigen_bereich(diagramm, verkauf_csv) -> None:
    with pytest.raises(NatterDatenError, match="0 bis 1"):
        diagramm.load_csv(str(verkauf_csv), 0, 9)


def test_spalte_ohne_zahlen_ergibt_eine_deutsche_meldung(diagramm, tmp_path) -> None:
    pfad = tmp_path / "noten.csv"
    pfad.write_text("name;note\nAnna;gut\nBen;mittel\n", encoding="utf-8")

    with pytest.raises(NatterDatenError) as fehler:
        diagramm.load_csv(str(pfad), "name", "note")

    assert "enthält nicht nur Zahlen" in str(fehler.value)
    assert "gut" in str(fehler.value)


def test_einspaltige_datei_ergibt_eine_deutsche_meldung(diagramm, tmp_path) -> None:
    pfad = tmp_path / "eine_spalte.csv"
    pfad.write_text("wert\n1\n2\n3\n", encoding="utf-8")

    with pytest.raises(NatterDatenError, match="mindestens 2 Spalten"):
        diagramm.load_csv(str(pfad), None, None)


def test_leere_datei_ergibt_eine_deutsche_meldung(diagramm, tmp_path) -> None:
    pfad = tmp_path / "leer.csv"
    pfad.write_text("", encoding="utf-8")

    with pytest.raises(NatterDatenError, match="enthält keine Daten"):
        diagramm.load_csv(str(pfad), 0, 1)


def test_ein_fehler_laesst_das_vorherige_diagramm_stehen(diagramm, verkauf_csv, tmp_path) -> None:
    diagramm.load_csv(str(verkauf_csv), "monat", "umsatz")
    kaputt = tmp_path / "noten.csv"
    kaputt.write_text("name;note\nAnna;gut\nBen;mittel\n", encoding="utf-8")

    with pytest.raises(NatterDatenError):
        diagramm.load_csv(str(kaputt), "name", "note")

    assert list(diagramm.dataframe.columns) == ["monat", "umsatz"]
    assert len(diagramm._achse.patches) == 5


# -- add_regression ------------------------------------------------------


def test_add_regression_legt_eine_kurve_ueber_die_punkte(diagramm) -> None:
    x = [1, 2, 3, 4]
    y = [3, 5, 7, 9]
    diagramm.add_scatter_series(x, y, title="Messwerte")

    diagramm.add_regression(x, y)

    (kurve,) = diagramm._achse.lines
    assert min(kurve.get_xdata()) == pytest.approx(1)
    assert max(kurve.get_xdata()) == pytest.approx(4)
    assert list(diagramm._achse.collections)  # die Punkte bleiben stehen


def test_add_regression_schreibt_die_formel_in_die_legende(diagramm) -> None:
    diagramm.add_scatter_series([1, 2, 3, 4], [3, 5, 7, 9], title="Messwerte")

    diagramm.add_regression([1, 2, 3, 4], [3, 5, 7, 9])

    legende = diagramm._achse.get_legend()
    assert legende is not None
    assert "y = 2,00·x + 1,00" in [text.get_text() for text in legende.get_texts()]


def test_add_regression_schaltet_die_legende_ein(diagramm) -> None:
    assert diagramm.legend is False

    diagramm.add_regression([1, 2, 3, 4], [3, 5, 7, 9])

    assert diagramm.legend is True


def test_add_regression_liefert_das_ergebnis_zurueck(diagramm) -> None:
    ergebnis = diagramm.add_regression([1, 2, 3, 4], [3, 5, 7, 9])

    assert ergebnis.steigung == pytest.approx(2.0)
    assert ergebnis.achsenabschnitt == pytest.approx(1.0)
    assert ergebnis.bestimmtheitsmass == 1.0


def test_add_regression_rechnet_ohne_argumente_mit_den_geladenen_daten(
    diagramm, verkauf_csv
) -> None:
    diagramm.kind = "scatter"
    diagramm.load_csv(str(verkauf_csv), "monat", "umsatz")

    ergebnis = diagramm.add_regression()

    assert ergebnis.steigung > 0
    assert ergebnis.bestimmtheitsmass > 0.9


def test_add_regression_kennt_alle_vier_arten(diagramm) -> None:
    x = [1, 2, 3, 4, 5]
    y = [2, 4, 8, 16, 32]

    for art in ("linear", "polynomial", "exponentiell", "logarithmisch"):
        diagramm.clear()
        ergebnis = diagramm.add_regression(x, y, art)
        assert ergebnis.art == art
        assert len(diagramm._achse.lines) == 1


def test_add_regression_ohne_daten_ergibt_eine_deutsche_meldung(diagramm) -> None:
    with pytest.raises(NatterDatenError, match="load_csv"):
        diagramm.add_regression()


def test_add_regression_mit_nur_einer_reihe_ergibt_eine_deutsche_meldung(diagramm) -> None:
    with pytest.raises(NatterDatenError, match="beide Reihen"):
        diagramm.add_regression([1, 2, 3])


# -- Sichtprüfung: was erst im gerenderten Bild auffiel -------------------


def test_legende_verdeckt_die_messpunkte_nicht(diagramm) -> None:
    """Die Formel in der Legende ist lang. In matplotlibs Standardschrift
    war der Legendenkasten in einem 320x240-Diagramm so breit, dass der
    oberste Messpunkt vollständig darunter verschwand – in der
    Sichtprüfung aufgefallen, von keinem Objektbaum-Test bemerkt."""
    x = [1, 2, 3, 4, 5]
    y = [1200.50, 1400.25, 1650.00, 1810.75, 2100.10]
    diagramm.kind = "scatter"
    diagramm.add_scatter_series(x, y, title="umsatz")
    ohne_legende = _pixel_in(diagramm, _SERIENFARBE)

    diagramm.add_regression(x, y, "polynomial")

    # Etwas darf die Regressionskurve verdecken, wo sie einen Punkt
    # kreuzt; ein ganzer Punkt von fünfen darf es nicht sein.
    assert _pixel_in(diagramm, _SERIENFARBE) >= 0.9 * ohne_legende


def test_spaetere_aenderung_von_kind_zeichnet_die_geladenen_daten_neu(
    diagramm, verkauf_csv
) -> None:
    diagramm.load_csv(str(verkauf_csv), "monat", "umsatz")
    assert len(diagramm._achse.patches) == 5

    diagramm.kind = "line"

    assert len(diagramm._achse.patches) == 0
    (linie,) = diagramm._achse.lines
    assert list(linie.get_ydata()) == pytest.approx([1200.50, 1400.25, 1650.00, 1810.75, 2100.10])


def test_clear_vergisst_auch_die_geladenen_daten(diagramm, verkauf_csv) -> None:
    # Sonst füllte ein späteres `kind = "line"` das gerade geleerte
    # Diagramm wieder, und `add_regression()` ohne Argumente rechnete
    # mit Daten, von denen nichts mehr zu sehen ist.
    diagramm.load_csv(str(verkauf_csv), "monat", "umsatz")

    diagramm.clear()

    assert diagramm.dataframe is None
    diagramm.kind = "line"
    assert len(diagramm._achse.lines) == 0
    with pytest.raises(NatterDatenError, match="load_csv"):
        diagramm.add_regression()
