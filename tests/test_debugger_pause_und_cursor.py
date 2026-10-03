"""Pause bei einem frei laufenden Programm (Punkt 56) und „Ausführen
bis Cursor“ (Punkt 78). Gegen echtes `debugpy`.

Bis 0.3.5 ließ sich „Pause“ erst nach einem Halt an einem Haltepunkt
benutzen - bei einer Endlosschleife, dem häufigsten Grund dafür, war
der Befehl grau. „Ausführen bis Cursor“ gab es im Debug-Client, aber
keinen Weg dorthin.
"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtGui import QTextCursor

from ide.shell.hauptfenster import HauptFenster
from tests.conftest import DEBUG_ZEITGRENZE


def _projekt(fenster: HauptFenster, ordner: Path, quelltext: str) -> Path:
    ordner.mkdir(parents=True, exist_ok=True)
    (ordner / "main.py").write_text(quelltext, encoding="utf-8")
    natter = ordner / "test.natter"
    natter.write_text(json.dumps({
        "format": "natter-project/1", "name": "Test", "type": "console", "main": "main.py",
    }), encoding="utf-8")
    fenster.projekt_oeffnen(natter)
    return ordner / "main.py"


def _cursor_in_zeile(editor, zeile: int) -> None:  # noqa: ANN001
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.Start)
    cursor.movePosition(QTextCursor.MoveOperation.Down, n=zeile - 1)
    editor.setTextCursor(cursor)


def _aktiv(fenster: HauptFenster, kennung: str) -> bool:
    return fenster.aktionen[kennung].qaction.isEnabled()


def _halt_zeile(fenster: HauptFenster) -> int:
    return fenster._aktueller_editor().textCursor().blockNumber() + 1


def _variable(fenster: HauptFenster, name: str) -> str | None:
    baum = fenster.variablen_baum
    for i in range(baum.topLevelItemCount()):
        eintrag = baum.topLevelItem(i)
        if eintrag.text(0) == name:
            return eintrag.text(1)
    return None


def test_pause_haelt_eine_endlosschleife_an(qtbot, tmp_path: Path) -> None:  # noqa: ANN001
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    _projekt(fenster, tmp_path, "zahl = 0\nwhile True:\n    zahl += 1\n")

    try:
        fenster._projekt_mit_debugger_starten_aktion()
        qtbot.waitUntil(lambda: _aktiv(fenster, "start.pause"), timeout=DEBUG_ZEITGRENZE)
        assert not _aktiv(fenster, "start.einzelschritt")

        fenster.aktionen["start.pause"].qaction.trigger()
        qtbot.waitUntil(
            lambda: fenster._aktueller_thread_id is not None, timeout=DEBUG_ZEITGRENZE
        )

        assert _aktiv(fenster, "start.einzelschritt")
        assert not _aktiv(fenster, "start.pause")

        fenster.aktionen["start.fortsetzen"].qaction.trigger()
        assert not _aktiv(fenster, "start.einzelschritt")
        assert _aktiv(fenster, "start.pause")
    finally:
        if fenster.debug_sitzung is not None:
            fenster._debugger_stoppen_aktion()


def test_ausfuehren_bis_cursor_vor_dem_start_und_aus_einem_halt(
    qtbot, tmp_path: Path  # noqa: ANN001
) -> None:
    """Beide Wege in einem Lauf.

    Vor dem Start: F4 startet das Programm mit dem Debugger und hält
    in der Zeile des Cursors, und der vorübergehende Haltepunkt gilt
    nur einmal. Das Programm steht in einer Schleife, ein zweiter
    Halt in derselben Zeile wäre also zu sehen; mit „Fortsetzen“ geht
    es stattdessen bis zum Haltepunkt aus dem Editor.

    Aus einem Halt: F4 läuft bis zur Zeile des Cursors, und danach
    sind wieder genau die Haltepunkte aus dem Editor gesetzt. Zum
    Schluss läuft das Programm durch, und im Editor ist kein
    vorübergehender Haltepunkt stehen geblieben."""
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    main = _projekt(
        fenster,
        tmp_path,
        "for i in range(3):\n"
        "    x = i\n"
        "a = 1  # Haltepunkt aus dem Editor\n"
        "b = 2\n"
        "c = 3\n"
        "fertig = True\n",
    )
    editor = fenster.datei_oeffnen(main)
    editor.breakpoint_umschalten(3)
    _cursor_in_zeile(editor, 2)

    try:
        fenster.aktionen["start.bis_cursor"].qaction.trigger()
        qtbot.waitUntil(
            lambda: fenster._aktueller_thread_id is not None, timeout=DEBUG_ZEITGRENZE
        )
        assert _halt_zeile(fenster) == 2

        fenster.aktionen["start.fortsetzen"].qaction.trigger()
        qtbot.waitUntil(
            lambda: fenster._aktueller_thread_id is not None and _halt_zeile(fenster) != 2,
            timeout=DEBUG_ZEITGRENZE,
        )
        assert _halt_zeile(fenster) == 3

        _cursor_in_zeile(editor, 5)
        fenster.aktionen["start.bis_cursor"].qaction.trigger()
        qtbot.waitUntil(
            lambda: fenster._aktueller_thread_id is not None and _halt_zeile(fenster) == 5,
            timeout=DEBUG_ZEITGRENZE,
        )
        qtbot.waitUntil(
            lambda: fenster.debug_sitzung.client.gesetzte_breakpoints(main) == [3],
            timeout=DEBUG_ZEITGRENZE,
        )

        fenster.aktionen["start.fortsetzen"].qaction.trigger()
        qtbot.waitUntil(lambda: fenster.debug_sitzung is None, timeout=DEBUG_ZEITGRENZE)
        assert editor.breakpoints == {3}
    finally:
        if fenster.debug_sitzung is not None:
            fenster._debugger_stoppen_aktion()


def test_f9_setzt_haltepunkt_und_f5_setzt_einen_halt_fort(
    qtbot, tmp_path: Path, hauptfenster: HauptFenster  # noqa: ANN001
) -> None:
    """Punkt 508: F9 setzt und entfernt den Haltepunkt in der Zeile
    des Cursors, und F5 setzt ein angehaltenes Programm fort, statt
    nach einem Neustart zu fragen. Die Schleife hält zweimal in
    derselben Zeile; ein Neustart wäre an `i` zu erkennen. Punkt 509:
    die Haltezeile ist eigens markiert, bis das Programm endet."""
    fenster = hauptfenster
    main = _projekt(
        fenster, tmp_path, "for i in range(2):\n    x = i\nfertig = True\n"
    )
    editor = fenster.datei_oeffnen(main)
    assert fenster.aktionen["start.haltepunkt"].qaction.shortcut().toString() == "F9"
    _cursor_in_zeile(editor, 2)
    fenster.aktionen["start.haltepunkt"].qaction.trigger()
    assert editor.breakpoints == {2}

    starten = fenster.aktionen["start.mit_debugger"].qaction
    assert starten.shortcut().toString() == "F5"
    starten.trigger()
    qtbot.waitUntil(
        lambda: fenster._aktueller_thread_id is not None, timeout=DEBUG_ZEITGRENZE
    )
    sitzung = fenster.debug_sitzung
    # Punkt 509: die Haltezeile bleibt markiert, auch wenn der Cursor
    # woanders hinwandert.
    qtbot.waitUntil(lambda: editor.haltezeile == 2, timeout=DEBUG_ZEITGRENZE)
    _cursor_in_zeile(editor, 3)
    assert editor.haltezeile == 2

    starten.trigger()
    qtbot.waitUntil(
        lambda: fenster._aktueller_thread_id is not None
        and fenster.debug_sitzung is sitzung
        and _variable(fenster, "i") == "1",
        timeout=DEBUG_ZEITGRENZE,
    )

    _cursor_in_zeile(editor, 2)
    fenster.aktionen["start.haltepunkt"].qaction.trigger()
    assert editor.breakpoints == set()
    starten.trigger()
    qtbot.waitUntil(lambda: fenster.debug_sitzung is None, timeout=DEBUG_ZEITGRENZE)
    assert editor.haltezeile is None
