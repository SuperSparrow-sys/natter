"""Tests für HauptFenster.designer_oeffnen(): Doppelklick auf ein
Formular im Explorer öffnet den Designer statt Rohtext. Headless. Siehe
Arbeitspaket M3, Schritt 3.

`designer_oeffnen()` verdrahtet den Designer bewusst so, dass jede
Änderung automatisch in die `.pfm` zurückgeschrieben wird (Abschnitt
4.2/4.4) - daher hier grundsätzlich eine Kopie in `tmp_path` statt der
echten `beispielprojekte/04_CookieKlicker/u_main.pfm` (AGENTS.md: Tests dürfen
Beispielprojekte nie direkt mutieren)."""

import shutil
from pathlib import Path

_AMPEL_VORLAGE = Path(__file__).resolve().parent.parent / "beispielprojekte" / "06_Kontoverwaltung"


def _ampel_kopie(tmp_path: Path) -> Path:
    ziel = tmp_path / "06_Kontoverwaltung"
    shutil.copytree(_AMPEL_VORLAGE, ziel)
    return ziel


def test_designer_oeffnen_zeigt_formular_und_fuellt_inspektor(tmp_path: Path, hauptfenster) -> None:
    ampel_pfm = _ampel_kopie(tmp_path) / "u_main.pfm"

    formular = hauptfenster.designer_oeffnen(ampel_pfm)

    assert hauptfenster.editor_tabs.count() == 1
    assert hauptfenster.editor_tabs.tabText(0) == "u_main (Designer)"
    assert formular.caption == "Kontoverwaltung"
    assert hauptfenster.objektinspektor.formular is formular


def test_designer_oeffnen_zweimal_aktiviert_nur_den_vorhandenen_tab(
    tmp_path: Path, hauptfenster
) -> None:
    ampel_pfm = _ampel_kopie(tmp_path) / "u_main.pfm"

    hauptfenster.designer_oeffnen(ampel_pfm)
    hauptfenster.designer_oeffnen(ampel_pfm)

    assert hauptfenster.editor_tabs.count() == 1


def test_explorer_doppelklick_auf_pfm_oeffnet_den_designer(tmp_path: Path, hauptfenster) -> None:
    hauptfenster.projekt_oeffnen(_ampel_kopie(tmp_path))

    formular_eintrag = hauptfenster.explorer.formulare_gruppe.child(0)
    hauptfenster.explorer.itemActivated.emit(formular_eintrag, 0)

    assert hauptfenster.editor_tabs.count() == 1
    assert hauptfenster.editor_tabs.tabText(0) == "u_main (Designer)"


def test_klick_im_designer_aktualisiert_den_objektinspektor(tmp_path: Path, hauptfenster) -> None:
    ampel_pfm = _ampel_kopie(tmp_path) / "u_main.pfm"
    formular = hauptfenster.designer_oeffnen(ampel_pfm)
    canvas = hauptfenster._offene_canvases[0]

    canvas.klick_bei(formular.b_anlegen.left + 5, formular.b_anlegen.top + 5)

    eigenschaften_namen = [
        hauptfenster.objektinspektor.eigenschaften_tabelle.item(z, 0).text()
        for z in range(hauptfenster.objektinspektor.eigenschaften_tabelle.rowCount())
    ]
    assert "caption" in eigenschaften_namen
    zeile = eigenschaften_namen.index("caption")
    assert (
        hauptfenster.objektinspektor.eigenschaften_tabelle.item(zeile, 1).text() == "Konto anlegen"
    )
