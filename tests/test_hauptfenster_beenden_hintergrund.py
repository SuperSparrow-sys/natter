"""Punkt 254: Natter wird geschlossen, während im Hintergrund ein
Testlauf mit Endlosschleife läuft.

Bis 0.3.6 ging das Fenster zu, ohne auf den Faden zu warten. Qt
beendete den Prozess mit `0xC0000409`, weil ein laufender `QThread`
zerstört wurde, und `harness.py` rechnete ohne Elternteil weiter.
"""

from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys
import textwrap
import time
from pathlib import Path

from PySide6.QtWidgets import QApplication

_ENDLOSER_TEST = """\
import os
import subprocess
import sys
import unittest


class TestEndlos(unittest.TestCase):
    def test_haengt(self):
        kind = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(120)"]
        )
        with open("pids.txt", "w") as datei:
            datei.write(f"{os.getpid()} {kind.pid}")
        while True:
            pass
"""


def _projekt_anlegen(ordner: Path) -> Path:
    ordner.mkdir(parents=True, exist_ok=True)
    (ordner / "main.py").write_text("pass\n", encoding="utf-8")
    (ordner / "test_endlos.py").write_text(_ENDLOSER_TEST, encoding="utf-8")
    daten = {
        "format": "natter-project/1",
        "name": "Endlos",
        "type": "console",
        "main": "main.py",
    }
    pfad = ordner / "endlos.natter"
    pfad.write_text(json.dumps(daten), encoding="utf-8")
    return pfad


def _prozess_lebt(pid: int) -> bool:
    if sys.platform != "win32":
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True
    kernel32 = ctypes.windll.kernel32
    griff = kernel32.OpenProcess(0x1000, False, pid)
    if not griff:
        return False
    try:
        code = ctypes.c_ulong()
        kernel32.GetExitCodeProcess(griff, ctypes.byref(code))
        return code.value == 259  # STILL_ACTIVE
    finally:
        kernel32.CloseHandle(griff)


def _pids_abwarten(ordner: Path, zeitlimit: float = 30.0) -> list[int]:
    datei = ordner / "pids.txt"
    ende = time.monotonic() + zeitlimit
    while time.monotonic() < ende:
        QApplication.processEvents()
        try:
            text = datei.read_text(encoding="utf-8").split()
        except OSError:
            text = []
        if len(text) == 2:
            return [int(t) for t in text]
        time.sleep(0.05)
    raise AssertionError("Der Test im Projekt ist nie angelaufen")


def _verschwunden(pids: list[int], zeitlimit: float = 10.0) -> bool:
    ende = time.monotonic() + zeitlimit
    while time.monotonic() < ende:
        if not any(_prozess_lebt(pid) for pid in pids):
            return True
        time.sleep(0.1)
    return False


def _aufraeumen(pids: list[int]) -> None:
    """Hinterlässt auch bei einem Fehlschlag keine Prozesse."""
    for pid in pids:
        if _prozess_lebt(pid):
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True,
                check=False,
            )


def test_schliessen_bricht_den_testlauf_ab(
    tmp_path: Path, hauptfenster_bauen
) -> None:
    fenster = hauptfenster_bauen()
    fenster.projekt_oeffnen(_projekt_anlegen(tmp_path))
    fenster._alle_tests_ausfuehren_aktion()
    lauf = fenster._hintergrundarbeit
    pids = _pids_abwarten(tmp_path)
    try:
        beginn = time.monotonic()
        fenster.close()
        dauer = time.monotonic() - beginn

        assert not lauf.isRunning()
        assert dauer < 20
        assert _verschwunden(pids)
    finally:
        _aufraeumen(pids)
        lauf.wait(70_000)


_SKRIPT = """\
import sys
from pathlib import Path

from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import QApplication

ordner = Path(sys.argv[1])
heim = Path(sys.argv[2])
QSettings.setDefaultFormat(QSettings.Format.IniFormat)
QSettings.setPath(
    QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(heim)
)
Path.home = staticmethod(lambda: heim)

import ide.pfade
import pcl.pruefungsmodus

ide.pfade.dokumente_ordner = lambda: heim / "Dokumente"
pcl.pruefungsmodus._weitere_ablagen = lambda: []

from ide.shell.hauptfenster import HauptFenster

app = QApplication([])
fenster = HauptFenster()
fenster.show()
fenster.projekt_oeffnen(ordner / "endlos.natter")
fenster._alle_tests_ausfuehren_aktion()


def pruefen():
    if (ordner / "pids.txt").is_file():
        fenster.close()
        app.quit()
    else:
        QTimer.singleShot(50, pruefen)


QTimer.singleShot(50, pruefen)
app.exec()
"""


def test_natter_endet_beim_schliessen_ohne_fehlercode(
    tmp_path: Path,
) -> None:
    """Die Prüfung aus „Zu tun": ein eigener Prozess, der Natter
    während des Testlaufs schließt, endet mit 0, und weder
    `harness.py` noch der vom Test gestartete Prozess bleibt übrig."""
    projekt = tmp_path / "projekt"
    _projekt_anlegen(projekt)
    heim = tmp_path / "heim"
    heim.mkdir()
    skript = tmp_path / "schliessen.py"
    skript.write_text(textwrap.dedent(_SKRIPT), encoding="utf-8")
    umgebung = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    wurzel = Path(__file__).resolve().parents[1]
    umgebung["PYTHONPATH"] = str(wurzel)

    lauf = subprocess.run(
        [sys.executable, str(skript), str(projekt), str(heim)],
        cwd=wurzel,
        env=umgebung,
        capture_output=True,
        timeout=120,
        check=False,
    )
    pids = [int(t) for t in (projekt / "pids.txt").read_text().split()]
    try:
        assert lauf.returncode == 0, lauf.stderr.decode(errors="replace")
        assert _verschwunden(pids)
    finally:
        _aufraeumen(pids)
