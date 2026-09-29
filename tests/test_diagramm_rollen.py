"""Tests für das Rollen (Scrollen) im Diagramm-Editor.

Vom Nutzer gemeldet: „scrollen horizontal und vertikal funktioniert
nicht im editor“. Die Zeichenflächen steckten in keinem Rollbereich und
hatten eine feste Mindestgröße von 640×480 – alles außerhalb des
Fensters war damit schlicht nicht erreichbar, obwohl ein A4-Blatt quer
schon 1123 px breit ist.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QScrollArea

from ide.diagramm import DiagrammFenster, diagramm_erzeugen
from ide.diagramm.bloecke import Einfuegestelle
from ide.diagramm.seite import seitengroesse


def _fenster(tmp_path: Path, typ: str) -> DiagrammFenster:
    return DiagrammFenster(diagramm_erzeugen(typ, tmp_path / f"{typ}.pdiag", typ))


@pytest.mark.parametrize("typ", ["class", "struktogramm", "entscheidungstabelle"])
def test_zeichenflaeche_steckt_in_einem_rollbereich(tmp_path: Path, typ: str) -> None:
    fenster = _fenster(tmp_path, typ)

    # Seit M15, Abschnitt 5 ist der Rollbereich nicht mehr selbst das
    # zentrale Widget: er steckt in einem Raster zusammen mit den
    # Linealen. Geprüft wird deshalb, dass er dort wirklich sitzt.
    assert fenster.rollbereich.parent() is not None
    assert isinstance(fenster.rollbereich, QScrollArea)
    assert fenster.rollbereich in fenster.centralWidget().findChildren(QScrollArea)
    assert fenster.rollbereich.widget() is fenster.zeichenflaeche
    # Ohne `widgetResizable` bliebe die Fläche auf ihrer Wunschgröße und
    # füllte ein großes Fenster nicht aus.
    assert fenster.rollbereich.widgetResizable() is True


def test_klassendiagramm_ist_mindestens_so_gross_wie_das_blatt(tmp_path: Path) -> None:
    fenster = _fenster(tmp_path, "class")
    breite, hoehe = seitengroesse(fenster.diagramm.daten["page"])

    groesse = fenster.zeichenflaeche.minimumSize()

    assert groesse.width() >= breite
    assert groesse.height() >= hoehe


def test_flaeche_waechst_mit_einer_form_ausserhalb_des_blatts(tmp_path: Path) -> None:
    """Eine Form neben dem Blatt muss erreichbar bleiben – sonst wäre sie
    nach dem Verschieben verloren."""
    fenster = _fenster(tmp_path, "class")
    vorher = fenster.zeichenflaeche.minimumSize().width()

    fenster.zeichenflaeche.form_platzieren("class", 2400, 300)

    assert fenster.zeichenflaeche.minimumSize().width() > vorher


def test_struktogramm_flaeche_waechst_mit_den_bloecken(tmp_path: Path) -> None:
    fenster = _fenster(tmp_path, "struktogramm")
    flaeche = fenster.zeichenflaeche
    vorher = flaeche.minimumSize().height()

    for _ in range(12):
        flaeche.block_einfuegen(
            "statement", Einfuegestelle(flaeche.wurzel, "children", 999)
        )

    assert flaeche.minimumSize().height() > vorher


def test_tabellenflaeche_waechst_mit_den_regeln(tmp_path: Path) -> None:
    fenster = _fenster(tmp_path, "entscheidungstabelle")
    flaeche = fenster.zeichenflaeche
    vorher = flaeche.minimumSize().width()

    for _ in range(10):
        flaeche.regel_hinzufuegen()

    assert flaeche.minimumSize().width() > vorher


def test_in_einem_kleinen_fenster_laesst_sich_wirklich_rollen(tmp_path: Path) -> None:
    """Der eigentlich gemeldete Fehler: im kleinen Fenster kam man nicht
    an den rechten und unteren Teil des Blatts."""
    fenster = _fenster(tmp_path, "class")
    fenster.zeichenflaeche.form_platzieren("class", 1000, 700)
    fenster.resize(700, 480)
    fenster.show()

    waagerecht = fenster.rollbereich.horizontalScrollBar()
    senkrecht = fenster.rollbereich.verticalScrollBar()
    assert waagerecht.maximum() > 0
    assert senkrecht.maximum() > 0

    waagerecht.setValue(waagerecht.maximum())
    senkrecht.setValue(senkrecht.maximum())

    assert waagerecht.value() == waagerecht.maximum()
    assert senkrecht.value() == senkrecht.maximum()


def test_kleines_diagramm_braucht_keine_rollbalken(tmp_path: Path) -> None:
    """Umgekehrt soll ein großes Fenster nicht grundlos Rollbalken
    zeigen."""
    fenster = _fenster(tmp_path, "entscheidungstabelle")
    fenster.resize(1400, 900)
    fenster.show()

    assert fenster.rollbereich.horizontalScrollBar().maximum() == 0
    assert fenster.rollbereich.verticalScrollBar().maximum() == 0
