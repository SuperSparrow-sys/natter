"""Tests für ide/designer/canvas.py: Ziehen, Tastatur, Löschen,
Duplizieren, automatisches `.pfm`-Speichern. Headless. Siehe
docs/arbeitspakete/M3.md, Schritt 4.
"""

import json
from pathlib import Path

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
        self.s_rot.width = 40
        self.s_rot.height = 40


def _tastendruck(taste: int, modifikatoren=Qt.KeyboardModifier.NoModifier) -> QKeyEvent:
    return QKeyEvent(QEvent.Type.KeyPress, taste, modifikatoren)


def test_verschieben_aendert_left_top() -> None:
    formular = _Formular()
    canvas = DesignerCanvas(formular)
    canvas.klick_bei(105, 105)

    canvas.verschieben(5, -5)

    assert (formular.b_ein.left, formular.b_ein.top) == (105, 95)


def test_groesse_aendern_hat_mindestens_ein_pixel() -> None:
    formular = _Formular()
    canvas = DesignerCanvas(formular)
    canvas.klick_bei(105, 105)

    canvas.groesse_aendern(-1000, -1000)

    assert formular.b_ein.width == 1
    assert formular.b_ein.height == 1


def test_loeschen_entfernt_die_komponente_und_waehlt_das_formular() -> None:
    formular = _Formular()
    canvas = DesignerCanvas(formular)
    canvas.klick_bei(105, 105)

    canvas.loeschen()

    assert not hasattr(formular, "b_ein")
    assert canvas.ausgewaehlte_komponente is formular


def test_duplizieren_erzeugt_eine_versetzte_kopie() -> None:
    formular = _Formular()
    canvas = DesignerCanvas(formular)
    canvas.klick_bei(105, 105)

    kopie = canvas.duplizieren()

    assert kopie is not formular.b_ein
    assert kopie.caption == formular.b_ein.caption
    assert kopie.left == formular.b_ein.left + RASTER
    assert kopie.top == formular.b_ein.top + RASTER
    assert canvas.ausgewaehlte_komponente is kopie
    assert canvas._attributname(kopie) == "b_ein_kopie"


def test_duplizieren_findet_einen_eindeutigen_namen() -> None:
    formular = _Formular()
    canvas = DesignerCanvas(formular)
    canvas.klick_bei(105, 105)

    canvas.duplizieren()
    # (101, 101) statt (105, 105): liegt in der schmalen Ecke von b_ein,
    # die nicht von der (um RASTER versetzten) Kopie überlappt wird und
    # außerhalb von deren Größenanfassern - trifft eindeutig wieder b_ein.
    canvas.klick_bei(101, 101)  # b_ein wieder auswählen
    zweite_kopie = canvas.duplizieren()

    assert canvas._attributname(zweite_kopie) == "b_ein_kopie2"


def test_pfeiltaste_bewegt_um_ein_rasterfeld() -> None:
    formular = _Formular()
    canvas = DesignerCanvas(formular)
    canvas.klick_bei(105, 105)

    canvas.eventFilter(formular.b_ein._qwidget, _tastendruck(Qt.Key.Key_Right))

    assert formular.b_ein.left == 100 + RASTER


def test_alt_pfeiltaste_bewegt_um_ein_pixel() -> None:
    formular = _Formular()
    canvas = DesignerCanvas(formular)
    canvas.klick_bei(105, 105)

    canvas.eventFilter(
        formular.b_ein._qwidget,
        _tastendruck(Qt.Key.Key_Right, Qt.KeyboardModifier.AltModifier),
    )

    assert formular.b_ein.left == 101


def test_umschalt_pfeiltaste_aendert_die_groesse() -> None:
    formular = _Formular()
    canvas = DesignerCanvas(formular)
    canvas.klick_bei(105, 105)

    canvas.eventFilter(
        formular.b_ein._qwidget,
        _tastendruck(Qt.Key.Key_Right, Qt.KeyboardModifier.ShiftModifier),
    )

    assert formular.b_ein.width == 80 + RASTER


def test_entf_taste_loescht() -> None:
    formular = _Formular()
    canvas = DesignerCanvas(formular)
    canvas.klick_bei(105, 105)

    canvas.eventFilter(formular.b_ein._qwidget, _tastendruck(Qt.Key.Key_Delete))

    assert not hasattr(formular, "b_ein")


def test_strg_d_dupliziert() -> None:
    formular = _Formular()
    canvas = DesignerCanvas(formular)
    canvas.klick_bei(105, 105)

    canvas.eventFilter(
        formular.b_ein._qwidget,
        _tastendruck(Qt.Key.Key_D, Qt.KeyboardModifier.ControlModifier),
    )

    assert hasattr(formular, "b_ein_kopie")


def test_tastatur_ohne_auswahl_der_komponente_wirkt_nicht_auf_das_formular() -> None:
    formular = _Formular()
    canvas = DesignerCanvas(formular)
    canvas.klick_bei(250, 250)  # wählt das Formular selbst

    ergebnis = canvas.eventFilter(formular._qwidget, _tastendruck(Qt.Key.Key_Right))

    assert ergebnis is False


def test_maus_ziehen_verschiebt_die_komponente() -> None:
    formular = _Formular()
    canvas = DesignerCanvas(formular)
    widget = formular.b_ein._qwidget

    druck = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        QPointF(5, 5),
        QPointF(105, 105),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    bewegung = QMouseEvent(
        QEvent.Type.MouseMove,
        QPointF(15, 5),
        QPointF(115, 105),
        Qt.MouseButton.NoButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    loslassen = QMouseEvent(
        QEvent.Type.MouseButtonRelease,
        QPointF(15, 5),
        QPointF(115, 105),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )

    assert canvas.eventFilter(widget, druck) is True
    assert canvas.eventFilter(widget, bewegung) is True
    assert formular.b_ein.left == 110  # 100 + (115 - 105)
    assert canvas.eventFilter(widget, loslassen) is True


def test_automatisches_pfm_speichern_nach_verschieben(tmp_path: Path) -> None:
    formular = _Formular()
    pfm_pfad = tmp_path / "test.pfm"
    canvas = DesignerCanvas(formular, pfm_pfad=pfm_pfad)
    canvas.klick_bei(105, 105)

    canvas.verschieben(RASTER, 0)

    gespeichert = json.loads(pfm_pfad.read_text(encoding="utf-8"))
    kind = next(k for k in gespeichert["children"] if k["name"] == "b_ein")
    assert kind["properties"]["left"] == 100 + RASTER


def test_ohne_pfm_pfad_wird_nichts_geschrieben(tmp_path: Path) -> None:
    formular = _Formular()
    canvas = DesignerCanvas(formular)  # kein pfm_pfad
    canvas.klick_bei(105, 105)

    canvas.verschieben(RASTER, 0)  # darf nicht fehlschlagen

    assert list(tmp_path.iterdir()) == []
