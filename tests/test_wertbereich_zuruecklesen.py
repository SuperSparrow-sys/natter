"""Ein Minimum über dem Maximum: Eigenschaften und Widget sagen danach
dasselbe (Punkt 131)."""

import pytest

from pcl import Form, ProgressBar, ScrollBar, SpinEdit, TrackBar


@pytest.mark.parametrize("klasse", [SpinEdit, TrackBar, ScrollBar, ProgressBar])
def test_minimum_ueber_maximum_zieht_die_eigenschaft_maximum_mit(klasse) -> None:
    formular = Form()
    komponente = klasse(formular)
    komponente.maximum = 100
    komponente.minimum = 200
    assert komponente.maximum == komponente._qwidget.maximum() == 200
    assert komponente.minimum == komponente._qwidget.minimum() == 200


@pytest.mark.parametrize("klasse", [SpinEdit, TrackBar, ScrollBar, ProgressBar])
def test_maximum_unter_minimum_zieht_die_eigenschaft_minimum_mit(klasse) -> None:
    formular = Form()
    komponente = klasse(formular)
    komponente.minimum = 0
    komponente.maximum = -5
    # Welche Grenze Qt nachzieht, ist je Widget verschieden; die
    # Eigenschaften müssen nur dasselbe sagen wie das Widget.
    assert komponente.minimum == komponente._qwidget.minimum()
    assert komponente.maximum == komponente._qwidget.maximum()
    assert komponente.minimum <= komponente.maximum


def test_progressbar_behaelt_ihre_position_bei_gueltigem_bereich() -> None:
    formular = Form()
    balken = ProgressBar(formular)
    balken.position = 40
    balken.maximum = 50
    assert balken.position == 40
    assert balken._qwidget.value() == 40
