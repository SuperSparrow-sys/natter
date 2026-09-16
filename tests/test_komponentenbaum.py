"""Tests für ide/inspector/komponentenbaum.py: Komponentenbaum. Headless.
Siehe docs/arbeitspakete/M3.md, Schritt 2.
"""

from ide.inspector.komponentenbaum import KOMPONENTE_ROLLE, Komponentenbaum
from pcl import Button, Form, Shape


class _Formular(Form):
    def create_components(self) -> None:
        self.b_ein = Button(self)
        self.s_rot = Shape(self)


def test_wurzel_ist_das_formular() -> None:
    formular = _Formular()
    baum = Komponentenbaum()

    baum.formular_anzeigen(formular)

    assert baum.topLevelItemCount() == 1
    wurzel = baum.topLevelItem(0)
    assert wurzel.text(0) == "_Formular: Form"
    assert wurzel.data(0, KOMPONENTE_ROLLE) is formular


def test_kinder_in_erzeugungsreihenfolge_mit_typ() -> None:
    formular = _Formular()
    baum = Komponentenbaum()

    baum.formular_anzeigen(formular)

    wurzel = baum.topLevelItem(0)
    assert wurzel.childCount() == 2
    assert wurzel.child(0).text(0) == "b_ein: Button"
    assert wurzel.child(0).data(0, KOMPONENTE_ROLLE) is formular.b_ein
    assert wurzel.child(1).text(0) == "s_rot: Shape"
    assert wurzel.child(1).data(0, KOMPONENTE_ROLLE) is formular.s_rot


def test_erneutes_anzeigen_ersetzt_den_baum() -> None:
    formular = _Formular()
    baum = Komponentenbaum()

    baum.formular_anzeigen(formular)
    baum.formular_anzeigen(formular)

    assert baum.topLevelItemCount() == 1
    assert baum.topLevelItem(0).childCount() == 2
