"""Tests für DesignerCanvas.komponente_umbenennen(): die Eigenschaft
„Name“ ändert den Attributnamen im Formular (Abschnitt 7.6). Headless.
Siehe docs/arbeitspakete/M3.md, Schritt 8.
"""

import pytest

from ide.designer.canvas import DesignerCanvas
from pcl import Button, Form


class _LeeresFormular(Form):
    pass


def test_umbenennen_aendert_das_attribut() -> None:
    formular = _LeeresFormular()
    canvas = DesignerCanvas(formular)
    komponente = canvas.komponente_platzieren(Button, 0, 0)

    canvas.komponente_umbenennen(komponente, "b_ein")

    assert not hasattr(formular, "button")
    assert formular.b_ein is komponente
    assert canvas._attributname(komponente) == "b_ein"


def test_umbenennen_auf_denselben_namen_ist_ein_no_op() -> None:
    formular = _LeeresFormular()
    canvas = DesignerCanvas(formular)
    komponente = canvas.komponente_platzieren(Button, 0, 0)

    canvas.komponente_umbenennen(komponente, "button")

    assert formular.button is komponente


def test_umbenennen_auf_vergebenen_namen_loest_fehler_aus() -> None:
    formular = _LeeresFormular()
    canvas = DesignerCanvas(formular)
    canvas.komponente_platzieren(Button, 0, 0)
    zweite = canvas.komponente_platzieren(Button, 20, 20)

    with pytest.raises(ValueError):
        canvas.komponente_umbenennen(zweite, "button")

    assert formular.button2 is zweite


def test_umbenennen_mit_ungueltigem_bezeichner_loest_fehler_aus() -> None:
    formular = _LeeresFormular()
    canvas = DesignerCanvas(formular)
    komponente = canvas.komponente_platzieren(Button, 0, 0)

    with pytest.raises(ValueError):
        canvas.komponente_umbenennen(komponente, "123 nicht gueltig")

    assert formular.button is komponente


def test_das_formular_selbst_kann_nicht_umbenannt_werden() -> None:
    formular = _LeeresFormular()
    canvas = DesignerCanvas(formular)

    with pytest.raises(ValueError):
        canvas.komponente_umbenennen(formular, "irgendwas")


def test_umbenennen_ist_rueckgaengig_machbar() -> None:
    formular = _LeeresFormular()
    canvas = DesignerCanvas(formular)
    komponente = canvas.komponente_platzieren(Button, 0, 0)
    canvas.komponente_umbenennen(komponente, "b_ein")

    canvas.rueckgaengig()

    assert formular.button is komponente
    assert not hasattr(formular, "b_ein")


def test_umbenannte_komponente_bleibt_im_ereignis_codegen_ansprechbar() -> None:
    formular = _LeeresFormular()
    canvas = DesignerCanvas(formular)
    komponente = canvas.komponente_platzieren(Button, 0, 0)
    canvas.komponente_umbenennen(komponente, "b_ein")

    assert canvas._attributname(komponente) == "b_ein"
