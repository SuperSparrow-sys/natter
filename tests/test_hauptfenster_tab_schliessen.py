"""Tests für „×“ auf einem Editor-Tab (Abschnitt 7.9). Beim
Durchspielen der Bedienung entdeckt: `editor_tabs.tabCloseRequested`
war nie mit irgendeiner Methode verbunden – der Schließen-Knopf tat
buchstäblich nichts.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QMessageBox

from ide.shell.hauptfenster import HauptFenster


def _editor_mit_text(fenster: HauptFenster, tmp_path: Path, text: str, name: str = "u_main.py"):
    pfad = tmp_path / name
    pfad.write_text(text, encoding="utf-8")
    return fenster.datei_oeffnen(pfad)


def test_unveraenderter_tab_schliesst_sofort(tmp_path: Path) -> None:
    fenster = HauptFenster()
    _editor_mit_text(fenster, tmp_path, "x = 1\n")
    assert fenster.editor_tabs.count() == 1

    fenster._tab_schliessen(0)

    assert fenster.editor_tabs.count() == 0


def test_veraenderter_tab_fragt_nach_und_speichert_bei_save(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fenster = HauptFenster()
    editor = _editor_mit_text(fenster, tmp_path, "x = 1\n")
    editor.insertPlainText("zusatz")
    pfad = tmp_path / "u_main.py"

    monkeypatch.setattr(
        "ide.shell.hauptfenster.QMessageBox.question",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Save),
    )

    fenster._tab_schliessen(0)

    assert fenster.editor_tabs.count() == 0
    assert "zusatz" in pfad.read_text(encoding="utf-8")


def test_veraenderter_tab_bei_discard_verwirft_aenderungen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fenster = HauptFenster()
    editor = _editor_mit_text(fenster, tmp_path, "x = 1\n")
    editor.insertPlainText("zusatz")
    pfad = tmp_path / "u_main.py"

    monkeypatch.setattr(
        "ide.shell.hauptfenster.QMessageBox.question",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Discard),
    )

    fenster._tab_schliessen(0)

    assert fenster.editor_tabs.count() == 0
    assert "zusatz" not in pfad.read_text(encoding="utf-8")


def test_veraenderter_tab_bei_cancel_bleibt_offen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fenster = HauptFenster()
    editor = _editor_mit_text(fenster, tmp_path, "x = 1\n")
    editor.insertPlainText("zusatz")

    monkeypatch.setattr(
        "ide.shell.hauptfenster.QMessageBox.question",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Cancel),
    )

    fenster._tab_schliessen(0)

    assert fenster.editor_tabs.count() == 1


def test_designer_tab_schliesst_ohne_nachfrage_und_raeumt_buchhaltung_auf(
    tmp_path: Path,
) -> None:
    import shutil

    projekt_original = (
        Path(__file__).resolve().parent.parent / "beispielprojekte" / "04_CookieKlicker"
    )
    projekt_kopie = tmp_path / "CookieKlicker"
    shutil.copytree(projekt_original, projekt_kopie)

    fenster = HauptFenster()
    fenster.projekt_oeffnen(projekt_kopie / "04_CookieKlicker.natter")
    formular = fenster.designer_oeffnen(projekt_kopie / "u_main.pfm")
    assert fenster.editor_tabs.count() == 1
    assert formular._qwidget in fenster._widget_zu_canvas

    fenster._tab_schliessen(0)

    assert fenster.editor_tabs.count() == 0
    assert formular._qwidget not in fenster._widget_zu_canvas
    assert str(projekt_kopie / "u_main.pfm") not in fenster._pfad_zu_formular
