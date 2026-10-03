"""Name und Symbol eines Programms in der Windows-Taskleiste (Punkt 469).

`pcl.Application` meldet ein Programm unter der Kennung
`Natter.Programm` an, getrennt von der IDE (Punkt 416). Für diese
Kennung gibt es keine Verknüpfung im Startmenü, aus der Windows einen
Namen nehmen könnte; der Knopf hieß deshalb „Python“, nach der
Dateibeschreibung von `pythonw.exe`. Ein Eintrag unter
`HKCU\\Software\\Classes\\AppUserModelId` änderte daran nichts.

Was wirkt, sind drei Eigenschaften am Fenster selbst: der Name, das
Symbol und der Befehl, den Windows beim Anheften startet. Windows
übernimmt den Namen nur zusammen mit dem Befehl, und es liest beides,
wenn der Knopf entsteht. `fenster_benennen` läuft deshalb, bevor ein
Formular zum ersten Mal gezeigt wird.

Gilt nur, wenn das Programm aus einer installierten Natter läuft: der
Befehl ist dann `Natter.exe` neben dem Ordner `python`. Im
Entwicklungsbaum und in einer exportierten Exe geschieht nichts.
"""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from pathlib import Path

#: So heißt der Knopf eines Programms in der Taskleiste.
ANZEIGENAME = "Natter-Programm"

#: Gesetzt von `pcl.application`, wenn das Programm unter eigener
#: Kennung angemeldet ist. Ohne sie gälten Name und Symbol für die
#: Gruppe „Python“ und damit für fremde Programme.
kennung_gesetzt = False


class _GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    ]


def _guid(text: str) -> _GUID:
    teile = text.split("-")
    rest = bytes.fromhex(teile[3] + teile[4])
    return _GUID(
        int(teile[0], 16), int(teile[1], 16), int(teile[2], 16),
        (ctypes.c_ubyte * 8)(*rest),
    )


class _PROPERTYKEY(ctypes.Structure):
    _fields_ = [("fmtid", _GUID), ("pid", wintypes.DWORD)]


class _PROPVARIANT(ctypes.Structure):
    _fields_ = [
        ("vt", ctypes.c_ushort),
        ("r1", ctypes.c_ushort),
        ("r2", ctypes.c_ushort),
        ("r3", ctypes.c_ushort),
        ("wert", ctypes.c_void_p),
        ("rest", ctypes.c_void_p),
    ]


_VT_LPWSTR = 31
_IID_IPROPERTYSTORE = "886d8eeb-8cf2-4446-8d02-cdba1dbdcf99"
_PKEY_APPUSERMODEL = "9f4c2855-9f79-4b39-a8d0-e1d42de1d5f3"
_RELAUNCH_COMMAND = 2
_RELAUNCH_ICON = 3
_RELAUNCH_NAME = 4


def natter_exe() -> Path | None:
    """`Natter.exe` der Installation, aus der dieses Python stammt."""
    kandidat = Path(sys.executable).resolve().parent.parent / "Natter.exe"
    return kandidat if kandidat.is_file() else None


def fenster_benennen(hwnd: int) -> bool:
    """Gibt dem Fenster Namen, Symbol und Befehl für die Taskleiste.
    Liefert, ob es geklappt hat; ein Fehler bleibt still, der Knopf
    heißt dann wie bisher."""
    if sys.platform != "win32" or not kennung_gesetzt:
        return False
    exe = natter_exe()
    if exe is None:
        return False
    try:
        return _setzen(hwnd, {
            _RELAUNCH_COMMAND: f'"{exe}"',
            _RELAUNCH_ICON: f"{exe},0",
            _RELAUNCH_NAME: ANZEIGENAME,
        })
    except (AttributeError, OSError, ValueError):
        return False


def _setzen(hwnd: int, werte: dict[int, str]) -> bool:
    shell32 = ctypes.windll.shell32
    store = ctypes.c_void_p()
    iid = _guid(_IID_IPROPERTYSTORE)
    ergebnis = shell32.SHGetPropertyStoreForWindow(
        wintypes.HWND(hwnd), ctypes.byref(iid), ctypes.byref(store)
    )
    if ergebnis != 0 or not store:
        return False
    tabelle = ctypes.cast(
        ctypes.cast(store, ctypes.POINTER(ctypes.c_void_p))[0],
        ctypes.POINTER(ctypes.c_void_p),
    )
    # IPropertyStore: 2 Release, 6 SetValue, 7 Commit.
    release = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(tabelle[2])
    set_value = ctypes.WINFUNCTYPE(
        ctypes.c_long, ctypes.c_void_p,
        ctypes.POINTER(_PROPERTYKEY), ctypes.POINTER(_PROPVARIANT),
    )(tabelle[6])
    commit = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p)(tabelle[7])
    try:
        ok = True
        for pid, text in werte.items():
            puffer = ctypes.create_unicode_buffer(text)
            schluessel = _PROPERTYKEY(_guid(_PKEY_APPUSERMODEL), pid)
            wert = _PROPVARIANT(
                vt=_VT_LPWSTR, wert=ctypes.addressof(puffer)
            )
            gesetzt = set_value(
                store, ctypes.byref(schluessel), ctypes.byref(wert)
            )
            ok = gesetzt == 0 and ok
        return commit(store) == 0 and ok
    finally:
        release(store)
