"""`anchors`: Komponenten wachsen mit dem Fenster (Punkt 108)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ide.codegen.design import design_code_erzeugen
from ide.designer.laden import formular_fuer_designer_laden
from ide.designer.pfm_schreiben import pfm_aus_formular
from ide.inspector.eigenschaften_tabelle import EigenschaftenTabelle
from pcl import Button, Form, MainMenu, Memo, Panel
from pcl.errors import NatterPropertyError

_OFFEN: list[Form] = []


class _Notiz(Form):
    def create_components(self) -> None:
        self.width = 400
        self.height = 300
        self.m_text = Memo(self)
        self.m_text.left = 10
        self.m_text.top = 10
        self.m_text.width = 380
        self.m_text.height = 240
        self.m_text.anchors.right = True
        self.m_text.anchors.bottom = True
        self.b_ok = Button(self)
        self.b_ok.left = 315
        self.b_ok.top = 265
        self.b_ok.anchors.left = False
        self.b_ok.anchors.top = False
        self.b_ok.anchors.right = True
        self.b_ok.anchors.bottom = True
        self.b_fest = Button(self)
        self.b_fest.left = 10
        self.b_fest.top = 265


@pytest.fixture
def notiz(qtbot) -> _Notiz:
    formular = _Notiz()
    _OFFEN.append(formular)
    formular.show()
    qtbot.waitExposed(formular._qwidget)
    return formular


def test_ein_memo_mit_rechts_und_unten_waechst_mit(notiz, qtbot) -> None:
    notiz._qwidget.resize(600, 450)
    qtbot.waitUntil(lambda: notiz.m_text.width == 580, timeout=2000)

    assert notiz.m_text.height == 390
    assert notiz.m_text._qwidget.width() == 580
    assert notiz.m_text._qwidget.height() == 390
    assert (notiz.m_text.left, notiz.m_text.top) == (10, 10)


def test_ein_knopf_nur_rechts_unten_rueckt_mit(notiz, qtbot) -> None:
    notiz._qwidget.resize(500, 350)
    qtbot.waitUntil(lambda: notiz.b_ok.left == 415, timeout=2000)

    assert notiz.b_ok.top == 315
    assert (notiz.b_ok.width, notiz.b_ok.height) == (75, 25)


def test_ohne_anker_bleibt_alles_stehen(notiz, qtbot) -> None:
    notiz._qwidget.resize(600, 450)
    qtbot.waitUntil(lambda: notiz.m_text.width == 580, timeout=2000)
    assert (notiz.b_fest.left, notiz.b_fest.top) == (10, 265)


def test_verkleinern_schrumpft_bis_null(notiz, qtbot) -> None:
    notiz._qwidget.resize(200, 100)
    qtbot.waitUntil(lambda: notiz.m_text.width == 180, timeout=2000)
    assert notiz.m_text.height == 40
    notiz._qwidget.resize(400, 300)
    qtbot.waitUntil(lambda: notiz.m_text.width == 380, timeout=2000)
    assert notiz.m_text.height == 240


def test_width_des_formulars_im_code_wirkt_ebenso(notiz, qtbot) -> None:
    notiz.width = 450
    qtbot.waitUntil(lambda: notiz.m_text.width == 430, timeout=2000)


def test_in_einem_behaelter_zaehlt_dessen_rand(qtbot) -> None:
    class MitPanel(Form):
        def create_components(self) -> None:
            self.p_flaeche = Panel(self)
            self.p_flaeche.width = 200
            self.p_flaeche.height = 100
            self.p_flaeche.anchors.right = True
            self.m_innen = Memo(self.p_flaeche)
            self.m_innen.left = 10
            self.m_innen.width = 180
            self.m_innen.anchors.right = True

    formular = MitPanel()
    _OFFEN.append(formular)
    formular.show()
    qtbot.waitExposed(formular._qwidget)
    formular._qwidget.resize(formular._qwidget.width() + 50, formular._qwidget.height())
    qtbot.waitUntil(lambda: formular.m_innen.width == 230, timeout=2000)
    assert formular.p_flaeche.width == 250


def test_mit_menueleiste_zaehlt_der_arbeitsbereich(qtbot) -> None:
    class MitMenue(Form):
        def create_components(self) -> None:
            self.mm_haupt = MainMenu(self)
            self.mm_haupt.entries = [{"caption": "&Datei"}]
            self.m_text = Memo(self)
            self.m_text.width = 480
            self.m_text.height = 360
            self.m_text.anchors.right = True
            self.m_text.anchors.bottom = True

    formular = MitMenue()
    _OFFEN.append(formular)
    formular.show()
    qtbot.waitExposed(formular._qwidget)
    leiste = formular._leistenhoehe()
    assert formular.m_text._qwidget.y() == leiste
    assert formular.m_text.height == 360

    formular._qwidget.resize(480, 360 + leiste + 40)
    qtbot.waitUntil(lambda: formular.m_text.height == 400, timeout=2000)
    assert formular.m_text._qwidget.y() == leiste


def test_anchors_nimmt_nur_wahrheitswerte() -> None:
    memo = Memo(Form())
    with pytest.raises(NatterPropertyError):
        memo.anchors.right = "ja"


def test_im_objektinspektor_vier_haekchen(qtbot) -> None:
    memo = Memo(Form())
    tabelle = EigenschaftenTabelle()
    qtbot.addWidget(tabelle)
    tabelle.komponente_anzeigen(memo)
    for seite in ("left", "top", "right", "bottom"):
        name = f"anchors_{seite}"
        assert tabelle._typ_von(name) is bool
        assert tabelle.kategorie_von(name) == "Layout"


def test_anchors_gehen_durch_pfm_und_erzeugten_code() -> None:
    formular = _Notiz()
    _OFFEN.append(formular)
    pfm = pfm_aus_formular(formular)
    memo = next(k for k in pfm["children"] if k["name"] == "m_text")
    assert memo["properties"]["anchors_right"] is True
    assert "anchors_left" not in memo["properties"]

    code = design_code_erzeugen(json.loads(json.dumps(pfm)), "u_test.pfm")
    assert "self.m_text.anchors.right = True" in code
    assert "self.b_ok.anchors.left = False" in code


def test_im_designer_bleibt_alles_wo_es_liegt(tmp_path: Path, qtbot) -> None:
    pfm = {
        "format": "pfm/1",
        "class": "Form1",
        "type": "Form",
        "properties": {},
        "children": [
            {
                "name": "m_text",
                "type": "Memo",
                "properties": {"width": 100, "anchors_right": True},
            }
        ],
    }
    pfad = tmp_path / "u_main.pfm"
    pfad.write_text(json.dumps(pfm), encoding="utf-8")
    (tmp_path / "u_main.py").write_text(
        "from u_main_design import Form1Design\n\n\nclass Form1(Form1Design):\n    pass\n",
        encoding="utf-8",
    )
    formular = formular_fuer_designer_laden(pfad)
    _OFFEN.append(formular)
    formular._qwidget.resize(900, 700)
    formular._qwidget.show()
    qtbot.waitExposed(formular._qwidget)
    assert formular.m_text.width == 100
    formular._qwidget.hide()
