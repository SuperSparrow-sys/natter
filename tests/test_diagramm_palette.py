"""Tests für ide/diagramm/palette.py: Formen-Palette (M9, Schritt 2).
Headless.
"""

from __future__ import annotations

from ide.diagramm.palette import KIND_ROLLE, FormenPalette


def _eintraege(palette: FormenPalette) -> dict[str, object]:
    gefunden = {}
    for i in range(palette.baum.topLevelItemCount()):
        gruppe = palette.baum.topLevelItem(i)
        for j in range(gruppe.childCount()):
            kind = gruppe.child(j)
            gefunden[kind.text(0)] = kind
    return gefunden


def test_klassendiagramm_palette_enthaelt_alle_formen_aus_dem_konzept() -> None:
    """Abschnitt 13.4: Klasse, abstrakte Klasse, Interface, Notiz, Paket."""
    palette = FormenPalette("class")

    assert set(_eintraege(palette)) == {
        "Klasse",
        "Abstrakte Klasse",
        "Interface",
        "Notiz",
        "Paket",
    }


def test_eintraege_haben_tooltip_mit_kurzbeschreibung() -> None:
    palette = FormenPalette("class")

    tooltip = _eintraege(palette)["Klasse"].toolTip(0)

    assert tooltip.startswith("Klasse – ")
    assert "Attribut" in tooltip


def test_klick_meldet_die_formart() -> None:
    palette = FormenPalette("class")
    gemeldet = []
    palette.form_gewaehlt.connect(gemeldet.append)

    eintrag = _eintraege(palette)["Interface"]
    palette._bei_klick(eintrag, 0)

    assert gemeldet == ["interface"]
    assert eintrag.data(0, KIND_ROLLE) == "interface"


def test_klick_auf_eine_gruppenueberschrift_meldet_nichts() -> None:
    palette = FormenPalette("class")
    gemeldet = []
    palette.form_gewaehlt.connect(gemeldet.append)

    palette._bei_klick(palette.baum.topLevelItem(0), 0)

    assert gemeldet == []


def test_suche_blendet_nicht_passende_formen_aus() -> None:
    palette = FormenPalette("class")

    palette.suche.setText("inter")

    eintraege = _eintraege(palette)
    assert eintraege["Interface"].isHidden() is False
    assert eintraege["Notiz"].isHidden() is True


def test_leere_suche_zeigt_wieder_alles() -> None:
    palette = FormenPalette("class")
    palette.suche.setText("inter")

    palette.suche.setText("")

    assert all(not eintrag.isHidden() for eintrag in _eintraege(palette).values())


def test_eigener_diagrammtyp_ist_aufgeklappt() -> None:
    palette = FormenPalette("class")

    assert palette.baum.topLevelItem(0).isExpanded() is True
