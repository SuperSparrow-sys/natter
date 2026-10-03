"""Fälle einer Mehrfach- oder Fallauswahl im Struktogramm (Punkt 53
der offenen Punkte).

Bis dahin ließen sich die Fälle nur im Code anlegen: `fall_hinzufuegen`
und `fall_entfernen` der Zeichenfläche rief nichts in der Oberfläche
auf, und die Beschriftung eines Falls war gar nicht zu ändern. Dazu
kommt die Fallauswahl („case of“) als eigener Block.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QInputDialog

from ide.diagramm import DiagrammFenster, diagramm_erzeugen
from ide.diagramm.bloecke import Einfuegestelle, fall_hinzufuegen, neuer_block
from ide.diagramm.struktogramm_canvas import VERSATZ, StruktogrammCanvas
from ide.diagramm.struktogramm_code import als_python


@pytest.fixture
def flaeche(qtbot, tmp_path: Path) -> StruktogrammCanvas:  # noqa: ANN001
    diagramm = diagramm_erzeugen("struktogramm", tmp_path / "s.pdiag", "vorzeichen")
    return StruktogrammCanvas(diagramm)


def _einfuegen(flaeche: StruktogrammCanvas, art: str) -> dict:
    return flaeche.block_einfuegen(art, Einfuegestelle(flaeche.wurzel, "children", 0))


def _beschriftungen(block: dict) -> list[str]:
    return [fall["label"] for fall in block["cases"]]


def _taste(flaeche: StruktogrammCanvas, taste: Qt.Key, text: str) -> None:
    flaeche.keyPressEvent(
        QKeyEvent(QEvent.Type.KeyPress, taste, Qt.KeyboardModifier.NoModifier, text)
    )


def _zelle(flaeche: StruktogrammCanvas, block: dict, nummer: int) -> QPointF:
    """Mitte der Beschriftungszelle eines Falls, in Flächenkoordinaten."""
    kasten = next(k for k in flaeche._layout_erneuern().alle() if k.block is block)
    bereich = kasten.zweige[nummer][1]
    return QPointF(bereich.center().x() + VERSATZ, bereich.top() + 8 + VERSATZ)


# -- Datenmodell ---------------------------------------------------------


def test_eine_fallauswahl_beginnt_mit_zwei_werten_und_sonst() -> None:
    block = neuer_block({"root": {"kind": "sequence", "children": []}}, "case_of")

    assert _beschriftungen(block) == ["1", "2", "sonst"]


def test_ein_neuer_fall_kommt_vor_sonst() -> None:
    block = neuer_block({"root": {"kind": "sequence", "children": []}}, "case_of")

    fall_hinzufuegen(block)

    assert _beschriftungen(block) == ["1", "2", "3", "sonst"]


# -- Hinzufügen, Entfernen, Rückgängig -----------------------------------


def test_plus_und_minus_aendern_die_faelle(flaeche: StruktogrammCanvas) -> None:
    auswahl = _einfuegen(flaeche, "multi_branch")
    flaeche.auswaehlen(auswahl)

    _taste(flaeche, Qt.Key.Key_Plus, "+")
    assert _beschriftungen(auswahl) == ["Fall 1", "Fall 2", "Fall 3"]

    _taste(flaeche, Qt.Key.Key_Minus, "-")
    assert _beschriftungen(auswahl) == ["Fall 1", "Fall 2"]


def test_plus_wirkt_auch_mit_einem_block_in_einer_spalte(flaeche: StruktogrammCanvas) -> None:
    auswahl = _einfuegen(flaeche, "case_of")
    anweisung = flaeche.block_einfuegen(
        "statement", Einfuegestelle(auswahl, "children", 0, 1)
    )
    flaeche.auswaehlen(anweisung)

    _taste(flaeche, Qt.Key.Key_Plus, "+")

    assert _beschriftungen(auswahl) == ["1", "2", "3", "sonst"]


def test_wiederholen_legt_denselben_fall_wieder_an(flaeche: StruktogrammCanvas) -> None:
    """Das alte Kommando entfernte beim Wiederholen einen Fall, statt
    ihn wieder anzulegen."""
    auswahl = _einfuegen(flaeche, "case_of")
    flaeche.fall_hinzufuegen(auswahl)
    neu = auswahl["cases"][2]

    flaeche.rueckgaengig()
    assert _beschriftungen(auswahl) == ["1", "2", "sonst"]
    flaeche.wiederholen()

    assert _beschriftungen(auswahl) == ["1", "2", "3", "sonst"]
    assert auswahl["cases"][2] is neu


def test_entfernen_nimmt_den_letzten_wert_und_laesst_sonst(flaeche: StruktogrammCanvas) -> None:
    auswahl = _einfuegen(flaeche, "case_of")

    flaeche.fall_entfernen(auswahl)
    assert _beschriftungen(auswahl) == ["1", "sonst"]

    flaeche.fall_entfernen(auswahl)
    assert _beschriftungen(auswahl) == ["1", "sonst"]

    flaeche.rueckgaengig()
    assert _beschriftungen(auswahl) == ["1", "2", "sonst"]


def test_ein_bestimmter_fall_laesst_sich_entfernen(flaeche: StruktogrammCanvas) -> None:
    auswahl = _einfuegen(flaeche, "case_of")

    flaeche.fall_entfernen(auswahl, 0)
    assert _beschriftungen(auswahl) == ["2", "sonst"]

    flaeche.rueckgaengig()
    assert _beschriftungen(auswahl) == ["1", "2", "sonst"]


# -- Beschriften ---------------------------------------------------------


def test_doppelklick_auf_die_beschriftung_beschriftet_den_fall(
    flaeche: StruktogrammCanvas, monkeypatch: pytest.MonkeyPatch
) -> None:
    auswahl = _einfuegen(flaeche, "multi_branch")
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("x < 0", True))
    punkt = _zelle(flaeche, auswahl, 0)

    flaeche.mouseDoubleClickEvent(
        QMouseEvent(
            QEvent.Type.MouseButtonDblClick,
            punkt,
            punkt,
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
    )

    assert _beschriftungen(auswahl) == ["x < 0", "Fall 2"]
    assert auswahl["text"] == "Auswahl"
    flaeche.rueckgaengig()
    assert _beschriftungen(auswahl) == ["Fall 1", "Fall 2"]


def test_fall_bei_trifft_nur_die_beschriftung(flaeche: StruktogrammCanvas) -> None:
    auswahl = _einfuegen(flaeche, "case_of")
    punkt = _zelle(flaeche, auswahl, 2)

    assert flaeche.fall_bei(punkt.x(), punkt.y()) == (auswahl, 2)
    assert flaeche.fall_bei(punkt.x(), punkt.y() + 60) is None


# -- Kontextmenü und Menü „Block“ ----------------------------------------


def test_kontextmenue_an_einer_spalte(flaeche: StruktogrammCanvas) -> None:
    auswahl = _einfuegen(flaeche, "case_of")
    punkt = _zelle(flaeche, auswahl, 0)

    menue = flaeche.kontextmenue_fuer(punkt.x(), punkt.y())
    aktionen = {a.text(): a for a in menue.actions() if a.text()}

    assert list(aktionen) == [
        "Fall beschriften …", "Fall hinzufügen", "Fall entfernen", "Beschriften …",
        "Ausschneiden", "Kopieren", "Duplizieren", "Einfügen", "Löschen",
        "Diagramm umbenennen …",
    ]
    aktionen["Fall entfernen"].trigger()
    assert _beschriftungen(auswahl) == ["2", "sonst"]


def test_menue_block_im_fenster(qtbot, tmp_path: Path) -> None:  # noqa: ANN001
    fenster = DiagrammFenster(
        diagramm_erzeugen("struktogramm", tmp_path / "s.pdiag", "vorzeichen")
    )
    qtbot.addWidget(fenster)
    flaeche = fenster.zeichenflaeche
    auswahl = _einfuegen(flaeche, "case_of")
    flaeche.auswaehlen(None)

    fenster._blockmenue_aktualisieren()
    assert not fenster.aktionen["Block/Fall hinzufügen"].isEnabled()

    flaeche.auswaehlen(auswahl)
    fenster._blockmenue_aktualisieren()
    fenster.aktionen["Block/Fall hinzufügen"].trigger()

    assert _beschriftungen(auswahl) == ["1", "2", "3", "sonst"]
    assert not fenster.aktionen["Block/Fall beschriften …"].isEnabled()


# -- Code ----------------------------------------------------------------


def _code(block: dict) -> str:
    return als_python({
        "format": "pdiag/1", "type": "struktogramm", "name": "t",
        "root": {"id": "b0", "kind": "sequence", "children": [block]},
    }).text


def _fall(label: str, text: str) -> dict:
    return {"label": label, "children": [{"id": label, "kind": "statement", "text": text}]}


def test_mehrfachauswahl_mit_drei_bedingungen() -> None:
    code = _code({"id": "b1", "kind": "multi_branch", "text": "Vorzeichen", "cases": [
        _fall("x < 0", "print(-1)"), _fall("x = 0", "print(0)"), _fall("x > 0", "print(1)"),
    ]})

    assert "if x < 0:" in code
    assert "elif x == 0:" in code
    assert "elif x > 0:" in code
    compile(code, "<struktogramm>", "exec")


def test_fallauswahl_wird_zu_match() -> None:
    code = _code({"id": "b1", "kind": "case_of", "text": "note", "cases": [
        _fall("1", 'print("sehr gut")'), _fall("2", 'print("gut")'), _fall("sonst", "print()"),
    ]})

    assert "match note:" in code
    assert "case 1:" in code
    assert "case _:" in code
    compile(code, "<struktogramm>", "exec")


def test_fallauswahl_mit_vergleich_am_anfang() -> None:
    code = _code({"id": "b1", "kind": "case_of", "text": "x", "cases": [
        _fall("< 0", "print(-1)"), _fall("> 0", "print(1)"), _fall("sonst", "print(0)"),
    ]})

    assert "if x < 0:" in code
    assert "elif x > 0:" in code
    assert "else:" in code
