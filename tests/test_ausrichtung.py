"""`alignment` für Label, Edit und Panel (Punkt 94)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from ide.designer.laden import formular_fuer_designer_laden
from pcl import Edit, Form, Label, Panel
from pcl.errors import NatterPropertyError

_WAAGERECHT = Qt.AlignmentFlag.AlignHorizontal_Mask


@pytest.mark.parametrize("klasse", [Label, Edit], ids=lambda k: k.__name__)
@pytest.mark.parametrize(
    ("wert", "flagge"),
    [
        ("left", Qt.AlignmentFlag.AlignLeft),
        ("center", Qt.AlignmentFlag.AlignHCenter),
        ("right", Qt.AlignmentFlag.AlignRight),
    ],
)
def test_alignment_richtet_das_widget_aus(klasse, wert, flagge) -> None:
    komponente = klasse(Form())
    komponente.alignment = wert
    assert komponente._qwidget.alignment() & _WAAGERECHT == flagge
    assert komponente._qwidget.alignment() & Qt.AlignmentFlag.AlignVCenter


def test_standardwerte() -> None:
    formular = Form()
    assert Label(formular).alignment == "left"
    assert Edit(formular).alignment == "left"
    assert Panel(formular).alignment == "center"


def test_ein_unbekannter_wert_wird_abgelehnt() -> None:
    with pytest.raises(NatterPropertyError, match="right"):
        Label(Form()).alignment = "rechts"


def _dunkle_spalten(panel: Panel) -> list[int]:
    bild = panel._qwidget.grab().toImage()
    spalten = []
    for x in range(8, bild.width() - 8):
        for y in range(4, bild.height() - 4):
            if QColor(bild.pixel(x, y)).lightness() < 100:
                spalten.append(x)
                break
    return spalten


def test_panel_zeichnet_rechtsbuendig_rechts() -> None:
    formular = Form()
    formular.theme = "light"
    panel = Panel(formular)
    panel.width = 300
    panel.height = 40
    panel.caption = "12"

    panel.alignment = "right"
    rechts = _dunkle_spalten(panel)
    panel.alignment = "left"
    links = _dunkle_spalten(panel)

    assert rechts and links
    assert min(rechts) > 150
    assert max(links) < 150


def test_der_designer_zeigt_die_ausrichtung(tmp_path: Path) -> None:
    pfm = {
        "format": "pfm/1",
        "class": "Form1",
        "type": "Form",
        "properties": {},
        "children": [
            {"name": "l_anzeige", "type": "Label", "properties": {"alignment": "right"}},
            {"name": "e_zahl", "type": "Edit", "properties": {"alignment": "center"}},
        ],
    }
    pfad = tmp_path / "u_main.pfm"
    pfad.write_text(json.dumps(pfm), encoding="utf-8")
    (tmp_path / "u_main.py").write_text(
        "from u_main_design import Form1Design\n\n\nclass Form1(Form1Design):\n    pass\n",
        encoding="utf-8",
    )

    formular = formular_fuer_designer_laden(pfad)

    anzeige = formular.l_anzeige._qwidget.alignment() & _WAAGERECHT
    zahl = formular.e_zahl._qwidget.alignment() & _WAAGERECHT
    assert anzeige == Qt.AlignmentFlag.AlignRight
    assert zahl == Qt.AlignmentFlag.AlignHCenter
