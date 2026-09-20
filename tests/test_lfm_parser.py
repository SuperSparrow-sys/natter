"""Tests für den `.lfm`-Parser (Abschnitt 15). Siehe
docs/arbeitspakete/M8.md, Schritt 1. Gegen echte `.lfm`-Dateien aus
`tests/daten/lfm/`, kein Mock.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ide.import_lfm.parser import LfmParserError, parse_lfm

_REFERENZ = Path(__file__).resolve().parent / "daten" / "lfm"

_ALLE_LFM_DATEIEN = sorted(_REFERENZ.glob("*/unit1.lfm")) + sorted(_REFERENZ.glob("*/u_main.lfm"))


def _laden(pfad: Path) -> dict:
    return parse_lfm(pfad.read_text(encoding="utf-8"))


def test_ampel_wurzelobjekt_und_kinder() -> None:
    objekt = _laden(_REFERENZ / "k_Ampel" / "u_main.lfm")

    assert objekt["name"] == "Form1"
    assert objekt["class"] == "TForm1"
    assert objekt["properties"]["Caption"] == "Form1"
    assert objekt["properties"]["Width"] == 620
    assert objekt["properties"]["OnCreate"] == "FormCreate"

    namen = [kind["name"] for kind in objekt["children"]]
    assert namen == [
        "b_einschalten",
        "b_wechseln",
        "b_Auschalten",
        "Label1",
        "Shape1",
        "s_rot",
        "s_gelb",
        "s_gruen",
    ]

    b_wechseln = objekt["children"][1]
    assert b_wechseln["class"] == "TButton"
    assert b_wechseln["properties"]["Caption"] == "Wechseln"
    assert b_wechseln["properties"]["OnClick"] == "b_wechselnClick"

    s_rot = objekt["children"][5]
    assert s_rot["properties"]["Brush.Color"] == "clBlack"
    assert s_rot["properties"]["Shape"] == "stCircle"


def test_negative_zahl_wird_als_int_geparst() -> None:
    objekt = _laden(_REFERENZ / "a_GUI_Komponenten" / "unit1.lfm")
    label = next(k for k in objekt["children"] if k["properties"].get("Font.Height") is not None)
    assert isinstance(label["properties"]["Font.Height"], int)
    assert label["properties"]["Font.Height"] < 0


def test_mengen_klammer_wird_als_liste_geparst() -> None:
    objekt = _laden(_REFERENZ / "a_GUI_Komponenten" / "unit1.lfm")
    label = next(k for k in objekt["children"] if "Font.Style" in k["properties"])
    assert label["properties"]["Font.Style"] == ["fsBold"]


def test_mehrzeilige_sammlung_items_strings() -> None:
    objekt = _laden(_REFERENZ / "f_Pizza" / "unit1.lfm")
    combobox = next(k for k in objekt["children"] if k["name"] == "cb_mws")
    assert combobox["properties"]["Items.Strings"] == ["7", "19"]


def test_mehrzeilige_sammlung_cells_mit_gemischten_typen() -> None:
    objekt = _laden(_REFERENZ / "g_StringGrid" / "unit1.lfm")
    grid = next(k for k in objekt["children"] if k["name"] == "sg_Tabelle")
    assert grid["properties"]["Cells"] == [
        4,
        0,
        0,
        "Nr.",
        1,
        0,
        "Name",
        2,
        0,
        "Vorname",
        3,
        0,
        "Geb.-Dat.",
    ]


def test_binaerblock_picture_data_wird_uebersprungen_ohne_absturz() -> None:
    objekt = _laden(_REFERENZ / "d_Cookie_klicker" / "unit1.lfm")

    bild = next(k for k in objekt["children"] if "Picture.Data" in k["properties"])
    wert = bild["properties"]["Picture.Data"]
    assert isinstance(wert, dict) and "binaer" in wert
    assert len(wert["binaer"]) > 100

    # Der Rest der Datei (nach dem Binärblock) muss trotzdem vollständig
    # geparst sein - der Button mit dem Bild hat noch weitere Kinder
    # danach im Formular.
    assert len(objekt["children"]) > 1


def test_ungueltiger_text_loest_lfmparsererror_aus() -> None:
    with pytest.raises(LfmParserError):
        parse_lfm("das ist kein .lfm")


def test_fehlendes_end_loest_lfmparsererror_aus() -> None:
    with pytest.raises(LfmParserError):
        parse_lfm("object Form1: TForm1\n  Caption = 'x'\n")


@pytest.mark.parametrize("pfad", _ALLE_LFM_DATEIEN, ids=lambda p: p.parent.name)
def test_alle_echten_referenzprojekte_parsen_ohne_absturz(pfad: Path) -> None:
    objekt = _laden(pfad)
    assert objekt["class"].startswith("TForm")
    assert isinstance(objekt["children"], list)
