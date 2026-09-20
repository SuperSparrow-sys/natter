"""Tests für ide/designer/canvas.py: Größenanfasser zum Ziehen mit der
Maus (wie in Lazarus). Headless. Siehe docs/PLAN.md, „Zurückgestellt“ →
visueller Feinschliff.
"""

from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent

from ide.designer.canvas import DesignerCanvas
from pcl import Button, Form


class _Formular(Form):
    def create_components(self) -> None:
        self.b_ein = Button(self)
        self.b_ein.left = 100
        self.b_ein.top = 100
        self.b_ein.width = 80
        self.b_ein.height = 30


def _ziehen(canvas: DesignerCanvas, anfasser_name: str, dx: int, dy: int) -> None:
    widget = canvas.anfasser_widget(anfasser_name)
    start = widget.pos()
    global_start = QPointF(start.x() + 3, start.y() + 3)
    global_ende = QPointF(global_start.x() + dx, global_start.y() + dy)

    druck = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        QPointF(3, 3),
        global_start,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    bewegung = QMouseEvent(
        QEvent.Type.MouseMove,
        QPointF(3 + dx, 3 + dy),
        global_ende,
        Qt.MouseButton.NoButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    loslassen = QMouseEvent(
        QEvent.Type.MouseButtonRelease,
        QPointF(3 + dx, 3 + dy),
        global_ende,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )

    assert canvas.eventFilter(widget, druck) is True
    assert canvas.eventFilter(widget, bewegung) is True
    assert canvas.eventFilter(widget, loslassen) is True


def test_ausgewaehlte_komponente_zeigt_acht_anfasser_an_den_richtigen_stellen() -> None:
    formular = _Formular()
    canvas = DesignerCanvas(formular)

    canvas.klick_bei(105, 105)

    mitte_x = 100 + 80 // 2 - 3
    mitte_y = 100 + 30 // 2 - 3
    assert canvas.anfasser_widget("nw").pos().toTuple() == (100 - 3, 100 - 3)
    assert canvas.anfasser_widget("se").pos().toTuple() == (180 - 3, 130 - 3)
    assert canvas.anfasser_widget("n").pos().toTuple() == (mitte_x, 100 - 3)
    assert canvas.anfasser_widget("s").pos().toTuple() == (mitte_x, 130 - 3)
    assert canvas.anfasser_widget("w").pos().toTuple() == (100 - 3, mitte_y)
    assert canvas.anfasser_widget("e").pos().toTuple() == (180 - 3, mitte_y)
    for name in ("nw", "n", "ne", "e", "se", "s", "sw", "w"):
        assert not canvas.anfasser_widget(name).isHidden()


def test_das_formular_bekommt_drei_anfasser() -> None:
    """Bis September 2026 waren es **null**: wer das Formular anklickte,
    sah gar keine, und die Fenstergroesse liess sich nur ueber
    `width`/`height` im Objektinspektor aendern (Nutzer-Meldung: „der
    designer hat eine zu kleine flaeche, diese soll anpassbar sein ueber
    die ecken zum ziehen").

    Drei, nicht acht: im Designer sitzt das Formular fest in der linken
    oberen Ecke, und `left`/`top` gibt es an einem Formular gar nicht -
    ein Zug an „nw" muesste es verschieben."""
    formular = _Formular()
    canvas = DesignerCanvas(formular)
    canvas.klick_bei(105, 105)

    canvas.klick_bei(5, 5)  # Formular-Hintergrund

    sichtbar = {
        name
        for name in ("nw", "n", "ne", "e", "se", "s", "sw", "w")
        if not canvas.anfasser_widget(name).isHidden()
    }
    assert sichtbar == {"e", "s", "se"}


def test_die_anfasser_des_formulars_liegen_innen() -> None:
    """Ein Anfasser, der halb ueber den Rand hinausragt, laege
    ausserhalb des Formular-Widgets und waere unsichtbar."""
    formular = _Formular()
    canvas = DesignerCanvas(formular)

    canvas.klick_bei(5, 5)

    for name in ("e", "s", "se"):
        x, y = canvas.anfasser_widget(name).pos().toTuple()
        assert 0 <= x <= formular.width - 7
        assert 0 <= y <= formular.height - 7


def test_das_formular_laesst_sich_groesser_ziehen() -> None:
    formular = _Formular()
    canvas = DesignerCanvas(formular)
    canvas.klick_bei(5, 5)
    vorher = (formular.width, formular.height)

    _ziehen(canvas, "se", 120, 80)

    assert (formular.width, formular.height) == (vorher[0] + 120, vorher[1] + 80)


def test_ein_zusammengezogenes_formular_bleibt_anfassbar() -> None:
    """Bei einem Pixel laegen die drei Anfasser uebereinander in einem
    Punkt - das Formular waere nicht mehr aufzuziehen."""
    formular = _Formular()
    canvas = DesignerCanvas(formular)
    canvas.klick_bei(5, 5)

    _ziehen(canvas, "se", -10_000, -10_000)

    assert (formular.width, formular.height) == (16, 16)


def test_se_anfasser_aendert_nur_breite_und_hoehe() -> None:
    formular = _Formular()
    canvas = DesignerCanvas(formular)
    canvas.klick_bei(105, 105)

    _ziehen(canvas, "se", 10, 5)

    assert (formular.b_ein.left, formular.b_ein.top) == (100, 100)
    assert (formular.b_ein.width, formular.b_ein.height) == (90, 35)


def test_nw_anfasser_bewegt_position_und_aendert_groesse_gegenlaeufig() -> None:
    formular = _Formular()
    canvas = DesignerCanvas(formular)
    canvas.klick_bei(105, 105)

    _ziehen(canvas, "nw", -10, -5)

    assert (formular.b_ein.left, formular.b_ein.top) == (90, 95)
    assert (formular.b_ein.width, formular.b_ein.height) == (90, 35)


def test_n_anfasser_aendert_nur_hoehe_von_oben() -> None:
    formular = _Formular()
    canvas = DesignerCanvas(formular)
    canvas.klick_bei(105, 105)

    _ziehen(canvas, "n", 0, -10)

    assert formular.b_ein.left == 100
    assert (formular.b_ein.top, formular.b_ein.height) == (90, 40)


def test_anfasser_ziehen_ist_rueckgaengig_machbar() -> None:
    formular = _Formular()
    canvas = DesignerCanvas(formular)
    canvas.klick_bei(105, 105)

    _ziehen(canvas, "se", 10, 10)
    assert (formular.b_ein.width, formular.b_ein.height) == (90, 40)

    canvas.rueckgaengig()

    assert (formular.b_ein.width, formular.b_ein.height) == (80, 30)


def test_anfasser_verkleinern_wird_bei_1px_begrenzt() -> None:
    formular = _Formular()
    canvas = DesignerCanvas(formular)
    canvas.klick_bei(105, 105)

    _ziehen(canvas, "se", -1000, -1000)

    assert (formular.b_ein.width, formular.b_ein.height) == (1, 1)


def test_anfasser_folgen_der_komponente_bei_tastaturverschiebung() -> None:
    formular = _Formular()
    canvas = DesignerCanvas(formular)
    canvas.klick_bei(105, 105)

    canvas.verschieben(8, 0)

    assert canvas.anfasser_widget("nw").pos().toTuple() == (108 - 3, 100 - 3)
