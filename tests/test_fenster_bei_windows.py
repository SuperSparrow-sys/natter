"""Was Natter Windows über ein Fenster mitteilt, gegen das echte
Windows statt gegen einen Ersatz.

Die übrigen Tests laufen auf der Plattform `offscreen`, und dort hat
ein Fenster keine Kennung, der Windows etwas zuordnen könnte. Der
Grund beim Abmelden (Punkt 344) und Name und Befehl in der Taskleiste
(Punkt 469) waren deshalb nur gegen nachgebaute Funktionen geprüft.
Hier entsteht in einem eigenen Prozess mit der Plattform `windows`
ein Fenster, das nie erscheint; was daran gesetzt wird, verschwindet
mit dem Prozess.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform != "win32", reason="nur unter Windows"
)

WURZEL = Path(__file__).resolve().parent.parent


def _im_fenster(code: str) -> str:
    """Führt `code` mit einem unsichtbaren Fenster `hwnd` aus und gibt
    die Ausgabe zurück."""
    vorspann = textwrap.dedent(
        """
        import ctypes
        from ctypes import wintypes
        from PySide6.QtWidgets import QApplication, QWidget
        app = QApplication([])
        fenster = QWidget()
        hwnd = int(fenster.winId())
        """
    )
    umgebung = {
        k: v for k, v in os.environ.items() if not k.startswith("QT_QPA")
    }
    umgebung["QT_QPA_PLATFORM"] = "windows"
    lauf = subprocess.run(
        [sys.executable, "-c", vorspann + textwrap.dedent(code)],
        cwd=WURZEL, env=umgebung, capture_output=True, text=True,
        timeout=60,
    )
    assert lauf.returncode == 0, lauf.stderr
    return lauf.stdout.strip()


def test_der_grund_beim_abmelden_steht_am_fenster() -> None:
    ausgabe = _im_fenster(
        """
        from ide.shell import abmeldegrund

        user32 = ctypes.WinDLL("user32")
        user32.ShutdownBlockReasonQuery.argtypes = [
            wintypes.HWND, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)
        ]

        def lesen():
            laenge = wintypes.DWORD(512)
            puffer = ctypes.create_unicode_buffer(512)
            if not user32.ShutdownBlockReasonQuery(
                hwnd, puffer, ctypes.byref(laenge)
            ):
                return "-"
            return puffer.value

        print(abmeldegrund.grund_nennen(hwnd))
        print(lesen() == abmeldegrund.GRUND)
        abmeldegrund.grund_entfernen(hwnd)
        print(lesen())
        """
    )
    assert ausgabe.splitlines() == ["True", "True", "-"]


def test_name_und_befehl_fuer_die_taskleiste_stehen_am_fenster() -> None:
    ausgabe = _im_fenster(
        """
        from pcl import taskleiste

        werte = {
            taskleiste._RELAUNCH_COMMAND: '"C:\\\\Natter\\\\Natter.exe"',
            taskleiste._RELAUNCH_NAME: taskleiste.ANZEIGENAME,
        }
        print(taskleiste._setzen(hwnd, werte))

        store = ctypes.c_void_p()
        iid = taskleiste._guid(taskleiste._IID_IPROPERTYSTORE)
        ctypes.windll.shell32.SHGetPropertyStoreForWindow(
            wintypes.HWND(hwnd), ctypes.byref(iid), ctypes.byref(store)
        )
        tabelle = ctypes.cast(
            ctypes.cast(store, ctypes.POINTER(ctypes.c_void_p))[0],
            ctypes.POINTER(ctypes.c_void_p),
        )
        # IPropertyStore: 5 GetValue, 2 Release.
        get_value = ctypes.WINFUNCTYPE(
            ctypes.c_long, ctypes.c_void_p,
            ctypes.POINTER(taskleiste._PROPERTYKEY),
            ctypes.POINTER(taskleiste._PROPVARIANT),
        )(tabelle[5])
        for pid in werte:
            schluessel = taskleiste._PROPERTYKEY(
                taskleiste._guid(taskleiste._PKEY_APPUSERMODEL), pid
            )
            wert = taskleiste._PROPVARIANT()
            get_value(store, ctypes.byref(schluessel), ctypes.byref(wert))
            print(ctypes.wstring_at(wert.wert) if wert.wert else "-")
            ctypes.oledll.ole32.PropVariantClear(ctypes.byref(wert))
        ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(tabelle[2])(store)
        """
    )
    assert ausgabe.splitlines() == [
        "True", '"C:\\Natter\\Natter.exe"', "Natter-Programm"
    ]
