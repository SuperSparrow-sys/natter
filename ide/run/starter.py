"""Startet ein Natter-Projekt als eigenen Prozess (Strg+F5, ohne
Debugger).

Siehe konzept-natter.md, Abschnitt 7.8:

- GUI-Projekte: eigenes Programmfenster, keine Konsole, IDE bleibt
  bedienbar
- Konsolenprojekte: eigenes Konsolenfenster unter Windows
  (`CREATE_NEW_CONSOLE`); auf anderen Plattformen (Entwicklung/Tests)
  läuft die Konsole im aktuellen Terminal weiter, da es dort kein
  Äquivalent gibt

Startet nicht blockierend (`subprocess.Popen`) – die IDE wartet nicht
auf das Programmende.
"""

from __future__ import annotations

import subprocess
import sys

from ide.project import Projekt


def projekt_starten(projekt: Projekt) -> subprocess.Popen:
    zusatz_optionen: dict[str, object] = {}
    if projekt.typ == "console" and sys.platform == "win32":
        zusatz_optionen["creationflags"] = subprocess.CREATE_NEW_CONSOLE

    return subprocess.Popen(
        [sys.executable, projekt.haupt_datei.name],
        cwd=projekt.ordner,
        **zusatz_optionen,
    )
