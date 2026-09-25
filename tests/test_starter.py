"""Tests für ide/run/starter.py: Programmausführung als eigener Prozess
(Abschnitt 7.8). Siehe Arbeitspaket M2, „Ausführung in eigenen
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
    args, kwargs = aufrufe[0]
    if sys.platform == "win32":
        assert kwargs.get("creationflags") == subprocess.CREATE_NEW_CONSOLE
    else:
        assert "creationflags" not in kwargs
    # Konsolenprogramme laufen durch die Hülle, die das Fenster offen
    # hält und ihm einen lesbaren Titel gibt
    assert "-c" in args[0]
    assert args[0][-1] == "main.py"
    assert args[0][-2].startswith("Natter")


def _huelle_ausfuehren(ordner: Path, inhalt: str) -> subprocess.CompletedProcess:
    """Führt die Hülle für Konsolenprogramme wirklich aus und beantwortet
    ihre Rückfrage mit einer Eingabetaste."""
    from ide.run.starter import _KONSOLEN_HUELLE

    (ordner / "main.py").write_text(inhalt, encoding="utf-8")
    return subprocess.run(
        [sys.executable, "-c", _KONSOLEN_HUELLE, "Natter – Test", "main.py"],
        cwd=ordner,
        input="\n",
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_konsolenprogramm_laeuft_und_das_fenster_bleibt_offen(tmp_path: Path) -> None:
    """Vom Nutzer indirekt gemeldet: er hatte angefangen, `input()` von
    Hand ans Ende seiner Beispielprogramme zu schreiben, weil sich das
    Konsolenfenster sofort wieder schloss. Das gehört in den Starter und
    nicht in jedes Programm."""
    ergebnis = _huelle_ausfuehren(tmp_path, 'print("Ausgabe des Programms")\n')

    assert "Ausgabe des Programms" in ergebnis.stdout
    assert "Eingabetaste" in ergebnis.stdout  # es wurde wirklich gewartet
    assert ergebnis.returncode == 0


def test_nach_einem_absturz_bleibt_das_fenster_auch_offen(tmp_path: Path) -> None:
    """Gerade dann will man den Fehler lesen können.

    Seit M12 steht dort die deutsche Wo/Was/Prüfe-Meldung statt des rohen
    englischen Tracebacks – dieselbe, die auch der Debugger und ein
    GUI-Programm zeigen. Die Originalmeldung von Python („kaputt“) bleibt
    als gekennzeichnetes Zitat darin erhalten."""
    ergebnis = _huelle_ausfuehren(
        tmp_path, 'print("vorher")\nraise ValueError("kaputt")\n'
    )

    assert "vorher" in ergebnis.stdout
    assert "Wo:" in ergebnis.stderr
    assert "ValueError" in ergebnis.stderr
    assert "kaputt" in ergebnis.stderr
    assert "Traceback (most recent call last)" not in ergebnis.stderr
    assert "Eingabetaste" in ergebnis.stdout
    assert ergebnis.returncode == 1


def test_rueckgabecode_des_programms_bleibt_erhalten(tmp_path: Path) -> None:
    ergebnis = _huelle_ausfuehren(tmp_path, "import sys\nsys.exit(3)\n")

    assert ergebnis.returncode == 3


def test_die_huelle_laesst_das_programm_sein_eigenes_argv_sehen(tmp_path: Path) -> None:
    """`sys.argv[0]` muss das Programm sein, nicht die Hülle und auch
    nicht der Fenstertitel – sonst stimmte in jedem Schülerprogramm der
    eigene Name nicht."""
    ergebnis = _huelle_ausfuehren(tmp_path, "import sys\nprint('ARGV', sys.argv[0])\n")

    assert "ARGV main.py" in ergebnis.stdout


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

    # Bis September 2026 stand hier `"creationflags" not in ...` - und
    # damit war das Gegenteil dessen zugesichert, was der Testname
    # sagt. Ohne Kennzeichen legt Windows für einen Unterprozess aus
    # dem Konsolen-Subsystem gerade ein neues Konsolenfenster an, weil
    # Natter als Fensterprogramm keines zum Erben hat. Hinter dem
    # Fenster des Schülerprogramms stand also ein schwarzer Kasten.
    if sys.platform == "win32":
        assert aufrufe[0][1]["creationflags"] & subprocess.CREATE_NO_WINDOW
    # Ein GUI-Programm hat sein eigenes Fenster - eine Eingabe-
    # aufforderung wäre dort sinnlos, die Konsole gibt es gar nicht.
    assert "-c" not in aufrufe[0][0][0]
    # Ohne Konsole braucht die Ausgabe ein Rohr, sonst ginge sie
    # verloren; gelesen wird sie vom Panel „Ausgabe“.
    assert aufrufe[0][1]["stdout"] is subprocess.PIPE
    assert aufrufe[0][1]["stderr"] is subprocess.STDOUT
