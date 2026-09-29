"""Punkt 437: der Objektinspektor bei wenig Höhe.

Bei 1280 × 800 mit 150 % stand unter „Eigenschaft | Wert“ keine
einzige Zeile, bei 1366 × 768 mit 125 % waren es zwei. Palette oben
und Panels unten liefen über die volle Breite und nahmen dem
Inspektor ihre Höhe, und der Komponentenbaum behielt ein Drittel des
Rests. Gemessen wird in logischen Pixeln, abzüglich Taskleiste und
Titelleiste eines maximierten Fensters; die Skalierung ändert an der
Aufteilung sonst nichts."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

WURZEL = Path(__file__).resolve().parent.parent


def _ganze_zeilen(tabelle) -> int:  # noqa: ANN001
    """Wie viele Zeilen ganz in den Sichtbereich passen."""
    hoehe = tabelle.viewport().height()
    return sum(
        1
        for zeile in range(tabelle.rowCount())
        if 0 <= tabelle.rowViewportPosition(zeile)
        and tabelle.rowViewportPosition(zeile) + tabelle.rowHeight(zeile)
        <= hoehe
    )


def _fenster_mit_button(hauptfenster, tmp_path: Path, breite: int, hoehe: int):  # noqa: ANN001, ANN202
    ziel = tmp_path / "03_Taschenrechner"
    shutil.copytree(WURZEL / "beispielprojekte" / "03_Taschenrechner", ziel)
    hauptfenster.resize(breite, hoehe)
    hauptfenster.show()
    hauptfenster.projekt_oeffnen(ziel / "03_Taschenrechner.natter")
    hauptfenster.designer_oeffnen(ziel / "u_main.pfm")
    canvas = hauptfenster._aktueller_canvas
    canvas.auswahl_setzen([canvas.formular.b_plus])
    for _ in range(3):
        QApplication.processEvents()
    return hauptfenster


@pytest.mark.parametrize(
    ("breite", "hoehe"),
    [(1093, 545), (853, 470)],
    ids=["1366x768_125", "1280x800_150"],
)
def test_bei_wenig_hoehe_zeigt_der_inspektor_acht_zeilen(
    hauptfenster, tmp_path: Path, breite: int, hoehe: int
) -> None:
    fenster = _fenster_mit_button(hauptfenster, tmp_path, breite, hoehe)
    inspektor = fenster.objektinspektor
    tabelle = inspektor.eigenschaften_tabelle
    assert tabelle.rowCount() > 8

    assert _ganze_zeilen(tabelle) >= 8

    # Der Baum bleibt benutzbar: mindestens drei Einträge zu sehen.
    baum = inspektor.baum
    zeile = baum.visualItemRect(baum.topLevelItem(0)).height()
    assert baum.viewport().height() >= 3 * zeile
    # Die Palette auch: die Kacheln stehen ganz da, sie liegt nur
    # nicht mehr über dem Inspektor.
    liste = fenster.palette.standard_liste
    assert liste.visualItemRect(liste.item(0)).bottom() <= (
        liste.viewport().height()
    )
    assert fenster.palette_dock.width() < breite - 200
    assert fenster.inspektor_dock.geometry().top() < (
        fenster.palette_dock.geometry().bottom()
    )


def test_auf_grossem_bildschirm_bleibt_der_aufbau(
    hauptfenster, tmp_path: Path
) -> None:
    """1920 × 1080 bei 100 %: Palette über die volle Breite, Zeilen in
    der gewohnten Höhe."""
    fenster = _fenster_mit_button(hauptfenster, tmp_path, 1920, 1001)
    assert not fenster.objektinspektor.knapp
    assert fenster.palette_dock.width() == 1920
    assert fenster.inspektor_dock.geometry().top() > (
        fenster.palette_dock.geometry().bottom()
    )

    # Kleiner gezogen wird es knapp, groß gezogen wieder wie vorher.
    tabelle = fenster.objektinspektor.eigenschaften_tabelle
    gewohnt = tabelle.rowHeight(0)
    fenster.resize(853, 470)
    QApplication.processEvents()
    assert fenster.objektinspektor.knapp
    assert tabelle.rowHeight(0) < gewohnt
    fenster.resize(1920, 1001)
    QApplication.processEvents()
    assert not fenster.objektinspektor.knapp
    assert tabelle.rowHeight(0) == gewohnt
    assert fenster.palette_dock.width() == 1920
