"""Getippter Text im Memo landet in `lines` (offener Punkt 55)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from pcl import Form, Memo


class _Fenster(Form):
    def create_components(self) -> None:
        self.m_notiz = Memo(self)
        self.m_notiz.width = 200
        self.m_notiz.height = 100
        self.geaendert: list[object] = []
        self.m_notiz.on_change = self.geaendert.append


def _fenster() -> _Fenster:
    fenster = _Fenster()
    fenster.show()
    fenster._qwidget.activateWindow()
    QApplication.processEvents()
    return fenster


def test_getippter_text_steht_in_lines(tmp_path: Path) -> None:
    fenster = _fenster()
    try:
        widget = fenster.m_notiz._qwidget
        widget.setFocus()
        QTest.keyClicks(widget, "Hallo")
        QTest.keyClick(widget, "\r")
        QTest.keyClicks(widget, "Welt")

        assert list(fenster.m_notiz.lines) == ["Hallo", "Welt"]

        ziel = tmp_path / "notiz.txt"
        fenster.m_notiz.lines.save_to_file(ziel)
        assert ziel.read_text(encoding="utf-8") == "Hallo\nWelt\n"
    finally:
        fenster._qwidget.hide()


def test_on_change_kommt_bei_jedem_tastendruck() -> None:
    fenster = _fenster()
    try:
        widget = fenster.m_notiz._qwidget
        widget.setFocus()
        QTest.keyClicks(widget, "abc")

        assert fenster.geaendert == [fenster.m_notiz] * 3
    finally:
        fenster._qwidget.hide()


def test_eine_zuweisung_meldet_sich_genau_einmal() -> None:
    """Das Programm schreibt ins Widget, Qt meldet die Änderung
    zurück. Daraus darf weder ein zweites `on_change` noch ein zweites
    Schreiben werden."""
    fenster = _fenster()
    try:
        fenster.m_notiz.lines = ["eins", "zwei"]

        assert fenster.geaendert == [fenster.m_notiz]
        assert fenster.m_notiz._qwidget.toPlainText() == "eins\nzwei"
        assert list(fenster.m_notiz.lines) == ["eins", "zwei"]
    finally:
        fenster._qwidget.hide()


def test_tippen_nach_einer_zuweisung_haengt_an() -> None:
    fenster = _fenster()
    try:
        fenster.m_notiz.lines.add("Zeile 1")
        widget = fenster.m_notiz._qwidget
        widget.setFocus()
        widget.moveCursor(widget.textCursor().MoveOperation.End)
        QTest.keyClick(widget, "\r")
        QTest.keyClicks(widget, "Zeile 2")

        assert list(fenster.m_notiz.lines) == ["Zeile 1", "Zeile 2"]
    finally:
        fenster._qwidget.hide()


def test_leeres_memo_hat_keine_zeilen() -> None:
    fenster = _fenster()
    try:
        fenster.m_notiz.lines = ["x"]
        fenster.m_notiz._qwidget.clear()

        assert list(fenster.m_notiz.lines) == []
    finally:
        fenster._qwidget.hide()
