"""Tests für ide/project/neu.py: „Neues Projekt …“ (Abschnitt 7.5). Siehe
Arbeitspaket M2, Schritt 4.
"""

import sys
from pathlib import Path

import pytest

from ide.project import projekt_erzeugen


def test_unbekannte_vorlage_wird_abgelehnt(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        projekt_erzeugen("web", tmp_path / "Test", "Test")


def test_nicht_leerer_zielordner_wird_abgelehnt(tmp_path: Path) -> None:
    ziel = tmp_path / "Test"
    ziel.mkdir()
    (ziel / "vorhanden.txt").write_text("x", encoding="utf-8")
    with pytest.raises(FileExistsError):
        projekt_erzeugen("gui", ziel, "Test")


def test_gui_projekt_erzeugt_alle_dateien(tmp_path: Path) -> None:
    ziel = tmp_path / "MeinProjekt"
    projekt = projekt_erzeugen("gui", ziel, "MeinProjekt")

    assert projekt.name == "MeinProjekt"
    assert projekt.typ == "gui"
    for dateiname in (
        "MeinProjekt.natter",
        "main.py",
        "u_main.pfm",
        "u_main_design.py",
        "u_main.py",
    ):
        assert (ziel / dateiname).exists(), dateiname


def test_gui_projekt_laesst_sich_starten_und_zeigt_den_namen(tmp_path: Path) -> None:
    ziel = tmp_path / "MeinProjekt"
    projekt_erzeugen("gui", ziel, "MeinProjekt")

    sys.path.insert(0, str(ziel))
    for modul in ("u_main", "u_main_design"):
        sys.modules.pop(modul, None)
    try:
        from u_main import Form1

        formular = Form1()
        assert formular.caption == "MeinProjekt"
    finally:
        sys.path.remove(str(ziel))
        for modul in ("u_main", "u_main_design"):
            sys.modules.pop(modul, None)


def test_console_projekt_erzeugt_main_und_natter_datei(tmp_path: Path) -> None:
    ziel = tmp_path / "KonsolenTest"
    projekt = projekt_erzeugen("console", ziel, "KonsolenTest")

    assert projekt.typ == "console"
    assert (ziel / "KonsolenTest.natter").exists()
    # Der Begruessungstext steht in `u_main.py`, nicht in `main.py`:
    # dort steht der Code der Schülerin (Nutzer,
    # "Jedes Projekt braucht eine Main um zu starten und eine u_main wo
    # der Schüler Code drin steht"). Bis dahin trug ein
    # Konsolenprojekt seinen ganzen Inhalt in der Startdatei.
    assert "KonsolenTest" in (ziel / "u_main.py").read_text(encoding="utf-8")
    assert "KonsolenTest" not in (ziel / "main.py").read_text(encoding="utf-8")
    # kein Formular bei einem Konsolenprojekt
    assert not (ziel / "u_main.pfm").exists()


def test_console_projekt_startet_wirklich(tmp_path: Path) -> None:
    """Der Import in `main.py` muss `u_main.py` auch tatsächlich
    ausführen - sonst startet ein frisches Konsolenprojekt stumm."""
    import subprocess
    import sys

    ziel = tmp_path / "Start"
    projekt_erzeugen("console", ziel, "Start")

    lauf = subprocess.run(
        [sys.executable, "main.py"],
        cwd=ziel,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert lauf.returncode == 0, lauf.stderr
    assert "Hallo, Start!" in lauf.stdout
