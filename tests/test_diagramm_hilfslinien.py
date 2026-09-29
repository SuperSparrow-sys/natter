"""Hilfslinien verschieben, löschen und an ihnen einrasten (Punkt 69
der offenen Punkte).

Hilfslinien ließen sich nur anlegen. `_einrasten` las `guides` nie,
obwohl `lineale.py` das Einrasten versprach. Das obere Lineal meldete
die waagerechte Mausposition und daraus wurde eine waagerechte Linie
auf dieser Höhe. Und im Struktogramm und in der Tabelle legte das
Lineal Linien an, die nirgends gezeichnet wurden.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent

from ide.diagramm import DiagrammFenster, diagramm_erzeugen
from ide.diagramm.lineale import hilfslinien_lesen


def _fenster(qtbot, tmp_path: Path, typ: str = "class") -> DiagrammFenster:  # noqa: ANN001
    fenster = DiagrammFenster(diagramm_erzeugen(typ, tmp_path / f"{typ}.pdiag", "k"))
    qtbot.addWidget(fenster)
    fenster.aktionen["Ansicht/Lineale"].setChecked(True)
    # Seit Punkt 304 richtet sich die Startgröße nach dem Bildschirm,
    # und der von `offscreen` ist klein. Die Zielpunkte unten brauchen
    # die frühere Größe.
    fenster.resize(1100, 750)
    fenster.show()
    qtbot.waitExposed(fenster)
    return fenster


def _maus(typ: QEvent.Type, lokal: QPointF, global_: QPointF | None = None) -> QMouseEvent:
    return QMouseEvent(
        typ,
        lokal,
        global_ if global_ is not None else lokal,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )


def _aus_lineal_ziehen(
    fenster: DiagrammFenster, oben: bool, ziel_auf_flaeche: QPoint
) -> None:
    lineal = fenster.lineal_oben if oben else fenster.lineal_links
    lineal.mousePressEvent(_maus(QEvent.Type.MouseButtonPress, QPointF(5, 5)))
    global_ = QPointF(fenster.zeichenflaeche.mapToGlobal(ziel_auf_flaeche))
    lokal = QPointF(lineal.mapFromGlobal(global_.toPoint()))
    lineal.mouseReleaseEvent(_maus(QEvent.Type.MouseButtonRelease, lokal, global_))


# -- Anlegen aus dem Lineal ----------------------------------------------


def test_oberes_lineal_gibt_eine_waagerechte_linie_auf_der_loslasshoehe(
    qtbot, tmp_path: Path  # noqa: ANN001
) -> None:
    fenster = _fenster(qtbot, tmp_path)

    _aus_lineal_ziehen(fenster, oben=True, ziel_auf_flaeche=QPoint(300, 150))

    assert hilfslinien_lesen(fenster.diagramm.daten) == [
        {"orientation": "h", "pos": 150.0}
    ]


def test_linkes_lineal_gibt_eine_senkrechte_linie(
    qtbot, tmp_path: Path  # noqa: ANN001
) -> None:
    fenster = _fenster(qtbot, tmp_path)

    _aus_lineal_ziehen(fenster, oben=False, ziel_auf_flaeche=QPoint(260, 90))

    assert hilfslinien_lesen(fenster.diagramm.daten) == [
        {"orientation": "v", "pos": 260.0}
    ]


def test_ein_klick_aufs_lineal_legt_keine_linie_an(
    qtbot, tmp_path: Path  # noqa: ANN001
) -> None:
    fenster = _fenster(qtbot, tmp_path)
    lineal = fenster.lineal_oben

    lineal.mousePressEvent(_maus(QEvent.Type.MouseButtonPress, QPointF(40, 5)))
    lineal.mouseReleaseEvent(
        _maus(
            QEvent.Type.MouseButtonRelease,
            QPointF(40, 5),
            QPointF(lineal.mapToGlobal(QPoint(40, 5))),
        )
    )

    assert "guides" not in fenster.diagramm.daten


@pytest.mark.parametrize("typ", ["struktogramm", "entscheidungstabelle"])
def test_ohne_zeichnung_keine_hilfslinien(
    qtbot, tmp_path: Path, typ: str  # noqa: ANN001
) -> None:
    fenster = _fenster(qtbot, tmp_path, typ)

    _aus_lineal_ziehen(fenster, oben=True, ziel_auf_flaeche=QPoint(100, 100))

    assert "guides" not in fenster.diagramm.daten
    assert not fenster.aktionen["Ansicht/Hilfslinien"].isEnabled()


# -- Einrasten -----------------------------------------------------------


def test_formen_rasten_an_einer_hilfslinie_ein(qtbot, tmp_path: Path) -> None:  # noqa: ANN001
    fenster = _fenster(qtbot, tmp_path)
    flaeche = fenster.zeichenflaeche
    form = flaeche.form_platzieren("class", 600, 500)
    fenster._hilfslinie_anlegen(403.0, waagerecht=False)
    fenster._hilfslinie_anlegen(301.0, waagerecht=True)

    # Linke Kante nahe 403, untere Kante nahe 301
    x, y = flaeche._einrasten(form, 400, 301 - form["h"] + 4)

    assert x == 403
    assert y + form["h"] == 301
    assert ("x", 403.0) in flaeche._hilfslinien

    # Die Mitte rastet ebenso
    x, _ = flaeche._einrasten(form, 403 - form["w"] / 2 + 3, 40)
    assert x + form["w"] / 2 == 403


def test_ausgeblendete_hilfslinien_rasten_nicht(qtbot, tmp_path: Path) -> None:  # noqa: ANN001
    fenster = _fenster(qtbot, tmp_path)
    flaeche = fenster.zeichenflaeche
    form = flaeche.form_platzieren("class", 600, 500)
    fenster._hilfslinie_anlegen(403.0, waagerecht=False)
    fenster.aktionen["Ansicht/Hilfslinien"].setChecked(False)

    x, _ = flaeche._einrasten(form, 401, 40)

    assert x == 400  # nur das Raster


def test_ziehen_mit_der_maus_rastet_ein(qtbot, tmp_path: Path) -> None:  # noqa: ANN001
    fenster = _fenster(qtbot, tmp_path)
    flaeche = fenster.zeichenflaeche
    form = flaeche.form_platzieren("class", 300, 300)
    fenster._hilfslinie_anlegen(501.0, waagerecht=False)
    griff = QPointF(form["x"] + 20, form["y"] + 20)

    flaeche.mousePressEvent(_maus(QEvent.Type.MouseButtonPress, griff))
    ziel = QPointF(griff.x() + (499 - form["x"]), griff.y())
    flaeche.mouseMoveEvent(_maus(QEvent.Type.MouseMove, ziel))
    flaeche.mouseReleaseEvent(_maus(QEvent.Type.MouseButtonRelease, ziel))

    assert form["x"] == 501


# -- Verschieben und Löschen ---------------------------------------------


def test_hilfslinie_ziehen_verschiebt_sie(qtbot, tmp_path: Path) -> None:  # noqa: ANN001
    fenster = _fenster(qtbot, tmp_path)
    flaeche = fenster.zeichenflaeche
    fenster._hilfslinie_anlegen(200.0, waagerecht=True)

    flaeche.mousePressEvent(_maus(QEvent.Type.MouseButtonPress, QPointF(700, 201)))
    flaeche.mouseMoveEvent(_maus(QEvent.Type.MouseMove, QPointF(700, 260)))
    assert hilfslinien_lesen(flaeche.diagramm.daten)[0]["pos"] == 260.0
    flaeche.mouseReleaseEvent(
        _maus(QEvent.Type.MouseButtonRelease, QPointF(700, 280))
    )

    assert hilfslinien_lesen(flaeche.diagramm.daten) == [
        {"orientation": "h", "pos": 280.0}
    ]
    # Ein einziger Schritt, und der nimmt nur das Verschieben zurück
    flaeche.rueckgaengig()
    assert hilfslinien_lesen(flaeche.diagramm.daten) == [
        {"orientation": "h", "pos": 200.0}
    ]


def test_aufs_lineal_gezogen_verschwindet_sie(qtbot, tmp_path: Path) -> None:  # noqa: ANN001
    fenster = _fenster(qtbot, tmp_path)
    flaeche = fenster.zeichenflaeche
    fenster._hilfslinie_anlegen(120.0, waagerecht=False)
    fenster._hilfslinie_anlegen(200.0, waagerecht=True)

    flaeche.mousePressEvent(_maus(QEvent.Type.MouseButtonPress, QPointF(121, 600)))
    flaeche.mouseReleaseEvent(
        _maus(QEvent.Type.MouseButtonRelease, QPointF(-8, 600))
    )

    assert hilfslinien_lesen(flaeche.diagramm.daten) == [
        {"orientation": "h", "pos": 200.0}
    ]
    flaeche.rueckgaengig()
    assert len(hilfslinien_lesen(flaeche.diagramm.daten)) == 2


def test_letzte_linie_geloescht_kein_leeres_feld(qtbot, tmp_path: Path) -> None:  # noqa: ANN001
    fenster = _fenster(qtbot, tmp_path)
    flaeche = fenster.zeichenflaeche
    fenster._hilfslinie_anlegen(120.0, waagerecht=True)

    assert flaeche.hilfslinie_loeschen(0)

    assert "guides" not in flaeche.diagramm.daten
    fenster.speichern()


def test_eine_form_auf_der_linie_geht_vor(qtbot, tmp_path: Path) -> None:  # noqa: ANN001
    """Liegt eine Form über der Linie, greift ein Klick die Form."""
    fenster = _fenster(qtbot, tmp_path)
    flaeche = fenster.zeichenflaeche
    form = flaeche.form_platzieren("class", 300, 300)
    mitte_y = form["y"] + form["h"] / 2
    fenster._hilfslinie_anlegen(mitte_y, waagerecht=True)

    flaeche.mousePressEvent(
        _maus(QEvent.Type.MouseButtonPress, QPointF(form["x"] + 10, mitte_y))
    )

    assert flaeche._zieh_hilfslinie is None
    assert flaeche.ausgewaehlte_form is form
