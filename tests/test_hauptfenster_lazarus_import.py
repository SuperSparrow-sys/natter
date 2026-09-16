"""Tests für „Werkzeuge → Lazarus-Formular importieren …“ (Abschnitt 15).
Siehe docs/arbeitspakete/M8.md, Schritt 3. Ein eigenes, minimales `.lfm`
in `tmp_path` (kein Zugriff auf `referenz/lazarus/`, dessen echte
Dateien sind bereits in tests/test_lfm_parser.py/test_lfm_zuordnung.py
abgedeckt - hier nur die IDE-Verdrahtung).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PySide6.QtWidgets import QFileDialog

from ide.shell.hauptfenster import HauptFenster

_LFM_TEXT = """\
object Form1: TForm1
  Left = 100
  Top = 100
  Width = 400
  Height = 300
  Caption = 'Form1'
  OnCreate = FormCreate
  object b_start: TButton
    Left = 8
    Top = 8
    Width = 75
    Height = 24
    Caption = 'Start'
    OnClick = b_startClick
  end
  object t_x: TTrackBar
    Left = 8
    Top = 40
  end
end
"""


def _dialoge_vorbereiten(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, quelle: Path, ziel: Path
) -> None:
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(quelle), ""))
    )
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(ziel), ""))
    )


def test_import_erzeugt_gueltiges_pfm_und_oeffnet_den_designer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    quelle = tmp_path / "unit1.lfm"
    quelle.write_text(_LFM_TEXT, encoding="utf-8")
    ziel = tmp_path / "u_main.pfm"
    _dialoge_vorbereiten(monkeypatch, tmp_path, quelle=quelle, ziel=ziel)
    fenster = HauptFenster()

    fenster._lazarus_formular_importieren_aktion()

    assert ziel.exists()
    daten = json.loads(ziel.read_text(encoding="utf-8"))
    assert daten["children"][0]["name"] == "b_start"
    assert daten["children"][0]["events"] == {"on_click": "b_start_click"}

    assert fenster.editor_tabs.count() == 1
    formular = fenster._offene_canvases[0].formular
    assert formular.b_start.caption == "Start"


def test_import_zeigt_importbericht_fuer_nicht_unterstuetzte_komponente(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    quelle = tmp_path / "unit1.lfm"
    quelle.write_text(_LFM_TEXT, encoding="utf-8")
    ziel = tmp_path / "u_main.pfm"
    _dialoge_vorbereiten(monkeypatch, tmp_path, quelle=quelle, ziel=ziel)
    fenster = HauptFenster()

    fenster._lazarus_formular_importieren_aktion()

    meldungen = [
        fenster.meldungen_liste.item(i).text() for i in range(fenster.meldungen_liste.count())
    ]
    assert any("TTrackBar" in m for m in meldungen)
    assert fenster.panels.currentWidget() is fenster.meldungen_liste


def test_import_abgebrochen_bei_der_quelle_tut_nichts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: ("", "")))
    fenster = HauptFenster()

    fenster._lazarus_formular_importieren_aktion()

    assert fenster.editor_tabs.count() == 0


def test_import_abgebrochen_beim_ziel_schreibt_keine_datei(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    quelle = tmp_path / "unit1.lfm"
    quelle.write_text(_LFM_TEXT, encoding="utf-8")
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(quelle), ""))
    )
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: ("", "")))
    fenster = HauptFenster()

    fenster._lazarus_formular_importieren_aktion()

    assert fenster.editor_tabs.count() == 0


def test_import_mit_ungueltigem_lfm_zeigt_fehlermeldung(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    quelle = tmp_path / "kaputt.lfm"
    quelle.write_text("das ist kein lfm", encoding="utf-8")
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(quelle), ""))
    )
    fenster = HauptFenster()

    fenster._lazarus_formular_importieren_aktion()

    assert "fehlgeschlagen" in fenster.statusBar().currentMessage()
    assert fenster.editor_tabs.count() == 0
