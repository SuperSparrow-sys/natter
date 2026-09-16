"""Tests für ide/shell/quelltexteditor.py: Zeilennummernrand, Breakpoints
im Rand (Abschnitt 8.1). Headless.
"""

from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest

from ide.shell.quelltexteditor import QuelltextEditor


def test_leerer_editor_hat_mindestens_eine_stelle_platz() -> None:
    editor = QuelltextEditor()
    schmale_breite = editor.zeilennummernrand_breite()
    assert schmale_breite > 0


def test_rand_wird_breiter_mit_mehr_zeilen() -> None:
    editor = QuelltextEditor()
    schmale_breite = editor.zeilennummernrand_breite()

    editor.setPlainText("\n".join(str(n) for n in range(1000)))

    assert editor.zeilennummernrand_breite() > schmale_breite


def test_blockanzahl_entspricht_der_zeilenanzahl() -> None:
    editor = QuelltextEditor()
    editor.setPlainText("eins\nzwei\ndrei")
    assert editor.blockCount() == 3


def test_viewport_raender_beruecksichtigen_den_zeilennummernrand() -> None:
    editor = QuelltextEditor()
    raender = editor.viewportMargins()
    assert raender.left() == editor.zeilennummernrand_breite()


def test_breakpoint_umschalten_fuegt_hinzu_und_entfernt_wieder() -> None:
    editor = QuelltextEditor()
    editor.breakpoint_umschalten(3)
    assert editor.breakpoints == {3}

    editor.breakpoint_umschalten(3)
    assert editor.breakpoints == set()


def test_breakpoint_umschalten_sendet_das_signal() -> None:
    editor = QuelltextEditor()
    empfangen = []
    editor.breakpoint_umgeschaltet.connect(
        lambda zeile, gesetzt: empfangen.append((zeile, gesetzt))
    )

    editor.breakpoint_umschalten(5)
    editor.breakpoint_umschalten(5)

    assert empfangen == [(5, True), (5, False)]


def test_klick_in_den_rand_schaltet_den_breakpoint_der_richtigen_zeile_um() -> None:
    editor = QuelltextEditor()
    editor.resize(400, 400)
    editor.setPlainText("\n".join(f"zeile{n}" for n in range(10)))
    editor.show()

    block = editor.document().findBlockByNumber(2)  # Zeile 3 (0-indiziert)
    y = round(editor.blockBoundingGeometry(block).translated(editor.contentOffset()).top())
    QTest.mouseClick(
        editor._rand, Qt.MouseButton.LeftButton, pos=QPoint(5, y + 3)  # noqa: SLF001
    )

    assert editor.breakpoints == {3}
