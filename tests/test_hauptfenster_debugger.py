"""Tests für die Debugger-Verdrahtung in HauptFenster (F5, Abschnitt
7.8/8.1): Breakpoints aus offenen Editor-Tabs, DebugSitzung-Signale
füllen Variablen-/Aufrufstapel-Panel. Gegen echtes `debugpy`, kein Mock.
Siehe docs/arbeitspakete/M4.md, Schritt 6.
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


def test_f5_ohne_projekt_zeigt_hinweis() -> None:
    fenster = HauptFenster()
    fenster._projekt_mit_debugger_starten_aktion()
    assert fenster.statusBar().currentMessage() == "Kein Projekt offen."


def test_f5_mit_ruff_fund_startet_nicht(tmp_path: Path) -> None:
    fenster = HauptFenster()
    _projekt_oeffnen(fenster, tmp_path, "def f():\n    return nicht_definiert\n")
    fenster._projekt_mit_debugger_starten_aktion()
    assert fenster.debug_sitzung is None
    assert fenster.meldungen_liste.count() >= 1


def test_f5_haelt_bei_einem_im_editor_gesetzten_breakpoint(qtbot, tmp_path: Path) -> None:
    fenster = HauptFenster()
    _projekt_oeffnen(
        fenster, tmp_path, "zahl = 42\nmarker = 1  # Zeile 2, Breakpoint\n"
    )
    editor = fenster.datei_oeffnen(fenster.projekt.haupt_datei)
    editor.breakpoint_umschalten(2)

    fenster._projekt_mit_debugger_starten_aktion()
    qtbot.waitUntil(lambda: fenster._aktueller_thread_id is not None, timeout=DEBUG_ZEITGRENZE)

    try:
        assert "Angehalten" in fenster.statusBar().currentMessage()
        qtbot.waitUntil(lambda: fenster.aufrufstapel_liste.count() > 0, timeout=DEBUG_ZEITGRENZE)
        qtbot.waitUntil(
            lambda: fenster.variablen_baum.topLevelItemCount() > 0,
            timeout=DEBUG_ZEITGRENZE,
        )

        werte = {
            fenster.variablen_baum.topLevelItem(i).text(0): fenster.variablen_baum.topLevelItem(
                i
            ).text(1)
            for i in range(fenster.variablen_baum.topLevelItemCount())
        }
        assert werte.get("zahl") == "42"
    finally:
        if fenster.debug_sitzung is not None:
            fenster._debugger_stoppen_aktion()


def test_f5_springt_beim_anhalten_zur_breakpoint_zeile(qtbot, tmp_path: Path) -> None:
    """Beim Durchspielen der Bedienung gefunden: bei einem normalen Halt
    (Breakpoint/Einzelschritt/Pause) blieb der Editor-Cursor an seiner
    alten Stelle stehen - nur eine unbehandelte Ausnahme sprang zur
    richtigen Zeile. Für einen Schüler-Debugger ein zentrales Feature."""
    fenster = HauptFenster()
    _projekt_oeffnen(
        fenster, tmp_path, "zahl = 42\nmarker = 1  # Zeile 2, Breakpoint\n"
    )
    editor = fenster.datei_oeffnen(fenster.projekt.haupt_datei)
    editor.breakpoint_umschalten(2)
    cursor = editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.Start)
    editor.setTextCursor(cursor)

    fenster._projekt_mit_debugger_starten_aktion()
    qtbot.waitUntil(lambda: fenster._aktueller_thread_id is not None, timeout=DEBUG_ZEITGRENZE)

    try:
        qtbot.waitUntil(lambda: fenster.aufrufstapel_liste.count() > 0, timeout=DEBUG_ZEITGRENZE)
        aktiver_editor = fenster.editor_tabs.currentWidget()
        assert aktiver_editor is editor
        assert editor.textCursor().blockNumber() == 1  # Zeile 2, 0-indiziert
    finally:
        if fenster.debug_sitzung is not None:
            fenster._debugger_stoppen_aktion()


def test_klick_auf_aufrufstapel_eintrag_springt_zu_dieser_zeile(qtbot, tmp_path: Path) -> None:
    fenster = HauptFenster()
    _projekt_oeffnen(
        fenster,
        tmp_path,
        "def innen():\n    marker = 1  # Zeile 2, Breakpoint\n    return marker\n\n\ninnen()\n",
    )
    editor = fenster.datei_oeffnen(fenster.projekt.haupt_datei)
    editor.breakpoint_umschalten(2)

    fenster._projekt_mit_debugger_starten_aktion()
    qtbot.waitUntil(lambda: fenster._aktueller_thread_id is not None, timeout=DEBUG_ZEITGRENZE)

    try:
        qtbot.waitUntil(lambda: fenster.aufrufstapel_liste.count() >= 2, timeout=DEBUG_ZEITGRENZE)
        aeusserer_rahmen = fenster.aufrufstapel_liste.item(1)  # main.py, Zeile 6

        fenster._bei_aufrufstapel_klick(aeusserer_rahmen)

        assert editor.textCursor().blockNumber() == 5  # Zeile 6, 0-indiziert
    finally:
        if fenster.debug_sitzung is not None:
            fenster._debugger_stoppen_aktion()


def test_fortsetzen_laesst_das_programm_zu_ende_laufen(qtbot, tmp_path: Path) -> None:
    fenster = HauptFenster()
    _projekt_oeffnen(
        fenster,
        tmp_path,
        'from pathlib import Path\n'
        'Path("marker.txt").write_text("fertig")\n'
        'marker = 1  # Zeile 3, Breakpoint\n',
    )
    editor = fenster.datei_oeffnen(fenster.projekt.haupt_datei)
    editor.breakpoint_umschalten(3)

    fenster._projekt_mit_debugger_starten_aktion()
    qtbot.waitUntil(lambda: fenster._aktueller_thread_id is not None, timeout=DEBUG_ZEITGRENZE)

    fenster._debugger_fortsetzen_aktion()
    qtbot.waitUntil(lambda: fenster.debug_sitzung is None, timeout=DEBUG_ZEITGRENZE)

    assert (tmp_path / "marker.txt").read_text(encoding="utf-8") == "fertig"


def test_unbehandelte_ausnahme_zeigt_die_fehlerkatalog_meldung_und_springt_hin(
    qtbot, tmp_path: Path
) -> None:
    fenster = HauptFenster()
    _projekt_oeffnen(
        fenster, tmp_path, "def f():\n    return 1 / 0\n\nf()\n"
    )

    fenster._projekt_mit_debugger_starten_aktion()
    qtbot.waitUntil(lambda: fenster.meldungen_liste.count() > 0, timeout=DEBUG_ZEITGRENZE)

    try:
        text = fenster.meldungen_liste.item(0).text()
        assert "ZeroDivisionError" in text
        assert "Zeile 2" in text

        editor = fenster.editor_tabs.currentWidget()
        assert editor.property("pfad") == str(fenster.projekt.haupt_datei)
        assert editor.textCursor().blockNumber() == 1  # Zeile 2, 0-indiziert
    finally:
        if fenster.debug_sitzung is not None:
            fenster._debugger_stoppen_aktion()


def test_als_tabelle_anzeigen_oeffnet_ein_tabellenfenster(qtbot, tmp_path: Path) -> None:
    """„Als Tabelle anzeigen“ im Panel „Variablen“ (Abschnitt 11.6):
    Ende zu Ende über das echte Hauptfenster und einen echten
    angehaltenen Debuggee."""
    fenster = HauptFenster()
    _projekt_oeffnen(
        fenster,
        tmp_path,
        'schueler = [{"name": "Anna", "punkte": 12}, {"name": "Ben", "punkte": 9}]\n'
        "marker = 1  # Zeile 2, Breakpoint\n",
    )
    editor = fenster.datei_oeffnen(fenster.projekt.haupt_datei)
    editor.breakpoint_umschalten(2)

    fenster._projekt_mit_debugger_starten_aktion()
    qtbot.waitUntil(lambda: fenster._aktueller_thread_id is not None, timeout=DEBUG_ZEITGRENZE)

    try:
        qtbot.waitUntil(
            lambda: fenster.variablen_baum.topLevelItemCount() > 0, timeout=DEBUG_ZEITGRENZE
        )
        fenster.variable_als_tabelle_zeigen("schueler")
        qtbot.waitUntil(
            lambda: fenster.letzte_tabellen_ansicht is not None, timeout=DEBUG_ZEITGRENZE
        )

        widget = fenster.letzte_tabellen_ansicht.tabelle_widget
        assert widget.columnCount() == 2
        assert widget.horizontalHeaderItem(0).text() == "name"
        assert widget.rowCount() == 2
        assert widget.item(1, 0).text() == "Ben"
    finally:
        if fenster.debug_sitzung is not None:
            fenster._debugger_stoppen_aktion()


def test_als_tabelle_anzeigen_ohne_debugger_meldet_das() -> None:
    fenster = HauptFenster()

    fenster.variable_als_tabelle_zeigen("irgendwas")

    assert "Kein angehaltenes Programm" in fenster.statusBar().currentMessage()


def test_special_variables_zeile_wird_nicht_als_ausdruck_geschickt(qtbot, tmp_path: Path) -> None:
    """Beim Bildschirmfoto gefunden: `debugpy` blendet im
    Variablen-Panel die Sammelzeile „special variables“ ein. Ein
    Doppelklick darauf schickte diesen Text als Python-Ausdruck an den
    Debugger und brachte einen Syntaxfehler ins Panel „Meldungen“."""
    fenster = HauptFenster()
    _projekt_oeffnen(fenster, tmp_path, "zahlen = [1, 2]\nmarker = 1  # Zeile 2\n")
    editor = fenster.datei_oeffnen(fenster.projekt.haupt_datei)
    editor.breakpoint_umschalten(2)

    fenster._projekt_mit_debugger_starten_aktion()
    qtbot.waitUntil(lambda: fenster._aktueller_thread_id is not None, timeout=DEBUG_ZEITGRENZE)

    try:
        qtbot.waitUntil(
            lambda: fenster.variablen_baum.topLevelItemCount() > 0, timeout=DEBUG_ZEITGRENZE
        )
        vorher = fenster.meldungen_liste.count()

        fenster.variable_als_tabelle_zeigen("special variables")

        assert "keine Variable" in fenster.statusBar().currentMessage()
        assert fenster.letzte_tabellen_ansicht is None
        assert fenster.meldungen_liste.count() == vorher
    finally:
        if fenster.debug_sitzung is not None:
            fenster._debugger_stoppen_aktion()


def test_variablen_panel_kommt_beim_halt_nach_vorne(qtbot, tmp_path: Path) -> None:
    """Beim Bildschirmfoto gefunden: das Programm stand am Breakpoint,
    die Variablen waren geladen - sichtbar blieb aber „Meldungen“."""
    fenster = HauptFenster()
    _projekt_oeffnen(fenster, tmp_path, "zahl = 42\nmarker = 1  # Zeile 2\n")
    editor = fenster.datei_oeffnen(fenster.projekt.haupt_datei)
    editor.breakpoint_umschalten(2)

    fenster._projekt_mit_debugger_starten_aktion()
    qtbot.waitUntil(lambda: fenster._aktueller_thread_id is not None, timeout=DEBUG_ZEITGRENZE)

    try:
        qtbot.waitUntil(
            lambda: fenster.variablen_baum.topLevelItemCount() > 0, timeout=DEBUG_ZEITGRENZE
        )
        assert fenster.panels.currentWidget() is fenster.variablen_baum
    finally:
        if fenster.debug_sitzung is not None:
            fenster._debugger_stoppen_aktion()


def test_unbehandelte_ausnahme_zeigt_weiter_die_meldungen(qtbot, tmp_path: Path) -> None:
    """Gegenprobe zum Test oben: bei einer unbehandelten Ausnahme
    behält das Panel „Meldungen“ den Vorrang - dort steht die
    Fehlermeldung aus dem Fehlerkatalog (Abschnitt 8.3)."""
    fenster = HauptFenster()
    _projekt_oeffnen(fenster, tmp_path, "zahlen = [1, 2]\nprint(zahlen[5])\n")

    fenster._projekt_mit_debugger_starten_aktion()
    qtbot.waitUntil(lambda: fenster.meldungen_liste.count() > 0, timeout=DEBUG_ZEITGRENZE)

    try:
        assert fenster.panels.currentWidget() is fenster.meldungen_liste
    finally:
        if fenster.debug_sitzung is not None:
            fenster._debugger_stoppen_aktion()
