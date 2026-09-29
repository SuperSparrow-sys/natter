"""Ein im Designer gesetztes Bild bleibt erhalten (offener Punkt 57).

`Image.picture` stand weder in der `.pfm` noch im erzeugten Code. Ein
Bild, das jemand in den Designer zog, war nach dem Speichern weg und
erschien im gestarteten Programm nie.

Alle Tests arbeiten in `tmp_path`, nie an einem Beispielprojekt.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

import ide.inspector.eigenschaften_tabelle as tabellen_modul
from ide.codegen.design import design_code_erzeugen, design_datei_erzeugen
from ide.designer.canvas import DesignerCanvas
from ide.designer.laden import formular_fuer_designer_laden
from ide.inspector.eigenschaften_tabelle import EigenschaftenTabelle, _WertMitKnopf
from pcl.properties import wert_lesen

_PFM = {
    "format": "pfm/1",
    "class": "Form1",
    "type": "Form",
    "properties": {"width": 300, "height": 200},
}

_WURZEL = Path(__file__).resolve().parents[1]


def _bild(pfad: Path) -> Path:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pixmap = QPixmap(40, 20)
    pixmap.fill(Qt.GlobalColor.blue)
    assert pixmap.save(str(pfad))
    return pfad


def _projekt(tmp_path: Path) -> Path:
    projekt = tmp_path / "projekt"
    projekt.mkdir()
    (projekt / "u_main.pfm").write_text(json.dumps(_PFM), encoding="utf-8")
    (projekt / "u_main.py").write_text(
        "from u_main_design import Form1Design\n\n\n"
        "class Form1(Form1Design):\n    pass\n",
        encoding="utf-8",
    )
    return projekt


def _canvas(projekt: Path) -> DesignerCanvas:
    pfm_pfad = projekt / "u_main.pfm"
    return DesignerCanvas(formular_fuer_designer_laden(pfm_pfad), pfm_pfad=pfm_pfad)


def test_abgelegtes_bild_steht_relativ_in_pfm_und_code(tmp_path: Path) -> None:
    projekt = _projekt(tmp_path)
    canvas = _canvas(projekt)

    canvas.bild_ablegen(_bild(tmp_path / "extern" / "keks.png"), 20, 20)
    canvas.jetzt_schreiben()

    pfm = json.loads((projekt / "u_main.pfm").read_text(encoding="utf-8"))
    bild = pfm["children"][0]
    assert bild["type"] == "Image"
    assert bild["properties"]["picture"] == "assets/keks.png"
    code = design_code_erzeugen(pfm, "u_main.pfm")
    assert f'self.{bild["name"]}.picture.file = "assets/keks.png"' in code


def test_nach_dem_wiederoeffnen_ist_das_bild_da(tmp_path: Path) -> None:
    projekt = _projekt(tmp_path)
    canvas = _canvas(projekt)
    bild = canvas.bild_ablegen(_bild(tmp_path / "extern" / "keks.png"), 20, 20)
    name = canvas.name_von(bild)
    canvas.jetzt_schreiben()

    wieder = formular_fuer_designer_laden(projekt / "u_main.pfm")

    komponente = getattr(wieder, name)
    assert komponente.picture.file == "assets/keks.png"
    assert not komponente.picture.original.isNull()


def test_das_gestartete_programm_zeigt_das_bild(tmp_path: Path) -> None:
    """Der eigentliche Punkt. Gestartet wird aus einem anderen Ordner
    als dem Projektordner, wie bei einem Doppelklick auf `main.py`
    aus dem Explorer heraus."""
    projekt = _projekt(tmp_path)
    canvas = _canvas(projekt)
    bild = canvas.bild_ablegen(_bild(tmp_path / "extern" / "keks.png"), 20, 20)
    name = canvas.name_von(bild)
    canvas.jetzt_schreiben()
    design_datei_erzeugen(projekt / "u_main.pfm", projekt / "u_main_design.py")
    (projekt / "pruefen.py").write_text(
        "from PySide6.QtWidgets import QApplication\n"
        "app = QApplication([])\n"
        "from u_main import Form1\n"
        "f = Form1()\n"
        f"print(f.{name}.picture.original.isNull())\n",
        encoding="utf-8",
    )
    umgebung = dict(os.environ)
    umgebung["QT_QPA_PLATFORM"] = "offscreen"
    umgebung["PYTHONPATH"] = str(_WURZEL)

    ergebnis = subprocess.run(
        [sys.executable, str(projekt / "pruefen.py")],
        cwd=tmp_path,
        env=umgebung,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert ergebnis.returncode == 0, ergebnis.stderr
    assert ergebnis.stdout.strip() == "False"


# ------------------------------------------------------ Objektinspektor


def _tabelle_mit_bild(tmp_path: Path):
    projekt = _projekt(tmp_path)
    canvas = _canvas(projekt)
    bild = canvas.bild_ablegen(_bild(tmp_path / "extern" / "keks.png"), 20, 20)
    tabelle = EigenschaftenTabelle()
    tabelle.komponente_anzeigen(bild, bei_aenderung=canvas.eigenschaft_uebernehmen)
    zeile = next(
        z for z in range(tabelle.rowCount()) if tabelle.item(z, 0).text() == "picture"
    )
    return projekt, bild, tabelle, zeile, canvas


def test_die_zeile_picture_hat_einen_dateiknopf(tmp_path: Path) -> None:
    _, _, tabelle, zeile, _ = _tabelle_mit_bild(tmp_path)
    index = tabelle.model().index(zeile, 1)

    editor = tabelle.itemDelegateForColumn(1).createEditor(
        tabelle.viewport(), None, index
    )

    assert isinstance(editor, _WertMitKnopf)
    assert tabelle.item(zeile, 1).text() == "assets/keks.png"


def test_die_dateiauswahl_kopiert_nach_assets(tmp_path: Path, monkeypatch) -> None:
    projekt, bild, tabelle, zeile, canvas = _tabelle_mit_bild(tmp_path)
    neu = _bild(tmp_path / "anderswo" / "stern.png")
    monkeypatch.setattr(tabellen_modul, "bilddatei_erfragen", lambda *_: str(neu))
    index = tabelle.model().index(zeile, 1)
    editor = tabelle.itemDelegateForColumn(1).createEditor(
        tabelle.viewport(), None, index
    )

    editor.dialog_oeffnen()
    tabelle.itemDelegateForColumn(1).setModelData(editor, tabelle.model(), index)

    assert (projekt / "assets" / "stern.png").is_file()
    assert wert_lesen(bild, "picture") == "assets/stern.png"
    canvas.jetzt_schreiben()
    pfm = json.loads((projekt / "u_main.pfm").read_text(encoding="utf-8"))
    assert pfm["children"][0]["properties"]["picture"] == "assets/stern.png"


def test_eine_fehlende_datei_wird_abgelehnt(tmp_path: Path) -> None:
    _, bild, tabelle, zeile, _ = _tabelle_mit_bild(tmp_path)
    gemeldet: list[str] = []
    tabelle.fehlertext_geaendert.connect(gemeldet.append)

    tabelle.item(zeile, 1).setText("assets/gibtsnicht.png")

    assert bild.picture.file == "assets/keks.png"
    assert tabelle.item(zeile, 1).text() == "assets/keks.png"
    assert gemeldet == ["Die Bilddatei „assets/gibtsnicht.png“ gibt es nicht."]


def test_leer_entfernt_das_bild(tmp_path: Path) -> None:
    _, bild, tabelle, zeile, _ = _tabelle_mit_bild(tmp_path)

    tabelle.item(zeile, 1).setText("")

    assert bild.picture.file == ""
    assert bild.picture.original.isNull()
