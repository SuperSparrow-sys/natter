"""Hilfeseiten und Bedienung sagen dasselbe (Punkte 181 und 183)."""

from __future__ import annotations

import re
from pathlib import Path

from ide.shell.hauptfenster import HauptFenster
from ide.shell.startbild import beispielprojekte

WURZEL = Path(__file__).resolve().parent.parent
HANDBUCH = (WURZEL / "docs" / "handbuch.md").read_text(encoding="utf-8")
ERSTE_SCHRITTE = (WURZEL / "docs" / "erste_schritte.md").read_text(encoding="utf-8")


def _abschnitt(text: str, ueberschrift: str) -> str:
    """Der Text von `ueberschrift` bis zur nächsten Überschrift gleicher
    oder höherer Ebene."""
    ebene = len(ueberschrift) - len(ueberschrift.lstrip("#"))
    anfang = text.index(ueberschrift + "\n")
    rest = text[anfang + len(ueberschrift) :]
    ende = re.search(rf"^#{{1,{ebene}}} ", rest, re.M)
    return rest[: ende.start()] if ende else rest


def test_handbuch_beschreibt_die_palette_wie_sie_sich_bedienen_laesst() -> None:
    """Punkt 181: eine Kachel lässt sich nicht ziehen, nur anklicken
    und dann ins Formular klicken."""
    text = _abschnitt(HANDBUCH, "### 3.1 Oberflächen zeichnen statt tippen")

    assert "gezogen" not in text
    assert "angeklickt" in text and "ins Formular geklickt" in text


def test_erste_schritte_nennt_alle_beispielprojekte() -> None:
    text = _abschnitt(ERSTE_SCHRITTE, "## Und wenn es nicht weitergeht?")
    nummern = re.findall(r"^\| (\d\d) \|", text, re.M)

    assert nummern == [pfad.parent.name[:2] for pfad in beispielprojekte()]


def test_handbuch_zaehlt_die_eigenschaften_des_pruefungsmodus_richtig() -> None:
    text = _abschnitt(HANDBUCH, "## 4. Der Prüfungsmodus")
    punkte = re.findall(r"^\d\. \*\*", text, re.M)

    assert len(punkte) == 3
    assert "Drei Eigenschaften" in text


def test_handbuch_nennt_die_sperren_des_pruefungsmodus() -> None:
    text = _abschnitt(HANDBUCH, "## 4. Der Prüfungsmodus")

    assert "Zuletzt geöffnet" in text
    assert "Beispielprojekte" in text


def test_meldung_ohne_testergebnisse_nennt_den_richtigen_menueeintrag(qtbot) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    eintrag = fenster.aktionen["projekt.alle_tests_ausfuehren"].qaction.text()

    fenster._testergebnisse_exportieren_aktion()

    assert f"„Projekt → {eintrag}“" in fenster.statusBar().currentMessage()


def test_tastenkuerzel_im_handbuch_passen_zu_den_menues(qtbot) -> None:
    """Punkt 213: das Handbuch nannte Strg+O für „Projekt öffnen“, die
    Taste gehörte aber zu „Datei → Öffnen …“. Die Tabellen zu Menü-
    befehlen müssen mit der erzeugten Übersicht übereinstimmen: jede
    Zeile beginnt mit dem ersten Wort des Befehls, den die Taste
    wirklich auslöst."""
    from ide.shell.tastenkuerzel import uebersicht

    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    befehle = {
        taste: name.replace("…", "").strip()
        for gruppe in uebersicht(fenster.aktionen)
        for taste, name in gruppe.eintraege
    }
    abschnitt = _abschnitt(HANDBUCH, "## 5. Tastenkürzel")
    geprueft = 0
    for ueberschrift in (
        "### Datei und Bearbeiten", "### Suchen", "### Starten und Debuggen"
    ):
        tabelle = _abschnitt(abschnitt, ueberschrift)
        for taste, beschreibung in re.findall(
            r"^\| `([^`]+)` \| (.+?) \|$", tabelle, re.M
        ):
            if taste not in befehle:
                continue
            erstes_wort = befehle[taste].split()[0].lower()
            assert beschreibung.lower().startswith(erstes_wort), (
                f"{taste}: Handbuch „{beschreibung}“, Menü „{befehle[taste]}“"
            )
            geprueft += 1
    assert geprueft >= 20
    assert befehle["Strg+O"] == "Projekt öffnen"


def test_hilfe_handbuch_oeffnet_das_handbuch(qtbot) -> None:
    """Punkt 307: das Handbuch ist in Natter erreichbar, in derselben
    Ansicht wie die übrigen Hilfeseiten."""
    from ide.viewers.hilfe_ansicht import HilfeAnsicht

    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    aktion = fenster.aktionen["hilfe.handbuch"].qaction
    assert aktion in fenster.menue("Hilfe").actions()

    aktion.trigger()

    ansicht = fenster.editor_tabs.currentWidget()
    assert isinstance(ansicht, HilfeAnsicht)
    index = fenster.editor_tabs.currentIndex()
    assert fenster.editor_tabs.tabText(index) == "Handbuch"
    text = ansicht.toPlainText()
    assert "Natter-Handbuch" in text
    assert "Mit einer Datenbank arbeiten" in text
    assert "Als ZIP speichern" in text


def test_handbuch_beschreibt_zip_abgabe_und_datenbank() -> None:
    """Punkt 307: zwei Aufgaben aus dem Unterricht fehlten."""
    abgabe = " ".join(
        _abschnitt(HANDBUCH, "### 3.6 Eine Aufgabe verteilen und die Abgaben einsammeln").split()
    )
    assert "Projekt → Als ZIP speichern …" in abgabe

    datenbank = " ".join(
        _abschnitt(HANDBUCH, "### 3.8 Mit einer Datenbank arbeiten").split()
    )
    for begriff in (
        "Ansicht → Datenbank", "Verbinden", "CREATE TABLE", "DBGrid",
        "show_rows", "SQLite3Connection",
    ):
        assert begriff in datenbank, begriff


def test_handbuch_nennt_projekt_schliessen(qtbot) -> None:
    """Punkt 306: der Menüweg im Handbuch stimmt mit dem Menü."""
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    eintrag = fenster.aktionen["projekt.schliessen"].qaction.text()

    text = " ".join(_abschnitt(HANDBUCH, "### Zurück zur Startseite").split())
    assert f"Projekt → {eintrag}" in text


def test_erste_schritte_nennt_beide_vorlagen_wie_der_dialog() -> None:
    """„Erste Schritte“ beschrieb nur das Fensterprogramm; wer mit einem
    Konsolenprogramm anfing, fand sein Projekt nicht wieder. Die Namen
    der Vorlagen stehen so da wie im Dialog „Neues Projekt“."""
    from ide.project.neu_dialog import _VORLAGEN_ANZEIGE

    text = (WURZEL / "docs" / "erste_schritte.md").read_text(encoding="utf-8")
    handbuch = (WURZEL / "docs" / "handbuch.md").read_text(encoding="utf-8")
    for name in _VORLAGEN_ANZEIGE.values():
        assert f"**{name}**" in text, name
        assert f"**{name}**" in handbuch, name
    assert "input(" in text and "def main():" in text
    assert "Startbild" not in text

