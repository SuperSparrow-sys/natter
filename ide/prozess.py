"""Unterprozesse ohne Konsolenfenster starten.

Natter läuft als Fensterprogramm und hat deshalb keine Konsole.
Startet es einen Unterprozess, der zum Konsolen-Subsystem gehört –
`python.exe`, `pip`, `ruff`, PyInstaller, der Debugger –, legt Windows
dafür ein eigenes Konsolenfenster an. Das blitzt auf, steht im Weg und
hat mit dem zu tun, was jemand gerade macht, überhaupt nichts. Selbst
wenn die Ausgabe über Rohre eingesammelt wird, erscheint das Fenster:
es hängt am Subsystem des gestarteten Programms, nicht an den Rohren.

Dagegen hilft nur `CREATE_NO_WINDOW` an jedem einzelnen Aufruf. Damit
es nicht siebenmal einzeln dasteht und beim achten Aufruf vergessen
wird, steht es hier.

Zwei Ausnahmen bleiben, und beide sind Absicht: ein Konsolenprojekt
einer Schülerin braucht sein Fenster, denn dort steht die Ausgabe
(`ide/run/starter.py` setzt dafür `CREATE_NEW_CONSOLE`), und beim
Bauen aus der Kommandozeile gibt es ohnehin eine Konsole, in der alles
erscheinen darf.
"""

from __future__ import annotations

import subprocess
import sys
from typing import Any

#: Unter Windows das Kennzeichen, das kein Konsolenfenster anlegt.
#: `getattr`, weil es die Flagge auf anderen Plattformen nicht gibt und
#: die Module auch dort importierbar bleiben sollen.
_OHNE_FENSTER = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def ohne_konsole(**weitere: Any) -> dict[str, Any]:
    """Die Argumente für `subprocess`, die kein Fenster aufgehen lassen.

    Gedacht zum Auspacken in den Aufruf::

        subprocess.run(befehl, **ohne_konsole(capture_output=True))

    Übergebene `creationflags` bleiben erhalten und werden ergänzt, statt
    überschrieben zu werden.
    """
    argumente = dict(weitere)
    if sys.platform == "win32":
        argumente["creationflags"] = int(argumente.get("creationflags", 0)) | _OHNE_FENSTER
    return argumente
