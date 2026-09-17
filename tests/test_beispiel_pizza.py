"""Abnahmetest für das Beispielprojekt Pizza – zugleich die M8-Abnahme
„ein Lazarus-Übungsprojekt importieren und fertigstellen“.

Das Formular stammt nicht aus dem Designer, sondern wurde über
„Werkzeuge → Lazarus-Formular importieren …“ aus dem echten
`referenz/lazarus/f_Pizza/unit1.lfm` übernommen; die Logik ist aus
`unit1.pas` nachgebildet. Siehe docs/arbeitspakete/M8.md, Schritt 6.

Geprüft wird über echte Qt-Interaktionen (Klicks, Bildlaufleiste), nicht
durch Nachrechnen im Test.
"""

import importlib
import json
import sys
from pathlib import Path

import pytest

_PROJEKT_ORDNER = Path(__file__).resolve().parent.parent / "beispielprojekte" / "Pizza"
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


def test_kurzwahl_ist_beim_start_gefuellt(form1_klasse) -> None:
    formular = form1_klasse()

    assert len(formular.lb_KurzWahl.items) == 10
    assert formular.lb_KurzWahl.items[0] == "Hawaii (8,50 EUR)"


def test_normale_pizza_mit_19_prozent(form1_klasse) -> None:
    formular = form1_klasse()
    formular.lb_KurzWahl.item_index = 0

    formular.b_hinzufuegen._qwidget.click()

    # 8,50 * 1,0 * 1,19 = 10,115 -> 10,12
    assert formular.m_zettel.lines[0] == "Pizza Hawaii Normal - 10,12 EUR"


def test_groesse_und_belaege_wirken_auf_den_preis(form1_klasse) -> None:
    formular = form1_klasse()
    formular.lb_KurzWahl.item_index = 1
    formular.rb_XXL._qwidget.setChecked(True)
    formular.c_kaese._qwidget.setChecked(True)
    formular.c_knoblauch._qwidget.setChecked(True)
    formular.cb_mws.item_index = 0

    formular.b_hinzufuegen._qwidget.click()

    # (8,50 * 1,4 + 1,99 + 0,50) * 1,07 = 15,4043 -> 15,40
    assert formular.m_zettel.lines[0] == "Pizza Napoli XXL - 15,40 EUR"


def test_eigene_eingabe_hat_vorrang_vor_der_kurzwahl(form1_klasse) -> None:
    """Im Original blieben beide Eingabefelder unbenutzt; beim
    Fertigstellen wurden sie verdrahtet."""
    formular = form1_klasse()
    formular.e_eingabeSorte.text = "Calzone"
    formular.e_Grundpreis.text = "10,00"
    formular.rb_small._qwidget.setChecked(True)
    formular.cb_mws.item_index = 0

    formular.b_hinzufuegen._qwidget.click()

    # 10,00 * 0,8 * 1,07 = 8,56
    assert formular.m_zettel.lines[0] == "Pizza Calzone Small - 8,56 EUR"


def test_kassenzettel_leeren(form1_klasse) -> None:
    formular = form1_klasse()
    formular.b_hinzufuegen._qwidget.click()
    assert len(formular.m_zettel.lines) == 1

    formular.b_zettelLeer._qwidget.click()

    assert len(formular.m_zettel.lines) == 0
    assert formular.m_zettel._qwidget.toPlainText() == ""


def test_bildlaufleiste_steuert_die_schriftgroesse(form1_klasse) -> None:
    """Der eigentliche Zweck der ScrollBar im Original
    (`m_zettel.Font.size := sb_behinderung.position`) – erst durch die
    neue `font`-Untereigenschaft überhaupt umsetzbar."""
    formular = form1_klasse()

    formular.sb_behinderung._qwidget.setValue(28)

    assert formular.m_zettel.font.size == 28
    assert "font-size: 28pt;" in formular.m_zettel._qwidget.styleSheet()


def test_formular_stammt_aus_dem_lazarus_import(form1_klasse) -> None:
    """Belegt, dass die aus der `.lfm` übernommenen Eigenschaften
    (Schrift, Sammlung, ScrollBar-Grenzen) im Projekt angekommen sind."""
    formular = form1_klasse()

    assert formular.l_Kassenzettel.font.size == 24
    assert formular.l_Kassenzettel.font.name == "Bodoni MT"
    assert formular.l_Kassenzettel.font.bold is True
    assert list(formular.cb_mws.items) == ["7", "19"]
    assert formular.sb_behinderung.minimum == 5
    assert formular.sb_behinderung.maximum == 50
    assert formular.m_zettel.read_only is True


def test_keine_komponente_ueberdeckt_eine_andere(form1_klasse) -> None:
    """Beim Fertigstellen behoben: die aus Lazarus übernommenen Breiten
    sind für Qts Schriftmetrik zu knapp, wodurch sich Beschriftungen
    gegenseitig überdeckten. Labels über Eingabefeldern sind wie im
    Original gewollt und daher ausgenommen."""
    formular = form1_klasse()
    gewollt = {("l_eingabeSorte", "e_eingabeSorte"), ("l_grundpreis", "e_Grundpreis")}
    kinder = [(name, k) for name, k in vars(formular).items() if hasattr(k, "left")]

    for i, (name_a, a) in enumerate(kinder):
        for name_b, b in kinder[i + 1 :]:
            if {(name_a, name_b), (name_b, name_a)} & gewollt:
                continue
            ueberlappt = (
                a.left < b.left + b.width
                and b.left < a.left + a.width
                and a.top < b.top + b.height
                and b.top < a.top + a.height
            )
            assert not ueberlappt, f"{name_a} überdeckt {name_b}"


def test_projektdatei_und_generierter_code_passen_zusammen() -> None:
    """Der Designer kompiliert den erzeugten Code nur im Speicher – hier
    wird geprüft, dass die Datei auf der Platte wirklich zur `.pfm`
    passt (real gefunden: nach dem Import blieb sie das leere
    Vorlagenformular)."""
    from ide.codegen.design import design_code_erzeugen

    pfm_pfad = _PROJEKT_ORDNER / "u_main.pfm"
    pfm = json.loads(pfm_pfad.read_text(encoding="utf-8"))

    erwartet = design_code_erzeugen(pfm, pfm_pfad.name)

    assert (_PROJEKT_ORDNER / "u_main_design.py").read_text(encoding="utf-8") == erwartet
