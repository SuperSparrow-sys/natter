"""`set_focus()` und `hint` an jeder Komponente (Punkt 96)."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from ide.palette.palette import ALLE_KOMPONENTEN
from pcl import Button, Edit, Form, Timer
from pcl.properties import eigenschaften

_OFFEN: list[Form] = []

SICHTBARE = [typ for typ in ALLE_KOMPONENTEN if not typ.nur_im_designer]


@pytest.mark.parametrize("klasse", SICHTBARE, ids=lambda k: k.__name__)
def test_jede_sichtbare_komponente_hat_hint(klasse) -> None:
    komponente = klasse(Form())
    komponente.hint = "Hier die Zahl eintragen"
    assert komponente._qwidget.toolTip() == "Hier die Zahl eintragen"
    assert "hint" in eigenschaften(klasse)


def test_ein_zeitgeber_zeigt_keinen_hint_im_objektinspektor() -> None:
    assert "hint" not in eigenschaften(Timer)


def test_set_focus_setzt_den_cursor_ins_feld(qtbot) -> None:
    formular = Form()
    _OFFEN.append(formular)
    knopf = Button(formular)
    feld = Edit(formular)
    feld.top = 40
    formular.show()
    qtbot.waitExposed(formular._qwidget)
    formular._qwidget.activateWindow()
    knopf._qwidget.setFocus()
    qtbot.waitUntil(lambda: QApplication.focusWidget() is knopf._qwidget, timeout=2000)

    feld.set_focus()

    qtbot.waitUntil(lambda: QApplication.focusWidget() is feld._qwidget, timeout=2000)
    assert feld._qwidget.hasFocus()
