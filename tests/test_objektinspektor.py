"""Tests für ide/inspector/objektinspektor.py: Objektinspektor
(Komponentenbaum + Eigenschaften-/Ereignisse-Reiter). Headless. Siehe
Arbeitspaket M3, Schritt 2.
"""

import json
from pathlib import Path

from ide.designer.canvas import DesignerCanvas
from ide.designer.laden import formular_fuer_designer_laden
from ide.inspector import Objektinspektor
from pcl import Button, Form

_PFM_MIT_BUTTON = {
    "format": "pfm/1",
    "class": "Form1",
    "type": "Form",
    "properties": {"caption": "Test", "width": 300, "height": 200},
    "children": [
        {
            "name": "b_anmelden",
            "type": "Button",
            "properties": {
                "caption": "Anmelden",
                "left": 10,
                "top": 10,
                "width": 75,
                "height": 25,
            },
        }
    ],
}


class _Formular(Form):
    def create_components(self) -> None:
        self.b_ein = Button(self)

    def b_ein_click(self, sender) -> None:
        pass


def test_formular_anzeigen_waehlt_die_wurzel_automatisch_aus() -> None:
    formular = _Formular()
    inspektor = Objektinspektor()

    inspektor.formular_anzeigen(formular)

    eigenschaften_namen = [
        inspektor.eigenschaften_tabelle.item(z, 0).text()
        for z in range(inspektor.eigenschaften_tabelle.rowCount())
    ]
    assert "caption" in eigenschaften_namen  # Form-Eigenschaft


def test_auswahlwechsel_im_baum_aktualisiert_beide_reiter() -> None:
    formular = _Formular()
    inspektor = Objektinspektor()
    inspektor.formular_anzeigen(formular)

    knopf_element = inspektor.baum.topLevelItem(0).child(0)
    inspektor.baum.setCurrentItem(knopf_element)

    eigenschaften_namen = [
        inspektor.eigenschaften_tabelle.item(z, 0).text()
        for z in range(inspektor.eigenschaften_tabelle.rowCount())
    ]
    assert "caption" in eigenschaften_namen
    assert "checked" not in eigenschaften_namen  # Button hat kein checked

    ereignis_namen = [
        inspektor.ereignisse_tabelle.item(z, 0).text()
        for z in range(inspektor.ereignisse_tabelle.rowCount())
    ]
    # Seit M15 stehen dort die fünf Maus-Ereignisse aus `Control`.
    assert "on_click" in ereignis_namen
    assert "on_mouse_down" in ereignis_namen


def test_eigenschaft_ueber_den_inspektor_aendern_wirkt_auf_die_komponente() -> None:
    formular = _Formular()
    inspektor = Objektinspektor()
    inspektor.formular_anzeigen(formular)

    knopf_element = inspektor.baum.topLevelItem(0).child(0)
    inspektor.baum.setCurrentItem(knopf_element)

    tabelle = inspektor.eigenschaften_tabelle
    for zeile in range(tabelle.rowCount()):
        if tabelle.item(zeile, 0).text() == "caption":
            tabelle.item(zeile, 1).setText("Einschalten")
            break

    assert formular.b_ein.caption == "Einschalten"
    assert formular.b_ein._qwidget.text() == "Einschalten"


def test_ohne_designer_canvas_fehlt_die_name_zeile() -> None:
    """Ohne `DesignerCanvas` (z. B. `formular_anzeigen(formular)` ohne
    zweites Argument) gibt es nichts umzubenennen - die Zeile „name“
    bleibt weg statt eine kaputte Umbenennen-Aktion vorzutäuschen."""
    formular = _Formular()
    inspektor = Objektinspektor()
    inspektor.formular_anzeigen(formular)

    knopf_element = inspektor.baum.topLevelItem(0).child(0)
    inspektor.baum.setCurrentItem(knopf_element)

    namen = [
        inspektor.eigenschaften_tabelle.item(z, 0).text()
        for z in range(inspektor.eigenschaften_tabelle.rowCount())
    ]
    assert "name" not in namen


def test_name_zeile_zeigt_den_bezeichner_und_erlaubt_umbenennen(tmp_path: Path) -> None:
    """Gemeldet: „caption und name sind
 unterschiedlich und der name also b_anmelden muss auch vom Nutzer
 frei veränderbar sein." Umbenennen läuft über
 `DesignerCanvas.komponente_umbenennen` (Undo, `.pfm`-Aktualisierung),
 genau wie ein Umbenennen über die Tastatur/ein Kommando im Designer
 selbst."""
    pfm_pfad = tmp_path / "u_main.pfm"
    pfm_pfad.write_text(json.dumps(_PFM_MIT_BUTTON), encoding="utf-8")
    formular = formular_fuer_designer_laden(pfm_pfad)
    canvas = DesignerCanvas(formular, pfm_pfad=pfm_pfad)

    inspektor = Objektinspektor()
    inspektor.formular_anzeigen(formular, canvas)
    inspektor.baum.setCurrentItem(inspektor.baum.topLevelItem(0).child(0))

    tabelle = inspektor.eigenschaften_tabelle
    assert tabelle.item(0, 0).text() == "name"
    assert tabelle.item(0, 1).text() == "b_anmelden"
    # caption bleibt unabhängig vom Namen (Anzeigetext vs. Bezeichner)
    assert tabelle.item(1, 0).text() == "caption"
    assert tabelle.item(1, 1).text() == "Anmelden"

    tabelle.item(0, 1).setText("b_login")

    assert hasattr(formular, "b_login")
    assert not hasattr(formular, "b_anmelden")
    assert formular.b_login.caption == "Anmelden"


def test_name_zeile_lehnt_ungueltigen_bezeichner_ab_und_setzt_zurueck(
    tmp_path: Path,
) -> None:
    pfm_pfad = tmp_path / "u_main.pfm"
    pfm_pfad.write_text(json.dumps(_PFM_MIT_BUTTON), encoding="utf-8")
    formular = formular_fuer_designer_laden(pfm_pfad)
    canvas = DesignerCanvas(formular, pfm_pfad=pfm_pfad)

    inspektor = Objektinspektor()
    inspektor.formular_anzeigen(formular, canvas)
    inspektor.baum.setCurrentItem(inspektor.baum.topLevelItem(0).child(0))

    tabelle = inspektor.eigenschaften_tabelle
    tabelle.item(0, 1).setText("123 ungültig")

    assert tabelle.item(0, 1).text() == "b_anmelden"
    assert "kein gültiger Bezeichner" in tabelle.fehlertext
    assert hasattr(formular, "b_anmelden")
