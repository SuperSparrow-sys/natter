"""Werte, die `pcl` bis 0.4.3 still falsch las oder annahm
(Punkte 475 bis 480).

Jeder Fall lief ohne Meldung durch und lieferte etwas anderes als
gemeint: den letzten Eintrag statt keinem, eine Farbe, die nirgends
erschien, eine Zahl um den Faktor tausend daneben.
"""

from __future__ import annotations

import pytest

from pcl import ComboBox, Edit, Form, Label, ListBox, Memo, Panel, RadioGroup, Shape, zahl
from pcl.errors import NatterPropertyError, NatterZahlError

#: Siehe `tests/test_maus_ereignisse.py`.
_AM_LEBEN: list[object] = []


@pytest.fixture
def formular():
    f = Form()
    _AM_LEBEN.append(f)
    return f


def test_ohne_auswahl_gibt_es_keinen_eintrag(formular) -> None:
    """Punkt 475: `items[item_index]` ohne Auswahl gab den letzten
    Eintrag. In `Memo.lines` bleibt `lines[-1]` die letzte Zeile."""
    fehler = []
    for typ in (ListBox, ComboBox, RadioGroup):
        k = typ(formular)
        _AM_LEBEN.append(k)
        k.items = ["a", "b", "c"]
        k.item_index = -1
        try:
            gelesen = k.items[k.item_index]
        except IndexError as ausnahme:
            if "nichts ausgewählt" not in str(ausnahme):
                fehler.append(f"{typ.__name__}: {ausnahme}")
        else:
            fehler.append(f"{typ.__name__}: {gelesen!r}")
    assert not fehler
    memo = Memo(formular)
    memo.lines = ["x", "y"]
    assert memo.lines[-1] == "y"


def test_combobox_behaelt_keinen_ungueltigen_index(formular) -> None:
    """Punkt 476: -2 blieb stehen, `items[-2]` ergab „b“. Das geschah,
    wenn vorher schon nichts gewählt war: Qt meldet dann keinen
    Wechsel, über den der Wert zurückkäme."""
    cb = ComboBox(formular)
    _AM_LEBEN.append(cb)
    cb.items = ["a", "b", "c"]
    cb.item_index = 5

    cb.item_index = -2

    assert cb.item_index == -1


def test_eine_farbe_wird_geprueft(formular) -> None:
    """Punkt 477: „rot“ wurde überall außer bei `font.color` still
    angenommen und zeigte nichts."""
    ziele = [
        (Label(formular), "color"),
        (Edit(formular), "color"),
        (Panel(formular), "color"),
        (formular, "color"),
    ]
    form = Shape(formular)
    ziele.append((form.brush, "color"))
    _AM_LEBEN.extend(z for z, _ in ziele)
    angenommen = []
    for ziel, name in ziele:
        try:
            setattr(ziel, name, "rot")
        except NatterPropertyError as ausnahme:
            assert "#RRGGBB" in str(ausnahme)
        else:
            angenommen.append(type(ziel).__name__)
        setattr(ziel, name, "#ff0000")
    assert not angenommen


def test_eine_farbe_macht_ein_label_undurchsichtig(formular) -> None:
    """Punkt 478: ohne `transparent = False` zeigte `color` nichts."""
    label = Label(formular)
    _AM_LEBEN.append(label)

    label.color = "#ff0000"

    assert not label.transparent
    assert "background-color: #ff0000" in label._qwidget.styleSheet()
    label.transparent = True
    assert "background-color" not in label._qwidget.styleSheet()


def test_englische_schreibweise_ist_keine_zahl() -> None:
    """Punkt 479: „1,234.5“ ergab still 1,2345."""
    with pytest.raises(NatterZahlError, match="deutscher Schreibweise"):
        zahl("1,234.5")
    assert zahl("1.234,5") == 1234.5


def test_none_heisst_kein_wert(formular) -> None:
    """Punkt 480: „ein NoneType (NoneType)“."""
    label = Label(formular)
    _AM_LEBEN.append(label)

    with pytest.raises(NatterPropertyError) as info:
        label.caption = None

    assert "kein Wert (None)" in str(info.value)
    assert "ohne return" in str(info.value)
