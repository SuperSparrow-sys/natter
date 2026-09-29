"""Eigene Farbe, Schriftgröße und verschobene Beschriftung zurücksetzen
(Punkt 71 der offenen Punkte).

Dazu zwei Fehler, die beim Nachsehen auffielen: „Rückgängig“ nach der
ersten eigenen Farbe schrieb `"fill": null` in die Form. Das Panel
fragte `"fill" in form` und zeigte die Farbe deshalb weiter als eigene
an, und `speichern()` scheiterte an der Schema-Prüfung. Genauso nach
dem ersten Knickpunkt einer Verbindung (`"waypoints": null`).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QPoint
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QColorDialog

from ide.diagramm import DiagrammFenster, diagramm_erzeugen
from ide.diagramm.datei import Diagramm
from ide.diagramm.kommandos import WerteKommando


@pytest.fixture
def fenster(qtbot, tmp_path: Path) -> DiagrammFenster:  # noqa: ANN001
    return DiagrammFenster(diagramm_erzeugen("class", tmp_path / "k.pdiag", "k"))


def _farbe_waehlen(monkeypatch: pytest.MonkeyPatch, farbe: str) -> None:
    monkeypatch.setattr(
        QColorDialog, "getColor", staticmethod(lambda *a, **k: QColor(farbe))
    )


def test_rueckgaengig_nach_der_ersten_farbe_laesst_kein_null_zurueck(
    fenster: DiagrammFenster, monkeypatch: pytest.MonkeyPatch
) -> None:
    form = fenster.zeichenflaeche.form_platzieren("class", 200, 200)
    panel = fenster.eigenschaften
    _farbe_waehlen(monkeypatch, "#ff0000")
    panel.fuellung.click()
    assert form["fill"] == "#ff0000"

    fenster.zeichenflaeche.rueckgaengig()

    assert "fill" not in form
    assert panel.fuellung.text() == "(Stilvorlage)"
    fenster.speichern()
    Diagramm.laden(fenster.diagramm.pfad)


def test_zuruecksetzen_nimmt_farben_und_schrift_weg(
    fenster: DiagrammFenster, monkeypatch: pytest.MonkeyPatch
) -> None:
    form = fenster.zeichenflaeche.form_platzieren("class", 200, 200)
    panel = fenster.eigenschaften
    assert not panel.stil_zuruecksetzen.isEnabled()

    _farbe_waehlen(monkeypatch, "#00ff00")
    panel.fuellung.click()
    panel.linie.click()
    panel.schrift.setValue(14)
    assert panel.stil_zuruecksetzen.isEnabled()

    panel.stil_zuruecksetzen.click()

    assert not {"fill", "line", "font_size"} & form.keys()
    assert panel.fuellung.text() == "(Stilvorlage)"
    assert panel.linie.text() == "(Stilvorlage)"
    assert not panel.stil_zuruecksetzen.isEnabled()

    # Ein einziger Schritt für „Rückgängig“
    fenster.zeichenflaeche.rueckgaengig()
    assert (form["fill"], form["line"], form["font_size"]) == ("#00ff00", "#00ff00", 14)


def test_alte_form_mit_null_gilt_als_stilvorlage(fenster: DiagrammFenster) -> None:
    form = fenster.zeichenflaeche.form_platzieren("class", 200, 200)
    form["fill"] = None

    fenster.eigenschaften.aktualisieren()

    assert fenster.eigenschaften.fuellung.text() == "(Stilvorlage)"


def _verbindung(fenster: DiagrammFenster) -> dict:
    flaeche = fenster.zeichenflaeche
    a = flaeche.form_platzieren("class", 200, 200)
    b = flaeche.form_platzieren("class", 600, 200)
    return flaeche.verbindung_erstellen("association", a, b)


def test_verschobene_beschriftung_zurueck_an_ihren_platz(
    fenster: DiagrammFenster,
) -> None:
    verbindung = _verbindung(fenster)
    panel = fenster.eigenschaften
    panel.beschriftung_von.setText("1")
    panel.beschriftung_von.editingFinished.emit()
    fenster.zeichenflaeche.kommandos.ausfuehren(
        WerteKommando(verbindung, {"label_offsets": {"from": [30, -12]}})
    )
    panel.aktualisieren()
    assert panel.lage_zuruecksetzen.isEnabled()

    panel.lage_zuruecksetzen.click()

    assert "label_offsets" not in verbindung
    assert verbindung["labels"] == {"from": "1"}
    assert not panel.lage_zuruecksetzen.isEnabled()
    fenster.zeichenflaeche.rueckgaengig()
    assert verbindung["label_offsets"] == {"from": [30, -12]}


def test_rueckgaengig_nach_dem_ersten_knickpunkt_bleibt_speicherbar(
    fenster: DiagrammFenster,
) -> None:
    verbindung = _verbindung(fenster)
    flaeche = fenster.zeichenflaeche

    flaeche.knickpunkt_setzen(verbindung, QPoint(400, 300))
    flaeche.rueckgaengig()

    assert "waypoints" not in verbindung
    fenster.speichern()
    Diagramm.laden(fenster.diagramm.pfad)
