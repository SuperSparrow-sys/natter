"""Komponenten ohne eigene Anzeige - im Designer sichtbar, im Programm nicht.

Ein Zeitgeber tickt nur; anzuzeigen hat er nichts. Trotzdem muss man ihn
im Designer anfassen können, sonst lässt sich sein Intervall nirgends
einstellen. Lazarus löst das seit jeher mit einem kleinen Symbol auf dem
Formular, das im fertigen Programm verschwindet.

Vorher war der `Timer` in Natter deshalb bewusst keine `Control`:
keine Kachel in der Palette, kein Eintrag in der `.pfm`, er musste im
Quelltext erzeugt werden. Der Nutzer hat das umgekehrt
- „der Timer muss als Komponente auch mit rein, der ist wichtig".

Die Lösung ist `Control.nur_im_designer`. Weil solche Komponenten damit
gewöhnliche `Control`s sind, brauchen Komponentenbaum,
Objektinspektor, `.pfm`-Schreiber und Codeerzeugung keinen einzigen
Sonderfall - genau das prüfen die Tests hier.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ide.codegen.design import design_code_erzeugen
from ide.designer.canvas import DesignerCanvas
from ide.designer.pfm_schreiben import formular_als_pfm_speichern
from ide.inspector.komponentenbaum import kind_komponenten
from pcl import Form, Timer
from pcl.control import Control


class _Formular(Form):
    def create_components(self) -> None:
        self.width = 400
        self.height = 300


@pytest.fixture
def formular(qtbot) -> _Formular:
    f = _Formular()
    qtbot.addWidget(f._qwidget)
    return f


def test_der_zeitgeber_versteckt_sich_im_laufenden_programm(formular) -> None:
    """So, wie ein Schülerprogramm ihn erzeugt: über das Formular."""
    zeitgeber = Timer(formular)

    assert isinstance(zeitgeber, Control)
    # `isHidden` statt `isVisible`: ein Kind eines noch nicht
    # angezeigten Fensters ist nie "visible", auch wenn es gezeigt
    # werden soll. `isHidden` fragt genau das, worum es hier geht -
    # wurde die Komponente ausdrücklich versteckt?
    assert zeitgeber._qwidget.isHidden()


def test_der_designer_holt_ihn_hervor(formular, tmp_path) -> None:
    """Der Gegentest: auf der Zeichenfläche muss man ihn sehen und
    anklicken können."""
    formular.t_ampel = Timer(formular)

    canvas = DesignerCanvas(formular, tmp_path / "u_main.pfm")

    assert not formular.t_ampel._qwidget.isHidden()
    # Und er ist anklickbar, also dem Canvas bekannt.
    assert formular.t_ampel._qwidget in canvas._widget_zu_komponente


def test_er_steht_im_komponentenbaum(formular) -> None:
    """Ohne eigenen Sonderfall - `kind_komponenten` sammelt alles, was
    eine `Control` ist."""
    formular.t_ampel = Timer(formular)

    namen = [name for name, _ in kind_komponenten(formular)]

    assert "t_ampel" in namen


def test_er_landet_mit_lage_und_intervall_in_der_pfm(formular, tmp_path) -> None:
    """Die Lage beschreibt, wo sein Symbol auf dem Formular liegt - wie
    Lazarus' DesignInfo. Ohne sie läge er nach dem nächsten Öffnen in
    der linken oberen Ecke."""
    formular.t_ampel = Timer(formular)
    formular.t_ampel.left = 120
    formular.t_ampel.top = 64
    formular.t_ampel.interval = 2000
    formular.t_ampel.enabled = False

    ziel = tmp_path / "u_main.pfm"
    formular_als_pfm_speichern(formular, ziel)
    kinder = json.loads(ziel.read_text(encoding="utf-8"))["children"]
    eintrag = next(k for k in kinder if k["name"] == "t_ampel")

    assert eintrag["type"] == "Timer"
    assert eintrag["properties"]["left"] == 120
    assert eintrag["properties"]["top"] == 64
    assert eintrag["properties"]["interval"] == 2000
    assert eintrag["properties"]["enabled"] is False


def test_die_codeerzeugung_braucht_keinen_sonderfall() -> None:
    """`Timer(self)` muss der Konstruktor vertragen - der Designer
    erzeugt für jede Komponente genau diesen Aufruf. Genau daran ist es
    beim ersten Versuch gescheitert."""
    pfm = {
        "format": "pfm/1",
        "class": "Form1",
        "type": "Form",
        "properties": {},
        "children": [
            {
                "name": "t_ampel",
                "type": "Timer",
                "properties": {"left": 10, "top": 10, "interval": 500},
                "events": {"on_timer": "t_ampel_timer"},
            }
        ],
    }

    quelltext = design_code_erzeugen(pfm, "u_main.pfm")

    assert "self.t_ampel = Timer(self)" in quelltext
    assert "self.t_ampel.interval = 500" in quelltext
    assert "self.t_ampel.on_timer = self.t_ampel_timer" in quelltext


def test_ein_beispielprojekt_zeigt_den_zeitgeber_auf_dem_formular() -> None:
    """Wer wissen will, wie ein Zeitgeber benutzt wird, findet ihn im
    Lehrgang - nicht nur in der Dokumentation."""
    pfm = Path("beispielprojekte/04_CookieKlicker/u_main.pfm")
    kinder = json.loads(pfm.read_text(encoding="utf-8"))["children"]

    assert any(k["type"] == "Timer" for k in kinder)
