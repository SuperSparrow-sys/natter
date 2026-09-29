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

Nicht jedes Laufwerk hat einen Papierkorb (Punkt 273). Auf dem
Heimatlaufwerk auf dem Schulserver, auf einem USB-Stick oder bei per
Richtlinie abgeschaltetem Papierkorb löscht `SHFileOperationW` die
Datei endgültig und meldet trotzdem Erfolg. `papierkorb_verfuegbar`
fragt deshalb für den Pfad selbst nach, und die Nachfrage vor dem
Löschen richtet sich danach.
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
#: Fragt Windows selbst noch einmal, falls die Datei doch endgültig
#: gelöscht würde, etwa weil sie größer ist als der Papierkorb. Hebt
#: `FOF_NOCONFIRMATION` für genau diesen Fall auf.
_FOF_WANTNUKEWARNING = 0x4000

#: Aus `GetDriveTypeW`: nur feste Laufwerke haben einen Papierkorb.
#: Wechseldatenträger und Netzlaufwerke löschen endgültig.
_DRIVE_FIXED = 3


class _SHQUERYRBINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("i64Size", ctypes.c_int64),
        ("i64NumItems", ctypes.c_int64),
    ]


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


def papierkorb_verfuegbar(pfad: Path | None = None) -> bool:
    """Ob diese Plattform einen Papierkorb anbietet, den Natter
    ansprechen kann, und mit `pfad` auch, ob das Laufwerk von `pfad`
    einen hat.

    Im Zweifel `False`: dann fragt Natter vor dem Löschen mit dem
    Hinweis, dass sich die Datei nicht zurückholen lässt. Eine Warnung
    zu viel ist harmlos, eine fehlende kostet die Arbeit.
    """
    if sys.platform != "win32":
        return False
    if pfad is None:
        return True
    try:
        wurzel = Path(pfad).resolve().anchor
    except OSError:
        return False
    if not wurzel:
        return False
    try:
        if _laufwerksart(wurzel) != _DRIVE_FIXED:
            return False
        if _papierkorb_abgeschaltet():
            return False
        return _papierkorb_abfragen(wurzel) == 0
    except OSError:
        return False


def _laufwerksart(wurzel: str) -> int:
    """`GetDriveTypeW` für `wurzel`, dem Laufwerk oder der Freigabe am
    Anfang eines Pfads."""
    return ctypes.windll.kernel32.GetDriveTypeW(wurzel)


def _papierkorb_abfragen(wurzel: str) -> int:
    """`SHQueryRecycleBinW` für `wurzel`; 0 heißt, das Laufwerk hat
    einen Papierkorb. Auf einem Laufwerk ohne Papierkorb, etwa unter
    einem UNC-Pfad, liefert die Abfrage einen Fehlercode."""
    info = _SHQUERYRBINFO(cbSize=ctypes.sizeof(_SHQUERYRBINFO))
    return ctypes.windll.shell32.SHQueryRecycleBinW(
        wurzel, ctypes.byref(info)
    )


def _papierkorb_abgeschaltet() -> bool:
    """Ob die Richtlinie „Dateien nicht in den Papierkorb verschieben“
    gesetzt ist, für das Konto oder den ganzen Rechner."""
    import winreg

    schluessel = (
        r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer"
    )
    for wurzel in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            with winreg.OpenKey(wurzel, schluessel) as offen:
                wert, _ = winreg.QueryValueEx(offen, "NoRecycleFiles")
        except OSError:
            continue
        if wert:
            return True
    return False


def in_den_papierkorb(pfad: Path) -> bool:
    """Legt `pfad` in den Papierkorb. Liefert `True`, wenn das geklappt
    hat, sonst `False` – dann ist nichts gelöscht, und endgültig zu
    löschen ist eine eigene Entscheidung des Aufrufers, über die vorher
    gefragt worden sein muss.

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
        fFlags=(
            _FOF_ALLOWUNDO
            | _FOF_NOCONFIRMATION
            | _FOF_SILENT
            | _FOF_NOERRORUI
            | _FOF_WANTNUKEWARNING
        ),
        fAnyOperationsAborted=False,
        hNameMappings=None,
        lpszProgressTitle=None,
    )
    ergebnis = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(auftrag))
    return ergebnis == 0 and not auftrag.fAnyOperationsAborted
