"""Ausgabe-Panel (Punkt 98) und Einstellungen/Schriftgröße (Punkt 101)."""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtWidgets import QApplication

from ide.shell.hauptfenster import HauptFenster


def _fenster(bauen, tmp_path: Path) -> HauptFenster:
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "main.py").write_text("a = 1\n", encoding="utf-8")
    (tmp_path / "u_zwei.py").write_text("b = 2\n", encoding="utf-8")
    natter = tmp_path / "t.natter"
    natter.write_text(json.dumps({
        "format": "natter-project/1", "name": "T", "type": "console", "main": "main.py",
    }), encoding="utf-8")
    fenster = bauen()
    fenster.projekt_oeffnen(natter)
    return fenster


def test_ausgabe_kopieren_ohne_uhrzeit_und_leeren(
    hauptfenster_bauen, tmp_path: Path
) -> None:
    fenster = _fenster(hauptfenster_bauen, tmp_path)
    fenster.ausgabe_liste.clear()
    fenster.ausgabe_zeile("Hallo")
    fenster.ausgabe_zeile("Welt")

    aktionen = {a.text(): a for a in fenster.ausgabe_kontextmenue().actions() if a.text()}
    assert not aktionen["Markierte Zeilen kopieren"].isEnabled()
    aktionen["Alles kopieren"].trigger()
    assert QApplication.clipboard().text() == "Hallo\nWelt"

    fenster.ausgabe_liste.item(1).setSelected(True)
    assert fenster._ausgabe_kopieren(nur_markierte=True) == "Welt"

    aktionen["Leeren"].trigger()
    assert fenster.ausgabe_liste.count() == 0


def test_ausgabe_wird_vor_dem_start_geleert(
    hauptfenster_bauen, tmp_path: Path
) -> None:
    fenster = _fenster(hauptfenster_bauen, tmp_path)
    fenster.ausgabe_zeile("vom letzten Lauf")

    fenster._projekt_starten_aktion()
    try:
        texte = [fenster.ausgabe_liste.item(i).text() for i in range(fenster.ausgabe_liste.count())]
        assert not any("vom letzten Lauf" in t for t in texte)
    finally:
        fenster._debugger_stoppen_aktion()


def test_ausgabe_bleibt_wenn_abgeschaltet(
    hauptfenster_bauen, tmp_path: Path
) -> None:
    fenster = _fenster(hauptfenster_bauen, tmp_path)
    fenster.einstellungen_uebernehmen(fenster.editor_schriftgroesse(), False)
    fenster.ausgabe_zeile("vom letzten Lauf")

    fenster._projekt_starten_aktion()
    try:
        texte = [fenster.ausgabe_liste.item(i).text() for i in range(fenster.ausgabe_liste.count())]
        assert any("vom letzten Lauf" in t for t in texte)
    finally:
        fenster._debugger_stoppen_aktion()


def test_umlaute_aus_print_kommen_im_panel_an(qtbot, tmp_path: Path) -> None:  # noqa: ANN001
    # Punkt 186: das Programm schrieb in der Kodierung des Systems ins
    # Rohr, Natter las UTF-8, und aus „Größe“ wurde „Gr��e“.
    (tmp_path / "main.py").write_text(
        "print('Größe: 3 €')\n", encoding="utf-8"
    )
    natter = tmp_path / "t.natter"
    natter.write_text(json.dumps({
        "format": "natter-project/1", "name": "T", "type": "gui", "main": "main.py",
    }), encoding="utf-8")
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    fenster.projekt_oeffnen(natter)

    fenster._projekt_starten_aktion()
    try:
        def texte() -> list[str]:
            liste = fenster.ausgabe_liste
            return [liste.item(i).text() for i in range(liste.count())]

        qtbot.waitUntil(
            lambda: any("3 €" in t or "3 �" in t for t in texte()),
            timeout=20_000,
        )
        assert any("Größe: 3 €" in t for t in texte()), texte()
    finally:
        fenster._debugger_stoppen_aktion()


def test_schriftgroesse_fuer_alle_editoren_und_gemerkt(
    hauptfenster_bauen, tmp_path: Path
) -> None:
    fenster = _fenster(hauptfenster_bauen, tmp_path)
    eins = fenster.datei_oeffnen(tmp_path / "main.py")
    zwei = fenster.datei_oeffnen(tmp_path / "u_zwei.py")

    fenster.aktionen["ansicht.schrift_groesser"].qaction.trigger()
    fenster.aktionen["ansicht.schrift_groesser"].qaction.trigger()

    assert eins.font().pointSize() == zwei.font().pointSize() == 13
    neu = _fenster(hauptfenster_bauen, tmp_path / "zweites")
    assert neu.editor_schriftgroesse() == 13
    neu.aktionen["ansicht.schrift_normal"].qaction.trigger()
    assert neu.editor_schriftgroesse() == 11


def test_mausrad_merkt_sich_die_groesse(hauptfenster_bauen, tmp_path: Path) -> None:  # noqa: ANN001
    fenster = _fenster(hauptfenster_bauen, tmp_path)
    eins = fenster.datei_oeffnen(tmp_path / "main.py")
    zwei = fenster.datei_oeffnen(tmp_path / "u_zwei.py")

    eins.schriftgroesse_aendern(3)

    assert zwei.font().pointSize() == 14
    assert fenster.editor_schriftgroesse() == 14


def _punkte(widget) -> float:  # noqa: ANN001
    widget.ensurePolished()
    return widget.font().pointSizeF()


def test_strg_plus_vergroessert_ausgabe_und_meldungen(
    hauptfenster_bauen, tmp_path: Path, qtbot
) -> None:
    """Punkt 302: am Beamer wächst die Ausgabe des Programms mit dem
    Quelltext mit."""
    fenster = _fenster(hauptfenster_bauen, tmp_path)
    fenster.show()
    qtbot.waitExposed(fenster)
    fenster.ausgabe_zeile("Hallo")
    vorher = _punkte(fenster.ausgabe_liste)
    meldungen_vorher = _punkte(fenster.meldungen_liste)

    for _ in range(3):
        fenster.aktionen["ansicht.schrift_groesser"].qaction.trigger()

    assert _punkte(fenster.ausgabe_liste) == vorher + 3
    assert _punkte(fenster.meldungen_liste) == meldungen_vorher + 3

    fenster.aktionen["ansicht.schrift_normal"].qaction.trigger()
    assert _punkte(fenster.ausgabe_liste) == vorher


def test_schriftgroesse_der_oberflaeche(
    hauptfenster_bauen, tmp_path: Path, qtbot
) -> None:
    """Punkt 302: eine Einstellung vergrößert die ganze Oberfläche und
    gilt auch nach einem Neustart."""
    fenster = _fenster(hauptfenster_bauen, tmp_path)
    fenster.show()
    qtbot.waitExposed(fenster)

    fenster.einstellungen_uebernehmen(
        fenster.editor_schriftgroesse(), True, oberflaeche=16
    )

    assert _punkte(fenster.explorer) == 16
    assert _punkte(fenster.objektinspektor) == 16
    assert _punkte(fenster.ausgabe_liste) == 16

    neu = hauptfenster_bauen()
    assert neu.oberflaeche_schriftgroesse() == 16
    neu.show()
    qtbot.waitExposed(neu)
    assert _punkte(neu.explorer) == 16


def test_einstellungen_dialog_zeigt_oberflaeche(hauptfenster_bauen) -> None:
    from ide.shell.einstellungen_dialog import EinstellungenDialog

    dialog = EinstellungenDialog(11, True, oberflaeche=14)
    try:
        assert dialog.oberflaeche() == 14
    finally:
        dialog.deleteLater()
