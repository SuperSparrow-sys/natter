"""Tests für Undo/Redo im DesignerCanvas (Command-Pattern). Headless.
Siehe Arbeitspaket M3, Schritt 5.
"""

from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent

from ide.designer.canvas import RASTER, DesignerCanvas
from pcl import Button, Form, Shape


class _Formular(Form):
    def create_components(self) -> None:
        self.b_ein = Button(self)
        self.b_ein.left = 100
        self.b_ein.top = 100
        self.b_ein.width = 80
        self.b_ein.height = 30

        self.s_rot = Shape(self)
        self.s_rot.left = 200
        self.s_rot.top = 200


def _tastendruck(taste: int, modifikatoren=Qt.KeyboardModifier.NoModifier) -> QKeyEvent:
    return QKeyEvent(QEvent.Type.KeyPress, taste, modifikatoren)


def test_verschieben_rueckgaengig_stellt_position_wieder_her() -> None:
    formular = _Formular()
    canvas = DesignerCanvas(formular)
    canvas.klick_bei(105, 105)

    canvas.verschieben(RASTER, 0)
    assert formular.b_ein.left == 100 + RASTER

    canvas.rueckgaengig()
    assert formular.b_ein.left == 100


def test_verschieben_wiederholen_wendet_es_erneut_an() -> None:
    formular = _Formular()
    canvas = DesignerCanvas(formular)
    canvas.klick_bei(105, 105)
    canvas.verschieben(RASTER, 0)
    canvas.rueckgaengig()

    canvas.wiederholen()

    assert formular.b_ein.left == 100 + RASTER


def test_groesse_aendern_rueckgaengig_auch_bei_begrenzung() -> None:
    formular = _Formular()
    canvas = DesignerCanvas(formular)
    canvas.klick_bei(105, 105)

    canvas.groesse_aendern(-1000, 0)  # wird auf Mindestgröße 1 begrenzt
    assert formular.b_ein.width == 1

    canvas.rueckgaengig()
    assert formular.b_ein.width == 80  # der echte Ausgangswert, nicht das Delta


def test_loeschen_rueckgaengig_stellt_die_komponente_wieder_her() -> None:
    formular = _Formular()
    canvas = DesignerCanvas(formular)
    canvas.klick_bei(105, 105)

    canvas.loeschen()
    assert not hasattr(formular, "b_ein")

    canvas.rueckgaengig()
    assert hasattr(formular, "b_ein")
    assert formular.b_ein.left == 100
    assert canvas.ausgewaehlte_komponente is formular.b_ein
    # wiederhergestelltes Widget lässt sich erneut auswählen/bearbeiten
    canvas.verschieben(RASTER, 0)
    assert formular.b_ein.left == 100 + RASTER


def test_loeschen_wiederholen_entfernt_erneut() -> None:
    formular = _Formular()
    canvas = DesignerCanvas(formular)
    canvas.klick_bei(105, 105)
    canvas.loeschen()
    canvas.rueckgaengig()

    canvas.wiederholen()

    assert not hasattr(formular, "b_ein")


def test_duplizieren_rueckgaengig_entfernt_die_kopie() -> None:
    formular = _Formular()
    canvas = DesignerCanvas(formular)
    canvas.klick_bei(105, 105)

    canvas.duplizieren()
    assert hasattr(formular, "b_ein_kopie")

    canvas.rueckgaengig()
    assert not hasattr(formular, "b_ein_kopie")
    assert canvas.ausgewaehlte_komponente is formular  # Löschen wählt das Formular


def test_duplizieren_wiederholen_erzeugt_sie_erneut() -> None:
    formular = _Formular()
    canvas = DesignerCanvas(formular)
    canvas.klick_bei(105, 105)
    canvas.duplizieren()
    canvas.rueckgaengig()

    canvas.wiederholen()

    assert hasattr(formular, "b_ein_kopie")
    assert formular.b_ein_kopie.left == 100 + RASTER


def test_ziehen_ist_ein_einziges_rueckgaengig_machbares_kommando() -> None:
    formular = _Formular()
    canvas = DesignerCanvas(formular)
    widget = formular.b_ein._qwidget

    for ereignistyp, lokal, globalpos, taste, tasten in (
        (QEvent.Type.MouseButtonPress, QPointF(5, 5), QPointF(105, 105),
         Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton),
        (QEvent.Type.MouseMove, QPointF(25, 5), QPointF(125, 105),
         Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton),
        (QEvent.Type.MouseButtonRelease, QPointF(25, 5), QPointF(125, 105),
         Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton),
    ):
        maus_ereignis = QMouseEvent(
            ereignistyp, lokal, globalpos, taste, tasten, Qt.KeyboardModifier.NoModifier
        )
        canvas.eventFilter(widget, maus_ereignis)

    assert formular.b_ein.left == 120  # 100 + (125 - 105)

    canvas.rueckgaengig()
    assert formular.b_ein.left == 100  # ein einziger Rückgängig-Schritt reicht


def test_strg_z_macht_rueckgaengig() -> None:
    formular = _Formular()
    canvas = DesignerCanvas(formular)
    canvas.klick_bei(105, 105)
    canvas.verschieben(RASTER, 0)

    canvas.eventFilter(
        formular.b_ein._qwidget,
        _tastendruck(Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier),
    )

    assert formular.b_ein.left == 100


def test_strg_umschalt_z_wiederholt() -> None:
    formular = _Formular()
    canvas = DesignerCanvas(formular)
    canvas.klick_bei(105, 105)
    canvas.verschieben(RASTER, 0)
    canvas.rueckgaengig()

    canvas.eventFilter(
        formular.b_ein._qwidget,
        _tastendruck(
            Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier
        ),
    )

    assert formular.b_ein.left == 100 + RASTER


def test_rueckgaengig_funktioniert_auch_ohne_aktuelle_auswahl() -> None:
    formular = _Formular()
    canvas = DesignerCanvas(formular)
    canvas.klick_bei(105, 105)
    canvas.verschieben(RASTER, 0)
    canvas.klick_bei(999, 999)  # wählt jetzt das Formular selbst

    ergebnis = canvas.eventFilter(
        formular._qwidget, _tastendruck(Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
    )

    assert ergebnis is True
    assert formular.b_ein.left == 100


def test_mehrere_schritte_vollstaendig_rueckgaengig_ergibt_ausgangszustand() -> None:
    formular = _Formular()
    canvas = DesignerCanvas(formular)
    canvas.klick_bei(105, 105)

    canvas.verschieben(RASTER, 0)
    canvas.groesse_aendern(RASTER, 0)
    canvas.duplizieren()
    canvas.klick_bei(105, 105)
    canvas.loeschen()

    for _ in range(4):
        canvas.rueckgaengig()

    assert formular.b_ein.left == 100
    assert formular.b_ein.width == 80
    assert not hasattr(formular, "b_ein_kopie")
    assert canvas.kommandos.kann_rueckgaengig is False
