"""Klappmenü-Kürzel an Komponenten, die ein Programm in einer Liste
hält (Punkt 653)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from pcl import Button, Form, PopupMenu


class _Spielfeld(Form):
    def create_components(self) -> None:
        self.pm = PopupMenu(self)
        self.pm.entries = [
            {"name": "mi_weg", "caption": "Löschen", "shortcut": "Strg+K",
             "on_click": "loeschen"},
        ]
        self.knoepfe = []
        for nummer in range(3):
            knopf = Button(self)
            knopf.left = 10 + 90 * nummer
            knopf.popup_menu = self.pm
            self.knoepfe.append(knopf)
        self.aufrufe: list[int] = []

    def loeschen(self, sender) -> None:  # noqa: ANN001
        self.aufrufe.append(self.knoepfe.index(sender.popup_component))


def test_klappmenue_kuerzel_an_knoepfen_in_einer_liste(qtbot) -> None:  # noqa: ANN001
    """Knöpfe, die das Programm nur in einer Liste hält, fand das
    Klappmenü nicht unter den Attributen des Formulars, und Strg+K tat
    nichts."""
    formular = _Spielfeld()
    formular.show()
    qtbot.waitExposed(formular._qwidget)
    formular._qwidget.activateWindow()
    qtbot.waitUntil(formular._qwidget.isActiveWindow, timeout=2000)

    for nummer in (1, 2):
        formular.knoepfe[nummer]._qwidget.setFocus()
        QTest.keyClick(
            formular.knoepfe[nummer]._qwidget, Qt.Key.Key_K,
            Qt.KeyboardModifier.ControlModifier,
        )

    assert formular.aufrufe == [1, 2]


def test_eine_aufgehobene_zuordnung_nimmt_das_kuerzel_weg(qtbot) -> None:  # noqa: ANN001
    formular = _Spielfeld()
    formular.show()
    qtbot.waitExposed(formular._qwidget)
    formular._qwidget.activateWindow()
    qtbot.waitUntil(formular._qwidget.isActiveWindow, timeout=2000)
    formular.knoepfe[0].popup_menu = None

    formular.knoepfe[0]._qwidget.setFocus()
    QTest.keyClick(
        formular.knoepfe[0]._qwidget, Qt.Key.Key_K, Qt.KeyboardModifier.ControlModifier
    )

    assert formular.aufrufe == []
