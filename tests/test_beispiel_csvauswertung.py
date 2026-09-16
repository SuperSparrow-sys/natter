"""Abnahmetest für das Beispielprojekt CsvAuswertung (M5, Schritt 9).

Treibt die Logik headless über einen echten Qt-Klick, wie
tests/test_beispiel_ampel.py. Liest nur eine Datei, schreibt keine -
anders als bei der Kontoverwaltung ist deshalb keine Kopie nach
`tmp_path` nötig (AGENTS.md verlangt das nur für Tests, die Zustand
verändern).
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

_PROJEKT_ORDNER = Path(__file__).resolve().parent.parent / "beispielprojekte" / "CsvAuswertung"
_PROJEKT_MODULE = ("main", "u_main")


@pytest.fixture
def form1_klasse(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(_PROJEKT_ORDNER)
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


def test_auswerten_fuellt_stringgrid_mit_gruppierten_summen(form1_klasse) -> None:
    formular = form1_klasse()

    formular.b_auswerten._qwidget.click()

    df = formular.sg_auswertung.to_dataframe()
    assert list(df.columns) == ["region", "umsatz"]
    summen = {zeile["region"]: float(zeile["umsatz"]) for _, zeile in df.iterrows()}
    assert summen["Nord"] == pytest.approx(1500.75)
    assert summen["Süd"] == pytest.approx(800.0)
    assert summen["Ost"] == pytest.approx(1700.75)
    assert summen["West"] == pytest.approx(600.30)


def test_auswerten_zeichnet_einen_balken_je_region(form1_klasse) -> None:
    formular = form1_klasse()

    formular.b_auswerten._qwidget.click()

    assert len(formular.ch_umsatz._achse.patches) == 4
    assert formular.ch_umsatz._achse.get_title() == "Umsatz je Region"
