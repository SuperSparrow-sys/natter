"""Tests für HauptFenster.designer_oeffnen(): Doppelklick auf ein
Formular im Explorer öffnet den Designer statt Rohtext. Headless. Siehe
docs/arbeitspakete/M3.md, Schritt 3.

`designer_oeffnen()` verdrahtet den Designer bewusst so, dass jede
Änderung automatisch in die `.pfm` zurückgeschrieben wird (Abschnitt
4.2/4.4) - daher hier grundsätzlich eine Kopie in `tmp_path` statt der
echten `beispielprojekte/Ampel/u_main.pfm` (AGENTS.md: Tests dürfen
Beispielprojekte nie direkt mutieren)."""

import shutil
from pathlib import Path

from ide.shell.hauptfenster import HauptFenster

_AMPEL_VORLAGE = Path(__file__).resolve().parent.parent / "beispielprojekte" / "Ampel"


def _ampel_kopie(tmp_path: Path) -> Path:
    ziel = tmp_path / "Ampel"
    shutil.copytree(_AMPEL_VORLAGE, ziel)
    return ziel


def test_designer_oeffnen_zeigt_formular_und_fuellt_inspektor(tmp_path: Path) -> None:
    fenster = HauptFenster()
    ampel_pfm = _ampel_kopie(tmp_path) / "u_main.pfm"

    formular = fenster.designer_oeffnen(ampel_pfm)

    assert fenster.editor_tabs.count() == 1
    assert fenster.editor_tabs.tabText(0) == "u_main (Designer)"
    assert formular.caption == "Ampel"
    assert fenster.objektinspektor.formular is formular


def test_designer_oeffnen_zweimal_aktiviert_nur_den_vorhandenen_tab(tmp_path: Path) -> None:
    fenster = HauptFenster()
    ampel_pfm = _ampel_kopie(tmp_path) / "u_main.pfm"

    fenster.designer_oeffnen(ampel_pfm)
    fenster.designer_oeffnen(ampel_pfm)

    assert fenster.editor_tabs.count() == 1


def test_explorer_doppelklick_auf_pfm_oeffnet_den_designer(tmp_path: Path) -> None:
    fenster = HauptFenster()
    fenster.projekt_oeffnen(_ampel_kopie(tmp_path))

    formular_eintrag = fenster.explorer.formulare_gruppe.child(0)
    fenster.explorer.itemDoubleClicked.emit(formular_eintrag, 0)

    assert fenster.editor_tabs.count() == 1
    assert fenster.editor_tabs.tabText(0) == "u_main (Designer)"


def test_klick_im_designer_aktualisiert_den_objektinspektor(tmp_path: Path) -> None:
    fenster = HauptFenster()
    ampel_pfm = _ampel_kopie(tmp_path) / "u_main.pfm"
    formular = fenster.designer_oeffnen(ampel_pfm)
    canvas = fenster._offene_canvases[0]

    canvas.klick_bei(formular.b_einschalten.left + 5, formular.b_einschalten.top + 5)

    eigenschaften_namen = [
        fenster.objektinspektor.eigenschaften_tabelle.item(z, 0).text()
        for z in range(fenster.objektinspektor.eigenschaften_tabelle.rowCount())
    ]
    assert "caption" in eigenschaften_namen
    zeile = eigenschaften_namen.index("caption")
    assert (
        fenster.objektinspektor.eigenschaften_tabelle.item(zeile, 1).text() == "Einschalten"
    )
