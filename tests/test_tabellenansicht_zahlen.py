"""Punkt 615: die Debugger-Tabellenansicht sortiert Zahlen nach ihrem
Wert, schreibt sie mit Dezimalkomma, begrenzt die Spaltenzahl und
hängt keine Rohantwort von 65 000 Zeichen an eine Meldung."""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt

from ide.debugger.tabellenansicht import (
    MAX_SPALTEN,
    TabellenFehler,
    tabelle_aus_antwort,
    tabelle_aus_wert,
)
from ide.viewers import TabellenAnsicht


def _spalte(fenster: TabellenAnsicht, nummer: int) -> list[str]:
    widget = fenster.tabelle_widget
    return [widget.item(zeile, nummer).text() for zeile in range(widget.rowCount())]


@pytest.mark.parametrize("richtung", [Qt.SortOrder.AscendingOrder, Qt.SortOrder.DescendingOrder])
def test_zahlen_werden_nach_ihrem_wert_sortiert(qtbot, richtung) -> None:  # noqa: ANN001
    werte = [10, 100, 2.25, 3.5, 9, 0, 1, 11]
    fenster = TabellenAnsicht("werte", tabelle_aus_wert(werte))
    qtbot.addWidget(fenster)

    fenster.tabelle_widget.sortItems(1, richtung)

    erwartet = sorted(werte, reverse=richtung == Qt.SortOrder.DescendingOrder)
    assert _spalte(fenster, 1) == [str(w).replace(".", ",") for w in erwartet]
    fenster.tabelle_widget.sortItems(0, Qt.SortOrder.AscendingOrder)
    assert _spalte(fenster, 0) == [str(n) for n in range(len(werte))]


def test_text_wird_deutsch_sortiert_und_steht_hinter_zahlen(qtbot) -> None:  # noqa: ANN001
    fenster = TabellenAnsicht("werte", tabelle_aus_wert(["Zebra", "äpfel", 3, "Birne"]))
    qtbot.addWidget(fenster)

    fenster.tabelle_widget.sortItems(1, Qt.SortOrder.AscendingOrder)

    assert _spalte(fenster, 1) == ["3", "äpfel", "Birne", "Zebra"]


def test_eine_sehr_breite_tabelle_wird_auf_die_ersten_spalten_begrenzt(qtbot) -> None:  # noqa: ANN001
    tabelle = tabelle_aus_wert([list(range(8000))])
    fenster = TabellenAnsicht("breit", tabelle)
    qtbot.addWidget(fenster)

    assert len(tabelle.spalten) == MAX_SPALTEN
    assert tabelle.spalten_gesamt == 8000
    assert "8000 Spalten" in fenster.beschreibung
    assert f"ersten {MAX_SPALTEN} Spalten" in fenster.beschreibung


def test_eine_gekuerzte_antwort_ergibt_eine_kurze_meldung() -> None:
    antwort = "'{\"spalten\": [" + "\"x\", " * 20000 + "'"

    with pytest.raises(TabellenFehler) as fehler:
        tabelle_aus_antwort(antwort)

    assert len(str(fehler.value)) < 200
    assert "zu groß" in str(fehler.value)
