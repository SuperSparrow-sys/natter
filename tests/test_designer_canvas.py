"""Tests für ide/designer/canvas.py: DesignerCanvas – Anzeige und
Auswahl. Headless. Siehe docs/arbeitspakete/M3.md, Schritt 3.
"""

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from ide.designer import DesignerCanvas
from pcl import Button, Form, Shape


class _Formular(Form):
    def create_components(self) -> None:
        self.b_ein = Button(self)
        self.b_ein.left = 10
        self.b_ein.top = 10
        self.b_ein.width = 80
        self.b_ein.height = 30

        self.s_rot = Shape(self)
        self.s_rot.left = 100
        self.s_rot.top = 100
        self.s_rot.width = 40
        self.s_rot.height = 40


def test_klick_bei_trifft_die_richtige_komponente() -> None:
    formular = _Formular()
    canvas = DesignerCanvas(formular)

    getroffen = canvas.klick_bei(20, 20)

    assert getroffen is formular.b_ein
    assert canvas.ausgewaehlte_komponente is formular.b_ein


def test_klick_auf_leeren_hintergrund_waehlt_das_formular_selbst() -> None:
    formular = _Formular()
    canvas = DesignerCanvas(formular)

    getroffen = canvas.klick_bei(250, 250)

    assert getroffen is formular


def test_auswahl_setzt_markierungseigenschaft_und_entfernt_die_alte() -> None:
    formular = _Formular()
    canvas = DesignerCanvas(formular)

    canvas.klick_bei(20, 20)
    assert formular.b_ein._qwidget.property("design_ausgewaehlt") is True

    canvas.klick_bei(110, 110)
    assert formular.s_rot._qwidget.property("design_ausgewaehlt") is True
    assert formular.b_ein._qwidget.property("design_ausgewaehlt") is False


def test_beobachter_wird_bei_auswahl_benachrichtigt() -> None:
    formular = _Formular()
    canvas = DesignerCanvas(formular)
    empfangen = []
    canvas.auswahl_beobachten(lambda komponente: empfangen.append(komponente))

    canvas.klick_bei(20, 20)

    assert empfangen == [formular.b_ein]


def test_echter_klick_auf_button_waehlt_aus_statt_on_click_auszuloesen() -> None:
    formular = _Formular()
    canvas = DesignerCanvas(formular)
    ausgeloest = []
    formular.b_ein.on_click = lambda sender: ausgeloest.append(sender)

    QTest.mouseClick(formular.b_ein._qwidget, Qt.MouseButton.LeftButton)

    assert canvas.ausgewaehlte_komponente is formular.b_ein
    assert ausgeloest == []  # der echte Klick wurde vom Designer abgefangen


def test_formular_theme_stylesheet_bleibt_beim_erzeugen_erhalten() -> None:
    formular = _Formular()
    formular.theme = "dark"
    urspruenglich = formular._qwidget.styleSheet()

    DesignerCanvas(formular)

    assert "#1e1e1e" in formular._qwidget.styleSheet()  # Theme-Farbe weiterhin da
    assert urspruenglich in formular._qwidget.styleSheet()
