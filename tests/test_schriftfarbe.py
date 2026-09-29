"""Schriftfarbe für jede Komponente mit Text (Punkt 93)."""

from __future__ import annotations

import json

import pytest
from PySide6.QtGui import QPalette

from ide.codegen.design import design_code_erzeugen
from ide.designer.pfm_schreiben import pfm_aus_formular
from ide.inspector.eigenschaften_tabelle import EigenschaftenTabelle
from pcl import Button, CheckBox, Edit, Form, Label, Memo, Panel, RadioButton
from pcl.errors import NatterPropertyError
from pcl.properties import ART_FARBE, VERSCHACHTELTE_EIGENSCHAFTEN, wert_lesen

MIT_TEXT = [Label, Button, Edit, Memo, CheckBox, RadioButton, Panel]


@pytest.mark.parametrize("klasse", MIT_TEXT, ids=lambda k: k.__name__)
def test_font_color_faerbt_den_text(klasse) -> None:
    komponente = klasse(Form())
    komponente.font.color = "#e53935"

    assert "color: #e53935;" in komponente._qwidget.styleSheet()
    komponente._qwidget.ensurePolished()
    farbe = komponente._qwidget.palette().color(QPalette.ColorRole.WindowText)
    text = komponente._qwidget.palette().color(QPalette.ColorRole.Text)
    assert "#e53935" in (farbe.name(), text.name())


def test_label_behaelt_neben_der_schriftfarbe_seinen_hintergrund() -> None:
    label = Label(Form())
    label.transparent = False
    label.color = "#ffff00"
    label.font.color = "#0000ff"
    qss = label._qwidget.styleSheet()
    assert "background-color: #ffff00;" in qss
    assert "color: #0000ff;" in qss


def test_leer_heisst_farbe_des_farbschemas() -> None:
    label = Label(Form())
    label.font.color = "#e53935"
    label.font.color = ""
    assert "color" not in label._qwidget.styleSheet()


def test_keine_farbe_wird_abgelehnt() -> None:
    label = Label(Form())
    with pytest.raises(NatterPropertyError, match="keine Farbe"):
        label.font.color = "rot-ish"


def test_font_color_steht_im_objektinspektor_mit_farbwaehler(qtbot) -> None:
    eintrag = VERSCHACHTELTE_EIGENSCHAFTEN["font_color"]
    assert (eintrag.attribut, eintrag.unter_attribut) == ("font", "color")
    assert eintrag.art == ART_FARBE

    label = Label(Form())
    tabelle = EigenschaftenTabelle()
    qtbot.addWidget(tabelle)
    tabelle.komponente_anzeigen(label)
    assert tabelle.art_von("font_color") == ART_FARBE
    assert tabelle.kategorie_von("font_color") == "Schrift"


def test_font_color_geht_durch_pfm_und_erzeugten_code() -> None:
    class Formular(Form):
        def create_components(self) -> None:
            self.l_antwort = Label(self)
            self.l_antwort.font.color = "#e53935"

    formular = Formular()
    pfm = pfm_aus_formular(formular)
    eintrag = pfm["children"][0]
    assert eintrag["properties"]["font_color"] == "#e53935"

    code = design_code_erzeugen(json.loads(json.dumps(pfm)), "u_test.pfm")
    assert 'self.l_antwort.font.color = "#e53935"' in code
    assert wert_lesen(formular.l_antwort, "font_color") == "#e53935"
