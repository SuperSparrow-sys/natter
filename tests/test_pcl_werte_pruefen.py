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


@pytest.mark.parametrize(
    "weg",
    [
        lambda lb: lb.items.__delitem__(lb.item_index),
        lambda lb: lb.items.__setitem__(lb.item_index, "X"),
        lambda lb: lb.items.pop(lb.item_index),
    ],
    ids=["del", "zuweisen", "pop"],
)
def test_ohne_auswahl_wird_auch_nichts_geaendert(formular, weg) -> None:
    """Punkt 571: Löschen, Überschreiben und `pop` über `item_index`
    trafen ohne Auswahl still den letzten Eintrag."""
    lb = ListBox(formular)
    _AM_LEBEN.append(lb)
    lb.items = ["a", "b", "c"]
    lb.item_index = -1

    with pytest.raises(IndexError, match="nichts ausgewählt"):
        weg(lb)
    assert list(lb.items) == ["a", "b", "c"]
    with pytest.raises(IndexError, match="Einen Eintrag 10 gibt es nicht"):
        del lb.items[10]


def test_radiogroup_meldet_auswahl_aus_dem_code(formular) -> None:
    """Punkt 583: `item_index = 1` und kürzere `items` lösten kein
    `on_change` aus, nur ein Klick."""
    rg = RadioGroup(formular)
    _AM_LEBEN.append(rg)
    gemeldet: list[int] = []
    rg.on_change = lambda sender: gemeldet.append(sender.item_index)
    rg.items = ["a", "b", "c"]

    rg.item_index = 1
    rg.items = ["a"]

    assert gemeldet == [1, -1]


@pytest.mark.parametrize("typ", [ComboBox, ListBox])
def test_kuerzere_items_heben_die_auswahl_auf(formular, typ) -> None:
    """Punkt 584: die ComboBox sprang auf Eintrag 0, die ListBox auf -1."""
    k = typ(formular)
    _AM_LEBEN.append(k)
    k.items = ["a", "b", "c"]
    k.item_index = 2

    k.items = ["a"]

    assert k.item_index == -1


def test_ein_leeres_maskedit_liefert_leeren_text(formular) -> None:
    """Punkt 592: mit der Maske 00.00.0000 lieferte ein leeres Feld „..“."""
    from pcl import MaskEdit

    me = MaskEdit(formular)
    _AM_LEBEN.append(me)
    me.mask = "00.00.0000"

    assert me.text == ""
    me.text = "20.09.2026"
    assert me.text == "20.09.2026"
    me.text = ""
    assert me.text == ""


def test_maske_mit_festem_text_wie_in_der_referenz(formular) -> None:
    """Punkt 618: „Datum: 00.00.0000“ zerstückelte das Wort, weil `D`
    und `a` Maskenzeichen sind. Mit Rückstrich, wie in der Referenz,
    steht es fest da."""
    from pcl import MaskEdit

    me = MaskEdit(formular)
    _AM_LEBEN.append(me)
    me.mask = r"\D\atum: 00.00.0000"
    me.text = "20092026"

    assert me._qwidget.displayText() == "Datum: 20.09.2026"
    assert me.text == "Datum: 20.09.2026"


def test_maskedit_meldet_nur_echte_aenderungen(formular) -> None:
    """Punkt 621: on_change kam auch bei abgelehnten Zeichen und bei der
    Rücktaste über leere Stellen."""
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    from pcl import MaskEdit

    me = MaskEdit(formular)
    _AM_LEBEN.append(me)
    me.mask = "00000"
    gemeldet: list[str] = []
    me.on_change = lambda sender: gemeldet.append(sender.text)

    QTest.keyClicks(me._qwidget, "x")
    QTest.keyClick(me._qwidget, Qt.Key.Key_Backspace)
    QTest.keyClicks(me._qwidget, "1")

    assert gemeldet == ["1"]


def test_radiogroup_meldet_eine_andere_option_unter_derselben_nummer(formular) -> None:
    """Punkt 621: `items.insert(0, …)` ließ die gewählte Option
    nachrücken, ohne `on_change`."""
    rg = RadioGroup(formular)
    _AM_LEBEN.append(rg)
    rg.items = ["a", "b"]
    rg.item_index = 0
    gemeldet: list[str] = []
    rg.on_change = lambda sender: gemeldet.append(sender.items[sender.item_index])

    rg.items.insert(0, "neu")

    assert gemeldet == ["neu"]
