"""Tests für HauptFenster.designer_oeffnen(): Doppelklick auf ein
Formular im Explorer öffnet den Designer statt Rohtext. Headless. Siehe
docs/arbeitspakete/M3.md, Schritt 3.
"""

from pathlib import Path

from ide.shell.hauptfenster import HauptFenster

_AMPEL_ORDNER = Path(__file__).resolve().parent.parent / "beispielprojekte" / "Ampel"
_AMPEL_PFM = _AMPEL_ORDNER / "u_main.pfm"


def test_designer_oeffnen_zeigt_formular_und_fuellt_inspektor() -> None:
    fenster = HauptFenster()

    formular = fenster.designer_oeffnen(_AMPEL_PFM)

    assert fenster.editor_tabs.count() == 1
    assert fenster.editor_tabs.tabText(0) == "u_main (Designer)"
    assert formular.caption == "Ampel"
    assert fenster.objektinspektor.formular is formular


def test_designer_oeffnen_zweimal_aktiviert_nur_den_vorhandenen_tab() -> None:
    fenster = HauptFenster()

    fenster.designer_oeffnen(_AMPEL_PFM)
    fenster.designer_oeffnen(_AMPEL_PFM)

    assert fenster.editor_tabs.count() == 1


def test_explorer_doppelklick_auf_pfm_oeffnet_den_designer() -> None:
    fenster = HauptFenster()
    fenster.projekt_oeffnen(_AMPEL_ORDNER)

    formular_eintrag = fenster.explorer.formulare_gruppe.child(0)
    fenster.explorer.itemDoubleClicked.emit(formular_eintrag, 0)

    assert fenster.editor_tabs.count() == 1
    assert fenster.editor_tabs.tabText(0) == "u_main (Designer)"


def test_klick_im_designer_aktualisiert_den_objektinspektor() -> None:
    fenster = HauptFenster()
    formular = fenster.designer_oeffnen(_AMPEL_PFM)
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
