"""Tests für pcl/crt.py (Abschnitt 9): CRT-Hilfsmodul für den Umstieg
aus dem CRT-Unterricht. `msvcrt`/`winsound` sind Windows-Standard-
bibliotheken; hier über `sys.modules`-Attrappen ersetzt, damit die Tests
auch auf dem Linux-CI-Runner laufen (siehe Arbeitspaket M6).
"""

from __future__ import annotations

import sys
import types

import pytest

from pcl import crt


def test_clr_scr_schreibt_die_ansi_loesch_sequenz(capsys: pytest.CaptureFixture) -> None:
    crt.clr_scr()
    assert capsys.readouterr().out == "\033[2J\033[H"


def test_goto_xy_schreibt_die_ansi_cursor_sequenz(capsys: pytest.CaptureFixture) -> None:
    crt.goto_xy(5, 10)
    assert capsys.readouterr().out == "\033[10;5H"


def test_text_color_mit_namen(capsys: pytest.CaptureFixture) -> None:
    crt.text_color("red")
    assert capsys.readouterr().out == "\033[31m"


def test_text_color_mit_zahl(capsys: pytest.CaptureFixture) -> None:
    crt.text_color(12)  # light_red
    assert capsys.readouterr().out == "\033[91m"


def test_text_color_mit_unbekanntem_namen_loest_value_error_aus() -> None:
    with pytest.raises(ValueError, match="Unbekannte Farbe"):
        crt.text_color("rosa")


def test_text_color_mit_zahl_ausserhalb_0_bis_15_loest_value_error_aus() -> None:
    with pytest.raises(ValueError, match="0 bis 15"):
        crt.text_color(99)


def test_text_background_mit_namen(capsys: pytest.CaptureFixture) -> None:
    crt.text_background("blue")
    assert capsys.readouterr().out == "\033[44m"


def test_delay_ruft_time_sleep_mit_sekunden_auf(monkeypatch: pytest.MonkeyPatch) -> None:
    aufgerufen = []
    monkeypatch.setattr(crt.time, "sleep", lambda sekunden: aufgerufen.append(sekunden))

    crt.delay(250)

    assert aufgerufen == [0.25]


def test_beep_ruft_winsound_mit_frequenz_und_dauer_auf(monkeypatch: pytest.MonkeyPatch) -> None:
    aufgerufen = []
    fake_winsound = types.ModuleType("winsound")
    fake_winsound.Beep = lambda frequenz, dauer: aufgerufen.append((frequenz, dauer))
    monkeypatch.setitem(sys.modules, "winsound", fake_winsound)

    crt.beep(440, 100)

    assert aufgerufen == [(440, 100)]


def test_read_key_liest_ein_zeichen_ueber_msvcrt(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_msvcrt = types.ModuleType("msvcrt")
    fake_msvcrt.getch = lambda: b"a"
    monkeypatch.setitem(sys.modules, "msvcrt", fake_msvcrt)

    assert crt.read_key() == "a"


def test_key_pressed_fragt_msvcrt_ab(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_msvcrt = types.ModuleType("msvcrt")
    fake_msvcrt.kbhit = lambda: True
    monkeypatch.setitem(sys.modules, "msvcrt", fake_msvcrt)

    assert crt.key_pressed() is True


def _getch_folge(monkeypatch: pytest.MonkeyPatch, *bytefolge: bytes) -> None:
    fake_msvcrt = types.ModuleType("msvcrt")
    folge = iter(bytefolge)
    fake_msvcrt.getch = lambda: next(folge)
    monkeypatch.setitem(sys.modules, "msvcrt", fake_msvcrt)


def test_read_key_liefert_pfeiltasten_mit_ihrem_namen(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Punkt 217: Windows meldet „Pfeil hoch“ als 0xE0 und „H“."""
    _getch_folge(monkeypatch, bytes([0xE0]), b"H", b"h")

    assert crt.read_key() == "Oben"
    # Das „H“ gehörte zur Pfeiltaste; der nächste Aufruf liest die
    # nächste Taste.
    assert crt.read_key() == "h"


def test_read_key_liefert_f_tasten_und_links(monkeypatch: pytest.MonkeyPatch) -> None:
    _getch_folge(
        monkeypatch,
        bytes([0x00]), b";",
        bytes([0xE0]), b"K",
        bytes([0xE0]), bytes([0x86]),
        bytes([0xE0]), bytes([0x73]),
    )

    assert [crt.read_key() for _ in range(4)] == ["F1", "Links", "F12", ""]
