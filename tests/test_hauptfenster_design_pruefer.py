"""Tests für die IDE-Verdrahtung des Design-Prüfers (Abschnitt 14).
Siehe docs/arbeitspakete/M7.md, Schritt 2. Ein eigenes, minimales `.pfm`
in `tmp_path` (nicht aus `beispielprojekte/`, weil `DesignerCanvas` bei
jeder Änderung automatisch zurückschreibt, siehe AGENTS.md).
"""

from __future__ import annotations

import json
from pathlib import Path

from ide.shell.hauptfenster import HauptFenster


def _pfm_schreiben(tmp_path: Path, *, button_left: int) -> Path:
    pfm = {
        "format": "pfm/1",
        "class": "Form1",
        "type": "Form",
        "properties": {"caption": "Form1", "width": 400, "height": 300},
        "children": [
            {
                "name": "b_a",
                "type": "Button",
                "properties": {"left": button_left, "top": 8, "width": 75, "height": 25},
            }
        ],
    }
    pfad = tmp_path / "u_main.pfm"
    pfad.write_text(json.dumps(pfm), encoding="utf-8")
    return pfad


def test_design_pruefen_ohne_offenen_designer_zeigt_hinweis() -> None:
    fenster = HauptFenster()

    fenster._design_pruefen_aktion()

    meldung = fenster.statusBar().currentMessage()
    assert meldung.startswith("Kein Formular-Designer geöffnet.")
    assert "Projekt-Explorer" in meldung


def test_design_pruefen_findet_komponente_ausserhalb_des_formulars(tmp_path: Path) -> None:
    pfad = _pfm_schreiben(tmp_path, button_left=380)
    fenster = HauptFenster()
    fenster.designer_oeffnen(pfad)

    fenster._design_pruefen_aktion()

    assert fenster.meldungen_liste.count() >= 1
    assert fenster.panels.currentWidget() is fenster.meldungen_liste
    assert "außerhalb" in fenster.meldungen_liste.item(0).text()


def test_design_pruefen_sauberes_formular_liefert_keine_funde(tmp_path: Path) -> None:
    pfad = _pfm_schreiben(tmp_path, button_left=8)
    fenster = HauptFenster()
    fenster.designer_oeffnen(pfad)

    fenster._design_pruefen_aktion()

    assert fenster.meldungen_liste.count() == 0


def test_klick_auf_befund_markiert_die_komponente_im_designer(tmp_path: Path) -> None:
    pfad = _pfm_schreiben(tmp_path, button_left=380)
    fenster = HauptFenster()
    formular = fenster.designer_oeffnen(pfad)
    fenster._design_pruefen_aktion()

    fenster.meldungen_liste.itemClicked.emit(fenster.meldungen_liste.item(0))

    canvas = fenster._offene_canvases[0]
    assert canvas.ausgewaehlte_komponente is formular.b_a


def test_design_pruefung_laeuft_automatisch_nach_einer_aenderung(tmp_path: Path) -> None:
    pfad = _pfm_schreiben(tmp_path, button_left=8)
    fenster = HauptFenster()
    formular = fenster.designer_oeffnen(pfad)
    canvas = fenster._offene_canvases[0]

    canvas.verschieben(1000, 0, formular.b_a)

    assert fenster.meldungen_liste.count() >= 1


def test_design_pruefung_automatisch_laesst_sich_abschalten(tmp_path: Path) -> None:
    pfad = _pfm_schreiben(tmp_path, button_left=8)
    fenster = HauptFenster()
    formular = fenster.designer_oeffnen(pfad)
    canvas = fenster._offene_canvases[0]
    fenster._design_pruefung_automatisch_aktion.qaction.setChecked(False)

    canvas.verschieben(1000, 0, formular.b_a)

    assert fenster.meldungen_liste.count() == 0
