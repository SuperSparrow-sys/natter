"""Punkt 306: „Projekt → Projekt schließen“ schließt das Projekt,
ohne ein anderes zu öffnen - mit derselben Nachfrage wie beim
Wechsel."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QMessageBox

from ide.project import projekt_erzeugen
from ide.shell.hauptfenster import HauptFenster


def _mit_projekt(hauptfenster_bauen, tmp_path: Path) -> HauptFenster:
    projekt = projekt_erzeugen("gui", tmp_path / "Ampel", "Ampel")
    fenster = hauptfenster_bauen()
    fenster.projekt_oeffnen(projekt.ordner / "Ampel.natter")
    fenster.designer_oeffnen(projekt.ordner / "u_main.pfm")
    fenster.datei_oeffnen(projekt.ordner / "u_main.py")
    return fenster


def test_menueeintrag_steht_im_projektmenue(hauptfenster_bauen) -> None:
    fenster = hauptfenster_bauen()
    texte = [a.text() for a in fenster.menue("Projekt").actions()]

    assert "Projekt schließen" in texte


def test_projekt_schliessen_zeigt_die_startseite(
    hauptfenster_bauen, tmp_path: Path
) -> None:
    fenster = _mit_projekt(hauptfenster_bauen, tmp_path)
    assert fenster.editor_tabs.count() >= 2
    assert fenster.objektinspektor.baum.topLevelItemCount() > 0

    fenster.aktionen["projekt.schliessen"].qaction.trigger()

    assert fenster.projekt is None
    assert fenster.mitte.currentWidget() is fenster.startbild
    assert fenster.editor_tabs.count() == 0
    assert fenster.objektinspektor.formular is None
    assert fenster.objektinspektor.baum.topLevelItemCount() == 0
    assert fenster.objektinspektor.eigenschaften_tabelle.rowCount() == 0
    sichtbar = [
        fenster.explorer.topLevelItem(i)
        for i in range(fenster.explorer.topLevelItemCount())
        if not fenster.explorer.topLevelItem(i).isHidden()
    ]
    assert sichtbar == []
    assert "geschlossen" in fenster.statusBar().currentMessage()


def test_abbrechen_laesst_das_projekt_offen(
    hauptfenster_bauen, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fenster = _mit_projekt(hauptfenster_bauen, tmp_path)
    editor = fenster.editor_tabs.currentWidget()
    editor.insertPlainText("# geändert\n")
    monkeypatch.setattr(
        HauptFenster,
        "_vor_dem_schliessen_fragen",
        lambda self, namen: QMessageBox.StandardButton.Cancel,
    )

    assert not fenster.projekt_schliessen()

    assert fenster.projekt is not None
    assert fenster.editor_tabs.count() >= 2


def test_ohne_projekt_nur_ein_hinweis(hauptfenster_bauen) -> None:
    fenster = hauptfenster_bauen()

    assert not fenster.projekt_schliessen()
    assert "kein Projekt" in fenster.statusBar().currentMessage()
