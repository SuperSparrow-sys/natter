"""Tests für ide/diagramm/canvas.py + kommandos.py: Verschieben,
Größe, Löschen, Duplizieren, Einrasten, Undo/Redo (M9, Schritt 3).
Headless.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent

from ide.diagramm import diagramm_erzeugen
from ide.diagramm.canvas import RASTER, DiagrammCanvas


@pytest.fixture
def canvas(tmp_path: Path) -> DiagrammCanvas:
    return DiagrammCanvas(diagramm_erzeugen("class", tmp_path / "k.pdiag", "k"))


def _maus(typ: QEvent.Type, x: float, y: float) -> QMouseEvent:
    knopf = Qt.MouseButton.LeftButton
    return QMouseEvent(
        typ,
        QPointF(x, y),
        QPointF(x, y),
        knopf,
        knopf if typ != QEvent.Type.MouseButtonRelease else Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )


def _taste(taste: Qt.Key, modifikatoren=Qt.KeyboardModifier.NoModifier) -> QKeyEvent:
    return QKeyEvent(QEvent.Type.KeyPress, taste, modifikatoren)


# -- Verschieben / Größe ---------------------------------------------------


def test_verschieben_aendert_die_position(canvas: DiagrammCanvas) -> None:
    form = canvas.form_platzieren("class", 200, 200)
    vorher = (form["x"], form["y"])

    canvas.verschieben(RASTER, 2 * RASTER)

    assert (form["x"], form["y"]) == (vorher[0] + RASTER, vorher[1] + 2 * RASTER)


def test_groesse_aendern_wird_von_der_mindestgroesse_begrenzt(canvas: DiagrammCanvas) -> None:
    """Eine Form darf nicht kleiner werden als ihr Inhalt braucht
    (Abschnitt 13.6)."""
    form = canvas.form_platzieren("class", 200, 200)

    canvas.groesse_aendern(-1000, -1000)

    assert form["w"] >= 72
    assert form["h"] >= 40


def test_loeschen_entfernt_die_form_und_die_auswahl(canvas: DiagrammCanvas) -> None:
    form = canvas.form_platzieren("class", 200, 200)

    canvas.loeschen()

    assert form not in canvas.formen
    assert canvas.ausgewaehlte_form is None


def test_duplizieren_erzeugt_eine_versetzte_kopie(canvas: DiagrammCanvas) -> None:
    form = canvas.form_platzieren("class", 200, 200)
    form["name"] = "TAmpel"

    kopie = canvas.duplizieren()

    assert kopie is not form
    assert kopie["id"] != form["id"]
    assert kopie["name"] == "TAmpel"
    assert (kopie["x"], kopie["y"]) == (form["x"] + RASTER, form["y"] + RASTER)
    # tiefe Kopie: Ändern der Kopie lässt das Original unberührt
    kopie["name"] = "TAnders"
    assert form["name"] == "TAmpel"


def test_ohne_auswahl_passiert_nichts(canvas: DiagrammCanvas) -> None:
    canvas.verschieben(8, 8)
    canvas.groesse_aendern(8, 8)
    canvas.loeschen()

    assert canvas.duplizieren() is None
    assert canvas.formen == []


# -- Undo / Redo -----------------------------------------------------------


def test_platzieren_laesst_sich_rueckgaengig_machen(canvas: DiagrammCanvas) -> None:
    canvas.form_platzieren("class", 200, 200)

    canvas.rueckgaengig()

    assert canvas.formen == []
    assert canvas.ausgewaehlte_form is None


def test_verschieben_laesst_sich_rueckgaengig_und_wiederholen(canvas: DiagrammCanvas) -> None:
    form = canvas.form_platzieren("class", 200, 200)
    vorher = (form["x"], form["y"])
    canvas.verschieben(RASTER, RASTER)

    canvas.rueckgaengig()
    assert (form["x"], form["y"]) == vorher

    canvas.wiederholen()
    assert (form["x"], form["y"]) == (vorher[0] + RASTER, vorher[1] + RASTER)


def test_geloeschte_form_kommt_an_ihre_alte_stelle_zurueck(canvas: DiagrammCanvas) -> None:
    """Die Reihenfolge entscheidet, welche Form oben liegt – nach dem
    Rückgängigmachen muss sie deshalb wieder stimmen."""
    erste = canvas.form_platzieren("class", 100, 100)
    zweite = canvas.form_platzieren("class", 300, 100)
    dritte = canvas.form_platzieren("class", 500, 100)

    canvas.loeschen(zweite)
    canvas.rueckgaengig()

    assert canvas.formen == [erste, zweite, dritte]


def test_wiederholtes_einfuegen_waehlt_die_form_wieder_aus(canvas: DiagrammCanvas) -> None:
    """Sonst ist nach „Wiederholen“ nichts ausgewählt und ein direkt
    folgendes „Löschen“ liefe ins Leere (im Menü-Test aufgefallen)."""
    form = canvas.form_platzieren("class", 200, 200)
    canvas.rueckgaengig()

    canvas.wiederholen()

    assert canvas.ausgewaehlte_form is form


def test_undo_ohne_vorgang_tut_nichts(canvas: DiagrammCanvas) -> None:
    canvas.rueckgaengig()
    canvas.wiederholen()

    assert canvas.formen == []


# -- Maus ------------------------------------------------------------------


def test_ziehen_verschiebt_die_form(canvas: DiagrammCanvas) -> None:
    form = canvas.form_platzieren("class", 200, 200)
    start_x, start_y = form["x"], form["y"]

    canvas.mousePressEvent(_maus(QEvent.Type.MouseButtonPress, 200, 200))
    canvas.mouseMoveEvent(_maus(QEvent.Type.MouseMove, 264, 240))
    canvas.mouseReleaseEvent(_maus(QEvent.Type.MouseButtonRelease, 264, 240))

    assert form["x"] == start_x + 64
    assert form["y"] == start_y + 40


def test_ziehen_ist_ein_einziger_undo_schritt(canvas: DiagrammCanvas) -> None:
    """Die Live-Vorschau während des Ziehens darf nicht jede
    Zwischenposition auf den Undo-Stapel legen."""
    form = canvas.form_platzieren("class", 200, 200)
    vorher = (form["x"], form["y"])

    canvas.mousePressEvent(_maus(QEvent.Type.MouseButtonPress, 200, 200))
    canvas.mouseMoveEvent(_maus(QEvent.Type.MouseMove, 220, 210))
    canvas.mouseMoveEvent(_maus(QEvent.Type.MouseMove, 264, 240))
    canvas.mouseReleaseEvent(_maus(QEvent.Type.MouseButtonRelease, 264, 240))

    canvas.rueckgaengig()

    assert (form["x"], form["y"]) == vorher


def test_ziehen_ohne_bewegung_erzeugt_keinen_undo_schritt(canvas: DiagrammCanvas) -> None:
    canvas.form_platzieren("class", 200, 200)

    canvas.mousePressEvent(_maus(QEvent.Type.MouseButtonPress, 200, 200))
    canvas.mouseReleaseEvent(_maus(QEvent.Type.MouseButtonRelease, 200, 200))
    canvas.rueckgaengig()  # macht das Platzieren rückgängig, nicht ein Nicht-Ziehen

    assert canvas.formen == []


def test_anfasser_ziehen_aendert_die_groesse(canvas: DiagrammCanvas) -> None:
    form = canvas.form_platzieren("class", 300, 300)
    rechts = form["x"] + form["w"]
    mitte_y = form["y"] + form["h"] / 2
    breite_vorher = form["w"]

    canvas.mousePressEvent(_maus(QEvent.Type.MouseButtonPress, rechts, mitte_y))
    canvas.mouseMoveEvent(_maus(QEvent.Type.MouseMove, rechts + 40, mitte_y))
    canvas.mouseReleaseEvent(_maus(QEvent.Type.MouseButtonRelease, rechts + 40, mitte_y))

    assert form["w"] == breite_vorher + 40


def test_anfasser_wird_nur_bei_ausgewaehlter_form_getroffen(canvas: DiagrammCanvas) -> None:
    form = canvas.form_platzieren("class", 300, 300)
    canvas.auswahl_aufheben()

    assert canvas.anfasser_bei(form["x"], form["y"]) is None


# -- Einrasten -------------------------------------------------------------


def test_ziehen_rastet_an_der_kante_einer_anderen_form_ein(canvas: DiagrammCanvas) -> None:
    """Abschnitt 13.3: Einrasten „an Kanten/Mitten anderer Formen“."""
    fest = canvas.form_platzieren("class", 200, 150)
    beweglich = canvas.form_platzieren("class", 200, 400)

    # zwei Pixel neben die linke Kante der festen Form ziehen
    ziel_x = fest["x"] + 2
    start_x, start_y = beweglich["x"], beweglich["y"]
    griff_x, griff_y = start_x + 10, start_y + 10

    canvas.mousePressEvent(_maus(QEvent.Type.MouseButtonPress, griff_x, griff_y))
    canvas.mouseMoveEvent(
        _maus(QEvent.Type.MouseMove, griff_x + (ziel_x - start_x), griff_y)
    )

    assert beweglich["x"] == fest["x"]
    assert ("x", float(fest["x"])) in canvas._hilfslinien


def test_hilfslinien_verschwinden_nach_dem_loslassen(canvas: DiagrammCanvas) -> None:
    fest = canvas.form_platzieren("class", 200, 150)
    beweglich = canvas.form_platzieren("class", 200, 400)
    griff_x, griff_y = beweglich["x"] + 10, beweglich["y"] + 10

    canvas.mousePressEvent(_maus(QEvent.Type.MouseButtonPress, griff_x, griff_y))
    canvas.mouseMoveEvent(
        _maus(QEvent.Type.MouseMove, griff_x + (fest["x"] + 2 - beweglich["x"]), griff_y)
    )
    canvas.mouseReleaseEvent(_maus(QEvent.Type.MouseButtonRelease, griff_x, griff_y))

    assert canvas._hilfslinien == []


# -- Tastatur --------------------------------------------------------------


def test_pfeiltaste_verschiebt_um_einen_rasterschritt(canvas: DiagrammCanvas) -> None:
    form = canvas.form_platzieren("class", 200, 200)
    vorher = form["x"]

    canvas.keyPressEvent(_taste(Qt.Key.Key_Right))

    assert form["x"] == vorher + RASTER


def test_alt_pfeiltaste_verschiebt_um_ein_pixel(canvas: DiagrammCanvas) -> None:
    form = canvas.form_platzieren("class", 200, 200)
    vorher = form["y"]

    canvas.keyPressEvent(_taste(Qt.Key.Key_Down, Qt.KeyboardModifier.AltModifier))

    assert form["y"] == vorher + 1


def test_umschalt_pfeiltaste_aendert_die_groesse(canvas: DiagrammCanvas) -> None:
    form = canvas.form_platzieren("class", 200, 200)
    vorher = form["w"]

    canvas.keyPressEvent(_taste(Qt.Key.Key_Right, Qt.KeyboardModifier.ShiftModifier))

    assert form["w"] == vorher + RASTER


def test_entf_loescht_die_ausgewaehlte_form(canvas: DiagrammCanvas) -> None:
    canvas.form_platzieren("class", 200, 200)

    canvas.keyPressEvent(_taste(Qt.Key.Key_Delete))

    assert canvas.formen == []


def test_strg_d_dupliziert(canvas: DiagrammCanvas) -> None:
    canvas.form_platzieren("class", 200, 200)

    canvas.keyPressEvent(_taste(Qt.Key.Key_D, Qt.KeyboardModifier.ControlModifier))

    assert len(canvas.formen) == 2


def test_strg_z_macht_rueckgaengig_und_strg_umschalt_z_wiederholt(
    canvas: DiagrammCanvas,
) -> None:
    canvas.form_platzieren("class", 200, 200)

    canvas.keyPressEvent(_taste(Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier))
    assert canvas.formen == []

    canvas.keyPressEvent(
        _taste(
            Qt.Key.Key_Z,
            Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier,
        )
    )
    assert len(canvas.formen) == 1


def test_escape_bricht_das_platzieren_ab(canvas: DiagrammCanvas) -> None:
    canvas.platzierungsmodus_setzen("class")

    canvas.keyPressEvent(_taste(Qt.Key.Key_Escape))

    assert canvas._platzierungs_kind is None
