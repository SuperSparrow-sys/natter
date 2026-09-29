"""Beenden mit ungespeicherten Änderungen (Punkt 84), „Alle
speichern“, „Beenden“ und „Weitersuchen“ (Punkt 85)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PySide6.QtWidgets import QMessageBox

from ide.shell.hauptfenster import HauptFenster


@pytest.fixture
def fenster(hauptfenster_bauen, tmp_path: Path) -> HauptFenster:
    (tmp_path / "main.py").write_text("a = 1\n", encoding="utf-8")
    (tmp_path / "u_zwei.py").write_text("b = 2\n", encoding="utf-8")
    natter = tmp_path / "t.natter"
    natter.write_text(json.dumps({
        "format": "natter-project/1", "name": "T", "type": "console", "main": "main.py",
    }), encoding="utf-8")
    fenster = hauptfenster_bauen()
    fenster.projekt_oeffnen(natter)
    fenster.show()
    return fenster


def _aendern(fenster: HauptFenster, pfad: Path, text: str):  # noqa: ANN202
    editor = fenster.datei_oeffnen(pfad)
    editor.setPlainText(text)
    editor.document().setModified(True)
    return editor


def test_beenden_fragt_und_abbrechen_laesst_das_fenster_offen(
    fenster: HauptFenster, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _aendern(fenster, tmp_path / "main.py", "a = 42\n")
    gefragt = []

    def fragen(self, namen):  # noqa: ANN001, ANN202
        gefragt.append(namen)
        return QMessageBox.StandardButton.Cancel

    monkeypatch.setattr(HauptFenster, "_vor_dem_schliessen_fragen", fragen)

    assert not fenster.close()
    assert gefragt == [["main.py"]]
    assert fenster.isVisible()
    assert (tmp_path / "main.py").read_text(encoding="utf-8") == "a = 1\n"


def test_beenden_mit_speichern_schreibt_alles(
    fenster: HauptFenster, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _aendern(fenster, tmp_path / "main.py", "a = 42\n")
    _aendern(fenster, tmp_path / "u_zwei.py", "b = 43\n")
    monkeypatch.setattr(
        HauptFenster, "_vor_dem_schliessen_fragen",
        lambda self, namen: QMessageBox.StandardButton.Save,
    )

    fenster.aktionen["datei.beenden"].qaction.trigger()

    assert not fenster.isVisible()
    assert (tmp_path / "main.py").read_text(encoding="utf-8") == "a = 42\n"
    assert (tmp_path / "u_zwei.py").read_text(encoding="utf-8") == "b = 43\n"


def test_ohne_aenderungen_wird_nicht_gefragt(
    fenster: HauptFenster, monkeypatch: pytest.MonkeyPatch
) -> None:
    def nicht_fragen(self, namen):  # noqa: ANN001, ANN202
        raise AssertionError("Es gab nichts zu fragen")

    monkeypatch.setattr(HauptFenster, "_vor_dem_schliessen_fragen", nicht_fragen)

    assert fenster.close()


def test_alle_speichern(fenster: HauptFenster, tmp_path: Path) -> None:
    eins = _aendern(fenster, tmp_path / "main.py", "a = 42\n")
    zwei = _aendern(fenster, tmp_path / "u_zwei.py", "b = 43\n")

    fenster.aktionen["datei.alle_speichern"].qaction.trigger()

    assert (tmp_path / "main.py").read_text(encoding="utf-8") == "a = 42\n"
    assert (tmp_path / "u_zwei.py").read_text(encoding="utf-8") == "b = 43\n"
    assert not eins.document().isModified() and not zwei.document().isModified()
    assert fenster.statusBar().currentMessage() == "2 Dateien gespeichert."


def test_beenden_steht_als_letztes_im_menue_datei(fenster: HauptFenster) -> None:
    eintraege = [a.text() for a in fenster._menues["Datei"].actions() if a.text()]

    assert eintraege[-1] == "Beenden"


def test_f3_sucht_weiter(fenster: HauptFenster, tmp_path: Path) -> None:
    editor = _aendern(fenster, tmp_path / "main.py", "x = 1\nx = 2\nx = 3\n")
    fenster._suchen_aktion()
    fenster._suchen_dialog.suchfeld.setText("x =")
    fenster._suchen_dialog.suchen()
    assert editor.textCursor().blockNumber() == 0

    fenster.aktionen["suchen.weitersuchen"].qaction.trigger()
    assert editor.textCursor().blockNumber() == 1
    fenster.aktionen["suchen.weitersuchen"].qaction.trigger()
    assert editor.textCursor().blockNumber() == 2


def test_beenden_nennt_und_speichert_geaenderte_diagramme(
    fenster: HauptFenster, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Punkt 111: auch ein offenes, geändertes Diagramm gehört zur
    Frage beim Beenden und zu „Alle speichern“."""
    from ide.diagramm import diagramm_erzeugen

    pfad = tmp_path / "diagramme" / "ablauf.pdiag"
    pfad.parent.mkdir()
    diagramm_erzeugen("struktogramm", pfad, "ablauf")
    diagrammfenster = fenster.diagramm_oeffnen(pfad)
    diagrammfenster.diagramm.daten["name"] = "geaendert"
    diagrammfenster._geaendert = True
    gefragt = []

    def fragen(self, namen):  # noqa: ANN001, ANN202
        gefragt.append(namen)
        return QMessageBox.StandardButton.Save

    monkeypatch.setattr(HauptFenster, "_vor_dem_schliessen_fragen", fragen)

    assert fenster.close()
    assert gefragt == [["ablauf.pdiag"]]
    assert '"geaendert"' in pfad.read_text(encoding="utf-8")
