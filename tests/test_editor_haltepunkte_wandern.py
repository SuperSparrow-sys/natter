"""Haltepunkte im Quelltexteditor bei Rückgängig, Wiederholen und
Änderungen, die mitten in einer Zeile beginnen (Punkte 596 und 610).

Ein Haltepunkt gehört zu einer Anweisung, nicht zu einer Zeilennummer.
Wandert er falsch, hält das Programm an einer anderen Stelle, oder er
ist ganz weg.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from ide.shell.quelltexteditor import QuelltextEditor


def _editor(qtbot, text: str) -> QuelltextEditor:  # noqa: ANN001
    feld = QuelltextEditor()
    qtbot.addWidget(feld)
    feld.setPlainText(text)
    return feld


def _cursor_auf(feld: QuelltextEditor, zeile: int, spalte: int = 0) -> None:
    cursor = feld.textCursor()
    cursor.setPosition(feld.document().findBlockByNumber(zeile - 1).position() + spalte)
    feld.setTextCursor(cursor)


def test_strg_d_auf_gefalteter_funktion_rueckgaengig_und_wiederholen(qtbot) -> None:  # noqa: ANN001
    """Nach Strg+Z blieb nur der erste, nach Strg+Y nur der zweite."""
    feld = _editor(qtbot, "x = 1\ny = 2\n\ndef f():\n    a = 1\n    b = 2\nz = 3\n")
    feld.breakpoints = {2, 5}
    feld.falten(4)
    _cursor_auf(feld, 4)

    feld.zeile_duplizieren()
    nachher = set(feld.breakpoints)
    feld.undo()
    zurueck = set(feld.breakpoints)
    feld.redo()

    assert zurueck == {2, 5}
    assert feld.breakpoints == nachher
    assert {2, 5} <= nachher


def test_rueckgaengig_aus_dem_kontextmenue_nimmt_den_haltepunkt_mit(qtbot) -> None:  # noqa: ANN001
    """Qts Eintrag im Kontextmenü rief am Editor vorbei."""
    feld = _editor(qtbot, "a = 1\nb = 2\nc = 3\n")
    feld.breakpoints = {3}
    _cursor_auf(feld, 2)
    feld.zeile_verschieben(True)
    assert feld.breakpoints == {2}

    rueckgaengig = next(
        a for a in feld.kontextmenue().actions() if a.objectName() == "edit-undo"
    )
    rueckgaengig.trigger()

    assert feld.toPlainText().startswith("a = 1\nb = 2")
    assert feld.breakpoints == {3}


def test_eine_geloeschte_zeile_bringt_ihren_haltepunkt_zurueck(qtbot) -> None:  # noqa: ANN001
    feld = _editor(qtbot, "a = 1\nb = 2\nc = 3\n")
    feld.breakpoints = {2}
    feld.bedingungen = {2: "b > 1"}
    cursor = feld.textCursor()
    block = feld.document().findBlockByNumber(1)
    cursor.setPosition(block.position())
    cursor.setPosition(block.next().position(), cursor.MoveMode.KeepAnchor)
    cursor.removeSelectedText()
    assert feld.breakpoints == set()

    QTest.keyClick(feld, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)

    assert feld.toPlainText().startswith("a = 1\nb = 2")
    assert feld.breakpoints == {2}
    assert feld.bedingungen == {2: "b > 1"}


@pytest.mark.parametrize(
    ("spalte", "erwartet"), [(4, {3}), (0, {3}), (9, {2})],
    ids=["hinter_dem_einzug", "am_anfang", "am_ende"],
)
def test_eingabetaste_und_der_haltepunkt(qtbot, spalte: int, erwartet: set) -> None:  # noqa: ANN001
    """Hinter dem Einzug von `    b = 2` schiebt die Eingabetaste die
    Anweisung nach unten, der Haltepunkt gehört zu ihr. Am Zeilenende
    bleibt er stehen."""
    feld = _editor(qtbot, "def f():\n    b = 2\n")
    feld.breakpoints = {2}
    _cursor_auf(feld, 2, spalte)

    QTest.keyClick(feld, Qt.Key.Key_Return)

    assert feld.breakpoints == erwartet
    zeile = sorted(erwartet)[0]
    assert feld.document().findBlockByNumber(zeile - 1).text().strip() == "b = 2"


@pytest.mark.parametrize(
    ("alt", "neu", "haltepunkt", "anweisung"),
    [
        # Neue Zeile davor, der Unterschied beginnt mitten in der Zeile.
        ("x = 1\ny = 2\n", "x = 0\nx = 1\ny = 2\n", 1, "x = 1"),
        # Die Zeile davor fällt weg.
        ("a = 1\nb = 2\nc = 3\n", "a = 1\nc = 3\n", 3, "c = 3"),
        # Eine Ereignismethode kommt mitten in die Klasse.
        (
            "class F:\n    def a(self):\n        pass\n\n    def b(self):\n        x = 1\n",
            "class F:\n    def a(self):\n        pass\n\n    def neu(self):\n"
            "        pass\n\n    def b(self):\n        x = 1\n",
            6,
            "x = 1",
        ),
    ],
    ids=["zeile_davor", "zeile_weg", "methode_eingefuegt"],
)
def test_ersetzen_von_aussen_haelt_den_haltepunkt_an_der_anweisung(
    qtbot, alt: str, neu: str, haltepunkt: int, anweisung: str  # noqa: ANN001
) -> None:
    """Beim Neuladen einer von außen geänderten Datei und beim Einfügen
    einer Ereignismethode ersetzt `editortext_ersetzen` den Text; der
    Haltepunkt blieb dabei auf der falschen Zeile oder fiel weg."""
    from ide.designer.canvas import editortext_ersetzen

    feld = _editor(qtbot, alt)
    feld.breakpoints = {haltepunkt}
    feld.bedingungen = {haltepunkt: "True"}

    editortext_ersetzen(feld, neu)

    assert len(feld.breakpoints) == 1
    zeile = next(iter(feld.breakpoints))
    assert feld.document().findBlockByNumber(zeile - 1).text().strip() == anweisung
    assert feld.bedingungen == {zeile: "True"}
    feld.undo()
    assert feld.breakpoints == {haltepunkt}
