"""Tests für die Debugger-Verdrahtung in HauptFenster (F5, Abschnitt
7.8/8.1): Breakpoints aus offenen Editor-Tabs, DebugSitzung-Signale
füllen Variablen-/Aufrufstapel-Panel. Gegen echtes `debugpy`, kein Mock.
Siehe docs/arbeitspakete/M4.md, Schritt 6.
"""

from __future__ import annotations

import json
from pathlib import Path

from ide.shell.hauptfenster import HauptFenster


def _projekt_oeffnen(fenster: HauptFenster, ordner: Path, main_inhalt: str) -> Path:
    ordner.mkdir(parents=True, exist_ok=True)
    (ordner / "main.py").write_text(main_inhalt, encoding="utf-8")
    daten = {"format": "natter-project/1", "name": "Test", "type": "console", "main": "main.py"}
    natter_pfad = ordner / "test.natter"
    natter_pfad.write_text(json.dumps(daten), encoding="utf-8")
    fenster.projekt_oeffnen(natter_pfad)
    return natter_pfad


def test_f5_ohne_projekt_zeigt_hinweis() -> None:
    fenster = HauptFenster()
    fenster._projekt_mit_debugger_starten_aktion()
    assert fenster.statusBar().currentMessage() == "Kein Projekt offen."


def test_f5_mit_ruff_fund_startet_nicht(tmp_path: Path) -> None:
    fenster = HauptFenster()
    _projekt_oeffnen(fenster, tmp_path, "def f():\n    return nicht_definiert\n")
    fenster._projekt_mit_debugger_starten_aktion()
    assert fenster.debug_sitzung is None
    assert fenster.meldungen_liste.count() >= 1


def test_f5_haelt_bei_einem_im_editor_gesetzten_breakpoint(qtbot, tmp_path: Path) -> None:
    fenster = HauptFenster()
    _projekt_oeffnen(
        fenster, tmp_path, "zahl = 42\nmarker = 1  # Zeile 2, Breakpoint\n"
    )
    editor = fenster.datei_oeffnen(fenster.projekt.haupt_datei)
    editor.breakpoint_umschalten(2)

    fenster._projekt_mit_debugger_starten_aktion()
    qtbot.waitUntil(lambda: fenster._aktueller_thread_id is not None, timeout=15000)

    try:
        assert "Angehalten" in fenster.statusBar().currentMessage()
        qtbot.waitUntil(lambda: fenster.aufrufstapel_liste.count() > 0, timeout=15000)
        qtbot.waitUntil(lambda: fenster.variablen_baum.topLevelItemCount() > 0, timeout=15000)

        werte = {
            fenster.variablen_baum.topLevelItem(i).text(0): fenster.variablen_baum.topLevelItem(
                i
            ).text(1)
            for i in range(fenster.variablen_baum.topLevelItemCount())
        }
        assert werte.get("zahl") == "42"
    finally:
        if fenster.debug_sitzung is not None:
            fenster._debugger_stoppen_aktion()


def test_fortsetzen_laesst_das_programm_zu_ende_laufen(qtbot, tmp_path: Path) -> None:
    fenster = HauptFenster()
    _projekt_oeffnen(
        fenster,
        tmp_path,
        'from pathlib import Path\n'
        'Path("marker.txt").write_text("fertig")\n'
        'marker = 1  # Zeile 3, Breakpoint\n',
    )
    editor = fenster.datei_oeffnen(fenster.projekt.haupt_datei)
    editor.breakpoint_umschalten(3)

    fenster._projekt_mit_debugger_starten_aktion()
    qtbot.waitUntil(lambda: fenster._aktueller_thread_id is not None, timeout=15000)

    fenster._debugger_fortsetzen_aktion()
    qtbot.waitUntil(lambda: fenster.debug_sitzung is None, timeout=15000)

    assert (tmp_path / "marker.txt").read_text(encoding="utf-8") == "fertig"
