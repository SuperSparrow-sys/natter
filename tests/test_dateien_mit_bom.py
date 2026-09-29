"""Projekt-, Formular- und Diagrammdateien mit BOM (Punkt 280).

Der Editor von Windows 10 bis Version 1809 speichert UTF-8 immer mit
den drei Bytes BOM am Anfang, andere Editoren auf Wunsch. Gelesen
wurde mit `utf-8`, und `json.loads` scheiterte daran: eine
unveränderte `.natter` galt als beschädigt, die Meldung dazu zeigte
den englischen Text von `json`. Geschrieben wird weiter ohne BOM.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from ide.codegen.design import design_datei_erzeugen
from ide.designer.laden import formular_fuer_designer_laden
from ide.diagramm.datei import Diagramm
from ide.project import Projekt
from ide.schema import fehler_beschreiben, pruefen, schema_fehler

BOM = b"\xef\xbb\xbf"
BEISPIEL = (
    Path(__file__).resolve().parent.parent
    / "beispielprojekte"
    / "06_Kontoverwaltung"
)
DIAGRAMM = Path("diagramme") / "konto_klassen.pdiag"

#: Woran sich der Rohtext von `json` und `jsonschema` erkennen lässt.
ENGLISCH = ("Expecting", "line ", "column", "is a required property",
            "is not of type", "Unexpected", "char ")


def _bom_voranstellen(pfad: Path) -> None:
    pfad.write_bytes(BOM + pfad.read_bytes())


@pytest.fixture
def projekt_mit_bom(tmp_path: Path) -> Path:
    """Eine Kopie von `06_Kontoverwaltung`, in der `.natter`, `.pfm`
    und ein `.pdiag` mit BOM beginnen."""
    ordner = tmp_path / "06_Kontoverwaltung"
    shutil.copytree(BEISPIEL, ordner)
    for datei in (
        ordner / "06_Kontoverwaltung.natter",
        ordner / "u_main.pfm",
        ordner / DIAGRAMM,
    ):
        _bom_voranstellen(datei)
    return ordner


def test_ein_projekt_mit_bom_laesst_sich_laden(projekt_mit_bom: Path) -> None:
    projekt = Projekt.laden(projekt_mit_bom / "06_Kontoverwaltung.natter")

    assert projekt.name == "06_Kontoverwaltung"


def test_ein_formular_mit_bom_ergibt_die_design_datei(
    projekt_mit_bom: Path,
) -> None:
    ziel = projekt_mit_bom / "u_main_design.py"
    ziel.unlink()

    quelltext = design_datei_erzeugen(projekt_mit_bom / "u_main.pfm", ziel)

    assert "class " in quelltext
    assert ziel.read_bytes()[:3] != BOM


def test_ein_formular_mit_bom_geht_im_designer_auf(
    projekt_mit_bom: Path,
) -> None:
    formular = formular_fuer_designer_laden(projekt_mit_bom / "u_main.pfm")

    assert formular.caption


def test_ein_diagramm_mit_bom_laesst_sich_laden(projekt_mit_bom: Path) -> None:
    diagramm = Diagramm.laden(projekt_mit_bom / DIAGRAMM)

    assert diagramm.daten["format"].startswith("pdiag/")


def test_gespeichert_wird_ohne_bom(projekt_mit_bom: Path) -> None:
    natter = projekt_mit_bom / "06_Kontoverwaltung.natter"
    Projekt.laden(natter).speichern()
    diagramm = Diagramm.laden(projekt_mit_bom / DIAGRAMM)
    diagramm.speichern()

    assert natter.read_bytes()[:3] != BOM
    assert (projekt_mit_bom / DIAGRAMM).read_bytes()[:3] != BOM


def test_eine_wirklich_beschaedigte_datei_meldet_sich_deutsch(
    tmp_path: Path,
) -> None:
    kaputt = tmp_path / "kaputt.natter"
    kaputt.write_bytes(BOM + b'{"format": "natter-project/1",')
    with pytest.raises(json.JSONDecodeError) as json_fehler:
        Projekt.laden(kaputt)
    with pytest.raises(schema_fehler()) as schema:
        pruefen({"format": 1}, {"type": "object", "required": ["name"]})

    for fehler in (json_fehler.value, schema.value, KeyError("class")):
        text = fehler_beschreiben(fehler)
        assert text
        assert not any(wort in text for wort in ENGLISCH), text


def test_ein_projekt_mit_bom_oeffnet_ohne_meldung(
    hauptfenster, projekt_mit_bom: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Der Weg über „Projekt → Projekt öffnen …“: keine Warnung, und
    Designer und Diagramm-Editor gehen auf."""
    from PySide6.QtWidgets import QMessageBox

    gezeigt: list[str] = []
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        lambda _eltern, _titel, text, *_rest: gezeigt.append(text),
    )

    projekt = hauptfenster.projekt_oeffnen_gemeldet(
        projekt_mit_bom / "06_Kontoverwaltung.natter"
    )
    assert projekt is not None
    assert gezeigt == []

    hauptfenster.oeffnen(projekt_mit_bom / "u_main.pfm")
    assert "beschädigt" not in hauptfenster.statusBar().currentMessage()
    assert hauptfenster.editor_tabs.count() >= 1

    hauptfenster.oeffnen(projekt_mit_bom / DIAGRAMM)
    assert "beschädigt" not in hauptfenster.statusBar().currentMessage()


def test_ein_beschaedigtes_projekt_nennt_keinen_englischen_text(
    hauptfenster, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from PySide6.QtWidgets import QMessageBox

    gezeigt: list[str] = []
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        lambda _eltern, _titel, text, *_rest: gezeigt.append(text),
    )
    kaputt = tmp_path / "kaputt.natter"
    kaputt.write_text('{"format": "natter-project/1",', encoding="utf-8")

    assert hauptfenster.projekt_oeffnen_gemeldet(kaputt) is None
    assert "beschädigt" in gezeigt[0]
    assert not any(wort in gezeigt[0] for wort in ENGLISCH), gezeigt[0]
