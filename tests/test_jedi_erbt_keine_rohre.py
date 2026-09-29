"""Der Hilfsprozess von jedi erbt keine fremden Rohre (Punkt 224).

Startete das Aufwärmen der Vervollständigung genau während der Prüfung
vor dem Start, erbte jedis Hilfsprozess die Schreibenden der Rohre von
ruff und hielt sie offen; F5 wartete dann für immer. Nachgestellt wird
das mit einem vererbbaren Rohr, das offen ist, während der Hilfsprozess
startet. In einem eigenen Prozess, damit jedi dort frisch startet.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent

_PROBE = r"""
import os, sys, threading

lesen, schreiben = os.pipe()
os.set_inheritable(schreiben, True)

from ide.shell.vervollstaendigung import _jedi

jedi = _jedi()
# Ein übersetztes Modul zwingt jedi, seinen Hilfsprozess zu starten.
jedi.Script("import math\nmath.").complete(2, 5)

os.close(schreiben)
ergebnis = []
faden = threading.Thread(target=lambda: ergebnis.append(os.read(lesen, 1)))
faden.daemon = True
faden.start()
faden.join(10)
print("ZU" if ergebnis == [b""] else "OFFEN")
sys.stdout.flush()
os._exit(0)
"""


def test_jedis_hilfsprozess_haelt_kein_fremdes_rohr_offen(tmp_path) -> None:
    skript = tmp_path / "probe.py"
    skript.write_text(_PROBE, encoding="utf-8")
    umgebung = dict(os.environ, PYTHONPATH=str(WURZEL))

    lauf = subprocess.run(
        [sys.executable, str(skript)],
        capture_output=True,
        text=True,
        timeout=120,
        env=umgebung,
        cwd=tmp_path,
    )

    assert lauf.stdout.strip() == "ZU", lauf.stdout + lauf.stderr[-2000:]
