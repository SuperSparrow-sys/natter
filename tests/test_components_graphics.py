"""Tests für `PaintBox` und `Canvas` (M15, Abschnitt 2). Headless.

Geprüft wird nicht, ob eine Methode ohne Ausnahme durchläuft, sondern ob
an der erwarteten Stelle die erwartete **Farbe** steht: eine
Zeichenoperation, die nichts zeichnet, sähe sonst wie ein bestandener
Test aus.

Für gerendertes Pixelbild braucht `QT_QPA_PLATFORM=offscreen` unter
Windows eine gesetzte Schriftart (siehe AGENTS.md); das erledigt
`conftest.py` für alle Tests.
"""

from __future__ import annotations

import pytest

from pcl import Form, PaintBox
from pcl.components.graphics import Canvas
from pcl.errors import NatterPropertyError

WEISS = "#ffffff"
ROT = "#c42b1c"
BLAU = "#0067c0"


def _flaeche(breite: int = 120, hoehe: int = 90) -> tuple[Form, PaintBox]:
    """Formular **und** PaintBox zurückgeben: ohne die Referenz aufs
    Formular räumt Python dessen Qt-Widget zwischen zwei Zeilen weg."""
    formular = Form()
    box = PaintBox(formular)
    box.width = breite
    box.height = hoehe
    return formular, box


def _farbe(box: PaintBox, x: int, y: int) -> str:
    return box.canvas.pixels[x, y]


# -- Grundlagen ---------------------------------------------------------


def test_eine_neue_zeichenflaeche_ist_weiss() -> None:
    _formular, box = _flaeche()
    assert _farbe(box, 5, 5) == WEISS
    assert box.canvas.width == 120
    assert box.canvas.height == 90


def test_paintbox_laesst_sich_ohne_elternformular_erzeugen() -> None:
    """Wie jede `Control`: im Code erzeugt und auf keinem Formular."""
    box = PaintBox()
    assert isinstance(box.canvas, Canvas)


# -- Zeichnen -----------------------------------------------------------


def test_line_to_zieht_eine_linie_in_der_stiftfarbe() -> None:
    _formular, box = _flaeche()
    box.canvas.pen.color = ROT
    box.canvas.move_to(10, 20)
    box.canvas.line_to(80, 20)

    assert _farbe(box, 45, 20) == ROT
    assert _farbe(box, 45, 40) == WEISS, "unter der Linie darf nichts stehen"


def test_line_to_setzt_den_stift_ans_ziel() -> None:
    _formular, box = _flaeche()
    box.canvas.pen.color = ROT
    box.canvas.move_to(10, 10)
    box.canvas.line_to(10, 60)
    box.canvas.line_to(70, 60)

    assert _farbe(box, 10, 35) == ROT
    assert _farbe(box, 40, 60) == ROT


def test_line_ist_die_kurzform_aus_move_to_und_line_to() -> None:
    _formular, box = _flaeche()
    box.canvas.pen.color = BLAU
    box.canvas.line(5, 70, 95, 70)
    assert _farbe(box, 50, 70) == BLAU


def test_rectangle_faerbt_rand_und_flaeche_getrennt() -> None:
    _formular, box = _flaeche()
    box.canvas.pen.color = ROT
    box.canvas.brush.color = BLAU
    box.canvas.rectangle(20, 20, 80, 70)

    assert _farbe(box, 50, 45) == BLAU, "die Fläche trägt brush.color"
    assert _farbe(box, 20, 45) == ROT, "der Rand trägt pen.color"
    assert _farbe(box, 10, 10) == WEISS


def test_rectangle_mit_clear_laesst_die_flaeche_leer() -> None:
    _formular, box = _flaeche()
    box.canvas.pen.color = ROT
    box.canvas.brush.color = BLAU
    box.canvas.brush.style = "clear"
    box.canvas.rectangle(20, 20, 80, 70)

    assert _farbe(box, 20, 45) == ROT
    assert _farbe(box, 50, 45) == WEISS


def test_rectangle_vertraegt_verkehrt_herum_angegebene_ecken() -> None:
    """(80, 70) nach (20, 20) muss dasselbe Rechteck ergeben - sonst
    zeichnet ein Programm je nach Ziehrichtung der Maus nichts."""
    _formular, box = _flaeche()
    box.canvas.brush.color = BLAU
    box.canvas.rectangle(80, 70, 20, 20)
    assert _farbe(box, 50, 45) == BLAU


def test_ellipse_fuellt_die_mitte_und_laesst_die_ecken_frei() -> None:
    _formular, box = _flaeche()
    box.canvas.brush.color = BLAU
    box.canvas.pen.color = BLAU
    box.canvas.ellipse(20, 20, 80, 80)

    assert _farbe(box, 50, 50) == BLAU, "die Mitte liegt in der Ellipse"
    assert _farbe(box, 22, 22) == WEISS, "die Ecke des Rechtecks liegt außerhalb"


def test_fill_rect_fuellt_ohne_rand() -> None:
    _formular, box = _flaeche()
    box.canvas.pen.color = ROT
    box.canvas.brush.color = BLAU
    box.canvas.fill_rect(20, 20, 80, 70)

    assert _farbe(box, 50, 45) == BLAU
    assert _farbe(box, 20, 45) == BLAU, "fill_rect zieht keinen Rand in pen.color"


def test_text_out_hinterlaesst_pixel_in_der_stiftfarbe() -> None:
    _formular, box = _flaeche()
    box.canvas.pen.color = ROT
    box.canvas.text_out(10, 10, "Hallo Welt")

    treffer = [
        (x, y)
        for y in range(8, 30)
        for x in range(8, 110)
        if box.canvas.pixels[x, y] != WEISS
    ]
    assert treffer, "text_out hat nichts hinterlassen"


def test_text_out_zeichnet_unterhalb_der_angegebenen_stelle() -> None:
    """In Lazarus ist (x, y) die linke **obere** Ecke des Textes, in Qt
    von sich aus die Schriftlinie. Ohne die Umrechnung stünde der Text
    über dem Rand und wäre halb abgeschnitten."""
    _formular, box = _flaeche()
    box.canvas.pen.color = ROT
    box.canvas.text_out(10, 40, "Hg")

    ueber = [x for x in range(10, 60) if box.canvas.pixels[x, 38] != WEISS]
    unter = [x for x in range(10, 60) if box.canvas.pixels[x, 45] != WEISS]
    assert not ueber, "oberhalb von y=40 darf nichts stehen"
    assert unter, "unterhalb von y=40 muss der Text stehen"


def test_pen_width_macht_die_linie_dicker() -> None:
    _formular, box = _flaeche()
    box.canvas.pen.color = ROT
    box.canvas.pen.width = 7
    box.canvas.line(10, 45, 110, 45)

    assert _farbe(box, 60, 45) == ROT
    assert _farbe(box, 60, 47) == ROT, "eine 7 Pixel breite Linie reicht bis y=47"


def test_pixels_setzt_und_liest_einen_einzelnen_punkt() -> None:
    _formular, box = _flaeche()
    box.canvas.pixels[30, 40] = ROT
    assert _farbe(box, 30, 40) == ROT
    assert _farbe(box, 31, 40) == WEISS


def test_clear_loescht_alles_gezeichnete() -> None:
    _formular, box = _flaeche()
    box.canvas.brush.color = BLAU
    box.canvas.rectangle(10, 10, 100, 80)
    assert _farbe(box, 50, 45) == BLAU

    box.canvas.clear()
    assert _farbe(box, 50, 45) == WEISS


def test_clear_an_der_paintbox_tut_dasselbe() -> None:
    _formular, box = _flaeche()
    box.canvas.brush.color = BLAU
    box.canvas.rectangle(10, 10, 100, 80)
    box.clear()
    assert _farbe(box, 50, 45) == WEISS


# -- Das Bild bleibt stehen ---------------------------------------------


def test_groesser_ziehen_behaelt_das_gezeichnete() -> None:
    """Der Punkt, um den es bei `PaintBox` überhaupt geht: wer nur im
    `paintEvent` malt, verliert alles bei der ersten Größenänderung."""
    _formular, box = _flaeche()
    box.canvas.brush.color = BLAU
    box.canvas.rectangle(10, 10, 60, 50)
    assert _farbe(box, 30, 30) == BLAU

    box.width = 300
    box.height = 220

    assert box.canvas.width == 300
    assert _farbe(box, 30, 30) == BLAU, "das Rechteck muss die Größenänderung überleben"
    assert _farbe(box, 250, 200) == WEISS, "die neue Fläche ist weiß"


def test_neuzeichnen_des_widgets_behaelt_das_gezeichnete() -> None:
    """Ein Fenster, das darüberfährt, löst `paintEvent` aus. Das Bild
    liegt im Pixmap und muss das überstehen."""
    _formular, box = _flaeche()
    box.canvas.pen.color = ROT
    box.canvas.line(10, 20, 100, 20)

    box._qwidget.render(box._qwidget.grab())  # erzwingt einen paintEvent
    assert _farbe(box, 50, 20) == ROT


def test_on_paint_wird_bei_groessenaenderung_ausgeloest() -> None:
    _formular, box = _flaeche()
    gerufen: list[object] = []
    box.on_paint = lambda sender: gerufen.append(sender)

    box.width = 240

    assert gerufen == [box]


def test_repaint_loest_on_paint_von_hand_aus() -> None:
    _formular, box = _flaeche()
    gerufen: list[object] = []
    box.on_paint = lambda sender: gerufen.append(sender)

    box.repaint()

    assert gerufen == [box]


def test_ohne_on_paint_passiert_bei_groessenaenderung_nichts_schlimmes() -> None:
    _formular, box = _flaeche()
    box.width = 240
    assert box.canvas.width == 240


# -- Fehler, die Lernenden passieren ------------------------------------


def test_eine_nicht_vorhandene_farbe_wird_deutsch_abgelehnt() -> None:
    _formular, box = _flaeche()
    with pytest.raises(NatterPropertyError, match="ist keine Farbe"):
        box.canvas.pen.color = "knallrot"


def test_eine_farbe_muss_text_sein() -> None:
    _formular, box = _flaeche()
    with pytest.raises(NatterPropertyError, match="Text"):
        box.canvas.brush.color = 16711680


def test_eine_unbekannte_fuellart_wird_deutsch_abgelehnt() -> None:
    _formular, box = _flaeche()
    with pytest.raises(NatterPropertyError, match="solid"):
        box.canvas.brush.style = "gestreift"


def test_stiftbreite_null_wird_abgelehnt() -> None:
    _formular, box = _flaeche()
    with pytest.raises(NatterPropertyError, match="ab 1"):
        box.canvas.pen.width = 0


def test_text_out_mit_einer_zahl_nennt_den_erwarteten_typ() -> None:
    _formular, box = _flaeche()
    with pytest.raises(NatterPropertyError, match="Text"):
        box.canvas.text_out(10, 10, 42)


def test_ein_punkt_ausserhalb_der_flaeche_nennt_die_groesse() -> None:
    _formular, box = _flaeche()
    with pytest.raises(NatterPropertyError, match="120 x 90"):
        _ = box.canvas.pixels[500, 500]
