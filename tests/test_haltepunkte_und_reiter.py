"""Punkte 112, 118, 119: Reiter schließen bei gescheitertem Speichern,
Haltepunkte während des Debuggens, Haltepunkte wandern mit ihrer Zeile."""

from __future__ import annotations

import json
import os
import shutil
import stat
from pathlib import Path

import pytest
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QMessageBox

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


# -- 112 -----------------------------------------------------------------


def test_reiter_bleibt_offen_wenn_speichern_scheitert(
    qtbot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hauptfenster  # noqa: ANN001
) -> None:
    main = _projekt(hauptfenster, tmp_path, "a = 1\n")
    editor = hauptfenster.datei_oeffnen(main)
    editor.setPlainText("a = 2\n")
    editor.document().setModified(True)
    os.chmod(main, stat.S_IREAD)
    monkeypatch.setattr(
        HauptFenster, "_reiter_schliessen_fragen", lambda self: QMessageBox.StandardButton.Save
    )
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: QMessageBox.StandardButton.Ok)
    try:
        index = hauptfenster.editor_tabs.indexOf(editor)
        hauptfenster._tab_schliessen(index)

        assert hauptfenster.editor_tabs.indexOf(editor) != -1
        assert editor.document().isModified()
        assert editor.toPlainText() == "a = 2\n"
    finally:
        os.chmod(main, stat.S_IWRITE | stat.S_IREAD)


# -- 119 -----------------------------------------------------------------


@pytest.fixture
def editor(qtbot) -> QuelltextEditor:  # noqa: ANN001
    editor = QuelltextEditor()
    qtbot.addWidget(editor)
    editor.setPlainText("a = 1\nb = 2\nc = 3\nd = 4\n")
    editor.breakpoint_umschalten(3)
    return editor


def _cursor_auf(editor: QuelltextEditor, zeile: int, spalte: int = 0) -> QTextCursor:
    cursor = editor.textCursor()
    cursor.setPosition(editor.document().findBlockByNumber(zeile - 1).position() + spalte)
    return cursor


def test_einfuegen_darueber_schiebt_den_haltepunkt(editor: QuelltextEditor) -> None:
    _cursor_auf(editor, 1).insertText("x = 0\ny = 0\n")

    assert editor.breakpoints == {5}
    assert editor.document().findBlockByNumber(4).text() == "c = 3"


def test_einfuegen_am_anfang_der_zeile_schiebt_sie_mit(editor: QuelltextEditor) -> None:
    _cursor_auf(editor, 3).insertText("neu = 1\n")

    assert editor.breakpoints == {4}


def test_einfuegen_mitten_in_der_zeile_laesst_sie_stehen(editor: QuelltextEditor) -> None:
    _cursor_auf(editor, 3, 5).insertText("\n")

    assert editor.breakpoints == {3}


def test_zeile_darueber_loeschen(editor: QuelltextEditor) -> None:
    cursor = _cursor_auf(editor, 1)
    cursor.setPosition(
        editor.document().findBlockByNumber(1).position(), QTextCursor.MoveMode.KeepAnchor
    )
    cursor.removeSelectedText()

    assert editor.breakpoints == {2}


def test_die_eigene_zeile_loeschen_nimmt_den_haltepunkt_mit(editor: QuelltextEditor) -> None:
    cursor = _cursor_auf(editor, 3)
    cursor.setPosition(
        editor.document().findBlockByNumber(3).position(), QTextCursor.MoveMode.KeepAnchor
    )
    cursor.removeSelectedText()

    assert editor.breakpoints == set()


def test_einfuegen_darunter_laesst_den_haltepunkt_stehen(editor: QuelltextEditor) -> None:
    _cursor_auf(editor, 4).insertText("e = 5\n")

    assert editor.breakpoints == {3}


# -- 118 -----------------------------------------------------------------


def test_haltepunkt_waehrend_des_debuggens_setzen(
    qtbot, tmp_path: Path, hauptfenster
) -> None:  # noqa: ANN001
    main = _projekt(hauptfenster, tmp_path, "a = 1\nb = 2\nc = 3\nd = 4\n")
    editor = hauptfenster.datei_oeffnen(main)
    editor.breakpoint_umschalten(1)

    hauptfenster._projekt_mit_debugger_starten_aktion()
    try:
        qtbot.waitUntil(
            lambda: hauptfenster._aktueller_thread_id is not None, timeout=DEBUG_ZEITGRENZE
        )
        editor.breakpoint_umschalten(1)
        editor.breakpoint_umschalten(4)
        qtbot.waitUntil(
            lambda: hauptfenster.debug_sitzung.client.gesetzte_breakpoints(main) == [4],
            timeout=DEBUG_ZEITGRENZE,
        )
        hauptfenster.aktionen["start.fortsetzen"].qaction.trigger()
        qtbot.waitUntil(
            lambda: hauptfenster._aktueller_thread_id is not None
            and hauptfenster.aufrufstapel_liste.count() > 0
            and hauptfenster.aufrufstapel_liste.item(0).text() == "main.py, Zeile 4, in <module>",
            timeout=DEBUG_ZEITGRENZE,
        )
    finally:
        if hauptfenster.debug_sitzung is not None:
            hauptfenster._debugger_stoppen_aktion()


def test_eine_zeile_waehrend_des_halts_aendert_den_haltepunkt_nicht(
    qtbot, tmp_path: Path, hauptfenster
) -> None:  # noqa: ANN001
    """Punkt 621: eine Zeile oberhalb eines Haltepunkts eingefügt, und
    debugpy bekam die neue Nummer, obwohl das Programm den alten Stand
    geladen hat. Weitergegeben wird die Zeile der Datei."""
    main = _projekt(hauptfenster, tmp_path, "a = 1\nb = 2\nc = 3\nd = 4\n")
    editor = hauptfenster.datei_oeffnen(main)
    editor.breakpoint_umschalten(1)
    editor.breakpoint_umschalten(3)

    hauptfenster._projekt_mit_debugger_starten_aktion()
    try:
        qtbot.waitUntil(
            lambda: hauptfenster._aktueller_thread_id is not None, timeout=DEBUG_ZEITGRENZE
        )
        _cursor_auf(editor, 2).insertText("x = 0\n")
        assert editor.breakpoints == {1, 4}
        qtbot.wait(300)
        assert hauptfenster.debug_sitzung.client.gesetzte_breakpoints(main) == [1, 3]
    finally:
        if hauptfenster.debug_sitzung is not None:
            hauptfenster._debugger_stoppen_aktion()


# -- 419 -----------------------------------------------------------------


def test_haltepunkte_ueberstehen_das_schliessen_des_reiters(
    qtbot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hauptfenster  # noqa: ANN001
) -> None:
    main = _projekt(hauptfenster, tmp_path, "a = 1\nb = 2\nc = 3\nd = 4\n")
    editor = hauptfenster.datei_oeffnen(main)
    editor.breakpoint_umschalten(3)
    editor.bedingung_setzen(4, "d > 0")
    # Eine Zeile darüber: beide wandern eine Zeile nach unten, und
    # gemerkt wird dieser Stand.
    _cursor_auf(editor, 1).insertText("x = 0\n")
    monkeypatch.setattr(
        HauptFenster, "_reiter_schliessen_fragen", lambda self: QMessageBox.StandardButton.Save
    )
    hauptfenster._tab_schliessen(hauptfenster.editor_tabs.indexOf(editor))
    assert hauptfenster.editor_tabs.indexOf(editor) == -1

    assert hauptfenster._offene_breakpoints() == {main: [4, 5]}
    assert hauptfenster._offene_bedingungen() == {main: {5: "d > 0"}}

    wieder = hauptfenster.datei_oeffnen(main)
    assert wieder.breakpoints == {4, 5}
    assert wieder.bedingungen == {5: "d > 0"}
    assert hauptfenster._offene_breakpoints() == {main: [4, 5]}


def test_haltepunkt_im_geschlossenen_reiter_haelt_das_programm(
    qtbot, tmp_path: Path, hauptfenster
) -> None:  # noqa: ANN001
    main = _projekt(hauptfenster, tmp_path, "a = 1\nb = 2\nc = 3\nd = 4\n")
    editor = hauptfenster.datei_oeffnen(main)
    editor.breakpoint_umschalten(3)
    hauptfenster._tab_schliessen(hauptfenster.editor_tabs.indexOf(editor))

    hauptfenster._projekt_mit_debugger_starten_aktion()
    try:
        qtbot.waitUntil(
            lambda: hauptfenster._aktueller_thread_id is not None
            and hauptfenster.aufrufstapel_liste.count() > 0
            and hauptfenster.aufrufstapel_liste.item(0).text() == "main.py, Zeile 3, in <module>",
            timeout=DEBUG_ZEITGRENZE,
        )
    finally:
        if hauptfenster.debug_sitzung is not None:
            hauptfenster._debugger_stoppen_aktion()


# Beim Schließen des Projekts ist der Reiter vorher schon zu, die
# Haltepunkte kommen also aus `_gemerkte_haltepunkte`; beim Neustart
# ist er bis zum Beenden offen.
@pytest.mark.parametrize("weg", ["projekt_schliessen", "neustart"])
def test_haltepunkte_ueberstehen_projekt_und_neustart(
    qtbot, tmp_path: Path, hauptfenster_bauen, weg: str  # noqa: ANN001
) -> None:
    fenster = hauptfenster_bauen()
    main = _projekt(
        fenster, tmp_path / "projekt", "a = 1\nb = 2\nc = 3\nd = 4\n"
    )
    natter = main.parent / "t.natter"
    editor = fenster.datei_oeffnen(main)
    editor.breakpoint_umschalten(2)
    editor.bedingung_setzen(4, "d > 0")

    if weg == "projekt_schliessen":
        fenster._tab_schliessen(fenster.editor_tabs.indexOf(editor))
        assert fenster.projekt_schliessen()
        assert fenster._offene_breakpoints() == {}
    else:
        fenster.close()
        fenster = hauptfenster_bauen()
    fenster.projekt_oeffnen(natter)
    wieder = fenster.datei_oeffnen(main)

    assert wieder.breakpoints == {2, 4}
    assert wieder.bedingungen == {4: "d > 0"}


def test_kopie_des_projektordners_hat_keine_haltepunkte(
    qtbot, tmp_path: Path, hauptfenster  # noqa: ANN001
) -> None:
    main = _projekt(hauptfenster, tmp_path / "lehrkraft", "a = 1\nb = 2\n")
    editor = hauptfenster.datei_oeffnen(main)
    editor.breakpoint_umschalten(2)
    assert hauptfenster.projekt_schliessen()
    kopie = tmp_path / "klasse"
    shutil.copytree(main.parent, kopie)

    hauptfenster.projekt_oeffnen(kopie / "t.natter")
    assert hauptfenster._offene_breakpoints() == {}
    assert hauptfenster.datei_oeffnen(kopie / "main.py").breakpoints == set()

    # Das Original hat seine Haltepunkte behalten.
    hauptfenster.projekt_oeffnen(main.parent / "t.natter")
    assert hauptfenster._offene_breakpoints() == {main: [2]}


def test_nach_verwerfen_steht_der_haltepunkt_auf_der_zeile_der_datei(
    qtbot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hauptfenster  # noqa: ANN001
) -> None:
    """Punkt 595: zwei Zeilen darüber eingefügt, nicht gespeichert,
    „Verwerfen“ - der gemerkte Haltepunkt stand auf Zeile 5 einer Datei
    mit drei Zeilen und war nach dem Wiederöffnen fort."""
    main = _projekt(hauptfenster, tmp_path, "a = 1\nb = 2\nc = 3\n")
    editor = hauptfenster.datei_oeffnen(main)
    editor.breakpoint_umschalten(3)
    editor.bedingung_setzen(3, "c > 0")
    _cursor_auf(editor, 1).insertText("x = 0\ny = 0\n")
    assert editor.breakpoints == {5}
    monkeypatch.setattr(
        HauptFenster, "_reiter_schliessen_fragen",
        lambda self: QMessageBox.StandardButton.Discard,
    )

    hauptfenster._tab_schliessen(hauptfenster.editor_tabs.indexOf(editor))
    wieder = hauptfenster.datei_oeffnen(main)

    assert wieder.toPlainText() == "a = 1\nb = 2\nc = 3\n"
    assert wieder.breakpoints == {3}
    assert wieder.bedingungen == {3: "c > 0"}
