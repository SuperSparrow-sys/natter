"""Edit mit Passwort, Maximallänge und Nur-Zahlen; Standardknopf
(Punkt 95)."""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLineEdit

from pcl import Button, Edit, Form, Memo

_OFFEN: list[Form] = []


class _Anmeldung(Form):
    def create_components(self) -> None:
        self.e_name = Edit(self)
        self.e_passwort = Edit(self)
        self.m_notiz = Memo(self)
        self.b_ok = Button(self)
        self.b_ok.default = True
        self.b_ok.on_click = self.b_ok_click
        self.b_anders = Button(self)
        self.b_anders.on_click = self.b_anders_click
        self.geklickt: list[str] = []

    def b_ok_click(self, sender) -> None:
        self.geklickt.append("ok")

    def b_anders_click(self, sender) -> None:
        self.geklickt.append("anders")


@pytest.fixture
def anmeldung(qtbot) -> _Anmeldung:
    formular = _Anmeldung()
    _OFFEN.append(formular)
    formular.show()
    qtbot.waitExposed(formular._qwidget)
    return formular


def test_password_verbirgt_die_zeichen() -> None:
    feld = Edit(Form())
    feld.password = True
    assert feld._qwidget.echoMode() == QLineEdit.EchoMode.Password
    feld.password = False
    assert feld._qwidget.echoMode() == QLineEdit.EchoMode.Normal


def test_max_length_begrenzt_das_eintippen(qtbot) -> None:
    feld = Edit(Form())
    feld.max_length = 3
    qtbot.keyClicks(feld._qwidget, "abcdef")
    assert feld.text == "abc"
    feld.max_length = 0
    assert feld._qwidget.maxLength() == 32767


def test_numbers_only_laesst_nur_zahlen_durch(qtbot) -> None:
    feld = Edit(Form())
    feld.numbers_only = True
    qtbot.keyClicks(feld._qwidget, "-1a2,5x,7")
    assert feld.text == "-12,57"


def test_ohne_numbers_only_geht_alles(qtbot) -> None:
    feld = Edit(Form())
    feld.numbers_only = True
    feld.numbers_only = False
    qtbot.keyClicks(feld._qwidget, "abc")
    assert feld.text == "abc"


def test_eingabe_im_edit_klickt_den_standardknopf(anmeldung, qtbot) -> None:
    anmeldung.e_name._qwidget.setFocus()
    qtbot.keyClick(anmeldung.e_name._qwidget, Qt.Key.Key_Return)
    assert anmeldung.geklickt == ["ok"]


def test_eingabe_im_memo_beginnt_eine_neue_zeile(anmeldung, qtbot) -> None:
    anmeldung.m_notiz._qwidget.setFocus()
    qtbot.keyClick(anmeldung.m_notiz._qwidget, Qt.Key.Key_Return)
    assert anmeldung.geklickt == []


def test_eingabe_auf_einem_anderen_knopf_klickt_diesen(anmeldung, qtbot) -> None:
    anmeldung.b_anders._qwidget.setFocus()
    qtbot.keyClick(anmeldung.b_anders._qwidget, Qt.Key.Key_Return)
    assert anmeldung.geklickt == ["anders"]


def test_ein_gesperrter_standardknopf_bleibt_stumm(anmeldung, qtbot) -> None:
    anmeldung.b_ok.enabled = False
    anmeldung.e_name._qwidget.setFocus()
    qtbot.keyClick(anmeldung.e_name._qwidget, Qt.Key.Key_Return)
    assert anmeldung.geklickt == []


def test_default_zeigt_den_rahmen_des_standardknopfs() -> None:
    knopf = Button(Form())
    knopf.default = True
    assert knopf._qwidget.isDefault()
