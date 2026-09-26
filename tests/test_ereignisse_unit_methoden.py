"""Der Reiter „Ereignisse“ bietet Methoden aus der Unit an (Punkt 38
der offenen Punkte).

Bis 0.3.3 kannte die Auswahl nur Methoden, die schon in der `.pfm`
verknüpft waren. Eine von Hand in `u_main.py` geschriebene Methode
`button_click(self, sender)` erschien nicht, obwohl
`docs/erste_schritte.md` verspricht, dass sich dort eine vorhandene
Methode auswählen lässt.
"""

from __future__ import annotations

from pathlib import Path

from ide.designer.laden import formular_fuer_designer_laden
from ide.inspector.ereignisse_tabelle import passende_methoden
from ide.project.neu import projekt_erzeugen
from pcl import Button

_UNIT = '''from u_main_design import Form1Design


class Form1(Form1Design):
    def form_create(self, sender):
        pass

    def button_click(self, sender):
        pass

    def maus_runter(self, sender, x, y):
        pass

    def _hilfsfunktion(self, sender):
        pass
'''


def _projekt(tmp_path: Path) -> Path:
    projekt = projekt_erzeugen("gui", tmp_path, "Umrechner")
    (projekt.ordner / "u_main.py").write_text(_UNIT, encoding="utf-8")
    return projekt.ordner / "u_main.pfm"


def test_methoden_aus_der_unit_stehen_in_der_auswahl(tmp_path: Path) -> None:
    formular = formular_fuer_designer_laden(_projekt(tmp_path))

    klick = passende_methoden(formular, "on_click")
    assert "button_click" in klick
    assert "form_create" in klick
    # falsche Zahl an Parametern und private Methoden bleiben draußen
    assert "maus_runter" not in klick
    assert "_hilfsfunktion" not in klick
    assert "maus_runter" in passende_methoden(formular, "on_mouse_down")


def test_methode_aus_der_unit_laesst_sich_verknuepfen(tmp_path: Path) -> None:
    from ide.inspector.ereignisse_tabelle import EreignisseTabelle

    formular = formular_fuer_designer_laden(_projekt(tmp_path))
    knopf = Button(formular)
    tabelle = EreignisseTabelle()
    meldungen = []
    tabelle.anzeigen(knopf, formular, lambda *a: meldungen.append(a))

    tabelle._handler_setzen("on_click", "button_click")

    assert knopf.on_click.__name__ == "button_click"
    assert meldungen[-1][1] == "on_click"


def test_spaeter_geschriebene_methode_erscheint_ohne_neu_laden(tmp_path: Path) -> None:
    pfm = _projekt(tmp_path)
    formular = formular_fuer_designer_laden(pfm)
    unit = pfm.with_suffix(".py")
    unit.write_text(
        _UNIT + "\n    def neu_click(self, sender):\n        pass\n",
        encoding="utf-8",
    )

    assert "neu_click" in passende_methoden(formular, "on_click")


def test_unit_mit_syntaxfehler_stoert_nicht(tmp_path: Path) -> None:
    pfm = _projekt(tmp_path)
    pfm.with_suffix(".py").write_text("class Form1(:\n", encoding="utf-8")

    formular = formular_fuer_designer_laden(pfm)

    assert passende_methoden(formular, "on_click") == []
