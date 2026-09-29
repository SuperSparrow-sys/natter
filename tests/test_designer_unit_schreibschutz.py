"""Eine Unit, die sich nicht schreiben oder nicht als UTF-8 lesen lässt
(Punkte 255 und 256).

Bis dahin endeten der Doppelklick im Reiter „Ereignisse“, das
Umbenennen einer Komponente und „Methode anlegen“ im Menü-Editor bei
einer schreibgeschützten Unit mit `PermissionError`, bei einer Unit in
Windows-1252 mit `UnicodeDecodeError`. Beim Umbenennen war die
Komponente zu diesem Zeitpunkt schon umbenannt. Eine Unit mit
Byte-Order-Markierung galt als Syntaxfehler in Zeile 1.
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest

from ide.designer.canvas import DesignerCanvas
from ide.designer.laden import formular_fuer_designer_laden, unit_methoden
from ide.inspector.menue_editor import MenueEditor, menue_methode_anlegen

_KOPF = (
    "# Rechnet für die Klasse\n"
    "from u_main_design import Form1Design\n\n\n"
    "class Form1(Form1Design):\n"
)
_METHODEN = "    def b_plus_click(self, sender):\n        pass\n"


def _projekt(tmp_path: Path, unit: bytes | None = None) -> DesignerCanvas:
    pfm = {
        "format": "pfm/1",
        "class": "Form1",
        "type": "Form",
        "properties": {"width": 480, "height": 360},
        "children": [
            {
                "name": "b_plus",
                "type": "Button",
                "properties": {"left": 16},
                "events": {"on_click": "b_plus_click"},
            },
            {"name": "b_minus", "type": "Button", "properties": {"left": 120}},
            {
                "name": "mm_haupt",
                "type": "MainMenu",
                "properties": {"entries": [{"name": "mi_ende", "caption": "&Ende"}]},
            },
        ],
    }
    pfm_pfad = tmp_path / "u_main.pfm"
    pfm_pfad.write_text(json.dumps(pfm), encoding="utf-8")
    if unit is None:
        unit = (_KOPF + _METHODEN).encode("utf-8")
    (tmp_path / "u_main.py").write_bytes(unit)
    return DesignerCanvas(formular_fuer_designer_laden(pfm_pfad), pfm_pfad=pfm_pfad)


@pytest.fixture
def meldungen(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    gesammelt: list[str] = []
    monkeypatch.setattr(
        "ide.designer.canvas.QMessageBox.warning",
        lambda _eltern, _titel, text, *a: gesammelt.append(text),
    )
    return gesammelt


@pytest.fixture
def schreibgeschuetzt(tmp_path: Path):
    """Setzt den Schreibschutz der Unit und nimmt ihn am Ende wieder
    weg, damit pytest den Ordner aufräumen kann."""
    unit = tmp_path / "u_main.py"

    def setzen() -> None:
        os.chmod(unit, stat.S_IREAD)

    yield setzen
    if unit.exists():
        os.chmod(unit, stat.S_IREAD | stat.S_IWRITE)


def _stimmig(tmp_path: Path, canvas: DesignerCanvas, unit_vorher: bytes) -> None:
    """Formular, `.pfm`, Unit und Rückgängig-Stapel sind unverändert."""
    pfm = json.loads((tmp_path / "u_main.pfm").read_text(encoding="utf-8"))
    namen = [k["name"] for k in pfm["children"]]
    assert namen == ["b_plus", "b_minus", "mm_haupt"]
    assert hasattr(canvas.formular, "b_plus")
    assert not hasattr(canvas.formular, "b_addieren")
    assert canvas.formular.b_plus.on_click.__name__ == "b_plus_click"
    assert canvas.formular.b_minus.on_click is None
    assert (tmp_path / "u_main.py").read_bytes() == unit_vorher
    assert not canvas.kommandos.kann_rueckgaengig


# ------------------------------------------------------------ Punkt 255


def test_methode_anlegen_bei_schreibschutz_meldet(
    tmp_path: Path, meldungen: list[str], schreibgeschuetzt
) -> None:
    canvas = _projekt(tmp_path)
    schreibgeschuetzt()
    unit_vorher = (tmp_path / "u_main.py").read_bytes()

    ergebnis = canvas.ereignis_handler_erzeugen(canvas.formular.b_minus)

    assert ergebnis is None
    assert len(meldungen) == 1
    assert "„u_main.py“ ist schreibgeschützt" in meldungen[0]
    _stimmig(tmp_path, canvas, unit_vorher)


def test_umbenennen_bei_schreibschutz_meldet(
    tmp_path: Path, schreibgeschuetzt
) -> None:
    canvas = _projekt(tmp_path)
    schreibgeschuetzt()
    unit_vorher = (tmp_path / "u_main.py").read_bytes()

    with pytest.raises(ValueError, match="„u_main.py“ ist schreibgeschützt"):
        canvas.komponente_umbenennen(canvas.formular.b_plus, "b_addieren")

    _stimmig(tmp_path, canvas, unit_vorher)


def test_umbenennen_setzt_das_formular_zurueck_wenn_das_schreiben_scheitert(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ein Netzlaufwerk verweigert das Schreiben auch ohne
    Schreibschutz-Merkmal an der Datei."""
    canvas = _projekt(tmp_path)
    unit_vorher = (tmp_path / "u_main.py").read_bytes()

    def verweigert(*_a, **_k) -> None:
        raise PermissionError(13, "Zugriff verweigert")

    monkeypatch.setattr("ide.designer.canvas.atomar_schreiben", verweigert)

    with pytest.raises(ValueError, match="behält ihren Namen"):
        canvas.komponente_umbenennen(canvas.formular.b_plus, "b_addieren")

    _stimmig(tmp_path, canvas, unit_vorher)
    # Die nächste Änderung schreibt die `.pfm` mit dem alten Namen.
    canvas.komponente_umbenennen(canvas.formular.b_minus, "b_weg")
    pfm = json.loads((tmp_path / "u_main.pfm").read_text(encoding="utf-8"))
    assert [k["name"] for k in pfm["children"]] == ["b_plus", "b_weg", "mm_haupt"]


def test_rueckgaengig_bei_inzwischen_schreibgeschuetzter_unit(
    tmp_path: Path, meldungen: list[str], schreibgeschuetzt
) -> None:
    canvas = _projekt(tmp_path)
    knopf = canvas.formular.b_plus
    canvas.komponente_umbenennen(knopf, "b_addieren")
    schreibgeschuetzt()
    unit_vorher = (tmp_path / "u_main.py").read_bytes()
    pfm_vorher = (tmp_path / "u_main.pfm").read_bytes()

    canvas.rueckgaengig()

    assert len(meldungen) == 1
    assert canvas._attributname(knopf) == "b_addieren"
    assert knopf.on_click.__name__ == "b_addieren_click"
    assert (tmp_path / "u_main.py").read_bytes() == unit_vorher
    assert (tmp_path / "u_main.pfm").read_bytes() == pfm_vorher
    # Der Schritt bleibt auf dem Stapel und geht, sobald die Datei
    # wieder beschreibbar ist.
    assert canvas.kommandos.kann_rueckgaengig
    os.chmod(tmp_path / "u_main.py", stat.S_IREAD | stat.S_IWRITE)
    canvas.rueckgaengig()
    assert canvas._attributname(knopf) == "b_plus"
    assert "def b_plus_click" in (tmp_path / "u_main.py").read_text(encoding="utf-8")


def test_menue_methode_anlegen_bei_schreibschutz_meldet(
    tmp_path: Path, meldungen: list[str], schreibgeschuetzt, qtbot
) -> None:
    canvas = _projekt(tmp_path)
    schreibgeschuetzt()
    unit_vorher = (tmp_path / "u_main.py").read_bytes()
    editor = MenueEditor(
        canvas.formular.mm_haupt.entries,
        methode_anlegen=lambda name: menue_methode_anlegen(canvas, name),
    )
    qtbot.addWidget(editor)
    editor.baum.setCurrentItem(editor.baum.topLevelItem(0))

    editor.anlegen_knopf.click()

    assert len(meldungen) == 1
    assert "„u_main.py“ ist schreibgeschützt" in meldungen[0]
    # Ohne Methode kein Name im Eintrag: sonst verwiese er nach „OK“
    # auf eine Methode, die es nicht gibt.
    assert editor.feld_on_click.text() == ""
    _stimmig(tmp_path, canvas, unit_vorher)


# ------------------------------------------------------------ Punkt 256


def test_unit_mit_bom_legt_eine_methode_an(
    tmp_path: Path, meldungen: list[str]
) -> None:
    bom = b"\xef\xbb\xbf" + (_KOPF + _METHODEN).encode("utf-8")
    canvas = _projekt(tmp_path, bom)

    assert "b_plus_click" in unit_methoden(tmp_path / "u_main.py", "Form1")
    name = canvas.ereignis_handler_erzeugen(canvas.formular.b_minus)

    assert meldungen == []
    assert name == "b_minus_click"
    text = (tmp_path / "u_main.py").read_text(encoding="utf-8-sig")
    assert "def b_minus_click(self, sender)" in text
    assert "def b_plus_click(self, sender)" in text
    canvas.komponente_umbenennen(canvas.formular.b_plus, "b_addieren")
    assert "def b_addieren_click" in (tmp_path / "u_main.py").read_text(
        encoding="utf-8-sig"
    )


def test_ansi_unit_wird_gemeldet(tmp_path: Path, meldungen: list[str]) -> None:
    ansi = (_KOPF + _METHODEN).encode("cp1252")
    canvas = _projekt(tmp_path, ansi)

    ergebnis = canvas.ereignis_handler_erzeugen(canvas.formular.b_minus)
    assert ergebnis is None
    assert len(meldungen) == 1
    assert "nicht in UTF-8 gespeichert" in meldungen[0]

    with pytest.raises(ValueError, match="nicht in UTF-8 gespeichert"):
        canvas.komponente_umbenennen(canvas.formular.b_plus, "b_addieren")

    assert menue_methode_anlegen(canvas, "mi_ende_click") is False
    assert len(meldungen) == 2
    _stimmig(tmp_path, canvas, ansi)
