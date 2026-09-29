"""Tests für ide/diagramm/datei.py und ide/diagramm/neu.py: `.pdiag`
laden/speichern/anlegen (M9, Schritt 1). Reine Dateilogik, kein Qt.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from ide.diagramm import Diagramm, diagramm_erzeugen, leeres_diagramm
from ide.diagramm.neu import MVP_TYPEN


@pytest.mark.parametrize("typ", MVP_TYPEN)
def test_neues_diagramm_ist_schemagueltig_und_laedt_wieder(typ: str, tmp_path: Path) -> None:
    pfad = tmp_path / f"{typ}.pdiag"

    erzeugt = diagramm_erzeugen(typ, pfad, "Testdiagramm")
    geladen = Diagramm.laden(pfad)

    assert erzeugt.typ == typ
    assert geladen.typ == typ
    assert geladen.name == "Testdiagramm"
    assert geladen.daten == erzeugt.daten


def test_klassendiagramm_startet_mit_leeren_formen_und_verbindungen(tmp_path: Path) -> None:
    diagramm = diagramm_erzeugen("class", tmp_path / "k.pdiag")

    assert diagramm.hat_formen is True
    assert diagramm.daten["shapes"] == []
    assert diagramm.daten["connectors"] == []


def test_struktogramm_startet_mit_leerem_wurzelblock_im_hochformat(tmp_path: Path) -> None:
    """Struktogramme wachsen nach unten (Abschnitt 13.5), deshalb
    Hochformat statt des sonstigen Querformats."""
    diagramm = diagramm_erzeugen("struktogramm", tmp_path / "s.pdiag")

    assert diagramm.hat_formen is False
    assert diagramm.daten["root"] == {"id": "root", "kind": "sequence", "children": []}
    assert diagramm.daten["page"]["orientation"] == "portrait"


def test_entscheidungstabelle_startet_mit_je_einer_zeile_und_regel(tmp_path: Path) -> None:
    diagramm = diagramm_erzeugen("entscheidungstabelle", tmp_path / "e.pdiag")

    assert diagramm.daten["conditions"] == [{"text": "", "values": [""]}]
    assert diagramm.daten["actions"] == [{"text": "", "values": [""]}]


def test_speichern_und_erneutes_laden_erhaelt_aenderungen(tmp_path: Path) -> None:
    pfad = tmp_path / "k.pdiag"
    diagramm = diagramm_erzeugen("class", pfad)

    diagramm.daten["shapes"].append(
        {"id": "s1", "kind": "class", "x": 96, "y": 64, "w": 184, "h": 136,
         "text": {"name": "TAmpel", "attributes": ["-an: bool"], "methods": ["+ein()"]}}
    )
    diagramm.speichern()

    # Seit M9 Schritt 12 wird die alte Textform beim Laden einmalig
    # in die strukturierte Form umgerechnet.
    geladen = Diagramm.laden(pfad).daten["shapes"][0]
    assert geladen["name"] == "TAmpel"
    assert geladen["attributes"][0]["name"] == "an"
    assert geladen["operations"][0]["name"] == "ein"


def test_speichern_unter_schreibt_an_den_neuen_pfad(tmp_path: Path) -> None:
    diagramm = diagramm_erzeugen("class", tmp_path / "alt.pdiag")
    neuer_pfad = tmp_path / "unterordner" / "neu.pdiag"

    diagramm.speichern(neuer_pfad)

    assert neuer_pfad.exists()
    assert diagramm.pfad == neuer_pfad


def test_ungueltige_datei_wird_beim_laden_abgelehnt(tmp_path: Path) -> None:
    pfad = tmp_path / "kaputt.pdiag"
    # gültiges JSON, aber fehlende Pflichtfelder (page/style)
    pfad.write_text(json.dumps({"format": "pdiag/1", "type": "class"}), encoding="utf-8")

    with pytest.raises(jsonschema.ValidationError):
        Diagramm.laden(pfad)


def test_struktogramm_ohne_wurzelblock_wird_abgelehnt(tmp_path: Path) -> None:
    """Das Schema verlangt `root` nur für Struktogramme (if/then) -
    genau diese typabhängige Pflicht wird hier geprüft."""
    pfad = tmp_path / "ohne_root.pdiag"
    daten = leeres_diagramm("struktogramm", "x")
    del daten["root"]
    pfad.write_text(json.dumps(daten), encoding="utf-8")

    with pytest.raises(jsonschema.ValidationError):
        Diagramm.laden(pfad)


def test_name_faellt_auf_den_dateinamen_zurueck(tmp_path: Path) -> None:
    pfad = tmp_path / "ampel_klassen.pdiag"
    daten = leeres_diagramm("class", "x")
    del daten["name"]
    pfad.write_text(json.dumps(daten), encoding="utf-8")

    assert Diagramm.laden(pfad).name == "ampel_klassen"


def test_vorhandene_datei_wird_nicht_ueberschrieben(tmp_path: Path) -> None:
    pfad = tmp_path / "k.pdiag"
    diagramm_erzeugen("class", pfad)

    with pytest.raises(FileExistsError):
        diagramm_erzeugen("struktogramm", pfad)


def test_unbekannter_typ_wird_abgelehnt() -> None:
    with pytest.raises(ValueError, match="Unbekannter Diagrammtyp"):
        leeres_diagramm("gibt_es_nicht", "x")
