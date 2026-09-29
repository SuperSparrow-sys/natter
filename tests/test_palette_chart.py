"""Tests für die Chart-Kachel in der Komponentenpalette (M10, Punkt 1).
Headless.
"""

from __future__ import annotations

from ide.palette import Komponentenpalette
from ide.palette.palette import STANDARD_KOMPONENTEN, TYP_ROLLE, ZUSAETZLICH_KOMPONENTEN
from pcl import Chart


def test_chart_steht_im_reiter_zusaetzlich() -> None:
    # „Zusätzlich“ und nicht „Standard“: ein Diagramm ist kein
    # Grundbaustein wie Knopf oder Textfeld.
    assert Chart in ZUSAETZLICH_KOMPONENTEN
    assert Chart not in STANDARD_KOMPONENTEN


def test_chart_kachel_hat_ein_echtes_symbol() -> None:
    palette = Komponentenpalette()
    liste = palette.zusaetzlich_liste
    kacheln = [liste.item(i) for i in range(liste.count())]

    chart_kachel = next(k for k in kacheln if k.data(TYP_ROLLE) is Chart)

    assert chart_kachel.toolTip().startswith("Chart – ")
    # Ein Tippfehler im Dateinamen liefert nur ein leeres QIcon, keinen
    # Fehler (siehe ide/assets/symbole.py) – das war real schon kaputt.
    assert not chart_kachel.icon().isNull()
    assert not chart_kachel.icon().pixmap(22, 22).isNull()


def test_chart_ist_ueber_die_palette_auswaehlbar() -> None:
    palette = Komponentenpalette()
    palette.setCurrentWidget(palette.zusaetzlich_liste)
    zeile = ZUSAETZLICH_KOMPONENTEN.index(Chart)
    palette.zusaetzlich_liste.setCurrentRow(zeile)

    assert palette.ausgewaehlter_typ() is Chart
