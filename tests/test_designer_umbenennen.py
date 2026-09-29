"""Tests für DesignerCanvas.komponente_umbenennen(): die Eigenschaft
„Name“ ändert den Attributnamen im Formular (Abschnitt 7.6). Headless.
Siehe Arbeitspaket M3, Schritt 8.
"""

from pathlib import Path

import pytest

from ide.designer.canvas import DesignerCanvas
from pcl import Button, Form


class _LeeresFormular(Form):
    pass


def test_umbenennen_aendert_das_attribut() -> None:
    formular = _LeeresFormular()
    canvas = DesignerCanvas(formular)
    komponente = canvas.komponente_platzieren(Button, 0, 0)

    canvas.komponente_umbenennen(komponente, "b_ein")

    assert not hasattr(formular, "button")
    assert formular.b_ein is komponente
    assert canvas._attributname(komponente) == "b_ein"


def test_umbenennen_auf_denselben_namen_ist_ein_no_op() -> None:
    formular = _LeeresFormular()
    canvas = DesignerCanvas(formular)
    komponente = canvas.komponente_platzieren(Button, 0, 0)

    canvas.komponente_umbenennen(komponente, "button")

    assert formular.button is komponente


def test_umbenennen_auf_vergebenen_namen_loest_fehler_aus() -> None:
    formular = _LeeresFormular()
    canvas = DesignerCanvas(formular)
    canvas.komponente_platzieren(Button, 0, 0)
    zweite = canvas.komponente_platzieren(Button, 20, 20)

    with pytest.raises(ValueError):
        canvas.komponente_umbenennen(zweite, "button")

    assert formular.button2 is zweite


def test_umbenennen_mit_ungueltigem_bezeichner_loest_fehler_aus() -> None:
    formular = _LeeresFormular()
    canvas = DesignerCanvas(formular)
    komponente = canvas.komponente_platzieren(Button, 0, 0)

    with pytest.raises(ValueError):
        canvas.komponente_umbenennen(komponente, "123 nicht gueltig")

    assert formular.button is komponente


def test_das_formular_selbst_kann_nicht_umbenannt_werden() -> None:
    formular = _LeeresFormular()
    canvas = DesignerCanvas(formular)

    with pytest.raises(ValueError):
        canvas.komponente_umbenennen(formular, "irgendwas")


def test_umbenennen_ist_rueckgaengig_machbar() -> None:
    formular = _LeeresFormular()
    canvas = DesignerCanvas(formular)
    komponente = canvas.komponente_platzieren(Button, 0, 0)
    canvas.komponente_umbenennen(komponente, "b_ein")

    canvas.rueckgaengig()

    assert formular.button is komponente
    assert not hasattr(formular, "b_ein")


def test_umbenannte_komponente_bleibt_im_ereignis_codegen_ansprechbar() -> None:
    formular = _LeeresFormular()
    canvas = DesignerCanvas(formular)
    komponente = canvas.komponente_platzieren(Button, 0, 0)
    canvas.komponente_umbenennen(komponente, "b_ein")

    assert canvas._attributname(komponente) == "b_ein"


# Lazarus zieht beim Umbenennen einer Komponente ihre Ereignismethoden
# mit. Natter tat das bis dahin nicht: aus `cb_ausgabe` wurde
# `cb_minus`, und im erzeugten Code stand weiter
# `self.cb_minus.on_change = self.cb_ausgabe_change`. Verknuepft war es
# richtig, zu lesen war es nicht.


def _formular_mit_ereignis(tmp_path: Path):
    """Ein Formular mit einer Checkbox, deren Methode Natter selbst
    angelegt hat."""
    import json

    from ide.designer.canvas import DesignerCanvas
    from ide.designer.laden import formular_fuer_designer_laden
    from pcl import CheckBox

    pfm = {
        "format": "pfm/1",
        "class": "Form1",
        "type": "Form",
        "properties": {"width": 480, "height": 360},
        "children": [],
    }
    (tmp_path / "u_main.pfm").write_text(json.dumps(pfm), encoding="utf-8")
    (tmp_path / "u_main.py").write_text(
        "from u_main_design import Form1Design\n\n\nclass Form1(Form1Design):\n    pass\n",
        encoding="utf-8",
    )
    formular = formular_fuer_designer_laden(tmp_path / "u_main.pfm")
    canvas = DesignerCanvas(formular, pfm_pfad=tmp_path / "u_main.pfm")
    haken = canvas.komponente_platzieren(CheckBox, 40, 40)
    canvas.komponente_umbenennen(haken, "cb_ausgabe")
    canvas.ereignis_handler_erzeugen(haken)
    return canvas, haken


def test_die_selbst_erzeugte_methode_wird_mit_umbenannt(tmp_path: Path) -> None:
    canvas, haken = _formular_mit_ereignis(tmp_path)
    assert "def cb_ausgabe_change" in (tmp_path / "u_main.py").read_text(encoding="utf-8")

    canvas.komponente_umbenennen(haken, "cb_minus")

    unit = (tmp_path / "u_main.py").read_text(encoding="utf-8")
    assert "def cb_minus_change(self, sender):" in unit
    assert "cb_ausgabe_change" not in unit
    design = (tmp_path / "u_main_design.py").read_text(encoding="utf-8")
    assert "self.cb_minus.on_change = self.cb_minus_change" in design


def test_rueckgaengig_holt_auch_den_methodennamen_zurueck(tmp_path: Path) -> None:
    canvas, haken = _formular_mit_ereignis(tmp_path)
    canvas.komponente_umbenennen(haken, "cb_minus")

    canvas.rueckgaengig()

    unit = (tmp_path / "u_main.py").read_text(encoding="utf-8")
    assert "def cb_ausgabe_change(self, sender):" in unit
    assert "cb_minus_change" not in unit


def test_eine_selbst_benannte_methode_bleibt_unangetastet(tmp_path: Path) -> None:
    """Nur was Natter angelegt hat, wird mit umbenannt - erkennbar am
    Namen `<komponente>_<ereignis>`. Einen Namen, den der Schüler
    selbst vergeben hat, fasst niemand an."""
    canvas, haken = _formular_mit_ereignis(tmp_path)
    quelltext = (tmp_path / "u_main.py").read_text(encoding="utf-8")
    (tmp_path / "u_main.py").write_text(
        quelltext.replace("cb_ausgabe_change", "ausgabe_umschalten"), encoding="utf-8"
    )
    import types

    from ide.designer.laden import platzhalter_erzeugen

    haken.on_change = types.MethodType(
        platzhalter_erzeugen("ausgabe_umschalten"), canvas.formular
    )

    canvas.komponente_umbenennen(haken, "cb_minus")

    unit = (tmp_path / "u_main.py").read_text(encoding="utf-8")
    assert "def ausgabe_umschalten(self, sender):" in unit
    design = (tmp_path / "u_main_design.py").read_text(encoding="utf-8")
    assert "self.cb_minus.on_change = self.ausgabe_umschalten" in design
