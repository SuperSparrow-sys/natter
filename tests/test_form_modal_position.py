"""Formular: modal öffnen, Position, Fenstersymbol (Punkt 92)."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QGuiApplication, QPixmap

from pcl import Button, Form
from pcl.errors import NatterPropertyError
from pcl.properties import eigenschaften

_OFFEN: list[Form] = []


def _formular() -> Form:
    formular = Form()
    _OFFEN.append(formular)
    return formular


def test_ein_zweites_formular_laesst_sich_modal_oeffnen() -> None:
    haupt = _formular()
    haupt.show()
    zweites = _formular()
    ablauf: list[str] = []

    def waehrenddessen() -> None:
        ablauf.append("offen")
        assert zweites._qwidget.isVisible()
        assert zweites._qwidget.windowModality() == Qt.WindowModality.ApplicationModal
        zweites.close()

    QTimer.singleShot(0, waehrenddessen)
    zweites.show_modal()
    ablauf.append("danach")

    assert ablauf == ["offen", "danach"]
    assert not zweites._qwidget.isVisible()
    assert zweites._qwidget.windowModality() == Qt.WindowModality.NonModal


def test_show_modal_liest_nach_dem_schliessen_was_eingetragen_wurde() -> None:
    class Eingabe(Form):
        def create_components(self) -> None:
            self.b_ok = Button(self)
            self.b_ok.on_click = self.b_ok_click
            self.ergebnis = ""

        def b_ok_click(self, sender) -> None:
            self.ergebnis = "fertig"
            self.close()

    dialog = Eingabe()
    _OFFEN.append(dialog)
    QTimer.singleShot(0, dialog.b_ok._qwidget.click)
    dialog.show_modal()

    assert dialog.ergebnis == "fertig"


def test_ein_sofort_geschlossenes_formular_haengt_nicht() -> None:
    formular = _formular()
    QTimer.singleShot(0, formular.close)
    formular.show_modal()
    assert not formular._qwidget.isVisible()


def test_position_designed_setzt_das_fenster_an_left_und_top() -> None:
    formular = _formular()
    formular.position = "designed"
    formular.left = 40
    formular.top = 60
    formular.show()

    assert (formular._qwidget.x(), formular._qwidget.y()) == (40, 60)


def test_screen_center_ist_der_standard_und_zentriert() -> None:
    formular = _formular()
    assert formular.position == "screen_center"
    formular.width = 200
    formular.height = 100
    formular.show()

    flaeche = QGuiApplication.primaryScreen().availableGeometry()
    mitte = formular._qwidget.frameGeometry().center()
    assert abs(mitte.x() - flaeche.center().x()) <= 2
    assert abs(mitte.y() - flaeche.center().y()) <= 2
    assert formular.left == formular._qwidget.x()


def test_left_verschiebt_ein_offenes_fenster() -> None:
    formular = _formular()
    formular.show()
    formular.left = 15
    formular.top = 25
    assert (formular._qwidget.x(), formular._qwidget.y()) == (15, 25)


def test_eine_unbekannte_position_wird_abgelehnt() -> None:
    formular = _formular()
    with pytest.raises(NatterPropertyError, match="screen_center"):
        formular.position = "mitte"


def test_icon_setzt_das_fenstersymbol(tmp_path: Path) -> None:
    bild = QPixmap(16, 16)
    bild.fill(QColor("#e53935"))
    pfad = tmp_path / "symbol.png"
    bild.save(str(pfad))

    formular = _formular()
    formular.icon = str(pfad)
    assert not formular._qwidget.windowIcon().isNull()

    formular.icon = ""
    assert formular._qwidget.windowIcon().isNull()


def test_die_neuen_eigenschaften_stehen_im_objektinspektor() -> None:
    props = eigenschaften(Form)
    for name in ("position", "left", "top", "icon"):
        assert name in props
    assert props["icon"].art == "bild"


def test_im_designer_bewegt_left_das_formular_nicht() -> None:
    class Vorschau(Form):
        _entwurfsansicht = True

    formular = Vorschau()
    _OFFEN.append(formular)
    formular._qwidget.move(0, 0)
    formular.position = "designed"
    formular.left = 300
    formular.show()
    assert formular._qwidget.x() == 0


_ZWEI_FORMULARE = """
import gc
from PySide6.QtWidgets import QApplication, QWidget
from pcl import Form

app = QApplication([])
erstes = Form()
erstes.show()
zweites = Form()
zweites.show()
app.processEvents()
zweites.close()
app.processEvents()
del zweites
gc.collect()
for _ in range(200):
    fenster = QWidget()
    fenster.show()
    fenster.close()
app.processEvents()
print("fertig")
"""


def test_ein_aufgeraeumtes_zweites_formular_beschaedigt_nichts(tmp_path) -> None:
    """Punkt 137: die Bildschirmmitte kam aus `QWidget.screen()` des
    noch verborgenen Fensters. Danach brach das Programm ab, sobald
    ein zweites Formular geschlossen und aufgeräumt war - nicht dort,
    sondern später beim nächsten Fenster. Im selben Prozess würde der
    Test die übrigen Tests mitreißen, deshalb läuft er in einem
    eigenen."""
    import os
    import subprocess
    import sys

    skript = tmp_path / "zwei_formulare.py"
    skript.write_text(_ZWEI_FORMULARE, encoding="utf-8")
    umgebung = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    umgebung["PYTHONPATH"] = str(Path(__file__).resolve().parent.parent)

    lauf = subprocess.run(
        [sys.executable, str(skript)],
        capture_output=True,
        text=True,
        timeout=120,
        env=umgebung,
    )

    assert lauf.returncode == 0, lauf.stderr[-2000:]
    assert "fertig" in lauf.stdout
