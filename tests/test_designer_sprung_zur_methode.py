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


def _neues_projekt(bauen, tmp_path: Path):
    projekt = projekt_erzeugen("gui", tmp_path, "Umrechner")
    fenster = bauen()
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


def test_doppelklick_oeffnet_die_unit_in_der_methode(tmp_path: Path, hauptfenster_bauen) -> None:
    fenster, canvas, knopf, unit = _neues_projekt(hauptfenster_bauen, tmp_path)

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


def test_doppelklick_auf_eine_vorhandene_methode_springt_dorthin(
    tmp_path: Path, hauptfenster_bauen
) -> None:
    fenster, canvas, knopf, _unit = _neues_projekt(hauptfenster_bauen, tmp_path)
    name = canvas.ereignis_handler_erzeugen(knopf)
    fenster.editor_tabs.setCurrentIndex(0)

    canvas.ereignis_handler_erzeugen(knopf)

    editor = _aktueller_editor(fenster)
    davor = editor.textCursor().block().previous()
    while davor.isValid() and davor.text().strip().startswith("#"):
        davor = davor.previous()
    assert davor.text().strip().startswith(f"def {name}(")


def test_ungespeicherte_aenderungen_in_der_unit_bleiben_erhalten(
    tmp_path: Path, hauptfenster_bauen
) -> None:
    """Die Unit ist offen und verändert, aber nicht gespeichert. Die neue
    Methode muss in den Editor, und die eigenen Zeilen dürfen nicht
    verschwinden - sonst ginge beim Speichern eines von beiden
    verloren."""
    fenster, canvas, knopf, unit = _neues_projekt(hauptfenster_bauen, tmp_path)
    editor = fenster.datei_oeffnen(unit)
    editor.setPlainText(editor.toPlainText() + "\n# eigene Notiz, noch nicht gespeichert\n")
    editor.document().setModified(True)

    name = canvas.ereignis_handler_erzeugen(knopf)

    text = _aktueller_editor(fenster).toPlainText()
    assert f"def {name}(" in text
    assert "# eigene Notiz, noch nicht gespeichert" in text


def test_methode_anlegen_behaelt_den_rueckgaengig_verlauf(
    tmp_path: Path, hauptfenster_bauen
) -> None:
    """Punkt 248: die Methode wurde mit `setPlainText` eingefügt, und
    danach ließ sich nichts mehr zurücknehmen. Jetzt nimmt das erste
    Strg+Z die Methode heraus und das zweite die eigene Änderung."""
    from PySide6.QtGui import QTextCursor

    fenster, canvas, knopf, unit = _neues_projekt(hauptfenster_bauen, tmp_path)
    editor = fenster.datei_oeffnen(unit)
    ursprung = editor.toPlainText()
    cursor = QTextCursor(editor.document())
    cursor.insertText("# eigene Notiz\n")
    mit_notiz = editor.toPlainText()
    assert editor.document().isModified()

    name = canvas.ereignis_handler_erzeugen(knopf)

    editor = _aktueller_editor(fenster)
    assert f"def {name}(" in editor.toPlainText()
    assert editor.document().isModified()
    assert editor.document().isUndoAvailable()
    editor.undo()
    assert editor.toPlainText() == mit_notiz
    editor.undo()
    assert editor.toPlainText() == ursprung


def test_sprung_trifft_die_methode_auch_mit_zeilenumbruch(
    qtbot, tmp_path: Path, hauptfenster_bauen
) -> None:
    """In der installierten 0.3.4 umbrach der Editor die langen
    Kommentare der Projektvorlage. Der Sprung zählte mit „Zeile nach
    unten“ sichtbare statt echter Zeilen und markierte ein Stück
    Kommentar statt des `pass` in der neuen Methode."""
    fenster, canvas, knopf, _unit = _neues_projekt(hauptfenster_bauen, tmp_path)
    qtbot.addWidget(fenster)
    fenster.resize(900, 600)
    fenster.show()
    editor = fenster.datei_oeffnen(_unit)
    editor.zeilenumbruch_setzen(True)
    editor.resize(300, 400)
    fenster.editor_tabs.setCurrentIndex(0)

    name = canvas.ereignis_handler_erzeugen(knopf)

    editor = _aktueller_editor(fenster)
    assert editor.textCursor().selectedText() == "pass"
    davor = editor.textCursor().block().previous()
    while davor.isValid() and davor.text().strip().startswith("#"):
        davor = davor.previous()
    assert davor.text().strip().startswith(f"def {name}(")


def test_die_erste_methode_ersetzt_das_pass_der_leeren_klasse(
    tmp_path: Path, hauptfenster_bauen
) -> None:
    fenster, canvas, knopf, unit = _neues_projekt(hauptfenster_bauen, tmp_path)

    name = canvas.ereignis_handler_erzeugen(knopf)

    text = unit.read_text(encoding="utf-8")
    klasse = text[text.index("class Form1"):]
    assert klasse.splitlines()[1].strip().startswith(f"def {name}(")
    assert not [z for z in text.splitlines() if z and not z.strip()]
