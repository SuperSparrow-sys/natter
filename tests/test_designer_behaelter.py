"""Behälter im Designer: ein `Panel` oder eine `GroupBox` nimmt auf,
was man darüber ablegt.

Das stand seit M1 als Punkt 1 unter „Offene Punkte" in
`docs/komponenten.md`. Im Code ging es immer schon –
`RadioButton(self.g_zahlung)` hängt den Knopf an die GroupBox, das
erledigt `Control.__init__` von selbst. Der Designer legte trotzdem
jede abgelegte Komponente ans Formular; ein Panel war dort eine
Fläche, auf der nichts liegen konnte.

Vier Stellen mussten dafür zusammenspielen, und alle vier werden hier
geprüft: das Ablegen (Eltern und Koordinaten), der Komponentenbaum,
das Zurückschreiben in die `.pfm` und der erzeugte Quelltext.

Die Namen bleiben flach. Ein Knopf im Panel heißt weiter
`self.b_ok`, wie in Lazarus; verschachtelt ist nur, woran er hängt.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ide.codegen.design import design_code_erzeugen
from ide.designer.canvas import DesignerCanvas
from ide.designer.laden import formular_fuer_designer_laden
from ide.inspector.komponentenbaum import Komponentenbaum, kind_komponenten
from pcl import Button, Form, GroupBox, Label, Panel

LEER = {
    "format": "pfm/1",
    "class": "Form1",
    "type": "Form",
    "properties": {"width": 480, "height": 360},
    "children": [],
}

UNIT = "from u_main_design import Form1Design\n\n\nclass Form1(Form1Design):\n    pass\n"


@pytest.fixture
def canvas(tmp_path: Path) -> DesignerCanvas:
    (tmp_path / "u_main.pfm").write_text(json.dumps(LEER), encoding="utf-8")
    (tmp_path / "u_main.py").write_text(UNIT, encoding="utf-8")
    formular = formular_fuer_designer_laden(tmp_path / "u_main.pfm")
    leinwand = DesignerCanvas(formular, pfm_pfad=tmp_path / "u_main.pfm")
    leinwand._pfad = tmp_path  # nur für den Zugriff in den Tests
    return leinwand


# ------------------------------------------------------------- Ablegen


def test_was_ueber_einem_panel_landet_gehoert_hinein(canvas: DesignerCanvas) -> None:
    panel = canvas.komponente_platzieren(Panel, 40, 40)

    knopf = canvas.komponente_platzieren(Button, 60, 70)

    assert knopf.eltern is panel


def test_die_koordinaten_zaehlen_ab_dem_behaelter(canvas: DesignerCanvas) -> None:
    """Sonst säße der Knopf im Panel an einer ganz anderen Stelle, als
    man ihn abgelegt hat - `left`/`top` zählen bei einem Kind ab der
    linken oberen Ecke seiner Eltern."""
    canvas.komponente_platzieren(Panel, 40, 40)

    knopf = canvas.komponente_platzieren(Button, 60, 70)

    # Eingerastet am 8px-Raster: aus (20, 30) wird (16, 32).
    assert (knopf.left, knopf.top) == (16, 32)


def test_neben_dem_panel_bleibt_alles_beim_formular(canvas: DesignerCanvas) -> None:
    canvas.komponente_platzieren(Panel, 40, 40)

    schild = canvas.komponente_platzieren(Label, 300, 300)

    assert schild.eltern is canvas.formular
    assert (schild.left, schild.top) == (304, 304)  # am Raster


def test_auch_eine_groupbox_nimmt_auf(canvas: DesignerCanvas) -> None:
    gruppe = canvas.komponente_platzieren(GroupBox, 30, 30)

    knopf = canvas.komponente_platzieren(Button, 50, 60)

    assert knopf.eltern is gruppe


def test_der_innerste_behaelter_gewinnt(canvas: DesignerCanvas) -> None:
    """Ein Panel in einer GroupBox nimmt die Komponente auf, nicht die
    GroupBox darum."""
    canvas.komponente_platzieren(GroupBox, 20, 20)
    panel = canvas.komponente_platzieren(Panel, 10, 20)  # in die GroupBox

    knopf = canvas.komponente_platzieren(Button, 60, 70)

    assert knopf.eltern is panel


def test_ein_knopf_nimmt_nichts_auf(canvas: DesignerCanvas) -> None:
    """Nur `Panel` und `GroupBox` sind Behälter - sonst verschwände eine
    Komponente, die zufällig über einem Knopf abgelegt wird."""
    canvas.komponente_platzieren(Button, 40, 40)

    zweiter = canvas.komponente_platzieren(Button, 50, 50)

    assert zweiter.eltern is canvas.formular


# ------------------------------------------------------------- Der Baum


def test_der_komponentenbaum_zeigt_die_verschachtelung(canvas: DesignerCanvas) -> None:
    panel = canvas.komponente_platzieren(Panel, 40, 40)
    knopf = canvas.komponente_platzieren(Button, 60, 70)
    canvas.komponente_platzieren(Label, 300, 300)

    baum = Komponentenbaum()
    baum.formular_anzeigen(canvas.formular)

    wurzel = baum.topLevelItem(0)
    oberste = [wurzel.child(i).text(0).split(":")[0] for i in range(wurzel.childCount())]
    assert oberste == ["panel", "label"]
    panel_zeile = wurzel.child(0)
    assert panel_zeile.childCount() == 1
    assert panel_zeile.child(0).text(0).startswith("button")
    assert [name for name, _ in kind_komponenten(panel)] == ["button"]
    assert knopf.eltern is panel


def test_die_namen_bleiben_flach(canvas: DesignerCanvas) -> None:
    """Ein Knopf im Panel heißt weiter `self.button` - wie in Lazarus.
    Verschachtelt ist nur, woran er hängt."""
    canvas.komponente_platzieren(Panel, 40, 40)
    knopf = canvas.komponente_platzieren(Button, 60, 70)

    assert canvas.formular.button is knopf


# ------------------------------------------------------------- Die .pfm


def test_die_pfm_traegt_das_kind_im_behaelter(canvas: DesignerCanvas) -> None:
    canvas.komponente_platzieren(Panel, 40, 40)
    canvas.komponente_platzieren(Button, 60, 70)

    daten = json.loads((canvas._pfad / "u_main.pfm").read_text(encoding="utf-8"))

    assert len(daten["children"]) == 1
    panel = daten["children"][0]
    assert panel["type"] == "Panel"
    assert [kind["name"] for kind in panel["children"]] == ["button"]


# ------------------------------------------------------ Erzeugter Code


def test_der_erzeugte_code_haengt_das_kind_an_den_behaelter() -> None:
    pfm = {
        **LEER,
        "children": [
            {
                "name": "p_feld",
                "type": "Panel",
                "properties": {"left": 10, "top": 10},
                "children": [
                    {
                        "name": "b_ok",
                        "type": "Button",
                        "properties": {"left": 20, "top": 30},
                    }
                ],
            }
        ],
    }

    code = design_code_erzeugen(pfm, "u_main.pfm")

    assert "self.p_feld = Panel(self)" in code
    assert "self.b_ok = Button(self.p_feld)" in code
    # Der Behälter muss vor seinem Kind stehen: `Button(self.p_feld)`
    # setzt voraus, dass `self.p_feld` schon existiert.
    assert code.index("self.p_feld = Panel") < code.index("self.b_ok = Button")
    # Und beide brauchen ihre Typannotation und ihren Import.
    assert "from pcl import Button, Form, Panel" in code
    assert "    b_ok: Button" in code


def test_der_code_laeuft_auch_wirklich(tmp_path: Path) -> None:
    """Die eigentliche Probe: aus der verschachtelten `.pfm` ein
    Formular bauen, wie es der Designer beim Öffnen tut."""
    pfm = {
        **LEER,
        "children": [
            {
                "name": "p_feld",
                "type": "Panel",
                "properties": {"left": 10, "top": 10, "width": 200, "height": 120},
                "children": [
                    {
                        "name": "b_ok",
                        "type": "Button",
                        "properties": {"left": 20, "top": 30, "caption": "OK"},
                    }
                ],
            }
        ],
    }
    (tmp_path / "u_main.pfm").write_text(json.dumps(pfm), encoding="utf-8")

    formular = formular_fuer_designer_laden(tmp_path / "u_main.pfm")

    assert isinstance(formular.p_feld, Panel)
    assert formular.b_ok.eltern is formular.p_feld
    assert formular.b_ok.caption == "OK"
    # Qt muss es genauso sehen, sonst läge der Knopf im Bild woanders.
    assert formular.b_ok._qwidget.parentWidget() is formular.p_feld._qwidget


# ------------------------------------------------------------- Rückgängig


def test_rueckgaengig_holt_das_kind_in_sein_panel_zurueck(
    canvas: DesignerCanvas,
) -> None:
    """Und nicht aufs Formular: dort läge es an einer Stelle, die sich
    aus Panel-Koordinaten ergibt."""
    panel = canvas.komponente_platzieren(Panel, 40, 40)
    knopf = canvas.komponente_platzieren(Button, 60, 70)

    canvas.loeschen(knopf)
    canvas.rueckgaengig()

    assert knopf.eltern is panel
    assert knopf._qwidget.parentWidget() is panel._qwidget


def test_ein_formular_ohne_behaelter_verhaelt_sich_wie_bisher() -> None:
    """Die Verschachtelung darf nichts am Normalfall verschoben
    haben."""

    class Formular(Form):
        def create_components(self) -> None:
            self.b_ein = Button(self)
            self.l_text = Label(self)

    formular = Formular()

    assert [name for name, _ in kind_komponenten(formular)] == ["b_ein", "l_text"]
    assert formular.b_ein.eltern is formular
