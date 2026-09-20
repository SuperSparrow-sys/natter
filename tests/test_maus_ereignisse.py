"""Maus-Ereignisse an jeder sichtbaren Komponente (M15, Abschnitt 4).

Bis dahin war `on_click` nur am `Button` verdrahtet, weil nur er ein
eigenes Qt-Klicksignal hat. `Label` und `Image` hatten je eine eigene
QLabel-Unterklasse, die `mousePressEvent` abfing - zwei Nachbauten
derselben Sache. Für `Shape`, `Panel`, `StringGrid` oder die frisch
gebaute `PaintBox` gab es gar nichts, und ausgerechnet eine
Zeichenfläche konnte damit nicht das, wofür man sie im Unterricht
benutzt: mit der Maus malen.

Ausgelöst wird hier mit echten `QMouseEvent`s über
`QApplication.sendEvent` - denselben Weg nimmt ein echter Klick.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from pcl import (
    Button,
    CheckBox,
    Edit,
    Form,
    Image,
    Label,
    Memo,
    PaintBox,
    Panel,
    Shape,
    StringGrid,
    Timer,
)
from pcl.control import EREIGNIS_PARAMETER, MAUS_EREIGNISSE

#: Alle Komponenten hier bleiben am Leben, solange das Modul lebt -
#: siehe die Begründung in `tests/test_beispiele_bedienen.py`.
_AM_LEBEN: list[object] = []

SICHTBARE = (Button, Label, Edit, CheckBox, Memo, Shape, Panel, StringGrid, Image, PaintBox)


def _maus(widget, art: QEvent.Type, x: int = 5, y: int = 5) -> None:
    # Mit `globalPos` als zweitem Punkt: die kürzere Fassung ist in
    # Qt 6 abgekündigt und füllte den Testlauf mit Warnungen.
    ereignis = QMouseEvent(
        art,
        QPointF(x, y),
        QPointF(x, y),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(widget, ereignis)


def _klick(widget, x: int = 5, y: int = 5) -> None:
    """Drücken und loslassen - ein Klick besteht aus beidem."""
    _maus(widget, QEvent.Type.MouseButtonPress, x, y)
    _maus(widget, QEvent.Type.MouseButtonRelease, x, y)


@pytest.fixture
def formular():
    f = Form()
    _AM_LEBEN.append(f)
    return f


def _komponente(formular, typ):
    k = typ(formular)
    _AM_LEBEN.append(k)
    return k


# -- Jede sichtbare Komponente kann alles ------------------------------


@pytest.mark.parametrize("typ", SICHTBARE, ids=[t.__name__ for t in SICHTBARE])
def test_jede_sichtbare_komponente_kennt_alle_maus_ereignisse(typ) -> None:
    from pcl.properties import ereignisse

    vorhanden = ereignisse(typ)
    for name in MAUS_EREIGNISSE:
        assert name in vorhanden, f"{typ.__name__} fehlt {name}"


@pytest.mark.parametrize("typ", SICHTBARE, ids=[t.__name__ for t in SICHTBARE])
def test_ein_klick_loest_on_click_aus(formular, typ) -> None:
    komponente = _komponente(formular, typ)
    gerufen: list[object] = []
    komponente.on_click = lambda sender: gerufen.append(sender)

    _klick(komponente._qwidget)

    assert gerufen == [komponente]


@pytest.mark.parametrize("typ", SICHTBARE, ids=[t.__name__ for t in SICHTBARE])
def test_ein_klick_loest_on_click_genau_einmal_aus(formular, typ) -> None:
    """Der `Button` hat ein natives Qt-Klicksignal. Ohne
    `_klick_kommt_vom_widget` hätte sein `on_click` doppelt ausgelöst -
    und ein Spielstand wäre zweimal hochgezählt worden."""
    komponente = _komponente(formular, typ)
    rufe: list[int] = []
    komponente.on_click = lambda sender: rufe.append(1)

    _klick(komponente._qwidget)

    assert len(rufe) == 1


@pytest.mark.parametrize("typ", SICHTBARE, ids=[t.__name__ for t in SICHTBARE])
def test_die_maus_meldet_ihre_koordinaten(formular, typ) -> None:
    komponente = _komponente(formular, typ)
    stellen: list[tuple[str, int, int]] = []
    komponente.on_mouse_down = lambda s, x, y: stellen.append(("down", x, y))
    komponente.on_mouse_move = lambda s, x, y: stellen.append(("move", x, y))
    komponente.on_mouse_up = lambda s, x, y: stellen.append(("up", x, y))

    _maus(komponente._qwidget, QEvent.Type.MouseButtonPress, 12, 7)
    _maus(komponente._qwidget, QEvent.Type.MouseMove, 30, 21)
    _maus(komponente._qwidget, QEvent.Type.MouseButtonRelease, 30, 21)

    assert stellen == [("down", 12, 7), ("move", 30, 21), ("up", 30, 21)]


@pytest.mark.parametrize("typ", SICHTBARE, ids=[t.__name__ for t in SICHTBARE])
def test_doppelklick_loest_on_double_click_aus(formular, typ) -> None:
    komponente = _komponente(formular, typ)
    gerufen: list[object] = []
    komponente.on_double_click = lambda sender: gerufen.append(sender)

    _maus(komponente._qwidget, QEvent.Type.MouseButtonDblClick)

    assert gerufen == [komponente]


# -- Feinheiten ---------------------------------------------------------


def test_ohne_zugewiesenen_handler_passiert_nichts(formular) -> None:
    """Eine Komponente ohne Ereignis-Methode darf beim Klicken nicht
    stolpern - das ist der Normalfall."""
    shape = _komponente(formular, Shape)

    _klick(shape._qwidget)
    _maus(shape._qwidget, QEvent.Type.MouseButtonDblClick)


def test_wer_danebenzieht_hat_nicht_geklickt(formular) -> None:
    """`on_click` kommt erst beim Loslassen, und nur wenn vorher auf
    derselben Komponente gedrückt wurde. Genauso verhält sich ein
    echter Knopf."""
    label = _komponente(formular, Label)
    rufe: list[int] = []
    label.on_click = lambda sender: rufe.append(1)

    _maus(label._qwidget, QEvent.Type.MouseButtonRelease)

    assert rufe == []


def test_das_ereignis_laeuft_danach_normal_weiter(formular) -> None:
    """Der Filter gibt `False` zurück. Täte er das nicht, könnte man in
    ein `Edit` nicht mehr hineinklicken."""
    feld = _komponente(formular, Edit)
    feld.on_click = lambda sender: None

    _klick(feld._qwidget, 3, 3)

    assert feld._qwidget.isEnabled()


def test_eine_unsichtbare_komponente_bekommt_keinen_filter(formular) -> None:
    """Ein Zeitgeber ist im laufenden Programm nicht da - eine Maus kann
    ihn nicht treffen."""
    zeitgeber = _komponente(formular, Timer)

    assert not hasattr(zeitgeber, "_maus_filter")


def test_die_koordinaten_zaehlen_ab_der_linken_oberen_ecke(formular) -> None:
    """Wie in Lazarus: (0, 0) ist die Ecke der Komponente, nicht die des
    Fensters."""
    box = _komponente(formular, PaintBox)
    box.left, box.top = 100, 60
    stellen: list[tuple[int, int]] = []
    box.on_mouse_down = lambda s, x, y: stellen.append((x, y))

    _maus(box._qwidget, QEvent.Type.MouseButtonPress, 0, 0)

    assert stellen == [(0, 0)]


# -- Damit lässt sich endlich malen -------------------------------------


def test_mit_der_maus_ziehen_malt_eine_linie(formular) -> None:
    """Der Grund für das ganze Paket: eine Zeichenfläche, auf der man
    mit der Maus malen kann."""
    box = _komponente(formular, PaintBox)
    box.width, box.height = 200, 120
    box.on_mouse_down = lambda s, x, y: (
        setattr(box, "_malt", True),
        box.canvas.pen.__setattr__("color", "#c42b1c"),
        box.canvas.move_to(x, y),
    )
    box.on_mouse_move = lambda s, x, y: (
        box.canvas.line_to(x, y) if getattr(box, "_malt", False) else None
    )
    box.on_mouse_up = lambda s, x, y: setattr(box, "_malt", False)

    _maus(box._qwidget, QEvent.Type.MouseButtonPress, 20, 60)
    _maus(box._qwidget, QEvent.Type.MouseMove, 180, 60)
    _maus(box._qwidget, QEvent.Type.MouseButtonRelease, 180, 60)

    assert box.canvas.pixels[100, 60] == "#c42b1c"
    assert box.canvas.pixels[100, 20] == "#ffffff"


def test_nach_dem_loslassen_wird_nicht_weitergemalt(formular) -> None:
    box = _komponente(formular, PaintBox)
    box.width, box.height = 200, 120
    box.on_mouse_down = lambda s, x, y: (
        setattr(box, "_malt", True),
        box.canvas.pen.__setattr__("color", "#c42b1c"),
        box.canvas.move_to(x, y),
    )
    box.on_mouse_move = lambda s, x, y: (
        box.canvas.line_to(x, y) if getattr(box, "_malt", False) else None
    )
    box.on_mouse_up = lambda s, x, y: setattr(box, "_malt", False)

    _maus(box._qwidget, QEvent.Type.MouseButtonPress, 20, 30)
    _maus(box._qwidget, QEvent.Type.MouseButtonRelease, 20, 30)
    _maus(box._qwidget, QEvent.Type.MouseMove, 180, 100)

    assert box.canvas.pixels[100, 65] == "#ffffff"


# -- Der Ereignis-Generator kennt die Koordinaten -----------------------


def test_die_maus_ereignisse_bringen_x_und_y_mit() -> None:
    assert EREIGNIS_PARAMETER["on_mouse_down"] == ("x", "y")
    assert EREIGNIS_PARAMETER["on_mouse_move"] == ("x", "y")
    assert EREIGNIS_PARAMETER["on_mouse_up"] == ("x", "y")


def test_on_click_bleibt_bei_sender_allein() -> None:
    """Wie `OnClick(Sender)` in Lazarus - wer wissen will, wo
    geklickt wurde, nimmt `on_mouse_down`."""
    assert "on_click" not in EREIGNIS_PARAMETER
    assert "on_double_click" not in EREIGNIS_PARAMETER


def test_der_generator_schreibt_die_koordinaten_in_die_methode() -> None:
    from ide.codegen.ereignis import handler_methode_einfuegen

    quelltext = "class Form1:\n    pass\n"

    ergebnis = handler_methode_einfuegen(
        quelltext, "Form1", "pb_bild_mouse_down", ("x", "y")
    )

    assert "def pb_bild_mouse_down(self, sender, x, y):" in ergebnis


def test_der_generator_bleibt_sonst_bei_self_und_sender() -> None:
    from ide.codegen.ereignis import handler_methode_einfuegen

    ergebnis = handler_methode_einfuegen("class Form1:\n    pass\n", "Form1", "b_ok_click")

    assert "def b_ok_click(self, sender):" in ergebnis
