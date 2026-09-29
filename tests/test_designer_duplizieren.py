"""Duplizieren im Designer übernimmt die ganze Komponente und bleibt
im Behälter des Originals (Punkt 121). Headless.
"""

import json
from pathlib import Path

import pytest

from ide.designer.canvas import RASTER, DesignerCanvas
from ide.designer.laden import formular_fuer_designer_laden

_PFM = {
    "format": "pfm/1",
    "class": "Form1",
    "type": "Form",
    "properties": {"width": 480, "height": 360},
    "children": [
        {
            "name": "lb_namen",
            "type": "ListBox",
            "properties": {
                "left": 8, "top": 8, "width": 140, "height": 90,
                "items": ["Anna", "Ben"],
                "font_size": 14,
            },
        },
        {
            "name": "m_text",
            "type": "Memo",
            "properties": {
                "left": 160, "top": 8, "width": 180, "height": 90,
                "lines": ["erste", "zweite"],
            },
        },
        {
            "name": "mm_haupt",
            "type": "MainMenu",
            "properties": {
                "left": 400, "top": 8,
                "entries": [
                    {"caption": "&Datei", "children": [{"caption": "&Ende"}]}
                ],
            },
        },
        {
            "name": "p_feld",
            "type": "Panel",
            "properties": {"left": 8, "top": 120, "width": 240, "height": 120},
            "children": [
                {
                    "name": "b_innen",
                    "type": "Button",
                    "properties": {"left": 200, "top": 50, "caption": "Los"},
                    "events": {"on_click": "b_innen_click"},
                }
            ],
        },
    ],
}


def _designer(tmp_path: Path) -> tuple[Path, DesignerCanvas]:
    pfm_pfad = tmp_path / "u_main.pfm"
    pfm_pfad.write_text(json.dumps(_PFM), encoding="utf-8")
    formular = formular_fuer_designer_laden(pfm_pfad)
    return pfm_pfad, DesignerCanvas(formular, pfm_pfad=pfm_pfad)


def _eintrag(eintraege: list[dict], name: str) -> dict:
    for eintrag in eintraege:
        if eintrag["name"] == name:
            return eintrag
        gefunden = _eintrag(eintrag.get("children", []), name)
        if gefunden:
            return gefunden
    return {}


def _ohne_name_und_lage(eintrag: dict) -> dict:
    kopie = json.loads(json.dumps(eintrag))
    kopie.pop("name")
    kopie["properties"].pop("left", None)
    kopie["properties"].pop("top", None)
    for kind in kopie.get("children", []):
        kind.pop("name")
    return kopie


@pytest.mark.parametrize("name", ["lb_namen", "m_text", "mm_haupt", "p_feld"])
def test_kopie_gleicht_dem_original_bis_auf_name_und_lage(
    tmp_path: Path, name: str
) -> None:
    pfm_pfad, canvas = _designer(tmp_path)
    original = getattr(canvas.formular, name)

    kopie = canvas.duplizieren(original)

    kopie_name = canvas._attributname(kopie)
    assert kopie_name == f"{name}_kopie"
    canvas.jetzt_schreiben()
    daten = json.loads(pfm_pfad.read_text(encoding="utf-8"))["children"]
    vorher = _eintrag(daten, name)
    nachher = _eintrag(daten, kopie_name)
    assert _ohne_name_und_lage(nachher) == _ohne_name_und_lage(vorher)
    assert nachher["properties"]["left"] == original.left + RASTER
    assert nachher["properties"]["top"] == original.top + RASTER


def test_kopie_eines_knopfs_im_panel_bleibt_im_panel(tmp_path: Path) -> None:
    pfm_pfad, canvas = _designer(tmp_path)
    panel = canvas.formular.p_feld
    knopf = canvas.formular.b_innen

    kopie = canvas.duplizieren(knopf)

    assert kopie.eltern is panel
    assert kopie._qwidget.parentWidget() is panel._qwidget
    assert (kopie.left, kopie.top) == (knopf.left + RASTER, knopf.top + RASTER)
    assert kopie.caption == "Los"
    assert kopie.on_click.__name__ == "b_innen_click"
    canvas.jetzt_schreiben()
    daten = json.loads(pfm_pfad.read_text(encoding="utf-8"))["children"]
    panel_eintrag = _eintrag(daten, "p_feld")
    assert [k["name"] for k in panel_eintrag["children"]] == [
        "b_innen", "b_innen_kopie"
    ]


def test_duplizieren_eines_panels_ist_ein_schritt(tmp_path: Path) -> None:
    pfm_pfad, canvas = _designer(tmp_path)

    canvas.duplizieren(canvas.formular.p_feld)
    assert hasattr(canvas.formular, "b_innen_kopie")
    canvas.rueckgaengig()

    assert not hasattr(canvas.formular, "p_feld_kopie")
    assert not hasattr(canvas.formular, "b_innen_kopie")
    canvas.jetzt_schreiben()
    daten = json.loads(pfm_pfad.read_text(encoding="utf-8"))["children"]
    assert [k["name"] for k in daten] == [
        "lb_namen", "m_text", "mm_haupt", "p_feld"
    ]
