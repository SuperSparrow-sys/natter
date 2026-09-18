"""Tests für ide/diagramm/eigenschaften.py: Eigenschaften-Bereich
rechts im Diagramm-Fenster (M9, Schritt 6). Headless.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ide.diagramm import DiagrammFenster, diagramm_erzeugen
from ide.diagramm.stil import stil as stil_zu_namen
from ide.diagramm.zeichnen import fuellfarbe, randfarbe, schriftgroesse


@pytest.fixture
def fenster(tmp_path: Path) -> DiagrammFenster:
    return DiagrammFenster(diagramm_erzeugen("class", tmp_path / "k.pdiag", "k"))


def test_ohne_auswahl_steht_nur_ein_hinweis(fenster: DiagrammFenster) -> None:
    panel = fenster.eigenschaften

    assert panel.hinweis.text() == "Nichts ausgewählt"
    assert panel.formular.isVisibleTo(panel) is False


def test_ausgewaehlte_form_zeigt_geometrie_und_gestaltung(fenster: DiagrammFenster) -> None:
    form = fenster.zeichenflaeche.form_platzieren("class", 200, 200)
    panel = fenster.eigenschaften

    assert "Form:" in panel.hinweis.text()
    assert panel.felder["x"].value() == form["x"]
    assert panel.felder["w"].value() == form["w"]
    assert panel.schrift.value() == schriftgroesse(form)
    # ohne eigene Farbe steht die Stilvorlage da
    assert panel.fuellung.text() == "(Stilvorlage)"


def test_geometrie_im_panel_aendern_verschiebt_die_form(fenster: DiagrammFenster) -> None:
    form = fenster.zeichenflaeche.form_platzieren("class", 200, 200)

    fenster.eigenschaften.felder["x"].setValue(320)

    assert form["x"] == 320


def test_aenderung_im_panel_ist_rueckgaengig_machbar(fenster: DiagrammFenster) -> None:
    form = fenster.zeichenflaeche.form_platzieren("class", 200, 200)
    vorher = form["x"]

    fenster.eigenschaften.felder["x"].setValue(320)
    fenster.zeichenflaeche.rueckgaengig()

    assert form["x"] == vorher


def test_eigene_farbe_gewinnt_gegen_die_stilvorlage(fenster: DiagrammFenster) -> None:
    form = fenster.zeichenflaeche.form_platzieren("class", 200, 200)
    stil = stil_zu_namen(fenster.diagramm.stil)
    assert fuellfarbe(form, stil) == stil.fuellung

    fenster.eigenschaften._anwenden(form, {"fill": "#ffe0b2", "line": "#bf360c"})

    assert fuellfarbe(form, stil) == "#ffe0b2"
    assert randfarbe(form, stil) == "#bf360c"


def test_schriftgroesse_im_panel_wirkt_auf_die_form(fenster: DiagrammFenster) -> None:
    form = fenster.zeichenflaeche.form_platzieren("class", 200, 200)

    fenster.eigenschaften.schrift.setValue(14)

    assert schriftgroesse(form) == 14


def test_ausgewaehlte_verbindung_zeigt_ihre_beschriftungen(fenster: DiagrammFenster) -> None:
    flaeche = fenster.zeichenflaeche
    quelle = flaeche.form_platzieren("class", 160, 160)
    ziel = flaeche.form_platzieren("class", 520, 160)
    verbindung = flaeche.verbindung_erstellen("composition", quelle, ziel)
    verbindung["labels"] = {"from": "1", "to": "3"}
    fenster.eigenschaften.aktualisieren()

    panel = fenster.eigenschaften
    assert "composition" in panel.hinweis.text()
    assert panel.beschriftung_von.text() == "1"
    assert panel.beschriftung_zu.text() == "3"
    # Geometriefelder gehören zu Formen und sind hier ausgeblendet
    assert panel.felder["x"].isVisibleTo(panel) is False


def test_beschriftung_im_panel_aendern_wirkt_auf_die_verbindung(
    fenster: DiagrammFenster,
) -> None:
    flaeche = fenster.zeichenflaeche
    quelle = flaeche.form_platzieren("class", 160, 160)
    ziel = flaeche.form_platzieren("class", 520, 160)
    verbindung = flaeche.verbindung_erstellen("association", quelle, ziel)
    fenster.eigenschaften.aktualisieren()

    fenster.eigenschaften.beschriftung_zu.setText("0..*")
    fenster.eigenschaften.beschriftung_zu.editingFinished.emit()

    assert verbindung["labels"]["to"] == "0..*"


def test_stil_uebertragen_kopiert_gestaltung_auf_die_zweite_form(
    fenster: DiagrammFenster,
) -> None:
    """Abschnitt 13.3: „Format einer Form auf andere übernehmen“."""
    flaeche = fenster.zeichenflaeche
    vorlage = flaeche.form_platzieren("class", 160, 160)
    fenster.eigenschaften._anwenden(vorlage, {"fill": "#e8f5e9", "font_size": 12})
    ziel = flaeche.form_platzieren("class", 520, 160)

    # erster Aufruf merkt die Vorlage (Auswahl liegt auf `ziel`), deshalb
    # explizit die Vorlage auswählen
    flaeche._auswaehlen(vorlage)
    fenster._stil_uebertragen()
    flaeche._auswaehlen(ziel)
    fenster._stil_uebertragen()

    assert ziel["fill"] == "#e8f5e9"
    assert ziel["font_size"] == 12


def test_stil_uebertragen_ohne_auswahl_meldet_das(fenster: DiagrammFenster) -> None:
    fenster._stil_uebertragen()

    assert "Keine Form ausgewählt" in fenster.statusBar().currentMessage()
