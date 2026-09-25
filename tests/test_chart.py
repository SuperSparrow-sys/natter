"""Tests für die Chart-Komponente (Abschnitt 11.6). Siehe
Arbeitspaket M5, Schritt 4. Headless, gegen echtes matplotlib
(Backend `FigureCanvasQTAgg`, kein Mock).
"""

from __future__ import annotations

import pandas as pd

from pcl import Chart, Form


class _Formular(Form):
    def create_components(self) -> None:
        self.ch_diagramm = Chart(self)


def test_add_bar_series_erzeugt_einen_balken_je_wert() -> None:
    formular = _Formular()
    formular.ch_diagramm.add_bar_series(["A", "B", "C"], [1, 2, 3])
    assert len(formular.ch_diagramm._achse.patches) == 3


def test_add_line_series_erzeugt_eine_linie_mit_allen_punkten() -> None:
    formular = _Formular()
    formular.ch_diagramm.add_line_series([1, 2, 3], [1, 4, 9])
    linien = formular.ch_diagramm._achse.lines
    assert len(linien) == 1
    assert list(linien[0].get_ydata()) == [1, 4, 9]


def test_add_pie_series_erzeugt_ein_tortenstueck_je_wert() -> None:
    formular = _Formular()
    formular.ch_diagramm.add_pie_series(["A", "B"], [1, 2])
    assert len(formular.ch_diagramm._achse.patches) == 2


def test_add_scatter_series_erzeugt_eine_punktwolke() -> None:
    formular = _Formular()
    formular.ch_diagramm.add_scatter_series([1, 2, 3], [3, 2, 1])
    sammlungen = formular.ch_diagramm._achse.collections
    assert len(sammlungen) == 1
    assert sammlungen[0].get_offsets().shape == (3, 2)


def test_clear_entfernt_alle_serien() -> None:
    formular = _Formular()
    formular.ch_diagramm.add_bar_series(["A"], [1])
    formular.ch_diagramm.add_line_series([1, 2], [1, 2])

    formular.ch_diagramm.clear()

    assert len(formular.ch_diagramm._achse.patches) == 0
    assert len(formular.ch_diagramm._achse.lines) == 0


def test_chart_nimmt_pandas_serien_entgegen() -> None:
    formular = _Formular()
    umsatz = pd.Series([10, 20, 30], index=["Nord", "Süd", "Ost"])

    formular.ch_diagramm.add_bar_series(umsatz.index, umsatz.values, title="Umsatz je Region")

    assert len(formular.ch_diagramm._achse.patches) == 3
    assert formular.ch_diagramm._achse.get_title() == "Umsatz je Region"


def test_farben_unterscheiden_sich_zwischen_hell_und_dunkel() -> None:
    hell = _Formular()
    hell.ch_diagramm._theme = "light"
    hell.ch_diagramm._farben_anwenden()

    dunkel = _Formular()
    dunkel.ch_diagramm._theme = "dark"
    dunkel.ch_diagramm._farben_anwenden()

    assert hell.ch_diagramm._figure.get_facecolor() != dunkel.ch_diagramm._figure.get_facecolor()
