"""Tests für Sammlungs-Eigenschaften (`items`/`lines`) und die
Schrift-Untereigenschaft (`font`) über die ganze `.pfm`-Pipeline.

Siehe docs/arbeitspakete/M8.md, Schritt 6. Beide Lücken blockierten die
M8-Abnahme: `Items.Strings`/`Lines.Strings` aus einer `.lfm` liessen sich
gar nicht abbilden, und `Font.Size` (das f_Pizza über eine ScrollBar
steuert) gab es in `pcl` nicht.
"""

import json
from pathlib import Path

import pytest

from ide.codegen.design import design_code_erzeugen
from ide.designer import formular_fuer_designer_laden
from ide.designer.pfm_schreiben import pfm_aus_formular
from ide.import_lfm.parser import parse_lfm
from ide.import_lfm.zuordnung import lfm_zu_pfm
from pcl import ComboBox, Form, Label, ListBox, Memo
from pcl.errors import NatterPropertyError, NatterUnbekannteEigenschaftError

_F_PIZZA_LFM = (
    Path(__file__).resolve().parent.parent / "referenz" / "lazarus" / "f_Pizza" / "unit1.lfm"
)


class _TestForm(Form):
    def create_components(self):
        self.lb = ListBox(self)
        self.cb = ComboBox(self)
        self.m = Memo(self)
        self.l = Label(self)


def _formular() -> _TestForm:
    return _TestForm()


# -- pcl: Sammlungen als Ganzes zuweisbar ---------------------------------


def test_items_lassen_sich_als_liste_zuweisen() -> None:
    formular = _formular()
    formular.lb.items = ["Hawaii", "Napoli"]

    assert list(formular.lb.items) == ["Hawaii", "Napoli"]
    assert formular.lb._qwidget.count() == 2


def test_lines_zuweisen_ersetzt_den_bisherigen_inhalt() -> None:
    formular = _formular()
    formular.m.lines.add("alt")

    formular.m.lines = ["neu"]

    assert list(formular.m.lines) == ["neu"]
    assert formular.m._qwidget.toPlainText() == "neu"


def test_nicht_zeichenketten_in_einer_sammlung_werden_abgelehnt() -> None:
    formular = _formular()
    with pytest.raises(NatterPropertyError):
        formular.lb.items = ["ok", 5]


def test_tippfehler_bleibt_trotz_property_setter_gesperrt() -> None:
    """Die Sperre gegen unbekannte Eigenschaften darf durch die neuen
    `property`-Setter nicht aufgeweicht werden."""
    formular = _formular()
    with pytest.raises(NatterUnbekannteEigenschaftError):
        formular.lb.itens = ["x"]


# -- pcl: Schrift ---------------------------------------------------------


def test_schriftgroesse_wirkt_ueber_qss_statt_setfont() -> None:
    """Das Theme setzt `font-size` per QSS auf dem Formular; ein
    `setFont()` auf der Komponente bliebe dagegen wirkungslos."""
    formular = _formular()
    formular.l.font.size = 24

    assert "font-size: 24pt;" in formular.l._qwidget.styleSheet()


def test_schrift_und_hintergrundfarbe_loeschen_sich_nicht_gegenseitig() -> None:
    formular = _formular()
    formular.l.transparent = False
    formular.l.color = "#ffff00"
    formular.l.font.bold = True

    stil = formular.l._qwidget.styleSheet()
    assert "background-color: #ffff00;" in stil
    assert "font-weight: bold;" in stil


def test_unveraenderte_schrift_erzeugt_kein_eigenes_stylesheet() -> None:
    formular = _formular()
    assert formular.l._qwidget.styleSheet() == ""


def test_falscher_typ_bei_schriftgroesse_wird_abgelehnt() -> None:
    formular = _formular()
    with pytest.raises(NatterPropertyError):
        formular.l.font.size = "gross"


# -- .pfm-Pipeline --------------------------------------------------------


def test_pfm_enthaelt_sammlungen_und_schrift() -> None:
    formular = _formular()
    formular.cb.items = ["7", "19"]
    formular.l.font.size = 24
    formular.l.font.bold = True

    pfm = pfm_aus_formular(formular)
    nach_name = {kind["name"]: kind["properties"] for kind in pfm["children"]}

    assert nach_name["cb"]["items"] == ["7", "19"]
    assert nach_name["l"]["font_size"] == 24
    assert nach_name["l"]["font_bold"] is True
    # leere Sammlungen und Standardschrift bleiben weg (Abschnitt 4.2)
    assert "items" not in nach_name["lb"]
    assert "font_size" not in nach_name["cb"]


def test_erzeugter_code_setzt_sammlung_und_schrift() -> None:
    pfm = {
        "format": "pfm/1",
        "class": "TForm1",
        "type": "Form",
        "properties": {},
        "children": [
            {
                "name": "cb",
                "type": "ComboBox",
                "properties": {"items": ["7", "19"], "font_size": 12},
            }
        ],
    }

    quelltext = design_code_erzeugen(pfm, "u_main.pfm")

    assert 'self.cb.items = ["7", "19"]' in quelltext
    assert "self.cb.font.size = 12" in quelltext


def test_rundreise_ueber_datei_erhaelt_sammlung_und_schrift(tmp_path: Path) -> None:
    """Der eigentliche Zweck: was im Designer steht, muss auch nach dem
    Speichern und erneuten Laden noch da sein."""
    formular = _formular()
    formular.cb.items = ["7", "19"]
    formular.m.lines = ["Zeile 1", "Zeile 2"]
    formular.l.font.size = 24

    pfad = tmp_path / "u_main.pfm"
    pfad.write_text(json.dumps(pfm_aus_formular(formular)), encoding="utf-8")
    geladen = formular_fuer_designer_laden(pfad)

    assert list(geladen.cb.items) == ["7", "19"]
    assert list(geladen.m.lines) == ["Zeile 1", "Zeile 2"]
    assert geladen.l.font.size == 24


# -- Lazarus-Import -------------------------------------------------------


def test_import_uebernimmt_items_schrift_und_scrollbar_grenzen() -> None:
    """Gegen das echte `f_Pizza`-Formular: `Items.Strings`, `Font.Height`/
    `Font.Style` und die ScrollBar-Grenzen (`Min`/`Max`/`Position`), die
    das Projekt zum Steuern der Schriftgröße braucht."""
    ergebnis = lfm_zu_pfm(parse_lfm(_F_PIZZA_LFM.read_text(encoding="utf-8")))
    nach_name = {kind["name"]: kind["properties"] for kind in ergebnis.pfm["children"]}

    assert nach_name["cb_mws"]["items"] == ["7", "19"]
    # Lazarus' Font.Height = -32 ist eine Pixelhöhe, pcl rechnet in Punkt
    assert nach_name["l_Kassenzettel"]["font_size"] == 24
    assert nach_name["l_Kassenzettel"]["font_name"] == "Bodoni MT"
    assert nach_name["l_Kassenzettel"]["font_bold"] is True
    assert nach_name["sb_behinderung"]["minimum"] == 5
    assert nach_name["sb_behinderung"]["maximum"] == 50
    assert nach_name["sb_behinderung"]["position"] == 5


def test_import_meldet_container_statt_ihn_stillschweigend_zu_verlieren() -> None:
    ergebnis = lfm_zu_pfm(parse_lfm(_F_PIZZA_LFM.read_text(encoding="utf-8")))

    assert any("TRadioGroup" in warnung for warnung in ergebnis.warnungen)


def test_schrift_am_formular_wird_gemeldet_statt_ungueltigen_code_zu_erzeugen() -> None:
    """`Form` hat keine `font`-Untereigenschaft; ohne die Ausnahme im
    Importer entstand ein `self.font.name = ...`, das beim Laden bricht."""
    lfm = "object Form1: TForm1\n  Font.Name = 'Arial'\nend\n"

    ergebnis = lfm_zu_pfm(parse_lfm(lfm))

    assert "font_name" not in ergebnis.pfm["properties"]
    assert any("Font.Name" in warnung for warnung in ergebnis.warnungen)
