"""Tests für ide/shell/quelltexteditor.py: Zeilennummernrand. Headless.
"""

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
