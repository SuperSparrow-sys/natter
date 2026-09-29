"""Womit Natter Python-Code startet (M12).

Vom Nutzer im installierten Programm gemeldet: „die Konsole und die GUI
sind beim Start nicht aufgegangen, sondern nur ein weiteres Fenster von
Natter.“

Die Ursache traf fünf Stellen, nicht nur die auffälligste: das
Schülerprogramm, den Debugger, die Prüfung vor dem Start, die
Paketverwaltung und den Exe-Export. Alle schrieben `sys.executable`
selbst in ihre Befehlsliste. Seither gehen sie über
`ide/run/interpreter.py`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from ide.run.interpreter import python_befehl, ruff_befehl


def test_im_entwicklungsbaum_ist_es_der_python() -> None:
    assert python_befehl() == [sys.executable]


@pytest.mark.parametrize(
    "modul",
    ["ide.run.starter", "ide.run.pruefung", "ide.debugger.dap_client"],
)
def test_keine_stelle_ruft_sys_executable_noch_direkt(modul: str) -> None:
    """Der Rundlauf über alle Stellen, die einen Unterprozess starten:
    wer hier `sys.executable` in eine Befehlsliste schreibt, baut den
    gemeldeten Fehler wieder ein."""
    import importlib

    quelle = Path(importlib.import_module(modul).__file__).read_text(encoding="utf-8")

    assert "python_befehl()" in quelle or "ruff_befehl()" in quelle
    assert "sys.executable," not in quelle


def test_ruff_wird_im_entwicklungsbaum_gefunden() -> None:
    befehl = ruff_befehl()

    assert len(befehl) == 1
    assert Path(befehl[0]).is_file()
