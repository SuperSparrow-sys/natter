"""Doppelklick auf eine Komponente: Methode anlegen und hinspringen
(Punkt 37 der offenen Punkte).

Bis 0.3.3 legte der Designer die Methode in `u_main.py` an, öffnete die
Unit aber nicht. Handbuch und Tastenübersicht versprechen „anlegen und
hinspringen“. Hier nachgestellt wie im Schülerweg: neues GUI-Projekt,
Button platzieren, Doppelklick (den löst `ereignis_handler_erzeugen`
aus, wie in `canvas.py` beim `MouseButtonDblClick`).
"""

from __future__ import annotations

from pathlib import Path

from ide.project.neu import projekt_erzeugen
from ide.shell.hauptfenster import HauptFenster
from ide.shell.quelltexteditor import QuelltextEditor
from pcl import Button


def _neues_projekt(tmp_path: Path):
    projekt = projekt_erzeugen("gui", tmp_path, "Umrechner")
    fenster = HauptFenster()
    fenster.projekt_oeffnen(projekt.ordner / "Umrechner.natter")
    pfm = projekt.ordner / "u_main.pfm"
    fenster.designer_oeffnen(pfm)
    canvas = fenster._aktueller_canvas
    knopf = canvas.komponente_platzieren(Button, 32, 128)
    return fenster, canvas, knopf, projekt.ordner / "u_main.py"


def _aktueller_editor(fenster: HauptFenster) -> QuelltextEditor:
    editor = fenster.editor_tabs.currentWidget()
    assert isinstance(editor, QuelltextEditor)
    return editor


def test_doppelklick_oeffnet_die_unit_in_der_methode(tmp_path: Path) -> None:
    fenster, canvas, knopf, unit = _neues_projekt(tmp_path)

    name = canvas.ereignis_handler_erzeugen(knopf)

    editor = _aktueller_editor(fenster)
    assert fenster.editor_tabs.tabText(fenster.editor_tabs.currentIndex()) == unit.name
    zeile = editor.textCursor().block().text()
    davor = editor.textCursor().block().previous()
    # Cursor steht im Rumpf der neuen Methode, `pass` ist markiert
    assert editor.textCursor().selectedText() == "pass" or zeile.strip().startswith("pass")
    while davor.isValid() and davor.text().strip().startswith("#"):
        davor = davor.previous()
    assert davor.text().strip().startswith(f"def {name}(")


def test_doppelklick_auf_eine_vorhandene_methode_springt_dorthin(tmp_path: Path) -> None:
    fenster, canvas, knopf, _unit = _neues_projekt(tmp_path)
    name = canvas.ereignis_handler_erzeugen(knopf)
    fenster.editor_tabs.setCurrentIndex(0)

    canvas.ereignis_handler_erzeugen(knopf)

    editor = _aktueller_editor(fenster)
    davor = editor.textCursor().block().previous()
    while davor.isValid() and davor.text().strip().startswith("#"):
        davor = davor.previous()
    assert davor.text().strip().startswith(f"def {name}(")


def test_ungespeicherte_aenderungen_in_der_unit_bleiben_erhalten(tmp_path: Path) -> None:
    """Die Unit ist offen und verändert, aber nicht gespeichert. Die neue
    Methode muss in den Editor, und die eigenen Zeilen dürfen nicht
    verschwinden - sonst ginge beim Speichern eines von beiden
    verloren."""
    fenster, canvas, knopf, unit = _neues_projekt(tmp_path)
    editor = fenster.datei_oeffnen(unit)
    editor.setPlainText(editor.toPlainText() + "\n# eigene Notiz, noch nicht gespeichert\n")
    editor.document().setModified(True)

    name = canvas.ereignis_handler_erzeugen(knopf)

    text = _aktueller_editor(fenster).toPlainText()
    assert f"def {name}(" in text
    assert "# eigene Notiz, noch nicht gespeichert" in text
