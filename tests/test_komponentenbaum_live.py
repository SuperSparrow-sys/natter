"""Der Komponentenbaum folgt dem Designer (Punkt 45 der offenen
Punkte).

Bis 0.3.3 entstand der Baum nur beim Öffnen des Formulars: ein neu
platzierter Knopf erschien dort erst nach Schließen und erneutem
Öffnen des Designers.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QTreeWidgetItemIterator

from ide.inspector.komponentenbaum import KOMPONENTE_ROLLE
from ide.project.neu import projekt_erzeugen
from ide.shell.hauptfenster import HauptFenster
from pcl import Button


def _zeilen(fenster: HauptFenster) -> list[str]:
    zeilen = QTreeWidgetItemIterator(fenster.objektinspektor.baum)
    texte = []
    while zeilen.value() is not None:
        texte.append(zeilen.value().text(0))
        zeilen += 1
    return texte


def _designer(tmp_path: Path):
    projekt = projekt_erzeugen("gui", tmp_path, "Umrechner")
    fenster = HauptFenster()
    fenster.projekt_oeffnen(projekt.ordner / "Umrechner.natter")
    fenster.designer_oeffnen(projekt.ordner / "u_main.pfm")
    return fenster, fenster._aktueller_canvas


def test_neu_platzierte_komponente_erscheint_sofort(tmp_path: Path) -> None:
    fenster, canvas = _designer(tmp_path)

    knopf = canvas.komponente_platzieren(Button, 32, 128)

    name = canvas.name_von(knopf)
    assert f"{name}: Button" in _zeilen(fenster)
    aktuell = fenster.objektinspektor.baum.currentItem()
    assert aktuell.data(0, KOMPONENTE_ROLLE) is knopf


def test_geloeschte_komponente_verschwindet(tmp_path: Path) -> None:
    fenster, canvas = _designer(tmp_path)
    knopf = canvas.komponente_platzieren(Button, 32, 128)
    name = canvas.name_von(knopf)

    canvas.loeschen()

    assert f"{name}: Button" not in _zeilen(fenster)


def test_umbenennen_zeigt_den_neuen_namen(tmp_path: Path) -> None:
    fenster, canvas = _designer(tmp_path)
    knopf = canvas.komponente_platzieren(Button, 32, 128)

    canvas.komponente_umbenennen(knopf, "b_rechnen")

    assert "b_rechnen: Button" in _zeilen(fenster)
