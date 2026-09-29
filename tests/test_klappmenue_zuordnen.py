"""Ein Klappmenü lässt sich im Designer zuordnen (offener Punkt 74).

`popup_menu` war eine reine Python-Eigenschaft: im Objektinspektor,
in der `.pfm` und im erzeugten Code kam sie nicht vor, und die
Zuordnung ging nur mit einer Zeile Code. Dazu verband jede weitere
Zuweisung das Qt-Signal noch einmal, sodass das Menü mehrfach
aufklappte.
"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QPoint

from ide.codegen.design import design_code_erzeugen
from ide.designer.canvas import DesignerCanvas
from ide.designer.laden import formular_fuer_designer_laden
from ide.inspector.eigenschaften_tabelle import KEIN_VERWEIS, EigenschaftenTabelle
from pcl import Button, Form, Label, PopupMenu, Timer

_PFM = {
    "format": "pfm/1",
    "class": "Form1",
    "type": "Form",
    "properties": {},
    "children": [
        {"name": "b_ziel", "type": "Button", "properties": {"popup_menu": "pm_knopf"}},
        {
            "name": "pm_knopf",
            "type": "PopupMenu",
            "properties": {"entries": [{"caption": "&Löschen"}]},
        },
    ],
}


def _zeile(tabelle: EigenschaftenTabelle, name: str) -> int | None:
    for zeile in range(tabelle.rowCount()):
        if tabelle.item(zeile, 0).text() == name:
            return zeile
    return None


class _Formular(Form):
    def create_components(self) -> None:
        self.b_ziel = Button(self)
        self.l_info = Label(self)
        self.pm_knopf = PopupMenu(self)
        self.pm_liste = PopupMenu(self)
        self.t_takt = Timer(self)


# ----------------------------------------------------- Laufzeit


def test_zweimal_zuweisen_klappt_einmal_auf(monkeypatch) -> None:
    """Die Ursache aus dem Punkt: `connect` bei jeder Zuweisung."""
    formular = _Formular()
    aufgeklappt: list[object] = []
    monkeypatch.setattr(
        PopupMenu, "aufklappen", lambda menue, k, x, y: aufgeklappt.append(k)
    )

    formular.b_ziel.popup_menu = formular.pm_knopf
    formular.b_ziel.popup_menu = None
    formular.b_ziel.popup_menu = formular.pm_knopf
    formular.b_ziel._qwidget.customContextMenuRequested.emit(QPoint(3, 4))

    assert aufgeklappt == [formular.b_ziel]


def test_nur_ein_klappmenue_laesst_sich_zuordnen() -> None:
    import pytest

    from pcl.errors import NatterPropertyError

    formular = _Formular()
    with pytest.raises(NatterPropertyError, match="erwartet ein PopupMenu"):
        formular.b_ziel.popup_menu = formular.l_info


# ------------------------------------------------ .pfm und Code


def test_der_code_ordnet_nach_allen_komponenten_zu() -> None:
    """In der `.pfm` steht der Knopf vor dem Menü. Die Zuordnung muss
    trotzdem erst kommen, wenn es das Menü schon gibt."""
    code = design_code_erzeugen(_PFM, "u_main.pfm")
    zeilen = [zeile.strip() for zeile in code.splitlines()]

    zuordnung = zeilen.index("self.b_ziel.popup_menu = self.pm_knopf")
    assert zuordnung > zeilen.index("self.pm_knopf = PopupMenu(self)")


def test_ein_unbekannter_name_wird_uebergangen() -> None:
    pfm = json.loads(json.dumps(_PFM))
    pfm["children"][0]["properties"]["popup_menu"] = "pm_gibtsnicht"

    code = design_code_erzeugen(pfm, "u_main.pfm")

    assert "popup_menu" not in code


def test_das_menue_erscheint_im_gestarteten_programm(tmp_path: Path) -> None:
    """Der erzeugte Code wird ausgeführt, wie beim Start des
    Schülerprogramms, und die rechte Maustaste klappt das Menü auf."""
    namensraum: dict = {}
    exec(design_code_erzeugen(_PFM, "u_main.pfm"), namensraum)
    formular = namensraum["Form1Design"]()

    assert formular.b_ziel.popup_menu is formular.pm_knopf
    menue = formular.pm_knopf.menue(formular.b_ziel._qwidget)
    assert [aktion.text() for aktion in menue.actions()] == ["&Löschen"]


def test_der_designer_speichert_die_zuordnung(tmp_path: Path) -> None:
    pfm_pfad = tmp_path / "u_main.pfm"
    pfm_pfad.write_text(json.dumps(_PFM), encoding="utf-8")
    canvas = DesignerCanvas(formular_fuer_designer_laden(pfm_pfad), pfm_pfad=pfm_pfad)
    formular = canvas.formular
    assert formular.b_ziel.popup_menu is formular.pm_knopf

    tabelle = EigenschaftenTabelle()
    tabelle.komponente_anzeigen(
        formular.b_ziel, bei_aenderung=canvas.eigenschaft_uebernehmen
    )
    tabelle.item(_zeile(tabelle, "popup_menu"), 1).setText(KEIN_VERWEIS)
    canvas.jetzt_schreiben()

    gespeichert = json.loads(pfm_pfad.read_text(encoding="utf-8"))
    assert "popup_menu" not in gespeichert["children"][0]["properties"]

    canvas.rueckgaengig()
    canvas.jetzt_schreiben()
    gespeichert = json.loads(pfm_pfad.read_text(encoding="utf-8"))
    assert gespeichert["children"][0]["properties"]["popup_menu"] == "pm_knopf"


# ------------------------------------------------- Objektinspektor


def test_die_auswahl_zeigt_die_klappmenues_des_formulars() -> None:
    formular = _Formular()
    tabelle = EigenschaftenTabelle()
    tabelle.komponente_anzeigen(formular.b_ziel)
    zeile = _zeile(tabelle, "popup_menu")
    index = tabelle.model().index(zeile, 1)

    auswahl = tabelle.itemDelegateForColumn(1).createEditor(
        tabelle.viewport(), None, index
    )

    assert [auswahl.itemText(i) for i in range(auswahl.count())] == [
        KEIN_VERWEIS,
        "pm_knopf",
        "pm_liste",
    ]
    assert tabelle.item(zeile, 1).text() == KEIN_VERWEIS


def test_die_auswahl_ordnet_zu() -> None:
    formular = _Formular()
    tabelle = EigenschaftenTabelle()
    tabelle.komponente_anzeigen(formular.b_ziel)
    zeile = _zeile(tabelle, "popup_menu")
    index = tabelle.model().index(zeile, 1)
    delegat = tabelle.itemDelegateForColumn(1)
    auswahl = delegat.createEditor(tabelle.viewport(), None, index)

    auswahl.setCurrentText("pm_liste")
    delegat.setModelData(auswahl, tabelle.model(), index)

    assert formular.b_ziel.popup_menu is formular.pm_liste
    assert tabelle.item(zeile, 1).text() == "pm_liste"


def test_ein_falscher_name_wird_abgelehnt() -> None:
    formular = _Formular()
    tabelle = EigenschaftenTabelle()
    tabelle.komponente_anzeigen(formular.b_ziel)

    tabelle.item(_zeile(tabelle, "popup_menu"), 1).setText("l_info")

    assert formular.b_ziel.popup_menu is None
    assert tabelle.fehlertext == "Auf dem Formular gibt es kein Klappmenü „l_info“."


def test_unsichtbare_komponenten_haben_keine_zeile() -> None:
    formular = _Formular()
    tabelle = EigenschaftenTabelle()

    for komponente in (formular.t_takt, formular.pm_knopf, formular):
        tabelle.komponente_anzeigen(komponente)
        assert _zeile(tabelle, "popup_menu") is None
