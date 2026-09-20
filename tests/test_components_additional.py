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


# --------------------------------------------------- StringGrid-Ereignisse
#
# `on_select_cell` und `on_edit_cell` standen seit M1 in Abschnitt 5.4
# und in docs/komponenten.md als "noch offen". Sie entsprechen
# OnSelectCell und OnEditingDone in Lazarus; beide bekommen spalte und
# zeile in dieser Reihenfolge - wie Lazarus' (ACol, ARow) und wie
# cells[spalte, zeile].


def test_stringgrid_meldet_die_ausgewaehlte_zelle() -> None:
    formular = _Formular()
    gemeldet: list[tuple[int, int]] = []
    formular.sg_tabelle.on_select_cell = lambda sender, spalte, zeile: gemeldet.append(
        (spalte, zeile)
    )

    formular.sg_tabelle._qwidget.setCurrentCell(2, 1)

    assert gemeldet == [(1, 2)]


def test_stringgrid_meldet_keine_auswahl_wenn_gar_keine_zelle_mehr_da_ist() -> None:
    """Qt zeigt mit -1 an, dass nichts ausgewaehlt ist - etwa nachdem
    die letzte Zeile gelöscht wurde. Das ist keine Auswahl."""
    formular = _Formular()
    gemeldet: list[tuple[int, int]] = []
    formular.sg_tabelle.on_select_cell = lambda sender, spalte, zeile: gemeldet.append(
        (spalte, zeile)
    )

    formular.sg_tabelle._qwidget.setCurrentCell(-1, -1)

    assert gemeldet == []


def test_stringgrid_meldet_eine_aenderung_durch_den_benutzer() -> None:
    formular = _Formular()
    gemeldet: list[tuple[int, int, str]] = []
    formular.sg_tabelle.on_edit_cell = (
        lambda sender, spalte, zeile, text: gemeldet.append((spalte, zeile, text))
    )
    formular.sg_tabelle.cells[1, 2] = "vorher"

    # So kommt eine Änderung an, die der Benutzer im Widget vorgenommen
    # hat: über den Eintrag selbst, nicht über `cells`.
    formular.sg_tabelle._qwidget.item(2, 1).setText("nachher")

    assert gemeldet == [(1, 2, "nachher")]


def test_was_das_programm_selbst_schreibt_ist_keine_aenderung() -> None:
    """Sonst loeste schon das Fuellen der Tabelle hundert Ereignisse
    aus - `load_dataframe` schreibt Zelle für Zelle."""
    formular = _Formular()
    gemeldet: list[object] = []
    formular.sg_tabelle.on_edit_cell = lambda *args: gemeldet.append(args)

    for zeile in range(3):
        formular.sg_tabelle.cells[0, zeile] = str(zeile)

    assert gemeldet == []


def test_nach_dem_programmschreiben_meldet_der_benutzer_wieder() -> None:
    """Die Sperre darf nicht haengenbleiben."""
    formular = _Formular()
    gemeldet: list[object] = []
    formular.sg_tabelle.cells[0, 0] = "a"
    formular.sg_tabelle.on_edit_cell = lambda *args: gemeldet.append(args)

    formular.sg_tabelle._qwidget.item(0, 0).setText("b")

    assert len(gemeldet) == 1


# --------------------------------------------------- Image: stretch & Co.
#
# stretch/proportional/center standen seit M1 als "noch offen".
# Abweichung von Lazarus, bewusst: `stretch` steht auf True. Die Kekse
# in 04_CookieKlicker sind 512x512 Punkte gross und liegen in einem
# 300x300 grossen Image - mit Lazarus' Standard saehe man ein Viertel
# Keks.


@pytest.fixture
def bild(tmp_path: Path) -> Path:
    pfad = tmp_path / "breit.png"
    karte = QPixmap(400, 100)
    karte.fill(QColor("#c42b1c"))
    karte.save(str(pfad))
    return pfad


def test_image_zieht_das_bild_standardmaessig_auf_die_volle_flaeche(bild: Path) -> None:
    formular = _Formular()
    formular.i_bild.width, formular.i_bild.height = 200, 200
    formular.i_bild.picture.load_from_file(str(bild))

    assert formular.i_bild.stretch is True
    assert formular.i_bild._qwidget.hasScaledContents()


def test_image_ohne_stretch_zeigt_originalgroesse(bild: Path) -> None:
    formular = _Formular()
    formular.i_bild.width, formular.i_bild.height = 200, 200
    formular.i_bild.picture.load_from_file(str(bild))

    formular.i_bild.stretch = False

    assert not formular.i_bild._qwidget.hasScaledContents()
    assert formular.i_bild._qwidget.pixmap().size().toTuple() == (400, 100)


def test_image_proportional_behaelt_das_seitenverhaeltnis(bild: Path) -> None:
    """400x100 in 200x200 wird 200x50, nicht 200x200."""
    formular = _Formular()
    formular.i_bild.width, formular.i_bild.height = 200, 200
    formular.i_bild.picture.load_from_file(str(bild))

    formular.i_bild.proportional = True

    assert not formular.i_bild._qwidget.hasScaledContents()
    assert formular.i_bild._qwidget.pixmap().size().toTuple() == (200, 50)


def test_image_rechnet_immer_vom_original(bild: Path) -> None:
    """Wer zweimal hintereinander skaliert, bekommt Treppen - deshalb
    liegt das ungeskalierte Bild in `picture.original`."""
    formular = _Formular()
    formular.i_bild.width, formular.i_bild.height = 200, 200
    formular.i_bild.picture.load_from_file(str(bild))
    formular.i_bild.proportional = True

    formular.i_bild.width, formular.i_bild.height = 800, 800

    assert formular.i_bild._qwidget.pixmap().size().toTuple() == (800, 200)
    assert formular.i_bild.picture.original.size().toTuple() == (400, 100)


def test_image_center_setzt_das_bild_mittig(bild: Path) -> None:
    from PySide6.QtCore import Qt

    formular = _Formular()
    formular.i_bild.picture.load_from_file(str(bild))

    formular.i_bild.center = True

    assert formular.i_bild._qwidget.alignment() == Qt.AlignmentFlag.AlignCenter


def test_image_ohne_bild_bleibt_leer() -> None:
    formular = _Formular()
    formular.i_bild.stretch = False
    assert formular.i_bild._qwidget.pixmap().isNull()
