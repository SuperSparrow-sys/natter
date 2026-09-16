"""Tests für pcl/components/additional.py: StringGrid, Image. Headless.
Siehe docs/PLAN.md, M1 Schritt 6.
"""

from pathlib import Path

import pytest
from PySide6.QtGui import QColor, QPixmap

from pcl import Form, Image, StringGrid
from pcl.errors import NatterPropertyError


class _Formular(Form):
    def create_components(self) -> None:
        self.sg_tabelle = StringGrid(self)
        self.i_bild = Image(self)


def test_stringgrid_standardgroesse() -> None:
    formular = _Formular()
    assert (formular.sg_tabelle.row_count, formular.sg_tabelle.col_count) == (5, 5)
    assert formular.sg_tabelle._qwidget.rowCount() == 5
    assert formular.sg_tabelle._qwidget.columnCount() == 5


def test_stringgrid_row_count_aenderung_wirkt_sofort() -> None:
    formular = _Formular()
    formular.sg_tabelle.row_count = 3
    assert formular.sg_tabelle._qwidget.rowCount() == 3


def test_stringgrid_cells_schreiben_und_lesen() -> None:
    formular = _Formular()
    formular.sg_tabelle.row_count = 2
    formular.sg_tabelle.cells[0, 1] = "1"
    formular.sg_tabelle.cells[1, 1] = "Max"

    assert formular.sg_tabelle.cells[0, 1] == "1"
    assert formular.sg_tabelle.cells[1, 1] == "Max"


def test_stringgrid_leere_zelle_liefert_leerstring() -> None:
    formular = _Formular()
    assert formular.sg_tabelle.cells[0, 0] == ""


def test_stringgrid_cells_lehnt_falschen_typ_ab() -> None:
    formular = _Formular()
    with pytest.raises(NatterPropertyError):
        formular.sg_tabelle.cells[0, 0] = 5


def test_image_ohne_bild_hat_kein_pixmap() -> None:
    formular = _Formular()
    assert formular.i_bild.picture.pfad is None


def test_image_load_from_file_zeigt_bild(tmp_path: Path) -> None:
    formular = _Formular()
    bilddatei = tmp_path / "test.png"
    pixmap = QPixmap(2, 2)
    pixmap.fill(QColor("red"))
    pixmap.save(str(bilddatei))

    formular.i_bild.picture.load_from_file(str(bilddatei))

    assert formular.i_bild.picture.pfad == str(bilddatei)
    assert not formular.i_bild._qwidget.pixmap().isNull()


def test_image_clear_entfernt_bild(tmp_path: Path) -> None:
    formular = _Formular()
    bilddatei = tmp_path / "test.png"
    pixmap = QPixmap(2, 2)
    pixmap.fill(QColor("red"))
    pixmap.save(str(bilddatei))

    formular.i_bild.picture.load_from_file(str(bilddatei))
    formular.i_bild.picture.clear()

    assert formular.i_bild.picture.pfad is None
    assert formular.i_bild._qwidget.pixmap().isNull()


def test_image_load_from_file_lehnt_falschen_typ_ab() -> None:
    formular = _Formular()
    with pytest.raises(NatterPropertyError):
        formular.i_bild.picture.load_from_file(5)
