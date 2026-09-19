"""Abnahmetest für das Beispielprojekt Garten (M2-Abnahmekriterium:
„Projekt u_pflanzen/u_garten anlegen und starten“, Abschnitt 20/7.4).

Zwei Teile: (1) die Formularlogik headless über echte Qt-Eingaben/-Klicks,
wie bei den M1-Abnahmeprojekten; (2) das Projekt in der IDE öffnen und
prüfen, dass der Explorer die drei Units korrekt gruppiert (`u_main`
gehört zum Formular, `u_pflanzen`/`u_garten` erscheinen bei Units).
"""

import importlib
import sys
from pathlib import Path

import pytest

from ide.shell.hauptfenster import HauptFenster

_GARTEN_ORDNER = Path(__file__).resolve().parent.parent / "beispielprojekte" / "Garten"
_PROJEKT_MODULE = ("main", "u_main", "u_main_design", "u_garten", "u_pflanzen")


@pytest.fixture
def form1_klasse():
    sys.path.insert(0, str(_GARTEN_ORDNER))
    for name in _PROJEKT_MODULE:
        sys.modules.pop(name, None)
    try:
        modul = importlib.import_module("u_main")
        yield modul.Form1
    finally:
        sys.path.remove(str(_GARTEN_ORDNER))
        for name in _PROJEKT_MODULE:
            sys.modules.pop(name, None)


def test_eingabefelder_haben_beschriftungen_die_ins_label_passen(form1_klasse) -> None:
    # Nutzer-Feedback: ohne Beschriftung war nicht erkennbar, wofür die
    # beiden Eingabefelder gedacht sind.
    formular = form1_klasse()
    for label in (formular.l_name, formular.l_wasserbedarf):
        metriken = label._qwidget.fontMetrics()
        benoetigt = metriken.horizontalAdvance(label.caption)
        assert benoetigt <= label.width, (
            f"{label.caption!r} braucht {benoetigt}px, Label ist nur {label.width}px breit"
        )


def test_pflanzen_hinzufuegen_aktualisiert_garten_und_liste(form1_klasse) -> None:
    formular = form1_klasse()

    formular.e_name.text = "Tomate"
    formular.e_wasserbedarf.text = "5"
    formular.b_pflanzen._qwidget.click()

    assert len(formular.garten.beete) == 1
    assert formular.garten.beete[0].name == "Tomate"
    assert formular.garten.beete[0].wasserbedarf == 5
    assert formular.lb_beete._qwidget.count() == 1
    assert formular.lb_beete._qwidget.item(0).text() == "Tomate (Wasserbedarf: 5)"
    # Eingabefelder werden nach dem Pflanzen geleert
    assert formular.e_name.text == ""
    assert formular.e_wasserbedarf.text == ""


def test_ungueltiger_wasserbedarf_wird_ignoriert(form1_klasse) -> None:
    formular = form1_klasse()

    formular.e_name.text = "Rose"
    formular.e_wasserbedarf.text = "viel"
    formular.b_pflanzen._qwidget.click()

    assert formular.garten.beete == []
    assert formular.lb_beete._qwidget.count() == 0


def test_mehrere_pflanzen_werden_gesammelt(form1_klasse) -> None:
    formular = form1_klasse()

    for name, bedarf in (("Tomate", "5"), ("Kaktus", "1")):
        formular.e_name.text = name
        formular.e_wasserbedarf.text = bedarf
        formular.b_pflanzen._qwidget.click()

    assert [p.name for p in formular.garten.beete] == ["Tomate", "Kaktus"]
    assert formular.lb_beete._qwidget.count() == 2


def test_projekt_in_der_ide_oeffnen_gruppiert_units_korrekt() -> None:
    fenster = HauptFenster()
    fenster.projekt_oeffnen(_GARTEN_ORDNER)

    formulare = {
        fenster.explorer.formulare_gruppe.child(i).text(0)
        for i in range(fenster.explorer.formulare_gruppe.childCount())
    }
    units = {
        fenster.explorer.units_gruppe.child(i).text(0)
        for i in range(fenster.explorer.units_gruppe.childCount())
    }
    assert formulare == {"u_main"}
    # Seit M12 steht die Startdatei nicht mehr bei den Units: sie wird
    # erzeugt und nicht bearbeitet, wie die `.lpr` in Lazarus. Erreichbar
    # bleibt sie über „Projekt → Startdatei anzeigen“.
    assert units == {"u_pflanzen.py", "u_garten.py"}
