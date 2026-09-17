"""Abnahmetest für das Beispielprojekt StringGrid-Übung (M1, Schritt 8).

Headless über echte Qt-Eingaben/-Klicks; der `show_message`-Dialog bei zu
langen Eingaben wird über `QTimer.singleShot` bedient wie in
tests/test_dialogs.py.
"""

import importlib
import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

_PROJEKT_ORDNER = Path(__file__).resolve().parent.parent / "beispielprojekte" / "StringGridUebung"
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


def _eingeben(formular, name: str, vorname: str, datum: str) -> None:
    formular.e_name.text = name
    formular.e_vorname.text = vorname
    formular.e_datum.text = datum


def test_eingabefeld_beschriftungen_sind_breit_genug(form1_klasse) -> None:
    # Real per Screenshot gefunden: "Geburtsdatum:" wurde abgeschnitten
    # ("Geburtsdatun" ohne das "m" am Ende).
    formular = form1_klasse()
    for label in (formular.l_name, formular.l_vorname, formular.l_geburtsdatum):
        metriken = label._qwidget.fontMetrics()
        benoetigt = metriken.horizontalAdvance(label.caption)
        assert benoetigt <= label.width, (
            f"{label.caption!r} braucht {benoetigt}px, Label ist nur {label.width}px breit"
        )


def test_kopfzeile_steht_nach_dem_start(form1_klasse) -> None:
    formular = form1_klasse()
    kopf = [formular.sg_tabelle.cells[spalte, 0] for spalte in range(4)]
    assert kopf == ["Nr.", "Name", "Vorname", "Geb.-Dat."]
    assert formular.sg_tabelle.row_count == 2


def test_uebernehmen_traegt_zeile_ein(form1_klasse) -> None:
    formular = form1_klasse()
    _eingeben(formular, "Muster", "Max", "01.01.2000")

    formular.b_uebernehmen._qwidget.click()

    zeile1 = [formular.sg_tabelle.cells[spalte, 1] for spalte in range(4)]
    assert zeile1 == ["1", "Muster", "Max", "01.01.2000"]


def test_zu_lange_eingabe_zeigt_hinweis_und_ueberschreibt_zeile(form1_klasse) -> None:
    formular = form1_klasse()

    gesehener_text = []

    def bedienen() -> None:
        box = QApplication.activeModalWidget()
        gesehener_text.append(box.text())
        box.accept()

    _eingeben(formular, "EinSehrLangerNachname", "Max", "01.01.2000")
    QTimer.singleShot(0, bedienen)
    formular.b_uebernehmen._qwidget.click()

    assert gesehener_text == ["Deinen Eingaben sind zu Lang"]
    # Zeile 1 bleibt leer, weil die zu lange Eingabe verworfen wurde
    assert formular.sg_tabelle.cells[1, 1] == ""

    _eingeben(formular, "Muster", "Max", "01.01.2000")
    formular.b_uebernehmen._qwidget.click()

    zeile1 = [formular.sg_tabelle.cells[spalte, 1] for spalte in range(4)]
    assert zeile1 == ["1", "Muster", "Max", "01.01.2000"]


def test_zuruecksetzen_leert_erste_zeile(form1_klasse) -> None:
    formular = form1_klasse()
    _eingeben(formular, "Muster", "Max", "01.01.2000")
    formular.b_uebernehmen._qwidget.click()

    formular.b_zuruecksetzen._qwidget.click()

    zeile1 = [formular.sg_tabelle.cells[spalte, 1] for spalte in range(4)]
    assert zeile1 == ["", "", "", ""]
    assert formular.sg_tabelle.row_count == 2


def test_schliessen_schliesst_das_fenster(form1_klasse) -> None:
    formular = form1_klasse()
    formular.show()
    formular.b_schliessen._qwidget.click()
    assert formular._qwidget.isVisible() is False
