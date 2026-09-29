"""Tests für die Menüs „Suchen“, „Quelltext“, „Fenster“ und „Hilfe“
(Abschnitt 7.2). Gemeldet: diese Menüs
existierten, waren aber leer/wirkungslos.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ide.shell.hauptfenster import HauptFenster
from ide.shell.suchen_dialog import SuchenErsetzenDialog


def _editor_mit_text(fenster: HauptFenster, tmp_path: Path, text: str, name: str = "u_main.py"):
    pfad = tmp_path / name
    pfad.write_text(text, encoding="utf-8")
    return fenster.datei_oeffnen(pfad)


# -- Suchen -------------------------------------------------------------


def test_suchen_ohne_offenen_editor_zeigt_hinweis(hauptfenster) -> None:
    hauptfenster._suchen_aktion()
    meldung = hauptfenster.statusBar().currentMessage()
    assert meldung.startswith("Kein Quelltext-Reiter vorn.")
    assert "Projekt-Explorer" in meldung


def test_suchen_oeffnet_den_dialog_fuer_den_aktiven_editor(tmp_path: Path, hauptfenster) -> None:
    _editor_mit_text(hauptfenster, tmp_path, "x = 1\n")

    hauptfenster._suchen_aktion()

    assert isinstance(hauptfenster._suchen_dialog, SuchenErsetzenDialog)
    # Ein eigenes schwebendes Werkzeugfenster statt in die Hauptfenster-
    # Fläche eingebettet zu werden (sonst verschwindet es hinter den Docks).
    assert hauptfenster._suchen_dialog.isWindow() is True


def test_gehe_zu_zeile_ohne_offenen_editor_zeigt_hinweis(hauptfenster) -> None:
    hauptfenster._gehe_zu_zeile_aktion()
    meldung = hauptfenster.statusBar().currentMessage()
    assert meldung.startswith("Kein Quelltext-Reiter vorn.")
    assert "Projekt-Explorer" in meldung


def test_gehe_zu_zeile_bewegt_den_cursor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hauptfenster
) -> None:
    editor = _editor_mit_text(hauptfenster, tmp_path, "zeile1\nzeile2\nzeile3\n")
    erwartete_position = editor.document().findBlockByNumber(2).position()

    monkeypatch.setattr(
        "ide.shell.hauptfenster.QInputDialog.getInt",
        staticmethod(lambda *a, **k: (3, True)),
    )

    hauptfenster._gehe_zu_zeile_aktion()

    assert editor.textCursor().position() == erwartete_position


def test_gehe_zu_zeile_bei_abbruch_bewegt_den_cursor_nicht(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hauptfenster
) -> None:
    editor = _editor_mit_text(hauptfenster, tmp_path, "zeile1\nzeile2\nzeile3\n")
    ausgangs_position = editor.textCursor().position()

    monkeypatch.setattr(
        "ide.shell.hauptfenster.QInputDialog.getInt",
        staticmethod(lambda *a, **k: (3, False)),
    )

    hauptfenster._gehe_zu_zeile_aktion()

    assert editor.textCursor().position() == ausgangs_position


# -- Quelltext ------------------------------------------------------------


def test_kommentar_umschalten_ohne_offenen_editor_tut_nichts(hauptfenster) -> None:
    hauptfenster._kommentar_umschalten_aktion()  # keine Ausnahme


def test_kommentar_umschalten_wirkt_auf_die_aktuelle_zeile(tmp_path: Path, hauptfenster) -> None:
    editor = _editor_mit_text(hauptfenster, tmp_path, "x = 1\ny = 2\n")
    cursor = editor.textCursor()
    cursor.setPosition(0)
    editor.setTextCursor(cursor)

    hauptfenster._kommentar_umschalten_aktion()

    assert editor.toPlainText() == "# x = 1\ny = 2\n"

    hauptfenster._kommentar_umschalten_aktion()
    assert editor.toPlainText() == "x = 1\ny = 2\n"


def test_kommentar_umschalten_laesst_die_zeilen_markiert(
    tmp_path: Path, hauptfenster,
) -> None:
    # Punkt 220: nach dem ersten Strg+# war die Markierung weg, das
    # zweite nahm nur die letzte Zeile zurück.
    editor = _editor_mit_text(
        hauptfenster, tmp_path, "a = 1\nb = 2\nc = 3\nd = 4\n"
    )
    cursor = editor.textCursor()
    cursor.setPosition(0)
    cursor.setPosition(17, cursor.MoveMode.KeepAnchor)  # bis in c = 3
    editor.setTextCursor(cursor)

    hauptfenster._kommentar_umschalten_aktion()
    assert editor.toPlainText() == "# a = 1\n# b = 2\n# c = 3\nd = 4\n"
    markierung = editor.textCursor()
    assert markierung.selectionStart() == 0
    assert markierung.selectionEnd() == len("# a = 1\n# b = 2\n# c = 3")

    hauptfenster._kommentar_umschalten_aktion()
    assert editor.toPlainText() == "a = 1\nb = 2\nc = 3\nd = 4\n"

    # Ein Schritt für Rückgängig.
    editor.undo()
    assert editor.toPlainText() == "# a = 1\n# b = 2\n# c = 3\nd = 4\n"


def test_kommentar_umschalten_ohne_markierung_laesst_die_marke_stehen(
    tmp_path: Path, hauptfenster,
) -> None:
    editor = _editor_mit_text(hauptfenster, tmp_path, "x = 1\ny = 2\n")
    cursor = editor.textCursor()
    cursor.setPosition(2)  # vor dem =
    editor.setTextCursor(cursor)

    hauptfenster._kommentar_umschalten_aktion()
    assert editor.textCursor().hasSelection() is False
    assert editor.textCursor().position() == 4
    assert editor.textCursor().blockNumber() == 0


# -- Fenster ---------------------------------------------------------------


def test_naechster_und_vorheriger_tab(tmp_path: Path, hauptfenster) -> None:
    _editor_mit_text(hauptfenster, tmp_path, "a\n", "a.py")
    _editor_mit_text(hauptfenster, tmp_path, "b\n", "b.py")
    hauptfenster.editor_tabs.setCurrentIndex(0)

    hauptfenster._naechster_tab_aktion()
    assert hauptfenster.editor_tabs.currentIndex() == 1

    hauptfenster._naechster_tab_aktion()  # läuft um
    assert hauptfenster.editor_tabs.currentIndex() == 0

    hauptfenster._vorheriger_tab_aktion()  # läuft rückwärts um
    assert hauptfenster.editor_tabs.currentIndex() == 1


# -- Hilfe -------------------------------------------------------------


def test_komponenten_referenz_oeffnet_einen_hilfe_reiter(hauptfenster_bauen) -> None:
    """Früher an Windows weitergereicht. Für `.md` ist dort meist gar
    nichts eingetragen: im besten Fall ging der Editor auf, im
    Normalfall passierte nichts (M11, Abschnitt 4)."""
    from ide.viewers import HilfeAnsicht

    fenster = hauptfenster_bauen()

    assert fenster._komponenten_referenz_aktion() is True

    reiter = fenster.editor_tabs.currentWidget()
    assert isinstance(reiter, HilfeAnsicht)
    assert fenster.editor_tabs.tabText(fenster.editor_tabs.currentIndex()) == (
        "Komponenten-Referenz"
    )


def test_ueber_zeigt_eine_dialogbox(monkeypatch: pytest.MonkeyPatch, hauptfenster) -> None:
    aufgerufen = []
    monkeypatch.setattr(
        "ide.shell.hauptfenster.QMessageBox.about",
        staticmethod(lambda *a, **k: aufgerufen.append(a)),
    )

    hauptfenster._ueber_aktion()

    assert len(aufgerufen) == 1
