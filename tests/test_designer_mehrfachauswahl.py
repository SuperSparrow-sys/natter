"""Mehrfachauswahl, Kopieren und Einfügen im Designer (Punkt 73).

Bis 0.3.5 war immer nur eine Komponente ausgewählt, und Ausschneiden,
Kopieren und Einfügen waren im Designer grau.
"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest

from ide.designer.canvas import DesignerCanvas
from ide.designer.pfm_schreiben import pfm_aus_formular
from ide.inspector.komponentenbaum import kind_komponenten
from pcl import Button, Edit, Form, ListBox, Panel


class _Formular(Form):
    def create_components(self) -> None:
        self.b_ok = Button(self)
        self.b_ok.left, self.b_ok.top = 16, 16
        self.e_name = Edit(self)
        self.e_name.left, self.e_name.top = 16, 56
        self.lb_liste = ListBox(self)
        self.lb_liste.left, self.lb_liste.top = 200, 16
        self.lb_liste.items.add("Apfel")
        self.p_rand = Panel(self)
        self.p_rand.left, self.p_rand.top = 16, 160
        self.p_rand.width, self.p_rand.height = 200, 120
        self.b_innen = Button(self.p_rand)
        self.b_innen.left, self.b_innen.top = 8, 8


class _Zweites(Form):
    pass


def _canvas(qtbot, formular: Form, tmp_path: Path | None = None) -> DesignerCanvas:  # noqa: ANN001
    qtbot.addWidget(formular._qwidget)
    formular._qwidget.resize(480, 360)
    formular._qwidget.show()
    pfm = None
    if tmp_path is not None:
        pfm = tmp_path / "u_main.pfm"
        pfm.write_text(json.dumps(pfm_aus_formular(formular)), encoding="utf-8")
    return DesignerCanvas(formular, pfm_pfad=pfm)


def _namen(objekt) -> list[str]:  # noqa: ANN001
    return [name for name, _ in kind_komponenten(objekt)]


def test_strg_klick_waehlt_mehrere(qtbot) -> None:  # noqa: ANN001
    formular = _Formular()
    canvas = _canvas(qtbot, formular)

    QTest.mouseClick(formular.b_ok._qwidget, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        formular.e_name._qwidget, Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.ControlModifier,
    )

    assert canvas.ausgewaehlte_komponenten() == [formular.b_ok, formular.e_name]
    assert canvas.ausgewaehlte_komponente is formular.e_name

    QTest.mouseClick(
        formular.b_ok._qwidget, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ShiftModifier
    )
    assert canvas.ausgewaehlte_komponenten() == [formular.e_name]


def test_rahmen_aufziehen(qtbot) -> None:  # noqa: ANN001
    formular = _Formular()
    canvas = _canvas(qtbot, formular)

    QTest.mousePress(formular._qwidget, Qt.MouseButton.LeftButton, pos=QPoint(4, 4))
    canvas._band_ziehen(QPoint(150, 100))
    canvas._band_beenden(QPoint(150, 100))

    assert set(canvas.ausgewaehlte_komponenten()) == {formular.b_ok, formular.e_name}


def test_pfeiltaste_und_entf_wirken_auf_alle(qtbot, tmp_path: Path) -> None:  # noqa: ANN001
    formular = _Formular()
    canvas = _canvas(qtbot, formular, tmp_path)
    canvas.auswahl_setzen([formular.b_ok, formular.e_name])

    canvas.verschieben(8, 0)
    assert (formular.b_ok.left, formular.e_name.left) == (24, 24)
    canvas.rueckgaengig()
    assert (formular.b_ok.left, formular.e_name.left) == (16, 16)

    canvas.auswahl_setzen([formular.b_ok, formular.e_name])
    canvas.loeschen()
    assert _namen(formular) == ["lb_liste", "p_rand"]
    canvas.rueckgaengig()
    assert set(_namen(formular)) == {"b_ok", "e_name", "lb_liste", "p_rand"}


def test_gemeinsam_ziehen(qtbot) -> None:  # noqa: ANN001
    formular = _Formular()
    canvas = _canvas(qtbot, formular)
    canvas.auswahl_setzen([formular.b_ok, formular.e_name])

    QTest.mousePress(formular.e_name._qwidget, Qt.MouseButton.LeftButton, pos=QPoint(5, 5))
    for mit in canvas._ziehen_gruppe:
        mit.left += 32
    formular.e_name.left += 32
    canvas._ziehen_beenden()

    assert (formular.b_ok.left, formular.e_name.left) == (48, 48)
    canvas.rueckgaengig()
    assert (formular.b_ok.left, formular.e_name.left) == (16, 16)


def test_kopieren_und_einfuegen_ins_selbe_formular(qtbot, tmp_path: Path) -> None:  # noqa: ANN001
    formular = _Formular()
    canvas = _canvas(qtbot, formular, tmp_path)
    canvas.auswahl_setzen([formular.lb_liste, formular.p_rand])

    assert canvas.kopieren()
    neu = canvas.einfuegen()

    namen = _namen(formular)
    assert "lb_liste_kopie" in namen and "p_rand_kopie" in namen
    kopie = formular.lb_liste_kopie
    assert list(kopie.items) == ["Apfel"]
    assert (kopie.left, kopie.top) != (formular.lb_liste.left, formular.lb_liste.top)
    # Der Knopf im Panel kam mit und liegt in der Kopie des Panels.
    assert _namen(formular.p_rand_kopie) == ["b_innen_kopie"]
    assert canvas.ausgewaehlte_komponenten() == neu
    canvas.jetzt_schreiben()
    gespeichert = json.loads((tmp_path / "u_main.pfm").read_text(encoding="utf-8"))
    assert "lb_liste_kopie" in [k["name"] for k in gespeichert["children"]]

    canvas.rueckgaengig()
    assert "lb_liste_kopie" not in _namen(formular)


def test_einfuegen_in_ein_anderes_formular(qtbot) -> None:  # noqa: ANN001
    quelle = _Formular()
    canvas_quelle = _canvas(qtbot, quelle)
    canvas_quelle.auswahl_setzen([quelle.b_ok])
    quelle.b_ok.caption = "Weiter"
    canvas_quelle.kopieren()

    ziel = _Zweites()
    canvas_ziel = _canvas(qtbot, ziel)
    canvas_ziel.einfuegen()

    assert _namen(ziel) == ["b_ok"]
    assert ziel.b_ok.caption == "Weiter"


def test_ausschneiden(qtbot) -> None:  # noqa: ANN001
    formular = _Formular()
    canvas = _canvas(qtbot, formular)
    canvas.auswahl_setzen([formular.b_ok])

    assert canvas.ausschneiden()
    assert "b_ok" not in _namen(formular)
    canvas.einfuegen()
    assert "b_ok" in _namen(formular)


def test_strg_a_waehlt_alles(qtbot) -> None:  # noqa: ANN001
    formular = _Formular()
    canvas = _canvas(qtbot, formular)

    canvas.alles_auswaehlen()

    assert set(canvas.ausgewaehlte_komponenten()) == {
        formular.b_ok, formular.e_name, formular.lb_liste, formular.p_rand,
    }


def test_einfuegen_in_einen_ausgewaehlten_behaelter(qtbot) -> None:  # noqa: ANN001
    formular = _Formular()
    canvas = _canvas(qtbot, formular)
    canvas.auswahl_setzen([formular.b_ok])
    canvas.kopieren()

    canvas.auswahl_setzen([formular.p_rand])
    canvas.einfuegen()

    assert "b_ok_kopie" in _namen(formular.p_rand)


def test_geloeschter_behaelter_gibt_die_namen_frei(qtbot, tmp_path: Path) -> None:  # noqa: ANN001
    """Punkt 109: die Namen des Inhalts blieben am Formular hängen."""
    formular = _Formular()
    canvas = _canvas(qtbot, formular, tmp_path)

    canvas.loeschen(formular.p_rand)

    assert not hasattr(formular, "b_innen")
    assert canvas._eindeutigen_namen_finden("b_innen") == "b_innen"
    canvas.rueckgaengig()
    assert formular.b_innen.eltern is formular.p_rand
    assert _namen(formular.p_rand) == ["b_innen"]
