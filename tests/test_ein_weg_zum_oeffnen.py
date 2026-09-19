"""Ein Weg zum Öffnen, nicht zwei (M11, Abschnitt 5).

Der Projekt-Explorer sah sich die Endung an und öffnete eine `.pfm` im
Designer, ein `.pdiag` im Diagramm-Editor, ein Bild in der Vorschau.
„Datei → Öffnen …“ tat das nicht: dort landete dieselbe `.pfm` als roher
JSON-Text im Quelltexteditor, das Diagramm ebenso – und ein PNG brachte
Natter mit einem `UnicodeDecodeError` ganz zum Absturz, weil niemand
damit rechnete, dass jemand ein Bild „öffnet“.

Zwei Wege zur selben Sache, die sich verschieden verhalten, sind
schlimmer als einer. Beide gehen jetzt durch `HauptFenster.oeffnen()`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings

from ide.shell.hauptfenster import HauptFenster


@pytest.fixture
def einstellungen(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> QSettings:
    datei = QSettings(str(tmp_path / "ide.ini"), QSettings.Format.IniFormat)
    import ide.pruefungsmodus as modul

    monkeypatch.setattr(modul, "einstellungen", lambda: datei)
    return datei


@pytest.fixture
def fenster(einstellungen: QSettings, qtbot) -> HauptFenster:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    return fenster


def _formular_anlegen(ordner: Path) -> Path:
    ordner.mkdir(parents=True, exist_ok=True)
    pfm = ordner / "u_haupt.pfm"
    pfm.write_text(
        json.dumps(
            {
                "format": "pfm/1",
                "class": "Form1",
                "type": "Form",
                "properties": {},
                "children": [
                    {"name": "b_ein", "type": "Button", "properties": {"left": 8, "top": 8}}
                ],
            }
        ),
        encoding="utf-8",
    )
    return pfm


def test_oeffnen_zeigt_ein_formular_im_designer(
    fenster: HauptFenster, tmp_path: Path
) -> None:
    """Über „Datei → Öffnen …“ stand hier vorher das rohe JSON."""
    pfm = _formular_anlegen(tmp_path / "p")

    fenster.oeffnen(pfm)

    assert fenster.editor_tabs.tabText(0) == "u_haupt (Designer)"
    assert fenster._aktueller_canvas is not None


def test_oeffnen_zeigt_ein_bild_in_der_vorschau(
    fenster: HauptFenster, tmp_path: Path
) -> None:
    """Ein PNG im Quelltexteditor war nicht nur unsinnig, sondern ein
    Absturz: `read_text` scheitert an den Binärdaten."""
    from PySide6.QtGui import QImage

    bild = tmp_path / "logo.png"
    QImage(4, 4, QImage.Format.Format_RGB32).save(str(bild), "PNG")

    fenster.oeffnen(bild)

    assert fenster.editor_tabs.count() == 1
    assert fenster.editor_tabs.tabText(0) == "logo.png"


def test_der_dialog_und_der_explorer_gehen_denselben_weg(
    fenster: HauptFenster, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Der eigentliche Punkt: „Datei → Öffnen …“ ruft dieselbe Stelle
    wie ein Doppelklick im Projekt-Explorer."""
    from PySide6.QtWidgets import QFileDialog

    pfm = _formular_anlegen(tmp_path / "p")
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", lambda *_a, **_k: (str(pfm), "")
    )

    fenster._datei_oeffnen_dialog()

    assert fenster.editor_tabs.tabText(0) == "u_haupt (Designer)"


def test_eine_nicht_lesbare_datei_meldet_sich_statt_abzustuerzen(
    fenster: HauptFenster, tmp_path: Path
) -> None:
    """Eine alte, nicht in UTF-8 gespeicherte Pascal-Datei oder eine
    `.exe` – vorher flog der `UnicodeDecodeError` bis nach oben durch."""
    datei = tmp_path / "alt.pas"
    datei.write_bytes(b"program Gru\xdf;\n")  # ISO-8859-1, kein UTF-8

    ergebnis = fenster.datei_oeffnen(datei)

    assert ergebnis is None
    assert fenster.editor_tabs.count() == 0
    meldung = fenster.statusBar().currentMessage()
    assert "alt.pas" in meldung
    assert "UTF-8" in meldung


def test_eine_gewoehnliche_unit_geht_weiter_in_den_editor(
    fenster: HauptFenster, tmp_path: Path
) -> None:
    datei = tmp_path / "u_hilfe.py"
    datei.write_text("x = 1\n", encoding="utf-8")

    fenster.oeffnen(datei)

    assert fenster.editor_tabs.tabText(0) == "u_hilfe.py"


def test_ein_beschaedigtes_formular_meldet_sich_statt_abzustuerzen(
    fenster: HauptFenster, tmp_path: Path
) -> None:
    """Eine von Hand verbogene oder abgeschnittene `.pfm` flog vorher
    als `JSONDecodeError` bis nach oben durch – in der gebauten Exe
    hieße das: Natter ist weg."""
    kaputt = tmp_path / "u_kaputt.pfm"
    kaputt.write_text('{"format": "pfm/1", "class": "Form1",', encoding="utf-8")

    fenster.oeffnen(kaputt)

    assert fenster.editor_tabs.count() == 0
    meldung = fenster.statusBar().currentMessage()
    assert "u_kaputt.pfm" in meldung
    assert "beschädigt" in meldung


def test_ein_formular_mit_falschem_inhalt_meldet_sich_auch(
    fenster: HauptFenster, tmp_path: Path
) -> None:
    """Gueltiges JSON, aber nicht das, was eine `.pfm` sein muss – das
    fängt das Schema ab."""
    kaputt = tmp_path / "u_falsch.pfm"
    kaputt.write_text('{"format": "pfm/1", "children": "keine Liste"}', encoding="utf-8")

    fenster.oeffnen(kaputt)

    assert fenster.editor_tabs.count() == 0
    assert "beschädigt" in fenster.statusBar().currentMessage()


def test_ein_beschaedigtes_diagramm_meldet_sich_ebenfalls(
    fenster: HauptFenster, tmp_path: Path
) -> None:
    kaputt = tmp_path / "ablauf.pdiag"
    kaputt.write_text("{kein json", encoding="utf-8")

    fenster.oeffnen(kaputt)

    assert "beschädigt" in fenster.statusBar().currentMessage()
