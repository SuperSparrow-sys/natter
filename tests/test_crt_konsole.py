"""`pcl.crt` schaltet im Konsolenfenster die Steuerzeichen ein
(offener Punkt 81).

Das klassische Konsolenfenster von Windows, das Natter für ein
Konsolenprogramm öffnet, verarbeitet ANSI-Steuerzeichen erst, wenn
`ENABLE_VIRTUAL_TERMINAL_PROCESSING` gesetzt ist. `crt.py` tat das
nicht.
"""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
from pathlib import Path

import pytest

from pcl import crt

_WURZEL = Path(__file__).resolve().parents[1]


class _Kernel32:
    """Eine Attrappe der drei Aufrufe aus `kernel32`."""

    def __init__(self, griff: int = 7, modus: int | None = 0x0003) -> None:
        self._griff = griff
        self._modus = modus
        self.gesetzt: list[tuple[int, int]] = []

    def GetStdHandle(self, nummer: int) -> int:  # noqa: N802
        assert nummer == -11
        return self._griff

    def GetConsoleMode(self, griff: int, zeiger) -> int:  # noqa: N802
        if self._modus is None:
            return 0  # keine Konsole
        ctypes.cast(zeiger, ctypes.POINTER(ctypes.c_uint32))[0] = self._modus
        return 1

    def SetConsoleMode(self, griff: int, modus: int) -> int:  # noqa: N802
        self.gesetzt.append((griff, modus))
        return 1


def test_der_modus_wird_eingeschaltet() -> None:
    kernel32 = _Kernel32(modus=0x0003)

    assert crt.virtuelles_terminal_einschalten(kernel32) is True
    assert kernel32.gesetzt == [(7, 0x0003 | 0x0004)]


def test_ist_er_schon_an_bleibt_alles_wie_es_ist() -> None:
    kernel32 = _Kernel32(modus=0x0007)

    assert crt.virtuelles_terminal_einschalten(kernel32) is True
    assert kernel32.gesetzt == []


def test_ohne_konsole_passiert_nichts() -> None:
    """Umgeleitet in eine Datei oder ins Ausgabefenster der IDE."""
    kernel32 = _Kernel32(modus=None)

    assert crt.virtuelles_terminal_einschalten(kernel32) is False
    assert kernel32.gesetzt == []


def test_ohne_griff_passiert_nichts() -> None:
    for griff in (0, -1):
        kernel32 = _Kernel32(griff=griff)
        assert crt.virtuelles_terminal_einschalten(kernel32) is False
        assert kernel32.gesetzt == []


def test_vorbereitet_wird_einmal_vor_der_ersten_ausgabe(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    aufrufe: list[object] = []
    monkeypatch.setattr(crt, "_konsole_bereit", False)
    monkeypatch.setattr(crt.sys, "platform", "win32")
    monkeypatch.setattr(
        crt, "virtuelles_terminal_einschalten", lambda k: aufrufe.append(k)
    )
    monkeypatch.setattr(
        crt.ctypes, "windll", type("W", (), {"kernel32": "k32"}), raising=False
    )

    crt.text_color("red")
    crt.goto_xy(1, 1)
    crt.clr_scr()

    assert aufrufe == ["k32"]
    assert capsys.readouterr().out == "\033[31m\033[1;1H\033[2J\033[H"


def test_ausserhalb_von_windows_wird_nichts_versucht(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    aufrufe: list[object] = []
    monkeypatch.setattr(crt, "_konsole_bereit", False)
    monkeypatch.setattr(crt.sys, "platform", "linux")
    monkeypatch.setattr(
        crt, "virtuelles_terminal_einschalten", lambda k: aufrufe.append(k)
    )

    crt.text_background("blue")

    assert aufrufe == []
    assert capsys.readouterr().out == "\033[44m"


_KIND = r'''
import ctypes
import ctypes.wintypes as w
import sys

from pcl import crt

k = ctypes.windll.kernel32
griff = k.GetStdHandle(-11)
vorher = ctypes.c_uint32()
k.GetConsoleMode(griff, ctypes.byref(vorher))

crt.clr_scr()
crt.text_color("red")
sys.stdout.write("X")
sys.stdout.flush()

nachher = ctypes.c_uint32()
k.GetConsoleMode(griff, ctypes.byref(nachher))
farbe = (w.WORD * 1)()
gelesen = w.DWORD()
k.ReadConsoleOutputAttribute(
    griff, farbe, 1, w._COORD(0, 0), ctypes.byref(gelesen)
)
zeichen = ctypes.create_unicode_buffer(2)
k.ReadConsoleOutputCharacterW(
    griff, zeichen, 1, w._COORD(0, 0), ctypes.byref(gelesen)
)
with open(sys.argv[1], "w", encoding="utf-8") as datei:
    datei.write(f"{vorher.value & 4} {nachher.value & 4} {farbe[0]} {zeichen.value}")
'''


@pytest.mark.skipif(sys.platform != "win32", reason="nur unter Windows")
def test_im_echten_konsolenfenster_wird_die_schrift_rot(tmp_path: Path) -> None:
    """Ein echtes Konsolenfenster, nur ohne sichtbares Fenster
    (`CREATE_NO_WINDOW`). Gelesen wird zurück, was dort steht: das
    „X“ links oben muss die Farbe Rot tragen und darf nicht hinter
    einem sichtbaren `←[31m` stehen."""
    skript = tmp_path / "kind.py"
    skript.write_text(_KIND, encoding="utf-8")
    ergebnis_datei = tmp_path / "ergebnis.txt"
    umgebung = dict(os.environ, PYTHONPATH=str(_WURZEL))

    lauf = subprocess.run(
        [sys.executable, str(skript), str(ergebnis_datei)],
        creationflags=subprocess.CREATE_NO_WINDOW,
        env=umgebung,
        timeout=60,
    )

    assert lauf.returncode == 0
    vorher, nachher, farbe, zeichen = ergebnis_datei.read_text(
        encoding="utf-8"
    ).split(" ")
    assert nachher == "4"
    assert zeichen == "X"
    # FOREGROUND_RED ist 0x4; Grün und Blau dürfen nicht dabei sein.
    assert int(farbe) & 0x7 == 0x4, (vorher, farbe)
