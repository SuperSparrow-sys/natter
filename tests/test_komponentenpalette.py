"""Tests für ide/palette/palette.py: Komponentenpalette. Headless. Siehe
docs/arbeitspakete/M3.md, Schritt 6.
"""

from ide.palette import Komponentenpalette
from pcl import Button, Shape


def test_hat_die_beiden_reiter() -> None:
    palette = Komponentenpalette()
    titel = [palette.tabText(i) for i in range(palette.count())]
    assert titel == ["Standard", "Zusätzlich"]


def test_standard_reiter_enthaelt_button() -> None:
    palette = Komponentenpalette()
    namen = [
        palette.standard_liste.item(i).text() for i in range(palette.standard_liste.count())
    ]
    assert "Button" in namen


def test_zusaetzlich_reiter_enthaelt_shape() -> None:
    palette = Komponentenpalette()
    namen = [
        palette.zusaetzlich_liste.item(i).text()
        for i in range(palette.zusaetzlich_liste.count())
    ]
    assert "Shape" in namen


def test_ausgewaehlter_typ_ohne_auswahl_ist_none() -> None:
    palette = Komponentenpalette()
    assert palette.ausgewaehlter_typ() is None


def test_ausgewaehlter_typ_liefert_die_klasse() -> None:
    palette = Komponentenpalette()
    palette.standard_liste.setCurrentRow(0)  # Button steht zuerst

    assert palette.ausgewaehlter_typ() is Button


def test_ausgewaehlter_typ_wechselt_mit_dem_reiter() -> None:
    palette = Komponentenpalette()
    palette.standard_liste.setCurrentRow(0)
    palette.setCurrentWidget(palette.zusaetzlich_liste)
    palette.zusaetzlich_liste.setCurrentRow(2)  # Shape steht zuletzt

    assert palette.ausgewaehlter_typ() is Shape
