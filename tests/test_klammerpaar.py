"""Hervorhebung des Klammerpaars am Cursor (Punkt 103)."""

from __future__ import annotations

import pytest

from ide.shell.quelltexteditor import QuelltextEditor


@pytest.fixture
def editor(qtbot) -> QuelltextEditor:  # noqa: ANN001
    editor = QuelltextEditor()
    qtbot.addWidget(editor)
    return editor


def _cursor(editor: QuelltextEditor, position: int) -> tuple[int, ...]:
    cursor = editor.textCursor()
    cursor.setPosition(position)
    editor.setTextCursor(cursor)
    return editor.klammerpaar_am_cursor()


def test_hinter_der_schliessenden_klammer(editor: QuelltextEditor) -> None:
    editor.setPlainText("print(len([1, 2]))")

    assert _cursor(editor, 18) == (17, 5)
    assert _cursor(editor, 16) == (15, 10)


def test_vor_der_oeffnenden_klammer(editor: QuelltextEditor) -> None:
    editor.setPlainText("x = (a + (b))")

    assert _cursor(editor, 4) == (4, 12)


def test_klammern_in_texten_zaehlen_nicht(editor: QuelltextEditor) -> None:
    editor.setPlainText('print(")", x)  # (\n')

    assert _cursor(editor, 5) == (5, 12)


def test_ohne_gegenklammer_nichts(editor: QuelltextEditor) -> None:
    editor.setPlainText("print(1")

    assert _cursor(editor, 6) == ()


def test_die_markierung_erscheint(editor: QuelltextEditor) -> None:
    editor.setPlainText("f(x)")
    _cursor(editor, 4)

    markiert = {
        auswahl.cursor.selectionStart()
        for auswahl in editor.extraSelections()
        if auswahl.cursor.hasSelection()
    }

    assert {1, 3} <= markiert
