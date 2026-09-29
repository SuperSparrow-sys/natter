"""Eine platzierte Komponente in einen Behälter ziehen und wieder
heraus (Punkt 72).

Beim Platzieren landete eine Komponente im Behälter unter der Maus,
beim späteren Verschieben änderten sich nur `left` und `top`: ein Knopf
blieb Kind des Formulars, auch wenn er mitten auf einem Panel lag.
"""

from __future__ import annotations

import json
from pathlib import Path

from ide.designer.canvas import DesignerCanvas
from ide.designer.pfm_schreiben import pfm_aus_formular
from pcl import Button, Form, GroupBox, Panel


class _Formular(Form):
    def create_components(self) -> None:
        self.p_rand = Panel(self)
        self.p_rand.left, self.p_rand.top = 200, 40
        self.p_rand.width, self.p_rand.height = 240, 200
        self.gb_innen = GroupBox(self.p_rand)
        self.gb_innen.left, self.gb_innen.top = 16, 16
        self.gb_innen.width, self.gb_innen.height = 120, 100
        self.b_ok = Button(self)
        self.b_ok.left, self.b_ok.top = 16, 16


def _canvas(qtbot, tmp_path: Path) -> tuple[_Formular, DesignerCanvas, Path]:  # noqa: ANN001
    formular = _Formular()
    qtbot.addWidget(formular._qwidget)
    formular._qwidget.resize(480, 360)
    formular._qwidget.show()
    pfm = tmp_path / "u_main.pfm"
    pfm.write_text(json.dumps(pfm_aus_formular(formular)), encoding="utf-8")
    return formular, DesignerCanvas(formular, pfm_pfad=pfm), pfm


def _ziehen(canvas: DesignerCanvas, komponente, left: int, top: int) -> None:  # noqa: ANN001
    """Wie ein Ziehen mit der Maus: Startwerte merken, verschieben,
    loslassen."""
    canvas._ziehen_komponente = komponente
    canvas._ziehen_start_werte = {"left": komponente.left, "top": komponente.top}
    komponente.left, komponente.top = left, top
    canvas._ziehen_beenden()
    canvas.jetzt_schreiben()


def _kinder(eintrag: dict) -> list[str]:
    return [k["name"] for k in eintrag.get("children", [])]


def test_in_ein_panel_und_wieder_heraus(qtbot, tmp_path: Path) -> None:  # noqa: ANN001
    formular, canvas, pfm = _canvas(qtbot, tmp_path)

    # Mitte des Knopfes landet auf dem Panel, außerhalb der GroupBox.
    _ziehen(canvas, formular.b_ok, 360, 200)

    assert formular.b_ok.eltern is formular.p_rand
    assert (formular.b_ok.left, formular.b_ok.top) == (160, 160)
    daten = json.loads(pfm.read_text(encoding="utf-8"))
    panel = next(k for k in daten["children"] if k["name"] == "p_rand")
    assert "b_ok" in _kinder(panel)
    assert "b_ok" not in _kinder(daten)

    # Innerhalb des Panels in die GroupBox: der innerste Behälter zählt.
    _ziehen(canvas, formular.b_ok, 30, 40)
    assert formular.b_ok.eltern is formular.gb_innen

    # Heraus aufs Formular: links neben das Panel, in GroupBox-
    # Koordinaten also weit ins Negative.
    _ziehen(canvas, formular.b_ok, -250, 150)
    assert formular.b_ok.eltern is formular


def test_rueckgaengig_haengt_zurueck(qtbot, tmp_path: Path) -> None:  # noqa: ANN001
    formular, canvas, _ = _canvas(qtbot, tmp_path)

    _ziehen(canvas, formular.b_ok, 360, 200)
    canvas.rueckgaengig()

    assert formular.b_ok.eltern is formular
    assert (formular.b_ok.left, formular.b_ok.top) == (16, 16)
    canvas.wiederholen()
    assert formular.b_ok.eltern is formular.p_rand


def test_ein_behaelter_faellt_nicht_in_sich_selbst(qtbot, tmp_path: Path) -> None:  # noqa: ANN001
    formular, canvas, _ = _canvas(qtbot, tmp_path)

    _ziehen(canvas, formular.p_rand, 210, 50)

    assert formular.p_rand.eltern is formular
    assert formular.gb_innen.eltern is formular.p_rand


def test_verschieben_im_selben_behaelter_bleibt_ein_verschieben(
    qtbot, tmp_path: Path  # noqa: ANN001
) -> None:
    formular, canvas, _ = _canvas(qtbot, tmp_path)

    _ziehen(canvas, formular.b_ok, 24, 64)

    assert formular.b_ok.eltern is formular
    assert (formular.b_ok.left, formular.b_ok.top) == (24, 64)
