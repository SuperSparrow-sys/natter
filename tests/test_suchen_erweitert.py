"""Suchen (Punkte 102 und 129): Schalter, Rückwärtssuche, Meldungen,
„Ersetzen“ nach derselben Regel wie „Alle ersetzen“, Suche in allen
Dateien."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ide.shell.suchen_dialog import SuchenErsetzenDialog, treffer_in_text


@pytest.fixture
def dialog(qtbot) -> SuchenErsetzenDialog:  # noqa: ANN001
    from ide.shell.quelltexteditor import QuelltextEditor

    editor = QuelltextEditor()
    qtbot.addWidget(editor)
    editor.setPlainText("Zahl = 1\nprint(Zahl)\nzahlen = []\n")
    dialog = SuchenErsetzenDialog(editor)
    qtbot.addWidget(dialog)
    return dialog


def test_ersetzen_und_alle_ersetzen_treffen_dieselben_stellen(dialog) -> None:  # noqa: ANN001
    dialog.suchfeld.setText("zahl")
    dialog.ersetzenfeld.setText("wert")
    dialog.ganze_woerter.setChecked(True)

    dialog.suchen()
    dialog.ersetzen()
    dialog.ersetzen()

    assert dialog._editor.toPlainText() == "wert = 1\nprint(wert)\nzahlen = []\n"


def test_gross_klein_beachten(dialog) -> None:  # noqa: ANN001
    dialog.suchfeld.setText("zahl")
    dialog.gross_klein.setChecked(True)
    dialog.ersetzenfeld.setText("x")

    assert dialog.alle_ersetzen() == 1
    assert dialog.meldung.text() == "1 Stelle ersetzt."


def test_kein_treffer_wird_gemeldet(dialog) -> None:  # noqa: ANN001
    dialog.suchfeld.setText("gibtsnicht")

    assert not dialog.suchen()
    assert dialog.meldung.text() == "„gibtsnicht“ kommt nicht vor."


def test_rueckwaerts(dialog) -> None:  # noqa: ANN001
    dialog.suchfeld.setText("Zahl")
    dialog.gross_klein.setChecked(True)
    cursor = dialog._editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.End)
    dialog._editor.setTextCursor(cursor)

    assert dialog.suchen(rueckwaerts=True)
    assert dialog._editor.textCursor().blockNumber() == 1


def test_suchen_laeuft_nach_dem_letzten_treffer_um(dialog) -> None:  # noqa: ANN001
    dialog.suchfeld.setText("Zahl")
    dialog.gross_klein.setChecked(True)

    assert dialog.suchen() is True
    erster_treffer = dialog._editor.textCursor().selectionStart()
    assert dialog.suchen() is True
    assert dialog._editor.textCursor().selectionStart() != erster_treffer
    # Nach dem letzten Treffer wieder von vorn.
    assert dialog.suchen() is True
    assert dialog._editor.textCursor().selectionStart() == erster_treffer


def test_alle_ersetzen_ohne_schalter(dialog) -> None:  # noqa: ANN001
    dialog.suchfeld.setText("zahl")
    dialog.ersetzenfeld.setText("wert")

    assert dialog.alle_ersetzen() == 3
    assert dialog._editor.toPlainText() == "wert = 1\nprint(wert)\nwerten = []\n"


def test_treffer_in_text() -> None:
    text = "a = zahl\nzahlen = 2\nZAHL = 3\n"

    assert [n for n, _ in treffer_in_text(text, "zahl")] == [1, 2, 3]
    assert [n for n, _ in treffer_in_text(text, "zahl", ganze_woerter=True)] == [1, 3]
    assert [n for n, _ in treffer_in_text(text, "zahl", gross_klein=True)] == [1, 2]


def test_in_allen_dateien_suchen(qtbot, tmp_path: Path, hauptfenster_bauen) -> None:  # noqa: ANN001
    (tmp_path / "main.py").write_text("from u_rechnen import summe\n", encoding="utf-8")
    (tmp_path / "u_rechnen.py").write_text("def summe(a, b):\n    return a + b\n", encoding="utf-8")
    (tmp_path / "u_main.py").write_text("x = 1\n", encoding="utf-8")
    natter = tmp_path / "t.natter"
    natter.write_text(json.dumps({
        "format": "natter-project/1", "name": "T", "type": "console", "main": "main.py",
    }), encoding="utf-8")
    fenster = hauptfenster_bauen()
    fenster.projekt_oeffnen(natter)
    editor = fenster.datei_oeffnen(tmp_path / "u_main.py")
    editor.setPlainText("x = summe(1, 2)\n")

    fenster.aktionen["suchen.in_dateien"].qaction.trigger()
    dialog = fenster.letzter_dateisuche_dialog
    dialog.suchfeld.setText("summe")
    anzahl = dialog.suchen()

    assert anzahl == 2
    assert "u_main.py, Zeile 1: x = summe(1, 2)" in dialog.zeilen()
    dialog._springen(dialog.liste.item(1))
    assert fenster._aktueller_editor().textCursor().blockNumber() == 0


def test_suchdialog_behaelt_den_suchtext(
    qtbot, tmp_path: Path, hauptfenster_bauen
) -> None:  # noqa: ANN001
    (tmp_path / "main.py").write_text("abc\n", encoding="utf-8")
    natter = tmp_path / "t.natter"
    natter.write_text(json.dumps({
        "format": "natter-project/1", "name": "T", "type": "console", "main": "main.py",
    }), encoding="utf-8")
    fenster = hauptfenster_bauen()
    fenster.projekt_oeffnen(natter)
    fenster.datei_oeffnen(tmp_path / "main.py")

    fenster._suchen_aktion()
    fenster._suchen_dialog.suchfeld.setText("abc")
    fenster._suchen_dialog.close()
    fenster._suchen_aktion()

    assert fenster._suchen_dialog.suchfeld.text() == "abc"
