"""Tests für HauptFenster._projekt_starten_aktion(): „Starten ohne
Debugger“ (Strg+F5, Abschnitt 7.8). Siehe docs/arbeitspakete/M2.md,
„Ausführung in eigenen Fenstern“.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from ide.shell.hauptfenster import HauptFenster


def _projekt_ordner_schreiben(ordner: Path, main_inhalt: str) -> Path:
    ordner.mkdir(parents=True, exist_ok=True)
    (ordner / "main.py").write_text(main_inhalt, encoding="utf-8")
    daten = {"format": "natter-project/1", "name": "Test", "type": "gui", "main": "main.py"}
    natter_pfad = ordner / "test.natter"
    natter_pfad.write_text(json.dumps(daten), encoding="utf-8")
    return natter_pfad


def test_ohne_offenes_projekt_zeigt_hinweis() -> None:
    fenster = HauptFenster()
    fenster._projekt_starten_aktion()
    assert fenster.statusBar().currentMessage() == "Kein Projekt offen."


def test_start_setzt_laufenden_prozess_und_zeigt_status(tmp_path: Path) -> None:
    natter_pfad = _projekt_ordner_schreiben(
        tmp_path,
        'from pathlib import Path\nPath("lief.txt").write_text("ja", encoding="utf-8")\n',
    )
    fenster = HauptFenster()
    fenster.projekt_oeffnen(natter_pfad)

    fenster._projekt_starten_aktion()
    assert fenster.laufender_prozess is not None
    fenster.laufender_prozess.wait(timeout=10)

    assert fenster.statusBar().currentMessage() == "Test gestartet"
    assert (tmp_path / "lief.txt").exists()


def test_start_mit_ruff_fund_startet_nicht_und_fuellt_die_meldungen(tmp_path: Path) -> None:
    natter_pfad = _projekt_ordner_schreiben(
        tmp_path, "def f():\n    return nicht_definiert\n"
    )
    fenster = HauptFenster()
    fenster.projekt_oeffnen(natter_pfad)

    fenster._projekt_starten_aktion()

    assert fenster.laufender_prozess is None
    assert fenster.meldungen_liste.count() >= 1
    assert "F821" in fenster.meldungen_liste.item(0).text()
    assert "Fund" in fenster.statusBar().currentMessage()


def test_sauberer_start_leert_vorherige_meldungen(tmp_path: Path) -> None:
    natter_pfad = _projekt_ordner_schreiben(
        tmp_path,
        'from pathlib import Path\nPath("lief.txt").write_text("ja", encoding="utf-8")\n',
    )
    fenster = HauptFenster()
    fenster.projekt_oeffnen(natter_pfad)
    fenster.meldungen_liste.addItem("alte Meldung")

    fenster._projekt_starten_aktion()
    fenster.laufender_prozess.wait(timeout=10)

    assert fenster.meldungen_liste.count() == 0


def test_erneuter_start_waehrend_das_programm_noch_laeuft_wird_abgelehnt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # main.py-Inhalt spielt hier keine Rolle: projekt_starten wird unten
    # durch einen echten, aber unabhängig gestarteten Prozess ersetzt.
    natter_pfad = _projekt_ordner_schreiben(tmp_path, "pass\n")
    fenster = HauptFenster()
    fenster.projekt_oeffnen(natter_pfad)

    laufender_prozess = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(5)"])
    monkeypatch.setattr(
        "ide.shell.hauptfenster.projekt_starten", lambda projekt: laufender_prozess
    )

    try:
        fenster._projekt_starten_aktion()
        assert fenster.laufender_prozess is laufender_prozess

        fenster._projekt_starten_aktion()
        assert fenster.statusBar().currentMessage() == "Test läuft bereits."
    finally:
        laufender_prozess.kill()
        laufender_prozess.wait(timeout=10)
