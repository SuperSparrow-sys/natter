"""Stränge eines Parallelabschnitts (Punkt 63 der offenen Punkte).

Ein neuer Parallelabschnitt hat zwei Stränge, und dabei blieb es: das
Format erlaubt beliebig viele, aber nichts in der Oberfläche fügte
einen hinzu. Jetzt wie bei den Fällen einer Mehrfachauswahl über das
Kontextmenü, das Menü „Block“ und die Tasten Plus und Minus.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent

from ide.diagramm import DiagrammFenster, diagramm_erzeugen
from ide.diagramm.bloecke import Einfuegestelle
from ide.diagramm.struktogramm_canvas import VERSATZ, StruktogrammCanvas
from ide.diagramm.struktogramm_code import als_python


@pytest.fixture
def flaeche(qtbot, tmp_path: Path) -> StruktogrammCanvas:  # noqa: ANN001
    diagramm = diagramm_erzeugen("struktogramm", tmp_path / "s.pdiag", "ablauf")
    return StruktogrammCanvas(diagramm)


def _parallel(flaeche: StruktogrammCanvas) -> dict:
    return flaeche.block_einfuegen(
        "parallel", Einfuegestelle(flaeche.wurzel, "children", 0)
    )


def _taste(flaeche: StruktogrammCanvas, taste: Qt.Key, text: str) -> None:
    flaeche.keyPressEvent(
        QKeyEvent(QEvent.Type.KeyPress, taste, Qt.KeyboardModifier.NoModifier, text)
    )


def test_drei_straenge_anlegen_und_wieder_entfernen(
    flaeche: StruktogrammCanvas,
) -> None:
    """Das Kriterium aus dem Punkt."""
    block = _parallel(flaeche)

    flaeche.strang_hinzufuegen(block)
    assert len(block["branches"]) == 3
    kasten = next(k for k in flaeche._layout_erneuern().alle() if k.block is block)
    assert len(kasten.zweige) == 3

    flaeche.strang_entfernen(block)
    assert len(block["branches"]) == 2


def test_zwei_straenge_bleiben_mindestens(flaeche: StruktogrammCanvas) -> None:
    block = _parallel(flaeche)

    assert flaeche.strang_entfernbar(block) is None
    flaeche.strang_entfernen(block)

    assert len(block["branches"]) == 2


def test_ein_strang_mit_inhalt_kommt_mit_rueckgaengig_zurueck(
    flaeche: StruktogrammCanvas,
) -> None:
    block = _parallel(flaeche)
    flaeche.strang_hinzufuegen(block)
    anweisung = flaeche.block_einfuegen(
        "statement", Einfuegestelle(block, "branches", 0, 1)
    )
    flaeche.auswaehlen(anweisung)

    flaeche.strang_entfernen(block, 1)
    assert [len(s) for s in block["branches"]] == [0, 0]
    assert flaeche.ausgewaehlter_block is None

    flaeche.rueckgaengig()
    assert block["branches"][1] == [anweisung]

    flaeche.wiederholen()
    assert [len(s) for s in block["branches"]] == [0, 0]


def test_wiederholen_setzt_denselben_strang_wieder_ein(
    flaeche: StruktogrammCanvas,
) -> None:
    block = _parallel(flaeche)
    flaeche.strang_hinzufuegen(block)
    neu = block["branches"][2]

    flaeche.rueckgaengig()
    assert len(block["branches"]) == 2
    flaeche.wiederholen()

    assert block["branches"][2] is neu


def test_plus_und_minus_im_parallelabschnitt(flaeche: StruktogrammCanvas) -> None:
    block = _parallel(flaeche)
    flaeche.auswaehlen(block)

    _taste(flaeche, Qt.Key.Key_Plus, "+")
    _taste(flaeche, Qt.Key.Key_Plus, "+")
    assert len(block["branches"]) == 4

    _taste(flaeche, Qt.Key.Key_Minus, "-")
    assert len(block["branches"]) == 3


def test_plus_wirkt_auf_den_innersten_block_mit_spalten(
    flaeche: StruktogrammCanvas,
) -> None:
    """Eine Mehrfachauswahl in einem Strang: Plus auf einer Anweisung
    darin gibt der Auswahl einen Fall, nicht dem Parallelabschnitt
    einen Strang."""
    block = _parallel(flaeche)
    auswahl = flaeche.block_einfuegen(
        "multi_branch", Einfuegestelle(block, "branches", 0, 0)
    )
    innen = flaeche.block_einfuegen(
        "statement", Einfuegestelle(auswahl, "children", 0, 0)
    )
    flaeche.auswaehlen(innen)

    _taste(flaeche, Qt.Key.Key_Plus, "+")

    assert len(auswahl["cases"]) == 3
    assert len(block["branches"]) == 2


def test_kontextmenue_entfernt_den_strang_unter_der_maus(
    flaeche: StruktogrammCanvas,
) -> None:
    block = _parallel(flaeche)
    flaeche.strang_hinzufuegen(block)
    markiert = flaeche.block_einfuegen(
        "statement", Einfuegestelle(block, "branches", 0, 0)
    )
    kasten = next(k for k in flaeche._layout_erneuern().alle() if k.block is block)
    mitte = kasten.zweige[0][1].center()

    menue = flaeche.kontextmenue_fuer(mitte.x() + VERSATZ, mitte.y() + VERSATZ)
    texte = [a.text() for a in menue.actions()]
    assert "Strang hinzufügen" in texte
    next(a for a in menue.actions() if a.text() == "Strang entfernen").trigger()

    assert len(block["branches"]) == 2
    assert all(markiert not in strang for strang in block["branches"])


def test_menue_block_kennt_die_straenge(
    qtbot, tmp_path: Path  # noqa: ANN001
) -> None:
    fenster = DiagrammFenster(
        diagramm_erzeugen("struktogramm", tmp_path / "m.pdiag", "ablauf")
    )
    flaeche = fenster.zeichenflaeche
    block = _parallel(flaeche)
    flaeche.auswaehlen(block)
    fenster._blockmenue_aktualisieren()

    assert not fenster.aktionen["Block/Strang entfernen"].isEnabled()
    fenster.aktionen["Block/Strang hinzufügen"].trigger()
    fenster._blockmenue_aktualisieren()
    assert fenster.aktionen["Block/Strang entfernen"].isEnabled()
    fenster.aktionen["Block/Strang entfernen"].trigger()

    assert len(block["branches"]) == 2


def test_der_code_nennt_jeden_strang(flaeche: StruktogrammCanvas) -> None:
    block = _parallel(flaeche)
    flaeche.strang_hinzufuegen(block)

    code = als_python(flaeche.diagramm.daten).text

    assert "# Strang 3" in code
