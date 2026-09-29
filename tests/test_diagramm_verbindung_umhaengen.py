"""Verbindungen umhängen und umwandeln (Punkt 66 der offenen Punkte).

`from`, `to` und `kind` schrieb nur `verbindung_erstellen`. Wer aus
einer Assoziation eine Komposition machen oder ein Ende an eine
andere Klasse hängen wollte, musste löschen und neu zeichnen - und
verlor dabei Beschriftungen und Knickpunkte.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent

from ide.diagramm import DiagrammFenster, diagramm_erzeugen
from ide.diagramm.formen import verbindungen_fuer
from ide.diagramm.zeichnen import verbindungs_punkte


def _fenster(tmp_path: Path, typ: str = "class") -> DiagrammFenster:
    return DiagrammFenster(diagramm_erzeugen(typ, tmp_path / f"{typ}.pdiag", "k"))


@pytest.fixture
def fenster(qtbot, tmp_path: Path) -> DiagrammFenster:  # noqa: ANN001
    return _fenster(tmp_path)


def _drei_klassen(fenster: DiagrammFenster) -> tuple[dict, dict, dict, dict]:
    flaeche = fenster.zeichenflaeche
    a = flaeche.form_platzieren("class", 200, 200)
    b = flaeche.form_platzieren("class", 700, 200)
    c = flaeche.form_platzieren("class", 700, 600)
    verbindung = flaeche.verbindung_erstellen("association", a, b)
    verbindung["labels"] = {"from": "1", "to": "*"}
    verbindung["waypoints"] = [[450, 120]]
    return a, b, c, verbindung


def _maus(typ: QEvent.Type, x: float, y: float) -> QMouseEvent:
    return QMouseEvent(
        typ,
        QPointF(x, y),
        QPointF(x, y),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )


# -- Art -----------------------------------------------------------------


def test_panel_bietet_nur_die_arten_des_diagrammtyps(fenster: DiagrammFenster) -> None:
    *_, verbindung = _drei_klassen(fenster)
    fenster.zeichenflaeche._verbindung_auswaehlen(verbindung)
    panel = fenster.eigenschaften

    angeboten = [panel.art.itemData(i) for i in range(panel.art.count())]

    assert angeboten == [art.kind for art in verbindungen_fuer("class")]
    assert panel.art.currentData() == "association"
    assert panel.hinweis.text() == "Verbindung: Assoziation"


def test_art_aendern_behaelt_beschriftung_und_knicke(
    fenster: DiagrammFenster,
) -> None:
    *_, verbindung = _drei_klassen(fenster)
    fenster.zeichenflaeche._verbindung_auswaehlen(verbindung)
    panel = fenster.eigenschaften

    panel.art.setCurrentIndex(panel.art.findData("composition"))

    assert verbindung["kind"] == "composition"
    assert verbindung["labels"] == {"from": "1", "to": "*"}
    assert verbindung["waypoints"] == [[450, 120]]

    fenster.zeichenflaeche.rueckgaengig()
    assert verbindung["kind"] == "association"


def test_im_zustandsdiagramm_gibt_es_keine_komposition(
    qtbot, tmp_path: Path  # noqa: ANN001
) -> None:
    fenster = _fenster(tmp_path, "state")
    flaeche = fenster.zeichenflaeche
    a = flaeche.form_platzieren("state", 200, 200)
    b = flaeche.form_platzieren("state", 600, 200)
    art = verbindungen_fuer("state")[0].kind
    flaeche.verbindung_erstellen(art, a, b)

    angeboten = [
        fenster.eigenschaften.art.itemData(i)
        for i in range(fenster.eigenschaften.art.count())
    ]
    assert "composition" not in angeboten
    assert angeboten == [a.kind for a in verbindungen_fuer("state")]


# -- Enden ---------------------------------------------------------------


def test_ende_auf_eine_andere_form_ziehen(fenster: DiagrammFenster) -> None:
    a, b, c, verbindung = _drei_klassen(fenster)
    flaeche = fenster.zeichenflaeche
    flaeche._verbindung_auswaehlen(verbindung)
    ende = verbindungs_punkte(verbindung, a, b)[-1]
    assert flaeche.endpunkt_bei(verbindung, ende.x(), ende.y()) == "to"

    flaeche.mousePressEvent(_maus(QEvent.Type.MouseButtonPress, ende.x(), ende.y()))
    ziel = c["x"] + c["w"] / 2, c["y"] + c["h"] / 2
    flaeche.mouseMoveEvent(_maus(QEvent.Type.MouseMove, *ziel))
    flaeche.mouseReleaseEvent(_maus(QEvent.Type.MouseButtonRelease, *ziel))

    assert (verbindung["from"], verbindung["to"]) == (a["id"], c["id"])
    assert verbindung["labels"] == {"from": "1", "to": "*"}
    assert verbindung["waypoints"] == [[450, 120]]
    # Die Formen selbst sind nicht verschoben worden
    assert (c["x"], c["y"]) == (flaeche.formen[2]["x"], flaeche.formen[2]["y"])

    flaeche.rueckgaengig()
    assert verbindung["to"] == b["id"]


def test_ende_ins_leere_aendert_nichts(fenster: DiagrammFenster) -> None:
    a, b, _, verbindung = _drei_klassen(fenster)
    flaeche = fenster.zeichenflaeche
    flaeche._verbindung_auswaehlen(verbindung)
    anfang = verbindungs_punkte(verbindung, a, b)[0]

    flaeche.mousePressEvent(
        _maus(QEvent.Type.MouseButtonPress, anfang.x(), anfang.y())
    )
    flaeche.mouseReleaseEvent(_maus(QEvent.Type.MouseButtonRelease, 60, 700))

    assert (verbindung["from"], verbindung["to"]) == (a["id"], b["id"])
    assert not flaeche.kommandos.kann_wiederholen


def test_kein_ende_an_die_form_am_anderen_ende(fenster: DiagrammFenster) -> None:
    a, b, _, verbindung = _drei_klassen(fenster)

    assert not fenster.zeichenflaeche.endpunkt_umhaengen(verbindung, "from", b)
    assert not fenster.zeichenflaeche.endpunkt_umhaengen(verbindung, "from", a)
    assert verbindung["from"] == a["id"]


def test_quelle_umhaengen_im_sequenzdiagramm(qtbot, tmp_path: Path) -> None:  # noqa: ANN001
    """Waagerechte Nachrichten: die Höhe bleibt beim Umhängen stehen."""
    fenster = _fenster(tmp_path, "sequence")
    flaeche = fenster.zeichenflaeche
    a = flaeche.form_platzieren("lifeline", 200, 200)
    b = flaeche.form_platzieren("lifeline", 500, 200)
    c = flaeche.form_platzieren("lifeline", 800, 200)
    nachricht = flaeche.verbindung_erstellen("sync_message", a, b)
    nachricht["y"] = 300

    assert flaeche.endpunkt_umhaengen(nachricht, "from", c)

    assert (nachricht["from"], nachricht["to"], nachricht["y"]) == (
        c["id"],
        b["id"],
        300,
    )
