"""Wechsel des Projekts: Reiter des vorigen gehen zu, nach der
Nachfrage wie beim Beenden (Punkt 152), und ein neu angelegtes
Projekt steht unter „Zuletzt geöffnet“ (Punkt 153).

Die Beispielprojekte werden vorher nach `tmp_path` kopiert: der
Designer schreibt jede Änderung in die `.pfm` zurück."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QDialog, QMessageBox

from ide.shell.hauptfenster import _PFAD_EIGENSCHAFT, HauptFenster
from ide.shell.startbild import zuletzt_geoeffnet

_BEISPIELE = Path(__file__).resolve().parent.parent / "beispielprojekte"


def _kopie(tmp_path: Path, name: str) -> Path:
    ziel = tmp_path / name
    shutil.copytree(_BEISPIELE / name, ziel)
    return next(ziel.glob("*.natter"))


def _reiter_pfade(fenster: HauptFenster) -> list[Path]:
    return [
        p
        for p in (fenster._reiter_pfad(i) for i in range(fenster.editor_tabs.count()))
        if p is not None
    ]


def _antwort(monkeypatch: pytest.MonkeyPatch, knopf) -> list[list[str]]:
    gefragt: list[list[str]] = []

    def fragen(_self, namen):
        gefragt.append(list(namen))
        return knopf

    monkeypatch.setattr(HauptFenster, "_vor_dem_schliessen_fragen", fragen)
    return gefragt


def _geaendert_oeffnen(fenster: HauptFenster, tmp_path: Path) -> Path:
    fenster.projekt_oeffnen(_kopie(tmp_path, "03_Taschenrechner"))
    unit = fenster.projekt.ordner / "u_main.py"
    editor = fenster.datei_oeffnen(unit)
    # Über den Cursor: `setPlainText` gilt nicht als Änderung.
    editor.moveCursor(QTextCursor.MoveOperation.End)
    editor.insertPlainText("\n# geändert\n")
    fenster.designer_oeffnen(fenster.projekt.ordner / "u_main.pfm")
    return unit


def test_abbrechen_laesst_das_vorige_projekt_offen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hauptfenster
) -> None:
    unit = _geaendert_oeffnen(hauptfenster, tmp_path)
    altes = hauptfenster.projekt
    gefragt = _antwort(monkeypatch, QMessageBox.StandardButton.Cancel)

    hauptfenster.projekt_oeffnen(_kopie(tmp_path, "02_Zahlenraten"))

    assert gefragt == [["u_main.py"]]
    assert hauptfenster.projekt is altes
    assert unit.resolve() in _reiter_pfade(hauptfenster)
    assert hauptfenster.editor_tabs.count() == 2


def test_verwerfen_schliesst_alle_reiter_des_vorigen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hauptfenster
) -> None:
    unit = _geaendert_oeffnen(hauptfenster, tmp_path)
    vorher = unit.read_text(encoding="utf-8")
    gefragt = _antwort(monkeypatch, QMessageBox.StandardButton.Discard)

    neu = hauptfenster.projekt_oeffnen(_kopie(tmp_path, "02_Zahlenraten"))
    hauptfenster.datei_oeffnen(neu.ordner / "u_main.py")

    assert gefragt == [["u_main.py"]]
    assert _reiter_pfade(hauptfenster) == [(neu.ordner / "u_main.py").resolve()]
    assert hauptfenster._pfad_zu_formular == {}
    assert unit.read_text(encoding="utf-8") == vorher


def test_speichern_schreibt_vor_dem_wechsel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hauptfenster
) -> None:
    unit = _geaendert_oeffnen(hauptfenster, tmp_path)
    _antwort(monkeypatch, QMessageBox.StandardButton.Save)

    hauptfenster.projekt_oeffnen(_kopie(tmp_path, "02_Zahlenraten"))

    assert unit.read_text(encoding="utf-8").endswith("# geändert\n")
    assert hauptfenster.editor_tabs.count() == 0


def test_dasselbe_projekt_erneut_oeffnen_fragt_nicht(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hauptfenster
) -> None:
    _geaendert_oeffnen(hauptfenster, tmp_path)
    gefragt = _antwort(monkeypatch, QMessageBox.StandardButton.Cancel)

    hauptfenster.projekt_oeffnen(hauptfenster.projekt.ordner / "03_Taschenrechner.natter")

    assert gefragt == []
    assert hauptfenster.editor_tabs.count() == 2


def test_dateien_ausserhalb_des_projekts_bleiben_offen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hauptfenster
) -> None:
    hauptfenster.projekt_oeffnen(_kopie(tmp_path, "03_Taschenrechner"))
    fremd = tmp_path / "notizen.py"
    fremd.write_text("x = 1\n", encoding="utf-8")
    editor = hauptfenster.datei_oeffnen(fremd)

    hauptfenster.projekt_oeffnen(_kopie(tmp_path, "02_Zahlenraten"))

    assert editor.property(_PFAD_EIGENSCHAFT) == str(fremd)
    assert hauptfenster.editor_tabs.indexOf(editor) != -1


class _AttrappenDialog:
    def __init__(self, werte: tuple[str, Path, str]) -> None:
        self._werte = werte

    def exec(self) -> int:
        return QDialog.DialogCode.Accepted

    def werte(self) -> tuple[str, Path, str]:
        return self._werte


def test_neues_projekt_steht_unter_zuletzt_geoeffnet(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hauptfenster
) -> None:
    attrappe = _AttrappenDialog(("gui", tmp_path / "Garten", "Garten"))
    monkeypatch.setattr(
        "ide.shell.hauptfenster.NeuesProjektDialog", lambda parent=None: attrappe
    )

    hauptfenster._neues_projekt_dialog()

    liste = zuletzt_geoeffnet(hauptfenster._design_einstellungen)
    assert liste[0].resolve() == (tmp_path / "Garten" / "Garten.natter").resolve()
    hauptfenster._zuletzt_menue_aufbauen()
    assert hauptfenster._zuletzt_menue.actions()[0].text() == "Garten"


def test_neues_projekt_fragt_nach_ungespeicherten_aenderungen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hauptfenster
) -> None:
    _geaendert_oeffnen(hauptfenster, tmp_path)
    altes = hauptfenster.projekt
    gefragt = _antwort(monkeypatch, QMessageBox.StandardButton.Cancel)
    attrappe = _AttrappenDialog(("gui", tmp_path / "Garten", "Garten"))
    monkeypatch.setattr(
        "ide.shell.hauptfenster.NeuesProjektDialog", lambda parent=None: attrappe
    )

    hauptfenster._neues_projekt_dialog()

    assert gefragt == [["u_main.py"]]
    assert hauptfenster.projekt is altes
    assert not (tmp_path / "Garten").exists()
