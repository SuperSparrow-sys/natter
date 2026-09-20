"""Abnahmetest für M3 (docs/arbeitspakete/M3.md, Schritt 8): baut ein
mitgeliefertes Formular ausschließlich über dieselben Operationen nach,
die Designer, Objektinspektor und Komponentenpalette in der laufenden
IDE auslösen (`komponente_platzieren`, `setattr` für Eigenschaften wie
die Eigenschaftentabelle, `komponente_umbenennen`,
`ereignis_handler_erzeugen` für den Doppelklick) - nicht durch Schreiben
der `.pfm` von Hand. Das Ergebnis wird mit der echten
`beispielprojekte/03_Taschenrechner/u_main.pfm` verglichen.

Bis M14 hing dieser Test am Beispielprojekt „Ampel". Mit dem Lehrgang
ist der Taschenrechner an seine Stelle getreten: er ist die erste Stufe
mit Oberfläche und besteht aus genau den Bausteinen, die ein Anfänger
zuerst benutzt - Beschriftung, Eingabefeld, Knopf. Was hier nicht über
die IDE nachbaubar ist, kann auf Stufe 3 niemand bauen.
"""

import json
from pathlib import Path

from ide.designer.canvas import DesignerCanvas
from ide.designer.pfm_schreiben import pfm_aus_formular
from pcl import Button, Edit, Form, Label

_ECHTE_PFM = (
    Path(__file__).resolve().parent.parent
    / "beispielprojekte"
    / "03_Taschenrechner"
    / "u_main.pfm"
)

_STARTINHALT = '''"""u_main: von Hand nachgebautes Formular (Abnahmetest)."""


class Form1:
    pass
'''


class Form1(Form):
    pass


def _unit_datei_vorbereiten(tmp_path: Path) -> Path:
    unit_pfad = tmp_path / "u_main.py"
    unit_pfad.write_text(_STARTINHALT, encoding="utf-8")
    return unit_pfad


def _platzieren(canvas: DesignerCanvas, typ, x: int, y: int):
    """Ablegen und danach auf den Pixel genau setzen.

    Das Ablegen rastet seit September 2026 am 8px-Raster ein (wie
    „Snap to grid" in Lazarus). Der Taschenrechner ist von Hand
    gesetzt und steht an mehreren Stellen dazwischen; nachgebaut wird
    er deshalb so, wie ein Schüler es auch täte - ablegen, dann im
    Objektinspektor genau einstellen.
    """
    komponente = canvas.komponente_platzieren(typ, x, y)
    komponente.left, komponente.top = x, y
    return komponente


def _in_der_ide_nachbauen(canvas: DesignerCanvas) -> list:
    """Baut den Taschenrechner Schritt für Schritt auf und gibt die
    Knöpfe zurück, für die Ereignismethoden entstehen sollen."""
    formular = canvas.formular
    formular.caption = "Taschenrechner"
    formular.width = 520
    formular.height = 340

    l_titel = _platzieren(canvas, Label, 24, 20)
    l_titel.width, l_titel.height = 300, 28
    l_titel.caption = "Taschenrechner"
    canvas.komponente_umbenennen(l_titel, "l_titel")

    l_zahl1 = _platzieren(canvas, Label, 24, 72)
    l_zahl1.width = 110
    l_zahl1.caption = "Erste Zahl"
    canvas.komponente_umbenennen(l_zahl1, "l_zahl1")

    e_zahl1 = _platzieren(canvas, Edit, 150, 68)
    e_zahl1.width = 120
    e_zahl1.text = "12"
    canvas.komponente_umbenennen(e_zahl1, "e_zahl1")

    l_zahl2 = _platzieren(canvas, Label, 24, 112)
    l_zahl2.width = 110
    l_zahl2.caption = "Zweite Zahl"
    canvas.komponente_umbenennen(l_zahl2, "l_zahl2")

    e_zahl2 = _platzieren(canvas, Edit, 150, 108)
    e_zahl2.width = 120
    e_zahl2.text = "4"
    canvas.komponente_umbenennen(e_zahl2, "e_zahl2")

    knoepfe = []
    for name, x, beschriftung in (
        ("b_plus", 24, "+"),
        ("b_minus", 134, "-"),
        ("b_mal", 244, "*"),
        ("b_geteilt", 354, "/"),
    ):
        knopf = _platzieren(canvas, Button, x, 160)
        knopf.width = 100
        knopf.caption = beschriftung
        canvas.komponente_umbenennen(knopf, name)
        knoepfe.append(knopf)

    l_ergebnis = _platzieren(canvas, Label, 24, 220)
    l_ergebnis.width, l_ergebnis.height = 440, 40
    l_ergebnis.caption = "Ergebnis: -"
    canvas.komponente_umbenennen(l_ergebnis, "l_ergebnis")

    # Doppelklick-Äquivalent: erzeugt die Ereignismethoden in u_main.py
    for knopf in knoepfe:
        canvas.ereignis_handler_erzeugen(knopf)
    return knoepfe


def test_das_formular_laesst_sich_vollstaendig_ueber_die_ide_nachbauen(tmp_path: Path) -> None:
    _unit_datei_vorbereiten(tmp_path)
    formular = Form1()
    canvas = DesignerCanvas(formular, pfm_pfad=tmp_path / "u_main.pfm")

    _in_der_ide_nachbauen(canvas)

    nachgebaut = pfm_aus_formular(formular)
    echt = json.loads(_ECHTE_PFM.read_text(encoding="utf-8"))

    assert nachgebaut["properties"]["caption"] == echt["properties"]["caption"]
    assert nachgebaut["properties"]["width"] == echt["properties"]["width"]
    assert nachgebaut["properties"]["height"] == echt["properties"]["height"]
    assert nachgebaut.get("events", {}) == echt.get("events", {})

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
            assert getattr(komponente, eigenschaft) == wert


def test_erzeugte_ereignismethoden_stehen_alle_in_der_unit(tmp_path: Path) -> None:
    unit_pfad = _unit_datei_vorbereiten(tmp_path)
    formular = Form1()
    canvas = DesignerCanvas(formular, pfm_pfad=tmp_path / "u_main.pfm")

    _in_der_ide_nachbauen(canvas)

    quelltext = unit_pfad.read_text(encoding="utf-8")
    for name in ("b_plus_click", "b_minus_click", "b_mal_click", "b_geteilt_click"):
        assert f"def {name}(self, sender)" in quelltext
