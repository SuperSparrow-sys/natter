"""Bearbeiten einer Auswahl im Designer (Punkte 168, 169, 170, 172
und 180).

Gemeinsam ziehen, Ausschneiden und Einfügen, Löschen mit Rückgängig,
Verdoppeln und Größe ändern sollen für eine Auswahl dasselbe tun wie
für eine einzelne Komponente - und jeder Schritt muss sich mit einem
Strg+Z genau zurücknehmen lassen.
"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent

from ide.designer.canvas import RASTER, DesignerCanvas
from ide.designer.pfm_schreiben import pfm_aus_formular
from ide.inspector.komponentenbaum import kind_komponenten
from pcl import Button, Form, Panel, PopupMenu


class _Formular(Form):
    def create_components(self) -> None:
        self.b_1 = Button(self)
        self.b_1.left, self.b_1.top = 16, 16
        self.b_2 = Button(self)
        self.b_2.left, self.b_2.top = 16, 56
        self.b_3 = Button(self)
        self.b_3.left, self.b_3.top = 16, 96
        self.b_1.on_click = self.b_1_click
        self.p_rand = Panel(self)
        self.p_rand.left, self.p_rand.top = 200, 40
        self.p_rand.width, self.p_rand.height = 240, 200
        self.pm_knopf = PopupMenu(self)
        self.b_2.popup_menu = self.pm_knopf

    def b_1_click(self, sender) -> None:  # noqa: ANN001
        pass


class _Anderes(Form):
    pass


class _AnderesMitMenue(Form):
    def create_components(self) -> None:
        self.pm_knopf = PopupMenu(self)


def _canvas(qtbot, formular: Form, tmp_path: Path) -> DesignerCanvas:  # noqa: ANN001
    qtbot.addWidget(formular._qwidget)
    formular._qwidget.resize(480, 360)
    formular._qwidget.show()
    pfm = tmp_path / f"{type(formular).__name__.lower()}.pfm"
    pfm.write_text(json.dumps(pfm_aus_formular(formular)), encoding="utf-8")
    return DesignerCanvas(formular, pfm_pfad=pfm)


def _pfm(canvas: DesignerCanvas) -> dict:
    canvas.jetzt_schreiben()
    return json.loads(canvas.pfm_pfad.read_text(encoding="utf-8"))


def _kinder(eintrag: dict) -> list[str]:
    return [k["name"] for k in eintrag.get("children", [])]


def _eintrag(eintrag: dict, name: str) -> dict:
    for kind in eintrag.get("children", []):
        if kind["name"] == name:
            return kind
        gefunden = _eintrag(kind, name) if kind.get("children") else None
        if gefunden:
            return gefunden
    return {}


def _taste(canvas: DesignerCanvas, taste: int, modifikatoren) -> None:  # noqa: ANN001
    ziel = canvas.ausgewaehlte_komponente._qwidget
    canvas.eventFilter(ziel, QKeyEvent(QEvent.Type.KeyPress, taste, modifikatoren))


# ---------------------------------------------------------- Punkt 168


def test_gemeinsam_auf_ein_panel_gezogen_liegen_beide_darin(qtbot, tmp_path: Path) -> None:  # noqa: ANN001
    formular = _Formular()
    canvas = _canvas(qtbot, formular, tmp_path)
    canvas.auswahl_setzen([formular.b_1, formular.b_2])

    # Wie ein Ziehen mit der Maus: b_2 wird gegriffen, b_1 zieht mit.
    canvas._ziehen_komponente = formular.b_2
    canvas._ziehen_start_werte = {"left": 16, "top": 56}
    canvas._ziehen_gruppe = {formular.b_1: (16, 16)}
    for knopf in (formular.b_1, formular.b_2):
        knopf.left += 240
        knopf.top += 64
    canvas._ziehen_beenden()

    daten = _pfm(canvas)
    panel = _eintrag(daten, "p_rand")
    assert set(_kinder(panel)) == {"b_1", "b_2"}
    assert "b_1" not in _kinder(daten) and "b_2" not in _kinder(daten)
    assert formular.b_1.eltern is formular.p_rand
    assert (formular.b_1.left, formular.b_1.top) == (56, 40)

    canvas.rueckgaengig()
    assert formular.b_1.eltern is formular and formular.b_2.eltern is formular
    assert (formular.b_1.left, formular.b_1.top) == (16, 16)
    assert (formular.b_2.left, formular.b_2.top) == (16, 56)
    assert _kinder(_eintrag(_pfm(canvas), "p_rand")) == []

    canvas.wiederholen()
    assert set(_kinder(_eintrag(_pfm(canvas), "p_rand"))) == {"b_1", "b_2"}


# ---------------------------------------------------------- Punkt 169


def test_ausschneiden_und_einfuegen_behaelt_die_ereignisse(qtbot, tmp_path: Path) -> None:  # noqa: ANN001
    formular = _Formular()
    canvas = _canvas(qtbot, formular, tmp_path)
    canvas.auswahl_setzen([formular.b_1])

    assert canvas.ausschneiden()
    canvas.auswahl_setzen([formular.p_rand])
    neu = canvas.einfuegen()

    assert canvas._attributname(neu[0]) == "b_1"
    eintrag = _eintrag(_pfm(canvas), "b_1")
    assert eintrag["events"] == {"on_click": "b_1_click"}
    assert "b_1" in _kinder(_eintrag(_pfm(canvas), "p_rand"))

    canvas.rueckgaengig()
    assert "b_1" not in [n for n, _ in kind_komponenten(formular.p_rand)]


def test_in_einem_anderen_formular_fehlt_die_methode(qtbot, tmp_path: Path) -> None:  # noqa: ANN001
    quelle = _Formular()
    canvas_quelle = _canvas(qtbot, quelle, tmp_path)
    canvas_quelle.auswahl_setzen([quelle.b_1])
    canvas_quelle.kopieren()

    ziel = _Anderes()
    canvas_ziel = _canvas(qtbot, ziel, tmp_path)
    canvas_ziel.einfuegen()

    assert ziel.b_1.on_click is None
    assert "events" not in _eintrag(_pfm(canvas_ziel), "b_1")


# ---------------------------------------------------------- Punkt 170


def test_loeschen_und_rueckgaengig_behaelt_die_reihenfolge(qtbot, tmp_path: Path) -> None:  # noqa: ANN001
    formular = _Formular()
    canvas = _canvas(qtbot, formular, tmp_path)
    vorher = _kinder(_pfm(canvas))
    assert vorher[:3] == ["b_1", "b_2", "b_3"]

    canvas.loeschen(formular.b_1)
    canvas.rueckgaengig()
    assert _kinder(_pfm(canvas)) == vorher

    canvas.wiederholen()
    canvas.rueckgaengig()
    assert _kinder(_pfm(canvas)) == vorher

    canvas.auswahl_setzen([formular.b_1, formular.b_3])
    canvas.loeschen()
    assert _kinder(_pfm(canvas))[:1] == ["b_2"]
    canvas.rueckgaengig()
    assert _kinder(_pfm(canvas)) == vorher


# ---------------------------------------------------------- Punkt 172


def test_duplizieren_behaelt_das_klappmenue(qtbot, tmp_path: Path) -> None:  # noqa: ANN001
    formular = _Formular()
    canvas = _canvas(qtbot, formular, tmp_path)

    kopie = canvas.duplizieren(formular.b_2)

    assert kopie.popup_menu is formular.pm_knopf
    assert _eintrag(_pfm(canvas), "b_2_kopie")["properties"]["popup_menu"] == "pm_knopf"


def test_kopieren_und_einfuegen_behaelt_das_klappmenue(qtbot, tmp_path: Path) -> None:  # noqa: ANN001
    formular = _Formular()
    canvas = _canvas(qtbot, formular, tmp_path)
    canvas.auswahl_setzen([formular.b_2])
    canvas.kopieren()

    kopie = canvas.einfuegen()[0]

    assert kopie.popup_menu is formular.pm_knopf


def test_klappmenue_im_anderen_formular_nur_wenn_es_dort_eins_gibt(
    qtbot, tmp_path: Path  # noqa: ANN001
) -> None:
    quelle = _Formular()
    canvas_quelle = _canvas(qtbot, quelle, tmp_path)
    canvas_quelle.auswahl_setzen([quelle.b_2])
    canvas_quelle.kopieren()

    ohne = _Anderes()
    _canvas(qtbot, ohne, tmp_path).einfuegen()
    assert ohne.b_2.popup_menu is None

    mit = _AnderesMitMenue()
    _canvas(qtbot, mit, tmp_path).einfuegen()
    assert mit.b_2.popup_menu is mit.pm_knopf


def test_klappmenue_und_knopf_zusammen_kopiert(qtbot, tmp_path: Path) -> None:  # noqa: ANN001
    """Kommt das Menü mit, zeigt die Kopie des Knopfs auf die Kopie
    des Menüs."""
    formular = _Formular()
    canvas = _canvas(qtbot, formular, tmp_path)
    canvas.auswahl_setzen([formular.b_2, formular.pm_knopf])
    canvas.kopieren()

    canvas.einfuegen()

    assert formular.b_2_kopie.popup_menu is formular.pm_knopf_kopie


# ---------------------------------------------------------- Punkt 180


def test_umschalt_rechts_aendert_alle_breiten(qtbot, tmp_path: Path) -> None:  # noqa: ANN001
    formular = _Formular()
    canvas = _canvas(qtbot, formular, tmp_path)
    knoepfe = [formular.b_1, formular.b_2, formular.b_3]
    vorher = [k.width for k in knoepfe]
    canvas.auswahl_setzen(knoepfe)

    _taste(canvas, Qt.Key.Key_Right, Qt.KeyboardModifier.ShiftModifier)

    assert [k.width for k in knoepfe] == [b + RASTER for b in vorher]
    canvas.rueckgaengig()
    assert [k.width for k in knoepfe] == vorher


def test_strg_d_verdoppelt_die_ganze_auswahl(qtbot, tmp_path: Path) -> None:  # noqa: ANN001
    formular = _Formular()
    canvas = _canvas(qtbot, formular, tmp_path)
    canvas.auswahl_setzen([formular.b_1, formular.b_2, formular.b_3])

    _taste(canvas, Qt.Key.Key_D, Qt.KeyboardModifier.ControlModifier)

    namen = _kinder(_pfm(canvas))
    assert {"b_1_kopie", "b_2_kopie", "b_3_kopie"} <= set(namen)
    assert len(canvas.ausgewaehlte_komponenten()) == 3
    assert formular.b_1_kopie.on_click.__name__ == "b_1_click"

    canvas.rueckgaengig()
    assert not {"b_1_kopie", "b_2_kopie", "b_3_kopie"} & set(_kinder(_pfm(canvas)))
