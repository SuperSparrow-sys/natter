"""Abnahmetest für das Beispielprojekt CrtDemo (M6, Schritt 2).

Ruft `main()` direkt auf (reine Konsolenausgabe, kein Qt/Fenster nötig).
`msvcrt`/`winsound` werden wie in tests/test_crt.py über
`sys.modules`-Attrappen ersetzt, `time.sleep` gemockt, damit der Test
nicht wirklich wartet.
"""

from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path

import pytest

_PROJEKT_ORDNER = Path(__file__).resolve().parent.parent / "beispielprojekte" / "CrtDemo"


@pytest.fixture
def main_funktion():
    sys.path.insert(0, str(_PROJEKT_ORDNER))
    sys.modules.pop("main", None)
    try:
        modul = importlib.import_module("main")
        yield modul.main
    finally:
        sys.path.remove(str(_PROJEKT_ORDNER))
        sys.modules.pop("main", None)


def _tastatur_faelschen(monkeypatch: pytest.MonkeyPatch, taste: bytes) -> None:
    fake_msvcrt = types.ModuleType("msvcrt")
    zustand = {"angefragt": False}

    def kbhit() -> bool:
        wurde_gefragt = zustand["angefragt"]
        zustand["angefragt"] = True
        return wurde_gefragt

    fake_msvcrt.kbhit = kbhit
    fake_msvcrt.getch = lambda: taste
    monkeypatch.setitem(sys.modules, "msvcrt", fake_msvcrt)


def _bereitstellen(monkeypatch: pytest.MonkeyPatch, taste: bytes = b"x") -> list:
    _tastatur_faelschen(monkeypatch, taste)
    aufgerufen: list = []
    fake_winsound = types.ModuleType("winsound")
    fake_winsound.Beep = lambda *a, **k: aufgerufen.append((a, k))
    monkeypatch.setitem(sys.modules, "winsound", fake_winsound)
    monkeypatch.setattr("time.sleep", lambda sekunden: None)
    return aufgerufen


def test_crtdemo_zeigt_ueberschrift_und_reagiert_auf_tastendruck(
    main_funktion, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    _bereitstellen(monkeypatch, b"x")

    main_funktion()

    ausgabe = capsys.readouterr().out
    assert "CRT-Demo" in ausgabe
    assert "'x'" in ausgabe


def test_crtdemo_loescht_den_bildschirm_zuerst(
    main_funktion, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    _bereitstellen(monkeypatch, b"a")

    main_funktion()

    assert capsys.readouterr().out.startswith("\033[2J\033[H")


def test_crtdemo_piept_genau_einmal(
    main_funktion, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    aufgerufen = _bereitstellen(monkeypatch, b"a")

    main_funktion()
    capsys.readouterr()

    assert len(aufgerufen) == 1
