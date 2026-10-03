"""Punkte 86 bis 89: vor dem Start speichern, Konsolenprogramm unter
dem Debugger, Tab/Umschalt+Tab, Zeile und Spalte in der Statusleiste."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtTest import QTest

from ide.debugger.dap_client import debugpy_aufruf
from ide.shell.hauptfenster import HauptFenster
from ide.shell.quelltexteditor import QuelltextEditor
from tests.conftest import DEBUG_ZEITGRENZE


def _projekt(fenster: HauptFenster, ordner: Path, quelltext: str) -> Path:
    ordner.mkdir(parents=True, exist_ok=True)
    (ordner / "main.py").write_text(quelltext, encoding="utf-8")
    natter = ordner / "t.natter"
    natter.write_text(json.dumps({
        "format": "natter-project/1", "name": "T", "type": "console", "main": "main.py",
    }), encoding="utf-8")
    fenster.projekt_oeffnen(natter)
    return ordner / "main.py"


# -- 86 ------------------------------------------------------------------


def test_starten_speichert_vorher(qtbot, tmp_path: Path, hauptfenster) -> None:  # noqa: ANN001
    main = _projekt(hauptfenster, tmp_path, "print('alt')\n")
    editor = hauptfenster.datei_oeffnen(main)
    editor.setPlainText("print('neu')\n")
    editor.document().setModified(True)

    assert not hauptfenster._vorstart_pruefung_blockiert()

    assert main.read_text(encoding="utf-8") == "print('neu')\n"
    assert not editor.document().isModified()


# -- 87 ------------------------------------------------------------------


def test_konsolenprogramm_bekommt_unter_dem_debugger_ein_fenster(tmp_path: Path) -> None:
    befehl, optionen = debugpy_aufruf(5678, tmp_path / "main.py", tmp_path, "Natter – T")

    assert "-c" in befehl and befehl[-1] == str(tmp_path / "main.py")
    if sys.platform == "win32":
        assert optionen["creationflags"] & subprocess.CREATE_NEW_CONSOLE


def test_gui_programm_bleibt_ohne_fenster(tmp_path: Path) -> None:
    befehl, optionen = debugpy_aufruf(5678, tmp_path / "main.py", tmp_path)

    assert befehl[-1] == str(tmp_path / "main.py")
    if sys.platform == "win32":
        assert not optionen["creationflags"] & subprocess.CREATE_NEW_CONSOLE


def test_konsolenprogramm_haelt_unter_dem_debugger(
    qtbot, tmp_path: Path, hauptfenster
) -> None:  # noqa: ANN001
    main = _projekt(hauptfenster, tmp_path, "zahl = 42\nprint(zahl)\n")
    editor = hauptfenster.datei_oeffnen(main)
    editor.breakpoint_umschalten(2)

    hauptfenster._projekt_mit_debugger_starten_aktion()
    try:
        qtbot.waitUntil(
            lambda: hauptfenster._aktueller_thread_id is not None, timeout=DEBUG_ZEITGRENZE
        )
        # Der Sprung zur Zeile kommt mit dem Aufrufstapel, etwas später.
        qtbot.waitUntil(
            lambda: editor.textCursor().blockNumber() == 1, timeout=DEBUG_ZEITGRENZE
        )
        stapel = [
            hauptfenster.aufrufstapel_liste.item(i).text()
            for i in range(hauptfenster.aufrufstapel_liste.count())
        ]
        assert stapel[0] == "main.py, Zeile 2, in <module>"
    finally:
        if hauptfenster.debug_sitzung is not None:
            hauptfenster._debugger_stoppen_aktion()


# -- 88 ------------------------------------------------------------------


@pytest.fixture
def editor(qtbot) -> QuelltextEditor:  # noqa: ANN001
    editor = QuelltextEditor()
    qtbot.addWidget(editor)
    editor.setPlainText("a = 1\nb = 2\n\nc = 3\n")
    return editor


def _markieren(editor: QuelltextEditor, von_zeile: int, bis_zeile: int) -> None:
    cursor = editor.textCursor()
    cursor.setPosition(editor.document().findBlockByNumber(von_zeile).position())
    ende = editor.document().findBlockByNumber(bis_zeile)
    cursor.setPosition(ende.position() + len(ende.text()), QTextCursor.MoveMode.KeepAnchor)
    editor.setTextCursor(cursor)


def test_tab_rueckt_markierte_zeilen_ein(editor: QuelltextEditor) -> None:
    _markieren(editor, 0, 3)

    QTest.keyClick(editor, Qt.Key.Key_Tab)

    assert editor.toPlainText() == "    a = 1\n    b = 2\n\n    c = 3\n"
    editor.undo()
    assert editor.toPlainText() == "a = 1\nb = 2\n\nc = 3\n"


def test_umschalt_tab_rueckt_aus(editor: QuelltextEditor) -> None:
    editor.setPlainText("    a = 1\n        b = 2\n  c = 3\n")
    _markieren(editor, 0, 2)

    QTest.keyClick(editor, Qt.Key.Key_Backtab, Qt.KeyboardModifier.ShiftModifier)

    assert editor.toPlainText() == "a = 1\n    b = 2\nc = 3\n"


def test_umschalt_tab_rueckt_auch_einen_tabulator_aus(editor: QuelltextEditor) -> None:
    """Punkt 621: gezählt wurden nur Leerzeichen."""
    editor.setPlainText("\t\ta = 1\n\tb = 2\n")
    _markieren(editor, 0, 1)

    QTest.keyClick(editor, Qt.Key.Key_Backtab, Qt.KeyboardModifier.ShiftModifier)

    assert editor.toPlainText() == "\ta = 1\nb = 2\n"


def test_umschalt_tab_ohne_markierung_betrifft_die_zeile(editor: QuelltextEditor) -> None:
    editor.setPlainText("x = 1\n    y = 2\n")
    cursor = editor.textCursor()
    cursor.setPosition(editor.document().findBlockByNumber(1).position() + 6)
    editor.setTextCursor(cursor)

    QTest.keyClick(editor, Qt.Key.Key_Backtab, Qt.KeyboardModifier.ShiftModifier)

    assert editor.toPlainText() == "x = 1\ny = 2\n"


def test_tab_ohne_mehrzeilige_markierung_fuegt_leerzeichen_ein(editor: QuelltextEditor) -> None:
    cursor = editor.textCursor()
    cursor.setPosition(0)
    editor.setTextCursor(cursor)

    QTest.keyClick(editor, Qt.Key.Key_Tab)

    assert editor.toPlainText().startswith("    a = 1\n")


# -- 89 ------------------------------------------------------------------


def test_zeile_und_spalte_in_der_statusleiste(
    qtbot, tmp_path: Path, hauptfenster
) -> None:  # noqa: ANN001
    main = _projekt(hauptfenster, tmp_path, "a = 1\nbeta = 2\n")
    editor = hauptfenster.datei_oeffnen(main)

    cursor = editor.textCursor()
    cursor.setPosition(editor.document().findBlockByNumber(1).position() + 4)
    editor.setTextCursor(cursor)

    assert hauptfenster.cursor_anzeige.text() == "Zeile 2, Spalte 5"
