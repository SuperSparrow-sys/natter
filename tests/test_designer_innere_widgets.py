"""Klicks in das Innere einer Komponente (Punkt 50 der offenen Punkte).

Ein StringGrid besteht aus mehreren Widgets; ein Klick in die Zellen
landet im Viewport der Tabelle. Der Designer beobachtete nur das äußere
Widget: mit gewählter Kachel legte ein Klick in das Grid nichts an, und
der Platzierungsmodus blieb still aktiv.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest

from ide.designer.canvas import DesignerCanvas
from pcl import Chart, Form, StringGrid


class _Formular(Form):
    def create_components(self) -> None:
        self.stringgrid = StringGrid(self)
        self.stringgrid.left = 20
        self.stringgrid.top = 30


def _canvas(qtbot) -> tuple[_Formular, DesignerCanvas]:  # noqa: ANN001
    formular = _Formular()
    qtbot.addWidget(formular._qwidget)
    formular._qwidget.resize(480, 360)
    formular._qwidget.show()
    return formular, DesignerCanvas(formular)


def _komponenten(formular: Form) -> list:
    return [w for w in vars(formular).values() if hasattr(w, "_qwidget")]


def test_platzieren_per_klick_in_ein_stringgrid(qtbot) -> None:  # noqa: ANN001
    formular, canvas = _canvas(qtbot)
    vorher = len(_komponenten(formular))
    canvas.platzierungsmodus_setzen(Chart)

    QTest.mouseClick(
        formular.stringgrid._qwidget.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(40, 40)
    )

    assert len(_komponenten(formular)) == vorher + 1
    assert canvas._platzierungs_typ is None
    neu = [k for k in _komponenten(formular) if isinstance(k, Chart)][0]
    # Die Stelle wird in Formularkoordinaten umgerechnet
    assert neu.left > formular.stringgrid.left
    assert neu.top > formular.stringgrid.top


def test_klick_in_die_zellen_waehlt_das_stringgrid(qtbot) -> None:  # noqa: ANN001
    formular, canvas = _canvas(qtbot)

    QTest.mouseClick(
        formular.stringgrid._qwidget.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(40, 40)
    )

    assert canvas.ausgewaehlte_komponente is formular.stringgrid


def test_auch_ein_neu_platziertes_grid_nimmt_klicks_an(qtbot) -> None:  # noqa: ANN001
    """Der Weg einer Schülerin: das Grid entsteht erst im Designer."""
    formular, canvas = _canvas(qtbot)
    grid = canvas.komponente_platzieren(StringGrid, 20, 200)
    canvas.platzierungsmodus_setzen(Chart)

    QTest.mouseClick(grid._qwidget.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(30, 30))

    assert any(isinstance(k, Chart) for k in _komponenten(formular))
