"""Punkt 310: dieselbe Sache heißt in Meldungen, Menüs und im
Diagramm-Editor gleich, und Strg+0 bedeutet in beiden Fenstern
dasselbe."""

from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtGui import QKeySequence

from ide.diagramm import DiagrammFenster, diagramm_erzeugen

WURZEL = Path(__file__).resolve().parent.parent


def test_meldung_ohne_projekt_nennt_den_menueeintrag(hauptfenster) -> None:
    eintrag = hauptfenster.aktionen["projekt.oeffnen"].qaction.text()

    hauptfenster._als_zip_aktion()

    meldung = hauptfenster.statusBar().currentMessage()
    assert meldung.startswith("Kein Projekt offen.")
    assert f"„Projekt → {eintrag}“" in meldung
    assert eintrag == "Projekt öffnen …"


def test_kein_text_nennt_den_alten_menueweg() -> None:
    quelle = (WURZEL / "ide" / "shell" / "hauptfenster.py").read_text(
        encoding="utf-8"
    )

    assert '"Kein Projekt offen. Zuerst über „Projekt → Öffnen' not in quelle


def test_fenstermenue_sagt_reiter(hauptfenster) -> None:
    texte = [
        a.text() for a in hauptfenster.menue("Fenster").actions() if a.text()
    ]

    assert "Reiter schließen" in texte
    assert "Nächster Reiter" in texte
    assert "Vorheriger Reiter" in texte
    assert not [t for t in texte if re.search(r"\bTabs?\b", t)]


def test_statuszeile_zeigt_den_stil_wie_das_menue(tmp_path: Path) -> None:
    fenster = DiagrammFenster(
        diagramm_erzeugen("class", tmp_path / "k.pdiag", "k")
    )
    try:
        fenster._statusleiste_aktualisieren()
        meldung = fenster.statusBar().currentMessage()
        vorlagen = [
            a.text()
            for a in fenster.aktionen["Format/Stilvorlage …"].menu().actions()
        ]
        assert "Stil: Modern hell" in meldung
        assert "Modern hell" in vorlagen
    finally:
        fenster._geaendert = False
        fenster.close()


def test_strg_0_stellt_in_beiden_fenstern_die_normale_groesse_her(
    hauptfenster, tmp_path: Path
) -> None:
    strg_0 = QKeySequence("Ctrl+0")
    normal = hauptfenster.aktionen["ansicht.schrift_normal"].qaction
    assert normal.shortcut() == strg_0
    assert normal.text() == "Normale Schriftgröße"

    fenster = DiagrammFenster(
        diagramm_erzeugen("class", tmp_path / "k.pdiag", "k")
    )
    try:
        diagramm = [
            name
            for name, aktion in fenster.aktionen.items()
            if strg_0 in aktion.shortcuts()
        ]
        assert diagramm == ["Ansicht/Zoom 100 %"]
        fenster.zeichenflaeche.zoom_setzen(3.0)
        fenster.aktionen["Ansicht/Zoom 100 %"].trigger()
        assert fenster.zeichenflaeche.zoom == 1.0
    finally:
        fenster._geaendert = False
        fenster.close()
