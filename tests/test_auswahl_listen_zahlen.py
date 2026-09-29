"""Gewählte Zelle im StringGrid, Listenbefehle an `items`/`lines`,
deutsches FloatSpinEdit und `text()` ohne Exponentenschreibweise
(Punkte 190 bis 193)."""

from __future__ import annotations

import pytest
from PySide6.QtCore import QLocale

from pcl import FloatSpinEdit, Form, ListBox, Memo, StringGrid, text
from pcl.errors import NatterPropertyError

# -- 190: StringGrid.col / row ---------------------------------------------


def test_stringgrid_row_waehlt_eine_zeile() -> None:
    sg = StringGrid(Form())
    assert (sg.col, sg.row) == (-1, -1)
    gemeldet: list[tuple[int, int]] = []
    sg.on_select_cell = lambda sender, spalte, zeile: gemeldet.append(
        (spalte, zeile)
    )
    sg.row = 2
    assert sg._qwidget.currentRow() == 2
    assert (sg.col, sg.row) == (0, 2)
    sg.col = 3
    assert sg._qwidget.currentColumn() == 3
    assert (sg.col, sg.row) == (3, 2)
    assert gemeldet[-1] == (3, 2)


def test_stringgrid_minus_eins_hebt_die_auswahl_auf() -> None:
    sg = StringGrid(Form())
    sg.row = 1
    sg.row = -1
    assert (sg.col, sg.row) == (-1, -1)
    sg.col = 2
    sg.col = -1
    assert (sg.col, sg.row) == (-1, -1)


def test_stringgrid_row_ausserhalb_meldet_sich_deutsch() -> None:
    sg = StringGrid(Form())
    with pytest.raises(NatterPropertyError, match="von -1 bis 4"):
        sg.row = 5
    with pytest.raises(NatterPropertyError, match="erhalten wurde ein Text"):
        sg.col = "1"


# -- 191: Listenbefehle an items / lines -----------------------------------


def _angezeigt(komponente: ListBox | Memo) -> list[str]:
    widget = komponente._qwidget
    if isinstance(komponente, Memo):
        return widget.toPlainText().split("\n")
    return [widget.item(i).text() for i in range(widget.count())]


def _sammlung(komponente: ListBox | Memo):
    return komponente.lines if isinstance(komponente, Memo) else komponente.items


@pytest.mark.parametrize("art", [ListBox, Memo])
def test_items_und_lines_kennen_die_listenbefehle(art: type) -> None:
    komponente = art(Form())
    zeilen = _sammlung(komponente)
    zeilen.zuweisen(["b", "c", "a", "c"])

    zeilen.insert(0, "x")
    assert list(zeilen) == ["x", "b", "c", "a", "c"]
    assert zeilen.index("c") == 2
    assert zeilen.count("c") == 2
    zeilen.remove("c")
    assert list(zeilen) == ["x", "b", "a", "c"]
    assert zeilen.pop() == "c"
    assert zeilen.pop(0) == "x"
    assert list(zeilen) == ["b", "a"]
    zeilen.sort()
    assert list(zeilen) == ["a", "b"]
    zeilen.sort(reverse=True)
    assert list(zeilen) == ["b", "a"]
    assert _angezeigt(komponente) == ["b", "a"]

    with pytest.raises(NatterPropertyError):
        zeilen.insert(0, 5)
    with pytest.raises(ValueError, match="steht nicht in der Liste"):
        zeilen.remove("fehlt")
    with pytest.raises(ValueError, match="steht nicht in der Liste"):
        zeilen.index("fehlt")
    with pytest.raises(IndexError, match="gibt es nicht"):
        zeilen.pop(7)
    assert list(zeilen) == ["b", "a"]


# -- 192: FloatSpinEdit immer deutsch --------------------------------------


def test_floatspinedit_zeigt_unter_englischer_sprache_ein_komma() -> None:
    vorher = QLocale()
    QLocale.setDefault(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
    try:
        feld = FloatSpinEdit(Form())
        feld.value = 2.5
        assert feld._qwidget.text() == "2,50"
        feld._qwidget.lineEdit().setText("3,25")
        feld._qwidget.interpretText()
        assert feld.value == 3.25
    finally:
        QLocale.setDefault(vorher)


# -- 193: text() ohne Exponentenschreibweise --------------------------------


@pytest.mark.parametrize(
    ("wert", "erwartet"),
    [
        (0.00001, "0,00001"),
        (-0.000123, "-0,000123"),
        (1e16, "10000000000000000"),
        (1e20, "100000000000000000000"),
        (1e-10, "0,0000000001"),
        (0.1 + 0.2, "0,3"),
        # Die Grenze: ab 10^21 und unter 10^-10 als Zehnerpotenz.
        (1e21, "1 · 10^21"),
        (2.5e21, "2,5 · 10^21"),
        (-2.5e-11, "-2,5 · 10^-11"),
    ],
)
def test_text_ohne_exponentenschreibweise(wert: float, erwartet: str) -> None:
    assert text(wert) == erwartet
