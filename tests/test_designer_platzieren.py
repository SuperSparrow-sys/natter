"""Tests für DesignerCanvas.komponente_platzieren(): Palette → Formular
(Abschnitt 7.3). Headless. Siehe docs/arbeitspakete/M3.md, Schritt 6.
"""

from ide.designer.canvas import DesignerCanvas
from pcl import Button, Form
from pcl.components.additional import StringGrid
from pcl.components.standard import ScrollBar


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


def test_button_behaelt_den_control_standard_75x25() -> None:
    # Kompakte Komponenten wie Button brauchen keine eigene Startgröße.
    formular = _LeeresFormular()
    canvas = DesignerCanvas(formular)

    komponente = canvas.komponente_platzieren(Button, 40, 60)

    assert (komponente.width, komponente.height) == (75, 25)


def test_stringgrid_bekommt_beim_platzieren_eine_groessere_startflaeche() -> None:
    # Der einheitliche 75x25-Standard ließ eine 5x5-StringGrid beim
    # Rundgang durch alle Palettentypen nur verzerrt/zusammengequetscht
    # aussehen (siehe ide/designer/canvas.py, _STANDARDGROESSEN).
    formular = _LeeresFormular()
    canvas = DesignerCanvas(formular)

    komponente = canvas.komponente_platzieren(StringGrid, 40, 60)

    assert (komponente.width, komponente.height) == (220, 150)


def test_scrollbar_bekommt_beim_platzieren_eine_breite_flache_startgroesse() -> None:
    formular = _LeeresFormular()
    canvas = DesignerCanvas(formular)

    komponente = canvas.komponente_platzieren(ScrollBar, 40, 60)

    assert (komponente.width, komponente.height) == (150, 17)
