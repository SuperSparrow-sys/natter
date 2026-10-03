"""Achsen mit Dezimalkomma, `add_regression()` über die Punkte im
Diagramm (Punkt 127)."""

import pytest

from pcl import Chart, Form
from pcl.errors import NatterDatenError


def _beschriftungen(achse) -> list[str]:
    return [text.get_text() for text in achse.get_ticklabels()]


def test_die_achsen_zeigen_0_5_mit_komma() -> None:
    diagramm = Chart(Form())
    diagramm.add_line_series([0, 0.5, 1, 1.5], [0, 0.25, 0.5, 0.75])
    # Wo matplotlib seine Striche setzt, hängt von der Größe ab. Die
    # Stellen hier fest, damit der Test den Formatter prüft.
    diagramm._achse.set_xticks([0, 0.5, 1, 1.5])
    diagramm._figure.canvas.draw()

    x_texte = _beschriftungen(diagramm._achse.xaxis)
    y_texte = _beschriftungen(diagramm._achse.yaxis)
    assert "0,5" in x_texte
    assert not any("." in text for text in x_texte + y_texte)


@pytest.mark.parametrize("nach_clear", [False, True])
def test_kategorien_bleiben_beschriftet(nach_clear: bool) -> None:
    """Auch nach `clear()`: dort stand bis 0.4.3 unter den Monaten
    der Wetterdaten aus Beispiel 07 die Zählung 0, 1, 2."""
    diagramm = Chart(Form())
    if nach_clear:
        diagramm.add_line_series([1, 2], [3, 4])
        diagramm.clear()
    diagramm.add_bar_series(["Mo", "Di"], [1.5, 2.5])
    diagramm._figure.canvas.draw()

    assert _beschriftungen(diagramm._achse.xaxis) == ["Mo", "Di"]
    assert any("," in text for text in _beschriftungen(diagramm._achse.yaxis))


def test_add_regression_ohne_argumente_nimmt_die_punkte_der_letzten_serie() -> None:
    diagramm = Chart(Form())
    diagramm.add_scatter_series([1, 2, 3, 4], [2.1, 3.9, 6.2, 7.8])
    ergebnis = diagramm.add_regression()
    assert ergebnis.steigung == pytest.approx(1.94, abs=0.01)


def test_add_regression_auf_leerem_diagramm_meldet_sich() -> None:
    diagramm = Chart(Form())
    diagramm.clear()
    with pytest.raises(NatterDatenError, match="add_scatter_series"):
        diagramm.add_regression()


def test_csv_in_cp1252_mit_komma_in_x_ergibt_eine_regression(tmp_path) -> None:
    """Punkte 572 und 576: eine CSV in der Windows-Kodierung endete in
    einem UnicodeDecodeError, und eine x-Spalte mit Dezimalkomma blieb
    Text, sodass add_regression() scheiterte."""
    datei = tmp_path / "versuch.csv"
    zeilen = ["zeit;weg (Länge)"] + [
        f"{t:.1f};{2.5 * t - 1.9:.2f}".replace(".", ",") for t in (0.5, 1, 1.5, 2, 10)
    ]
    datei.write_bytes(("\r\n".join(zeilen) + "\r\n").encode("cp1252"))
    diagramm = Chart(Form())
    diagramm.kind = "scatter"

    diagramm.load_csv(datei, 0, 1)
    ergebnis = diagramm.add_regression()

    assert ergebnis.steigung == pytest.approx(2.5, abs=0.01)


def test_leeres_kreisdiagramm_meldet_sich_deutsch() -> None:
    """Punkt 592: matplotlib meldete „All wedge sizes are zero“."""
    with pytest.raises(NatterDatenError, match="Kreisdiagramm"):
        Chart(Form()).add_pie_series([], [])


def test_tausenderpunkte_in_der_csv(tmp_path) -> None:
    """Punkt 592: „1.200,50“ galt als „nicht nur Zahlen“."""
    datei = tmp_path / "umsatz.csv"
    datei.write_text("monat;umsatz\nJan;1.200,50\nFeb;980,00\n", encoding="utf-8")
    diagramm = Chart(Form())

    diagramm.load_csv(datei, 0, 1)

    from pcl.components.chart import _als_zahlen

    assert list(_als_zahlen(diagramm._dataframe["umsatz"], "umsatz", "x")) == [1200.5, 980.0]
