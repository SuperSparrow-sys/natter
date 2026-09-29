"""Namen für Bildschirmleser und Tastaturfokus im Designer (Punkt 44
und ein Teil von Punkt 45 der offenen Punkte).

Die Kacheln der Komponentenpalette und die Symbole von Menü und
Zeitgeber zeigen nur ein Bild. Bis 0.3.3 meldete UI Automation sie
ohne Namen oder gar nicht, und nach einem Klick auf das Menüsymbol
ging F2 ins Leere.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAccessible
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from ide.designer.canvas import DesignerCanvas
from ide.palette.palette import TYP_ROLLE, Komponentenpalette
from pcl import Form, MainMenu, Timer


class _Formular(Form):
    def create_components(self) -> None:
        self.mm_haupt = MainMenu(self)
        self.mm_haupt.entries = [{"name": "mi_datei", "caption": "&Datei"}]
        self.t_uhr = Timer(self)
        self.t_uhr.left = 60


def test_jede_palettenkachel_hat_einen_namen(qtbot) -> None:  # noqa: ANN001
    palette = Komponentenpalette()
    qtbot.addWidget(palette)
    palette.show()

    for liste in palette.listen:
        schnittstelle = QAccessible.queryAccessibleInterface(liste)
        namen = []
        for zeile in range(liste.count()):
            typ = liste.item(zeile).data(TYP_ROLLE)
            kind = _kind_mit_namen(schnittstelle, typ.__name__)
            assert kind is not None, typ.__name__
            namen.append(typ.__name__)
        assert namen


def _kind_mit_namen(schnittstelle, name: str):  # noqa: ANN001, ANN202
    """Sucht in der Barrierefreiheits-Schnittstelle einer Liste den
    Eintrag mit diesem Namen, so wie ein Bildschirmleser ihn liest."""
    offen = [schnittstelle]
    while offen:
        knoten = offen.pop()
        if knoten is None:
            continue
        if knoten.text(QAccessible.Text.Name) == name:
            return knoten
        offen.extend(knoten.child(i) for i in range(knoten.childCount()))
    return None


def _canvas(qtbot) -> tuple[_Formular, DesignerCanvas]:  # noqa: ANN001
    formular = _Formular()
    qtbot.addWidget(formular._qwidget)
    canvas = DesignerCanvas(formular)
    formular._qwidget.show()
    formular._qwidget.activateWindow()
    qtbot.waitUntil(formular._qwidget.isActiveWindow, timeout=2000)
    return formular, canvas


def test_symbole_nicht_sichtbarer_komponenten_haben_einen_namen(qtbot) -> None:  # noqa: ANN001
    formular, _canvas_ = _canvas(qtbot)

    assert formular.mm_haupt._qwidget.accessibleName() == "MainMenu"
    assert formular.t_uhr._qwidget.accessibleName() == "Timer"


def test_f2_nach_klick_auf_das_menuesymbol_oeffnet_den_editor(
    qtbot, monkeypatch  # noqa: ANN001
) -> None:
    formular, canvas = _canvas(qtbot)
    geoeffnet = []
    monkeypatch.setattr(
        canvas, "menue_bearbeiten", lambda k: geoeffnet.append(k) or True
    )
    symbol = formular.mm_haupt._qwidget

    QTest.mouseClick(symbol, Qt.MouseButton.LeftButton)
    assert QApplication.focusWidget() is symbol
    QTest.keyClick(QApplication.focusWidget(), Qt.Key.Key_F2)

    assert geoeffnet == [formular.mm_haupt]
