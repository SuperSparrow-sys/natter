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
