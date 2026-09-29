"""Regel entfernen und hinzufügen an der ausgewählten Stelle (Punkt 68
der offenen Punkte).

Das Menü rief `regel_entfernen()` und `regel_hinzufuegen()` ohne
Nummer auf. Entfernt wurde deshalb immer die letzte Regel, auch wenn
eine andere ausgewählt war, und eine neue kam immer ans Ende.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ide.diagramm import DiagrammFenster, diagramm_erzeugen
from ide.diagramm.tabelle import zellen
from ide.diagramm.tabelle_canvas import VERSATZ


@pytest.fixture
def fenster(qtbot, tmp_path: Path) -> DiagrammFenster:  # noqa: ANN001
    fenster = DiagrammFenster(
        diagramm_erzeugen("entscheidungstabelle", tmp_path / "t.pdiag", "ampel")
    )
    daten = fenster.diagramm.daten
    daten["conditions"] = [{"text": "Ampel an?", "values": ["J", "N", "*"]}]
    daten["actions"] = [{"text": "grün", "values": ["X", "", "X"]}]
    return fenster


def _waehlen(fenster: DiagrammFenster, teil: str, zeile: int, spalte: int) -> None:
    flaeche = fenster.zeichenflaeche
    flaeche.auswaehlen(
        next(
            z
            for z in zellen(flaeche.diagramm.daten, VERSATZ, VERSATZ)
            if (z.teil, z.zeile, z.spalte) == (teil, zeile, spalte)
        )
    )


def _bedingung(fenster: DiagrammFenster) -> list[str]:
    return fenster.diagramm.daten["conditions"][0]["values"]


def test_regel_entfernen_nimmt_die_ausgewaehlte(fenster: DiagrammFenster) -> None:
    _waehlen(fenster, "actions", 0, 1)

    fenster.aktionen["Tabelle/Regel entfernen"].trigger()

    assert _bedingung(fenster) == ["J", "*"]
    assert fenster.diagramm.daten["actions"][0]["values"] == ["X", "X"]

    fenster.zeichenflaeche.rueckgaengig()
    assert _bedingung(fenster) == ["J", "N", "*"]


def test_ohne_auswahl_bleibt_es_bei_der_letzten(fenster: DiagrammFenster) -> None:
    fenster.aktionen["Tabelle/Regel entfernen"].trigger()

    assert _bedingung(fenster) == ["J", "N"]


def test_neue_regel_kommt_hinter_die_ausgewaehlte(fenster: DiagrammFenster) -> None:
    _waehlen(fenster, "conditions", 0, 0)

    fenster.aktionen["Tabelle/Regel hinzufügen"].trigger()

    assert _bedingung(fenster) == ["J", "", "N", "*"]
    assert fenster.diagramm.daten["actions"][0]["values"] == ["X", "", "", "X"]


def test_ohne_auswahl_kommt_die_neue_regel_ans_ende(fenster: DiagrammFenster) -> None:
    fenster.aktionen["Tabelle/Regel hinzufügen"].trigger()

    assert _bedingung(fenster) == ["J", "N", "*", ""]


def test_zeilenbeschriftung_ist_keine_regel(fenster: DiagrammFenster) -> None:
    """Die Textspalte links gehört zu keiner Regel - dann gilt das
    Verhalten ohne Auswahl."""
    _waehlen(fenster, "conditions", 0, -1)

    assert fenster.zeichenflaeche.ausgewaehlte_regel() is None
    fenster.aktionen["Tabelle/Regel hinzufügen"].trigger()

    assert _bedingung(fenster) == ["J", "N", "*", ""]
