"""Abnahmetest für M3 (docs/arbeitspakete/M3.md, Schritt 8): baut das
Ampel-Formular ausschließlich über dieselben Operationen nach, die
Designer, Objektinspektor und Komponentenpalette in der laufenden IDE
auslösen (`komponente_platzieren`, `setattr` für Eigenschaften wie die
Eigenschaftentabelle, `komponente_umbenennen`, `ereignis_handler_erzeugen`
für Doppelklick) - nicht durch Schreiben der `.pfm` von Hand. Ergebnis wird
mit der echten `beispielprojekte/Ampel/u_main.pfm` verglichen.

Einzige Ausnahme (noch nicht als Inspektor-Zeile umgesetzt, siehe M3.md):
`Shape.brush.color` ist eine aufklappbare Untereigenschaft ohne eigene
Tabellenzeile, wird hier daher wie in `u_main.py` direkt zugewiesen statt
über die (noch nicht existierende) Inspektor-Zeile.
"""

import json
from pathlib import Path

from ide.designer.canvas import DesignerCanvas
from ide.designer.pfm_schreiben import pfm_aus_formular
from pcl import Button, Form, Label, Shape

_ECHTE_AMPEL_PFM = (
    Path(__file__).resolve().parent.parent / "beispielprojekte" / "Ampel" / "u_main.pfm"
)

_STARTINHALT = '''"""u_main: von Hand nachgebautes Ampel-Formular (Abnahmetest)."""


class Form1:
    pass
'''


class Form1(Form):
    pass


def _unit_datei_vorbereiten(tmp_path: Path) -> Path:
    unit_pfad = tmp_path / "u_main.py"
    unit_pfad.write_text(_STARTINHALT, encoding="utf-8")
    return unit_pfad


def _ampel_in_der_ide_nachbauen(canvas: DesignerCanvas) -> None:
    formular = canvas.formular
    formular.caption = "Ampel"
    formular.width = 620
    formular.height = 736

    # Breiter als Lazarus' 75px-Original: bei unserer (bewusst nicht zu
    # kleinen) UI-Schriftgröße passte "Einschalten" u. Ä. sonst nicht in
    # den Button (real per Screenshot gefunden - kein Lazarus-Fehler,
    # sondern ein Unterschied in der Zeichenbreite zwischen den
    # Toolkits, siehe docs/PLAN.md).
    b_ein = canvas.komponente_platzieren(Button, 392, 184)
    b_ein.width, b_ein.height = 170, 25
    b_ein.caption = "Einschalten"
    canvas.komponente_umbenennen(b_ein, "b_einschalten")

    b_wechseln = canvas.komponente_platzieren(Button, 400, 223)
    b_wechseln.width, b_wechseln.height = 170, 25
    b_wechseln.caption = "Wechseln"
    canvas.komponente_umbenennen(b_wechseln, "b_wechseln")

    b_aus = canvas.komponente_platzieren(Button, 413, 262)
    b_aus.width, b_aus.height = 170, 25
    b_aus.caption = "Auschalten"
    canvas.komponente_umbenennen(b_aus, "b_auschalten")

    l_titel = canvas.komponente_platzieren(Label, 128, 67)
    l_titel.width, l_titel.height = 192, 32
    l_titel.caption = "Ampel Simulator"
    canvas.komponente_umbenennen(l_titel, "l_titel")

    s_gehaeuse = canvas.komponente_platzieren(Shape, 135, 160)
    s_gehaeuse.width, s_gehaeuse.height = 169, 330
    s_gehaeuse.brush.color = "#808080"
    canvas.komponente_umbenennen(s_gehaeuse, "s_gehaeuse")

    s_rot = canvas.komponente_platzieren(Shape, 170, 176)
    s_rot.width, s_rot.height = 96, 89
    s_rot.shape = "circle"
    s_rot.brush.color = "#000000"
    canvas.komponente_umbenennen(s_rot, "s_rot")

    s_gelb = canvas.komponente_platzieren(Shape, 169, 272)
    s_gelb.width, s_gelb.height = 97, 89
    s_gelb.shape = "circle"
    s_gelb.brush.color = "#000000"
    canvas.komponente_umbenennen(s_gelb, "s_gelb")

    s_gruen = canvas.komponente_platzieren(Shape, 176, 376)
    s_gruen.width, s_gruen.height = 90, 80
    s_gruen.shape = "circle"
    s_gruen.brush.color = "#000000"
    canvas.komponente_umbenennen(s_gruen, "s_gruen")

    # Doppelklick-Äquivalent: erzeugt die Ereignismethoden in u_main.py
    canvas.ereignis_handler_erzeugen(formular)
    canvas.ereignis_handler_erzeugen(b_ein)
    canvas.ereignis_handler_erzeugen(b_wechseln)
    canvas.ereignis_handler_erzeugen(b_aus)


def test_ampel_laesst_sich_vollstaendig_ueber_die_ide_nachbauen(tmp_path: Path) -> None:
    _unit_datei_vorbereiten(tmp_path)
    formular = Form1()
    canvas = DesignerCanvas(formular, pfm_pfad=tmp_path / "u_main.pfm")

    _ampel_in_der_ide_nachbauen(canvas)

    nachgebaut = pfm_aus_formular(formular)
    echt = json.loads(_ECHTE_AMPEL_PFM.read_text(encoding="utf-8"))

    assert nachgebaut["properties"]["caption"] == echt["properties"]["caption"]
    assert nachgebaut["properties"]["width"] == echt["properties"]["width"]
    assert nachgebaut["properties"]["height"] == echt["properties"]["height"]
    assert nachgebaut["events"] == echt["events"]

    nachgebaute_kinder = {kind["name"]: kind for kind in nachgebaut["children"]}
    echte_kinder = {kind["name"]: kind for kind in echt["children"]}
    assert set(nachgebaute_kinder) == set(echte_kinder)

    # Eigenschaften werden gegen die LIVE-Komponente verglichen statt gegen
    # das serialisierte .pfm: die echte Datei enthält von Hand auch Werte,
    # die zufällig dem Standardwert entsprechen (z. B. width/height 75/25
    # bei Button), während die IDE korrekt nur Abweichungen speichert
    # (Abschnitt 4.2) - beides ist derselbe Zustand, nur unterschiedlich
    # knapp serialisiert.
    for name, echtes_kind in echte_kinder.items():
        nachgebautes_kind = nachgebaute_kinder[name]
        assert nachgebautes_kind["type"] == echtes_kind["type"]
        assert nachgebautes_kind.get("events", {}) == echtes_kind.get("events", {})
        komponente = getattr(formular, name)
        for eigenschaft, wert in echtes_kind["properties"].items():
            if eigenschaft == "brush_color":
                assert komponente.brush.color == wert
            else:
                assert getattr(komponente, eigenschaft) == wert


def test_erzeugte_ereignismethoden_stehen_alle_in_der_unit(tmp_path: Path) -> None:
    unit_pfad = _unit_datei_vorbereiten(tmp_path)
    formular = Form1()
    canvas = DesignerCanvas(formular, pfm_pfad=tmp_path / "u_main.pfm")

    _ampel_in_der_ide_nachbauen(canvas)

    quelltext = unit_pfad.read_text(encoding="utf-8")
    for methodenname in (
        "form_create",
        "b_einschalten_click",
        "b_wechseln_click",
        "b_auschalten_click",
    ):
        assert f"def {methodenname}(self, sender):" in quelltext
    compile(quelltext, str(unit_pfad), "exec")
