"""Tests für die Klassen-/Eigenschaftszuordnung `.lfm` → `.pfm`
(Abschnitt 15). Siehe docs/arbeitspakete/M8.md, Schritt 2.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from ide.import_lfm.parser import parse_lfm
from ide.import_lfm.zuordnung import lfm_zu_pfm

_REFERENZ = Path(__file__).resolve().parent.parent / "referenz" / "lazarus"
_SCHEMA = json.loads(
    (Path(__file__).resolve().parent.parent / "schemas" / "pfm.schema.json").read_text(
        encoding="utf-8"
    )
)


def _lfm(text: str) -> dict:
    return parse_lfm(text)


def test_klassenzuordnung_button() -> None:
    lfm = _lfm("object Form1: TForm1\n  object b_x: TButton\n    Caption = 'X'\n  end\nend\n")
    ergebnis = lfm_zu_pfm(lfm)
    assert ergebnis.pfm["children"][0]["type"] == "Button"
    assert not ergebnis.warnungen


def test_unbekannte_klasse_wird_gemeldet_und_uebersprungen() -> None:
    lfm = _lfm(
        "object Form1: TForm1\n  object t_x: TTrackBar\n    Left = 0\n  end\nend\n"
    )
    ergebnis = lfm_zu_pfm(lfm)
    assert ergebnis.pfm["children"] == []
    assert any("TTrackBar" in w for w in ergebnis.warnungen)


def test_eigenschaften_werden_umgewandelt() -> None:
    lfm = _lfm(
        "object Form1: TForm1\n"
        "  object cb_x: TCheckBox\n"
        "    Caption = 'Ja'\n"
        "    Checked = True\n"
        "    Left = 10\n"
        "    Top = 20\n"
        "    Width = 30\n"
        "    Height = 40\n"
        "  end\n"
        "end\n"
    )
    ergebnis = lfm_zu_pfm(lfm)
    eigenschaften = ergebnis.pfm["children"][0]["properties"]
    assert eigenschaften == {
        "caption": "Ja",
        "checked": True,
        "left": 10,
        "top": 20,
        "width": 30,
        "height": 40,
    }


def test_form_left_top_werden_verworfen() -> None:
    lfm = _lfm("object Form1: TForm1\n  Left = 100\n  Top = 200\n  Caption = 'X'\nend\n")
    ergebnis = lfm_zu_pfm(lfm)
    assert "left" not in ergebnis.pfm["properties"]
    assert "top" not in ergebnis.pfm["properties"]
    assert ergebnis.pfm["properties"]["caption"] == "X"


def test_unbekannte_eigenschaft_wird_gemeldet_und_uebersprungen() -> None:
    lfm = _lfm(
        "object Form1: TForm1\n"
        "  object l_x: TLabel\n"
        "    Caption = 'X'\n"
        "    ParentFont = False\n"
        "  end\n"
        "end\n"
    )
    ergebnis = lfm_zu_pfm(lfm)
    assert "ParentFont" not in ergebnis.pfm["children"][0]["properties"]
    assert any("ParentFont" in w for w in ergebnis.warnungen)


@pytest.mark.parametrize(
    ("konstante", "hex_wert"),
    [
        ("clBlack", "#000000"),
        ("clGray", "#808080"),
        ("clSilver", "#c0c0c0"),
        ("clYellow", "#ffff00"),
    ],
)
def test_farbkonstanten_werden_umgewandelt(konstante: str, hex_wert: str) -> None:
    lfm = _lfm(
        f"object Form1: TForm1\n"
        f"  object s_x: TShape\n"
        f"    Brush.Color = {konstante}\n"
        f"  end\n"
        f"end\n"
    )
    ergebnis = lfm_zu_pfm(lfm)
    assert ergebnis.pfm["children"][0]["properties"]["brush_color"] == hex_wert


def test_lazarus_hex_farbe_umgekehrte_byte_reihenfolge() -> None:
    # $00BBGGRR: rot=FF, grün=80, blau=00 -> #ff8000
    lfm = _lfm(
        "object Form1: TForm1\n"
        "  object s_x: TShape\n"
        "    Brush.Color = $000080FF\n"
        "  end\n"
        "end\n"
    )
    ergebnis = lfm_zu_pfm(lfm)
    assert ergebnis.pfm["children"][0]["properties"]["brush_color"] == "#ff8000"


def test_unbekannte_farbkonstante_wird_gemeldet() -> None:
    lfm = _lfm(
        "object Form1: TForm1\n"
        "  object s_x: TShape\n"
        "    Brush.Color = clNichtVorhanden\n"
        "  end\n"
        "end\n"
    )
    ergebnis = lfm_zu_pfm(lfm)
    assert "brush_color" not in ergebnis.pfm["children"][0]["properties"]
    assert any("clNichtVorhanden" in w for w in ergebnis.warnungen)


@pytest.mark.parametrize(
    ("lazarus_form", "pcl_form"),
    [("stRectangle", "rectangle"), ("stCircle", "circle"), ("stRoundSquare", "rounded_rectangle")],
)
def test_shape_form_wird_umgewandelt(lazarus_form: str, pcl_form: str) -> None:
    lfm = _lfm(
        f"object Form1: TForm1\n"
        f"  object s_x: TShape\n"
        f"    Shape = {lazarus_form}\n"
        f"  end\n"
        f"end\n"
    )
    ergebnis = lfm_zu_pfm(lfm)
    assert ergebnis.pfm["children"][0]["properties"]["shape"] == pcl_form


@pytest.mark.parametrize(
    ("ereignis", "handler", "erwartet_schluessel", "erwarteter_handler"),
    [
        ("OnClick", "b_einschaltenClick", "on_click", "b_einschalten_click"),
        ("OnCreate", "FormCreate", "on_create", "form_create"),
        ("OnChange", "e_nameChange", "on_change", "e_name_change"),
    ],
)
def test_ereignis_handler_werden_umgewandelt(
    ereignis: str, handler: str, erwartet_schluessel: str, erwarteter_handler: str
) -> None:
    if ereignis == "OnCreate":
        lfm = _lfm(f"object Form1: TForm1\n  {ereignis} = {handler}\nend\n")
        ergebnis = lfm_zu_pfm(lfm)
        assert ergebnis.pfm["events"] == {erwartet_schluessel: erwarteter_handler}
    else:
        lfm = _lfm(
            f"object Form1: TForm1\n"
            f"  object b_x: TButton\n"
            f"    {ereignis} = {handler}\n"
            f"  end\n"
            f"end\n"
        )
        ergebnis = lfm_zu_pfm(lfm)
        assert ergebnis.pfm["children"][0]["events"] == {erwartet_schluessel: erwarteter_handler}


def test_nicht_unterstuetztes_ereignis_wird_gemeldet() -> None:
    lfm = _lfm(
        "object Form1: TForm1\n"
        "  object s_x: TShape\n"
        "    OnChangeBounds = s_xChangeBounds\n"
        "  end\n"
        "end\n"
    )
    ergebnis = lfm_zu_pfm(lfm)
    assert "events" not in ergebnis.pfm["children"][0]
    assert any("OnChangeBounds" in w for w in ergebnis.warnungen)


def test_ende_zu_ende_gegen_echtes_ampel_lfm_ist_gueltiges_pfm() -> None:
    text = (_REFERENZ / "k_Ampel" / "u_main.lfm").read_text(encoding="utf-8")
    ergebnis = lfm_zu_pfm(parse_lfm(text))

    jsonschema.validate(ergebnis.pfm, _SCHEMA)

    assert ergebnis.pfm["properties"]["caption"] == "Form1"
    assert len(ergebnis.pfm["children"]) == 8
    namen = [k["name"] for k in ergebnis.pfm["children"]]
    assert "b_einschalten" in namen
    assert "s_rot" in namen

    s_rot = next(k for k in ergebnis.pfm["children"] if k["name"] == "s_rot")
    assert s_rot["properties"]["shape"] == "circle"
    assert s_rot["properties"]["brush_color"] == "#000000"

    b_wechseln = next(k for k in ergebnis.pfm["children"] if k["name"] == "b_wechseln")
    assert b_wechseln["events"] == {"on_click": "b_wechseln_click"}

    # OnChangeBounds (bei s_rot im echten .lfm vorhanden) wird nicht
    # unterstützt und muss im Importbericht auftauchen.
    assert any("OnChangeBounds" in w for w in ergebnis.warnungen)
