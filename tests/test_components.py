"""Tests für pcl/components/standard.py und additional.py: Button, Label,
Shape. Headless. Siehe docs/PLAN.md, M1 Schritt 3.
"""

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent

from pcl import Button, Form, Label, Shape
from pcl.errors import NatterPropertyError, NatterUnbekannteEigenschaftError


class _Formular(Form):
    def create_components(self) -> None:
        self.b_ein = Button(self)
        self.l_titel = Label(self)
        self.s_rot = Shape(self)


def test_button_standardwert_und_qwidget_text() -> None:
    formular = _Formular()
    assert formular.b_ein.caption == "Button"
    assert formular.b_ein._qwidget.text() == "Button"


def test_button_caption_aenderung_wirkt_sofort() -> None:
    formular = _Formular()
    formular.b_ein.caption = "Einschalten"
    assert formular.b_ein._qwidget.text() == "Einschalten"


def test_button_klick_loest_on_click_mit_sender_aus() -> None:
    formular = _Formular()
    empfangen = []
    formular.b_ein.on_click = lambda sender: empfangen.append(sender)

    formular.b_ein._qwidget.click()

    assert empfangen == [formular.b_ein]


def test_button_ohne_handler_klickt_ohne_fehler() -> None:
    formular = _Formular()
    formular.b_ein._qwidget.click()  # kein on_click gesetzt, darf nicht knallen


def test_label_standardwert_und_aenderung() -> None:
    formular = _Formular()
    assert formular.l_titel.caption == "Label1"
    assert formular.l_titel._qwidget.text() == "Label1"

    formular.l_titel.caption = "Ampel Simulator"
    assert formular.l_titel._qwidget.text() == "Ampel Simulator"


def test_label_klick_loest_on_click_mit_sender_aus() -> None:
    # Anklickbares Label wie in Lazarus (TLabel.OnClick), z. B. für
    # Cookie-Klicker-artige Übungen (referenz/lazarus/d_Cookie_klicker).
    formular = _Formular()
    empfangen = []
    formular.l_titel.on_click = lambda sender: empfangen.append(sender)

    druck = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        QPointF(5, 5),
        QPointF(5, 5),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    formular.l_titel._qwidget.mousePressEvent(druck)

    assert empfangen == [formular.l_titel]


def test_label_ohne_handler_klickt_ohne_fehler() -> None:
    formular = _Formular()
    druck = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        QPointF(5, 5),
        QPointF(5, 5),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    formular.l_titel._qwidget.mousePressEvent(druck)  # kein on_click gesetzt


def test_shape_standardwert() -> None:
    formular = _Formular()
    assert formular.s_rot.shape == "rectangle"
    assert formular.s_rot.brush.color == "#000000"


def test_shape_brush_color_aenderung() -> None:
    formular = _Formular()
    formular.s_rot.brush.color = "#e53935"
    assert formular.s_rot.brush.color == "#e53935"


def test_shape_brush_color_lehnt_falschen_typ_ab() -> None:
    formular = _Formular()
    with pytest.raises(NatterPropertyError):
        formular.s_rot.brush.color = 5


def test_shape_shape_eigenschaft_aenderbar() -> None:
    formular = _Formular()
    formular.s_rot.shape = "circle"
    assert formular.s_rot.shape == "circle"


def test_shape_rounded_rectangle_ist_eine_gueltige_form() -> None:
    # Entspricht Lazarus TShape.Shape = stRoundSquare
    # (referenz/lazarus/b_schneefigur/unit1.lfm).
    formular = _Formular()
    formular.s_rot.shape = "rounded_rectangle"
    assert formular.s_rot.shape == "rounded_rectangle"


def test_tippfehler_auf_echten_komponenten_wird_gemeldet() -> None:
    formular = _Formular()
    with pytest.raises(NatterUnbekannteEigenschaftError):
        formular.b_ein.captoin = "x"
