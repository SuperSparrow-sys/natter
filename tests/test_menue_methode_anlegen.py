"""Menü-Editor legt die Methode an, Tippfehler werden gemeldet
(offener Punkt 75).

„Beim Anklicken“ war ein freies Textfeld: es entstand keine Methode,
und ein falscher Name blieb ohne Meldung, weil `_handler_suchen` ihn
still überging.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from ide.designer.canvas import DesignerCanvas
from ide.designer.laden import formular_fuer_designer_laden
from ide.inspector.menue_editor import (
    MenueEditor,
    menue_methode_anlegen,
    methodenname_vorschlagen,
)
from pcl import Form, MainMenu, PopupMenu
from pcl.errors import NatterUnbekannteEigenschaftError
from pcl.fehleranzeige import fehlertext

_PFM = {
    "format": "pfm/1",
    "class": "Form1",
    "type": "Form",
    "properties": {},
    "children": [
        {
            "name": "mm_haupt",
            "type": "MainMenu",
            "properties": {
                "entries": [
                    {
                        "name": "mi_datei",
                        "caption": "&Datei",
                        "children": [
                            {
                                "name": "mi_beenden",
                                "caption": "B&eenden",
                                "on_click": "mi_beenden_click",
                            }
                        ],
                    }
                ]
            },
        }
    ],
}

_UNIT = '''"""Unit."""

from u_main_design import Form1Design


class Form1(Form1Design):
    pass
'''


def _designer(tmp_path: Path) -> DesignerCanvas:
    pfm_pfad = tmp_path / "u_main.pfm"
    pfm_pfad.write_text(json.dumps(_PFM), encoding="utf-8")
    (tmp_path / "u_main.py").write_text(_UNIT, encoding="utf-8")
    return DesignerCanvas(formular_fuer_designer_laden(pfm_pfad), pfm_pfad=pfm_pfad)


def _methoden(unit: Path) -> dict[str, list[str]]:
    baum = ast.parse(unit.read_text(encoding="utf-8"))
    return {
        k.name: [p.arg for p in k.args.args]
        for k in ast.walk(baum)
        if isinstance(k, ast.FunctionDef)
    }


# ------------------------------------------------------ Methode anlegen


def test_der_designer_oeffnet_sich_trotz_fehlender_methode(tmp_path: Path) -> None:
    """Im Designer ist eine noch nicht geschriebene Methode der
    Normalfall und darf das Öffnen nicht verhindern."""
    canvas = _designer(tmp_path)

    assert canvas.formular.mm_haupt.entries[0]["children"][0]["on_click"] == (
        "mi_beenden_click"
    )


def test_menue_methode_anlegen_schreibt_die_methode(tmp_path: Path) -> None:
    canvas = _designer(tmp_path)
    gemeldet: list[tuple] = []
    canvas.methode_beobachten(lambda *angaben: gemeldet.append(angaben))

    menue_methode_anlegen(canvas, "mi_beenden_click")
    menue_methode_anlegen(canvas, "mi_beenden_click")

    assert _methoden(tmp_path / "u_main.py") == {
        "mi_beenden_click": ["self", "sender"]
    }
    # Der Editor springt beide Male hin, geschrieben wird einmal.
    assert [angabe[2] for angabe in gemeldet] == ["mi_beenden_click"] * 2


def test_der_knopf_im_editor_schlaegt_einen_namen_vor(qtbot) -> None:
    angelegt: list[str] = []
    editor = MenueEditor(
        [{"name": "mi_speichern", "caption": "&Speichern"}],
        methode_anlegen=angelegt.append,
    )
    qtbot.addWidget(editor)
    editor.baum.setCurrentItem(editor.baum.topLevelItem(0))

    editor.anlegen_knopf.click()

    assert angelegt == ["mi_speichern_click"]
    assert editor.feld_on_click.text() == "mi_speichern_click"
    editor.anwenden()
    assert editor.eintraege()[0]["on_click"] == "mi_speichern_click"


def test_ein_eingetragener_name_bleibt(qtbot) -> None:
    angelegt: list[str] = []
    editor = MenueEditor([{"caption": "&Neu"}], methode_anlegen=angelegt.append)
    qtbot.addWidget(editor)
    editor.baum.setCurrentItem(editor.baum.topLevelItem(0))
    editor.feld_on_click.setText("datei_neu")

    editor.anlegen_knopf.click()

    assert angelegt == ["datei_neu"]


def test_ohne_designer_ist_der_knopf_grau(qtbot) -> None:
    editor = MenueEditor([{"caption": "&Neu"}])
    qtbot.addWidget(editor)

    assert not editor.anlegen_knopf.isEnabled()


@pytest.mark.parametrize(
    ("eintrag", "name"),
    [
        ({"name": "mi_ende", "caption": "B&eenden"}, "mi_ende_click"),
        ({"caption": "B&eenden"}, "mi_beenden_click"),
        ({"caption": "Über Natter …"}, "mi_ueber_natter_click"),
        ({"caption": ""}, "mi_eintrag_click"),
    ],
)
def test_namensvorschlag(eintrag, name) -> None:
    assert methodenname_vorschlagen(eintrag) == name


def test_der_designer_reicht_das_anlegen_an_den_editor(
    tmp_path: Path, monkeypatch
) -> None:
    """Doppelklick und F2 auf das Menüsymbol öffnen den Editor über
    den Designer. Auch dort muss der Knopf funktionieren."""
    canvas = _designer(tmp_path)
    erhalten: dict = {}

    class _Editor:
        uebernommen = False

        def __init__(self, eintraege, eltern=None, methode_anlegen=None):
            erhalten["anlegen"] = methode_anlegen

        def exec(self) -> int:
            erhalten["anlegen"]("mi_beenden_click")
            return 0

    monkeypatch.setattr("ide.inspector.menue_editor.MenueEditor", _Editor)

    canvas.menue_bearbeiten(canvas.formular.mm_haupt)

    assert "mi_beenden_click" in _methoden(tmp_path / "u_main.py")


# ------------------------------------------------ Meldung beim Start


class _MitMenue(Form):
    def create_components(self) -> None:
        self.mm_haupt = MainMenu(self)
        self.mm_haupt.entries = [
            {
                "caption": "&Datei",
                "children": [{"caption": "B&eenden", "on_click": "beenden"}],
            }
        ]

    def beeden(self, sender) -> None:  # Tippfehler
        pass


def test_ein_tippfehler_wird_beim_start_deutsch_gemeldet() -> None:
    with pytest.raises(NatterUnbekannteEigenschaftError) as fehler:
        _MitMenue()

    meldung = fehlertext(type(fehler.value), fehler.value, fehler.tb)
    assert "„Beenden“" in meldung
    assert "'beenden'" in meldung
    assert "_MitMenue" in meldung


def test_auch_im_klappmenue() -> None:
    class _Formular(Form):
        def create_components(self) -> None:
            self.pm_liste = PopupMenu(self)
            self.pm_liste.entries = [{"caption": "&Löschen", "on_click": "loeschn"}]

    with pytest.raises(NatterUnbekannteEigenschaftError, match="„Löschen“"):
        _Formular()


def test_eine_vorhandene_methode_geht_durch() -> None:
    class _Formular(_MitMenue):
        def beenden(self, sender) -> None:
            pass

    formular = _Formular()

    assert formular.mm_haupt.entries[0]["children"][0]["on_click"] == "beenden"


def test_auch_aktualisieren_prueft() -> None:
    class _Formular(_MitMenue):
        def beenden(self, sender) -> None:
            pass

    formular = _Formular()
    formular.mm_haupt.eintrag("&Datei")  # kein Bezeichner, nur Text
    formular.mm_haupt._eintraege[0]["children"][0]["on_click"] = "weg"

    with pytest.raises(NatterUnbekannteEigenschaftError):
        formular.mm_haupt.aktualisieren()
