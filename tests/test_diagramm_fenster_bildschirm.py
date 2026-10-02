"""Fenstergröße, Thema und Hilfe im Diagramm-Editor (Punkte 304, 305
und 308). Headless.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QRect, QSettings
from PySide6.QtWidgets import QMessageBox

from ide.diagramm import DiagrammFenster, diagramm_erzeugen, fenstergroesse
from ide.diagramm.codefenster import CodeFenster
from ide.diagramm.klassendialog import KlassenDialog
from ide.diagramm.neu import MVP_TYPEN

#: Die Arbeitsfläche von 1366 × 768 bei 125 % ohne Taskleiste.
_KLEIN = QRect(0, 0, 1093, 575)


@pytest.fixture
def kleiner_bildschirm(monkeypatch: pytest.MonkeyPatch) -> QRect:
    monkeypatch.setattr(
        fenstergroesse, "verfuegbare_flaeche", lambda fenster: _KLEIN
    )
    return _KLEIN


def _liegt_darin(fenster, flaeche: QRect) -> bool:
    """Ob das Fenster samt geschätztem Rahmen in `flaeche` liegt."""
    lage = fenster.geometry()
    return (
        lage.left() >= flaeche.left()
        and lage.top() >= flaeche.top()
        and lage.right() + fenstergroesse._RAHMEN_BREITE <= flaeche.right()
        and lage.bottom() + fenstergroesse._RAHMEN_HOEHE <= flaeche.bottom()
    )


def test_fenster_passen_auf_einen_kleinen_bildschirm(
    tmp_path: Path, kleiner_bildschirm: QRect
) -> None:
    fenster = DiagrammFenster(
        diagramm_erzeugen("class", tmp_path / "k.pdiag", "k")
    )
    code = CodeFenster("x = 1\n", "Quelltext – k", fenster)
    klasse = fenster.zeichenflaeche.form_platzieren("class", 100, 100)
    dialog = KlassenDialog(klasse, fenster)

    for element in (fenster, code, dialog):
        assert _liegt_darin(element, kleiner_bildschirm), (
            type(element).__name__,
            element.geometry(),
        )


def test_diagrammfenster_merkt_sich_seine_groesse(tmp_path: Path) -> None:
    erstes = DiagrammFenster(
        diagramm_erzeugen("class", tmp_path / "a.pdiag", "a")
    )
    erstes.resize(700, 480)
    erstes.close()

    zweites = DiagrammFenster(
        diagramm_erzeugen("class", tmp_path / "b.pdiag", "b")
    )

    assert (zweites.width(), zweites.height()) == (700, 480)


def test_quelltextfenster_merkt_sich_seine_groesse() -> None:
    erstes = CodeFenster("x = 1\n", "Quelltext")
    erstes.resize(500, 400)
    erstes.reject()

    zweites = CodeFenster("x = 1\n", "Quelltext")

    assert (zweites.width(), zweites.height()) == (500, 400)


def test_quelltextfenster_uebernimmt_das_dunkle_design() -> None:
    """Punkt 305: der Editor im Quelltext-Fenster war immer hell."""
    QSettings(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        "Natter",
        "Natter-IDE",
    ).setValue("design/thema", "dark")

    fenster = CodeFenster("from __future__ import annotations\n", "Quelltext")

    assert fenster.ansicht._thema == "dark"


@pytest.mark.parametrize("typ", list(MVP_TYPEN))
def test_hilfe_im_diagramm_editor_zeigt_etwas(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, typ: str
) -> None:
    """Punkt 308: „Hilfe → Über den Diagramm-Editor“ tat nichts."""
    gezeigt: list[tuple[str, str]] = []
    monkeypatch.setattr(
        QMessageBox,
        "about",
        staticmethod(lambda eltern, titel, text: gezeigt.append((titel, text))),
    )
    fenster = DiagrammFenster(
        diagramm_erzeugen(typ, tmp_path / f"{typ}.pdiag", typ)
    )

    fenster.aktionen["Hilfe/Über den Diagramm-Editor"].trigger()

    assert len(gezeigt) == 1
    titel, text = gezeigt[0]
    assert titel == "Über den Diagramm-Editor"
    assert "Handbuch, Abschnitt 3.4" in text
