"""Tests für DesignerCanvas.ereignis_handler_erzeugen(): Doppelklick
erzeugt eine Ereignis-Methode per libcst (Abschnitt 4.4). Headless. Siehe
docs/arbeitspakete/M3.md, Schritt 7.
"""

from pathlib import Path

from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent

from ide.designer.canvas import DesignerCanvas
from pcl import Button, Form, Label


class _Formular(Form):
    def create_components(self) -> None:
        self.b_ein = Button(self)
        self.b_ein.left = 10
        self.b_ein.top = 10

        self.l_titel = Label(self)  # kein Ereignis


_STARTINHALT = '''"""Testdatei."""

from u_main_design import Form1Design


class _Formular(Form1Design):
    pass
'''


def _unit_datei_vorbereiten(tmp_path: Path) -> Path:
    unit_pfad = tmp_path / "test.py"
    unit_pfad.write_text(_STARTINHALT, encoding="utf-8")
    return unit_pfad


def test_ohne_pfm_pfad_passiert_nichts() -> None:
    formular = _Formular()
    canvas = DesignerCanvas(formular)  # kein pfm_pfad -> kein unit_pfad
    canvas.klick_bei(15, 15)

    ergebnis = canvas.ereignis_handler_erzeugen(formular.b_ein)

    assert ergebnis is None
    assert formular.b_ein.on_click is None


def test_komponente_ohne_ereignis_liefert_none(tmp_path: Path) -> None:
    _unit_datei_vorbereiten(tmp_path)
    formular = _Formular()
    canvas = DesignerCanvas(formular, pfm_pfad=tmp_path / "test.pfm")

    ergebnis = canvas.ereignis_handler_erzeugen(formular.l_titel)

    assert ergebnis is None


def test_erzeugt_methode_in_der_datei_und_verknuepft_sie(tmp_path: Path) -> None:
    unit_pfad = _unit_datei_vorbereiten(tmp_path)
    formular = _Formular()
    canvas = DesignerCanvas(formular, pfm_pfad=tmp_path / "test.pfm")

    ergebnis = canvas.ereignis_handler_erzeugen(formular.b_ein)

    assert ergebnis == "b_ein_click"
    assert "def b_ein_click(self, sender):" in unit_pfad.read_text(encoding="utf-8")
    assert formular.b_ein.on_click.__name__ == "b_ein_click"
    # aufrufbar, ohne einen Fehler auszulösen (reine Platzhalterwirkung)
    formular.b_ein.on_click(formular.b_ein)


def test_bereits_verknuepftes_ereignis_wird_nicht_neu_erzeugt(tmp_path: Path) -> None:
    unit_pfad = _unit_datei_vorbereiten(tmp_path)
    formular = _Formular()
    canvas = DesignerCanvas(formular, pfm_pfad=tmp_path / "test.pfm")
    canvas.ereignis_handler_erzeugen(formular.b_ein)
    inhalt_danach_erstem_mal = unit_pfad.read_text(encoding="utf-8")

    ergebnis = canvas.ereignis_handler_erzeugen(formular.b_ein)

    assert ergebnis == "b_ein_click"
    assert unit_pfad.read_text(encoding="utf-8") == inhalt_danach_erstem_mal


def test_pfm_wird_mit_dem_verknuepften_ereignis_gespeichert(tmp_path: Path) -> None:
    import json

    _unit_datei_vorbereiten(tmp_path)
    pfm_pfad = tmp_path / "test.pfm"
    formular = _Formular()
    canvas = DesignerCanvas(formular, pfm_pfad=pfm_pfad)

    canvas.ereignis_handler_erzeugen(formular.b_ein)

    daten = json.loads(pfm_pfad.read_text(encoding="utf-8"))
    kind = next(k for k in daten["children"] if k["name"] == "b_ein")
    assert kind["events"] == {"on_click": "b_ein_click"}


def test_rueckgaengig_entfernt_die_verknuepfung_aber_nicht_die_methode(tmp_path: Path) -> None:
    unit_pfad = _unit_datei_vorbereiten(tmp_path)
    formular = _Formular()
    canvas = DesignerCanvas(formular, pfm_pfad=tmp_path / "test.pfm")
    canvas.ereignis_handler_erzeugen(formular.b_ein)

    canvas.rueckgaengig()

    assert formular.b_ein.on_click is None
    assert "def b_ein_click(self, sender):" in unit_pfad.read_text(encoding="utf-8")


def test_echter_doppelklick_erzeugt_den_handler(tmp_path: Path) -> None:
    unit_pfad = _unit_datei_vorbereiten(tmp_path)
    formular = _Formular()
    canvas = DesignerCanvas(formular, pfm_pfad=tmp_path / "test.pfm")
    widget = formular.b_ein._qwidget

    druck = QMouseEvent(
        QEvent.Type.MouseButtonPress, QPointF(5, 5), QPointF(15, 15),
        Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
    )
    doppelklick = QMouseEvent(
        QEvent.Type.MouseButtonDblClick, QPointF(5, 5), QPointF(15, 15),
        Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
    )

    canvas.eventFilter(widget, druck)
    canvas.eventFilter(widget, doppelklick)

    assert "def b_ein_click(self, sender):" in unit_pfad.read_text(encoding="utf-8")
    assert formular.b_ein.on_click.__name__ == "b_ein_click"
    # der Doppelklick darf keinen Ziehvorgang hinterlassen
    assert canvas._ziehen_komponente is None
