"""Punkt 132: Strg+Y wiederholt in allen drei Zeichenflächen.

Das Handbuch nennt Strg+Y, das Menü kannte nur Strg+Umschalt+Z. Im
Struktogramm und in der Entscheidungstabelle blieb Strg+Y deshalb
ohne Wirkung; nur die Zeichenfläche der Formen-Diagramme fing die
Taste selbst ab. Geprüft wird mit einem echten Tastendruck, der über
das Fenster läuft.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtTest import QTest

from ide.diagramm import DiagrammFenster, diagramm_erzeugen
from ide.diagramm.bloecke import Einfuegestelle


def _formen(fenster: DiagrammFenster) -> tuple[Callable[[], None], Callable[[], int]]:
    flaeche = fenster.zeichenflaeche
    return (
        lambda: flaeche.form_platzieren("class", 40, 40),
        lambda: len(flaeche.formen),
    )


def _struktogramm(
    fenster: DiagrammFenster,
) -> tuple[Callable[[], None], Callable[[], int]]:
    flaeche = fenster.zeichenflaeche
    return (
        lambda: flaeche.block_einfuegen(
            "statement", Einfuegestelle(flaeche.wurzel, "children", 0)
        ),
        lambda: len(flaeche.wurzel.get("children") or []),
    )


def _tabelle(fenster: DiagrammFenster) -> tuple[Callable[[], None], Callable[[], int]]:
    flaeche = fenster.zeichenflaeche
    return (
        lambda: flaeche.zeile_hinzufuegen("conditions"),
        lambda: len(flaeche.diagramm.daten.get("conditions") or []),
    )


@pytest.mark.parametrize(
    ("typ", "werkzeug"),
    [
        ("class", _formen),
        ("struktogramm", _struktogramm),
        ("entscheidungstabelle", _tabelle),
    ],
)
def test_strg_y_wiederholt(tmp_path: Path, qtbot, typ: str, werkzeug) -> None:  # noqa: ANN001
    fenster = DiagrammFenster(diagramm_erzeugen(typ, tmp_path / "d.pdiag", "d"))
    qtbot.addWidget(fenster)
    fenster.show()
    fenster.activateWindow()
    qtbot.waitExposed(fenster)
    # Tastenkürzel eines Fensters greifen nur, wenn es aktiv ist.
    qtbot.waitUntil(fenster.isActiveWindow)
    flaeche = fenster.zeichenflaeche
    flaeche.setFocus()
    qtbot.waitUntil(flaeche.hasFocus)
    aendern, zaehlen = werkzeug(fenster)
    vorher = zaehlen()
    aendern()
    nachher = zaehlen()
    assert nachher != vorher
    flaeche.rueckgaengig()
    assert zaehlen() == vorher

    QTest.keyClick(flaeche, Qt.Key.Key_Y, Qt.KeyboardModifier.ControlModifier)

    assert zaehlen() == nachher


def test_menue_nennt_beide_kuerzel(tmp_path: Path) -> None:
    fenster = DiagrammFenster(
        diagramm_erzeugen("struktogramm", tmp_path / "d.pdiag", "d")
    )

    kuerzel = fenster.aktionen["Bearbeiten/Wiederholen"].shortcuts()

    assert QKeySequence("Ctrl+Y") in kuerzel
    assert QKeySequence("Ctrl+Shift+Z") in kuerzel
