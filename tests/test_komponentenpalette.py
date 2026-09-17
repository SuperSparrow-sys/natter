"""Tests für ide/palette/palette.py: Komponentenpalette. Headless. Siehe
docs/arbeitspakete/M3.md, Schritt 6.
"""

from ide.palette import Komponentenpalette
from ide.palette.palette import STANDARD_KOMPONENTEN, TYP_ROLLE, ZUSAETZLICH_KOMPONENTEN
from pcl import Button, Shape


def test_jede_komponente_hat_ein_echtes_symbol() -> None:
    # Ein Tippfehler im Dateinamen liefert sonst nur ein leeres QIcon
    # (symbol() wirft absichtlich nie, siehe ide/assets/symbole.py) -
    # ohne diesen Test würde das nicht auffallen.
    palette = Komponentenpalette()
    for liste in (palette.standard_liste, palette.zusaetzlich_liste):
        for i in range(liste.count()):
            eintrag = liste.item(i)
            assert not eintrag.icon().isNull(), f"kein Symbol für {eintrag.toolTip()!r}"


def test_alle_bekannten_komponenten_sind_in_der_palette() -> None:
    palette = Komponentenpalette()
    standard_typen = {
        palette.standard_liste.item(i).data(TYP_ROLLE)
        for i in range(palette.standard_liste.count())
    }
    zusaetzlich_typen = {
        palette.zusaetzlich_liste.item(i).data(TYP_ROLLE)
        for i in range(palette.zusaetzlich_liste.count())
    }
    assert standard_typen == set(STANDARD_KOMPONENTEN)
    assert zusaetzlich_typen == set(ZUSAETZLICH_KOMPONENTEN)


def test_hat_die_beiden_reiter() -> None:
    palette = Komponentenpalette()
    titel = [palette.tabText(i) for i in range(palette.count())]
    assert titel == ["Standard", "Zusätzlich"]


def test_standard_reiter_enthaelt_button() -> None:
    # Wie in Lazarus zeigen die Kacheln nur ein Symbol, der Name steht im
    # Tooltip statt als sichtbarer Text (siehe ide/palette/palette.py).
    palette = Komponentenpalette()
    namen = [
        palette.standard_liste.item(i).toolTip() for i in range(palette.standard_liste.count())
    ]
    assert "Button" in namen


def test_zusaetzlich_reiter_enthaelt_shape() -> None:
    palette = Komponentenpalette()
    namen = [
        palette.zusaetzlich_liste.item(i).toolTip()
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
