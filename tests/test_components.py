"""Tests für pcl/components/standard.py und additional.py: Button, Label,
Shape. Headless. Siehe docs/PLAN.md, M1 Schritt 3.
"""

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

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


def _maus_senden(widget, art: QEvent.Type) -> None:
    """Ein Mausereignis so zustellen, wie Qt es tut.

    **Nicht `widget.mousePressEvent(...)` direkt aufrufen**: seit M15
    hängt die Klickbehandlung an einem Ereignisfilter in `Control`, und
    einen Filter sieht nur, was durch `QApplication.sendEvent` läuft.
    Der direkte Methodenaufruf ging am Filter vorbei und meldete
    nichts."""
    ereignis = QMouseEvent(
        art,
        QPointF(5, 5),
        QPointF(5, 5),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(widget, ereignis)


def _klicken(widget) -> None:
    """Drücken und loslassen - `on_click` kommt beim Loslassen."""
    _maus_senden(widget, QEvent.Type.MouseButtonPress)
    _maus_senden(widget, QEvent.Type.MouseButtonRelease)


def test_label_klick_loest_on_click_mit_sender_aus() -> None:
    # Anklickbares Label wie in Lazarus (TLabel.OnClick), z. B. für
    # Cookie-Klicker-artige Übungen (tests/daten/lazarus/d_Cookie_klicker).
    formular = _Formular()
    empfangen = []
    formular.l_titel.on_click = lambda sender: empfangen.append(sender)

    _klicken(formular.l_titel._qwidget)

    assert empfangen == [formular.l_titel]


def test_label_ohne_handler_klickt_ohne_fehler() -> None:
    formular = _Formular()

    _klicken(formular.l_titel._qwidget)  # kein on_click gesetzt


def test_shape_standardwert() -> None:
    formular = _Formular()
    assert formular.s_rot.shape == "rectangle"
    assert formular.s_rot.brush.color == "#c0c0c0"


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
    # (tests/daten/lazarus/b_schneefigur/unit1.lfm).
    formular = _Formular()
    formular.s_rot.shape = "rounded_rectangle"
    assert formular.s_rot.shape == "rounded_rectangle"


# -- Rand/Füllung/Z-Ebene (Nutzer-Feedback September 2026, wie Lazarus) ----


def test_shape_pen_color_ist_unabhaengig_von_brush_color() -> None:
    formular = _Formular()
    assert formular.s_rot.pen_color == "#000000"

    formular.s_rot.pen_color = "#2962ff"
    formular.s_rot.brush.color = "#e53935"

    assert formular.s_rot.pen_color == "#2962ff"
    assert formular.s_rot.brush.color == "#e53935"


def test_shape_transparent_standardwert_ist_falsch() -> None:
    formular = _Formular()
    assert formular.s_rot.transparent is False


def test_shape_transparent_umschaltbar() -> None:
    formular = _Formular()
    formular.s_rot.transparent = True
    assert formular.s_rot.transparent is True


def test_control_nach_vorne_bringen_und_nach_hinten_schicken_ohne_fehler() -> None:
    # Reine Delegation an QWidget.raise_()/lower() (Z-Ebene wie Lazarus
    # BringToFront/SendToBack) - hier nur geprüft, dass beides ohne
    # Fehler funktioniert; die tatsächliche Stapelreihenfolge ist Qt-
    # intern und nicht sinnvoll headless abfragbar.
    formular = _Formular()
    formular.s_rot.nach_vorne_bringen()
    formular.s_rot.nach_hinten_schicken()
    formular.l_titel.nach_vorne_bringen()


def test_label_ist_standardmaessig_transparent_ohne_eigene_farbe() -> None:
    formular = _Formular()
    assert formular.l_titel.transparent is True
    assert formular.l_titel.color == ""


def test_label_farbe_wirkt_nur_wenn_nicht_transparent() -> None:
    formular = _Formular()
    formular.l_titel.color = "#ffeb3b"
    formular.l_titel.transparent = False
    assert "#ffeb3b" in formular.l_titel._qwidget.styleSheet()

    formular.l_titel.transparent = True
    assert formular.l_titel._qwidget.styleSheet() == ""


def test_tippfehler_auf_echten_komponenten_wird_gemeldet() -> None:
    formular = _Formular()
    with pytest.raises(NatterUnbekannteEigenschaftError):
        formular.b_ein.captoin = "x"
