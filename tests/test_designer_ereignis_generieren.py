"""Tests für DesignerCanvas.ereignis_handler_erzeugen(): Doppelklick
erzeugt eine Ereignis-Methode per libcst (Abschnitt 4.4). Headless. Siehe
docs/arbeitspakete/M3.md, Schritt 7.
"""

from pathlib import Path

from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent

from ide.designer.canvas import DesignerCanvas
from pcl import Button, Form, Shape


class _Formular(Form):
    def create_components(self) -> None:
        self.b_ein = Button(self)
        self.b_ein.left = 10
        self.b_ein.top = 10

        self.s_rahmen = Shape(self)  # kein Ereignis


_STARTINHALT = '''"""Testdatei."""

from u_main_design import Form1Design


class _Formular(Form1Design):
    pass
'''


def _unit_datei_vorbereiten(tmp_path: Path) -> Path:
    unit_pfad = tmp_path / "test.py"
    unit_pfad.write_text(_STARTINHALT, encoding="utf-8")
    return unit_pfad


def test_ohne_pfm_pfad_passiert_nichts() -> None:
    formular = _Formular()
    canvas = DesignerCanvas(formular)  # kein pfm_pfad -> kein unit_pfad
    canvas.klick_bei(15, 15)

    ergebnis = canvas.ereignis_handler_erzeugen(formular.b_ein)

    assert ergebnis is None
    assert formular.b_ein.on_click is None


def test_eine_shape_bekommt_seit_m15_ihren_klick(tmp_path: Path) -> None:
    """Hier stand bis M15 „Komponente ohne Ereignis liefert None": eine
    `Shape` hatte keines. Seit die Maus-Ereignisse in `Control` stehen,
    hat jede sichtbare Komponente `on_click` - auch eine Form, die man
    im Unterricht gern als Schaltfläche missbraucht."""
    _unit_datei_vorbereiten(tmp_path)
    formular = _Formular()
    canvas = DesignerCanvas(formular, pfm_pfad=tmp_path / "test.pfm")

    ergebnis = canvas.ereignis_handler_erzeugen(formular.s_rahmen)

    assert ergebnis == "s_rahmen_click"


def test_mehrere_eigene_ereignisse_bleiben_mehrdeutig(tmp_path: Path) -> None:
    """Beim `DBNavigator` wäre jede Wahl geraten - Einfügen, Löschen,
    Speichern und Abbrechen stehen gleichberechtigt nebeneinander."""
    from pcl import DBNavigator

    _unit_datei_vorbereiten(tmp_path)
    formular = _Formular()
    navigator = DBNavigator(formular)

    canvas = DesignerCanvas(formular, pfm_pfad=tmp_path / "test.pfm")

    assert canvas.ereignis_handler_erzeugen(navigator) is None


def test_erzeugt_methode_in_der_datei_und_verknuepft_sie(tmp_path: Path) -> None:
    unit_pfad = _unit_datei_vorbereiten(tmp_path)
    formular = _Formular()
    canvas = DesignerCanvas(formular, pfm_pfad=tmp_path / "test.pfm")

    ergebnis = canvas.ereignis_handler_erzeugen(formular.b_ein)

    assert ergebnis == "b_ein_click"
    assert "def b_ein_click(self, sender):" in unit_pfad.read_text(encoding="utf-8")
    assert formular.b_ein.on_click.__name__ == "b_ein_click"
    # aufrufbar, ohne einen Fehler auszulösen (reine Platzhalterwirkung)
    formular.b_ein.on_click(formular.b_ein)


def test_bereits_verknuepftes_ereignis_wird_nicht_neu_erzeugt(tmp_path: Path) -> None:
    unit_pfad = _unit_datei_vorbereiten(tmp_path)
    formular = _Formular()
    canvas = DesignerCanvas(formular, pfm_pfad=tmp_path / "test.pfm")
    canvas.ereignis_handler_erzeugen(formular.b_ein)
    inhalt_danach_erstem_mal = unit_pfad.read_text(encoding="utf-8")

    ergebnis = canvas.ereignis_handler_erzeugen(formular.b_ein)

    assert ergebnis == "b_ein_click"
    assert unit_pfad.read_text(encoding="utf-8") == inhalt_danach_erstem_mal


def test_pfm_wird_mit_dem_verknuepften_ereignis_gespeichert(tmp_path: Path) -> None:
    import json

    _unit_datei_vorbereiten(tmp_path)
    pfm_pfad = tmp_path / "test.pfm"
    formular = _Formular()
    canvas = DesignerCanvas(formular, pfm_pfad=pfm_pfad)

    canvas.ereignis_handler_erzeugen(formular.b_ein)

    daten = json.loads(pfm_pfad.read_text(encoding="utf-8"))
    kind = next(k for k in daten["children"] if k["name"] == "b_ein")
    assert kind["events"] == {"on_click": "b_ein_click"}


def test_rueckgaengig_entfernt_die_verknuepfung_aber_nicht_die_methode(tmp_path: Path) -> None:
    unit_pfad = _unit_datei_vorbereiten(tmp_path)
    formular = _Formular()
    canvas = DesignerCanvas(formular, pfm_pfad=tmp_path / "test.pfm")
    canvas.ereignis_handler_erzeugen(formular.b_ein)

    canvas.rueckgaengig()

    assert formular.b_ein.on_click is None
    assert "def b_ein_click(self, sender):" in unit_pfad.read_text(encoding="utf-8")


def test_echter_doppelklick_erzeugt_den_handler(tmp_path: Path) -> None:
    unit_pfad = _unit_datei_vorbereiten(tmp_path)
    formular = _Formular()
    canvas = DesignerCanvas(formular, pfm_pfad=tmp_path / "test.pfm")
    widget = formular.b_ein._qwidget

    druck = QMouseEvent(
        QEvent.Type.MouseButtonPress, QPointF(5, 5), QPointF(15, 15),
        Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
    )
    doppelklick = QMouseEvent(
        QEvent.Type.MouseButtonDblClick, QPointF(5, 5), QPointF(15, 15),
        Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
    )

    canvas.eventFilter(widget, druck)
    canvas.eventFilter(widget, doppelklick)

    assert "def b_ein_click(self, sender):" in unit_pfad.read_text(encoding="utf-8")
    assert formular.b_ein.on_click.__name__ == "b_ein_click"
    # der Doppelklick darf keinen Ziehvorgang hinterlassen
    assert canvas._ziehen_komponente is None


def test_doppelklick_auf_das_formular_erzeugt_form_create(tmp_path: Path) -> None:
    unit_pfad = _unit_datei_vorbereiten(tmp_path)
    formular = _Formular()
    canvas = DesignerCanvas(formular, pfm_pfad=tmp_path / "test.pfm")

    ergebnis = canvas.ereignis_handler_erzeugen(formular)

    assert ergebnis == "form_create"
    assert "def form_create(self, sender):" in unit_pfad.read_text(encoding="utf-8")
    assert formular.on_create.__name__ == "form_create"


def test_stringgrid_nennt_sein_kennzeichnendes_ereignis(tmp_path: Path) -> None:
    """Seit das `StringGrid` zwei eigene Ereignisse hat, wäre es sonst
    mehrdeutig geworden - und ein Doppelklick hätte gar nichts mehr
    angelegt. `standard_ereignis` sagt, welches gemeint ist: die
    Auswahl, wie `OnSelectCell` in Lazarus."""
    from pcl import StringGrid

    unit_pfad = _unit_datei_vorbereiten(tmp_path)
    formular = _Formular()
    formular.sg_tabelle = StringGrid(formular)
    canvas = DesignerCanvas(formular, pfm_pfad=tmp_path / "test.pfm")

    ergebnis = canvas.ereignis_handler_erzeugen(formular.sg_tabelle)

    assert ergebnis == "sg_tabelle_select_cell"
    # Die Methode traegt spalte und zeile, nicht nur sender.
    assert (
        "def sg_tabelle_select_cell(self, sender, spalte, zeile):"
        in unit_pfad.read_text(encoding="utf-8")
    )


# ----------------------------------------- Ein bestimmtes Ereignis
#
# Seit September 2026 nimmt `ereignis_handler_erzeugen` auch einen
# Ereignisnamen entgegen. So ruft der Reiter "Ereignisse" des
# Objektinspektors an, wo jede Zeile fuer sich steht - vorher liess
# sich dort nur verknuepfen, was schon da war.


def test_ein_bestimmtes_ereignis_laesst_sich_anlegen(tmp_path: Path) -> None:
    unit_pfad = _unit_datei_vorbereiten(tmp_path)
    formular = _Formular()
    canvas = DesignerCanvas(formular, pfm_pfad=tmp_path / "test.pfm")

    ergebnis = canvas.ereignis_handler_erzeugen(formular.b_ein, "on_double_click")

    assert ergebnis == "b_ein_double_click"
    assert "def b_ein_double_click(self, sender):" in unit_pfad.read_text(encoding="utf-8")


def test_die_signatur_stimmt_zum_ereignis(tmp_path: Path) -> None:
    """Der eigentliche Punkt: `on_mouse_down` bekommt `x` und `y`.

    Geprueft ueber den Syntaxbaum und nicht ueber eine Textsuche - eine
    Textsuche uebersaehe eine zusaetzliche Zeile Einrueckung genauso
    wie eine vertauschte Reihenfolge der Parameter.
    """
    import ast

    from pcl.control import EREIGNIS_PARAMETER

    unit_pfad = _unit_datei_vorbereiten(tmp_path)
    formular = _Formular()
    canvas = DesignerCanvas(formular, pfm_pfad=tmp_path / "test.pfm")

    for ereignis in ("on_mouse_down", "on_mouse_move", "on_mouse_up"):
        name = canvas.ereignis_handler_erzeugen(formular.b_ein, ereignis)
        assert name is not None, ereignis

    baum = ast.parse(unit_pfad.read_text(encoding="utf-8"))
    methoden = {
        knoten.name: [p.arg for p in knoten.args.args]
        for knoten in ast.walk(baum)
        if isinstance(knoten, ast.FunctionDef)
    }

    for ereignis, zusatz in EREIGNIS_PARAMETER.items():
        if not ereignis.startswith("on_mouse"):
            continue
        name = f"b_ein_{ereignis.removeprefix('on_')}"
        assert methoden[name] == ["self", "sender", *zusatz], name


def test_ein_fremdes_ereignis_wird_abgelehnt(tmp_path: Path) -> None:
    """Ein Button hat kein `on_timer`. Es anzulegen hiesse, eine Methode
    zu schreiben, die nie aufgerufen wird."""
    unit_pfad = _unit_datei_vorbereiten(tmp_path)
    formular = _Formular()
    canvas = DesignerCanvas(formular, pfm_pfad=tmp_path / "test.pfm")
    vorher = unit_pfad.read_text(encoding="utf-8")

    assert canvas.ereignis_handler_erzeugen(formular.b_ein, "on_timer") is None
    assert unit_pfad.read_text(encoding="utf-8") == vorher


def test_zweimal_dasselbe_ereignis_schreibt_nur_einmal(tmp_path: Path) -> None:
    unit_pfad = _unit_datei_vorbereiten(tmp_path)
    formular = _Formular()
    canvas = DesignerCanvas(formular, pfm_pfad=tmp_path / "test.pfm")

    erster = canvas.ereignis_handler_erzeugen(formular.b_ein, "on_mouse_up")
    nach_dem_ersten = unit_pfad.read_text(encoding="utf-8")
    zweiter = canvas.ereignis_handler_erzeugen(formular.b_ein, "on_mouse_up")

    assert erster == zweiter
    assert unit_pfad.read_text(encoding="utf-8") == nach_dem_ersten
