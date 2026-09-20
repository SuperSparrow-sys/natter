"""Tests für Knickpunkte und verschiebbare Beschriftungen an
Verbindungen (M9, Teilschritt 4b). Headless.

Gezeichnet und gespeichert wurden Knickpunkte schon seit Schritt 4 –
hier geht es um das interaktive Setzen, Verschieben und Entfernen.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent

from ide.diagramm import DiagrammFenster, diagramm_erzeugen
from ide.diagramm.canvas import DiagrammCanvas
from ide.diagramm.zeichnen import beschriftungs_rechtecke, segment_bei


@pytest.fixture
def flaeche(tmp_path: Path) -> DiagrammCanvas:
    fenster = DiagrammFenster(diagramm_erzeugen("class", tmp_path / "k.pdiag", "k"))
    return fenster.zeichenflaeche


@pytest.fixture
def verbindung(flaeche: DiagrammCanvas) -> dict:
    """Zwei Klassen weit auseinander, damit zwischen ihnen wirklich
    Linie liegt, auf die man klicken kann."""
    quelle = flaeche.form_platzieren("class", 200, 200)
    ziel = flaeche.form_platzieren("class", 800, 200)
    flaeche.auswahl_aufheben()
    return flaeche.verbindung_erstellen("association", quelle, ziel)


def _maus(x: float, y: float, typ) -> QMouseEvent:
    return QMouseEvent(
        typ,
        QPointF(x, y),
        QPointF(x, y),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )


def _linienmitte(flaeche: DiagrammCanvas, verbindung: dict) -> tuple[float, float]:
    quelle = flaeche.form_mit_id(verbindung["from"])
    ziel = flaeche.form_mit_id(verbindung["to"])
    return (
        (quelle["x"] + quelle["w"] + ziel["x"]) / 2,
        quelle["y"] + quelle["h"] / 2,
    )


# -- Knickpunkt setzen ---------------------------------------------------


def test_doppelklick_auf_die_linie_setzt_einen_knickpunkt(
    flaeche: DiagrammCanvas, verbindung: dict
) -> None:
    x, y = _linienmitte(flaeche, verbindung)

    flaeche.mouseDoubleClickEvent(_maus(x, y, QEvent.Type.MouseButtonDblClick))

    assert len(verbindung.get("waypoints") or []) == 1


def test_der_knickpunkt_liegt_am_raster(flaeche: DiagrammCanvas, verbindung: dict) -> None:
    """Wie alles andere im Editor – sonst bekäme man krumme Linien, die
    sich nicht mit den Formen ausrichten lassen."""
    x, y = _linienmitte(flaeche, verbindung)

    flaeche.mouseDoubleClickEvent(_maus(x + 3, y + 3, QEvent.Type.MouseButtonDblClick))

    knick = verbindung["waypoints"][0]
    assert knick[0] % 8 == 0 and knick[1] % 8 == 0


def test_doppelklick_auf_den_knickpunkt_nimmt_ihn_weg(
    flaeche: DiagrammCanvas, verbindung: dict
) -> None:
    x, y = _linienmitte(flaeche, verbindung)
    flaeche.mouseDoubleClickEvent(_maus(x, y, QEvent.Type.MouseButtonDblClick))
    knick_x, knick_y = verbindung["waypoints"][0]

    flaeche.mouseDoubleClickEvent(_maus(knick_x, knick_y, QEvent.Type.MouseButtonDblClick))

    assert verbindung["waypoints"] == []


def test_setzen_laesst_sich_zuruecknehmen(flaeche: DiagrammCanvas, verbindung: dict) -> None:
    x, y = _linienmitte(flaeche, verbindung)
    flaeche.mouseDoubleClickEvent(_maus(x, y, QEvent.Type.MouseButtonDblClick))

    flaeche.rueckgaengig()

    assert not verbindung.get("waypoints")


def test_die_verbindung_ist_danach_ausgewaehlt(flaeche: DiagrammCanvas, verbindung: dict) -> None:
    """Sonst sähe man die neuen Knickpunkte gar nicht – sie werden nur
    an der ausgewählten Verbindung gezeichnet."""
    x, y = _linienmitte(flaeche, verbindung)

    flaeche.mouseDoubleClickEvent(_maus(x, y, QEvent.Type.MouseButtonDblClick))

    assert flaeche.ausgewaehlte_verbindung is verbindung


def test_neuer_knick_landet_im_angeklickten_linienstueck(
    flaeche: DiagrammCanvas, verbindung: dict
) -> None:
    """Der eigentliche Knackpunkt: immer ans Ende zu hängen wäre bei
    einer schon geknickten Linie ein Sprung quer durchs Diagramm."""
    verbindung["waypoints"] = [[500, 500]]
    quelle = flaeche.form_mit_id(verbindung["from"])
    # Ein Punkt nahe dem ersten Stück (Quelle → Knick)
    nah_am_anfang = QPointF(quelle["x"] + quelle["w"] + 20, quelle["y"] + 60)

    assert (
        segment_bei(nah_am_anfang, verbindung, quelle, flaeche.form_mit_id(verbindung["to"])) == 0
    )

    flaeche.knickpunkt_setzen(verbindung, nah_am_anfang.toPoint())

    assert verbindung["waypoints"][1] == [500, 500]


def test_knickpunkt_entfernen_mit_falscher_nummer(
    flaeche: DiagrammCanvas, verbindung: dict
) -> None:
    assert flaeche.knickpunkt_entfernen(verbindung, 5) is False


# -- Knickpunkt ziehen ---------------------------------------------------


def test_knickpunkt_laesst_sich_ziehen(flaeche: DiagrammCanvas, verbindung: dict) -> None:
    verbindung["waypoints"] = [[500, 400]]
    flaeche._verbindung_auswaehlen(verbindung)

    flaeche.mousePressEvent(_maus(500, 400, QEvent.Type.MouseButtonPress))
    flaeche.mouseMoveEvent(_maus(560, 480, QEvent.Type.MouseMove))
    flaeche.mouseReleaseEvent(_maus(560, 480, QEvent.Type.MouseButtonRelease))

    assert verbindung["waypoints"] == [[560, 480]]


def test_ziehen_ist_ein_undo_schritt(flaeche: DiagrammCanvas, verbindung: dict) -> None:
    """Die Live-Vorschau verändert die Linie laufend – trotzdem soll ein
    einziges Strg+Z den ganzen Zug zurücknehmen."""
    verbindung["waypoints"] = [[500, 400]]
    flaeche._verbindung_auswaehlen(verbindung)
    flaeche.mousePressEvent(_maus(500, 400, QEvent.Type.MouseButtonPress))
    flaeche.mouseMoveEvent(_maus(520, 420, QEvent.Type.MouseMove))
    flaeche.mouseMoveEvent(_maus(560, 480, QEvent.Type.MouseMove))
    flaeche.mouseReleaseEvent(_maus(560, 480, QEvent.Type.MouseButtonRelease))

    flaeche.rueckgaengig()

    assert verbindung["waypoints"] == [[500, 400]]


def test_ein_knickpunkt_ohne_ausgewaehlte_verbindung_wird_nicht_gegriffen(
    flaeche: DiagrammCanvas, verbindung: dict
) -> None:
    """Er wird dann auch nicht gezeichnet – man würde ins Blaue
    greifen."""
    verbindung["waypoints"] = [[500, 400]]
    flaeche.auswahl_aufheben()

    flaeche.mousePressEvent(_maus(500, 400, QEvent.Type.MouseButtonPress))

    assert flaeche._zieh_knick is None


def test_die_linie_geht_wirklich_ueber_den_knickpunkt(
    flaeche: DiagrammCanvas, verbindung: dict
) -> None:
    """Gegenprobe zum Ziehen: ein gesetzter Knick muss die Linienführung
    auch ändern, nicht nur in der Datei stehen."""
    from ide.diagramm.zeichnen import verbindungs_punkte

    quelle = flaeche.form_mit_id(verbindung["from"])
    ziel = flaeche.form_mit_id(verbindung["to"])
    vorher = verbindungs_punkte(verbindung, quelle, ziel)

    verbindung["waypoints"] = [[500, 500]]
    nachher = verbindungs_punkte(verbindung, quelle, ziel)

    assert len(nachher) == len(vorher) + 1
    assert (nachher[1].x(), nachher[1].y()) == (500, 500)


# -- Beschriftungen verschieben ------------------------------------------


def test_beschriftung_wird_getroffen(flaeche: DiagrammCanvas, verbindung: dict) -> None:
    verbindung["labels"] = {"from": "1", "to": "0..*"}
    quelle = flaeche.form_mit_id(verbindung["from"])
    ziel = flaeche.form_mit_id(verbindung["to"])
    rechteck = beschriftungs_rechtecke(verbindung, quelle, ziel)["to"]

    getroffen = flaeche.beschriftung_bei(rechteck.center().x(), rechteck.center().y())

    assert getroffen == (verbindung, "to")


def test_beschriftung_laesst_sich_verschieben(flaeche: DiagrammCanvas, verbindung: dict) -> None:
    verbindung["labels"] = {"from": "1", "to": "0..*"}
    quelle = flaeche.form_mit_id(verbindung["from"])
    ziel = flaeche.form_mit_id(verbindung["to"])
    mitte = beschriftungs_rechtecke(verbindung, quelle, ziel)["from"].center()

    flaeche.mousePressEvent(_maus(mitte.x(), mitte.y(), QEvent.Type.MouseButtonPress))
    flaeche.mouseMoveEvent(_maus(mitte.x() + 30, mitte.y() - 20, QEvent.Type.MouseMove))
    flaeche.mouseReleaseEvent(_maus(mitte.x() + 30, mitte.y() - 20, QEvent.Type.MouseButtonRelease))

    assert verbindung["label_offsets"]["from"] == [30, -20]


def test_verschobene_beschriftung_wird_auch_dort_gezeichnet(
    flaeche: DiagrammCanvas, verbindung: dict
) -> None:
    """Sonst würde sie woanders gezeichnet als angeklickt – deshalb
    rechnen Zeichnen und Treffer über dieselbe Funktion."""
    verbindung["labels"] = {"from": "1"}
    quelle = flaeche.form_mit_id(verbindung["from"])
    ziel = flaeche.form_mit_id(verbindung["to"])
    vorher = beschriftungs_rechtecke(verbindung, quelle, ziel)["from"].center()

    verbindung["label_offsets"] = {"from": [40, -25]}
    nachher = beschriftungs_rechtecke(verbindung, quelle, ziel)["from"].center()

    assert nachher.x() - vorher.x() == pytest.approx(40)
    assert nachher.y() - vorher.y() == pytest.approx(-25)


def test_verschieben_ist_ein_undo_schritt(flaeche: DiagrammCanvas, verbindung: dict) -> None:
    verbindung["labels"] = {"from": "1"}
    quelle = flaeche.form_mit_id(verbindung["from"])
    ziel = flaeche.form_mit_id(verbindung["to"])
    mitte = beschriftungs_rechtecke(verbindung, quelle, ziel)["from"].center()
    flaeche.mousePressEvent(_maus(mitte.x(), mitte.y(), QEvent.Type.MouseButtonPress))
    flaeche.mouseMoveEvent(_maus(mitte.x() + 30, mitte.y(), QEvent.Type.MouseMove))
    flaeche.mouseReleaseEvent(_maus(mitte.x() + 30, mitte.y(), QEvent.Type.MouseButtonRelease))

    flaeche.rueckgaengig()

    assert (verbindung.get("label_offsets") or {}).get("from", [0, 0]) == [0, 0]


def test_leere_beschriftung_wird_nicht_getroffen(flaeche: DiagrammCanvas, verbindung: dict) -> None:
    """Ein unsichtbares Textfeld im Weg wäre ein Rätsel."""
    verbindung["labels"] = {"from": "", "to": ""}

    assert flaeche.beschriftung_bei(400, 264) is None


# -- Speichern und Laden -------------------------------------------------


def test_knickpunkte_und_versatz_ueberleben_das_speichern(tmp_path: Path) -> None:
    from ide.diagramm.datei import Diagramm

    pfad = tmp_path / "s.pdiag"
    fenster = DiagrammFenster(diagramm_erzeugen("class", pfad, "s"))
    flaeche = fenster.zeichenflaeche
    quelle = flaeche.form_platzieren("class", 200, 200)
    ziel = flaeche.form_platzieren("class", 800, 200)
    strich = flaeche.verbindung_erstellen("association", quelle, ziel)
    strich["waypoints"] = [[500, 400]]
    strich["labels"] = {"from": "1"}
    strich["label_offsets"] = {"from": [12, -8]}
    fenster.speichern()

    geladen = Diagramm.laden(pfad)

    wieder = geladen.daten["connectors"][0]
    assert wieder["waypoints"] == [[500, 400]]
    assert wieder["label_offsets"]["from"] == [12, -8]
