"""Tests für ide/palette/palette.py: Komponentenpalette. Headless. Siehe
docs/arbeitspakete/M3.md, Schritt 6.
"""

from ide.palette import Komponentenpalette
from ide.palette.palette import (
    ALLE_KOMPONENTEN,
    REITER,
    STANDARD_KOMPONENTEN,
    TYP_ROLLE,
    ZUSAETZLICH_KOMPONENTEN,
)
from pcl import Button, Shape


def test_jede_komponente_hat_ein_echtes_symbol() -> None:
    # Ein Tippfehler im Dateinamen liefert sonst nur ein leeres QIcon
    # (symbol() wirft absichtlich nie, siehe ide/assets/symbole.py) -
    # ohne diesen Test würde das nicht auffallen.
    palette = Komponentenpalette()
    for liste in palette.listen:
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


def test_die_reiter_stehen_in_der_reihenfolge_von_REITER() -> None:
    """Die Titel kommen aus `REITER` und nur von dort - wer einen Reiter
    ergänzt, trägt ihn dort ein und ist fertig. Hier stand bis M15 eine
    zweite, von Hand gepflegte Liste („Standard", „Zusätzlich"); der
    Reiter „Eingabe" ließ sie umfallen."""
    palette = Komponentenpalette()

    titel = [palette.tabText(i) for i in range(palette.count())]

    assert titel == [name for name, _ in REITER]
    assert titel[:2] == ["Standard", "Zusätzlich"]


def test_standard_reiter_enthaelt_button() -> None:
    # Wie in Lazarus zeigen die Kacheln nur ein Symbol, der Name steht im
    # Kurzhinweis statt als sichtbarer Text (siehe ide/palette/palette.py).
    # Seit M11, Abschnitt 4 steht dort Name und Erklaerung.
    palette = Komponentenpalette()
    namen = [
        palette.standard_liste.item(i).toolTip() for i in range(palette.standard_liste.count())
    ]
    assert any(name.startswith("Button – ") for name in namen)


def test_zusaetzlich_reiter_enthaelt_shape() -> None:
    palette = Komponentenpalette()
    namen = [
        palette.zusaetzlich_liste.item(i).toolTip()
        for i in range(palette.zusaetzlich_liste.count())
    ]
    assert any(name.startswith("Shape – ") for name in namen)


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


def test_jeder_reiter_aus_reiter_steht_wirklich_da() -> None:
    """`REITER` ist die einzige Stelle, an der ein Reiter steht – also
    muss die Palette genau daraus bestehen (M15)."""
    palette = Komponentenpalette()

    assert palette.count() == len(REITER)
    for seite, (beschriftung, komponenten) in enumerate(REITER):
        assert palette.tabText(seite) == beschriftung
        liste = palette.widget(seite)
        assert liste is palette.listen[seite]
        assert liste.count() == len(komponenten)


def test_alle_komponenten_fasst_jeden_reiter() -> None:
    assert set(ALLE_KOMPONENTEN) == {typ for _, k in REITER for typ in k}
    assert len(ALLE_KOMPONENTEN) == sum(len(k) for _, k in REITER)


def test_liste_zu_findet_den_reiter_und_meckert_sonst() -> None:
    import pytest

    palette = Komponentenpalette()

    assert palette.liste_zu("Standard") is palette.standard_liste
    assert palette.liste_zu("Zusätzlich") is palette.zusaetzlich_liste
    with pytest.raises(KeyError):
        palette.liste_zu("Datenbank")


def test_jeder_reiter_ist_im_hauptfenster_verdrahtet(qtbot) -> None:
    """Der eigentliche Grund für `palette.listen`: vorher verband das
    Hauptfenster zwei namentlich genannte Listen. Ein dritter Reiter
    wäre stumm geblieben – seine Kacheln sichtbar, aber nicht
    ablegbar. Dieser Test hält das fest, bevor es wieder passiert."""
    from ide.shell.hauptfenster import HauptFenster

    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    for liste in fenster.palette.listen:
        assert liste.receivers("2itemActivated(QListWidgetItem*)") > 0
        assert liste.receivers("2itemClicked(QListWidgetItem*)") > 0
