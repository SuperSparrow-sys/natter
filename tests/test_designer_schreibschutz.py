"""Punkt 235: ein Formular, dessen `.pfm` sich nicht schreiben lässt.

Bis dahin endete jede Änderung im Designer mit einem `PermissionError`
aus dem Designer heraus. Jetzt meldet der Designer das einmal, der
Reiter führt die Änderung als ungespeichert, und Strg+S schreibt sie,
sobald die Datei wieder beschreibbar ist.

Die Datei ist eine Kopie in `tmp_path`; der Designer schreibt jede
Änderung zurück.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from pcl import Button

_VORLAGE = (
    Path(__file__).resolve().parent.parent
    / "beispielprojekte"
    / "03_Taschenrechner"
)


@pytest.fixture
def meldungen(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    from PySide6.QtWidgets import QMessageBox

    gesammelt: list[str] = []

    def warnung(_eltern, _titel, text, *_rest, **_benannt):  # noqa: ANN001, ANN002, ANN003, ANN202
        gesammelt.append(text)
        return QMessageBox.StandardButton.Ok

    monkeypatch.setattr(QMessageBox, "warning", warnung)
    return gesammelt


def test_schreibgeschuetzte_pfm_meldet_statt_abzustuerzen(
    tmp_path: Path, hauptfenster, meldungen: list[str]
) -> None:
    ordner = tmp_path / "03_Taschenrechner"
    shutil.copytree(_VORLAGE, ordner)
    pfm = ordner / "u_main.pfm"
    hauptfenster.designer_oeffnen(pfm)
    canvas = hauptfenster._offene_canvases[0]
    vorher = pfm.read_bytes()
    pfm.chmod(0o444)
    try:
        canvas.komponente_platzieren(Button, 10, 10)
        canvas.jetzt_schreiben()
        canvas.komponente_platzieren(Button, 10, 60)
        canvas.jetzt_schreiben()

        assert len(meldungen) == 1
        assert "u_main.pfm" in meldungen[0]
        assert "nicht gespeichert" in meldungen[0]
        assert pfm.read_bytes() == vorher
        assert canvas.ungespeichert
        assert hauptfenster.editor_tabs.tabText(0) == "u_main (Designer) ●"
        assert canvas.kommandos.kann_rueckgaengig
    finally:
        pfm.chmod(0o666)

    assert hauptfenster._aktuelle_datei_speichern()

    assert not canvas.ungespeichert
    assert hauptfenster.editor_tabs.tabText(0) == "u_main (Designer)"
    assert pfm.read_bytes() != vorher
    assert len(meldungen) == 1
