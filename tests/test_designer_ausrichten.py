"""Ausrichten, Verteilen, gleiche Größe und Rasterweite im Designer
(Punkt 105). Headless.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ide.designer.canvas import DesignerCanvas
from ide.designer.pfm_schreiben import pfm_aus_formular
from pcl import Button, Form, Panel


class _Formular(Form):
    def create_components(self) -> None:
        self.b_eins = Button(self)
        self.b_eins.left, self.b_eins.top = 16, 16
        self.b_eins.width, self.b_eins.height = 80, 25
        self.b_zwei = Button(self)
        self.b_zwei.left, self.b_zwei.top = 120, 60
        self.b_zwei.width, self.b_zwei.height = 100, 30
        self.b_drei = Button(self)
        self.b_drei.left, self.b_drei.top = 300, 100
        self.b_drei.width, self.b_drei.height = 60, 40
        self.p_rand = Panel(self)
        self.p_rand.left, self.p_rand.top = 16, 200
        self.p_rand.width, self.p_rand.height = 200, 100
        self.b_innen = Button(self.p_rand)
        self.b_innen.left, self.b_innen.top = 40, 8


def _canvas(qtbot, tmp_path: Path) -> DesignerCanvas:  # noqa: ANN001
    formular = _Formular()
    qtbot.addWidget(formular._qwidget)
    formular._qwidget.resize(480, 360)
    pfm = tmp_path / "u_main.pfm"
    pfm.write_text(json.dumps(pfm_aus_formular(formular)), encoding="utf-8")
    return DesignerCanvas(formular, pfm_pfad=pfm)


def _lagen(canvas: DesignerCanvas) -> dict[str, tuple[int, int, int, int]]:
    return {
        name: (k.left, k.top, k.width, k.height)
        for name, k in vars(canvas.formular).items()
        if name.startswith(("b_", "p_"))
    }


def _drei(canvas: DesignerCanvas) -> tuple:
    f = canvas.formular
    # Zuletzt gewählt ist der Bezug: b_zwei.
    canvas.auswahl_setzen([f.b_eins, f.b_drei, f.b_zwei])
    return f.b_eins, f.b_zwei, f.b_drei


@pytest.mark.parametrize(
    ("kante", "erwartet"),
    [
        ("links", {"b_eins": (120, 16), "b_drei": (120, 100)}),
        ("rechts", {"b_eins": (140, 16), "b_drei": (160, 100)}),
        ("oben", {"b_eins": (16, 60), "b_drei": (300, 60)}),
        ("unten", {"b_eins": (16, 65), "b_drei": (300, 50)}),
    ],
)
def test_ausrichten_an_der_zuletzt_gewaehlten(
    qtbot, tmp_path: Path, kante: str, erwartet: dict  # noqa: ANN001
) -> None:
    canvas = _canvas(qtbot, tmp_path)
    eins, zwei, drei = _drei(canvas)
    vorher = _lagen(canvas)

    assert canvas.ausrichten(kante)

    assert (eins.left, eins.top) == erwartet["b_eins"]
    assert (drei.left, drei.top) == erwartet["b_drei"]
    assert (zwei.left, zwei.top) == (120, 60)
    # Ein Schritt: ein Strg+Z stellt alles wieder her.
    canvas.rueckgaengig()
    assert _lagen(canvas) == vorher


def test_ausrichten_ueber_behaelter_hinweg(qtbot, tmp_path: Path) -> None:  # noqa: ANN001
    """Ein Knopf im Panel und einer auf dem Formular: verglichen wird
    in Formular-Koordinaten."""
    canvas = _canvas(qtbot, tmp_path)
    f = canvas.formular
    canvas.auswahl_setzen([f.b_innen, f.b_zwei])

    assert canvas.ausrichten("links")

    # Das Panel beginnt bei x=16, b_zwei bei x=120.
    assert f.b_innen.left == 120 - 16
    assert f.b_innen.eltern is f.p_rand


def test_waagerecht_verteilen(qtbot, tmp_path: Path) -> None:  # noqa: ANN001
    canvas = _canvas(qtbot, tmp_path)
    eins, zwei, drei = _drei(canvas)

    assert canvas.verteilen("waagerecht")

    # Von 16 bis 360 liegen 344 Pixel, belegt sind 240: zwei Lücken
    # zu je 52. b_eins und b_drei bleiben stehen.
    assert eins.left == 16
    assert zwei.left == 16 + 80 + 52
    assert drei.left == 300
    assert (eins.top, zwei.top, drei.top) == (16, 60, 100)


def test_senkrecht_verteilen(qtbot, tmp_path: Path) -> None:  # noqa: ANN001
    canvas = _canvas(qtbot, tmp_path)
    eins, zwei, drei = _drei(canvas)

    assert canvas.verteilen("senkrecht")

    # Von 16 bis 140 liegen 124 Pixel, belegt sind 95: zwei Lücken
    # zu je 14,5.
    assert eins.top == 16
    assert zwei.top == round(16 + 25 + 14.5)
    assert drei.top == 100


def test_verteilen_braucht_drei(qtbot, tmp_path: Path) -> None:  # noqa: ANN001
    canvas = _canvas(qtbot, tmp_path)
    f = canvas.formular
    canvas.auswahl_setzen([f.b_eins, f.b_zwei])

    assert not canvas.verteilen("waagerecht")
    assert not canvas.kommandos.kann_rueckgaengig


def test_gleiche_breite_und_hoehe(qtbot, tmp_path: Path) -> None:  # noqa: ANN001
    canvas = _canvas(qtbot, tmp_path)
    eins, zwei, drei = _drei(canvas)

    assert canvas.gleiche_groesse(breite=True)
    assert (eins.width, drei.width) == (100, 100)
    assert (eins.height, drei.height) == (25, 40)

    assert canvas.gleiche_groesse(hoehe=True)
    assert (eins.height, drei.height) == (30, 30)

    canvas.rueckgaengig()
    assert (eins.height, drei.height) == (25, 40)
    assert (eins.width, drei.width) == (100, 100)


def test_aenderung_landet_in_der_pfm(qtbot, tmp_path: Path) -> None:  # noqa: ANN001
    canvas = _canvas(qtbot, tmp_path)
    _drei(canvas)

    canvas.ausrichten("links")
    canvas.jetzt_schreiben()

    daten = json.loads(canvas.pfm_pfad.read_text(encoding="utf-8"))
    lagen = {k["name"]: k["properties"].get("left") for k in daten["children"]}
    assert lagen["b_eins"] == lagen["b_zwei"] == lagen["b_drei"] == 120


def _untermenue(menue, text: str):  # noqa: ANN001, ANN202
    return next(a.menu() for a in menue.actions() if a.text() == text)


def test_kontextmenue_bei_mehrfachauswahl(qtbot, tmp_path: Path) -> None:  # noqa: ANN001
    canvas = _canvas(qtbot, tmp_path)
    eins, zwei, drei = _drei(canvas)

    menue = canvas.kontextmenue_fuer(zwei)
    ausrichten = _untermenue(menue, "Ausrichten")

    assert ausrichten.isEnabled()
    texte = [a.text() for a in ausrichten.actions() if not a.isSeparator()]
    assert texte == [
        "Linke Kanten",
        "Rechte Kanten",
        "Obere Kanten",
        "Untere Kanten",
        "Waagerecht gleichmäßig verteilen",
        "Senkrecht gleichmäßig verteilen",
        "Gleiche Breite",
        "Gleiche Höhe",
    ]
    next(a for a in ausrichten.actions() if a.text() == "Obere Kanten").trigger()
    assert eins.top == drei.top == 60


def test_ausrichten_ist_bei_einer_komponente_grau(qtbot, tmp_path: Path) -> None:  # noqa: ANN001
    canvas = _canvas(qtbot, tmp_path)
    canvas.auswahl_setzen([canvas.formular.b_eins])

    menue = canvas.kontextmenue_fuer(canvas.formular.b_eins)

    assert not _untermenue(menue, "Ausrichten").isEnabled()


def test_rechtsklick_in_die_auswahl_behaelt_sie(qtbot, tmp_path: Path) -> None:  # noqa: ANN001
    canvas = _canvas(qtbot, tmp_path)
    eins, zwei, drei = _drei(canvas)

    canvas.rechtsklick_auswaehlen(eins)

    assert set(canvas.ausgewaehlte_komponenten()) == {eins, zwei, drei}
    assert canvas.ausgewaehlte_komponente is eins
    menue = canvas.kontextmenue_fuer(eins)
    assert _untermenue(menue, "Ausrichten").isEnabled()
    # Außerhalb der Auswahl: nur die angeklickte.
    canvas.rechtsklick_auswaehlen(canvas.formular.p_rand)
    assert canvas.ausgewaehlte_komponenten() == [canvas.formular.p_rand]


def test_rasterweite_aendert_die_pfeiltasten(qtbot, tmp_path: Path) -> None:  # noqa: ANN001
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QKeyEvent

    canvas = _canvas(qtbot, tmp_path)
    knopf = canvas.formular.b_eins
    canvas.auswahl_setzen([knopf])

    menue = canvas.kontextmenue_fuer(knopf)
    raster = _untermenue(menue, "Raster")
    assert [a.text() for a in raster.actions()] == ["4 Pixel", "8 Pixel", "16 Pixel"]
    assert [a.isChecked() for a in raster.actions()] == [False, True, False]
    raster.actions()[2].trigger()

    assert canvas.raster == 16
    assert canvas._raster_widget.raster == 16
    canvas.eventFilter(
        knopf._qwidget,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Right, Qt.KeyboardModifier.NoModifier),
    )
    assert knopf.left == 16 + 16
