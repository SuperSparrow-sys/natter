"""Tests für DesignerCanvas.komponente_platzieren(): Palette → Formular
(Abschnitt 7.3). Headless. Siehe docs/arbeitspakete/M3.md, Schritt 6.
"""

from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent

from ide.designer.canvas import DesignerCanvas
from pcl import Button, Form
from pcl.components.additional import StringGrid
from pcl.components.standard import ScrollBar


def _klick(x: float, y: float) -> QMouseEvent:
    return QMouseEvent(
        QEvent.Type.MouseButtonPress,
        QPointF(x, y),
        QPointF(x, y),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )


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


def test_platzierungsmodus_platziert_beim_naechsten_klick_auf_das_formular() -> None:
    """Nutzer-Feedback (September 2026): „ich möchte per Klick neue
    Objekte auf der GUI hinzufügen" - Klick auf ein Palettensymbol
    (`platzierungsmodus_setzen`), dann Klick auf das Formular platziert
    dort, wie in Lazarus. Ergänzung zum bisherigen Doppelklick (immer
    mittig)."""
    formular = _LeeresFormular()
    canvas = DesignerCanvas(formular)

    canvas.platzierungsmodus_setzen(Button)
    getroffen = canvas.eventFilter(formular._qwidget, _klick(40, 60))

    assert getroffen is True
    assert isinstance(formular.button, Button)
    assert (formular.button.left, formular.button.top) == (40, 60)


def test_platzierungsmodus_endet_automatisch_nach_dem_klick() -> None:
    formular = _LeeresFormular()
    canvas = DesignerCanvas(formular)
    canvas.platzierungsmodus_setzen(Button)

    canvas.eventFilter(formular._qwidget, _klick(40, 60))
    # ein zweiter Klick soll nicht nochmal platzieren, sondern nur noch
    # normal auswählen/ziehen (Klick trifft nichts -> kein Fehler)
    canvas.eventFilter(formular._qwidget, _klick(200, 200))

    assert not hasattr(formular, "button2")


def test_platzierungsmodus_ohne_typ_bricht_ab() -> None:
    formular = _LeeresFormular()
    canvas = DesignerCanvas(formular)
    canvas.platzierungsmodus_setzen(Button)

    canvas.platzierungsmodus_setzen(None)
    canvas.eventFilter(formular._qwidget, _klick(40, 60))

    assert not hasattr(formular, "button")


def test_platzierung_auf_einer_bestehenden_komponente_rechnet_die_position_um() -> None:
    """Ein Klick während des Platzierungsmodus kann auch ein bereits
    vorhandenes Widget treffen (z. B. ein größeres, das den Klickpunkt
    überdeckt) - die neue Komponente landet trotzdem an der richtigen
    Formular-Koordinate, nicht an (0, 0) relativ zum getroffenen
    Widget."""
    formular = _LeeresFormular()
    canvas = DesignerCanvas(formular)
    bestehend = canvas.komponente_platzieren(Button, 100, 100)

    canvas.platzierungsmodus_setzen(Button)
    canvas.eventFilter(bestehend._qwidget, _klick(5, 5))

    assert (formular.button2.left, formular.button2.top) == (105, 105)
