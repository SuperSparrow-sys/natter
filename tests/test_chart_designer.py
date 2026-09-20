"""Tests für die Chart-Komponente im Designer (M10, Punkt 1 und 2):
Platzieren aus der Palette, `.pfm`-Eintrag und Rundreise über die Datei.
Headless.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ide.designer.canvas import DesignerCanvas
from ide.designer.laden import formular_fuer_designer_laden
from ide.designer.pfm_schreiben import pfm_aus_formular
from pcl import Chart, Form
from pcl.components.chart import _ARTEN


class _LeeresFormular(Form):
    pass


def _pfm_eintrag(formular: Form) -> dict:
    return pfm_aus_formular(formular)["children"][0]


def test_platzieren_erzeugt_ein_diagramm_in_sinnvoller_groesse() -> None:
    canvas = DesignerCanvas(_LeeresFormular())

    diagramm = canvas.komponente_platzieren(Chart, 30, 40)

    assert isinstance(diagramm, Chart)
    # Eingerastet am 8px-Raster: aus 30 wird 32.
    assert (diagramm.left, diagramm.top) == (32, 40)
    # Deutlich größer als ein Knopf, sonst wäre nur der Rahmen der Figur
    # zu sehen.
    assert (diagramm.width, diagramm.height) == (320, 240)


def test_platzieren_erzeugt_den_erwarteten_pfm_eintrag() -> None:
    formular = _LeeresFormular()
    canvas = DesignerCanvas(formular)

    canvas.komponente_platzieren(Chart, 30, 40)

    eintrag = _pfm_eintrag(formular)
    assert eintrag["name"] == "chart"
    assert eintrag["type"] == "Chart"
    assert eintrag["properties"] == {"left": 32, "top": 40}


@pytest.mark.parametrize("art", _ARTEN)
def test_rundreise_ueber_die_datei_erhaelt_die_diagrammart(art: str, tmp_path: Path) -> None:
    formular = _LeeresFormular()
    canvas = DesignerCanvas(formular)
    diagramm = canvas.komponente_platzieren(Chart, 10, 10)
    diagramm.kind = art
    diagramm.title = "Messreihe"
    diagramm.x_label = "Zeit"
    diagramm.y_label = "Temperatur"
    diagramm.legend = True
    diagramm.grid = True

    pfad = tmp_path / "u_main.pfm"
    pfad.write_text(json.dumps(pfm_aus_formular(formular)), encoding="utf-8")
    geladen = formular_fuer_designer_laden(pfad)

    assert geladen.chart.kind == art
    assert geladen.chart.title == "Messreihe"
    assert geladen.chart.x_label == "Zeit"
    assert geladen.chart.y_label == "Temperatur"
    assert geladen.chart.legend is True
    assert geladen.chart.grid is True
    assert geladen.chart._achse.get_title() == "Messreihe"
