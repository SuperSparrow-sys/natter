"""Tests für ide/run/starter.py: Programmausführung als eigener Prozess
(Abschnitt 7.8). Siehe docs/arbeitspakete/M2.md, „Ausführung in eigenen
Fenstern“.

Startet bewusst keine echten `pcl`-GUI-Projekte (deren Ereignisschleife
würde nie von selbst enden) - stattdessen kleine, sich selbst
beendende Skripte, um nur den Start-Mechanismus zu prüfen. Das
Konsolenfenster selbst (`CREATE_NEW_CONSOLE`) ist nur strukturell
geprüft (echtes Fenster erst auf dem Windows-Laptop verifizierbar, siehe
`prototypes/`).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from ide.project import Projekt
from ide.run import projekt_starten


def _projekt_schreiben(ordner: Path, typ: str, main_inhalt: str) -> Projekt:
    ordner.mkdir(parents=True, exist_ok=True)
    (ordner / "main.py").write_text(main_inhalt, encoding="utf-8")
    daten = {"format": "natter-project/1", "name": "Test", "type": typ, "main": "main.py"}
    natter_pfad = ordner / "test.natter"
    natter_pfad.write_text(json.dumps(daten), encoding="utf-8")
    return Projekt.laden(natter_pfad)


def test_gui_projekt_startet_im_projektordner_und_terminiert(tmp_path: Path) -> None:
    projekt = _projekt_schreiben(
        tmp_path,
        "gui",
        'from pathlib import Path\nPath("lief.txt").write_text("ja", encoding="utf-8")\n',
    )

    prozess = projekt_starten(projekt)
    returncode = prozess.wait(timeout=10)

    assert returncode == 0
    assert (tmp_path / "lief.txt").read_text(encoding="utf-8") == "ja"


def test_konsolenprojekt_bekommt_ein_eigenes_konsolenfenster_unter_windows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    projekt = _projekt_schreiben(tmp_path, "console", "pass\n")

    aufrufe = []

    class GefaelschterProzess:
        def wait(self, timeout=None):
            return 0

    def gefaelschtes_popen(*args, **kwargs):
        aufrufe.append((args, kwargs))
        return GefaelschterProzess()

    monkeypatch.setattr(subprocess, "Popen", gefaelschtes_popen)

    projekt_starten(projekt)

    assert len(aufrufe) == 1
    _, kwargs = aufrufe[0]
    if sys.platform == "win32":
        assert kwargs.get("creationflags") == subprocess.CREATE_NEW_CONSOLE
    else:
        assert "creationflags" not in kwargs


def test_gui_projekt_bekommt_kein_eigenes_konsolenfenster(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    projekt = _projekt_schreiben(tmp_path, "gui", "pass\n")

    aufrufe = []

    class GefaelschterProzess:
        def wait(self, timeout=None):
            return 0

    def gefaelschtes_popen(*args, **kwargs):
        aufrufe.append((args, kwargs))
        return GefaelschterProzess()

    monkeypatch.setattr(subprocess, "Popen", gefaelschtes_popen)

    projekt_starten(projekt)

    assert "creationflags" not in aufrufe[0][1]
