"""Tastatur-Ereignisse, `visible` und `on_close` (offener Punkt 54).

Die Regel für die Tastatur: das Formular bekommt jede Taste in seinem
Fenster, eine Komponente nur die, die sie mit dem Fokus bekommt. Beide
melden sich, zuerst das Formular.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from ide.codegen.design import design_code_erzeugen
from ide.designer.canvas import DesignerCanvas
from ide.designer.laden import formular_fuer_designer_laden
from ide.designer.pfm_schreiben import pfm_aus_formular
from ide.inspector.ereignisse_tabelle import passende_methoden
from pcl import Button, Edit, Form, Label, Panel, Shape, Timer
from pcl.control import EREIGNIS_PARAMETER, tastenname
from pcl.properties import eigenschaften, ereignisse


class _Spiel(Form):
    """Das Beispiel aus der Komponenten-Referenz: die Pfeiltasten
    schieben eine Figur über das Formular."""

    def create_components(self) -> None:
        self.gemeldet: list[tuple[str, str]] = []
        self.s_figur = Shape(self)
        self.s_figur.left = 100
        self.s_figur.top = 100
        self.p_rahmen = Panel(self)
        self.p_rahmen.left = 300
        self.b_ok = Button(self.p_rahmen)
        self.e_name = Edit(self)
        self.e_name.top = 250
        self.on_key_press = self.form_key_press
        self.b_ok.on_key_press = lambda s, t: self.gemeldet.append(("b_ok", t))
        self.p_rahmen.on_key_press = lambda s, t: self.gemeldet.append(
            ("p_rahmen", t)
        )
        self.e_name.on_key_press = lambda s, t: self.gemeldet.append(
            ("e_name", t)
        )

    def form_key_press(self, sender, taste):
        self.gemeldet.append(("form", taste))
        if taste == "Links":
            self.s_figur.left -= 10
        elif taste == "Rechts":
            self.s_figur.left += 10
        elif taste == "Oben":
            self.s_figur.top -= 10
        elif taste == "Unten":
            self.s_figur.top += 10


@pytest.fixture
def spiel():
    fenster = _Spiel()
    fenster.show()
    fenster._qwidget.activateWindow()
    QApplication.processEvents()
    yield fenster
    fenster._qwidget.hide()


def _fokus(widget) -> None:
    widget.setFocus()
    QApplication.processEvents()
    assert widget.hasFocus()


# ------------------------------------------------------ Tastennamen


@pytest.mark.parametrize(
    ("taste", "text", "name"),
    [
        (Qt.Key.Key_A, "a", "A"),
        (Qt.Key.Key_Z, "Z", "Z"),
        (Qt.Key.Key_7, "7", "7"),
        (Qt.Key.Key_Return, "\r", "Eingabe"),
        (Qt.Key.Key_Enter, "\r", "Eingabe"),
        (Qt.Key.Key_Space, " ", "Leertaste"),
        (Qt.Key.Key_Left, "", "Links"),
        (Qt.Key.Key_Right, "", "Rechts"),
        (Qt.Key.Key_Up, "", "Oben"),
        (Qt.Key.Key_Down, "", "Unten"),
        (Qt.Key.Key_Escape, "\x1b", "Esc"),
        (Qt.Key.Key_Tab, "\t", "Tab"),
        (Qt.Key.Key_Backspace, "\x08", "Rücktaste"),
        (Qt.Key.Key_Delete, "", "Entf"),
        (Qt.Key.Key_Home, "", "Pos1"),
        (Qt.Key.Key_End, "", "Ende"),
        (Qt.Key.Key_PageUp, "", "Bild auf"),
        (Qt.Key.Key_PageDown, "", "Bild ab"),
        (Qt.Key.Key_Insert, "", "Einfg"),
        (Qt.Key.Key_F1, "", "F1"),
        (Qt.Key.Key_F12, "", "F12"),
        (Qt.Key.Key_Plus, "+", "+"),
        (Qt.Key.Key_Adiaeresis, "ä", "Ä"),
        (Qt.Key.Key_ssharp, "ß", "ß"),
    ],
)
def test_tastennamen_sind_deutsch(taste, text, name) -> None:
    assert tastenname(taste, text) == name


def test_umschalt_allein_meldet_nichts() -> None:
    assert tastenname(Qt.Key.Key_Shift, "") is None
    assert tastenname(Qt.Key.Key_Control, "") is None


# ------------------------------------------ Formular und Komponente


def test_pfeiltasten_bewegen_die_figur(spiel) -> None:
    """Das Formular hört die Pfeiltasten, auch wenn das Eingabefeld
    den Fokus hat."""
    _fokus(spiel.e_name._qwidget)

    QTest.keyClick(spiel.e_name._qwidget, Qt.Key.Key_Left)
    QTest.keyClick(spiel.e_name._qwidget, Qt.Key.Key_Down)
    QTest.keyClick(spiel.e_name._qwidget, Qt.Key.Key_Down)

    assert (spiel.s_figur.left, spiel.s_figur.top) == (90, 120)
    assert spiel.s_figur._qwidget.geometry().topLeft().toTuple() == (90, 120)


def test_erst_das_formular_dann_die_komponente(spiel) -> None:
    _fokus(spiel.e_name._qwidget)

    QTest.keyClick(spiel.e_name._qwidget, Qt.Key.Key_Return)

    assert spiel.gemeldet == [("form", "Eingabe"), ("e_name", "Eingabe")]


def test_ein_behaelter_meldet_nicht_die_tasten_seines_kinds(spiel) -> None:
    """Ein Knopf will „A“ nicht haben, Qt reicht die Taste an das
    Panel weiter. Das Panel hat aber nicht den Fokus."""
    _fokus(spiel.b_ok._qwidget)

    QTest.keyClick(spiel.b_ok._qwidget, Qt.Key.Key_A)

    assert spiel.gemeldet == [("form", "A"), ("b_ok", "A")]


def test_ohne_fokus_im_fenster_hoert_das_formular_trotzdem() -> None:
    class _NurText(Form):
        def create_components(self) -> None:
            self.gemeldet: list[str] = []
            self.l_info = Label(self)
            self.on_key_press = lambda s, t: self.gemeldet.append(t)

    fenster = _NurText()
    fenster.show()
    fenster._qwidget.activateWindow()
    QApplication.processEvents()
    fokus = QApplication.focusWidget()
    if fokus is not None:
        fokus.clearFocus()
    try:
        QApplication.sendEvent(
            fenster._qwidget,
            QKeyEvent(
                QEvent.Type.KeyPress,
                Qt.Key.Key_Space,
                Qt.KeyboardModifier.NoModifier,
                " ",
            ),
        )
        assert fenster.gemeldet == ["Leertaste"]
    finally:
        fenster._qwidget.hide()


def test_on_close_meldet_das_schliessen() -> None:
    class _Fenster(Form):
        def create_components(self) -> None:
            self.geschlossen: list[object] = []
            self.on_close = self.geschlossen.append

    fenster = _Fenster()
    fenster.show()
    fenster.close()

    assert fenster.geschlossen == [fenster]


# ------------------------------------------------------------ visible


def test_visible_blendet_aus_und_wieder_ein(spiel) -> None:
    assert spiel.b_ok.visible is True
    spiel.b_ok.visible = False
    assert not spiel.b_ok._qwidget.isVisible()
    spiel.b_ok.visible = True
    assert spiel.b_ok._qwidget.isVisible()


def test_visible_false_vor_dem_anzeigen_bleibt_verborgen() -> None:
    class _Fenster(Form):
        def create_components(self) -> None:
            self.b_geheim = Button(self)
            self.b_geheim.visible = False

    fenster = _Fenster()
    fenster.show()
    try:
        assert not fenster.b_geheim._qwidget.isVisible()
    finally:
        fenster._qwidget.hide()


def test_ein_zeitgeber_kennt_weder_visible_noch_tasten() -> None:
    assert "visible" not in eigenschaften(Timer)
    assert "on_key_press" not in ereignisse(Timer)


def test_jede_sichtbare_komponente_und_das_formular_haben_die_tastatur() -> None:
    assert "on_key_press" in ereignisse(Button)
    assert "visible" in eigenschaften(Button)
    assert {"on_key_press", "on_close"} <= set(ereignisse(Form))
    assert EREIGNIS_PARAMETER["on_key_press"] == ("taste",)


# ------------------------------------------------- Designer und Code


_PFM = {
    "format": "pfm/1",
    "class": "TFenster",
    "type": "Form",
    "properties": {},
    "events": {"on_key_press": "form_key_press", "on_close": "form_close"},
    "children": [
        {
            "name": "b_geheim",
            "type": "Button",
            "properties": {"visible": False},
            "events": {"on_key_press": "b_geheim_key_press"},
        }
    ],
}


def test_codegen_schreibt_visible_und_die_ereignisse() -> None:
    code = design_code_erzeugen(_PFM, "u_fenster.pfm")

    assert "self.b_geheim.visible = False" in code
    assert "self.on_key_press = self.form_key_press" in code
    assert "self.on_close = self.form_close" in code
    assert "self.b_geheim.on_key_press = self.b_geheim_key_press" in code


def test_im_designer_bleibt_eine_verborgene_komponente_sichtbar(
    tmp_path: Path,
) -> None:
    pfm_pfad = tmp_path / "u_fenster.pfm"
    pfm_pfad.write_text(json.dumps(_PFM), encoding="utf-8")

    formular = formular_fuer_designer_laden(pfm_pfad)
    formular.show()
    try:
        assert formular.b_geheim.visible is False
        assert formular.b_geheim._qwidget.isVisible()
        # Und zurück in die .pfm geht der eingestellte Wert, nicht das,
        # was der Designer zeigt.
        daten = pfm_aus_formular(formular)
        assert daten["children"][0]["properties"] == {"visible": False}
        assert daten["events"] == _PFM["events"]
    finally:
        formular._qwidget.hide()


def test_doppelklick_legt_die_methode_mit_taste_an(tmp_path: Path) -> None:
    unit_pfad = tmp_path / "test.py"
    unit_pfad.write_text(
        "from u_main_design import Form1Design\n\n\n"
        "class _Formular(Form1Design):\n    pass\n",
        encoding="utf-8",
    )

    class _Formular(Form):
        def create_components(self) -> None:
            self.b_ein = Button(self)

    formular = _Formular()
    canvas = DesignerCanvas(formular, pfm_pfad=tmp_path / "test.pfm")

    name = canvas.ereignis_handler_erzeugen(formular, "on_key_press")

    assert name == "form_key_press"
    baum = ast.parse(unit_pfad.read_text(encoding="utf-8"))
    methode = next(
        k for k in ast.walk(baum)
        if isinstance(k, ast.FunctionDef) and k.name == name
    )
    assert [p.arg for p in methode.args.args] == ["self", "sender", "taste"]
    assert formular.on_key_press.__name__ == name


def test_die_auswahl_bietet_methoden_mit_taste_an() -> None:
    class _Formular(Form):
        def form_key_press(self, sender, taste):
            pass

        def b_ok_click(self, sender):
            pass

    assert passende_methoden(_Formular(), "on_key_press") == [
        "form_key_press"
    ]


def test_der_doppelklick_auf_eine_komponente_bleibt_beim_klick(
    tmp_path: Path,
) -> None:
    """`on_key_press` hat jede Komponente. Es darf dem Doppelklick im
    Designer nicht das kennzeichnende Ereignis wegnehmen."""
    (tmp_path / "test.py").write_text(
        "class _Formular:\n    pass\n", encoding="utf-8"
    )

    class _Formular(Form):
        def create_components(self) -> None:
            self.b_ein = Button(self)
            self.e_ein = Edit(self)

    formular = _Formular()
    canvas = DesignerCanvas(formular, pfm_pfad=tmp_path / "test.pfm")

    assert canvas.ereignis_handler_erzeugen(formular.b_ein) == "b_ein_click"
    assert canvas.ereignis_handler_erzeugen(formular.e_ein) == "e_ein_change"
