"""Eine im Objektinspektor gewählte Ereignis-Verknüpfung muss ankommen.

Gefunden bei der Durchsicht „Was sieht eine Lernende?“ (M12): Der Reiter
„Ereignisse“ setzte den Handler nur am Live-Objekt. Der Designer
zeigte die Verknüpfung an, die `.pfm` und `u_*_design.py` erfuhren nichts
davon – und im gestarteten Programm tat der Knopf nichts.

Das Tückische daran: manchmal kam sie doch an. Änderte die Schülerin
danach noch irgendeine Eigenschaft, schrieb der Designer die `.pfm`
komplett aus dem Live-Formular neu und nahm den Handler dabei mit. „Mal
geht mein Knopf, mal nicht“ ist für jemanden, der programmieren lernt,
der denkbar schlechteste Fehler: er lehrt, dem eigenen Programm nicht zu
trauen.

Derselbe Fehler war bei den Eigenschaften schon einmal gefunden und
behoben worden (siehe `DesignerCanvas.eigenschaft_uebernehmen`); der
Reiter daneben blieb dabei übersehen.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

from ide.designer.canvas import DesignerCanvas
from ide.inspector.ereignisse_tabelle import KEIN_HANDLER
from ide.inspector.objektinspektor import Objektinspektor
from pcl import Button, Form


class _Formular(Form):
    def create_components(self) -> None:
        pass

    def b_ein_click(self, sender) -> None:
        self.caption = "geklickt"

    def b_aus_click(self, sender) -> None:
        self.caption = "auch geklickt"


@pytest.fixture
def aufbau(tmp_path: Path) -> tuple[Objektinspektor, DesignerCanvas, Any, Path]:
    pfm = tmp_path / "u_main.pfm"
    formular = _Formular()
    canvas = DesignerCanvas(formular, pfm_pfad=pfm)
    knopf = canvas.komponente_platzieren(Button, 10, 10)

    inspektor = Objektinspektor()
    inspektor.formular_anzeigen(formular, canvas)
    # Genau wie im Hauptfenster: der Designer gibt jede Auswahl an den
    # Objektinspektor weiter. Ohne diese Verbindung prüfte der Test
    # einen Aufbau, den es so nirgends gibt - und hätte den Neuaufbau
    # mitten in der Meldung gar nicht ausgelöst.
    canvas.auswahl_beobachten(inspektor._eigenschaften_anzeigen)
    inspektor.baum.setCurrentItem(inspektor.baum.topLevelItem(0).child(0))
    return inspektor, canvas, knopf, pfm


def _auswahl(inspektor: Objektinspektor):
    """Das Auswahlfeld der ersten Ereigniszeile."""
    return inspektor.ereignisse_tabelle.cellWidget(0, 1)


def _pfm_ereignisse(pfm: Path) -> dict[str, str]:
    inhalt = json.loads(pfm.read_text(encoding="utf-8"))
    return inhalt["children"][0].get("events", {})


def test_die_verknuepfung_steht_in_der_pfm(aufbau) -> None:
    inspektor, _canvas, _knopf, pfm = aufbau

    _auswahl(inspektor).setCurrentText("b_ein_click")

    assert _pfm_ereignisse(pfm) == {"on_click": "b_ein_click"}


def test_die_verknuepfung_steht_im_erzeugten_code(aufbau) -> None:
    inspektor, _canvas, _knopf, pfm = aufbau

    _auswahl(inspektor).setCurrentText("b_ein_click")

    code = (pfm.parent / "u_main_design.py").read_text(encoding="utf-8")
    assert "self.button.on_click = self.b_ein_click" in code


def test_im_gestarteten_programm_haengt_der_handler_am_knopf(aufbau) -> None:
    """Der Punkt, um den es geht: nicht die Anzeige im Designer, sondern
    das Programm, das die Schülerin danach startet."""
    inspektor, _canvas, _knopf, pfm = aufbau
    _auswahl(inspektor).setCurrentText("b_ein_click")

    design = pfm.parent / "u_main_design.py"
    spec = importlib.util.spec_from_file_location("verknuepfung_design", design)
    modul = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = modul
    try:
        spec.loader.exec_module(modul)

        class _Programm(modul._FormularDesign):
            def b_ein_click(self, sender) -> None:
                self.caption = "geklickt"

        formular = _Programm()
        assert formular.button.on_click is not None
        assert formular.button.on_click.__name__ == "b_ein_click"
    finally:
        del sys.modules[spec.name]


def test_kein_handler_nimmt_die_verknuepfung_wieder_heraus(aufbau) -> None:
    inspektor, _canvas, _knopf, pfm = aufbau
    _auswahl(inspektor).setCurrentText("b_ein_click")
    assert _pfm_ereignisse(pfm)

    _auswahl(inspektor).setCurrentText(KEIN_HANDLER)

    assert _pfm_ereignisse(pfm) == {}
    code = (pfm.parent / "u_main_design.py").read_text(encoding="utf-8")
    assert "on_click" not in code


def test_das_verknuepfen_laesst_sich_rueckgaengig_machen(aufbau) -> None:
    """Weil die Meldung über denselben Kommandostapel läuft wie eine
    Eigenschaftsänderung, gibt es Rückgängig gratis dazu."""
    inspektor, canvas, knopf, pfm = aufbau
    _auswahl(inspektor).setCurrentText("b_ein_click")

    canvas.rueckgaengig()

    assert knopf.on_click is None
    assert _pfm_ereignisse(pfm) == {}


def test_ein_wechsel_des_handlers_kommt_ebenfalls_an(aufbau) -> None:
    inspektor, _canvas, _knopf, pfm = aufbau
    _auswahl(inspektor).setCurrentText("b_ein_click")

    _auswahl(inspektor).setCurrentText("b_aus_click")

    assert _pfm_ereignisse(pfm) == {"on_click": "b_aus_click"}


def test_der_reiter_ueberlebt_den_neuaufbau_mitten_im_waehlen(aufbau) -> None:
    """Der Designer gibt nach jeder Änderung die Auswahl neu bekannt,
    und der Objektinspektor baut daraufhin beide Reiter neu auf – mitten
    im Signal des Auswahlfelds, aus dem die Meldung kam. Qt räumt das
    alte Feld erst danach weg (`deleteLater`), es darf also weder
    abstürzen noch die Anzeige verlieren."""
    inspektor, _canvas, _knopf, _pfm = aufbau

    _auswahl(inspektor).setCurrentText("b_ein_click")

    nachher = _auswahl(inspektor)
    assert nachher is not None
    assert nachher.currentText() == "b_ein_click"
    # Und die Eigenschaften-Seite steht auch noch.
    assert inspektor.eigenschaften_tabelle.rowCount() > 0
