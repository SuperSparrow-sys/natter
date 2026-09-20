"""Tests für das Rollen (Scrollen) im Formular-Designer.

Vom Nutzer gemeldet: „scrollen horizontal und vertikal funktioniert
nicht im editor“. Ein Designer-Tab enthielt bis dahin direkt das
Formular-Widget – ein Formular, das größer ist als der Tab-Bereich,
wurde also einfach abgeschnitten und war nicht erreichbar.

Ein eigenes, minimales `.pfm` in `tmp_path` (nicht aus
`beispielprojekte/`, weil `DesignerCanvas` bei jeder Änderung
automatisch zurückschreibt, siehe AGENTS.md).
"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtWidgets import QScrollArea

from ide.shell.hauptfenster import HauptFenster


def _pfm_schreiben(tmp_path: Path, breite: int = 1400, hoehe: int = 1000) -> Path:
    pfm = {
        "format": "pfm/1",
        "class": "Form1",
        "type": "Form",
        "properties": {"caption": "Form1", "width": breite, "height": hoehe},
        "children": [
            {
                "name": "b_a",
                "type": "Button",
                "properties": {"left": 8, "top": 8, "width": 75, "height": 25},
            }
        ],
    }
    pfad = tmp_path / "u_main.pfm"
    pfad.write_text(json.dumps(pfm), encoding="utf-8")
    return pfad


def test_designer_tab_steckt_in_einem_rollbereich(tmp_path: Path) -> None:
    fenster = HauptFenster()
    formular = fenster.designer_oeffnen(_pfm_schreiben(tmp_path))

    tab = fenster.editor_tabs.currentWidget()

    assert isinstance(tab, QScrollArea)
    assert tab.widget() is formular._qwidget


def test_formular_behaelt_seine_eingestellte_groesse(tmp_path: Path) -> None:
    """Die Größe eines Formulars ist eine Eigenschaft, die der Nutzer
    gesetzt hat – sie darf sich nicht danach richten, wie groß das
    IDE-Fenster gerade ist. Deshalb kein `widgetResizable`."""
    fenster = HauptFenster()
    formular = fenster.designer_oeffnen(_pfm_schreiben(tmp_path, 1400, 1000))
    fenster.resize(700, 500)
    fenster.show()

    assert fenster.editor_tabs.currentWidget().widgetResizable() is False
    assert formular._qwidget.width() == 1400
    assert formular._qwidget.height() == 1000


def test_grosses_formular_laesst_sich_in_beide_richtungen_rollen(tmp_path: Path) -> None:
    fenster = HauptFenster()
    fenster.designer_oeffnen(_pfm_schreiben(tmp_path, 1400, 1000))
    fenster.resize(800, 600)
    fenster.show()

    tab = fenster.editor_tabs.currentWidget()
    waagerecht, senkrecht = tab.horizontalScrollBar(), tab.verticalScrollBar()
    assert waagerecht.maximum() > 0
    assert senkrecht.maximum() > 0

    waagerecht.setValue(waagerecht.maximum())
    senkrecht.setValue(senkrecht.maximum())

    assert waagerecht.value() == waagerecht.maximum()
    assert senkrecht.value() == senkrecht.maximum()


def test_tabwechsel_findet_den_canvas_trotz_rollbereich(tmp_path: Path) -> None:
    """Der Rollbereich darf die Zuordnung Tab → Designer-Canvas nicht
    kaputt machen – sonst wüsste die IDE nach einem Tabwechsel nicht
    mehr, welches Formular gerade bearbeitet wird."""
    fenster = HauptFenster()
    fenster.designer_oeffnen(_pfm_schreiben(tmp_path))

    fenster._bei_tab_wechsel(fenster.editor_tabs.currentIndex())

    assert fenster._aktueller_canvas is not None


def test_zweites_oeffnen_holt_denselben_tab_nach_vorne(tmp_path: Path) -> None:
    """`indexOf` findet das Formular im Rollbereich nicht mehr – ohne die
    angepasste Suche würde jedes erneute Öffnen einen zweiten Tab
    anlegen."""
    pfad = _pfm_schreiben(tmp_path)
    fenster = HauptFenster()
    fenster.designer_oeffnen(pfad)

    fenster.designer_oeffnen(pfad)

    assert fenster.editor_tabs.count() == 1


def test_designer_tab_laesst_sich_schliessen(tmp_path: Path) -> None:
    fenster = HauptFenster()
    fenster.designer_oeffnen(_pfm_schreiben(tmp_path))

    fenster._tab_schliessen(0)

    assert fenster.editor_tabs.count() == 0
    assert fenster._offene_canvases == []
