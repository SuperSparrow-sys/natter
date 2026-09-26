"""Klammern schließen und Parameterhilfe mit einer deutschen Tastatur
(Punkt 43 der offenen Punkte).

Auf einer deutschen Tastatur entstehen `(`, `)` und `"` mit der
Umschalttaste, `[ ] { }` mit AltGr, das Windows als Strg+Alt meldet.
Bis 0.3.3 schloss der Editor Klammern nur ohne jede Zusatztaste, also
auf dieser Tastatur nie.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QHelpEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QToolTip

from ide.shell.quelltexteditor import QuelltextEditor

UMSCHALT = Qt.KeyboardModifier.ShiftModifier
ALTGR = Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier


def _editor(qtbot, text: str = "") -> QuelltextEditor:  # noqa: ANN001
    editor = QuelltextEditor()
    qtbot.addWidget(editor)
    editor.resize(700, 400)
    editor.show()
    editor.setPlainText(text)
    cursor = editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.End)
    editor.setTextCursor(cursor)
    return editor


def test_umschalt_klammer_wird_geschlossen(qtbot) -> None:  # noqa: ANN001
    editor = _editor(qtbot, "print")

    QTest.keyClick(editor, "(", UMSCHALT)
    QTest.keyClick(editor, '"', UMSCHALT)

    assert editor.toPlainText() == 'print("")'
    assert editor.textCursor().positionInBlock() == len('print("')


def test_altgr_klammer_wird_geschlossen(qtbot) -> None:  # noqa: ANN001
    editor = _editor(qtbot, "zahlen = ")

    QTest.keyClick(editor, "[", ALTGR)

    assert editor.toPlainText() == "zahlen = []"


def test_umschalt_schliessende_klammer_wird_uebersprungen(qtbot) -> None:  # noqa: ANN001
    editor = _editor(qtbot, "print")
    QTest.keyClick(editor, "(", UMSCHALT)

    QTest.keyClick(editor, ")", UMSCHALT)

    assert editor.toPlainText() == "print()"


def test_strg_allein_schreibt_keine_klammer(qtbot) -> None:  # noqa: ANN001
    editor = _editor(qtbot, "x")

    QTest.keyClick(editor, "(", Qt.KeyboardModifier.ControlModifier)

    assert editor.toPlainText() == "x"


def test_parameterhilfe_bleibt_nach_uebernahme_mit_eingabe(qtbot) -> None:  # noqa: ANN001
    """Die Hilfe erschien und verschwand sofort wieder: die Maus ruhte
    über dem Editor, die Vorschlagsliste verschwand unter ihr, und Qt
    schickte ein Tooltip-Ereignis. Weil an dieser Stelle kein Fund
    stand, blendete der Editor jeden Kurzhinweis aus."""
    editor = _editor(
        qtbot,
        "def konto_abheben(konto: int, betrag: float) -> float:\n"
        "    return 1.0\n\n\n",
    )
    editor.funde_setzen({1: "Ein Fund in der ersten Zeile"})
    # Das Fenster ist vorn, wie beim Tippen. Sonst schließt das
    # Aktivieren der Anwendung den ersten Kurzhinweis gleich wieder.
    editor.activateWindow()
    qtbot.waitUntil(editor.isActiveWindow, timeout=2000)
    QTest.keyClicks(editor, "konto_ab")
    assert editor.vorschlagsliste.isVisible()

    QTest.keyClick(editor, Qt.Key.Key_Return)
    assert editor.textCursor().block().text() == "konto_abheben()"
    assert "konto: int" in editor.letzte_parameterhilfe
    assert QToolTip.isVisible()

    stelle = editor.cursorRect().center()
    QApplication.sendEvent(
        editor,
        QHelpEvent(
            QEvent.Type.ToolTip, stelle, editor.viewport().mapToGlobal(stelle)
        ),
    )
    # `QToolTip.hideText()` blendet erst nach einer kurzen Pause aus
    QTest.qWait(500)

    assert QToolTip.isVisible()
    assert QToolTip.text() == editor.letzte_parameterhilfe


def test_ohne_parameterhilfe_verschwindet_ein_fundhinweis(qtbot) -> None:  # noqa: ANN001
    """Ein Fund-Hinweis verschwindet weiterhin, wenn die Maus auf eine
    Zeile ohne Fund wandert."""
    editor = _editor(qtbot, "x = 1\ny = 2\n")
    editor.funde_setzen({1: "Ein Fund in der ersten Zeile"})
    QToolTip.showText(editor.mapToGlobal(editor.rect().center()), "Fund", editor)

    stelle = editor.cursorRect().center()
    QApplication.sendEvent(
        editor,
        QHelpEvent(
            QEvent.Type.ToolTip, stelle, editor.viewport().mapToGlobal(stelle)
        ),
    )

    qtbot.waitUntil(lambda: not QToolTip.isVisible(), timeout=2000)
