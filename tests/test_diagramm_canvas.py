"""Tests für ide/diagramm/canvas.py: Formen platzieren und auswählen
(M9, Schritt 2). Headless.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent

from ide.diagramm import diagramm_erzeugen
from ide.diagramm.canvas import RASTER, DiagrammCanvas


@pytest.fixture
def canvas(tmp_path: Path) -> DiagrammCanvas:
    return DiagrammCanvas(diagramm_erzeugen("class", tmp_path / "k.pdiag", "k"))


def _klick(x: float, y: float) -> QMouseEvent:
    return QMouseEvent(
        QEvent.Type.MouseButtonPress,
        QPointF(x, y),
        QPointF(x, y),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )


def test_platzierte_form_landet_mittig_unter_dem_klick_am_raster(canvas: DiagrammCanvas) -> None:
    form = canvas.form_platzieren("class", 300, 200)

    # Klickpunkt ist die Mitte, Kanten rasten am 8-px-Raster ein
    assert form["x"] == 300 - form["w"] / 2
    assert form["y"] % RASTER == 0
    assert form["x"] % RASTER == 0


def test_platzieren_vergibt_eindeutige_ids(canvas: DiagrammCanvas) -> None:
    erste = canvas.form_platzieren("class", 100, 100)
    zweite = canvas.form_platzieren("class", 300, 100)

    assert erste["id"] != zweite["id"]
    assert len(canvas.formen) == 2


def test_abstrakte_klasse_wird_als_abstrakt_markiert(canvas: DiagrammCanvas) -> None:
    form = canvas.form_platzieren("abstract_class", 100, 100)

    assert form["abstract"] is True


def test_platzierte_form_ist_hoch_genug_fuer_ihren_inhalt(canvas: DiagrammCanvas) -> None:
    """Abschnitt 13.6: „automatische Mindestgröße, damit Text nie
    abgeschnitten wird“."""
    form = canvas.form_platzieren("class", 200, 200)

    assert form["h"] >= 72


def test_hoehe_waechst_mit_dem_text_mit(canvas: DiagrammCanvas) -> None:
    """Real im Screenshot aufgefallen: ein Interface mit zwei Methoden
    und ohne Attribute schnitt die letzte Methode ab, weil Attribut- und
    Methodenbereich zusammen statt getrennt gerechnet wurden."""
    form = canvas.form_platzieren("interface", 200, 200)
    vorher = form["h"]

    form["text"] = {"name": "ISchaltbar", "attributes": [], "methods": ["+ein()", "+aus()"]}
    canvas.hoehe_anpassen(form)

    from ide.diagramm.zeichnen import mindesthoehe

    assert form["h"] >= mindesthoehe(form)
    assert form["h"] > vorher


def test_hoehe_anpassen_verkleinert_nicht(canvas: DiagrammCanvas) -> None:
    form = canvas.form_platzieren("class", 200, 200)
    form["h"] = 400

    canvas.hoehe_anpassen(form)

    assert form["h"] == 400


def test_klick_auf_die_flaeche_platziert_die_scharfe_form(canvas: DiagrammCanvas) -> None:
    canvas.platzierungsmodus_setzen("class")

    canvas.mousePressEvent(_klick(200, 160))

    assert len(canvas.formen) == 1
    assert canvas.formen[0]["kind"] == "class"


def test_platzierungsmodus_endet_nach_einem_klick(canvas: DiagrammCanvas) -> None:
    canvas.platzierungsmodus_setzen("class")
    canvas.mousePressEvent(_klick(200, 160))

    canvas.mousePressEvent(_klick(400, 300))

    assert len(canvas.formen) == 1


def test_klick_auf_eine_form_waehlt_sie_aus(canvas: DiagrammCanvas) -> None:
    form = canvas.form_platzieren("class", 200, 200)
    canvas.auswahl_aufheben()

    canvas.mousePressEvent(_klick(200, 200))

    assert canvas.ausgewaehlte_form is form


def test_klick_ins_leere_hebt_die_auswahl_auf(canvas: DiagrammCanvas) -> None:
    canvas.form_platzieren("class", 200, 200)

    canvas.mousePressEvent(_klick(600, 450))

    assert canvas.ausgewaehlte_form is None


def test_bei_ueberlappung_gewinnt_die_obere_form(canvas: DiagrammCanvas) -> None:
    canvas.form_platzieren("class", 200, 200)
    obere = canvas.form_platzieren("class", 210, 205)

    assert canvas.form_bei(205, 202) is obere


def test_platzieren_meldet_eine_aenderung(canvas: DiagrammCanvas, qtbot=None) -> None:
    meldungen = []
    canvas.geaendert.connect(lambda: meldungen.append(True))

    canvas.form_platzieren("class", 100, 100)

    assert meldungen == [True]


def test_auswahl_meldet_die_gewaehlte_form(canvas: DiagrammCanvas) -> None:
    gemeldet = []
    canvas.auswahl_geaendert.connect(gemeldet.append)

    form = canvas.form_platzieren("class", 100, 100)

    assert gemeldet == [form]


def test_unbekannte_formart_wird_abgelehnt(canvas: DiagrammCanvas) -> None:
    with pytest.raises(ValueError, match="Unbekannte Formart"):
        canvas.form_platzieren("gibt_es_nicht", 10, 10)
