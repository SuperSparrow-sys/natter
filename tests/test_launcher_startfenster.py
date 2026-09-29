"""Startfenster und Sperre gegen einen doppelten Start im Starter
`Natter.exe` (Punkt 110). Gegen echte Windows-Fenster."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from tools import launcher

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="nur unter Windows")
WURZEL = Path(__file__).resolve().parent.parent


def _ist_fenster(griff: int) -> bool:
    import ctypes

    return bool(ctypes.windll.user32.IsWindow(ctypes.c_void_p(griff)))


def test_startfenster_erscheint_und_verschwindet() -> None:
    fenster = launcher.startfenster_zeigen()

    assert fenster
    assert launcher.hat_sichtbares_fenster(os.getpid())
    launcher.startfenster_schliessen(fenster)
    assert not _ist_fenster(fenster)


def test_ein_zweiter_start_waehrend_des_ladens_wird_erkannt() -> None:
    erster, sperre = launcher.start_laeuft_schon()
    try:
        assert not erster
        zweiter, _ = launcher.start_laeuft_schon()
        assert zweiter
    finally:
        launcher.sperre_freigeben(sperre)
    danach, sperre = launcher.start_laeuft_schon()
    launcher.sperre_freigeben(sperre)
    assert not danach


def test_warten_endet_sobald_das_programm_ein_fenster_zeigt() -> None:
    # Die echte Python, nicht der Zwischenstarter aus `.venv`: dessen
    # Fenster gehörte einem Enkelprozess mit anderer Nummer. In der
    # Auslieferung startet `Natter.exe` die `pythonw.exe` direkt.
    python = getattr(sys, "_base_executable", sys.executable)
    kind = subprocess.Popen(
        [
            python, "-c",
            "import time; from tools import launcher as l; time.sleep(1); "
            "l.startfenster_zeigen('Kind'); time.sleep(20)",
        ],
        cwd=WURZEL,
        env={**os.environ, "PYTHONPATH": str(WURZEL)},
    )
    try:
        beginn = time.monotonic()
        launcher.warten_bis_sichtbar(kind, None)
        dauer = time.monotonic() - beginn
        assert kind.poll() is None
        assert dauer < 15
    finally:
        kind.kill()
        kind.wait(timeout=10)
