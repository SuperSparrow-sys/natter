"""Abnahmetest für das Beispielprojekt Regression – zugleich das
Abnahmekriterium aus M10:

    „Ein Schülerprojekt, das eine CSV mit zwei Spalten einliest, die
    Punkte als Punktdiagramm auf einem Formular zeigt, eine lineare
    Regression darüberlegt und Steigung, Achsenabschnitt und
    Bestimmtheitsmaß in Beschriftungsfeldern ausgibt – vollständig im
    Designer zusammengeklickt, ohne eine Zeile Aufbau-Code von Hand.“

Geprüft wird deshalb beides: dass es rechnet, **und** dass der Aufbau
wirklich aus der `.pfm` kommt und nicht im Formular-Code steht.
"""

import importlib
import sys
from pathlib import Path

import pytest

_ORDNER = Path(__file__).resolve().parent.parent / "beispielprojekte" / "Regression"
_PROJEKT_MODULE = ("main", "u_main", "u_main_design")


@pytest.fixture
def form1_klasse():
    sys.path.insert(0, str(_ORDNER))
    for name in _PROJEKT_MODULE:
        sys.modules.pop(name, None)
    try:
        modul = importlib.import_module("u_main")
        yield modul.Form1
    finally:
        sys.path.remove(str(_ORDNER))
        for name in _PROJEKT_MODULE:
            sys.modules.pop(name, None)


@pytest.fixture
def formular(form1_klasse):
    return form1_klasse()


# -- Das Abnahmekriterium ------------------------------------------------


def test_die_csv_wird_beim_start_eingelesen(formular) -> None:
    daten = formular.ch_punkte.dataframe

    assert daten is not None
    assert list(daten.columns) == ["Koerpergroesse", "Schuhgroesse"]
    assert len(daten) == 15


def test_die_punkte_stehen_wirklich_im_diagramm(formular) -> None:
    """Nicht „die Daten sind geladen“, sondern: es ist etwas gezeichnet."""
    assert formular.ch_punkte._achse.collections, "kein Punktdiagramm gezeichnet"


def test_der_knopf_rechnet_die_regression(formular) -> None:
    formular.b_rechnen._qwidget.click()

    # Faustregel aus dem Unterricht: Schuhgröße etwa Körpergröße/3 - 13,
    # also eine Steigung um 0,33. Das Bestimmtheitsmaß ist hoch, aber
    # bewusst nicht 1 - die Messreihe streut, und genau das soll sie.
    assert formular.l_steigung.caption.startswith("Steigung: 0.3")
    assert "Achsenabschnitt: -" in formular.l_achsenabschnitt.caption
    bestimmtheit = float(formular.l_bestimmtheit.caption.rsplit(": ", 1)[1])
    assert 0.95 < bestimmtheit < 1.0


def test_die_gerade_liegt_wirklich_ueber_den_punkten(formular) -> None:
    vorher = len(formular.ch_punkte._achse.lines)

    formular.b_rechnen._qwidget.click()

    assert len(formular.ch_punkte._achse.lines) == vorher + 1


def test_die_formel_steht_in_der_legende(formular) -> None:
    formular.b_rechnen._qwidget.click()

    legende = formular.ch_punkte._achse.get_legend()
    assert legende is not None
    texte = [text.get_text() for text in legende.get_texts()]
    assert any(eintrag.startswith("y = ") for eintrag in texte), texte


def test_die_vorhersage_ist_plausibel(formular) -> None:
    """175 cm liegt mitten in der Messreihe – die Vorhersage muss
    zwischen den benachbarten Messwerten liegen (41 und 42)."""
    formular.b_rechnen._qwidget.click()

    zahl = float(formular.l_vorhersage.caption.rsplit(": ", 1)[1])
    assert 40.0 <= zahl <= 43.0


def test_die_tabelle_zeigt_dieselben_zahlen(formular) -> None:
    """Der übliche Weg im Unterricht: Daten erst als Tabelle zeigen,
    dann als Diagramm."""
    assert formular.sg_messwerte.cells[0, 0] == "Körpergröße"
    assert formular.sg_messwerte.cells[0, 1] == "158"
    assert formular.sg_messwerte.cells[1, 1] == "36"


# -- „ohne eine Zeile Aufbau-Code von Hand" ------------------------------


def test_der_aufbau_steht_in_der_pfm_und_nicht_im_formular_code() -> None:
    """Der Kern des Abnahmekriteriums. Stünde hier ein `Chart(self)`,
    wäre das Formular von Hand gebaut und nicht zusammengeklickt."""
    quelltext = (_ORDNER / "u_main.py").read_text(encoding="utf-8")

    for verboten in ("Chart(", "StringGrid(", "Label(", "Button(", ".left =", ".top ="):
        assert verboten not in quelltext, f"{verboten!r} gehört in die .pfm"


def test_der_designcode_passt_zur_pfm() -> None:
    """Sonst liefe das Beispiel nur, solange niemand die `.pfm`
    anfasst."""
    import json

    from ide.codegen.design import design_code_erzeugen

    pfm = json.loads((_ORDNER / "u_main.pfm").read_text(encoding="utf-8"))
    erwartet = design_code_erzeugen(pfm, "u_main.pfm")

    assert (_ORDNER / "u_main_design.py").read_text(encoding="utf-8") == erwartet


def test_das_projekt_ist_als_natter_projekt_beschrieben() -> None:
    import json

    projekt = json.loads((_ORDNER / "regression.natter").read_text(encoding="utf-8"))

    assert projekt["main"] == "main.py"
    assert projekt["main_form"] == "u_main"
    assert (_ORDNER / projekt["main"]).exists()
