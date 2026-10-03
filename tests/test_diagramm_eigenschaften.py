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
    assert "Komposition" in panel.hinweis.text()
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


def test_feld_schrift_zeigt_und_nimmt_das_komma_auch_bei_englischem_format(
    tmp_path: Path,
) -> None:
    """Punkt 325: Qt übernimmt das Zahlenformat aus der
    Windows-Einstellung „Region“. Nachgestellt wird ein englisches
    Format über `QLocale.setDefault`, wie es Qt beim Start aus Windows
    setzt."""
    from PySide6.QtCore import QLocale
    from PySide6.QtGui import QValidator

    from ide.deutsch import deutsch_einschalten

    vorher = QLocale()
    englisch = QLocale(QLocale.Language.English, QLocale.Country.UnitedStates)
    try:
        QLocale.setDefault(englisch)
        # Das Panel selbst, ohne den Start der IDE ...
        fenster = DiagrammFenster(
            diagramm_erzeugen("class", tmp_path / "k.pdiag", "k")
        )
        fenster.zeichenflaeche.form_platzieren("class", 200, 200)
        feld = fenster.eigenschaften.schrift
        feld.setValue(10.5)
        assert feld.text() == "10,50 pt"
        assert feld.validate("11,5 pt", 5)[0] == QValidator.State.Acceptable
        fenster.close()

        # ... und der Start stellt Deutsch für alle Felder der IDE ein.
        QLocale.setDefault(englisch)
        deutsch_einschalten()
        assert QLocale().decimalPoint() == ","
    finally:
        QLocale.setDefault(vorher)


def test_bei_einer_klasse_fuehrt_ein_knopf_zu_den_attributen(
    fenster: DiagrammFenster, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Punkt 496: das Panel zeigte bei einer Klasse nur Lage und
    Farben; zu Attributen und Operationen führte nur der Doppelklick.
    Bei einer Notiz gibt es den Knopf nicht."""
    flaeche = fenster.zeichenflaeche
    panel = fenster.eigenschaften
    geoeffnet: list[object] = []
    monkeypatch.setattr(
        flaeche, "eigenschaften_bearbeiten", lambda form=None: geoeffnet.append(form)
    )

    flaeche.form_platzieren("note", 400, 400)
    panel.aktualisieren()
    assert panel.klasse_bearbeiten.isHidden()

    flaeche.form_platzieren("class", 200, 200)
    panel.aktualisieren()
    assert not panel.klasse_bearbeiten.isHidden()
    panel.klasse_bearbeiten.click()
    assert len(geoeffnet) == 1
