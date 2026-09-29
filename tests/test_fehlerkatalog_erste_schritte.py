"""Laufzeitmeldungen für die Fehler, die im ersten Jahr am häufigsten
vorkommen (Punkte 289, 290, 293, 298 und der Laufzeitteil von 294).

Die Ausnahmen entstehen hier echt, aus Dateien in `tmp_path`, damit
„Wo“ auf dieselbe Weise ermittelt wird wie in einem Schülerprogramm.
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest

from pcl.fehlerkatalog import (
    Fehlermeldung,
    fehlermeldung_aus_dap_erzeugen,
    fehlermeldung_erzeugen,
)


def _ausloesen(f) -> BaseException:  # noqa: ANN001
    try:
        f()
    except BaseException as fehler:  # noqa: BLE001 - genau das wird geprüft
        return fehler
    raise AssertionError("f() hat keine Ausnahme ausgelöst")


@pytest.fixture
def projektordner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Ein Ordner auf `sys.path`, aus dem sich Units importieren lassen,
    wie aus einem Projektordner. Die Units verschwinden danach wieder
    aus `sys.modules`."""
    monkeypatch.syspath_prepend(str(tmp_path))
    vorher = set(sys.modules)
    yield tmp_path
    for name in set(sys.modules) - vorher:
        sys.modules.pop(name, None)


def _meldung(fehler: BaseException) -> Fehlermeldung:
    meldung = fehlermeldung_erzeugen(fehler)
    assert meldung is not None
    return meldung


# -- Punkt 289: die Funktion fehlt, nicht die Unit --------------------------


def test_fehlende_funktion_in_vorhandener_unit(projektordner: Path) -> None:
    (projektordner / "u_probe289.py").write_text(
        'name = "Anna"\n', encoding="utf-8"
    )
    (projektordner / "start289.py").write_text(
        "from u_probe289 import main\n\nmain()\n", encoding="utf-8"
    )

    meldung = _meldung(
        _ausloesen(lambda: importlib.import_module("start289"))
    )

    assert "In der Unit u_probe289 gibt es keine Funktion" in meldung.was
    assert "main" in meldung.was
    assert "konnte nicht geladen werden" not in meldung.was
    assert "def main():" in meldung.pruefe
    assert meldung.wo.startswith("u_probe289.py")


def test_fehlende_unit_bleibt_bei_der_alten_meldung(projektordner: Path) -> None:
    (projektordner / "start289b.py").write_text(
        "from u_gibt_es_nicht import main\n", encoding="utf-8"
    )

    meldung = _meldung(
        _ausloesen(lambda: importlib.import_module("start289b"))
    )

    assert "konnte nicht geladen werden" in meldung.was
    assert meldung.wo.startswith("start289b.py")


# -- Punkt 290: Ereignis ohne Methode ---------------------------------------


def _design_und_unit(ordner: Path) -> None:
    (ordner / "u_probe290_design.py").write_text(
        "# Automatisch erzeugt aus u_probe290.pfm - nicht bearbeiten\n"
        "class _Knopf:\n"
        "    on_click = None\n"
        "\n"
        "\n"
        "class Form1Design:\n"
        "    def create_components(self):\n"
        "        self.button = _Knopf()\n"
        "        self.button.on_click = self.button_click\n",
        encoding="utf-8",
    )
    (ordner / "u_probe290.py").write_text(
        "from u_probe290_design import Form1Design\n"
        "\n"
        "\n"
        "class Form1(Form1Design):\n"
        "    pass\n",
        encoding="utf-8",
    )


def test_ereignis_ohne_methode_nennt_komponente_und_ereignis(
    projektordner: Path,
) -> None:
    _design_und_unit(projektordner)
    unit = importlib.import_module("u_probe290")

    meldung = _meldung(_ausloesen(lambda: unit.Form1().create_components()))

    assert "on_click" in meldung.was
    assert "button" in meldung.was
    assert "button_click" in meldung.was
    assert "u_probe290.py" in meldung.was
    assert "Doppelklick" in meldung.pruefe
    assert meldung.wo.startswith("u_probe290.py")
    assert "_design" not in meldung.als_text()


def test_ereignis_ohne_methode_auch_im_debugger(projektordner: Path) -> None:
    """Derselbe Fall, wie ihn der Debugger als Text bekommt."""
    _design_und_unit(projektordner)
    datei = projektordner / "u_probe290_design.py"
    info = {
        "exceptionId": "AttributeError",
        "breakMode": "unhandled",
        "description": "'Form1' object has no attribute 'button_click'",
        "details": {
            "message": "'Form1' object has no attribute 'button_click'",
            "typeName": "AttributeError",
            "stackTrace": (
                f'  File "{datei}", line 9, in create_components\n'
                "    self.button.on_click = self.button_click\n"
                "                           ^^^^^^^^^^^^^^^^^\n"
            ),
        },
    }

    meldung = fehlermeldung_aus_dap_erzeugen(info)

    assert meldung is not None
    assert "button_click" in meldung.was
    assert meldung.wo.startswith("u_probe290.py")


def test_ein_anderes_fehlendes_attribut_bleibt_wie_es_war() -> None:
    class Objekt:
        pass

    meldung = _meldung(_ausloesen(lambda: Objekt().gibt_es_nicht))

    assert "existiert bei diesem Objekt nicht" in meldung.was


# -- Punkt 294, Laufzeitteil: Komponente im Designer gelöscht --------------


def _formular_ohne_label(ordner: Path, stamm: str) -> None:
    (ordner / f"{stamm}.pfm").write_text(
        json.dumps(
            {
                "format": "pfm/1",
                "class": "Form1",
                "type": "Form",
                "properties": {},
                "children": [
                    {"name": "b_ok", "type": "Button", "properties": {}}
                ],
            }
        ),
        encoding="utf-8",
    )
    (ordner / f"{stamm}.py").write_text(
        "class Form1:\n"
        "    def b_ok_click(self, sender) -> None:\n"
        "        self.label.caption = 'x'\n",
        encoding="utf-8",
    )


def test_geloeschte_komponente_wird_als_solche_gemeldet(
    projektordner: Path,
) -> None:
    _formular_ohne_label(projektordner, "u_probe294")
    unit = importlib.import_module("u_probe294")

    meldung = _meldung(_ausloesen(lambda: unit.Form1().b_ok_click(None)))

    assert "Auf dem Formular Form1 gibt es keine Komponente „label“" in (
        meldung.was
    )
    assert "Designer" in meldung.pruefe
    assert meldung.wo.startswith("u_probe294.py, Zeile 3")
    assert meldung.quelltext == "self.label.caption = 'x'"


def test_geloeschte_komponente_auch_im_debugger(projektordner: Path) -> None:
    _formular_ohne_label(projektordner, "u_probe294b")
    datei = projektordner / "u_probe294b.py"
    info = {
        "exceptionId": "AttributeError",
        "breakMode": "unhandled",
        "description": "'Form1' object has no attribute 'label'",
        "details": {
            "message": "'Form1' object has no attribute 'label'",
            "typeName": "AttributeError",
            "stackTrace": (
                f'  File "{datei}", line 3, in b_ok_click\n'
                "    self.label.caption = 'x'\n"
                "    ^^^^^^^^^^\n"
            ),
        },
    }

    meldung = fehlermeldung_aus_dap_erzeugen(info)

    assert meldung is not None
    assert "keine Komponente „label“" in meldung.was


def test_eine_vorhandene_komponente_bleibt_bei_der_alten_meldung(
    projektordner: Path,
) -> None:
    """Steht die Komponente in der `.pfm`, fehlt etwas anderes, etwa
    weil die Zeile vor dem Aufbau des Formulars läuft."""
    _formular_ohne_label(projektordner, "u_probe294c")
    (projektordner / "u_probe294c.py").write_text(
        "class Form1:\n"
        "    def b_ok_click(self, sender) -> None:\n"
        "        self.b_ok.caption = 'x'\n",
        encoding="utf-8",
    )
    unit = importlib.import_module("u_probe294c")

    meldung = _meldung(_ausloesen(lambda: unit.Form1().b_ok_click(None)))

    assert "keine Komponente" not in meldung.was


# -- Punkt 293: leeres Eingabefeld ------------------------------------------


@pytest.mark.parametrize("umwandlung", [int, float], ids=["int", "float"])
def test_leerer_text_wird_als_leeres_feld_erklaert(umwandlung) -> None:  # noqa: ANN001
    meldung = _meldung(_ausloesen(lambda: umwandlung("")))

    assert meldung.was.startswith("Der Text ist leer")
    assert "nichts eingegeben" in meldung.was
    assert "„“" not in meldung.was
    assert "leer" in meldung.pruefe
    assert meldung.pruefe.endswith("?") or "?" in meldung.pruefe


def test_ein_nicht_leerer_text_bleibt_bei_der_alten_meldung() -> None:
    meldung = _meldung(_ausloesen(lambda: int("12 cm")))

    assert "lässt sich nicht als ganze Zahl lesen" in meldung.was


# -- Punkt 298: die dritte Überschrift spricht niemanden an -----------------


def test_keine_meldung_beginnt_mit_pruefe() -> None:
    meldung = _meldung(_ausloesen(lambda: 1 / 0))
    text = meldung.als_text()

    assert "Prüfe" not in text
    assert "\nZu prüfen: " in text
