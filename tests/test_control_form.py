"""Tests für pcl/control.py, pcl/form.py, pcl/application.py: Qt-Anbindung,
headless. Siehe PLAN.md (Git-Historie), M1 Schritt 2.
"""

import pytest
from PySide6.QtWidgets import QWidget

from pcl.application import Application
from pcl.control import Control
from pcl.errors import NatterUnbekannteEigenschaftError
from pcl.form import Form


class Feld(Control):
    """Minimale Test-Komponente: ein nacktes QWidget als Platzhalter."""

    def _qwidget_erzeugen(self, eltern_widget):
        return QWidget(eltern_widget)


class LeeresFormular(Form):
    pass


class FormularMitFeld(Form):
    def create_components(self):
        self.caption = "Testformular"
        self.feld = Feld(self)
        self.feld.left = 10
        self.feld.top = 20
        self.feld.width = 100
        self.feld.height = 40


def test_form_uebernimmt_standard_props_ins_qwidget() -> None:
    formular = LeeresFormular()
    assert formular._qwidget.windowTitle() == "Form1"
    assert formular._qwidget.width() == 480
    assert formular._qwidget.height() == 360


def test_form_caption_aenderung_wirkt_sofort() -> None:
    formular = LeeresFormular()
    formular.caption = "Neuer Titel"
    assert formular._qwidget.windowTitle() == "Neuer Titel"


def test_form_close_schliesst_das_qwidget() -> None:
    formular = LeeresFormular()
    formular.show()
    assert formular._qwidget.isVisible() is True
    formular.close()
    assert formular._qwidget.isVisible() is False


def test_create_components_wird_beim_erzeugen_aufgerufen() -> None:
    formular = FormularMitFeld()
    assert formular._qwidget.windowTitle() == "Testformular"
    geometrie = formular.feld._qwidget.geometry()
    assert (geometrie.x(), geometrie.y(), geometrie.width(), geometrie.height()) == (
        10,
        20,
        100,
        40,
    )


def test_control_geometrie_aenderung_wirkt_sofort() -> None:
    formular = FormularMitFeld()
    formular.feld.left = 55
    assert formular.feld._qwidget.geometry().x() == 55


def test_control_enabled_aenderung_wirkt_sofort() -> None:
    formular = FormularMitFeld()
    assert formular.feld._qwidget.isEnabled() is True
    formular.feld.enabled = False
    assert formular.feld._qwidget.isEnabled() is False


def test_on_create_wird_vor_erster_anzeige_ausgeloest() -> None:
    ausgeloest = []

    class FormularMitEreignis(Form):
        def create_components(self) -> None:
            self.on_create = self._erstellt

        def _erstellt(self, sender) -> None:
            ausgeloest.append(sender)

    formular = FormularMitEreignis()
    assert ausgeloest == [formular]


def test_eigene_attribute_auf_formular_bleiben_erlaubt() -> None:
    formular = FormularMitFeld()
    formular.ampel = "irgendein eigenes Objekt"
    assert formular.ampel == "irgendein eigenes Objekt"


def test_unbekannte_eigenschaft_auf_control_wird_gemeldet() -> None:
    formular = FormularMitFeld()
    with pytest.raises(NatterUnbekannteEigenschaftError):
        formular.feld.captoin = "x"


def test_application_erzeugt_nur_eine_qapplication_instanz() -> None:
    app1 = Application()
    app2 = Application()
    assert app1._qapp is app2._qapp
