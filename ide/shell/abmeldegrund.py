"""Windows beim Abmelden sagen, warum Natter es aufhält (Punkt 344).

Fragt Natter beim Abmelden nach ungespeicherten Änderungen, zeigt
Windows nach wenigen Sekunden eine eigene Seite mit den Programmen, die
das Abmelden aufhalten, und dem Knopf „Trotzdem abmelden“. Ohne Grund
steht dort nur der Name des Fensters, und am Stundenende drückt man
den Knopf, ohne zu wissen, dass der Text im Editor dann verloren ist.
`ShutdownBlockReasonCreate` setzt den Satz darunter, solange die
Frage offen ist.

Ungefragt gespeichert wird dabei nicht: die Frage „Speichern,
Verwerfen, Abbrechen“ bleibt die Entscheidung der Schülerin, und eine
eigene Sicherung, die beim nächsten Öffnen angeboten würde, wäre eine
zusätzliche Ablage mit eigenen Regeln zum Aufräumen.

Außerhalb von Windows und unter der Plattform `offscreen` der Tests
geschieht nichts: dort gibt es kein echtes Fenster, dem Windows einen
Grund zuordnen könnte.
"""

from __future__ import annotations

import ctypes
import sys
from typing import Any

#: Der Satz auf der Seite von Windows. Kurz, weil Windows ihn in einer
#: schmalen Spalte unter dem Programmnamen zeigt.
GRUND = (
    "Ungespeicherte Änderungen in Natter. Ohne Speichern gehen sie "
    "beim Abmelden verloren."
)


def _user32() -> Any | None:
    """Die Funktionen aus `user32.dll`, oder `None`, wo es sie nicht
    gibt oder kein echtes Fenster dahintersteht."""
    if sys.platform != "win32":
        return None
    from PySide6.QtGui import QGuiApplication

    if QGuiApplication.platformName() != "windows":
        return None
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.ShutdownBlockReasonCreate.argtypes = [
        wintypes.HWND, wintypes.LPCWSTR,
    ]
    user32.ShutdownBlockReasonCreate.restype = wintypes.BOOL
    user32.ShutdownBlockReasonDestroy.argtypes = [wintypes.HWND]
    user32.ShutdownBlockReasonDestroy.restype = wintypes.BOOL
    return user32


def grund_nennen(fenster: int, grund: str = GRUND) -> bool:
    """Setzt `grund` für das Fenster mit der Kennung `fenster`.
    Liefert, ob Windows ihn angenommen hat."""
    user32 = _user32()
    if user32 is None or not fenster:
        return False
    try:
        return bool(user32.ShutdownBlockReasonCreate(fenster, grund))
    except (AttributeError, OSError):
        return False


def grund_entfernen(fenster: int) -> None:
    """Nimmt den Grund wieder heraus, sobald die Frage beantwortet
    ist."""
    user32 = _user32()
    if user32 is None or not fenster:
        return
    try:
        user32.ShutdownBlockReasonDestroy(fenster)
    except (AttributeError, OSError):
        pass
