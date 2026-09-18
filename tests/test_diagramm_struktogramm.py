"""Tests für den Struktogramm-Editor: Zeichenfläche, Einfügestellen,
Palette und Fenster-Anbindung (M9, Schritt 9). Headless.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QImage, QKeyEvent, QMouseEvent, QPainter

from ide.diagramm import DiagrammFenster, diagramm_erzeugen
from ide.diagramm.bloecke import Einfuegestelle, alle_bloecke
from ide.diagramm.stil import stil
from ide.diagramm.struktogramm import BLOCK_BESCHRIFTUNGEN, struktogramm_zeichnen
from ide.diagramm.struktogramm_canvas import VERSATZ, StruktogrammCanvas
from ide.diagramm.struktogramm_palette import KIND_ROLLE, BlockPalette


@pytest.fixture
def flaeche(tmp_path: Path) -> StruktogrammCanvas:
    diagramm = diagramm_erzeugen("struktogramm", tmp_path / "s.pdiag", "ampel_zeichnen")
    return StruktogrammCanvas(diagramm)


def _wurzelstelle(flaeche: StruktogrammCanvas, index: int = 0) -> Einfuegestelle:
    return Einfuegestelle(flaeche.wurzel, "children", index)


def _klick(x: float, y: float, typ=QEvent.Type.MouseButtonPress) -> QMouseEvent:
    return QMouseEvent(
        typ,
        QPointF(x, y),
        QPointF(x, y),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )


# -- Einfügen ------------------------------------------------------------


def test_leeres_struktogramm_hat_eine_einfuegestelle(flaeche: StruktogrammCanvas) -> None:
    """Sonst käme man nie zum ersten Block."""
    stellen = flaeche.einfuegestellen()

    assert len(stellen) == 1
    assert stellen[0][0].eltern is flaeche.wurzel


def test_block_einfuegen_haengt_ihn_in_den_baum(flaeche: StruktogrammCanvas) -> None:
    block = flaeche.block_einfuegen("statement", _wurzelstelle(flaeche))

    assert flaeche.wurzel["children"] == [block]
    assert flaeche.ausgewaehlter_block is block


def test_nach_zwei_bloecken_gibt_es_drei_stellen(flaeche: StruktogrammCanvas) -> None:
    """Oberhalb, dazwischen und unterhalb."""
    flaeche.block_einfuegen("statement", _wurzelstelle(flaeche))
    flaeche.block_einfuegen("statement", _wurzelstelle(flaeche, 1))

    stellen = [s for s, _ in flaeche.einfuegestellen() if s.eltern is flaeche.wurzel]

    assert sorted(s.index for s in stellen) == [0, 1, 2]


def test_verzweigung_bietet_beide_zweige_als_einfugestelle(
    flaeche: StruktogrammCanvas,
) -> None:
    verzweigung = flaeche.block_einfuegen("branch", _wurzelstelle(flaeche))

    schluessel = {
        stelle.schluessel
        for stelle, _ in flaeche.einfuegestellen()
        if stelle.eltern is verzweigung
    }

    assert schluessel == {"then", "else"}


def test_schleife_bietet_ihren_koerper_an(flaeche: StruktogrammCanvas) -> None:
    schleife = flaeche.block_einfuegen("head_loop", _wurzelstelle(flaeche))

    stellen = [s for s, _ in flaeche.einfuegestellen() if s.eltern is schleife]

    assert len(stellen) == 1


def test_einfuegestelle_der_schleife_liegt_unter_ihrem_kopf(
    flaeche: StruktogrammCanvas,
) -> None:
    """Sonst landete der Block im Schleifenkopf statt im Körper."""
    schleife = flaeche.block_einfuegen("head_loop", _wurzelstelle(flaeche))
    kasten = next(k for k in flaeche._layout.alle() if k.block is schleife)

    _, bereich = next(
        (s, b) for s, b in flaeche.einfuegestellen() if s.eltern is schleife
    )

    assert bereich.top() >= kasten.kopf.bottom() - 0.01


def test_mehrfachauswahl_bietet_jede_spalte_an(flaeche: StruktogrammCanvas) -> None:
    auswahl = flaeche.block_einfuegen("multi_branch", _wurzelstelle(flaeche))

    faelle = {
        stelle.fall for stelle, _ in flaeche.einfuegestellen() if stelle.eltern is auswahl
    }

    assert faelle == {0, 1}


def test_klick_im_einfuegemodus_setzt_den_block(flaeche: StruktogrammCanvas) -> None:
    flaeche.einfuegemodus_setzen("statement")

    flaeche.mousePressEvent(_klick(VERSATZ + 40, VERSATZ + 10))

    assert len(flaeche.wurzel["children"]) == 1
    # danach zurück zum Auswahlwerkzeug, wie bei der Formen-Palette
    assert flaeche._einfuegeart is None


def test_escape_bricht_das_einfuegen_ab(flaeche: StruktogrammCanvas) -> None:
    flaeche.einfuegemodus_setzen("branch")

    flaeche.keyPressEvent(
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
    )

    assert flaeche._einfuegeart is None
    assert flaeche.wurzel["children"] == []


# -- Auswahl und Bearbeiten ----------------------------------------------


def test_klick_waehlt_den_innersten_block(flaeche: StruktogrammCanvas) -> None:
    """Ohne das träfe man immer nur die umgebende Schleife."""
    schleife = flaeche.block_einfuegen("head_loop", _wurzelstelle(flaeche))
    innen = flaeche.block_einfuegen("statement", Einfuegestelle(schleife, "children", 0))
    kasten = next(k for k in flaeche._layout.alle() if k.block is innen)

    getroffen = flaeche.block_bei(
        VERSATZ + kasten.rechteck.center().x(), VERSATZ + kasten.rechteck.center().y()
    )

    assert getroffen is innen


def test_klick_ins_leere_hebt_die_auswahl_auf(flaeche: StruktogrammCanvas) -> None:
    flaeche.block_einfuegen("statement", _wurzelstelle(flaeche))

    flaeche.mousePressEvent(_klick(2000, 2000))

    assert flaeche.ausgewaehlter_block is None


def test_text_setzen_ist_ein_undo_schritt(flaeche: StruktogrammCanvas) -> None:
    block = flaeche.block_einfuegen("statement", _wurzelstelle(flaeche))
    vorher = block["text"]

    flaeche.text_setzen(block, "zustand := zustand + 1")
    assert block["text"] == "zustand := zustand + 1"

    flaeche.rueckgaengig()
    assert block["text"] == vorher


def test_loeschen_nimmt_den_block_aus_dem_baum(flaeche: StruktogrammCanvas) -> None:
    block = flaeche.block_einfuegen("statement", _wurzelstelle(flaeche))

    flaeche.loeschen(block)

    assert flaeche.wurzel["children"] == []
    assert flaeche.ausgewaehlter_block is None


def test_geloeschter_block_kommt_an_seine_alte_stelle_zurueck(
    flaeche: StruktogrammCanvas,
) -> None:
    flaeche.block_einfuegen("statement", _wurzelstelle(flaeche))
    mitte = flaeche.block_einfuegen("call", _wurzelstelle(flaeche, 1))
    flaeche.block_einfuegen("jump", _wurzelstelle(flaeche, 2))

    flaeche.loeschen(mitte)
    flaeche.rueckgaengig()

    assert flaeche.wurzel["children"][1] is mitte


def test_die_wurzel_laesst_sich_nicht_loeschen(flaeche: StruktogrammCanvas) -> None:
    """Ohne Wurzel gäbe es kein Struktogramm mehr."""
    flaeche.loeschen(flaeche.wurzel)

    assert flaeche.diagramm.daten["root"] is flaeche.wurzel


def test_loeschen_nimmt_den_inhalt_mit_und_bringt_ihn_zurueck(
    flaeche: StruktogrammCanvas,
) -> None:
    schleife = flaeche.block_einfuegen("head_loop", _wurzelstelle(flaeche))
    innen = flaeche.block_einfuegen("statement", Einfuegestelle(schleife, "children", 0))

    flaeche.loeschen(schleife)
    assert len(alle_bloecke(flaeche.diagramm.daten)) == 1

    flaeche.rueckgaengig()
    assert flaeche.wurzel["children"][0]["children"][0] is innen


def test_enter_legt_eine_anweisung_darunter_an(flaeche: StruktogrammCanvas) -> None:
    """Wie im Quelltexteditor (Abschnitt 13.5)."""
    erster = flaeche.block_einfuegen("statement", _wurzelstelle(flaeche))
    flaeche.auswaehlen(erster)

    flaeche.keyPressEvent(
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier)
    )

    assert len(flaeche.wurzel["children"]) == 2
    assert flaeche.wurzel["children"][0] is erster


def test_entf_loescht_den_ausgewaehlten_block(flaeche: StruktogrammCanvas) -> None:
    flaeche.block_einfuegen("statement", _wurzelstelle(flaeche))

    flaeche.keyPressEvent(
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Delete, Qt.KeyboardModifier.NoModifier)
    )

    assert flaeche.wurzel["children"] == []


# -- Fälle der Mehrfachauswahl -------------------------------------------


def test_fall_hinzufuegen_und_rueckgaengig(flaeche: StruktogrammCanvas) -> None:
    auswahl = flaeche.block_einfuegen("multi_branch", _wurzelstelle(flaeche))

    flaeche.fall_hinzufuegen(auswahl)
    assert len(auswahl["cases"]) == 3

    flaeche.rueckgaengig()
    assert len(auswahl["cases"]) == 2


def test_fall_entfernen_und_rueckgaengig(flaeche: StruktogrammCanvas) -> None:
    auswahl = flaeche.block_einfuegen("multi_branch", _wurzelstelle(flaeche))

    flaeche.fall_entfernen(auswahl)
    assert len(auswahl["cases"]) == 1

    flaeche.rueckgaengig()
    assert len(auswahl["cases"]) == 2


def test_fall_nur_bei_der_mehrfachauswahl(flaeche: StruktogrammCanvas) -> None:
    block = flaeche.block_einfuegen("statement", _wurzelstelle(flaeche))

    flaeche.fall_hinzufuegen(block)

    assert "cases" not in block


# -- Palette -------------------------------------------------------------


def test_palette_zeigt_jede_blockart() -> None:
    palette = BlockPalette()

    arten = []
    for i in range(palette.baum.topLevelItemCount()):
        gruppe = palette.baum.topLevelItem(i)
        arten.extend(gruppe.child(j).data(0, KIND_ROLLE) for j in range(gruppe.childCount()))

    # Die Wurzel (`sequence`) steht bewusst nicht in den Beschriftungen:
    # sie entsteht mit dem Struktogramm und wird nie eingefügt.
    assert set(arten) == set(BLOCK_BESCHRIFTUNGEN)


def test_palette_meldet_die_gewaehlte_art() -> None:
    palette = BlockPalette()
    gemeldet: list[str] = []
    palette.block_gewaehlt.connect(gemeldet.append)

    gruppe = palette.baum.topLevelItem(0)
    palette._geklickt(gruppe.child(0), 0)

    assert gemeldet == ["statement"]


def test_palette_filtert_nach_text() -> None:
    palette = BlockPalette()

    palette.suche.setText("schleife")

    sichtbar = []
    for i in range(palette.baum.topLevelItemCount()):
        gruppe = palette.baum.topLevelItem(i)
        if gruppe.isHidden():
            continue
        sichtbar.extend(
            gruppe.child(j).text(0)
            for j in range(gruppe.childCount())
            if not gruppe.child(j).isHidden()
        )

    assert sichtbar and all("chleife" in name for name in sichtbar)


# -- Fenster -------------------------------------------------------------


@pytest.fixture
def fenster(tmp_path: Path) -> DiagrammFenster:
    return DiagrammFenster(
        diagramm_erzeugen("struktogramm", tmp_path / "s.pdiag", "ampel_zeichnen")
    )


def test_struktogramm_fenster_bekommt_die_blockpalette(fenster: DiagrammFenster) -> None:
    assert isinstance(fenster.zeichenflaeche, StruktogrammCanvas)
    assert isinstance(fenster.palette, BlockPalette)
    # Im Screenshot aufgefallen: das Dock hieß noch „Formen“, obwohl ein
    # Struktogramm gar keine Formen kennt.
    assert fenster.palette_dock.windowTitle() == "Blöcke"
    assert fenster.eigenschaften_dock is None


def test_formen_eintraege_sind_beim_struktogramm_ausgegraut(
    fenster: DiagrammFenster,
) -> None:
    """Ehrlicher Zwischenstand: ein Struktogramm kennt keine Formen, also
    auch kein Duplizieren und kein Übertragen von Füllfarben."""
    assert fenster.aktionen["Bearbeiten/Duplizieren"].isEnabled() is False
    assert fenster.aktionen["Format/Stil übertragen"].isEnabled() is False
    assert fenster.aktionen["Ansicht/Layout-Hinweise"].isEnabled() is False


def test_statusleiste_zaehlt_bloecke_statt_formen(fenster: DiagrammFenster) -> None:
    fenster.zeichenflaeche.block_einfuegen(
        "statement", Einfuegestelle(fenster.zeichenflaeche.wurzel, "children", 0)
    )
    fenster.zeichenflaeche.auswaehlen(None)
    fenster._statusleiste_aktualisieren()

    assert "1 Blöcke" in fenster.statusBar().currentMessage()


def test_menue_rueckgaengig_wirkt_auf_die_blockflaeche(fenster: DiagrammFenster) -> None:
    flaeche = fenster.zeichenflaeche
    flaeche.block_einfuegen("statement", Einfuegestelle(flaeche.wurzel, "children", 0))

    fenster.aktionen["Bearbeiten/Rückgängig"].trigger()

    assert flaeche.wurzel["children"] == []


def test_struktogramm_wird_gespeichert_und_wieder_geladen(
    fenster: DiagrammFenster,
) -> None:
    from ide.diagramm.datei import Diagramm

    flaeche = fenster.zeichenflaeche
    block = flaeche.block_einfuegen("head_loop", Einfuegestelle(flaeche.wurzel, "children", 0))
    flaeche.text_setzen(block, "solange nicht fertig")
    fenster.speichern()

    geladen = Diagramm.laden(fenster.diagramm.pfad)

    assert geladen.daten["root"]["children"][0]["text"] == "solange nicht fertig"


def test_struktogramm_laesst_sich_als_pdf_exportieren(
    fenster: DiagrammFenster, tmp_path: Path
) -> None:
    flaeche = fenster.zeichenflaeche
    flaeche.block_einfuegen("statement", Einfuegestelle(flaeche.wurzel, "children", 0))

    pfad = fenster.exportieren(tmp_path / "ampel.pdf")

    assert pfad.read_bytes().startswith(b"%PDF")
    assert pfad.stat().st_size > 1000


def test_struktogramm_bekommt_im_pdf_einen_druckrand(fenster: DiagrammFenster) -> None:
    """Im PDF-Sichtnachweis aufgefallen: das Struktogramm beginnt bei
    (0, 0) und klebte deshalb am Blattrand."""
    from ide.diagramm.export import _seitenversatz
    from ide.diagramm.seite import satzspiegel

    links, oben = _seitenversatz(fenster.diagramm.daten)
    erwartet_links, erwartet_oben, _, _ = satzspiegel(fenster.diagramm.daten["page"])

    assert (links, oben) == (erwartet_links, erwartet_oben)
    assert links > 0 and oben > 0


# -- Endlosschleife, Parallelabschnitt, Try-Block (Schritt 14) -----------


def test_endlosschleife_bietet_ihren_koerper_an(flaeche: StruktogrammCanvas) -> None:
    schleife = flaeche.block_einfuegen("forever_loop", _wurzelstelle(flaeche))
    kasten = next(k for k in flaeche._layout.alle() if k.block is schleife)

    stellen = [(s, b) for s, b in flaeche.einfuegestellen() if s.eltern is schleife]

    assert len(stellen) == 1
    assert stellen[0][1].top() >= kasten.kopf.bottom() - 0.01


def test_parallelabschnitt_bietet_jeden_strang_an(flaeche: StruktogrammCanvas) -> None:
    abschnitt = flaeche.block_einfuegen("parallel", _wurzelstelle(flaeche))

    stellen = [s for s, _ in flaeche.einfuegestellen() if s.eltern is abschnitt]

    assert {s.fall for s in stellen} == {0, 1}
    assert {s.schluessel for s in stellen} == {"branches"}


def test_try_block_bietet_alle_drei_abschnitte_an(flaeche: StruktogrammCanvas) -> None:
    versuch = flaeche.block_einfuegen("try", _wurzelstelle(flaeche))

    schluessel = {
        stelle.schluessel for stelle, _ in flaeche.einfuegestellen() if stelle.eltern is versuch
    }

    assert schluessel == {"children", "catch", "finally"}


def test_block_im_strang_landet_im_richtigen_strang(flaeche: StruktogrammCanvas) -> None:
    abschnitt = flaeche.block_einfuegen("parallel", _wurzelstelle(flaeche))

    innen = flaeche.block_einfuegen(
        "statement", Einfuegestelle(abschnitt, "branches", 0, fall=1)
    )

    assert abschnitt["branches"] == [[], [innen]]


def test_neue_bloecke_bleiben_im_rahmen(flaeche: StruktogrammCanvas) -> None:
    """Das Layout darf auch mit den drei neuen Arten nirgends
    aufbrechen (Abschnitt 13.5)."""
    verzweigung = flaeche.block_einfuegen("branch", _wurzelstelle(flaeche))
    abschnitt = flaeche.block_einfuegen("parallel", Einfuegestelle(verzweigung, "then", 0))
    flaeche.block_einfuegen("statement", Einfuegestelle(abschnitt, "branches", 0, fall=0))
    versuch = flaeche.block_einfuegen("try", Einfuegestelle(verzweigung, "else", 0))
    flaeche.block_einfuegen("forever_loop", Einfuegestelle(versuch, "catch", 0))

    wurzel = flaeche._layout_erneuern()
    aussen = wurzel.kinder[0]

    for kasten in wurzel.alle():
        assert kasten.rechteck.left() >= aussen.rechteck.left() - 0.01
        assert kasten.rechteck.right() <= aussen.rechteck.right() + 0.01
        assert kasten.rechteck.bottom() <= aussen.rechteck.bottom() + 0.01


def test_rueckgaengig_und_wiederholen_im_strang(flaeche: StruktogrammCanvas) -> None:
    abschnitt = flaeche.block_einfuegen("parallel", _wurzelstelle(flaeche))
    innen = flaeche.block_einfuegen(
        "statement", Einfuegestelle(abschnitt, "branches", 0, fall=1)
    )

    flaeche.rueckgaengig()
    assert abschnitt["branches"] == [[], []]

    flaeche.wiederholen()
    assert abschnitt["branches"][1] == [innen]


def test_geloeschter_block_kehrt_in_seinen_abschnitt_zurueck(
    flaeche: StruktogrammCanvas,
) -> None:
    versuch = flaeche.block_einfuegen("try", _wurzelstelle(flaeche))
    innen = flaeche.block_einfuegen("statement", Einfuegestelle(versuch, "finally", 0))

    flaeche.loeschen(innen)
    assert versuch["finally"] == []

    flaeche.rueckgaengig()
    assert versuch["finally"] == [innen]


def test_enter_haengt_auch_in_einem_strang_an(flaeche: StruktogrammCanvas) -> None:
    """Enter braucht den Schlüssel der Liste – bei einem Strang ist das
    `branches` samt Nummer."""
    abschnitt = flaeche.block_einfuegen("parallel", _wurzelstelle(flaeche))
    erster = flaeche.block_einfuegen(
        "statement", Einfuegestelle(abschnitt, "branches", 0, fall=1)
    )
    flaeche.auswaehlen(erster)

    flaeche.keyPressEvent(
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier)
    )

    assert len(abschnitt["branches"][1]) == 2
    assert abschnitt["branches"][0] == []


def test_alle_blockarten_lassen_sich_zeichnen(flaeche: StruktogrammCanvas) -> None:
    """Gezeichnet wird sonst nur im Fenster – hier einmal auf ein Bild,
    damit jeder neue Blocktyp wirklich durch seine Malroutine läuft."""
    for art in sorted(set(BLOCK_BESCHRIFTUNGEN) - {"sequence"}):
        flaeche.block_einfuegen(art, _wurzelstelle(flaeche))

    bild = QImage(800, 2000, QImage.Format.Format_RGB32)
    bild.fill("#ffffff")
    maler = QPainter(bild)
    wurzel = struktogramm_zeichnen(maler, flaeche.diagramm.daten, stil("modern-light"))
    maler.end()

    assert len(wurzel.kinder) == len(BLOCK_BESCHRIFTUNGEN)
    # Irgendetwas muss auf dem weißen Blatt gelandet sein.
    farben = {
        QImage.pixelColor(bild, x, y).name()
        for x in range(0, 600, 5)
        for y in range(0, 900, 5)
    }
    assert len(farben) > 1
