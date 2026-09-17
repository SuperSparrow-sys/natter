"""Tests für ide/shell/quelltexteditor.py: Zeilennummernrand, Breakpoints
im Rand (Abschnitt 8.1). Headless.
"""

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QFontInfo
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


# -- Dunkles Design (Nutzer-Feedback September 2026) -----------------------


def test_editor_kann_direkt_im_dunklen_thema_erzeugt_werden() -> None:
    editor = QuelltextEditor(thema="dark")
    assert editor._rand_farben["hintergrund"] == "#252526"  # noqa: SLF001


def test_thema_setzen_wechselt_rand_und_hervorhebung() -> None:
    editor = QuelltextEditor()
    hell_hintergrund = editor._rand_farben["hintergrund"]  # noqa: SLF001

    editor.thema_setzen("dark")

    assert editor._rand_farben["hintergrund"] != hell_hintergrund  # noqa: SLF001
    assert editor._hervorhebung._thema == "dark"  # noqa: SLF001


# -- Automatischer Einzug (Nutzer-Feedback September 2026) -----------------


def test_enter_uebernimmt_den_einzug_der_vorzeile() -> None:
    editor = QuelltextEditor()
    editor.setPlainText("    x = 1")
    cursor = editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.End)
    editor.setTextCursor(cursor)

    QTest.keyClick(editor, Qt.Key.Key_Return)

    assert editor.toPlainText() == "    x = 1\n    "


def test_enter_nach_doppelpunkt_erhoeht_den_einzug() -> None:
    editor = QuelltextEditor()
    editor.setPlainText("def f():")
    cursor = editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.End)
    editor.setTextCursor(cursor)

    QTest.keyClick(editor, Qt.Key.Key_Return)

    assert editor.toPlainText() == "def f():\n    "


def test_enter_nach_eingerueckter_zeile_mit_doppelpunkt_erhoeht_weiter() -> None:
    editor = QuelltextEditor()
    editor.setPlainText("class X:\n    def f(self):")
    cursor = editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.End)
    editor.setTextCursor(cursor)

    QTest.keyClick(editor, Qt.Key.Key_Return)

    assert editor.toPlainText() == "class X:\n    def f(self):\n        "


def test_enter_ohne_doppelpunkt_am_zeilenende_behaelt_einzug() -> None:
    editor = QuelltextEditor()
    editor.setPlainText("    return 1  # kommentar mit : darin")
    cursor = editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.End)
    editor.setTextCursor(cursor)

    QTest.keyClick(editor, Qt.Key.Key_Return)

    assert editor.toPlainText().endswith("\n    ")


def test_tab_fuegt_leerzeichen_statt_eines_tabulatorzeichens_ein() -> None:
    editor = QuelltextEditor()

    QTest.keyClick(editor, Qt.Key.Key_Tab)

    assert editor.toPlainText() == "    "
    assert "\t" not in editor.toPlainText()


def test_cascadia_code_wird_ohne_systeminstallation_gefunden() -> None:
    """Nutzer-Feedback: „wenn Schriftart nicht installiert, soll diese
    installiert werden“ - die Schriftdatei wird direkt aus
    ide/assets/fonts/ in Qts Anwendungsschrift-Datenbank geladen, ganz
    ohne Windows-Systeminstallation (portable Natter-Philosophie)."""
    editor = QuelltextEditor()
    aufgeloest = QFontInfo(editor.font()).family()
    assert aufgeloest == "Cascadia Code"
