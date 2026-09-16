"""Abnahmetest für das Beispielprojekt Ampel (M1, Schritt 5).

Treibt dieselbe Logik wie das echte Programm headless über echte Qt-
Klicks, ohne die blockierende Ereignisschleife aus `pcl.Application.run`
zu starten (wie der Rest der Testsuite, siehe konzept-natter.md,
Abschnitt 19: "Runtime pcl: pytest + pytest-qt headless"). Das sichtbare
`python main.py` auf einem echten Windows-Rechner ist Sache der
Gesamtabnahme (Abschnitt 19, letzte Zeile "Abnahme").
"""

import importlib
import sys
from pathlib import Path

import pytest

_PROJEKT_ORDNER = Path(__file__).resolve().parent.parent / "beispielprojekte" / "Ampel"
_PROJEKT_MODULE = ("main", "u_main", "u_main_design", "u_ampel")


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


def _farben(formular) -> tuple[str, str, str]:
    return (
        formular.s_gruen.brush.color,
        formular.s_rot.brush.color,
        formular.s_gelb.brush.color,
    )


def test_ampel_startet_eingeschaltet_bei_gruen(form1_klasse) -> None:
    formular = form1_klasse()
    assert _farben(formular) == ("#008000", "#000000", "#000000")


def test_ampel_wechseln_durchlaeuft_gruen_gelb_rot_gelb(form1_klasse) -> None:
    formular = form1_klasse()

    formular.b_wechseln._qwidget.click()
    assert _farben(formular) == ("#000000", "#000000", "#ffff00")

    formular.b_wechseln._qwidget.click()
    assert _farben(formular) == ("#000000", "#ff0000", "#000000")

    formular.b_wechseln._qwidget.click()
    assert _farben(formular) == ("#000000", "#000000", "#ffff00")

    formular.b_wechseln._qwidget.click()
    assert _farben(formular) == ("#008000", "#000000", "#000000")


def test_ampel_ausschalten_loescht_alle_lichter(form1_klasse) -> None:
    formular = form1_klasse()

    formular.b_auschalten._qwidget.click()
    assert _farben(formular) == ("#000000", "#000000", "#000000")


def test_ampel_einschalten_zeigt_aktuelle_phase_wieder(form1_klasse) -> None:
    formular = form1_klasse()

    formular.b_wechseln._qwidget.click()  # Phase 2 (gelb)
    formular.b_auschalten._qwidget.click()
    assert _farben(formular) == ("#000000", "#000000", "#000000")

    formular.b_einschalten._qwidget.click()
    assert _farben(formular) == ("#000000", "#000000", "#ffff00")
