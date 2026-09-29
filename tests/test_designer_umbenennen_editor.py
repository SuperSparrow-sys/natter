"""Umbenennen im Designer, während die Unit im Editor offen ist
(Punkt 114). Nach dem Speichern müssen Unit und `.pfm` denselben
Methodennamen tragen. Headless.
"""

from __future__ import annotations

import json
from pathlib import Path

from ide.project.neu import projekt_erzeugen
from ide.shell.quelltexteditor import QuelltextEditor
from pcl import Button


def _vorbereiten(bauen, tmp_path: Path):
    projekt = projekt_erzeugen("gui", tmp_path, "Umrechner")
    fenster = bauen()
    fenster.projekt_oeffnen(projekt.ordner / "Umrechner.natter")
    pfm = projekt.ordner / "u_main.pfm"
    fenster.designer_oeffnen(pfm)
    canvas = fenster._aktueller_canvas
    knopf = canvas.komponente_platzieren(Button, 32, 128)
    assert canvas.ereignis_handler_erzeugen(knopf) == "button_click"
    editor = fenster.editor_tabs.currentWidget()
    assert isinstance(editor, QuelltextEditor)
    return fenster, canvas, knopf, editor, pfm, projekt.ordner / "u_main.py"


def _methode_in_pfm(pfm: Path) -> str:
    daten = json.loads(pfm.read_text(encoding="utf-8"))
    return next(
        kind["events"]["on_click"]
        for kind in daten["children"]
        if kind["type"] == "Button"
    )


def test_speichern_nach_umbenennen_behaelt_den_neuen_namen(
    tmp_path: Path, hauptfenster_bauen,
) -> None:
    fenster, canvas, knopf, editor, pfm, unit = _vorbereiten(hauptfenster_bauen, tmp_path)

    canvas.komponente_umbenennen(knopf, "b_los")

    assert "def b_los_click(" in editor.toPlainText()
    assert not editor.document().isModified()
    fenster.editor_tabs.setCurrentWidget(editor)
    fenster._aktuelle_datei_speichern()
    text = unit.read_text(encoding="utf-8")
    assert "def b_los_click(" in text
    assert "button_click" not in text
    assert _methode_in_pfm(pfm) == "b_los_click"


def test_ungespeicherte_aenderungen_bleiben_und_der_name_stimmt(
    tmp_path: Path, hauptfenster_bauen,
) -> None:
    fenster, canvas, knopf, editor, pfm, unit = _vorbereiten(hauptfenster_bauen, tmp_path)
    cursor = editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.End)
    cursor.insertText("\n# noch nicht gespeichert\n")
    assert editor.document().isModified()

    canvas.komponente_umbenennen(knopf, "b_los")

    assert editor.document().isModified()
    assert "# noch nicht gespeichert" in editor.toPlainText()
    assert fenster.alle_speichern()
    text = unit.read_text(encoding="utf-8")
    assert "def b_los_click(" in text
    assert "button_click" not in text
    assert "# noch nicht gespeichert" in text
    assert _methode_in_pfm(pfm) == "b_los_click"


def test_rueckgaengig_aendert_auch_den_offenen_editor(tmp_path: Path, hauptfenster_bauen) -> None:
    fenster, canvas, knopf, editor, pfm, unit = _vorbereiten(hauptfenster_bauen, tmp_path)
    canvas.komponente_umbenennen(knopf, "b_los")

    canvas.rueckgaengig()

    assert "def button_click(" in editor.toPlainText()
    assert "b_los_click" not in editor.toPlainText()
    fenster.editor_tabs.setCurrentWidget(editor)
    fenster._aktuelle_datei_speichern()
    assert "def button_click(" in unit.read_text(encoding="utf-8")
    assert _methode_in_pfm(pfm) == "button_click"
