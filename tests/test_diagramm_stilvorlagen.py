"""Tests für die Stilvorlagen-Umschaltung und die Ansicht-Schalter im
Diagramm-Fenster (M9, Schritt 7). Headless.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtGui import QImage, QPainter

from ide.diagramm import DiagrammFenster, diagramm_erzeugen
from ide.diagramm.stil import BESCHRIFTUNGEN, MODERN_DUNKEL, MODERN_HELL, SCHWARZ_WEISS
from ide.diagramm.zeichnen import form_zeichnen


@pytest.fixture
def fenster(tmp_path: Path) -> DiagrammFenster:
    return DiagrammFenster(diagramm_erzeugen("class", tmp_path / "k.pdiag", "k"))


def _gemalte_farben(stil) -> set[str]:
    """Malt eine Klasse mit der Vorlage und gibt die vorkommenden Farben
    zurück – so wird die Vorlage wirklich am Ergebnis geprüft und nicht
    nur am Datensatz."""
    form = {
        "id": "s1",
        "kind": "class",
        "x": 10,
        "y": 10,
        "w": 200,
        "h": 140,
        "text": {"name": "TAmpel", "attributes": ["-an: bool"], "methods": ["+ein()"]},
    }
    bild = QImage(240, 180, QImage.Format.Format_RGB32)
    bild.fill(stil.hintergrund)
    maler = QPainter(bild)
    form_zeichnen(maler, form, stil)
    maler.end()
    return {
        QImage.pixelColor(bild, x, y).name()
        for x in range(0, 240, 2)
        for y in range(0, 180, 2)
    }


# -- Stilvorlagen --------------------------------------------------------


@pytest.mark.parametrize("stil", [MODERN_HELL, MODERN_DUNKEL, SCHWARZ_WEISS])
def test_jede_stilvorlage_malt_ihre_eigenen_farben(stil) -> None:
    farben = _gemalte_farben(stil)

    assert stil.fuellung in farben
    assert stil.hintergrund in farben


def test_helle_und_dunkle_vorlage_unterscheiden_sich_sichtbar(fenster) -> None:
    assert _gemalte_farben(MODERN_HELL) != _gemalte_farben(MODERN_DUNKEL)


def test_schwarz_weiss_kommt_ohne_bunte_farben_aus() -> None:
    """Für die Abgabe auf Papier (Abschnitt 13.6)."""
    for farbe in (SCHWARZ_WEISS.fuellung, SCHWARZ_WEISS.rand, SCHWARZ_WEISS.linie):
        rot, gruen, blau = farbe[1:3], farbe[3:5], farbe[5:7]
        assert rot == gruen == blau


def test_format_menue_bietet_alle_drei_vorlagen(fenster) -> None:
    untermenue = fenster.aktionen["Format/Stilvorlage …"].menu()

    assert [a.text() for a in untermenue.actions()] == list(BESCHRIFTUNGEN.values())


def test_vorlage_umschalten_aendert_das_diagramm(fenster) -> None:
    fenster.stil_setzen("black-white")

    assert fenster.diagramm.stil == "black-white"
    assert fenster.stil_aktionen["black-white"].isChecked() is True


def test_vorlage_umschalten_ist_rueckgaengig_machbar(fenster) -> None:
    fenster.stil_setzen("modern-dark")

    fenster.zeichenflaeche.rueckgaengig()

    assert fenster.diagramm.stil == "modern-light"


def test_gewaehlte_vorlage_steht_in_der_statusleiste(fenster) -> None:
    fenster.stil_setzen("modern-dark")

    assert "modern-dark" in fenster.statusBar().currentMessage()


def test_vorlage_ueberlebt_speichern_und_laden(fenster, tmp_path: Path) -> None:
    from ide.diagramm.datei import Diagramm

    fenster.stil_setzen("black-white")
    fenster.speichern()

    assert Diagramm.laden(fenster.diagramm.pfad).stil == "black-white"


# -- Layout-Hinweise im Fenster -----------------------------------------


def test_ueberlappende_formen_werden_auf_der_flaeche_gemeldet(fenster) -> None:
    flaeche = fenster.zeichenflaeche
    erste = flaeche.form_platzieren("class", 300, 300)
    flaeche.form_platzieren("class", 320, 320)

    assert erste["id"] in {k for h in flaeche.hinweise for k in h.elemente}
    assert "Layout-Hinweis" in fenster.statusBar().currentMessage()


def test_hinweise_lassen_sich_abschalten(fenster) -> None:
    """Wie beim Design-Prüfer (M7): Hinweise melden nur, blockieren nie –
    und wer sie nicht will, schaltet sie ab."""
    flaeche = fenster.zeichenflaeche
    flaeche.form_platzieren("class", 300, 300)
    flaeche.form_platzieren("class", 320, 320)
    assert flaeche.hinweise

    fenster.aktionen["Ansicht/Layout-Hinweise"].setChecked(False)

    assert flaeche.hinweise == []
    assert "Layout-Hinweis" not in fenster.statusBar().currentMessage()


def test_hinweis_verschwindet_wenn_das_problem_behoben_ist(fenster) -> None:
    flaeche = fenster.zeichenflaeche
    flaeche.form_platzieren("class", 300, 300)
    zweite = flaeche.form_platzieren("class", 320, 320)
    assert flaeche.hinweise

    flaeche.verschieben(600, 0, zweite)

    assert flaeche.hinweise == []


def test_raster_und_seitenraender_sind_umschaltbar(fenster) -> None:
    for pfad, attribut in (
        ("Ansicht/Raster", "raster_sichtbar"),
        ("Ansicht/Seitenränder", "seitenrand_sichtbar"),
    ):
        aktion = fenster.aktionen[pfad]
        assert aktion.isChecked() is True

        aktion.setChecked(False)
        assert getattr(fenster.zeichenflaeche, attribut) is False

        aktion.setChecked(True)
        assert getattr(fenster.zeichenflaeche, attribut) is True
