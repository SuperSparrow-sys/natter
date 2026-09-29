"""ListBox mit Mehrfachauswahl und Sortierung, StringGrid mit
Spaltenköpfen, Spaltenbreiten und Schreibschutz (Punkt 97)."""

from __future__ import annotations

import json

import pytest
from PySide6.QtWidgets import QAbstractItemView

from ide.codegen.design import design_code_erzeugen
from ide.designer.pfm_schreiben import pfm_aus_formular
from pcl import Form, ListBox, StringGrid
from pcl.errors import NatterPropertyError, NatterZellenError

# -- ListBox --------------------------------------------------------------


def _liste(*eintraege: str) -> ListBox:
    liste = ListBox(Form())
    liste.items = list(eintraege)
    return liste


def test_ohne_multi_select_ist_hoechstens_einer_gewaehlt() -> None:
    liste = _liste("a", "b", "c")
    assert liste._qwidget.selectionMode() == QAbstractItemView.SelectionMode.SingleSelection
    liste.item_index = 1
    assert liste.selected == [1]
    with pytest.raises(NatterPropertyError, match="multi_select"):
        liste.selected = [0, 2]


def test_multi_select_waehlt_mehrere() -> None:
    liste = _liste("a", "b", "c", "d")
    liste.multi_select = True
    assert (
        liste._qwidget.selectionMode() == QAbstractItemView.SelectionMode.ExtendedSelection
    )
    liste.selected = [3, 0]
    assert liste.selected == [0, 3]
    liste.selected = []
    assert liste.selected == []


def test_selected_mit_einer_nummer_ausserhalb_meldet_sich() -> None:
    liste = _liste("a")
    with pytest.raises(NatterZellenError, match="Eintrag 5 gibt es nicht"):
        liste.selected = [5]


def test_sorted_ordnet_die_eintraege_und_haelt_sie_geordnet() -> None:
    liste = _liste("Birne", "apfel", "Zitrone")
    liste.sorted = True
    assert list(liste.items) == ["apfel", "Birne", "Zitrone"]
    liste.items.add("Mango")
    assert list(liste.items) == ["apfel", "Birne", "Mango", "Zitrone"]
    angezeigt = [liste._qwidget.item(i).text() for i in range(liste._qwidget.count())]
    assert angezeigt == list(liste.items)


def test_ohne_sorted_bleibt_die_reihenfolge() -> None:
    liste = _liste("b", "a")
    assert list(liste.items) == ["b", "a"]


# -- StringGrid -----------------------------------------------------------


def _kopf(tabelle: StringGrid, spalte: int) -> str:
    element = tabelle._qwidget.horizontalHeaderItem(spalte)
    return element.text() if element is not None else ""


def test_col_titles_beschriften_die_spaltenkoepfe() -> None:
    tabelle = StringGrid(Form())
    tabelle.col_count = 3
    tabelle.col_titles = ["Name", "Punkte"]
    assert [_kopf(tabelle, s) for s in range(3)] == ["Name", "Punkte", ""]

    tabelle.col_titles.clear()
    assert tabelle._qwidget.horizontalHeaderItem(0) is None


def test_col_titles_gelten_auch_fuer_spaeter_hinzukommende_spalten() -> None:
    tabelle = StringGrid(Form())
    tabelle.col_count = 1
    tabelle.col_titles = ["A", "B"]
    tabelle.col_count = 2
    assert _kopf(tabelle, 1) == "B"


def test_col_widths_setzt_die_breite_einer_spalte() -> None:
    tabelle = StringGrid(Form())
    tabelle.col_widths[1] = 140
    assert tabelle.col_widths[1] == 140
    assert tabelle._qwidget.columnWidth(1) == 140
    with pytest.raises(NatterZellenError, match="Spalte 9"):
        tabelle.col_widths[9] = 10


def test_default_col_width_gilt_fuer_alle_uebrigen() -> None:
    tabelle = StringGrid(Form())
    tabelle.default_col_width = 60
    assert tabelle._qwidget.columnWidth(0) == 60


def test_read_only_sperrt_die_zellen_fuer_den_benutzer() -> None:
    tabelle = StringGrid(Form())
    tabelle.read_only = True
    assert (
        tabelle._qwidget.editTriggers() == QAbstractItemView.EditTrigger.NoEditTriggers
    )
    tabelle.cells[0, 0] = "geht trotzdem"
    assert tabelle.cells[0, 0] == "geht trotzdem"
    tabelle.read_only = False
    assert tabelle._qwidget.editTriggers() != QAbstractItemView.EditTrigger.NoEditTriggers


def test_alles_geht_durch_pfm_und_erzeugten_code() -> None:
    class Formular(Form):
        def create_components(self) -> None:
            self.sg_punkte = StringGrid(self)
            self.sg_punkte.col_titles = ["Name", "Punkte"]
            self.sg_punkte.read_only = True
            self.lb_namen = ListBox(self)
            self.lb_namen.multi_select = True
            self.lb_namen.sorted = True

    pfm = pfm_aus_formular(Formular())
    code = design_code_erzeugen(json.loads(json.dumps(pfm)), "u_test.pfm")

    assert 'self.sg_punkte.col_titles = ["Name", "Punkte"]' in code
    assert "self.sg_punkte.read_only = True" in code
    assert "self.lb_namen.multi_select = True" in code
    assert "self.lb_namen.sorted = True" in code
