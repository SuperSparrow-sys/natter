"""Vergessenes `self.` vor einem Komponentennamen (Punkt 431).

`edit.text = "x"` statt `self.edit.text = "x"` in einer Methode des
Formulars ist der häufigste Fehler in den ersten Fensterprogrammen.
Die Prüfung vor dem Start, die Laufzeitmeldung und die Meldung im
Debugger fragten nach Schreibweise und Import, und beides stimmt. Hier
geht jeder Fall alle drei Wege; die Frage nach `self.` muss überall
gleich lauten und nur dort stehen, wo der Name in der Klasse bekannt
ist.

Das Projekt entsteht aus der echten Vorlage in `tmp_path`.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from ide.project import Projekt
from ide.project.neu import projekt_erzeugen
from ide.run.pruefung import projekt_pruefen
from pcl.fehlerkatalog import (
    fehlermeldung_aus_dap_erzeugen,
    fehlermeldung_erzeugen,
)

_KOPF = (
    "from u_main_design import Form1Design\n\n\n"
    "class Form1(Form1Design):\n"
    "    def form_create(self, sender):\n"
    "        self.zaehler = 0\n\n"
    "    def button_click(self, sender):\n"
)
#: Zeile, in der die Methode `button_click` den Fehler auslöst.
_ZEILE = 9

FAELLE = [
    pytest.param(
        '        edit.text = "x"\n',
        "Auf dem Formular gibt es eine Komponente edit. Ist sie gemeint, "
        "und fehlt davor self.?",
        id="komponente",
    ),
    pytest.param(
        "        print(zaehler)\n",
        "In der Klasse Form1 wird self.zaehler gesetzt. Ist dieser Wert "
        "gemeint, und fehlt davor self.?",
        id="attribut",
    ),
    pytest.param("        print(ergebnis)\n", None, id="sonst"),
]


def _projekt(ordner: Path, zeile: str) -> Projekt:
    projekt = projekt_erzeugen("gui", ordner, "Fenster")
    pfm_pfad = projekt.ordner / "u_main.pfm"
    pfm = json.loads(pfm_pfad.read_text(encoding="utf-8"))
    pfm["children"].extend(
        [
            {
                "name": "button",
                "type": "Button",
                "properties": {"left": 10, "top": 10},
                "events": {"on_click": "button_click"},
            },
            {
                "name": "edit",
                "type": "Edit",
                "properties": {"left": 10, "top": 50},
            },
        ]
    )
    pfm["events"] = {"on_create": "form_create"}
    pfm_pfad.write_text(json.dumps(pfm), encoding="utf-8")
    (projekt.ordner / "u_main.py").write_text(_KOPF + zeile, encoding="utf-8")
    return projekt


def _vorstart(projekt: Projekt) -> tuple[str, str]:
    funde = [f for f in projekt_pruefen(projekt) if f.code == "F821"]
    assert len(funde) == 1
    assert (funde[0].datei.name, funde[0].zeile) == ("u_main.py", _ZEILE)
    return funde[0].was, funde[0].pruefe


def _ausnahme(ordner: Path) -> NameError:
    sys.modules.pop("u_main_design", None)
    sys.path.insert(0, str(ordner))
    try:
        spec = importlib.util.spec_from_file_location(
            "u_main_probe_431", ordner / "u_main.py"
        )
        assert spec is not None and spec.loader is not None
        modul = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modul)
        try:
            modul.Form1.button_click(None, None)
        except NameError as fehler:
            return fehler
    finally:
        sys.path.remove(str(ordner))
        sys.modules.pop("u_main_design", None)
    raise AssertionError("kein NameError")


def _laufzeit(projekt: Projekt) -> tuple[str, str]:
    meldung = fehlermeldung_erzeugen(_ausnahme(projekt.ordner))
    assert meldung is not None
    assert meldung.wo.startswith(f"u_main.py, Zeile {_ZEILE}")
    return meldung.was, meldung.pruefe


def _debugger(projekt: Projekt) -> tuple[str, str]:
    ordner = projekt.ordner
    fehler = _ausnahme(ordner)
    zeile = (ordner / "u_main.py").read_text("utf-8").splitlines()[_ZEILE - 1]
    meldung = fehlermeldung_aus_dap_erzeugen(
        {
            "exceptionId": "NameError",
            "description": str(fehler),
            "details": {
                "message": str(fehler),
                "stackTrace": (
                    f'  File "{ordner / "u_main.py"}", line {_ZEILE}, '
                    f"in button_click\n    {zeile.strip()}\n"
                ),
            },
        }
    )
    assert meldung is not None
    return meldung.was, meldung.pruefe


WEGE = [
    pytest.param(_vorstart, id="vorstart"),
    pytest.param(_laufzeit, id="laufzeit"),
    pytest.param(_debugger, id="debugger"),
]


@pytest.mark.parametrize("weg", WEGE)
@pytest.mark.parametrize("zeile,leitfrage", FAELLE)
def test_die_leitfrage_nennt_das_fehlende_self_nur_wo_es_passt(
    tmp_path: Path, weg, zeile: str, leitfrage: str | None
) -> None:
    was, pruefe = weg(_projekt(tmp_path / "p", zeile))

    assert "nicht bekannt" in was
    if leitfrage is None:
        assert "self." not in pruefe
        assert "geschrieben" in pruefe or "Schreibweise" in pruefe
    else:
        assert pruefe == leitfrage
