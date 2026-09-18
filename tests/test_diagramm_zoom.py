"""Tests für Zoom und Ansicht verschieben im Diagramm-Editor
(M9, Teilschritt 2b). Headless.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent, QWheelEvent

from ide.diagramm import DiagrammFenster, diagramm_erzeugen
from ide.diagramm.canvas import MAX_ZOOM, MIN_ZOOM, DiagrammCanvas


@pytest.fixture
def fenster(tmp_path: Path) -> DiagrammFenster:
    return DiagrammFenster(diagramm_erzeugen("class", tmp_path / "k.pdiag", "k"))


@pytest.fixture
def flaeche(fenster: DiagrammFenster) -> DiagrammCanvas:
    return fenster.zeichenflaeche


def _maus(x: float, y: float, typ, taste=Qt.MouseButton.LeftButton) -> QMouseEvent:
    return QMouseEvent(
        typ, QPointF(x, y), QPointF(x, y), taste, taste, Qt.KeyboardModifier.NoModifier
    )


def _rad(nach_oben: bool, strg: bool) -> QWheelEvent:
    return QWheelEvent(
        QPointF(10, 10),
        QPointF(10, 10),
        QPoint(0, 0),
        QPoint(0, 120 if nach_oben else -120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.ControlModifier if strg else Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )


# -- Zoomstufe -----------------------------------------------------------


def test_neues_diagramm_steht_auf_hundert_prozent(flaeche: DiagrammCanvas) -> None:
    assert flaeche.zoom == 1.0


def test_zoom_bleibt_in_seinen_grenzen(flaeche: DiagrammCanvas) -> None:
    """Sonst zoomt man sich aus Versehen ins Nichts."""
    flaeche.zoom_setzen(100.0)
    assert flaeche.zoom == MAX_ZOOM

    flaeche.zoom_setzen(0.001)
    assert flaeche.zoom == MIN_ZOOM


def test_zoom_meldet_die_neue_stufe(flaeche: DiagrammCanvas) -> None:
    gemeldet: list[float] = []
    flaeche.zoom_geaendert.connect(gemeldet.append)

    flaeche.zoom_setzen(2.0)

    assert gemeldet == [2.0]


def test_gleiche_stufe_meldet_nichts(flaeche: DiagrammCanvas) -> None:
    gemeldet: list[float] = []
    flaeche.zoom_geaendert.connect(gemeldet.append)

    flaeche.zoom_setzen(1.0)

    assert gemeldet == []


def test_flaeche_waechst_mit_dem_zoom(flaeche: DiagrammCanvas) -> None:
    """Sonst bliebe beim Hineinzoomen der untere Teil unerreichbar."""
    vorher = flaeche.minimumSize().width()

    flaeche.zoom_setzen(2.0)

    assert flaeche.minimumSize().width() == pytest.approx(vorher * 2, abs=2)


def test_strg_mausrad_zoomt(flaeche: DiagrammCanvas) -> None:
    flaeche.wheelEvent(_rad(nach_oben=True, strg=True))
    assert flaeche.zoom > 1.0

    vorher = flaeche.zoom
    flaeche.wheelEvent(_rad(nach_oben=False, strg=True))
    assert flaeche.zoom < vorher


def test_mausrad_ohne_strg_zoomt_nicht(flaeche: DiagrammCanvas) -> None:
    """Ohne Strg gehört das Rad dem Rollbereich."""
    flaeche.wheelEvent(_rad(nach_oben=True, strg=False))

    assert flaeche.zoom == 1.0


def test_alles_anzeigen_passt_den_inhalt_ein(flaeche: DiagrammCanvas) -> None:
    flaeche.form_platzieren("class", 300, 300)

    flaeche.alles_anzeigen(600, 400)

    breite, hoehe = flaeche._inhalt_in_diagrammkoordinaten()
    assert breite * flaeche.zoom <= 600 + 1
    assert hoehe * flaeche.zoom <= 400 + 1


# -- Treffer bei veränderter Zoomstufe -----------------------------------


def test_klick_trifft_die_form_auch_bei_doppeltem_zoom(flaeche: DiagrammCanvas) -> None:
    """Der eigentliche Knackpunkt am Zoom: die Trefferprüfung rechnet in
    Diagrammkoordinaten, die Maus liefert Bildschirmkoordinaten."""
    form = flaeche.form_platzieren("class", 300, 300)
    flaeche.auswahl_aufheben()
    flaeche.zoom_setzen(2.0)

    mitte_x = (form["x"] + form["w"] / 2) * 2
    mitte_y = (form["y"] + form["h"] / 2) * 2
    flaeche.mousePressEvent(_maus(mitte_x, mitte_y, QEvent.Type.MouseButtonPress))

    assert flaeche.ausgewaehlte_form is form


def test_platzieren_landet_bei_zoom_an_der_richtigen_stelle(
    flaeche: DiagrammCanvas,
) -> None:
    flaeche.zoom_setzen(0.5)
    flaeche.platzierungsmodus_setzen("class")

    flaeche.mousePressEvent(_maus(200, 150, QEvent.Type.MouseButtonPress))

    form = flaeche.formen[0]
    # Klick bei 200/150 auf dem Bildschirm = 400/300 im Diagramm
    assert form["x"] + form["w"] / 2 == pytest.approx(400, abs=8)
    assert form["y"] + form["h"] / 2 == pytest.approx(300, abs=8)


def test_texteditor_liegt_bei_zoom_ueber_seiner_form(flaeche: DiagrammCanvas) -> None:
    """Eine Notiz, keine Klasse: Klassen öffnen seit Schritt 12 den
    Eigenschaften-Dialog, und dessen `exec()` käme headless nie
    zurück."""
    form = flaeche.form_platzieren("note", 300, 300)
    flaeche.zoom_setzen(2.0)

    editor = flaeche.bearbeiten_starten(form)

    assert editor.geometry().left() == pytest.approx(form["x"] * 2, abs=2)
    assert editor.geometry().width() == pytest.approx(form["w"] * 2, abs=2)


# -- Ansicht verschieben -------------------------------------------------


def test_leertaste_schaltet_auf_verschieben(flaeche: DiagrammCanvas) -> None:
    flaeche.keyPressEvent(
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Space, Qt.KeyboardModifier.NoModifier)
    )

    assert flaeche._leertaste is True


def test_ziehen_mit_leertaste_waehlt_nichts_aus(flaeche: DiagrammCanvas) -> None:
    """Wer die Ansicht schiebt, will keine Form anfassen."""
    form = flaeche.form_platzieren("class", 300, 300)
    flaeche.auswahl_aufheben()
    flaeche.keyPressEvent(
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Space, Qt.KeyboardModifier.NoModifier)
    )

    flaeche.mousePressEvent(
        _maus(form["x"] + 10, form["y"] + 10, QEvent.Type.MouseButtonPress)
    )

    assert flaeche.ausgewaehlte_form is None
    assert flaeche._greif_start is not None


def test_mittlere_maustaste_verschiebt_auch_ohne_leertaste(
    flaeche: DiagrammCanvas,
) -> None:
    flaeche.mousePressEvent(
        _maus(100, 100, QEvent.Type.MouseButtonPress, Qt.MouseButton.MiddleButton)
    )

    assert flaeche._greif_start is not None


def test_ansicht_verschieben_rollt_wirklich(fenster: DiagrammFenster) -> None:
    flaeche = fenster.zeichenflaeche
    fenster.resize(700, 480)
    fenster.show()
    senkrecht = fenster.rollbereich.verticalScrollBar()
    senkrecht.setValue(100)

    flaeche.ansicht_verschieben(0, -40)

    assert senkrecht.value() == 140


def test_loslassen_beendet_das_verschieben(flaeche: DiagrammCanvas) -> None:
    flaeche.mousePressEvent(
        _maus(100, 100, QEvent.Type.MouseButtonPress, Qt.MouseButton.MiddleButton)
    )

    flaeche.mouseReleaseEvent(
        _maus(120, 120, QEvent.Type.MouseButtonRelease, Qt.MouseButton.MiddleButton)
    )

    assert flaeche._greif_start is None


def test_leertaste_loslassen_schaltet_zurueck(flaeche: DiagrammCanvas) -> None:
    flaeche.keyPressEvent(
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Space, Qt.KeyboardModifier.NoModifier)
    )

    flaeche.keyReleaseEvent(
        QKeyEvent(QEvent.Type.KeyRelease, Qt.Key.Key_Space, Qt.KeyboardModifier.NoModifier)
    )

    assert flaeche._leertaste is False


def test_leertaste_beim_beschriften_bleibt_ein_leerzeichen(
    flaeche: DiagrammCanvas,
) -> None:
    """Sonst könnte man in einem Klassennamen keine Lücke tippen."""
    form = flaeche.form_platzieren("note", 300, 300)
    flaeche.bearbeiten_starten(form)

    flaeche.keyPressEvent(
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Space, Qt.KeyboardModifier.NoModifier)
    )

    assert flaeche._leertaste is False


# -- Menü ----------------------------------------------------------------


def test_zoom_eintraege_sind_aktiv(fenster: DiagrammFenster) -> None:
    for name in ("Zoom vergrößern", "Zoom verkleinern", "Alles anzeigen", "Zoom 100 %"):
        assert fenster.aktionen[f"Ansicht/{name}"].isEnabled() is True


def test_menue_zoom_wirkt_auf_die_flaeche(fenster: DiagrammFenster) -> None:
    fenster.aktionen["Ansicht/Zoom vergrößern"].trigger()

    assert fenster.zeichenflaeche.zoom > 1.0


def test_zoom_hundert_prozent_stellt_zurueck(fenster: DiagrammFenster) -> None:
    fenster.zeichenflaeche.zoom_setzen(3.0)

    fenster.aktionen["Ansicht/Zoom 100 %"].trigger()

    assert fenster.zeichenflaeche.zoom == 1.0


def test_zoomstufe_steht_in_der_statusleiste(fenster: DiagrammFenster) -> None:
    fenster.zeichenflaeche.zoom_setzen(1.5)

    assert "Zoom 150 %" in fenster.statusBar().currentMessage()


def test_struktogramm_hat_keine_zoom_eintraege(tmp_path: Path) -> None:
    """Ehrlicher Zwischenstand: die Blockfläche kann noch nicht zoomen,
    der Eintrag ist deshalb ausgegraut statt wirkungslos."""
    fenster = DiagrammFenster(
        diagramm_erzeugen("struktogramm", tmp_path / "s.pdiag", "s")
    )

    assert fenster.aktionen["Ansicht/Zoom vergrößern"].isEnabled() is False
