"""Tests für ide/diagramm/textbearbeitung.py: Formen direkt beschriften
(M9, Schritt 5). Headless.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QLineEdit, QPlainTextEdit

from ide.diagramm import diagramm_erzeugen
from ide.diagramm.canvas import DiagrammCanvas
from ide.diagramm.textbearbeitung import FELDER
from ide.diagramm.zeichnen import klassen_bereiche


@pytest.fixture
def canvas(tmp_path: Path) -> DiagrammCanvas:
    return DiagrammCanvas(diagramm_erzeugen("class", tmp_path / "k.pdiag", "k"))


def _doppelklick(x: float, y: float) -> QMouseEvent:
    return QMouseEvent(
        QEvent.Type.MouseButtonDblClick,
        QPointF(x, y),
        QPointF(x, y),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )


def test_doppelklick_oeffnet_die_eingabefelder(canvas: DiagrammCanvas) -> None:
    form = canvas.form_platzieren("class", 200, 200)

    canvas.mouseDoubleClickEvent(
        _doppelklick(form["x"] + form["w"] / 2, form["y"] + form["h"] / 2)
    )

    editor = canvas._editor
    assert editor is not None
    assert set(editor._felder) == set(FELDER)
    assert isinstance(editor._felder["name"], QLineEdit)
    assert isinstance(editor._felder["attributes"], QPlainTextEdit)


def test_doppelklick_ins_leere_oeffnet_nichts(canvas: DiagrammCanvas) -> None:
    canvas.form_platzieren("class", 200, 200)

    canvas.mouseDoubleClickEvent(_doppelklick(600, 440))

    assert canvas._editor is None


def test_felder_liegen_ueber_ihren_bereichen(canvas: DiagrammCanvas) -> None:
    """Abschnitt 13.3: „bearbeitet direkt in der Form“ – die Felder
    müssen genau dort liegen, wo der Text gezeichnet wird."""
    form = canvas.form_platzieren("class", 300, 300)
    editor = canvas.bearbeiten_starten(form)
    bereiche = klassen_bereiche(form)

    for name, feld in editor._felder.items():
        erwartet = bereiche[name].translated(-form["x"], -form["y"]).toRect()
        assert feld.geometry() == erwartet


def test_eingabe_wird_uebernommen(canvas: DiagrammCanvas) -> None:
    form = canvas.form_platzieren("class", 200, 200)
    editor = canvas.bearbeiten_starten(form)

    editor._felder["name"].setText("TAmpel")
    editor._felder["attributes"].setPlainText("-an: bool\n-zustand: int")
    editor._felder["methods"].setPlainText("+einschalten()")
    editor.uebernehmen()

    assert form["text"] == {
        "name": "TAmpel",
        "attributes": ["-an: bool", "-zustand: int"],
        "methods": ["+einschalten()"],
    }
    assert canvas._editor is None


def test_leere_zeilen_fallen_weg(canvas: DiagrammCanvas) -> None:
    """Ein versehentliches Enter am Ende soll keine leere Attributzeile
    hinterlassen."""
    form = canvas.form_platzieren("class", 200, 200)
    editor = canvas.bearbeiten_starten(form)

    editor._felder["attributes"].setPlainText("-an: bool\n\n   \n")
    editor.uebernehmen()

    assert form["text"]["attributes"] == ["-an: bool"]


def test_uebernehmen_ist_ein_undo_schritt(canvas: DiagrammCanvas) -> None:
    form = canvas.form_platzieren("class", 200, 200)
    vorher = dict(form["text"])
    editor = canvas.bearbeiten_starten(form)
    editor._felder["name"].setText("TAmpel")
    editor.uebernehmen()

    canvas.rueckgaengig()

    assert form["text"] == vorher


def test_form_waechst_mit_dem_neuen_text_mit(canvas: DiagrammCanvas) -> None:
    form = canvas.form_platzieren("class", 200, 200)
    vorher = form["h"]
    editor = canvas.bearbeiten_starten(form)

    editor._felder["methods"].setPlainText("\n".join(f"+m{i}()" for i in range(8)))
    editor.uebernehmen()

    assert form["h"] > vorher


def test_abbrechen_laesst_den_text_unveraendert(canvas: DiagrammCanvas) -> None:
    form = canvas.form_platzieren("class", 200, 200)
    vorher = dict(form["text"])
    editor = canvas.bearbeiten_starten(form)

    editor._felder["name"].setText("Nicht übernehmen")
    editor.abbrechen()

    assert form["text"] == vorher
    assert canvas._editor is None


def test_escape_bricht_die_eingabe_ab(canvas: DiagrammCanvas) -> None:
    form = canvas.form_platzieren("class", 200, 200)
    editor = canvas.bearbeiten_starten(form)
    editor._felder["name"].setText("Verworfen")

    editor.eventFilter(
        editor._felder["name"],
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier),
    )

    assert form["text"]["name"] != "Verworfen"


def test_strg_eingabe_uebernimmt(canvas: DiagrammCanvas) -> None:
    form = canvas.form_platzieren("class", 200, 200)
    editor = canvas.bearbeiten_starten(form)
    editor._felder["name"].setText("TAmpel")

    editor.eventFilter(
        editor._felder["name"],
        QKeyEvent(
            QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.ControlModifier
        ),
    )

    assert form["text"]["name"] == "TAmpel"


def test_strg_pfeil_sortiert_zeilen_um(canvas: DiagrammCanvas) -> None:
    """Abschnitt 13.4: „Zeilen … per Strg+Pfeil umsortieren“."""
    form = canvas.form_platzieren("class", 200, 200)
    editor = canvas.bearbeiten_starten(form)
    feld = editor._felder["methods"]
    feld.setPlainText("+zweite()\n+erste()")
    cursor = feld.textCursor()
    cursor.movePosition(cursor.MoveOperation.End)
    feld.setTextCursor(cursor)

    editor.eventFilter(
        feld,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Up, Qt.KeyboardModifier.ControlModifier),
    )

    assert feld.toPlainText().splitlines() == ["+erste()", "+zweite()"]


def test_notiz_hat_nur_ein_namensfeld(canvas: DiagrammCanvas) -> None:
    notiz = canvas.form_platzieren("note", 200, 200)

    editor = canvas.bearbeiten_starten(notiz)

    assert set(editor._felder) == {"name"}


def test_f2_startet_die_bearbeitung_der_auswahl(canvas: DiagrammCanvas) -> None:
    canvas.form_platzieren("class", 200, 200)

    canvas.keyPressEvent(
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_F2, Qt.KeyboardModifier.NoModifier)
    )

    assert canvas._editor is not None


def test_zweites_bearbeiten_ersetzt_das_erste(canvas: DiagrammCanvas) -> None:
    erste = canvas.form_platzieren("class", 160, 160)
    zweite = canvas.form_platzieren("class", 480, 160)

    canvas.bearbeiten_starten(erste)
    editor = canvas.bearbeiten_starten(zweite)

    assert canvas._editor is editor
    assert editor.form is zweite


def test_abgeraeumter_editor_loest_nichts_mehr_aus(canvas: DiagrammCanvas) -> None:
    """Real gefunden: beim Abräumen schickte Qt den sterbenden Feldern
    noch FocusOut, das erneut „übernehmen -> abräumen“ anstieß und auf
    bereits gelöschte Widgets zugriff – der ganze Testlauf stürzte
    danach in einem *anderen* Test ab (Windows: access violation)."""
    form = canvas.form_platzieren("class", 200, 200)
    editor = canvas.bearbeiten_starten(form)
    uebernahmen: list[dict] = []
    editor.fertig.connect(uebernahmen.append)

    editor.uebernehmen()
    editor.uebernehmen()  # zweiter Aufruf, wie ihn ein FocusOut auslösen würde
    editor.abbrechen()

    assert len(uebernahmen) == 1
    assert editor._beendet is True
