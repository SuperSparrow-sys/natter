"""Tests für ide/codegen/design.py: `.pfm` -> `u_*_design.py`. Siehe
PLAN.md (Git-Historie), M1 Schritt 4.
"""

from typing import Any

import jsonschema
import pytest

from ide.codegen.design import design_code_erzeugen

PFM: dict[str, Any] = {
    "format": "pfm/1",
    "class": "Form1",
    "type": "Form",
    "properties": {"caption": "Ampel", "width": 480, "height": 360, "theme": "system"},
    "events": {"on_create": "form_create"},
    "children": [
        {
            "name": "b_ein",
            "type": "Button",
            "properties": {
                "caption": "Einschalten",
                "left": 24,
                "top": 24,
                "width": 120,
                "height": 32,
            },
            "events": {"on_click": "b_ein_click"},
        },
        {
            "name": "s_rot",
            "type": "Shape",
            "properties": {
                "shape": "circle",
                "left": 200,
                "top": 24,
                "width": 64,
                "height": 64,
                "brush_color": "#000000",
            },
        },
    ],
}


def _design_klasse_laden(pfm: dict[str, Any] = PFM) -> type:
    quelltext = design_code_erzeugen(pfm, "u_main.pfm")
    namensraum: dict[str, Any] = {}
    exec(compile(quelltext, "<erzeugt>", "exec"), namensraum)
    return namensraum[f"{pfm['class']}Design"]


def test_kopfzeile_markiert_datei_als_generiert() -> None:
    quelltext = design_code_erzeugen(PFM, "u_main.pfm")
    assert quelltext.startswith("# Automatisch erzeugt aus u_main.pfm - nicht bearbeiten\n")


def test_importe_enthalten_alle_verwendeten_typen_sortiert() -> None:
    quelltext = design_code_erzeugen(PFM, "u_main.pfm")
    assert "from pcl import Button, Form, Shape\n" in quelltext


def test_ungueltige_pfm_wird_abgelehnt() -> None:
    kaputt = {"format": "pfm/1"}  # Pflichtfelder fehlen
    with pytest.raises(jsonschema.ValidationError):
        design_code_erzeugen(kaputt, "kaputt.pfm")


def test_erzeugte_klasse_liefert_dieselben_werte_wie_die_pfm() -> None:
    form1_design = _design_klasse_laden()

    class Form1(form1_design):
        def form_create(self, sender: Any) -> None:
            pass

        def b_ein_click(self, sender: Any) -> None:
            pass

    formular = Form1()

    assert formular.caption == "Ampel"
    assert formular.width == 480
    assert formular.height == 360
    assert formular.theme == "system"

    assert formular.b_ein.caption == "Einschalten"
    assert (formular.b_ein.left, formular.b_ein.top) == (24, 24)
    assert (formular.b_ein.width, formular.b_ein.height) == (120, 32)

    assert formular.s_rot.shape == "circle"
    assert formular.s_rot.left == 200
    assert formular.s_rot.brush.color == "#000000"


def test_on_create_handler_wird_verknuepft() -> None:
    form1_design = _design_klasse_laden()
    aufgerufen = []

    class Form1(form1_design):
        def form_create(self, sender: Any) -> None:
            aufgerufen.append(sender)

        def b_ein_click(self, sender: Any) -> None:
            pass

    formular = Form1()
    assert aufgerufen == [formular]


def test_button_klick_ruft_verknuepften_handler_auf() -> None:
    form1_design = _design_klasse_laden()
    geklickt = []

    class Form1(form1_design):
        def form_create(self, sender: Any) -> None:
            pass

        def b_ein_click(self, sender: Any) -> None:
            geklickt.append(sender)

    formular = Form1()
    formular.b_ein._qwidget.click()
    assert geklickt == [formular.b_ein]


def test_formular_ohne_kinder_erzeugt_leeren_rumpf_mit_pass() -> None:
    minimal = {"format": "pfm/1", "class": "Leer", "type": "Form", "properties": {}}
    quelltext = design_code_erzeugen(minimal, "u_leer.pfm")
    assert f"{' ' * 8}pass" in quelltext
