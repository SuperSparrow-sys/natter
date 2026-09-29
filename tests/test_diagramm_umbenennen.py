"""Diagramm umbenennen (Punkt 64 der offenen Punkte).

`daten["name"]` wurde nur beim Anlegen geschrieben. Beim Struktogramm
steht der Name als Kopfzeile darüber und wird zum Funktionsnamen im
erzeugten Quelltext - ein Tippfehler beim Anlegen ließ sich danach
nicht mehr beheben.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QInputDialog

from ide.diagramm import DiagrammFenster, diagramm_erzeugen
from ide.diagramm.neu import MVP_TYPEN
from ide.diagramm.struktogramm import KOPFHOEHE
from ide.diagramm.struktogramm_canvas import VERSATZ


def _fenster(tmp_path: Path, typ: str, name: str = "alt") -> DiagrammFenster:
    return DiagrammFenster(diagramm_erzeugen(typ, tmp_path / f"{typ}.pdiag", name))


def _antwort(monkeypatch: pytest.MonkeyPatch, text: str) -> None:
    monkeypatch.setattr(
        QInputDialog, "getText", staticmethod(lambda *a, **k: (text, True))
    )


@pytest.mark.parametrize("typ", list(MVP_TYPEN))
def test_jedes_diagramm_laesst_sich_ueber_das_menue_umbenennen(
    qtbot, tmp_path: Path, typ: str, monkeypatch: pytest.MonkeyPatch  # noqa: ANN001
) -> None:
    fenster = _fenster(tmp_path, typ)
    _antwort(monkeypatch, "  neu  ")

    fenster.aktionen["Bearbeiten/Diagramm umbenennen …"].trigger()

    assert fenster.diagramm.daten["name"] == "neu"
    fenster.speichern()
    gespeichert = json.loads(fenster.diagramm.pfad.read_text(encoding="utf-8"))
    assert gespeichert["name"] == "neu"

    fenster.zeichenflaeche.rueckgaengig()
    assert fenster.diagramm.daten["name"] == "alt"


def test_abbrechen_laesst_den_namen_stehen(
    qtbot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch  # noqa: ANN001
) -> None:
    fenster = _fenster(tmp_path, "class")
    monkeypatch.setattr(
        QInputDialog, "getText", staticmethod(lambda *a, **k: ("neu", False))
    )

    fenster.aktionen["Bearbeiten/Diagramm umbenennen …"].trigger()

    assert fenster.diagramm.daten["name"] == "alt"
    assert not fenster.zeichenflaeche.kommandos.kann_rueckgaengig


def test_struktogramm_neuer_name_in_kopfzeile_und_code(
    qtbot, tmp_path: Path  # noqa: ANN001
) -> None:
    fenster = _fenster(tmp_path, "struktogramm", "kasse_buchn")

    assert fenster.diagramm_umbenennen("kasse_buchen")

    flaeche = fenster.zeichenflaeche
    assert flaeche.kopfzeile_bei(VERSATZ + 20, VERSATZ + KOPFHOEHE / 2)
    assert fenster.quelltext_code().startswith("def kasse_buchen():")


def test_doppelklick_auf_die_kopfzeile_fragt_nach_dem_namen(
    qtbot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch  # noqa: ANN001
) -> None:
    fenster = _fenster(tmp_path, "struktogramm", "zaehlen")
    flaeche = fenster.zeichenflaeche
    _antwort(monkeypatch, "zaehlen_bis_zehn")

    punkt = QPointF(VERSATZ + 40, VERSATZ + KOPFHOEHE / 2)
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

    assert fenster.diagramm.daten["name"] == "zaehlen_bis_zehn"


def test_leerer_name_nimmt_die_kopfzeile_weg_und_zurueck(
    qtbot, tmp_path: Path  # noqa: ANN001
) -> None:
    fenster = _fenster(tmp_path, "struktogramm", "zaehlen")
    flaeche = fenster.zeichenflaeche
    oben_vorher = flaeche._layout_erneuern().rechteck.top()

    flaeche.diagramm_umbenennen("")
    assert flaeche._layout_erneuern().rechteck.top() == 0
    assert not flaeche.kopfzeile_bei(VERSATZ + 20, VERSATZ + 5)

    flaeche.rueckgaengig()
    assert flaeche._layout_erneuern().rechteck.top() == oben_vorher


def test_kontextmenue_des_struktogramms_bietet_umbenennen(
    qtbot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch  # noqa: ANN001
) -> None:
    fenster = _fenster(tmp_path, "struktogramm", "zaehlen")
    _antwort(monkeypatch, "summe")

    menue = fenster.zeichenflaeche.kontextmenue_fuer(VERSATZ + 5, VERSATZ + 5)
    next(a for a in menue.actions() if a.text() == "Diagramm umbenennen …").trigger()

    assert fenster.diagramm.daten["name"] == "summe"
