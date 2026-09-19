"""Tests für die sichtbare Einrückung im Quelltexteditor
(M11, Abschnitt 2.1). Headless.

Bei Python **ist** die Einrückung die Syntax – wer sie nicht sieht,
sucht seinen Fehler an der falschen Stelle. Geprüft wird deshalb beides:
die Rechnung (wie tief ist diese Zeile?) und das gemalte Bild.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QColor, QKeyEvent

from ide.shell.hauptfenster import HauptFenster
from ide.shell.quelltexteditor import QuelltextEditor

CODE = (
    "class Ampel:\n"
    "    def umschalten(self):\n"
    "        if self.farbe == 'rot':\n"
    "\n"
    "            self.farbe = 'gruen'\n"
    "        return self.farbe\n"
)


@pytest.fixture
def editor() -> QuelltextEditor:
    editor = QuelltextEditor()
    editor.setPlainText(CODE)
    editor.resize(420, 300)
    return editor


def _taste(taste, text: str = "") -> QKeyEvent:
    return QKeyEvent(QEvent.Type.KeyPress, taste, Qt.KeyboardModifier.NoModifier, text)


# -- Einrückungstiefe ----------------------------------------------------


@pytest.mark.parametrize(
    ("zeile", "tiefe"),
    [(0, 0), (1, 1), (2, 2), (4, 3), (5, 2)],
)
def test_die_tiefe_wird_richtig_gezaehlt(editor: QuelltextEditor, zeile: int, tiefe: int) -> None:
    assert editor.einzugstiefe(zeile) == tiefe


def test_eine_leerzeile_uebernimmt_die_tiefe_der_naechsten(
    editor: QuelltextEditor,
) -> None:
    """Sonst rissen die Linien mitten in einem Block ab – gerade dort,
    wo eine Leerzeile zwei Absätze einer Funktion trennt, und genau dann
    braucht man sie am meisten."""
    assert editor.einzugstiefe(3) == editor.einzugstiefe(4) == 3


def test_leerzeilen_am_ende_haben_keine_tiefe(editor: QuelltextEditor) -> None:
    """Dort kommt keine Zeile mehr, von der man etwas übernehmen
    könnte."""
    letzte = editor.document().blockCount() - 1

    assert editor.einzugstiefe(letzte) == 0


def test_ein_tabulator_zaehlt_wie_vier_leerzeichen(editor: QuelltextEditor) -> None:
    editor.setPlainText("def f():\n\tpass\n")

    assert editor.einzugstiefe(1) == 1


# -- Gezeichnet ----------------------------------------------------------


def _senkrechte_linien(editor: QuelltextEditor) -> int:
    """Wie viele Pixel in der Linienfarbe wirklich gemalt werden."""
    from ide.shell.quelltexteditor import _EINZUGSLINIEN_FARBEN

    bild = editor.grab().toImage()
    farbe = QColor(_EINZUGSLINIEN_FARBEN["light"]).name()
    return sum(
        bild.pixelColor(x, y).name() == farbe
        for x in range(bild.width())
        for y in range(bild.height())
    )


def test_die_linien_werden_wirklich_gemalt(editor: QuelltextEditor) -> None:
    editor.einzugslinien_setzen(False)
    ohne = _senkrechte_linien(editor)

    editor.einzugslinien_setzen(True)

    assert _senkrechte_linien(editor) > ohne + 50


def test_ohne_einrueckung_keine_linien() -> None:
    """Gegenprobe: eine Datei ohne Einrückung bekommt keine Linien."""
    editor = QuelltextEditor()
    editor.setPlainText("a = 1\nb = 2\nc = 3\n")
    editor.resize(420, 300)

    assert _senkrechte_linien(editor) == 0


def test_der_schalter_wirkt_sofort(editor: QuelltextEditor) -> None:
    editor.einzugslinien_setzen(True)
    mit = _senkrechte_linien(editor)

    editor.einzugslinien_setzen(False)

    assert _senkrechte_linien(editor) < mit


# -- Rücktaste -----------------------------------------------------------


def test_ruecktaste_loescht_eine_ganze_ebene(editor: QuelltextEditor) -> None:
    """Mit vier Leerzeichen je Ebene bräuchte es sonst vier Anschläge –
    und wer dabei einmal zu oft drückt, bekommt einen
    `IndentationError`, den er nicht sieht."""
    cursor = editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.Start)
    cursor.movePosition(cursor.MoveOperation.Down)
    cursor.movePosition(cursor.MoveOperation.EndOfLine)
    cursor.movePosition(cursor.MoveOperation.StartOfLine)
    cursor.movePosition(cursor.MoveOperation.Right, n=4)
    editor.setTextCursor(cursor)

    editor.keyPressEvent(_taste(Qt.Key.Key_Backspace))

    assert editor.document().findBlockByNumber(1).text() == "def umschalten(self):"


def test_ruecktaste_im_text_bleibt_normal(editor: QuelltextEditor) -> None:
    """Mitten im Text ist die Rücktaste, was sie immer war."""
    cursor = editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.Start)
    cursor.movePosition(cursor.MoveOperation.EndOfLine)
    editor.setTextCursor(cursor)

    editor.keyPressEvent(_taste(Qt.Key.Key_Backspace))

    assert editor.document().findBlockByNumber(0).text() == "class Ampel"


def test_ruecktaste_bei_krummer_einrueckung_rueckt_auf_die_ebene(
    editor: QuelltextEditor,
) -> None:
    """Sechs Leerzeichen sind anderthalb Ebenen. Ein Anschlag bringt
    auf die nächste ganze Ebene, nicht vier Zeichen zurück ins
    Nichts."""
    editor.setPlainText("def f():\n      pass\n")
    cursor = editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.Start)
    cursor.movePosition(cursor.MoveOperation.Down)
    cursor.movePosition(cursor.MoveOperation.Right, n=6)
    editor.setTextCursor(cursor)

    editor.keyPressEvent(_taste(Qt.Key.Key_Backspace))

    assert editor.document().findBlockByNumber(1).text() == "    pass"


def test_ruecktaste_bei_markiertem_text_bleibt_normal(
    editor: QuelltextEditor,
) -> None:
    cursor = editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.Start)
    cursor.movePosition(cursor.MoveOperation.Right, cursor.MoveMode.KeepAnchor, n=5)
    editor.setTextCursor(cursor)

    editor.keyPressEvent(_taste(Qt.Key.Key_Backspace))

    # "class" war markiert und ist weg - das Leerzeichen dahinter bleibt
    assert editor.document().findBlockByNumber(0).text() == " Ampel:"


# -- Menü ----------------------------------------------------------------


def test_das_ansicht_menue_hat_den_schalter(qtbot) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    titel = [aktion.text() for aktion in fenster.menue("Ansicht").actions()]

    assert "Einrückungslinien" in titel
    assert fenster.einzugslinien_aktion.isCheckable() is True


def test_der_schalter_wirkt_auf_offene_tabs(qtbot, tmp_path) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    datei = tmp_path / "u_test.py"
    datei.write_text(CODE, encoding="utf-8")
    fenster.datei_oeffnen(datei)
    editor = fenster.editor_tabs.currentWidget()

    fenster.einzugslinien_aktion.setChecked(False)

    assert editor.einzugslinien_sichtbar is False
