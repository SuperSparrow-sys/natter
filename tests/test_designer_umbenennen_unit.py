"""Umbenennen und Methoden anlegen, wenn die Unit mitspielt
(Punkte 140, 141, 147, 150 und 173).

Das Umbenennen einer Komponente zieht ihre selbst erzeugten
Ereignismethoden mit. Dabei durfte keine Methode doppelt entstehen,
ein Syntaxfehler in der Unit keinen halben Zustand hinterlassen,
kein anderer Verweis auf die alte Methode zurückbleiben und keine
Komponente eine Methode verdecken, die nach dem Öffnen des Designers
geschrieben wurde.
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest

from ide.designer.canvas import DesignerCanvas
from ide.designer.laden import formular_fuer_designer_laden
from ide.inspector.ereignisse_tabelle import passende_methoden
from pcl import Button

_KOPF = "from u_main_design import Form1Design\n\n\nclass Form1(Form1Design):\n"


def _projekt(tmp_path: Path, kinder: list[dict], methoden: str) -> DesignerCanvas:
    pfm = {
        "format": "pfm/1",
        "class": "Form1",
        "type": "Form",
        "properties": {"width": 480, "height": 360},
        "children": kinder,
    }
    pfm_pfad = tmp_path / "u_main.pfm"
    pfm_pfad.write_text(json.dumps(pfm), encoding="utf-8")
    (tmp_path / "u_main.py").write_text(_KOPF + methoden, encoding="utf-8")
    formular = formular_fuer_designer_laden(pfm_pfad)
    return DesignerCanvas(formular, pfm_pfad=pfm_pfad)


def _knopf(name: str, left: int, handler: str | None = None) -> dict:
    eintrag: dict = {"name": name, "type": "Button", "properties": {"left": left}}
    if handler is not None:
        eintrag["events"] = {"on_click": handler}
    return eintrag


def _unit(tmp_path: Path) -> str:
    return (tmp_path / "u_main.py").read_text(encoding="utf-8")


def _pfm(tmp_path: Path) -> dict:
    return json.loads((tmp_path / "u_main.pfm").read_text(encoding="utf-8"))


def _ereignisse(pfm: dict) -> dict[str, dict]:
    return {k["name"]: k.get("events", {}) for k in pfm.get("children", [])}


# ---------------------------------------------------------- Punkt 140


def test_umbenennen_auf_eine_vorhandene_methode_wird_abgelehnt(tmp_path: Path) -> None:
    canvas = _projekt(
        tmp_path,
        [_knopf("b_ja", 16, "b_ja_click"), _knopf("b_ok", 120, "b_ok_click")],
        "    def b_ja_click(self, sender):\n"
        "        self.caption = 'JA-CODE'\n\n"
        "    def b_ok_click(self, sender):\n"
        "        self.caption = 'OK-CODE'\n",
    )
    formular = canvas.formular
    canvas.loeschen(formular.b_ja)
    vorher = (tmp_path / "u_main.pfm").read_text(encoding="utf-8")

    with pytest.raises(ValueError, match="b_ja_click"):
        canvas.komponente_umbenennen(formular.b_ok, "b_ja")

    unit = _unit(tmp_path)
    assert unit.count("def b_ja_click") == 1
    assert unit.count("def b_ok_click") == 1
    assert "JA-CODE" in unit and "OK-CODE" in unit
    assert formular.b_ok.on_click.__name__ == "b_ok_click"
    assert (tmp_path / "u_main.pfm").read_text(encoding="utf-8") == vorher


# ---------------------------------------------------------- Punkt 141


_KAPUTT = "    def b_ok_click(self, sender):\n        self.caption = (\n"


def test_umbenennen_bei_syntaxfehler_aendert_nichts(tmp_path: Path) -> None:
    canvas = _projekt(
        tmp_path,
        [_knopf("b_ok", 16, "b_ok_click")],
        "    def b_ok_click(self, sender):\n        pass\n",
    )
    formular = canvas.formular
    (tmp_path / "u_main.py").write_text(_KOPF + _KAPUTT, encoding="utf-8")
    pfm_vorher = (tmp_path / "u_main.pfm").read_text(encoding="utf-8")

    with pytest.raises(ValueError, match=r"u_main.py hat in Zeile \d+ einen Syntaxfehler"):
        canvas.komponente_umbenennen(formular.b_ok, "b_weiter")

    assert canvas._attributname(formular.b_ok) == "b_ok"
    assert not hasattr(formular, "b_weiter")
    assert formular.b_ok.on_click.__name__ == "b_ok_click"
    assert (tmp_path / "u_main.pfm").read_text(encoding="utf-8") == pfm_vorher
    assert _unit(tmp_path) == _KOPF + _KAPUTT
    assert not canvas.kommandos.kann_rueckgaengig


def test_methode_anlegen_bei_syntaxfehler_meldet_und_aendert_nichts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    canvas = _projekt(tmp_path, [_knopf("b_ok", 16)], _KAPUTT)
    meldungen: list[str] = []
    monkeypatch.setattr(
        "ide.designer.canvas.QMessageBox.warning",
        lambda _eltern, _titel, text, *a: meldungen.append(text),
    )
    pfm_vorher = (tmp_path / "u_main.pfm").read_text(encoding="utf-8")

    ergebnis = canvas.ereignis_handler_erzeugen(canvas.formular.b_ok)

    assert ergebnis is None
    assert len(meldungen) == 1
    assert "u_main.py hat in Zeile 6 einen Syntaxfehler" in meldungen[0]
    assert canvas.formular.b_ok.on_click is None
    assert (tmp_path / "u_main.pfm").read_text(encoding="utf-8") == pfm_vorher
    assert _unit(tmp_path) == _KOPF + _KAPUTT
    assert not canvas.kommandos.kann_rueckgaengig


def test_rueckgaengig_bei_inzwischen_kaputter_unit_bleibt_stimmig(tmp_path: Path) -> None:
    """Bekommt die Unit nach dem Umbenennen einen Syntaxfehler, nimmt
    Strg+Z den Namen der Komponente zurück und lässt die Methode, wie
    sie ist. Der Verweis zeigt dann weiter auf den Namen, der in der
    Unit steht."""
    canvas = _projekt(
        tmp_path,
        [_knopf("b_ok", 16, "b_ok_click")],
        "    def b_ok_click(self, sender):\n        pass\n",
    )
    knopf = canvas.formular.b_ok
    canvas.komponente_umbenennen(knopf, "b_ja")
    kaputt = _unit(tmp_path) + "    def (\n"
    (tmp_path / "u_main.py").write_text(kaputt, encoding="utf-8")

    canvas.rueckgaengig()

    assert canvas._attributname(knopf) == "b_ok"
    assert _ereignisse(_pfm(tmp_path)) == {"b_ok": {"on_click": "b_ja_click"}}
    assert _unit(tmp_path) == kaputt


# ---------------------------------------------------------- Punkt 147


def test_andere_nutzer_der_methode_ziehen_mit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, qapp  # noqa: ANN001
) -> None:
    canvas = _projekt(
        tmp_path,
        [_knopf("b_ok", 16, "b_ok_click"), _knopf("b_abbrechen", 120, "b_ok_click")],
        "    def b_ok_click(self, sender):\n        self.caption = 'geklickt'\n",
    )
    formular = canvas.formular

    canvas.komponente_umbenennen(formular.b_ok, "b_ja")

    assert _ereignisse(_pfm(tmp_path)) == {
        "b_ja": {"on_click": "b_ja_click"},
        "b_abbrechen": {"on_click": "b_ja_click"},
    }
    design = (tmp_path / "u_main_design.py").read_text(encoding="utf-8")
    assert "self.b_abbrechen.on_click = self.b_ja_click" in design
    assert "b_ok_click" not in design + _unit(tmp_path)

    # Das Programm startet und der Knopf ruft die umbenannte Methode.
    monkeypatch.syspath_prepend(str(tmp_path))
    for name in ("u_main", "u_main_design"):
        sys.modules.pop(name, None)
    try:
        programm = importlib.import_module("u_main").Form1()
        programm.b_abbrechen.on_click(programm.b_abbrechen)
        assert programm.caption == "geklickt"
    finally:
        for name in ("u_main", "u_main_design"):
            sys.modules.pop(name, None)

    canvas.rueckgaengig()
    assert _ereignisse(_pfm(tmp_path)) == {
        "b_ok": {"on_click": "b_ok_click"},
        "b_abbrechen": {"on_click": "b_ok_click"},
    }
    assert "def b_ok_click" in _unit(tmp_path)
    canvas.wiederholen()
    assert _ereignisse(_pfm(tmp_path))["b_abbrechen"] == {"on_click": "b_ja_click"}


def test_menueeintraege_ziehen_mit(tmp_path: Path) -> None:
    canvas = _projekt(
        tmp_path,
        [
            _knopf("b_ok", 16, "b_ok_click"),
            {
                "name": "mm_haupt",
                "type": "MainMenu",
                "properties": {
                    "entries": [{"caption": "&Weiter", "on_click": "b_ok_click"}]
                },
            },
        ],
        "    def b_ok_click(self, sender):\n        pass\n",
    )

    canvas.komponente_umbenennen(canvas.formular.b_ok, "b_ja")

    menue = next(k for k in _pfm(tmp_path)["children"] if k["name"] == "mm_haupt")
    assert menue["properties"]["entries"][0]["on_click"] == "b_ja_click"
    canvas.rueckgaengig()
    menue = next(k for k in _pfm(tmp_path)["children"] if k["name"] == "mm_haupt")
    assert menue["properties"]["entries"][0]["on_click"] == "b_ok_click"


# ---------------------------------------------------------- Punkt 150


def test_die_auswahl_kennt_nur_methoden_der_unit(tmp_path: Path) -> None:
    canvas = _projekt(
        tmp_path,
        [_knopf("b_ok", 16, "b_ok_click"), _knopf("b_weiter", 120)],
        "    def b_ok_click(self, sender):\n        pass\n\n"
        "    def rechnen(self, sender):\n        pass\n",
    )
    formular = canvas.formular
    assert "b_ok_click" in passende_methoden(formular, "on_click")

    canvas.komponente_umbenennen(formular.b_ok, "b_ja")
    auswahl = passende_methoden(formular, "on_click")
    assert "b_ja_click" in auswahl
    assert "b_ok_click" not in auswahl

    # Von Hand aus der Unit gelöscht.
    unit = _unit(tmp_path).replace("    def rechnen(self, sender):\n        pass\n", "")
    (tmp_path / "u_main.py").write_text(unit, encoding="utf-8")
    assert "rechnen" not in passende_methoden(formular, "on_click")


def test_eine_fehlende_methode_laesst_das_formular_trotzdem_oeffnen(tmp_path: Path) -> None:
    """Punkt 115 gilt weiter: verweist die `.pfm` auf eine Methode, die
    es in der Unit nicht gibt, öffnet sich das Formular."""
    canvas = _projekt(tmp_path, [_knopf("b_ok", 16, "b_fehlt_click")], "    pass\n")

    assert canvas.formular.b_ok.on_click.__name__ == "b_fehlt_click"
    assert "b_fehlt_click" not in passende_methoden(canvas.formular, "on_click")


# ---------------------------------------------------------- Punkt 173


def test_umbenennen_in_eine_spaeter_geschriebene_methode_wird_abgelehnt(
    tmp_path: Path,
) -> None:
    canvas = _projekt(tmp_path, [_knopf("b_ok", 16)], "    pass\n")
    formular = canvas.formular
    (tmp_path / "u_main.py").write_text(
        _KOPF + "    def berechnen(self):\n        return 42\n", encoding="utf-8"
    )

    with pytest.raises(ValueError, match="berechnen"):
        canvas.komponente_umbenennen(formular.b_ok, "berechnen")

    assert canvas._attributname(formular.b_ok) == "b_ok"
    assert not canvas.kommandos.kann_rueckgaengig


def test_neue_komponente_ohne_unit_bleibt_unberuehrt() -> None:
    """Ein Formular ohne Unit (etwa in Tests) prüft nur seine Klasse."""
    from pcl import Form

    class _Leer(Form):
        pass

    canvas = DesignerCanvas(_Leer())
    knopf = canvas.komponente_platzieren(Button, 0, 0)
    canvas.komponente_umbenennen(knopf, "berechnen")
    assert canvas._attributname(knopf) == "berechnen"
