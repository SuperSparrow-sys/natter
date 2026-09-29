"""„Datei → Neues Formular …“ (Punkt 58).

Ein Projekt konnte mehrere Formulare haben, anlegen ließ sich aber nur
eine Unit; ein zweites Formular kam nur über den Import einer `.lfm`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from ide.project.neu import projekt_erzeugen
from ide.shell.hauptfenster import HauptFenster


@pytest.fixture
def fenster(hauptfenster_bauen, tmp_path: Path) -> HauptFenster:
    projekt = projekt_erzeugen("gui", tmp_path / "Rechner", "Rechner")
    fenster = hauptfenster_bauen()
    fenster.projekt_oeffnen(next(projekt.ordner.glob("*.natter")))
    return fenster


def test_neues_formular_legt_drei_dateien_an(fenster: HauptFenster) -> None:
    ordner = fenster.projekt.ordner

    pfm = fenster.formular_erzeugen("u_einstellungen")

    assert pfm == ordner / "u_einstellungen.pfm"
    assert json.loads(pfm.read_text(encoding="utf-8"))["class"] == "Form2"
    assert "class Form2(Form2Design):" in (ordner / "u_einstellungen.py").read_text(
        encoding="utf-8"
    )
    assert "class Form2Design" in (ordner / "u_einstellungen_design.py").read_text(
        encoding="utf-8"
    )
    assert pfm in fenster.projekt.formulare()
    reiter = [fenster.editor_tabs.tabText(i) for i in range(fenster.editor_tabs.count())]
    assert "u_einstellungen (Designer)" in reiter


def test_das_naechste_formular_bekommt_die_naechste_nummer(fenster: HauptFenster) -> None:
    fenster.formular_erzeugen("u_form2")

    assert fenster._naechster_formularname() == ("u_form3", "Form3")


@pytest.mark.parametrize("name", ["einstellungen", "u-zwei", "u_main", "u ab"])
def test_ungeeignete_namen_werden_abgelehnt(fenster: HauptFenster, name: str) -> None:
    with pytest.raises((ValueError, FileExistsError)):
        fenster.formular_erzeugen(name)


def test_konsolenprojekt_bekommt_kein_formular(
    qtbot, tmp_path: Path, hauptfenster_bauen
) -> None:  # noqa: ANN001
    projekt = projekt_erzeugen("console", tmp_path / "K", "K")
    fenster = hauptfenster_bauen()
    fenster.projekt_oeffnen(next(projekt.ordner.glob("*.natter")))

    fenster._neues_formular_aktion()

    assert "Konsolenprogramm" in fenster.statusBar().currentMessage()
    assert fenster.projekt.formulare() == []


def test_das_neue_formular_laesst_sich_im_programm_oeffnen(fenster: HauptFenster) -> None:
    fenster.formular_erzeugen("u_einstellungen")
    skript = (
        "from pcl import Application\n"
        "app = Application()\n"
        "from u_einstellungen import Form2\n"
        "f = Form2()\n"
        "f.show()\n"
        "print(f.caption, f._qwidget.isVisible())\n"
    )
    umgebung = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}

    lauf = subprocess.run(
        [sys.executable, "-c", skript],
        cwd=fenster.projekt.ordner,
        capture_output=True,
        text=True,
        timeout=120,
        env=umgebung,
        check=False,
    )

    assert lauf.returncode == 0, lauf.stderr
    assert lauf.stdout.strip() == "Form2 True"


def _python_und_formulare(ordner: Path) -> dict[str, bytes]:
    return {
        p.name: p.read_bytes()
        for p in ordner.iterdir()
        if p.suffix in (".py", ".pfm")
    }


@pytest.mark.parametrize("name", ["u_Main", "u_MAIN", "u_Main.py"])
def test_ein_name_in_anderer_schreibweise_ueberschreibt_nichts(
    fenster: HauptFenster, name: str
) -> None:
    # Punkt 184: Windows unterscheidet in Dateinamen nicht zwischen
    # Groß- und Kleinschreibung, „u_Main“ traf u_main.py.
    ordner = fenster.projekt.ordner
    vorher = _python_und_formulare(ordner)
    assert "u_main.py" in vorher

    with pytest.raises(FileExistsError):
        fenster.formular_erzeugen(name)

    assert _python_und_formulare(ordner) == vorher
