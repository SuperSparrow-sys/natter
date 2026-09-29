"""Maus und Tasten an den inneren Widgets einer Komponente (Punkte
146, 162 und 163).

Bei Listen, Textfeldern und Tabellen kommt die Maus am Anzeigebereich
im Inneren an, bei Spinboxen und Datumsfeldern am Eingabefeld darin,
bei einer RadioGroup an der Option. Hing der Filter nur am äußeren
Widget, kam dort kein Klick an, und nach einem Klick auf eine Option
hörte das Formular keine Taste mehr.

Geklickt wird hier auf das Widget, das tatsächlich unter der Mitte
liegt, mit Ereignissen über `QApplication.sendEvent`. Dieser Weg
reicht ein nicht angenommenes Ereignis an die Eltern weiter wie ein
echter Klick.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QApplication, QWidget

import pcl
from pcl import Form, Label, ListBox, RadioGroup, SpinEdit

#: Alle Komponenten hier bleiben am Leben, solange das Modul lebt -
#: siehe die Begründung in `tests/test_beispiele_bedienen.py`.
_AM_LEBEN: list[object] = []

SICHTBARE = [
    getattr(pcl, name)
    for name in pcl.__all__
    if isinstance(getattr(pcl, name), type)
    and issubclass(getattr(pcl, name), pcl.Control)
    and getattr(pcl, name) is not pcl.Control
    and not getattr(pcl, name).nur_im_designer
]


def _maus(
    widget: QWidget,
    art: QEvent.Type,
    stelle: QPoint,
    taste: Qt.MouseButton = Qt.MouseButton.LeftButton,
) -> None:
    ereignis = QMouseEvent(
        art,
        QPointF(stelle),
        QPointF(widget.mapToGlobal(stelle)),
        taste,
        taste if art != QEvent.Type.MouseButtonRelease else Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(widget, ereignis)


def _unter_der_mitte(aussen: QWidget) -> tuple[QWidget, QPoint]:
    mitte = aussen.rect().center()
    innen = aussen.childAt(mitte) or aussen
    return innen, innen.mapFrom(aussen, mitte)


def _aufklapper_schliessen() -> None:
    while (offen := QApplication.activePopupWidget()) is not None:
        offen.close()


@pytest.fixture
def formular():
    f = Form()
    f.width, f.height = 600, 500
    _AM_LEBEN.append(f)
    return f


@pytest.mark.parametrize("typ", SICHTBARE, ids=lambda t: t.__name__)
def test_klick_auf_das_widget_unter_der_mitte_ist_on_click(formular, typ) -> None:
    k = typ(formular)
    _AM_LEBEN.append(k)
    k.left, k.top, k.width, k.height = 10, 10, 280, 200
    if isinstance(k, RadioGroup):
        k.items = ["eins", "zwei", "drei", "vier", "fünf", "sechs"]
    formular._qwidget.show()
    QApplication.processEvents()
    gemeldet: list[str] = []
    k.on_mouse_down = lambda s, x, y: gemeldet.append("d")
    k.on_click = lambda s: gemeldet.append("c")
    innen, stelle = _unter_der_mitte(k._qwidget)
    _maus(innen, QEvent.Type.MouseButtonPress, stelle)
    _aufklapper_schliessen()
    _maus(innen, QEvent.Type.MouseButtonRelease, stelle)
    _aufklapper_schliessen()
    formular._qwidget.hide()
    if typ is pcl.Button:
        # Der Knopf meldet den Klick über sein eigenes Signal.
        assert "c" in gemeldet
    else:
        assert gemeldet == ["d", "c"]


def test_doppelklick_auf_einen_listeneintrag(formular) -> None:
    lb = ListBox(formular)
    _AM_LEBEN.append(lb)
    lb.items = ["rot", "grün"]
    lb.width, lb.height = 200, 150
    gemeldet: list[str] = []
    lb.on_double_click = lambda s: gemeldet.append("dd")
    innen = lb._qwidget.viewport()
    _maus(innen, QEvent.Type.MouseButtonDblClick, QPoint(10, 5))
    assert gemeldet == ["dd"]


def test_koordinaten_zaehlen_ab_der_komponente(formular) -> None:
    sp = SpinEdit(formular)
    _AM_LEBEN.append(sp)
    sp.width, sp.height = 120, 30
    stellen: list[tuple[int, int]] = []
    sp.on_mouse_down = lambda s, x, y: stellen.append((x, y))
    innen = sp._qwidget.lineEdit()
    _maus(innen, QEvent.Type.MouseButtonPress, QPoint(4, 4))
    erwartet = innen.mapTo(sp._qwidget, QPoint(4, 4))
    assert stellen == [(erwartet.x(), erwartet.y())]


def test_ein_klick_innen_wird_nur_einmal_gemeldet(formular) -> None:
    lb = ListBox(formular)
    _AM_LEBEN.append(lb)
    lb.width, lb.height = 200, 150
    gemeldet: list[str] = []
    lb.on_mouse_down = lambda s, x, y: gemeldet.append("d")
    lb.on_mouse_up = lambda s, x, y: gemeldet.append("u")
    lb.on_click = lambda s: gemeldet.append("c")
    innen = lb._qwidget.viewport()
    # Unterhalb der Einträge nimmt die Liste den Klick nicht an, und
    # Qt reicht ihn an das äußere Widget weiter.
    _maus(innen, QEvent.Type.MouseButtonPress, QPoint(50, 100))
    _maus(innen, QEvent.Type.MouseButtonRelease, QPoint(50, 100))
    assert gemeldet == ["d", "u", "c"]


# -- Punkt 162: rechte Taste und Loslassen daneben ----------------------


def test_rechtsklick_ist_kein_on_click(formular) -> None:
    lb = Label(formular)
    _AM_LEBEN.append(lb)
    gemeldet: list[str] = []
    lb.on_click = lambda s: gemeldet.append("label click")
    rechts = Qt.MouseButton.RightButton
    _maus(lb._qwidget, QEvent.Type.MouseButtonPress, QPoint(5, 5), rechts)
    _maus(lb._qwidget, QEvent.Type.MouseButtonRelease, QPoint(5, 5), rechts)
    _aufklapper_schliessen()
    assert gemeldet == []


def test_daneben_losgelassen_ist_kein_on_click(formular) -> None:
    lb = Label(formular)
    _AM_LEBEN.append(lb)
    gemeldet: list[str] = []
    lb.on_click = lambda s: gemeldet.append("label click")
    _maus(lb._qwidget, QEvent.Type.MouseButtonPress, QPoint(5, 5))
    _maus(lb._qwidget, QEvent.Type.MouseButtonRelease, QPoint(400, 300))
    assert gemeldet == []
    # Auf der Komponente losgelassen bleibt es ein Klick.
    _maus(lb._qwidget, QEvent.Type.MouseButtonPress, QPoint(5, 5))
    _maus(lb._qwidget, QEvent.Type.MouseButtonRelease, QPoint(6, 6))
    assert gemeldet == ["label click"]


# -- Punkt 163: Tasten nach einem Klick in eine RadioGroup -------------


def test_nach_klick_auf_eine_option_hoert_das_formular_tasten(formular) -> None:
    rg = RadioGroup(formular)
    _AM_LEBEN.append(rg)
    rg.width, rg.height = 200, 120
    rg.items = ["leicht", "schwer"]
    formular._qwidget.show()
    QApplication.processEvents()
    tasten: list[tuple[str, str]] = []
    formular.on_key_press = lambda s, taste: tasten.append(("form", taste))
    rg.on_key_press = lambda s, taste: tasten.append(("rg", taste))
    option = rg._optionen[1]
    mitte = option.rect().center()
    _maus(option, QEvent.Type.MouseButtonPress, mitte)
    _maus(option, QEvent.Type.MouseButtonRelease, mitte)
    option.setFocus()
    QApplication.processEvents()
    assert rg.item_index == 1
    ereignis = QKeyEvent(
        QEvent.Type.KeyPress, Qt.Key.Key_A, Qt.KeyboardModifier.NoModifier, "a"
    )
    QApplication.sendEvent(option, ereignis)
    formular._qwidget.hide()
    assert tasten == [("form", "A"), ("rg", "A")]
