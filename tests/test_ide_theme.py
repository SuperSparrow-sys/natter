"""Tests für ide/shell/theme.py: QSS-Generator für das IDE-Hauptfenster
selbst (getrennt von pcl.theme, das nur Schülerprogramme einfärbt).
Gemeldet: die IDE wirkte insgesamt farblos/grau,
weil dafür bisher gar kein eigenes Stylesheet existierte.
"""

import pytest
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QProgressBar,
    QWidget,
)

from ide.shell.theme import _tokens_laden, ide_qss_erzeugen


def test_qss_enthaelt_die_tokens_des_gewaehlten_themes() -> None:
    hell = ide_qss_erzeugen("light")
    dunkel = ide_qss_erzeugen("dark")

    assert "#ffffff" in hell  # color.light.bg
    assert "#1e1e1e" in dunkel  # color.dark.bg
    assert hell != dunkel


def test_qss_deckt_die_wichtigsten_ide_rahmen_widgets_ab() -> None:
    qss = ide_qss_erzeugen("light")
    for auswahl in (
        "QMenuBar",
        "QMenu",
        "QToolBar",
        "QDockWidget",
        "QTabBar::tab",
        "QTreeWidget",
        "QStatusBar",
        "QScrollBar",
    ):
        assert auswahl in qss, f"{auswahl} fehlt im IDE-Stylesheet"


def test_qss_verwendet_die_akzentfarbe_fuer_ausgewaehlte_elemente() -> None:
    hell = ide_qss_erzeugen("light")
    dunkel = ide_qss_erzeugen("dark")

    assert hell.count("#0067c0") >= 3  # color.light.accent
    assert dunkel.count("#4cc2ff") >= 3  # color.dark.accent


def test_im_dunklen_thema_steht_keine_weisse_schrift_fest() -> None:
    """Weiß auf der Akzentfarbe ist die Voreinstellung für einen Knopf
 mit Akzent-Hintergrund - im hellen Thema stimmt das, weil `bg`
 ohnehin weiß ist. Im dunklen Thema ist der Akzent ein helles Blau
 (#4cc2ff), und weiße Schrift darauf ist kaum zu lesen.

 `pcl/theme` nimmt an denselben Stellen seit jeher `bg` statt einer
 festen Farbe; das IDE-Stylesheet zieht nach (Rückmeldung
 zum Hover: „die schrift darf nicht weis werden").
 """
    assert "#ffffff" not in ide_qss_erzeugen("dark").lower()


@pytest.mark.parametrize("thema", ["light", "dark"])
def test_die_ladeanzeige_steht_ohne_eigenen_kasten_in_der_statusleiste(
    qtbot, thema: str,  # noqa: ANN001
) -> None:
    """Punkt 412: Behälter, Text und Balken der Ladeanzeige bekamen
 über die allgemeine QWidget-Regel die Grundfarbe des Fensters und
 standen als heller Kasten in der grauen Statusleiste."""
    fenster = QMainWindow()
    qtbot.addWidget(fenster)
    fenster.setStyleSheet(ide_qss_erzeugen(thema))
    fenster.setCentralWidget(QWidget())
    anzeige = QWidget()
    zeile = QHBoxLayout(anzeige)
    zeile.setContentsMargins(0, 0, 0, 0)
    balken = QProgressBar()
    balken.setRange(0, 0)
    balken.setMaximumWidth(120)
    balken.setMaximumHeight(14)
    balken.setTextVisible(False)
    text = QLabel("Programm wird geladen … 15 s")
    zeile.addWidget(balken)
    zeile.addWidget(text)
    leiste = fenster.statusBar()
    leiste.addPermanentWidget(anzeige)
    fenster.resize(600, 200)
    fenster.show()
    qtbot.waitExposed(fenster)
    # Die Leiste bekommt ihre Farbe erst nach dem ersten Zeichnen;
    # vorher ist alles hell, und der Vergleich bewiese nichts.
    flaeche = QColor(_tokens_laden()["color"][thema]["surface"])
    qtbot.waitUntil(
        lambda: leiste.grab().toImage().pixelColor(5, 11) == flaeche,
    )

    bild = leiste.grab().toImage()
    grund = bild.pixelColor(5, bild.height() // 2)
    # Die oberste Zeile über der Schrift, mitten im Text: rechts
    # davon liegt der Griff zum Ziehen der Fenstergröße.
    oben = text.mapTo(leiste, text.rect().center())
    im_text = bild.pixelColor(oben.x(), text.mapTo(leiste, text.rect().topLeft()).y())
    assert im_text == grund, (
        f"Hintergrund der Ladeanzeige {im_text.name()}, "
        f"Statusleiste {grund.name()}"
    )
