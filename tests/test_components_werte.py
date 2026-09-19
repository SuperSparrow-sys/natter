"""Tests für die Wertkomponenten aus `pcl/components/additional.py`:
SpinEdit, FloatSpinEdit, TrackBar, ProgressBar. Headless.

Geprüft wird für jede Eigenschaft, dass sie wirklich auf dem Qt-Widget
ankommt (nicht nur im `Prop` steht), und für jedes Ereignis, dass es
feuert - in beide Richtungen, also auch bei Bedienung über das Widget.
"""

from PySide6.QtWidgets import QSlider

from pcl import FloatSpinEdit, Form, ProgressBar, SpinEdit, TrackBar


class _Formular(Form):
    def create_components(self) -> None:
        self.se_anzahl = SpinEdit(self)
        self.fse_preis = FloatSpinEdit(self)
        self.tb_regler = TrackBar(self)
        self.pb_fortschritt = ProgressBar(self)


# -- SpinEdit ----------------------------------------------------------


def test_spinedit_standardwerte_stehen_auch_im_widget() -> None:
    formular = _Formular()
    feld = formular.se_anzahl

    assert (feld.minimum, feld.maximum, feld.value, feld.increment) == (0, 100, 0, 1)
    assert feld._qwidget.minimum() == 0
    assert feld._qwidget.maximum() == 100
    assert feld._qwidget.value() == 0
    assert feld._qwidget.singleStep() == 1


def test_spinedit_jede_eigenschaft_wirkt_auf_das_widget() -> None:
    formular = _Formular()
    feld = formular.se_anzahl

    feld.minimum = 5
    feld.maximum = 50
    feld.increment = 5
    feld.value = 20

    assert feld._qwidget.minimum() == 5
    assert feld._qwidget.maximum() == 50
    assert feld._qwidget.singleStep() == 5
    assert feld._qwidget.value() == 20


def test_spinedit_eingabe_am_widget_landet_in_value() -> None:
    formular = _Formular()
    formular.se_anzahl._qwidget.setValue(42)

    assert formular.se_anzahl.value == 42


def test_spinedit_on_change_feuert_mit_dem_neuen_wert() -> None:
    formular = _Formular()
    empfangen: list[int] = []
    formular.se_anzahl.on_change = lambda sender: empfangen.append(sender.value)

    formular.se_anzahl.value = 12

    assert empfangen == [12]


def test_spinedit_zu_grosser_wert_wird_gekappt_und_steht_gekappt_im_prop() -> None:
    """Qt kappt an `maximum`. Ohne den Abgleich in `_prop_gleichziehen`
    stünde danach im `Prop` eine Zahl, die das Widget gar nicht anzeigt -
    `value` und Anzeige liefen auseinander."""
    formular = _Formular()
    feld = formular.se_anzahl
    feld.maximum = 10

    feld.value = 500

    assert feld._qwidget.value() == 10
    assert feld.value == 10


def test_spinedit_kleineres_maximum_zieht_den_wert_mit() -> None:
    formular = _Formular()
    feld = formular.se_anzahl
    feld.value = 80

    feld.maximum = 20

    assert feld._qwidget.value() == 20
    assert feld.value == 20


# -- FloatSpinEdit -----------------------------------------------------


def test_floatspinedit_standardwerte_stehen_auch_im_widget() -> None:
    formular = _Formular()
    feld = formular.fse_preis

    assert (feld.minimum, feld.maximum, feld.value, feld.increment) == (0.0, 100.0, 0.0, 1.0)
    assert feld.decimals == 2
    assert feld._qwidget.decimals() == 2


def test_floatspinedit_jede_eigenschaft_wirkt_auf_das_widget() -> None:
    formular = _Formular()
    feld = formular.fse_preis

    feld.minimum = 0.5
    feld.maximum = 9.5
    feld.increment = 0.25
    feld.value = 3.75

    assert feld._qwidget.minimum() == 0.5
    assert feld._qwidget.maximum() == 9.5
    assert feld._qwidget.singleStep() == 0.25
    assert feld._qwidget.value() == 3.75


def test_floatspinedit_decimals_rundet_den_wert_wirklich() -> None:
    formular = _Formular()
    feld = formular.fse_preis
    feld.decimals = 1

    feld.value = 2.25

    assert feld._qwidget.value() == 2.3
    assert feld.value == 2.3


def test_floatspinedit_ganze_zahl_wird_zu_float() -> None:
    """`Prop` lässt ein `int` für eine `float`-Eigenschaft durch
    (`_passt_typ`). Gelesen werden soll trotzdem immer ein `float`,
    sonst hinge der Typ davon ab, wie zugewiesen wurde."""
    formular = _Formular()
    feld = formular.fse_preis

    feld.value = 3

    assert isinstance(feld.value, float)
    assert feld.value == 3.0


def test_floatspinedit_on_change_feuert_bei_eingabe_am_widget() -> None:
    formular = _Formular()
    empfangen: list[float] = []
    formular.fse_preis.on_change = lambda sender: empfangen.append(sender.value)

    formular.fse_preis._qwidget.setValue(4.5)

    assert empfangen == [4.5]


# -- TrackBar ----------------------------------------------------------


def test_trackbar_standardwerte_entsprechen_lazarus() -> None:
    # TTrackBar: Min=0, Max=10, Position=0, Frequency=1.
    formular = _Formular()
    regler = formular.tb_regler

    assert (regler.minimum, regler.maximum, regler.position, regler.frequency) == (0, 10, 0, 1)
    assert regler._qwidget.maximum() == 10


def test_trackbar_bringt_eine_brauchbare_standardgroesse_mit() -> None:
    # Als Prop-Standard und nicht über _STANDARDGROESSEN des Designers,
    # damit erzeugter Code dieselbe Größe bekommt wie eine platzierte
    # Komponente.
    formular = _Formular()

    assert (formular.tb_regler.width, formular.tb_regler.height) == (150, 30)
    assert formular.tb_regler._qwidget.width() == 150


def test_trackbar_jede_eigenschaft_wirkt_auf_das_widget() -> None:
    formular = _Formular()
    regler = formular.tb_regler

    regler.minimum = 2
    regler.maximum = 20
    regler.position = 15
    regler.frequency = 5

    assert regler._qwidget.minimum() == 2
    assert regler._qwidget.maximum() == 20
    assert regler._qwidget.value() == 15
    assert regler._qwidget.tickInterval() == 5
    assert regler._qwidget.tickPosition() == QSlider.TickPosition.TicksBelow


def test_trackbar_frequency_null_schaltet_die_teilstriche_ab() -> None:
    formular = _Formular()
    formular.tb_regler.frequency = 0

    assert formular.tb_regler._qwidget.tickPosition() == QSlider.TickPosition.NoTicks


def test_trackbar_ziehen_am_widget_landet_in_position() -> None:
    formular = _Formular()
    formular.tb_regler._qwidget.setValue(4)

    assert formular.tb_regler.position == 4


def test_trackbar_on_change_feuert() -> None:
    formular = _Formular()
    empfangen: list[int] = []
    formular.tb_regler.on_change = lambda sender: empfangen.append(sender.position)

    formular.tb_regler.position = 8

    assert empfangen == [8]


# -- ProgressBar -------------------------------------------------------


def test_progressbar_standardwerte_stehen_auch_im_widget() -> None:
    formular = _Formular()
    balken = formular.pb_fortschritt

    assert (balken.minimum, balken.maximum, balken.position) == (0, 100, 0)
    assert balken.show_text is True
    assert balken._qwidget.isTextVisible() is True
    assert (balken.width, balken.height) == (150, 22)


def test_progressbar_jede_eigenschaft_wirkt_auf_das_widget() -> None:
    formular = _Formular()
    balken = formular.pb_fortschritt

    balken.minimum = 10
    balken.maximum = 60
    balken.position = 30
    balken.show_text = False

    assert balken._qwidget.minimum() == 10
    assert balken._qwidget.maximum() == 60
    assert balken._qwidget.value() == 30
    assert balken._qwidget.isTextVisible() is False


def test_progressbar_zu_grosser_wert_wird_gekappt() -> None:
    formular = _Formular()
    balken = formular.pb_fortschritt

    balken.position = 300

    assert balken._qwidget.value() == 100
    assert balken.position == 100
