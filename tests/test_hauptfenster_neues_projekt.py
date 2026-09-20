"""Tests für „Projekt → Neues Projekt …“ (Abschnitt 7.2).

Rückmeldung (beim Blick auf das Projekt-Menü: „ist
da alles?“): `projekt_erzeugen` existierte bereits (seit M2), war aber
aus der laufenden IDE heraus nirgends erreichbar – kein Menüeintrag, kein
Dialog. `NeuesProjektDialog` selbst wird hier über eine einfache
Attrappe ersetzt statt echter Modal-Interaktion, wie an anderer Stelle in
dieser Datei üblich (siehe z. B. tests/test_hauptfenster_pakete.py).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QDialog

from ide.shell.hauptfenster import HauptFenster


class _AttrappenDialog:
    def __init__(self, ergebnis: int, werte: tuple[str, Path, str] | None) -> None:
        self._ergebnis = ergebnis
        self._werte = werte

    def exec(self) -> int:
        return self._ergebnis

    def werte(self) -> tuple[str, Path, str] | None:
        return self._werte


def test_neues_projekt_legt_es_an_und_zeigt_es_im_explorer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fenster = HauptFenster()
    attrappe = _AttrappenDialog(QDialog.DialogCode.Accepted, ("gui", tmp_path / "Test", "Test"))
    monkeypatch.setattr("ide.shell.hauptfenster.NeuesProjektDialog", lambda parent=None: attrappe)

    fenster._neues_projekt_dialog()

    assert fenster.projekt is not None
    assert fenster.projekt.name == "Test"
    assert (tmp_path / "Test" / "Test.natter").exists()
    formulare = [
        fenster.explorer.formulare_gruppe.child(i).text(0)
        for i in range(fenster.explorer.formulare_gruppe.childCount())
    ]
    assert formulare == ["u_main"]


def test_neues_projekt_abgebrochen_tut_nichts(monkeypatch: pytest.MonkeyPatch) -> None:
    fenster = HauptFenster()
    attrappe = _AttrappenDialog(QDialog.DialogCode.Rejected, None)
    monkeypatch.setattr("ide.shell.hauptfenster.NeuesProjektDialog", lambda parent=None: attrappe)

    fenster._neues_projekt_dialog()

    assert fenster.projekt is None


def test_neues_projekt_ohne_name_oder_ordner_zeigt_hinweis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fenster = HauptFenster()
    attrappe = _AttrappenDialog(QDialog.DialogCode.Accepted, None)
    monkeypatch.setattr("ide.shell.hauptfenster.NeuesProjektDialog", lambda parent=None: attrappe)

    fenster._neues_projekt_dialog()

    meldung = fenster.statusBar().currentMessage()
    assert meldung.startswith("Name und Ordner werden benötigt")
    assert "ausfüllen" in meldung


def test_neues_projekt_in_nicht_leerem_ordner_zeigt_fehlermeldung(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ziel = tmp_path / "Test"
    ziel.mkdir()
    (ziel / "vorhanden.txt").write_text("x", encoding="utf-8")
    fenster = HauptFenster()
    attrappe = _AttrappenDialog(QDialog.DialogCode.Accepted, ("gui", ziel, "Test"))
    monkeypatch.setattr("ide.shell.hauptfenster.NeuesProjektDialog", lambda parent=None: attrappe)

    fenster._neues_projekt_dialog()

    assert "konnte nicht angelegt werden" in fenster.statusBar().currentMessage()
