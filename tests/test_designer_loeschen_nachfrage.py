"""Löschen einer Komponente, die die Unit noch benutzt (Punkt 294).

Bis dahin verschwand die Komponente ohne Nachfrage, und das Programm
brach erst beim Lauf ab. Die Formulare liegen in `tmp_path`, weil der
Designer bei jeder Änderung in die `.pfm` zurückschreibt.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ide.designer.canvas import DesignerCanvas
from ide.designer.laden import formular_fuer_designer_laden

_UNIT = (
    "from u_main_design import Form1Design\n"
    "\n"
    "\n"
    "class Form1(Form1Design):\n"
    "    def b_ok_click(self, sender):\n"
    "        self.label.caption = 'x'\n"
)


def _canvas(tmp_path: Path) -> DesignerCanvas:
    pfm = {
        "format": "pfm/1",
        "class": "Form1",
        "type": "Form",
        "properties": {"width": 400, "height": 300},
        "children": [
            {"name": "label", "type": "Label", "properties": {"left": 8}},
            {"name": "b_ok", "type": "Button", "properties": {"left": 96}},
        ],
    }
    pfm_pfad = tmp_path / "u_main.pfm"
    pfm_pfad.write_text(json.dumps(pfm), encoding="utf-8")
    (tmp_path / "u_main.py").write_text(_UNIT, encoding="utf-8")
    return DesignerCanvas(
        formular_fuer_designer_laden(pfm_pfad), pfm_pfad=pfm_pfad
    )


@pytest.mark.parametrize("antwort", [False, True])
def test_loeschen_fragt_bei_verwendung_in_der_unit(
    tmp_path: Path, monkeypatch, antwort: bool
) -> None:
    canvas = _canvas(tmp_path)
    fragen: list[tuple[str, int]] = []

    def fragen_merken(self, name: str, zeile: int) -> bool:
        fragen.append((name, zeile))
        return antwort

    monkeypatch.setattr(
        DesignerCanvas, "_loeschen_trotzdem_fragen", fragen_merken
    )

    canvas.loeschen(canvas.formular.label)

    assert fragen == [("label", 6)]
    assert hasattr(canvas.formular, "label") is not antwort


def test_loeschen_ohne_verwendung_fragt_nicht(
    tmp_path: Path, monkeypatch
) -> None:
    canvas = _canvas(tmp_path)
    fragen: list[str] = []
    monkeypatch.setattr(
        DesignerCanvas,
        "_loeschen_trotzdem_fragen",
        lambda self, name, zeile: fragen.append(name) or False,
    )

    canvas.loeschen(canvas.formular.b_ok)

    assert fragen == []
    assert not hasattr(canvas.formular, "b_ok")
