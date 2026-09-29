"""Tests für Namen, die beim Umbenennen im Designer nicht gehen
(Punkte 113 und 120): Eigenschaften und Methoden der Formularklasse
und Schlüsselwörter. Headless.
"""

import json
from pathlib import Path

import pytest

from ide.designer.canvas import DesignerCanvas, _UmbenennenKommando
from ide.designer.laden import formular_fuer_designer_laden
from ide.inspector import Objektinspektor

_PFM = {
    "format": "pfm/1",
    "class": "Form1",
    "type": "Form",
    "properties": {"caption": "Test", "width": 300, "height": 200},
    "children": [
        {
            "name": "e_x",
            "type": "Edit",
            "properties": {"left": 8, "top": 8, "width": 120, "height": 25},
        },
        {
            "name": "b_ok",
            "type": "Button",
            "properties": {"left": 8, "top": 48, "width": 75, "height": 25},
        },
    ],
}


def _designer(tmp_path: Path) -> tuple[Path, DesignerCanvas]:
    pfm_pfad = tmp_path / "u_main.pfm"
    pfm_pfad.write_text(json.dumps(_PFM), encoding="utf-8")
    formular = formular_fuer_designer_laden(pfm_pfad)
    return pfm_pfad, DesignerCanvas(formular, pfm_pfad=pfm_pfad)


def _namen_in_pfm(pfm_pfad: Path) -> list[str]:
    daten = json.loads(pfm_pfad.read_text(encoding="utf-8"))
    return [kind["name"] for kind in daten["children"]]


@pytest.mark.parametrize("name", ["caption", "width", "color", "show", "close"])
def test_namen_der_formularklasse_werden_abgelehnt(
    tmp_path: Path, name: str
) -> None:
    _, canvas = _designer(tmp_path)
    feld = canvas.formular.e_x

    with pytest.raises(ValueError, match="des Formulars"):
        canvas.komponente_umbenennen(feld, name)

    assert canvas.formular.e_x is feld
    assert name not in vars(canvas.formular)


def test_umbenennen_in_caption_zeigt_meldung_und_behaelt_die_komponente(
    tmp_path: Path,
) -> None:
    pfm_pfad, canvas = _designer(tmp_path)
    inspektor = Objektinspektor()
    inspektor.formular_anzeigen(canvas.formular, canvas)
    baum = inspektor.baum.topLevelItem(0)
    inspektor.baum.setCurrentItem(baum.child(0))
    tabelle = inspektor.eigenschaften_tabelle
    assert tabelle.item(0, 1).text() == "e_x"

    tabelle.item(0, 1).setText("caption")

    assert "des Formulars" in tabelle.fehlertext
    assert tabelle.item(0, 1).text() == "e_x"
    assert "e_x" in vars(canvas.formular)
    canvas.verschieben(8, 0, canvas.formular.b_ok)
    assert _namen_in_pfm(pfm_pfad) == ["e_x", "b_ok"]


def test_gescheitertes_umbenennen_laesst_das_attribut_stehen(
    tmp_path: Path,
) -> None:
    """Auch ohne die Prüfung vorab: scheitert das Setzen des neuen
    Namens, bleibt der alte."""
    _, canvas = _designer(tmp_path)
    feld = canvas.formular.e_x

    kommando = _UmbenennenKommando(canvas, feld, "caption")
    with pytest.raises(TypeError):
        kommando.tun()

    assert canvas.formular.e_x is feld
    assert list(vars(canvas.formular)).index("e_x") < list(
        vars(canvas.formular)
    ).index("b_ok")


@pytest.mark.parametrize("name", ["class", "for", "None", "lambda"])
def test_schluesselwoerter_werden_abgelehnt(tmp_path: Path, name: str) -> None:
    pfm_pfad, canvas = _designer(tmp_path)
    feld = canvas.formular.e_x

    with pytest.raises(ValueError, match="Schlüsselwort"):
        canvas.komponente_umbenennen(feld, name)

    assert canvas.formular.e_x is feld
    design = (tmp_path / "u_main_design.py")
    if design.exists():
        compile(design.read_text(encoding="utf-8"), str(design), "exec")


def test_class_show_und_caption_zeigen_eine_meldung_im_inspektor(
    tmp_path: Path,
) -> None:
    _, canvas = _designer(tmp_path)
    inspektor = Objektinspektor()
    inspektor.formular_anzeigen(canvas.formular, canvas)
    inspektor.baum.setCurrentItem(inspektor.baum.topLevelItem(0).child(0))
    tabelle = inspektor.eigenschaften_tabelle

    for name in ("class", "show", "caption"):
        tabelle.fehlertext = ""
        tabelle.item(0, 1).setText(name)
        assert tabelle.fehlertext, name
        assert tabelle.item(0, 1).text() == "e_x"
    assert canvas.formular.e_x is not None


def test_neue_komponente_bekommt_keinen_namen_der_formularklasse(
    tmp_path: Path,
) -> None:
    _, canvas = _designer(tmp_path)
    assert canvas._eindeutigen_namen_finden("caption") == "caption2"
