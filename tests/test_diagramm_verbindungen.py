"""Tests für Verbindungen im Diagramm-Editor (M9, Schritt 4):
ide/diagramm/canvas.py, formen.py, zeichnen.py. Headless.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QImage, QKeyEvent, QMouseEvent, QPainter

from ide.diagramm import Diagramm, diagramm_erzeugen
from ide.diagramm.canvas import DiagrammCanvas
from ide.diagramm.formen import KLASSENDIAGRAMM_VERBINDUNGEN, verbindungs_art
from ide.diagramm.stil import MODERN_HELL
from ide.diagramm.zeichnen import (
    verbindung_zeichnen,
    verbindungs_punkte,
    verbindungsbeschriftungen_zeichnen,
)


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


def _zwei_klassen(canvas: DiagrammCanvas) -> tuple[dict, dict]:
    ganzes = canvas.form_platzieren("class", 160, 160)
    teil = canvas.form_platzieren("class", 520, 160)
    canvas.auswahl_aufheben()
    return ganzes, teil


def _mitte(form: dict) -> tuple[float, float]:
    return form["x"] + form["w"] / 2, form["y"] + form["h"] / 2


# -- Anlegen ---------------------------------------------------------------


def test_zwei_klicks_verbinden_quelle_und_ziel(canvas: DiagrammCanvas) -> None:
    ganzes, teil = _zwei_klassen(canvas)
    canvas.verbindungsmodus_setzen("composition")

    canvas.mousePressEvent(_klick(*_mitte(ganzes)))
    canvas.mousePressEvent(_klick(*_mitte(teil)))

    assert len(canvas.verbindungen) == 1
    verbindung = canvas.verbindungen[0]
    assert verbindung["kind"] == "composition"
    assert (verbindung["from"], verbindung["to"]) == (ganzes["id"], teil["id"])
    assert canvas.ausgewaehlte_verbindung is verbindung


def test_klick_ins_leere_bricht_das_verbinden_ab(canvas: DiagrammCanvas) -> None:
    ganzes, _ = _zwei_klassen(canvas)
    canvas.verbindungsmodus_setzen("association")

    canvas.mousePressEvent(_klick(*_mitte(ganzes)))
    canvas.mousePressEvent(_klick(620, 460))

    assert canvas.verbindungen == []
    assert canvas._verbindungs_kind is None


def test_form_laesst_sich_nicht_mit_sich_selbst_verbinden(canvas: DiagrammCanvas) -> None:
    ganzes, _ = _zwei_klassen(canvas)

    assert canvas.verbindung_erstellen("association", ganzes, ganzes) is None
    assert canvas.verbindungen == []


def test_verbindungs_ids_sind_eindeutig(canvas: DiagrammCanvas) -> None:
    ganzes, teil = _zwei_klassen(canvas)

    erste = canvas.verbindung_erstellen("association", ganzes, teil)
    zweite = canvas.verbindung_erstellen("inheritance", teil, ganzes)

    assert erste["id"] != zweite["id"]


def test_unbekannte_verbindungsart_wird_abgelehnt(canvas: DiagrammCanvas) -> None:
    ganzes, teil = _zwei_klassen(canvas)

    with pytest.raises(ValueError, match="Unbekannte Verbindungsart"):
        canvas.verbindung_erstellen("gibt_es_nicht", ganzes, teil)


def test_formplatzierung_beendet_den_verbindungsmodus(canvas: DiagrammCanvas) -> None:
    canvas.verbindungsmodus_setzen("association")

    canvas.platzierungsmodus_setzen("class")

    assert canvas._verbindungs_kind is None


def test_escape_bricht_das_verbinden_ab(canvas: DiagrammCanvas) -> None:
    canvas.verbindungsmodus_setzen("association")

    canvas.keyPressEvent(
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
    )

    assert canvas._verbindungs_kind is None


# -- Folgen, Auswählen, Löschen --------------------------------------------


def test_verbindung_folgt_beim_verschieben_der_form(canvas: DiagrammCanvas) -> None:
    """Abschnitt 13.3: Enden docken an und folgen beim Verschieben."""
    ganzes, teil = _zwei_klassen(canvas)
    verbindung = canvas.verbindung_erstellen("association", ganzes, teil)
    vorher = verbindungs_punkte(verbindung, ganzes, teil)[-1]

    canvas.verschieben(0, 200, teil)

    nachher = verbindungs_punkte(verbindung, ganzes, teil)[-1]
    assert nachher.y() > vorher.y()


def test_linie_endet_am_formrand_nicht_in_der_mitte(canvas: DiagrammCanvas) -> None:
    ganzes, teil = _zwei_klassen(canvas)
    verbindung = canvas.verbindung_erstellen("association", ganzes, teil)

    start, ende = verbindungs_punkte(verbindung, ganzes, teil)

    # nebeneinander liegende Klassen: Start an der rechten Kante der
    # Quelle, Ende an der linken Kante des Ziels
    assert start.x() == pytest.approx(ganzes["x"] + ganzes["w"])
    assert ende.x() == pytest.approx(teil["x"])


def test_klick_auf_die_linie_waehlt_die_verbindung_aus(canvas: DiagrammCanvas) -> None:
    ganzes, teil = _zwei_klassen(canvas)
    verbindung = canvas.verbindung_erstellen("association", ganzes, teil)
    canvas.auswahl_aufheben()
    start, ende = verbindungs_punkte(verbindung, ganzes, teil)

    canvas.mousePressEvent(_klick((start.x() + ende.x()) / 2, (start.y() + ende.y()) / 2 + 3))

    assert canvas.ausgewaehlte_verbindung is verbindung
    assert canvas.ausgewaehlte_form is None


def test_entf_loescht_die_ausgewaehlte_verbindung(canvas: DiagrammCanvas) -> None:
    ganzes, teil = _zwei_klassen(canvas)
    canvas.verbindung_erstellen("association", ganzes, teil)

    canvas.loeschen()

    assert canvas.verbindungen == []
    assert len(canvas.formen) == 2


def test_form_loeschen_nimmt_ihre_verbindungen_mit(canvas: DiagrammCanvas) -> None:
    """Sonst blieben Verbindungen mit Verweisen auf eine nicht mehr
    vorhandene Form in der .pdiag zurück."""
    ganzes, teil = _zwei_klassen(canvas)
    dritte = canvas.form_platzieren("class", 160, 420)
    canvas.verbindung_erstellen("association", ganzes, teil)
    bleibt = canvas.verbindung_erstellen("association", ganzes, dritte)

    canvas.loeschen(teil)

    assert canvas.verbindungen == [bleibt]


def test_form_loeschen_mit_verbindungen_ist_ein_undo_schritt(canvas: DiagrammCanvas) -> None:
    ganzes, teil = _zwei_klassen(canvas)
    verbindung = canvas.verbindung_erstellen("composition", ganzes, teil)

    canvas.loeschen(teil)
    canvas.rueckgaengig()

    assert teil in canvas.formen
    assert canvas.verbindungen == [verbindung]


def test_verbindung_anlegen_ist_rueckgaengig_machbar(canvas: DiagrammCanvas) -> None:
    ganzes, teil = _zwei_klassen(canvas)
    canvas.verbindung_erstellen("association", ganzes, teil)

    canvas.rueckgaengig()

    assert canvas.verbindungen == []


def test_verbindung_wird_gespeichert_und_wieder_geladen(canvas: DiagrammCanvas) -> None:
    ganzes, teil = _zwei_klassen(canvas)
    verbindung = canvas.verbindung_erstellen("inheritance", teil, ganzes)
    verbindung["labels"] = {"from": "1", "to": "*"}
    canvas.diagramm.speichern()

    geladen = Diagramm.laden(canvas.diagramm.pfad)

    assert geladen.daten["connectors"] == [verbindung]


# -- Zeichnen --------------------------------------------------------------


@pytest.mark.parametrize("art", KLASSENDIAGRAMM_VERBINDUNGEN, ids=lambda art: art.kind)
def test_jede_verbindungsart_zeichnet_ohne_fehler_etwas_sichtbares(art) -> None:
    quelle = {"id": "a", "kind": "class", "x": 20, "y": 40, "w": 80, "h": 60}
    ziel = {"id": "b", "kind": "class", "x": 220, "y": 40, "w": 80, "h": 60}
    verbindung = {"id": "c", "kind": art.kind, "from": "a", "to": "b",
                  "labels": {"from": "1", "to": "*"}}
    bild = QImage(320, 140, QImage.Format.Format_ARGB32)
    bild.fill(0)

    maler = QPainter(bild)
    verbindung_zeichnen(maler, verbindung, quelle, ziel, MODERN_HELL)
    maler.end()

    # Mitte der Linie liegt zwischen den Formen und muss eingefärbt sein
    assert bild.pixelColor(160, 70).alpha() > 0


@pytest.mark.parametrize("kind", ["association", "composition"])
def test_beschriftung_steht_ausserhalb_der_form_und_frei_von_der_raute(kind: str) -> None:
    """Real im Screenshot aufgefallen: die Beschriftung lag halb in der
    Zielform und wurde von ihr überdeckt („0..*“ erschien als „0..“),
    an der Komposition saß sie unter der Raute."""
    quelle = {"id": "a", "kind": "class", "x": 20, "y": 40, "w": 100, "h": 60}
    ziel = {"id": "b", "kind": "class", "x": 260, "y": 40, "w": 100, "h": 60}
    verbindung = {"id": "c", "kind": kind, "from": "a", "to": "b",
                  "labels": {"from": "1", "to": "0..*"}}
    bild = QImage(400, 140, QImage.Format.Format_ARGB32)
    bild.fill(0)

    maler = QPainter(bild)
    verbindungsbeschriftungen_zeichnen(maler, verbindung, quelle, ziel, MODERN_HELL)
    maler.end()

    gefaerbt = [
        (x, y)
        for x in range(bild.width())
        for y in range(bild.height())
        if bild.pixelColor(x, y).alpha() > 0
    ]
    assert gefaerbt, "keine Beschriftung gezeichnet"
    # nichts davon liegt innerhalb einer der beiden Formen
    for x, y in gefaerbt:
        for form in (quelle, ziel):
            drin = (
                form["x"] <= x <= form["x"] + form["w"]
                and form["y"] <= y <= form["y"] + form["h"]
            )
            assert not drin, f"Beschriftung bei ({x}, {y}) liegt in einer Form"


def test_uml_notation_je_art() -> None:
    """Die Notation aus Abschnitt 13.4 steckt vollständig im Katalog."""
    assert verbindungs_art("composition").raute_an_quelle == "gefuellt"
    assert verbindungs_art("aggregation").raute_an_quelle == "leer"
    assert verbindungs_art("inheritance").spitze_am_ziel == "dreieck"
    assert verbindungs_art("realization").gestrichelt is True
    assert verbindungs_art("dependency").spitze_am_ziel == "offen"
    assert verbindungs_art("association").spitze_am_ziel == "keine"
