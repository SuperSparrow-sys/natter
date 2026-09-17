"""Abnahmetest für das Beispielprojekt Konsolenrechner: prüft den
Projekttyp "console" (Abschnitt 7.8) end-to-end über echte
`input()`/`print()`-Ein-/Ausgabe, ganz ohne Qt.

Ruft `main()` direkt auf und ersetzt `input()` durch eine Warteschlange
vorbereiteter Eingaben (wie ein Schüler sie eintippen würde), wie
tests/test_beispiel_crtdemo.py es für `main()`+`capsys` vormacht.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

_PROJEKT_ORDNER = Path(__file__).resolve().parent.parent / "beispielprojekte" / "Konsolenrechner"


@pytest.fixture
def konsolenrechner_modul():
    sys.path.insert(0, str(_PROJEKT_ORDNER))
    sys.modules.pop("main", None)
    try:
        yield importlib.import_module("main")
    finally:
        sys.path.remove(str(_PROJEKT_ORDNER))
        sys.modules.pop("main", None)


def _eingaben_bereitstellen(monkeypatch: pytest.MonkeyPatch, werte: list[str]) -> None:
    folge = iter(werte)
    monkeypatch.setattr("builtins.input", lambda *_: next(folge))


def test_addition(konsolenrechner_modul, monkeypatch, capsys: pytest.CaptureFixture) -> None:
    _eingaben_bereitstellen(monkeypatch, ["3 + 4", "ende"])

    konsolenrechner_modul.main()

    ausgabe = capsys.readouterr().out
    assert "Ergebnis: 7.0" in ausgabe
    assert "Bis bald!" in ausgabe


def test_division_durch_null_zeigt_fehlermeldung_statt_absturz(
    konsolenrechner_modul, monkeypatch, capsys: pytest.CaptureFixture
) -> None:
    _eingaben_bereitstellen(monkeypatch, ["5 / 0", "ende"])

    konsolenrechner_modul.main()  # darf nicht mit ZeroDivisionError abstürzen

    ausgabe = capsys.readouterr().out
    assert "Division durch 0 ist nicht erlaubt." in ausgabe


def test_ungueltige_zahl_zeigt_fehlermeldung_und_fragt_erneut(
    konsolenrechner_modul, monkeypatch, capsys: pytest.CaptureFixture
) -> None:
    _eingaben_bereitstellen(monkeypatch, ["abc + 4", "2 + 2", "ende"])

    konsolenrechner_modul.main()

    ausgabe = capsys.readouterr().out
    assert "Das sind keine gültigen Zahlen." in ausgabe
    assert "Ergebnis: 4.0" in ausgabe


def test_falsches_format_wird_abgewiesen(
    konsolenrechner_modul, monkeypatch, capsys: pytest.CaptureFixture
) -> None:
    _eingaben_bereitstellen(monkeypatch, ["3 plus 4 gleich", "ende"])

    konsolenrechner_modul.main()

    ausgabe = capsys.readouterr().out
    assert "Bitte genau 'Zahl Operator Zahl' eingeben." in ausgabe


def test_berechnen_alle_operatoren() -> None:
    sys.path.insert(0, str(_PROJEKT_ORDNER))
    sys.modules.pop("main", None)
    try:
        modul = importlib.import_module("main")
        assert modul.berechnen(3, "+", 4) == 7
        assert modul.berechnen(3, "-", 4) == -1
        assert modul.berechnen(3, "*", 4) == 12
        assert modul.berechnen(8, "/", 4) == 2
        assert modul.berechnen(1, "%", 1) is None
    finally:
        sys.path.remove(str(_PROJEKT_ORDNER))
        sys.modules.pop("main", None)
