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


def test_suchen_ohne_offenen_editor_zeigt_hinweis() -> None:
    fenster = HauptFenster()
    fenster._suchen_aktion()
    meldung = fenster.statusBar().currentMessage()
    assert meldung.startswith("Kein Editor-Tab aktiv.")
    assert "Projekt-Explorer" in meldung


def test_suchen_oeffnet_den_dialog_fuer_den_aktiven_editor(tmp_path: Path) -> None:
    fenster = HauptFenster()
    _editor_mit_text(fenster, tmp_path, "x = 1\n")

    fenster._suchen_aktion()

    assert isinstance(fenster._suchen_dialog, SuchenErsetzenDialog)
    # Ein eigenes schwebendes Werkzeugfenster statt in die Hauptfenster-
    # Fläche eingebettet zu werden (sonst verschwindet es hinter den Docks).
    assert fenster._suchen_dialog.isWindow() is True


def test_suchen_dialog_findet_text_und_laeuft_um(tmp_path: Path) -> None:
    fenster = HauptFenster()
    editor = _editor_mit_text(fenster, tmp_path, "eins\nzwei\neins\n")
    dialog = SuchenErsetzenDialog(editor)
    dialog.suchfeld.setText("eins")

    assert dialog.suchen() is True
    erster_treffer = editor.textCursor().selectionStart()
    assert dialog.suchen() is True
    zweiter_treffer = editor.textCursor().selectionStart()
    assert zweiter_treffer != erster_treffer
    # Nach dem letzten Treffer wieder von vorn.
    assert dialog.suchen() is True
    assert editor.textCursor().selectionStart() == erster_treffer


def test_suchen_dialog_alle_ersetzen(tmp_path: Path) -> None:
    fenster = HauptFenster()
    editor = _editor_mit_text(fenster, tmp_path, "alt alt alt\n")
    dialog = SuchenErsetzenDialog(editor)
    dialog.suchfeld.setText("alt")
    dialog.ersetzenfeld.setText("neu")

    anzahl = dialog.alle_ersetzen()

    assert anzahl == 3
    assert editor.toPlainText() == "neu neu neu\n"


def test_gehe_zu_zeile_ohne_offenen_editor_zeigt_hinweis() -> None:
    fenster = HauptFenster()
    fenster._gehe_zu_zeile_aktion()
    meldung = fenster.statusBar().currentMessage()
    assert meldung.startswith("Kein Editor-Tab aktiv.")
    assert "Projekt-Explorer" in meldung


def test_gehe_zu_zeile_bewegt_den_cursor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fenster = HauptFenster()
    editor = _editor_mit_text(fenster, tmp_path, "zeile1\nzeile2\nzeile3\n")
    erwartete_position = editor.document().findBlockByNumber(2).position()

    monkeypatch.setattr(
        "ide.shell.hauptfenster.QInputDialog.getInt",
        staticmethod(lambda *a, **k: (3, True)),
    )

    fenster._gehe_zu_zeile_aktion()

    assert editor.textCursor().position() == erwartete_position


def test_gehe_zu_zeile_bei_abbruch_bewegt_den_cursor_nicht(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fenster = HauptFenster()
    editor = _editor_mit_text(fenster, tmp_path, "zeile1\nzeile2\nzeile3\n")
    ausgangs_position = editor.textCursor().position()

    monkeypatch.setattr(
        "ide.shell.hauptfenster.QInputDialog.getInt",
        staticmethod(lambda *a, **k: (3, False)),
    )

    fenster._gehe_zu_zeile_aktion()

    assert editor.textCursor().position() == ausgangs_position


# -- Quelltext ------------------------------------------------------------


def test_kommentar_umschalten_ohne_offenen_editor_tut_nichts() -> None:
    fenster = HauptFenster()
    fenster._kommentar_umschalten_aktion()  # keine Ausnahme


def test_kommentar_umschalten_wirkt_auf_die_aktuelle_zeile(tmp_path: Path) -> None:
    fenster = HauptFenster()
    editor = _editor_mit_text(fenster, tmp_path, "x = 1\ny = 2\n")
    cursor = editor.textCursor()
    cursor.setPosition(0)
    editor.setTextCursor(cursor)

    fenster._kommentar_umschalten_aktion()

    assert editor.toPlainText() == "# x = 1\ny = 2\n"

    fenster._kommentar_umschalten_aktion()
    assert editor.toPlainText() == "x = 1\ny = 2\n"


# -- Fenster ---------------------------------------------------------------


def test_naechster_und_vorheriger_tab(tmp_path: Path) -> None:
    fenster = HauptFenster()
    _editor_mit_text(fenster, tmp_path, "a\n", "a.py")
    _editor_mit_text(fenster, tmp_path, "b\n", "b.py")
    fenster.editor_tabs.setCurrentIndex(0)

    fenster._naechster_tab_aktion()
    assert fenster.editor_tabs.currentIndex() == 1

    fenster._naechster_tab_aktion()  # läuft um
    assert fenster.editor_tabs.currentIndex() == 0

    fenster._vorheriger_tab_aktion()  # läuft rückwärts um
    assert fenster.editor_tabs.currentIndex() == 1


def test_layout_zuruecksetzen_stellt_geschlossene_docks_wieder_her() -> None:
    # Der Projekt-Explorer als Beispiel: die Datenbank ist seit M11,
    # Abschnitt 4 voreingestellt zu und käme deshalb zu Recht nicht
    # zurück.
    fenster = HauptFenster()
    fenster.show()
    fenster.explorer_dock.close()
    assert fenster.explorer_dock.isVisible() is False

    fenster._layout_zuruecksetzen_aktion()

    assert fenster.explorer_dock.isVisible() is True


# -- Hilfe -------------------------------------------------------------


def test_komponenten_referenz_oeffnet_einen_hilfe_reiter() -> None:
    """Früher an Windows weitergereicht. Für `.md` ist dort meist gar
    nichts eingetragen: im besten Fall ging der Editor auf, im
    Normalfall passierte nichts (M11, Abschnitt 4)."""
    from ide.viewers import HilfeAnsicht

    fenster = HauptFenster()

    assert fenster._komponenten_referenz_aktion() is True

    reiter = fenster.editor_tabs.currentWidget()
    assert isinstance(reiter, HilfeAnsicht)
    assert fenster.editor_tabs.tabText(fenster.editor_tabs.currentIndex()) == (
        "Komponenten-Referenz"
    )


def test_ueber_zeigt_eine_dialogbox(monkeypatch: pytest.MonkeyPatch) -> None:
    fenster = HauptFenster()
    aufgerufen = []
    monkeypatch.setattr(
        "ide.shell.hauptfenster.QMessageBox.about",
        staticmethod(lambda *a, **k: aufgerufen.append(a)),
    )

    fenster._ueber_aktion()

    assert len(aufgerufen) == 1
