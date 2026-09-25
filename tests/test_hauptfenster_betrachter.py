"""Tests für die IDE-Verdrahtung der Betrachter (Abschnitt 11.3-11.5):
Doppelklick im Explorer auf eine `.csv`-/Bild-/`.html`-Datei öffnet den
passenden Betrachter-Tab statt des Quelltexteditors. Siehe
Arbeitspaket M5, Schritt 7.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QTreeWidgetItem

from ide.shell.explorer import PFAD_ROLLE
from ide.shell.hauptfenster import HauptFenster
from ide.viewers import BildVorschau, CsvAnsicht, HtmlVorschau


def _eintrag(pfad: Path) -> QTreeWidgetItem:
    eintrag = QTreeWidgetItem([pfad.name])
    eintrag.setData(0, PFAD_ROLLE, str(pfad))
    return eintrag


def test_doppelklick_auf_csv_oeffnet_die_csv_ansicht(tmp_path: Path) -> None:
    datei = tmp_path / "schueler.csv"
    datei.write_text("name,punkte\nAnna,12\n", encoding="utf-8")
    fenster = HauptFenster()

    fenster._bei_explorer_doppelklick(_eintrag(datei), 0)

    aktiv = fenster.editor_tabs.currentWidget()
    assert isinstance(aktiv, CsvAnsicht)


def test_doppelklick_auf_bild_oeffnet_die_bildvorschau(tmp_path: Path) -> None:
    datei = tmp_path / "bild.png"
    pixmap = QPixmap(10, 10)
    pixmap.fill(QColor("blue"))
    pixmap.save(str(datei), "PNG")
    fenster = HauptFenster()

    fenster._bei_explorer_doppelklick(_eintrag(datei), 0)

    aktiv = fenster.editor_tabs.currentWidget()
    assert isinstance(aktiv, BildVorschau)


def test_doppelklick_auf_html_oeffnet_die_html_vorschau(tmp_path: Path) -> None:
    datei = tmp_path / "seite.html"
    datei.write_text("<h1>Highscore</h1>", encoding="utf-8")
    fenster = HauptFenster()

    fenster._bei_explorer_doppelklick(_eintrag(datei), 0)

    aktiv = fenster.editor_tabs.currentWidget()
    assert isinstance(aktiv, HtmlVorschau)


def test_doppelklick_auf_dieselbe_datei_aktiviert_nur_den_vorhandenen_tab(
    tmp_path: Path,
) -> None:
    datei = tmp_path / "schueler.csv"
    datei.write_text("name,punkte\nAnna,12\n", encoding="utf-8")
    fenster = HauptFenster()

    fenster._bei_explorer_doppelklick(_eintrag(datei), 0)
    erster_tab_anzahl = fenster.editor_tabs.count()
    fenster._bei_explorer_doppelklick(_eintrag(datei), 0)

    assert fenster.editor_tabs.count() == erster_tab_anzahl
