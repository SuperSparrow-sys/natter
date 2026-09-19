"""Tests für die Symbole des Diagramm-Editors (M11, Abschnitt 1):
Palettensymbole, Werkzeugleiste, und die Symbole, die in der Haupt-IDE
nachgetragen wurden. Headless.

Die Formkennung (`shape["kind"]`) ist zugleich der halbe Dateiname des
Symbols (`form_<kind>.svg`). Das ist Absicht: eine neue Form braucht
dadurch **eine** Datei und keinen zweiten Namen, den man an anderer
Stelle nachtragen müsste – und der erste Test hier merkt sofort, wenn
sie fehlt.
"""

from __future__ import annotations

from pathlib import Path

from ide.assets import symbol
from ide.diagramm import Diagramm, DiagrammFenster, diagramm_erzeugen
from ide.diagramm.fenster import _WERKZEUGLEISTE
from ide.diagramm.formen import FORMEN_JE_TYP, VERBINDUNGEN_JE_TYP
from ide.diagramm.palette import KIND_ROLLE, FormenPalette
from ide.diagramm.struktogramm import BLOCK_BESCHRIFTUNGEN
from ide.diagramm.struktogramm_palette import BlockPalette


def _fenster(tmp_path: Path, typ: str = "class") -> DiagrammFenster:
    diagramm: Diagramm = diagramm_erzeugen(typ, tmp_path / f"{typ}.pdiag", "Testdiagramm")
    return DiagrammFenster(diagramm)


def _palettensymbole(baum) -> dict[str, object]:
    gefunden = {}
    for i in range(baum.topLevelItemCount()):
        gruppe = baum.topLevelItem(i)
        for j in range(gruppe.childCount()):
            eintrag = gruppe.child(j)
            gefunden[eintrag.data(0, KIND_ROLLE)] = eintrag
    return gefunden


# -- Vollständigkeit ----------------------------------------------------


def test_jede_form_hat_ein_symbol() -> None:
    for formen in FORMEN_JE_TYP.values():
        for art in formen:
            assert not symbol(f"form_{art.kind}").isNull(), f"form_{art.kind}.svg fehlt"


def test_jede_verbindungsart_hat_ein_symbol() -> None:
    for verbindungen in VERBINDUNGEN_JE_TYP.values():
        for art in verbindungen:
            assert not symbol(f"verbindung_{art.kind}").isNull(), f"verbindung_{art.kind}.svg fehlt"


def test_jeder_struktogramm_block_hat_ein_symbol() -> None:
    for art in BLOCK_BESCHRIFTUNGEN:
        # `sequence` ist der Wurzelblock, er steht in keiner Palette.
        if art == "sequence":
            continue
        assert not symbol(f"block_{art}").isNull(), f"block_{art}.svg fehlt"


# -- Paletten -----------------------------------------------------------


def test_formenpalette_zeigt_zu_jedem_eintrag_ein_symbol() -> None:
    palette = FormenPalette("class")

    eintraege = _palettensymbole(palette.baum)
    assert eintraege, "die Palette ist leer"
    for kind, eintrag in eintraege.items():
        assert not eintrag.icon(0).isNull(), kind


def test_blockpalette_zeigt_zu_jedem_eintrag_ein_symbol() -> None:
    palette = BlockPalette()

    eintraege = _palettensymbole(palette.baum)
    assert len(eintraege) == 11
    for art, eintrag in eintraege.items():
        assert not eintrag.icon(0).isNull(), art


def test_palettensymbole_folgen_einem_designwechsel() -> None:
    """Ein `QIcon` merkt sich seine Farben – ohne Neuladen blieben die
    Symbole nach „Ansicht → Design“ in der alten Farbe stehen (in M11
    an der Komponentenpalette real aufgefallen)."""
    for palette in (FormenPalette("class"), BlockPalette()):
        eintrag = next(iter(_palettensymbole(palette.baum).values()))
        palette.symbole_erneuern("light")
        hell = eintrag.icon(0).pixmap(32, 32).toImage()
        palette.symbole_erneuern("dark")
        dunkel = eintrag.icon(0).pixmap(32, 32).toImage()

        assert hell != dunkel


# -- Werkzeugleiste -----------------------------------------------------


def test_werkzeugleiste_traegt_die_befehle_des_zeichnens(tmp_path: Path) -> None:
    fenster = _fenster(tmp_path)

    beschriftungen = [
        aktion.text() for aktion in fenster.werkzeugleiste.actions() if not aktion.isSeparator()
    ]
    assert beschriftungen == [
        "Speichern",
        "Rückgängig",
        "Wiederholen",
        "Löschen",
        "Zoom vergrößern",
        "Zoom verkleinern",
        "Alles anzeigen",
        "Raster",
    ]


def test_jeder_knopf_der_werkzeugleiste_traegt_ein_symbol(tmp_path: Path) -> None:
    fenster = _fenster(tmp_path)

    for aktion in fenster.werkzeugleiste.actions():
        if not aktion.isSeparator():
            assert not aktion.icon().isNull(), aktion.text()


def test_werkzeugleiste_benutzt_dieselbe_aktion_wie_das_menue(tmp_path: Path) -> None:
    """Abschnitt 7.3: „eine Aktion = Menüeintrag + Werkzeugleisten-Button
    … nur einmal implementiert“. Eine zweite `QAction` mit demselben Text
    sähe gleich aus, hätte aber ihr eigenes Tastenkürzel und ihren
    eigenen Ein/Aus-Zustand – und das Raster-Häkchen liefe auseinander.
    """
    fenster = _fenster(tmp_path)

    knoepfe = [a for a in fenster.werkzeugleiste.actions() if not a.isSeparator()]
    pfade = [eintrag[0] for eintrag in _WERKZEUGLEISTE if eintrag is not None]
    assert len(knoepfe) == len(pfade)
    for knopf, pfad in zip(knoepfe, pfade, strict=True):
        assert knopf is fenster.aktionen[pfad]


def test_raster_knopf_teilt_das_haekchen_mit_dem_menue(tmp_path: Path) -> None:
    fenster = _fenster(tmp_path)
    knopf = fenster.aktionen["Ansicht/Raster"]

    assert knopf.isCheckable() is True
    vorher = knopf.isChecked()
    knopf.trigger()

    assert knopf.isChecked() is not vorher
    assert fenster.zeichenflaeche.raster_sichtbar is knopf.isChecked()


def test_werkzeugleiste_graut_aus_was_der_diagrammtyp_nicht_kann(tmp_path: Path) -> None:
    """Ein Struktogramm kennt kein Raster – der Knopf ist deshalb
    ausgegraut statt ein Verhalten vorzutäuschen, genau wie im Menü."""
    fenster = _fenster(tmp_path, "struktogramm")

    knoepfe = {
        aktion.text(): aktion
        for aktion in fenster.werkzeugleiste.actions()
        if not aktion.isSeparator()
    }
    assert knoepfe["Raster"].isEnabled() is False
    assert knoepfe["Speichern"].isEnabled() is True


def test_werkzeugleiste_ist_18_px_wie_in_der_haupt_ide(tmp_path: Path) -> None:
    fenster = _fenster(tmp_path)

    assert fenster.werkzeugleiste.iconSize().width() == 18


# -- Nachgetragene Symbole der Haupt-IDE --------------------------------


def test_nachgetragene_symbole_der_haupt_ide_stehen_in_der_werkzeugleiste() -> None:
    """M11, Abschnitt 1: Suchen, Kommentar umschalten, Einzelschritt,
    Testlauf und Export hatten kein Symbol und erschienen deshalb gar
    nicht in der Werkzeugleiste (nur Aktionen mit `symbol` landen dort,
    siehe `Aktionsregister.an_hauptfenster_anhaengen`)."""
    from ide.shell.hauptfenster import HauptFenster

    fenster = HauptFenster()
    in_der_leiste = {
        aktion.text() for aktion in fenster.werkzeugleiste.actions() if not aktion.isSeparator()
    }

    for aktions_id, erwartetes_symbol in (
        ("suchen.suchen", "suchen"),
        ("quelltext.kommentar_umschalten", "kommentar"),
        ("start.einzelschritt", "einzelschritt"),
        ("projekt.alle_tests_ausfuehren", "testlauf"),
        ("projekt.als_exe_exportieren", "export"),
    ):
        aktion = fenster.aktionen[aktions_id]
        assert aktion.symbol == erwartetes_symbol
        assert not aktion.qaction.icon().isNull(), aktions_id
        assert aktion.name in in_der_leiste
