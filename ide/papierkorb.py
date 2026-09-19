"""Dateien in den Windows-Papierkorb legen statt sie zu löschen.

Gefunden beim Durchgehen der Frage „gibt es Stellen, an denen
Rückgängig fehlt?“ (M11, Abschnitt 4): „⋮ → Löschen …“ im
Projekt-Explorer rief `Path.unlink()` und sagte dazu ehrlich, die Datei
sei danach weg. In einem Klassenraum ist genau das der Fall, in dem
jemand die falsche Unit erwischt – und die Arbeit einer Doppelstunde
ist nicht wiederzubekommen. Der Papierkorb ist hier das „Rückgängig“:
Windows kennt ihn, die Schülerinnen und Schüler kennen ihn, und er
kostet nichts.

Windows bietet das über `SHFileOperationW` aus der Shell an; ein
eigenes Paket (`send2trash`) dafür aufzunehmen wäre unverhältnismäßig.
Auf anderen Plattformen (Entwicklung, Tests) gibt es kein Äquivalent
ohne zusätzliche Abhängigkeit – dort wird gelöscht wie bisher, und der
Aufrufer erfährt es am Rückgabewert.
"""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from pathlib import Path

#: Aus `shellapi.h`: löschen, dabei in den Papierkorb legen
#: (`FOF_ALLOWUNDO`), ohne Nachfrage und ohne Fortschrittsfenster –
#: gefragt hat Natter vorher schon selbst.
_FO_DELETE = 0x0003
_FOF_SILENT = 0x0004
_FOF_NOCONFIRMATION = 0x0010
_FOF_ALLOWUNDO = 0x0040
_FOF_NOERRORUI = 0x0400


class _SHFILEOPSTRUCTW(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("wFunc", wintypes.UINT),
        ("pFrom", wintypes.LPCWSTR),
        ("pTo", wintypes.LPCWSTR),
        ("fFlags", ctypes.c_uint16),
        ("fAnyOperationsAborted", wintypes.BOOL),
        ("hNameMappings", ctypes.c_void_p),
        ("lpszProgressTitle", wintypes.LPCWSTR),
    ]


def papierkorb_verfuegbar() -> bool:
    """Ob diese Plattform einen Papierkorb anbietet, den Natter
    ansprechen kann."""
    return sys.platform == "win32"


def in_den_papierkorb(pfad: Path) -> bool:
    """Legt `pfad` in den Papierkorb. Liefert `True`, wenn das geklappt
    hat, sonst `False` – dann muss der Aufrufer entscheiden, ob er
    endgültig löscht oder abbricht.

    Löst dieselben `OSError` aus wie `Path.unlink()`, wenn die Datei
    gar nicht erst gefunden wird: ein gesperrter oder fehlender Pfad ist
    keine Papierkorb-Frage.
    """
    if not papierkorb_verfuegbar():
        return False
    if not pfad.exists():
        raise FileNotFoundError(pfad)

    # `pFrom` ist eine Liste von Pfaden, die mit zwei Nullzeichen endet;
    # Python hängt nur eines an, deshalb eines von Hand dazu.
    auftrag = _SHFILEOPSTRUCTW(
        hwnd=None,
        wFunc=_FO_DELETE,
        pFrom=f"{pfad.resolve()}\0",
        pTo=None,
        fFlags=_FOF_ALLOWUNDO | _FOF_NOCONFIRMATION | _FOF_SILENT | _FOF_NOERRORUI,
        fAnyOperationsAborted=False,
        hNameMappings=None,
        lpszProgressTitle=None,
    )
    ergebnis = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(auftrag))
    return ergebnis == 0 and not auftrag.fAnyOperationsAborted
