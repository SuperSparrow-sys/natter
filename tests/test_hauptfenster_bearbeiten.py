"""Tests für das Menü „Bearbeiten“ (Abschnitt 7.2). Rückmeldung
: das Menü existierte, aber jeder Eintrag war wirkungslos.
Rückgängig/Wiederholen/Ausschneiden/Kopieren/Einfügen/Alles auswählen
wirken auf den aktiven Editor-Tab, über die eingebauten
`QPlainTextEdit`-Operationen.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication

from ide.shell.hauptfenster import HauptFenster


def _editor_mit_text(fenster: HauptFenster, tmp_path: Path, text: str):
    pfad = tmp_path / "u_main.py"
    pfad.write_text(text, encoding="utf-8")
    return fenster.datei_oeffnen(pfad)


def test_ohne_offenen_editor_tut_nichts(tmp_path: Path) -> None:
    fenster = HauptFenster()
    # Keine Ausnahme, einfach nichts zu tun.
    fenster._bearbeiten_rueckgaengig()
    fenster._bearbeiten_kopieren()
    fenster._bearbeiten_alles_auswaehlen()


def test_rueckgaengig_macht_eine_aenderung_rueckgaengig(tmp_path: Path) -> None:
    fenster = HauptFenster()
    editor = _editor_mit_text(fenster, tmp_path, "x = 1\n")
    editor.insertPlainText("zusatz")

    fenster._bearbeiten_rueckgaengig()

    assert "zusatz" not in editor.toPlainText()


def test_wiederholen_stellt_die_aenderung_wieder_her(tmp_path: Path) -> None:
    fenster = HauptFenster()
    editor = _editor_mit_text(fenster, tmp_path, "x = 1\n")
    editor.insertPlainText("zusatz")
    fenster._bearbeiten_rueckgaengig()

    fenster._bearbeiten_wiederholen()

    assert "zusatz" in editor.toPlainText()


def test_alles_auswaehlen_markiert_den_gesamten_text(tmp_path: Path) -> None:
    fenster = HauptFenster()
    editor = _editor_mit_text(fenster, tmp_path, "x = 1\ny = 2\n")

    fenster._bearbeiten_alles_auswaehlen()

    assert editor.textCursor().selectedText() == editor.toPlainText().replace("\n", " ")


def test_kopieren_und_einfuegen_ueber_die_zwischenablage(tmp_path: Path) -> None:
    fenster = HauptFenster()
    editor = _editor_mit_text(fenster, tmp_path, "hallo welt\n")
    cursor = editor.textCursor()
    cursor.select(cursor.SelectionType.WordUnderCursor)
    editor.setTextCursor(cursor)

    fenster._bearbeiten_kopieren()
    assert QApplication.clipboard().text() == "hallo"

    cursor = editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.End)
    editor.setTextCursor(cursor)
    fenster._bearbeiten_einfuegen()

    assert editor.toPlainText().endswith("hallo")
