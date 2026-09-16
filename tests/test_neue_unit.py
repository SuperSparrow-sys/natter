"""Tests für HauptFenster.unit_erzeugen(): „Neue Unit“ (Abschnitt 7.2,
7.4). Siehe docs/arbeitspakete/M2.md, Schritt 9.
"""

from pathlib import Path

import pytest

from ide.project import projekt_erzeugen
from ide.shell.hauptfenster import HauptFenster


@pytest.fixture
def fenster_mit_projekt(tmp_path: Path) -> HauptFenster:
    ziel = tmp_path / "Test"
    projekt_erzeugen("gui", ziel, "Test")
    fenster = HauptFenster()
    fenster.projekt_oeffnen(ziel)
    return fenster


def test_ohne_offenes_projekt_wird_abgelehnt() -> None:
    fenster = HauptFenster()
    with pytest.raises(RuntimeError):
        fenster.unit_erzeugen()


def test_erzeugt_u_neu1_beim_ersten_mal(fenster_mit_projekt: HauptFenster) -> None:
    pfad = fenster_mit_projekt.unit_erzeugen()
    assert pfad.name == "u_neu1.py"
    assert pfad.exists()
    assert pfad.read_text(encoding="utf-8") == ""


def test_zweite_neue_unit_heisst_u_neu2(fenster_mit_projekt: HauptFenster) -> None:
    fenster_mit_projekt.unit_erzeugen()
    zweite = fenster_mit_projekt.unit_erzeugen()
    assert zweite.name == "u_neu2.py"


def test_mit_eigenem_namen(fenster_mit_projekt: HauptFenster) -> None:
    pfad = fenster_mit_projekt.unit_erzeugen("u_pflanzen")
    assert pfad.name == "u_pflanzen.py"


def test_vorhandener_name_wird_abgelehnt(fenster_mit_projekt: HauptFenster) -> None:
    fenster_mit_projekt.unit_erzeugen("u_pflanzen")
    with pytest.raises(FileExistsError):
        fenster_mit_projekt.unit_erzeugen("u_pflanzen")


def test_neue_unit_erscheint_im_explorer_und_wird_geoeffnet(
    fenster_mit_projekt: HauptFenster,
) -> None:
    fenster_mit_projekt.unit_erzeugen("u_pflanzen")

    einheiten_namen = {
        fenster_mit_projekt.explorer.units_gruppe.child(i).text(0)
        for i in range(fenster_mit_projekt.explorer.units_gruppe.childCount())
    }
    assert "u_pflanzen.py" in einheiten_namen
    assert fenster_mit_projekt.editor_tabs.tabText(
        fenster_mit_projekt.editor_tabs.currentIndex()
    ) == "u_pflanzen.py"
