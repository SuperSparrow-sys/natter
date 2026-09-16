"""Tests für DesignerCanvas.komponente_platzieren(): Palette → Formular
(Abschnitt 7.3). Headless. Siehe docs/arbeitspakete/M3.md, Schritt 6.
"""

from ide.designer.canvas import DesignerCanvas
from pcl import Button, Form


class _LeeresFormular(Form):
    pass


def test_platzieren_erzeugt_die_richtige_komponentenklasse() -> None:
    formular = _LeeresFormular()
    canvas = DesignerCanvas(formular)

    komponente = canvas.komponente_platzieren(Button, 40, 60)

    assert isinstance(komponente, Button)
    assert (komponente.left, komponente.top) == (40, 60)
    assert canvas._attributname(komponente) == "button"


def test_platzierte_komponente_ist_ausgewaehlt_und_im_baum_vorhanden() -> None:
    formular = _LeeresFormular()
    canvas = DesignerCanvas(formular)

    komponente = canvas.komponente_platzieren(Button, 40, 60)

    assert canvas.ausgewaehlte_komponente is komponente
    assert formular.button is komponente


def test_mehrfaches_platzieren_erhaelt_eindeutige_namen() -> None:
    formular = _LeeresFormular()
    canvas = DesignerCanvas(formular)

    erster = canvas.komponente_platzieren(Button, 0, 0)
    zweiter = canvas.komponente_platzieren(Button, 20, 20)

    assert canvas._attributname(erster) == "button"
    assert canvas._attributname(zweiter) == "button2"


def test_platzieren_ist_rueckgaengig_machbar() -> None:
    formular = _LeeresFormular()
    canvas = DesignerCanvas(formular)
    canvas.komponente_platzieren(Button, 40, 60)

    canvas.rueckgaengig()

    assert not hasattr(formular, "button")


def test_platzierte_komponente_laesst_sich_direkt_anklicken() -> None:
    formular = _LeeresFormular()
    canvas = DesignerCanvas(formular)
    canvas.komponente_platzieren(Button, 40, 60)

    getroffen = canvas.klick_bei(45, 70)

    assert getroffen is formular.button
