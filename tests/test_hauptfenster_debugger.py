"""Tests für die Debugger-Verdrahtung in HauptFenster (F5, Abschnitt
7.8/8.1): Breakpoints aus offenen Editor-Tabs, DebugSitzung-Signale
füllen Variablen-/Aufrufstapel-Panel. Gegen echtes `debugpy`, kein Mock.
Siehe Arbeitspaket M4, Schritt 6.

Jeder Start eines echten Debuggers kostet ein bis zwei Sekunden. Bis
September 2026 startete hier fast jede Prüfung ihren eigenen Debugger
mit beinahe demselben Programm. Die Prüfungen am Haltepunkt laufen
deshalb jetzt gemeinsam in einem Durchgang durch ein Programm mit zwei
Haltepunkten; nur die unbehandelte Ausnahme braucht ein eigenes.
"""

from __future__ import annotations

import json
from pathlib import Path

from ide.shell.hauptfenster import HauptFenster
from tests.conftest import DEBUG_ZEITGRENZE


def _projekt_oeffnen(fenster: HauptFenster, ordner: Path, main_inhalt: str) -> Path:
    ordner.mkdir(parents=True, exist_ok=True)
    (ordner / "main.py").write_text(main_inhalt, encoding="utf-8")
    daten = {"format": "natter-project/1", "name": "Test", "type": "console", "main": "main.py"}
    natter_pfad = ordner / "test.natter"
    natter_pfad.write_text(json.dumps(daten), encoding="utf-8")
    fenster.projekt_oeffnen(natter_pfad)
    return natter_pfad


def _zeile(quelltext: str, merkmal: str) -> int:
    """Nummer (ab 1) der ersten Zeile, die `merkmal` enthält."""
    return next(
        i + 1 for i, zeile in enumerate(quelltext.splitlines()) if merkmal in zeile
    )


def _variablen(fenster: HauptFenster) -> dict[str, str]:
    baum = fenster.variablen_baum
    return {
        baum.topLevelItem(i).text(0): baum.topLevelItem(i).text(1)
        for i in range(baum.topLevelItemCount())
    }


def test_f5_ohne_projekt_zeigt_hinweis(qtbot) -> None:  # noqa: ANN001
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    fenster._projekt_mit_debugger_starten_aktion()
    meldung = fenster.statusBar().currentMessage()
    assert meldung.startswith("Kein Projekt offen.")
    assert "Projekt → Projekt öffnen …" in meldung


def test_f5_mit_ruff_fund_startet_nicht(qtbot, tmp_path: Path) -> None:  # noqa: ANN001
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    _projekt_oeffnen(fenster, tmp_path, "def f():\n    return nicht_definiert\n")
    fenster._projekt_mit_debugger_starten_aktion()
    assert fenster.debug_sitzung is None
    assert fenster.meldungen_liste.count() >= 1


def test_als_tabelle_anzeigen_ohne_debugger_meldet_das(qtbot) -> None:  # noqa: ANN001
    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    fenster.variable_als_tabelle_zeigen("irgendwas")

    meldung = fenster.statusBar().currentMessage()
    assert "nicht angehalten" in meldung
    assert "Haltepunkt" in meldung


PROGRAMM = (
    "from pathlib import Path\n"
    "\n"
    "\n"
    "def innen():\n"
    "    marker = 1  # zweiter Halt\n"
    "    return marker\n"
    "\n"
    "\n"
    "def verdoppeln(x):\n"
    "    return 2 * x\n"
    "\n"
    "\n"
    'schueler = [{"name": "Anna", "punkte": 12}, {"name": "Ben", "punkte": 9}]\n'
    "zahl = 42\n"
    "halt = 1  # erster Halt\n"
    "innen()  # Aufruf\n"
    'Path("marker.txt").write_text("fertig")\n'
)


def test_ein_durchgang_mit_zwei_haltepunkten(qtbot, tmp_path: Path) -> None:  # noqa: ANN001
    """Ein Lauf, in dem sich alles zeigt, was an einem Haltepunkt zu
    sehen sein soll.

    Am ersten Halt auf Modulebene: die Statuszeile meldet ihn, der
    Editor springt zur Zeile (bis dahin blieb der Cursor stehen, und
    nur eine unbehandelte Ausnahme sprang hin), das Panel „Variablen“
    kommt nach vorne (vorher blieb „Meldungen“ sichtbar) und zeigt die
    Werte ohne die englischen Gruppenzeilen „special variables“ und
    „function variables“ (Punkt 45). Die Sammelzeile „special
    variables“ geht nicht als Python-Ausdruck an den Debugger, und
    „Als Tabelle anzeigen“ öffnet ein Tabellenfenster.

    Am zweiten Halt in einer Funktion: ein Klick auf den äußeren
    Eintrag im Aufrufstapel springt zur aufrufenden Zeile. Danach
    läuft das Programm mit „Fortsetzen“ zu Ende."""
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    _projekt_oeffnen(fenster, tmp_path, PROGRAMM)
    editor = fenster.datei_oeffnen(fenster.projekt.haupt_datei)
    erster = _zeile(PROGRAMM, "erster Halt")
    zweiter = _zeile(PROGRAMM, "zweiter Halt")
    aufruf = _zeile(PROGRAMM, "# Aufruf")
    editor.breakpoint_umschalten(erster)
    editor.breakpoint_umschalten(zweiter)
    cursor = editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.Start)
    editor.setTextCursor(cursor)

    try:
        fenster._projekt_mit_debugger_starten_aktion()
        qtbot.waitUntil(
            lambda: fenster._aktueller_thread_id is not None, timeout=DEBUG_ZEITGRENZE
        )
        assert "Angehalten" in fenster.statusBar().currentMessage()
        qtbot.waitUntil(
            lambda: fenster.aufrufstapel_liste.count() > 0, timeout=DEBUG_ZEITGRENZE
        )
        assert fenster.editor_tabs.currentWidget() is editor
        assert editor.textCursor().blockNumber() == erster - 1

        qtbot.waitUntil(
            lambda: fenster.variablen_baum.topLevelItemCount() > 0,
            timeout=DEBUG_ZEITGRENZE,
        )
        assert fenster.panels.currentWidget() is fenster.variablen_baum
        werte = _variablen(fenster)
        assert werte.get("zahl") == "42"
        assert not [n for n in werte if n.endswith(" variables")], list(werte)

        meldungen_vorher = fenster.meldungen_liste.count()
        fenster.variable_als_tabelle_zeigen("special variables")
        assert "keine Variable" in fenster.statusBar().currentMessage()
        assert fenster.letzte_tabellen_ansicht is None
        assert fenster.meldungen_liste.count() == meldungen_vorher

        fenster.variable_als_tabelle_zeigen("schueler")
        qtbot.waitUntil(
            lambda: fenster.letzte_tabellen_ansicht is not None,
            timeout=DEBUG_ZEITGRENZE,
        )
        widget = fenster.letzte_tabellen_ansicht.tabelle_widget
        assert widget.columnCount() == 2
        assert widget.horizontalHeaderItem(0).text() == "name"
        assert widget.rowCount() == 2
        assert widget.item(1, 0).text() == "Ben"

        fenster._debugger_fortsetzen_aktion()
        qtbot.waitUntil(
            lambda: fenster._aktueller_thread_id is not None
            and fenster.aufrufstapel_liste.count() >= 2
            and "in innen" in fenster.aufrufstapel_liste.item(0).text(),
            timeout=DEBUG_ZEITGRENZE,
        )
        fenster._bei_aufrufstapel_klick(fenster.aufrufstapel_liste.item(1))
        assert editor.textCursor().blockNumber() == aufruf - 1

        fenster._debugger_fortsetzen_aktion()
        qtbot.waitUntil(lambda: fenster.debug_sitzung is None, timeout=DEBUG_ZEITGRENZE)
        assert (tmp_path / "marker.txt").read_text(encoding="utf-8") == "fertig"
    finally:
        if fenster.debug_sitzung is not None:
            fenster._debugger_stoppen_aktion()


def test_unbehandelte_ausnahme_zeigt_die_fehlerkatalog_meldung_und_springt_hin(
    qtbot, tmp_path: Path  # noqa: ANN001
) -> None:
    """Die Meldung aus dem Fehlerkatalog steht im Panel „Meldungen“,
    der Editor springt zur Fehlerzeile. Anders als bei einem
    Haltepunkt behält „Meldungen“ den Vorrang vor „Variablen“, denn
    dort steht die Erklärung (Abschnitt 8.3)."""
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    _projekt_oeffnen(fenster, tmp_path, "def f():\n    return 1 / 0\n\nf()\n")

    try:
        fenster._projekt_mit_debugger_starten_aktion()
        qtbot.waitUntil(
            lambda: fenster.meldungen_liste.count() > 0, timeout=DEBUG_ZEITGRENZE
        )
        text = fenster.meldungen_liste.item(0).text()
        assert "ZeroDivisionError" in text
        assert "Zeile 2" in text

        editor = fenster.editor_tabs.currentWidget()
        assert editor.property("pfad") == str(fenster.projekt.haupt_datei)
        assert editor.textCursor().blockNumber() == 1  # Zeile 2, 0-indiziert
        assert fenster.panels.currentWidget() is fenster.meldungen_liste
    finally:
        if fenster.debug_sitzung is not None:
            fenster._debugger_stoppen_aktion()
