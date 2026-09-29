"""Tab-Reihenfolge im Designer ändern (Punkt 61).

Die Design-Prüfung meldete eine ungünstige Reihenfolge, ändern ließ
sie sich nur durch Löschen und neu Anlegen. Nebenbei: eine umbenannte
Komponente rückte ans Ende der Reihenfolge.
"""

from __future__ import annotations

import json
from pathlib import Path

from ide.designer.canvas import DesignerCanvas
from ide.designer.pfm_schreiben import pfm_aus_formular
from ide.inspector.komponentenbaum import kind_komponenten
from ide.lint.regeln import pruefen as design_pruefen
from pcl import Button, Edit, Form, Label, Panel


class _Formular(Form):
    def create_components(self) -> None:
        # Absichtlich durcheinander angelegt: erst unten, dann oben.
        self.b_ok = Button(self)
        self.b_ok.left, self.b_ok.top = 20, 200
        self.e_name = Edit(self)
        self.e_name.left, self.e_name.top = 120, 40
        self.l_name = Label(self)
        self.l_name.left, self.l_name.top = 20, 40
        self.p_rand = Panel(self)
        self.p_rand.left, self.p_rand.top = 20, 100
        self.b_innen2 = Button(self.p_rand)
        self.b_innen2.left, self.b_innen2.top = 100, 10
        self.b_innen1 = Button(self.p_rand)
        self.b_innen1.left, self.b_innen1.top = 10, 10


def _canvas(qtbot, tmp_path: Path | None = None) -> tuple[_Formular, DesignerCanvas]:  # noqa: ANN001
    formular = _Formular()
    qtbot.addWidget(formular._qwidget)
    pfm = None
    if tmp_path is not None:
        pfm = tmp_path / "u_main.pfm"
        pfm.write_text(json.dumps(pfm_aus_formular(formular)), encoding="utf-8")
    return formular, DesignerCanvas(formular, pfm_pfad=pfm)


def _reihenfolge(objekt) -> list[str]:  # noqa: ANN001
    return [name for name, _ in kind_komponenten(objekt)]


def test_frueher_und_spaeter(qtbot) -> None:  # noqa: ANN001
    formular, canvas = _canvas(qtbot)

    assert canvas.tab_reihenfolge_verschieben(formular.l_name, -1)
    assert _reihenfolge(formular) == ["b_ok", "l_name", "e_name", "p_rand"]
    assert not canvas.tab_reihenfolge_verschieben(formular.p_rand, 1)

    canvas.rueckgaengig()
    assert _reihenfolge(formular) == ["b_ok", "e_name", "l_name", "p_rand"]


def test_nach_lage_ordnen_behebt_den_fund_der_design_pruefung(
    qtbot, tmp_path: Path  # noqa: ANN001
) -> None:
    formular, canvas = _canvas(qtbot, tmp_path)
    regeln = {b.regel for b in design_pruefen(pfm_aus_formular(formular))}
    assert "bedienbarkeit.tab_reihenfolge" in regeln

    assert canvas.tab_reihenfolge_nach_lage()

    assert _reihenfolge(formular) == ["l_name", "e_name", "p_rand", "b_ok"]
    assert _reihenfolge(formular.p_rand) == ["b_innen1", "b_innen2"]
    canvas.jetzt_schreiben()
    gespeichert = json.loads((tmp_path / "u_main.pfm").read_text(encoding="utf-8"))
    assert [k["name"] for k in gespeichert["children"]] == ["l_name", "e_name", "p_rand", "b_ok"]
    regeln = {b.regel for b in design_pruefen(gespeichert)}
    assert "bedienbarkeit.tab_reihenfolge" not in regeln
    assert not canvas.tab_reihenfolge_nach_lage()


def test_kontextmenue_bietet_die_reihenfolge_an(qtbot) -> None:  # noqa: ANN001
    formular, canvas = _canvas(qtbot)

    aktionen = {a.text(): a for a in canvas.kontextmenue_fuer(formular.b_ok).actions()}

    assert not aktionen["Früher in der Tab-Reihenfolge"].isEnabled()
    aktionen["Später in der Tab-Reihenfolge"].trigger()
    assert _reihenfolge(formular)[:2] == ["e_name", "b_ok"]
    aktionen["Tab-Reihenfolge nach Lage ordnen"].trigger()
    assert _reihenfolge(formular) == ["l_name", "e_name", "p_rand", "b_ok"]


def test_umbenennen_behaelt_die_stelle(qtbot) -> None:  # noqa: ANN001
    formular, canvas = _canvas(qtbot)

    canvas.komponente_umbenennen(formular.b_ok, "b_weiter")

    assert _reihenfolge(formular) == ["b_weiter", "e_name", "l_name", "p_rand"]
    canvas.rueckgaengig()
    assert _reihenfolge(formular) == ["b_ok", "e_name", "l_name", "p_rand"]
