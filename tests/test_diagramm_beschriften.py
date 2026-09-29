"""Tests für ide/diagramm/textbearbeitung.py: Notiz und Paket direkt in
der Fläche beschriften (M9, Schritt 5, seit Schritt 12 eingeschränkt).
Headless.

Klassen, abstrakte Klassen und Interfaces werden über den
Eigenschaften-Dialog bearbeitet – dafür ist
`tests/test_diagramm_klassendialog.py` zuständig. Hier geht es nur noch
um die beiden Formen mit einem einzigen Textfeld.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QPlainTextEdit

from ide.diagramm import diagramm_erzeugen
from ide.diagramm.canvas import DiagrammCanvas


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


def test_doppelklick_auf_eine_notiz_oeffnet_das_eingabefeld(
    canvas: DiagrammCanvas,
) -> None:
    notiz = canvas.form_platzieren("note", 200, 200)

    canvas.mouseDoubleClickEvent(
        _doppelklick(notiz["x"] + notiz["w"] / 2, notiz["y"] + notiz["h"] / 2)
    )

    editor = canvas._editor
    assert editor is not None
    assert set(editor._felder) == {"name"}
    assert isinstance(editor._felder["name"], QPlainTextEdit)


def test_doppelklick_ins_leere_oeffnet_nichts(canvas: DiagrammCanvas) -> None:
    canvas.form_platzieren("note", 200, 200)

    canvas.mouseDoubleClickEvent(_doppelklick(2000, 1400))

    assert canvas._editor is None


def test_feld_liegt_ueber_der_form(canvas: DiagrammCanvas) -> None:
    """Abschnitt 13.3: „bearbeitet direkt in der Form“."""
    notiz = canvas.form_platzieren("note", 300, 300)

    editor = canvas.bearbeiten_starten(notiz)

    assert editor.geometry().left() == notiz["x"]
    assert editor.geometry().width() == notiz["w"]


def test_eingabe_wird_uebernommen(canvas: DiagrammCanvas) -> None:
    notiz = canvas.form_platzieren("note", 200, 200)
    editor = canvas.bearbeiten_starten(notiz)

    editor._felder["name"].setPlainText("Zustand: 1=grün, 2=gelb")
    editor.uebernehmen()

    assert notiz["name"] == "Zustand: 1=grün, 2=gelb"
    assert canvas._editor is None


def test_umgebende_leerzeichen_fallen_weg(canvas: DiagrammCanvas) -> None:
    notiz = canvas.form_platzieren("note", 200, 200)
    editor = canvas.bearbeiten_starten(notiz)

    editor._felder["name"].setPlainText("  Hinweis  \n")
    editor.uebernehmen()

    assert notiz["name"] == "Hinweis"


def test_uebernehmen_ist_ein_undo_schritt(canvas: DiagrammCanvas) -> None:
    notiz = canvas.form_platzieren("note", 200, 200)
    vorher = notiz["name"]
    editor = canvas.bearbeiten_starten(notiz)
    editor._felder["name"].setPlainText("Neuer Text")
    editor.uebernehmen()

    canvas.rueckgaengig()

    assert notiz["name"] == vorher


def test_form_waechst_mit_dem_neuen_text_mit(canvas: DiagrammCanvas) -> None:
    notiz = canvas.form_platzieren("note", 200, 200)
    vorher = notiz["h"]
    editor = canvas.bearbeiten_starten(notiz)

    editor._felder["name"].setPlainText("sehr langer Hinweistext " * 12)
    editor.uebernehmen()

    assert notiz["h"] > vorher


def test_abbrechen_laesst_den_text_unveraendert(canvas: DiagrammCanvas) -> None:
    notiz = canvas.form_platzieren("note", 200, 200)
    vorher = notiz["name"]
    editor = canvas.bearbeiten_starten(notiz)

    editor._felder["name"].setPlainText("Nicht übernehmen")
    editor.abbrechen()

    assert notiz["name"] == vorher
    assert canvas._editor is None


def test_escape_bricht_die_eingabe_ab(canvas: DiagrammCanvas) -> None:
    notiz = canvas.form_platzieren("note", 200, 200)
    editor = canvas.bearbeiten_starten(notiz)
    editor._felder["name"].setPlainText("Verworfen")

    editor.eventFilter(
        editor._felder["name"],
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier),
    )

    assert notiz["name"] != "Verworfen"


def test_strg_eingabe_uebernimmt(canvas: DiagrammCanvas) -> None:
    notiz = canvas.form_platzieren("note", 200, 200)
    editor = canvas.bearbeiten_starten(notiz)
    editor._felder["name"].setPlainText("Fertig")

    editor.eventFilter(
        editor._felder["name"],
        QKeyEvent(
            QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.ControlModifier
        ),
    )

    assert notiz["name"] == "Fertig"


def test_paket_wird_genauso_beschriftet(canvas: DiagrammCanvas) -> None:
    paket = canvas.form_platzieren("package", 200, 200)

    editor = canvas.bearbeiten_starten(paket)
    editor._felder["name"].setPlainText("fachlogik")
    editor.uebernehmen()

    assert paket["name"] == "fachlogik"


def test_f2_startet_die_bearbeitung_der_auswahl(canvas: DiagrammCanvas) -> None:
    canvas.form_platzieren("note", 200, 200)

    canvas.keyPressEvent(
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_F2, Qt.KeyboardModifier.NoModifier)
    )

    assert canvas._editor is not None


def test_zweites_bearbeiten_ersetzt_das_erste(canvas: DiagrammCanvas) -> None:
    erste = canvas.form_platzieren("note", 160, 160)
    zweite = canvas.form_platzieren("note", 480, 160)

    canvas.bearbeiten_starten(erste)
    editor = canvas.bearbeiten_starten(zweite)

    assert canvas._editor is editor
    assert editor.form is zweite


def test_editor_skaliert_mit_dem_zoom(canvas: DiagrammCanvas) -> None:
    notiz = canvas.form_platzieren("note", 300, 300)
    canvas.zoom_setzen(2.0)

    editor = canvas.bearbeiten_starten(notiz)

    assert editor.geometry().left() == pytest.approx(notiz["x"] * 2, abs=2)
    assert editor.geometry().width() == pytest.approx(notiz["w"] * 2, abs=2)


def test_abgeraeumter_editor_loest_nichts_mehr_aus(canvas: DiagrammCanvas) -> None:
    """Real gefunden: beim Abräumen schickte Qt den sterbenden Feldern
    noch `FocusOut`, das erneut „übernehmen → abräumen“ anstieß und auf
    bereits gelöschte Widgets zugriff – der ganze Testlauf stürzte
    danach in einem *anderen* Test ab (Windows: access violation)."""
    notiz = canvas.form_platzieren("note", 200, 200)
    editor = canvas.bearbeiten_starten(notiz)
    uebernahmen: list[dict] = []
    editor.fertig.connect(uebernahmen.append)

    editor.uebernehmen()
    editor.uebernehmen()  # zweiter Aufruf, wie ihn ein FocusOut auslösen würde
    editor.abbrechen()

    assert len(uebernahmen) == 1
    assert editor._beendet is True
