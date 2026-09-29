"""Eine Zelle außerhalb von `row_count`/`col_count` meldet sich
(Punkt 126)."""

from pathlib import Path

import pytest

from pcl import Form, StringGrid
from pcl.errors import NatterZellenError
from pcl.fehlerkatalog import fehlermeldung_erzeugen

KATALOG = Path(__file__).resolve().parent.parent / "docs" / "fehlerkatalog.yaml"


def _tabelle() -> StringGrid:
    tabelle = StringGrid(Form())
    tabelle.row_count = 3
    tabelle.col_count = 2
    return tabelle


def test_schreiben_hinter_die_letzte_zeile_meldet_den_bereich() -> None:
    tabelle = _tabelle()
    with pytest.raises(NatterZellenError) as fehler:
        tabelle.cells[1, 7] = "x"
    assert str(fehler.value) == (
        "Zeile 7 gibt es nicht, die Tabelle hat 3 Zeilen (0 bis 2)."
    )


def test_lesen_einer_negativen_spalte_meldet_den_bereich() -> None:
    tabelle = _tabelle()
    with pytest.raises(NatterZellenError, match="Spalte -1 gibt es nicht"):
        _ = tabelle.cells[-1, 0]


def test_ein_index_ist_ein_indexerror() -> None:
    tabelle = _tabelle()
    with pytest.raises(IndexError):
        _ = tabelle.cells[0, 3]


def test_gueltige_zellen_gehen_weiter() -> None:
    tabelle = _tabelle()
    tabelle.cells[1, 2] = "unten rechts"
    assert tabelle.cells[1, 2] == "unten rechts"


def test_der_fehlerkatalog_hat_einen_eigenen_eintrag() -> None:
    try:
        _tabelle().cells[0, 9] = "x"
    except NatterZellenError as fehler:
        meldung = fehlermeldung_erzeugen(fehler)
    assert meldung is not None
    assert meldung.ueberschrift.startswith("Laufzeitfehler: Zelle außerhalb")
    assert "Zeile 9" in meldung.was
    assert "row_count" in meldung.pruefe
    assert "id: natter_zellen_error" in KATALOG.read_text(encoding="utf-8")
