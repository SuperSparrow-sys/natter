"""Abnahmetest für das Beispielprojekt GuiKomponenten (nachgebildet aus
referenz/lazarus/a_GUI_Komponenten/unit1.pas): ein erstes
Übungsprojekt zum Platzieren und Verknüpfen mehrerer GUI-Komponenten
(Label, Edit, Button).
"""

import importlib
import sys
from pathlib import Path

import pytest

from ide.shell.hauptfenster import HauptFenster

_PROJEKT_ORDNER = Path(__file__).resolve().parent.parent / "beispielprojekte" / "GuiKomponenten"
_PROJEKT_MODULE = ("main", "u_main", "u_main_design")


@pytest.fixture
def form1_klasse():
    sys.path.insert(0, str(_PROJEKT_ORDNER))
    for name in _PROJEKT_MODULE:
        sys.modules.pop(name, None)
    try:
        modul = importlib.import_module("u_main")
        yield modul.Form1
    finally:
        sys.path.remove(str(_PROJEKT_ORDNER))
        for name in _PROJEKT_MODULE:
            sys.modules.pop(name, None)


def test_begruessung_mit_namen(form1_klasse) -> None:
    formular = form1_klasse()

    formular.e_namenseingabe.text = "Anna"
    formular.b_begruessung._qwidget.click()

    assert formular.l_ausgabe.caption == "Sei gegrüßt, Anna!"


def test_begruessung_ohne_namen_zeigt_hinweis(form1_klasse) -> None:
    formular = form1_klasse()

    formular.b_begruessung._qwidget.click()

    assert formular.l_ausgabe.caption == "Bitte Namen im Eingabefeld eingeben."


def test_alle_komponenten_haben_die_richtige_groesse_und_position(form1_klasse) -> None:
    # Direkt gegen die Werte aus referenz/lazarus/a_GUI_Komponenten/unit1.lfm
    # geprüft (Nutzer-Feedback: "Buttons passen von Größe und Position").
    formular = form1_klasse()

    assert (formular.e_namenseingabe.left, formular.e_namenseingabe.top) == (64, 56)
    assert (formular.e_namenseingabe.width, formular.e_namenseingabe.height) == (200, 23)
    assert formular.e_namenseingabe.color == "#ffff00"

    assert (formular.b_begruessung.left, formular.b_begruessung.top) == (64, 88)
    assert (formular.b_begruessung.width, formular.b_begruessung.height) == (200, 25)

    assert (formular.b_schliessen.left, formular.b_schliessen.top) == (68, 270)
    assert (formular.b_schliessen.width, formular.b_schliessen.height) == (208, 33)


def test_projekt_in_der_ide_oeffnen_gruppiert_units_korrekt() -> None:
    fenster = HauptFenster()
    fenster.projekt_oeffnen(_PROJEKT_ORDNER)

    formulare = {
        fenster.explorer.formulare_gruppe.child(i).text(0)
        for i in range(fenster.explorer.formulare_gruppe.childCount())
    }
    assert formulare == {"u_main"}
