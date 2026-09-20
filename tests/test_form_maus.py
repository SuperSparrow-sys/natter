"""Das Formular kennt die Maus.

Punkt 14 der offenen Punkte. `Form` hatte genau ein Ereignis,
`on_create`. Wer ein Zeichenprogramm oder ein kleines Spiel bauen
wollte, brauchte den Ort des Klicks auf der Fläche und nicht auf
einem Knopf - und musste dafür ein `Panel` über das ganze Formular
legen und dessen Ereignisse benutzen. Das muss man wissen, und es
stand nirgends.

Die Ereignisse kommen einzeln dazu und nicht über einen Wechsel der
Basisklasse: `Control` bringt `left`, `top` und `parent` mit, und
nichts davon hat für ein Fenster dieselbe Bedeutung.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from pcl import Button, Form
from pcl.components.menus import MENUELEISTE_HOEHE, MainMenu
from pcl.control import EREIGNIS_PARAMETER
from pcl.properties import ereignisse

MAUS = ("on_mouse_down", "on_mouse_move", "on_mouse_up")


def _maus(typ, x: float, y: float) -> QMouseEvent:
    return QMouseEvent(
        typ,
        QPointF(x, y),
        QPointF(x, y),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )


class _Fenster(Form):
    def create_components(self) -> None:
        self.gemeldet: list[tuple] = []
        self.on_mouse_down = lambda s, x, y: self.gemeldet.append(("down", x, y))
        self.on_mouse_move = lambda s, x, y: self.gemeldet.append(("move", x, y))
        self.on_mouse_up = lambda s, x, y: self.gemeldet.append(("up", x, y))
        self.on_click = lambda s: self.gemeldet.append(("click",))
        self.on_double_click = lambda s: self.gemeldet.append(("doppel",))


def _senden(fenster: Form, typ, x: int, y: int) -> None:
    QApplication.sendEvent(fenster._qwidget, _maus(typ, x, y))


# ------------------------------------------ Die Ereignisse gibt es


def test_das_formular_hat_die_maus_ereignisse() -> None:
    vorhanden = set(ereignisse(Form))

    for name in (*MAUS, "on_click", "on_double_click"):
        assert name in vorhanden, name


def test_es_behaelt_dabei_on_create() -> None:
    assert "on_create" in ereignisse(Form)


def test_die_parameterliste_ist_dieselbe_wie_bei_einer_komponente() -> None:
    """Sonst legte der Generator für ein Formular eine Methode mit
    anderer Signatur an als für einen Knopf."""
    for name in MAUS:
        assert EREIGNIS_PARAMETER[name] == ("x", "y")


# ------------------------------------------ Und sie kommen auch an


def test_ein_druck_meldet_die_stelle(qtbot) -> None:
    fenster = _Fenster()
    qtbot.addWidget(fenster._qwidget)

    _senden(fenster, QEvent.Type.MouseButtonPress, 40, 25)

    assert fenster.gemeldet == [("down", 40, 25)]


def test_eine_bewegung_meldet_auch_ohne_gedrueckte_taste(qtbot) -> None:
    """Für eine Positionsanzeige ist genau das nötig. Ohne
    `setMouseTracking` liefert Qt die Bewegung nur beim Ziehen."""
    fenster = _Fenster()
    qtbot.addWidget(fenster._qwidget)

    assert fenster._qwidget.hasMouseTracking() is True

    _senden(fenster, QEvent.Type.MouseMove, 12, 34)

    assert ("move", 12, 34) in fenster.gemeldet


def test_ein_klick_wird_erst_beim_loslassen_gemeldet(qtbot) -> None:
    fenster = _Fenster()
    qtbot.addWidget(fenster._qwidget)

    _senden(fenster, QEvent.Type.MouseButtonPress, 10, 10)
    assert ("click",) not in fenster.gemeldet

    _senden(fenster, QEvent.Type.MouseButtonRelease, 10, 10)

    assert ("click",) in fenster.gemeldet


def test_ein_doppelklick_wird_gemeldet(qtbot) -> None:
    fenster = _Fenster()
    qtbot.addWidget(fenster._qwidget)

    _senden(fenster, QEvent.Type.MouseButtonDblClick, 10, 10)

    assert ("doppel",) in fenster.gemeldet


def test_ohne_handler_passiert_nichts(qtbot) -> None:
    """Ein Formular ohne zugewiesenes Ereignis darf nicht abstürzen."""
    fenster = Form()
    qtbot.addWidget(fenster._qwidget)

    _senden(fenster, QEvent.Type.MouseButtonPress, 5, 5)


# --------------------------- Die Koordinaten zählen ab dem Arbeitsbereich


class _MitMenue(_Fenster):
    def create_components(self) -> None:
        super().create_components()
        self.mm_haupt = MainMenu(self)
        self.mm_haupt.entries = [{"name": "mi_datei", "caption": "Datei"}]


def test_eine_menueleiste_verschiebt_die_koordinaten(qtbot) -> None:
    """`top = 0` ist in Natter der obere Rand unterhalb der Leiste,
    und jede platzierte Komponente wird um deren Höhe nach unten
    geschoben. Die Maus muss demselben Maß folgen, sonst zeichnet ein
    Programm um die Höhe der Menüleiste daneben."""
    fenster = _MitMenue()
    qtbot.addWidget(fenster._qwidget)
    fenster.show()

    _senden(fenster, QEvent.Type.MouseButtonPress, 40, 25 + MENUELEISTE_HOEHE)

    assert fenster.gemeldet == [("down", 40, 25)]


def test_ohne_menueleiste_wird_nichts_abgezogen(qtbot) -> None:
    fenster = _Fenster()
    qtbot.addWidget(fenster._qwidget)
    fenster.show()

    _senden(fenster, QEvent.Type.MouseButtonPress, 40, 25)

    assert fenster.gemeldet == [("down", 40, 25)]


# ---------------------------------- Ein Klick auf einen Knopf ist keiner


def test_ein_klick_auf_einen_knopf_meldet_nicht_das_formular(qtbot) -> None:
    """Sonst bekäme ein Zeichenprogramm bei jedem Knopfdruck einen
    Strich an der falschen Stelle."""

    class _MitKnopf(_Fenster):
        def create_components(self) -> None:
            super().create_components()
            self.b_ok = Button(self)
            self.b_ok.left = 10
            self.b_ok.top = 10

    fenster = _MitKnopf()
    qtbot.addWidget(fenster._qwidget)
    fenster.show()

    QApplication.sendEvent(
        fenster.b_ok._qwidget, _maus(QEvent.Type.MouseButtonPress, 5, 5)
    )

    assert ("down", 5, 5) not in fenster.gemeldet
