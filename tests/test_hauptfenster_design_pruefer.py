"""Tests für die IDE-Verdrahtung des Design-Prüfers (Abschnitt 14).
Siehe Arbeitspaket M7, Schritt 2. Ein eigenes, minimales `.pfm`
in `tmp_path` (nicht aus `beispielprojekte/`, weil `DesignerCanvas` bei
jeder Änderung automatisch zurückschreibt, siehe AGENTS.md).
"""

from __future__ import annotations

import json
from pathlib import Path


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


def test_design_pruefen_ohne_offenen_designer_zeigt_hinweis(hauptfenster) -> None:

    hauptfenster._design_pruefen_aktion()

    meldung = hauptfenster.statusBar().currentMessage()
    assert meldung.startswith("Kein Formular-Designer geöffnet.")
    assert "Projekt-Explorer" in meldung


def test_design_pruefen_findet_komponente_ausserhalb_des_formulars(
    tmp_path: Path, hauptfenster_bauen
) -> None:
    pfad = _pfm_schreiben(tmp_path, button_left=380)
    fenster = hauptfenster_bauen()
    fenster.designer_oeffnen(pfad)

    fenster._design_pruefen_aktion()

    assert fenster.meldungen_liste.count() >= 1
    assert fenster.panels.currentWidget() is fenster.meldungen_liste
    assert "außerhalb" in fenster.meldungen_liste.item(0).text()


def test_design_pruefen_sauberes_formular_liefert_keine_funde(
    tmp_path: Path, hauptfenster_bauen
) -> None:
    pfad = _pfm_schreiben(tmp_path, button_left=8)
    fenster = hauptfenster_bauen()
    fenster.designer_oeffnen(pfad)

    fenster._design_pruefen_aktion()

    assert fenster.meldungen_liste.count() == 0


def test_klick_auf_befund_markiert_die_komponente_im_designer(
    tmp_path: Path, hauptfenster_bauen
) -> None:
    pfad = _pfm_schreiben(tmp_path, button_left=380)
    fenster = hauptfenster_bauen()
    formular = fenster.designer_oeffnen(pfad)
    fenster._design_pruefen_aktion()

    fenster.meldungen_liste.itemClicked.emit(fenster.meldungen_liste.item(0))

    canvas = fenster._offene_canvases[0]
    assert canvas.ausgewaehlte_komponente is formular.b_a


def test_design_pruefung_laeuft_automatisch_nach_einer_aenderung(
    tmp_path: Path, hauptfenster_bauen
) -> None:
    pfad = _pfm_schreiben(tmp_path, button_left=8)
    fenster = hauptfenster_bauen()
    formular = fenster.designer_oeffnen(pfad)
    canvas = fenster._offene_canvases[0]

    canvas.verschieben(1000, 0, formular.b_a)
    canvas.jetzt_schreiben()

    assert fenster.meldungen_liste.count() >= 1


def test_design_pruefung_automatisch_laesst_sich_abschalten(
    tmp_path: Path, hauptfenster_bauen
) -> None:
    pfad = _pfm_schreiben(tmp_path, button_left=8)
    fenster = hauptfenster_bauen()
    formular = fenster.designer_oeffnen(pfad)
    canvas = fenster._offene_canvases[0]
    fenster._design_pruefung_automatisch_aktion.qaction.setChecked(False)

    canvas.verschieben(1000, 0, formular.b_a)
    canvas.jetzt_schreiben()

    assert fenster.meldungen_liste.count() == 0


def test_frisch_platzierte_komponenten_ohne_namenshinweis(
    tmp_path: Path, hauptfenster_bauen
) -> None:
    """Punkte 292 und 301: nach dem Platzieren steht kein Hinweis auf
    die Namen, die der Designer selbst vergeben hat."""
    from pcl import Button, Edit, Label

    pfad = _pfm_schreiben(tmp_path, button_left=8)
    fenster = hauptfenster_bauen()
    fenster.designer_oeffnen(pfad)
    canvas = fenster._offene_canvases[0]
    fenster._design_pruefung_automatisch_aktion.qaction.setChecked(True)

    canvas.komponente_platzieren(Button, 8, 64)
    canvas.komponente_platzieren(Edit, 8, 120)
    canvas.komponente_platzieren(Label, 8, 176)
    canvas.jetzt_schreiben()

    texte = [
        fenster.meldungen_liste.item(i).text()
        for i in range(fenster.meldungen_liste.count())
    ]
    assert not [t for t in texte if "Namenskonvention" in t]


def test_design_pruefung_laesst_funde_vor_dem_start_stehen(
    tmp_path: Path, hauptfenster_bauen
) -> None:
    """Punkt 292: eine Änderung im Designer leerte das Panel
    „Meldungen“ samt den Funden der Prüfung vor dem Start."""
    from PySide6.QtWidgets import QListWidgetItem

    from ide.shell.hauptfenster import _FUND_ROLLE

    pfad = _pfm_schreiben(tmp_path, button_left=380)
    fenster = hauptfenster_bauen()
    formular = fenster.designer_oeffnen(pfad)
    canvas = fenster._offene_canvases[0]
    fenster._design_pruefung_automatisch_aktion.qaction.setChecked(True)
    fund = QListWidgetItem("u_main.py:3:1: F401 `os` wird nicht benutzt")
    fund.setData(_FUND_ROLLE, (str(tmp_path / "u_main.py"), 3, 1))
    fenster.meldungen_liste.addItem(fund)

    canvas.verschieben(8, 0, formular.b_a)
    canvas.jetzt_schreiben()
    canvas.verschieben(-8, 0, formular.b_a)
    canvas.jetzt_schreiben()

    texte = [
        fenster.meldungen_liste.item(i).text()
        for i in range(fenster.meldungen_liste.count())
    ]
    assert "u_main.py:3:1: F401 `os` wird nicht benutzt" in texte
    assert sum("außerhalb" in t for t in texte) == 1
