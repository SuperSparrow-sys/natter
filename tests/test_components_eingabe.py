"""Tests für pcl/components/standard.py: Edit, CheckBox, RadioButton,
ScrollBar. Headless. Siehe PLAN.md (Git-Historie), M1 Schritt 6.
"""

from pcl import CheckBox, Edit, Form, RadioButton, ScrollBar


class _Formular(Form):
    def create_components(self) -> None:
        self.e_zahl1 = Edit(self)
        self.c_kaese = CheckBox(self)
        self.rb_small = RadioButton(self)
        self.sb_behinderung = ScrollBar(self)


def test_edit_standardwert_ist_leer() -> None:
    formular = _Formular()
    assert formular.e_zahl1.text == ""
    assert formular.e_zahl1._qwidget.text() == ""


def test_edit_zuweisung_aendert_qwidget() -> None:
    formular = _Formular()
    formular.e_zahl1.text = "42"
    assert formular.e_zahl1._qwidget.text() == "42"


def test_edit_eingabe_ueber_qwidget_aktualisiert_text_prop() -> None:
    formular = _Formular()
    formular.e_zahl1._qwidget.setText("3,5")
    assert formular.e_zahl1.text == "3,5"


def test_edit_on_change_wird_bei_eingabe_ausgeloest() -> None:
    formular = _Formular()
    empfangen = []
    formular.e_zahl1.on_change = lambda sender: empfangen.append(sender.text)

    formular.e_zahl1._qwidget.setText("7")

    assert empfangen == ["7"]


def test_edit_read_only_standardwert_ist_false() -> None:
    formular = _Formular()
    assert formular.e_zahl1.read_only is False
    assert formular.e_zahl1._qwidget.isReadOnly() is False


def test_edit_read_only_wirkt_sofort_auf_qwidget() -> None:
    # Entspricht Lazarus TEdit.ReadOnly = True (tests/daten/lfm/f_Pizza).
    formular = _Formular()
    formular.e_zahl1.read_only = True
    assert formular.e_zahl1._qwidget.isReadOnly() is True


def test_edit_color_setzt_hintergrundfarbe() -> None:
    # Entspricht Lazarus TEdit.Color = clYellow
    # (tests/daten/lfm/a_GUI_Komponenten).
    formular = _Formular()
    formular.e_zahl1.color = "#ffff00"
    assert "background-color: #ffff00" in formular.e_zahl1._qwidget.styleSheet()


def test_edit_color_leer_entfernt_das_lokale_stylesheet() -> None:
    formular = _Formular()
    formular.e_zahl1.color = "#ffff00"
    formular.e_zahl1.color = ""
    assert formular.e_zahl1._qwidget.styleSheet() == ""


def test_checkbox_standardwert() -> None:
    formular = _Formular()
    assert formular.c_kaese.caption == "CheckBox1"
    assert formular.c_kaese.checked is False
    assert formular.c_kaese._qwidget.isChecked() is False


def test_checkbox_checked_zuweisung_wirkt_sofort() -> None:
    formular = _Formular()
    formular.c_kaese.checked = True
    assert formular.c_kaese._qwidget.isChecked() is True


def test_checkbox_klick_aktualisiert_checked_und_loest_on_change_aus() -> None:
    formular = _Formular()
    empfangen = []
    formular.c_kaese.on_change = lambda sender: empfangen.append(sender.checked)

    formular.c_kaese._qwidget.click()

    assert formular.c_kaese.checked is True
    assert empfangen == [True]


def test_radiobutton_standardwert() -> None:
    formular = _Formular()
    assert formular.rb_small.caption == "RadioButton1"
    assert formular.rb_small.checked is False


def test_radiobutton_checked_zuweisung_wirkt_sofort() -> None:
    formular = _Formular()
    formular.rb_small.checked = True
    assert formular.rb_small._qwidget.isChecked() is True


def test_scrollbar_standardwerte() -> None:
    formular = _Formular()
    assert (formular.sb_behinderung.minimum, formular.sb_behinderung.maximum) == (0, 100)
    assert formular.sb_behinderung.position == 0


def test_scrollbar_min_max_position_wie_in_f_pizza() -> None:
    formular = _Formular()
    formular.sb_behinderung.minimum = 5
    formular.sb_behinderung.maximum = 50
    formular.sb_behinderung.position = 5

    assert formular.sb_behinderung._qwidget.minimum() == 5
    assert formular.sb_behinderung._qwidget.maximum() == 50
    assert formular.sb_behinderung._qwidget.value() == 5


def test_scrollbar_bewegen_aktualisiert_position_und_loest_on_change_aus() -> None:
    formular = _Formular()
    formular.sb_behinderung.maximum = 50
    empfangen = []
    formular.sb_behinderung.on_change = lambda sender: empfangen.append(sender.position)

    formular.sb_behinderung._qwidget.setValue(20)

    assert formular.sb_behinderung.position == 20
    assert empfangen == [20]
