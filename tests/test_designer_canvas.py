"""Tests für ide/designer/canvas.py: DesignerCanvas – Anzeige und
Auswahl. Headless. Siehe docs/arbeitspakete/M3.md, Schritt 3.
"""

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from ide.designer import DesignerCanvas
from pcl import Button, Form, Label, Shape


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

        # Ein `Label` zeigt als Einziges, ob der Auswahlrahmen die
        # Komponente selbst verändert: mit Rahmenbreite rückt QLabel
        # seinen Text ein.
        self.l_titel = Label(self)
        self.l_titel.left = 200
        self.l_titel.top = 0
        self.l_titel.width = 90
        self.l_titel.height = 25


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


def _rahmen_rechteck(canvas: DesignerCanvas) -> tuple[int, int, int, int]:
    """Das von den vier Rahmenstreifen umschlossene Rechteck."""
    kanten = [kante.geometry() for kante in canvas._rahmen_kanten]
    links = min(k.left() for k in kanten)
    oben = min(k.top() for k in kanten)
    rechts = max(k.right() for k in kanten)
    unten = max(k.bottom() for k in kanten)
    return links, oben, rechts - links + 1, unten - oben + 1


def test_der_auswahlrahmen_wandert_zur_neu_gewaehlten_komponente() -> None:
    """Der Rahmen besteht aus vier Streifen über dem Formular, nicht
    mehr aus einer QSS-Regel: ein Stylesheet an der Komponente selbst
    hätte ihre Maße verändert und den Designer vom laufenden Programm
    entfernt (M11, Abschnitt 3)."""
    formular = _Formular()
    canvas = DesignerCanvas(formular)

    canvas.klick_bei(20, 20)
    assert _rahmen_rechteck(canvas) == (10 - 2, 10 - 2, 80 + 4, 30 + 4)

    canvas.klick_bei(110, 110)
    assert _rahmen_rechteck(canvas) == (100 - 2, 100 - 2, 40 + 4, 40 + 4)


def test_der_auswahlrahmen_veraendert_die_komponente_nicht() -> None:
    """Genau das war der Fehler: die QSS-Regel gab jeder Komponente mit
    eigenem Stylesheet dauerhaft 2 px Rahmenbreite mit - ein `Label`
    rückte seinen Text im Designer um 5 px nach rechts, im Programm
    nicht."""
    im_programm = _Formular()
    im_programm.l_titel.font.bold = True

    im_designer = _Formular()
    canvas = DesignerCanvas(im_designer)
    canvas.klick_bei(210, 10)
    im_designer.l_titel.font.bold = True
    canvas.klick_bei(250, 250)  # wieder abwählen

    assert (
        im_designer.l_titel._qwidget.grab().toImage()
        == im_programm.l_titel._qwidget.grab().toImage()
    )


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
