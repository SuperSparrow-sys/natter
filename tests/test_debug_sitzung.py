"""Tests für ide/debugger/debug_sitzung.py: Qt-Wrapper um DapClient, der
jede DAP-Interaktion auf einem eigenen Thread ausführt und über Signale
zurückmeldet (Abschnitt 8.1) – die GUI darf beim Warten auf das
Schülerprogramm nicht einfrieren. Gegen echtes `debugpy`, kein Mock.
Siehe Arbeitspaket M4, Schritt 6. `qtbot.waitSignal()` pumpt
dabei die Qt-Ereignisschleife, die Queued-Connection-Signale aus dem
Worker-Thread brauchen, um im Test (Hauptthread) anzukommen.
"""

from __future__ import annotations

from pathlib import Path

from ide.debugger import DebugSitzung
from tests.conftest import DEBUG_ZEITGRENZE


def _skript_schreiben(tmp_path: Path, inhalt: str) -> Path:
    skript = tmp_path / "ziel.py"
    skript.write_text(inhalt, encoding="utf-8")
    return skript


def test_angehalten_signal_bei_einem_anfangs_breakpoint(qtbot, tmp_path: Path) -> None:
    skript = _skript_schreiben(
        tmp_path, 'from pathlib import Path\nPath("marker.txt").write_text("1")\n'
    )
    sitzung = DebugSitzung()
    try:
        with qtbot.waitSignal(sitzung.angehalten, timeout=DEBUG_ZEITGRENZE) as signal:
            sitzung.starten(skript, arbeitsordner=tmp_path, anfangs_breakpoints={skript: [2]})

        assert signal.args[0]["reason"] == "breakpoint"
        assert not (tmp_path / "marker.txt").exists()
    finally:
        sitzung.beenden()


def test_beendet_signal_mit_exitcode_0_bei_erfolgreichem_lauf(qtbot, tmp_path: Path) -> None:
    skript = _skript_schreiben(tmp_path, "pass\n")
    sitzung = DebugSitzung()

    with qtbot.waitSignal(sitzung.beendet, timeout=DEBUG_ZEITGRENZE) as signal:
        sitzung.starten(skript, arbeitsordner=tmp_path)

    assert signal.args[0] == 0


def test_fortsetzen_laesst_das_programm_bis_zum_ende_laufen(qtbot, tmp_path: Path) -> None:
    skript = _skript_schreiben(
        tmp_path, 'from pathlib import Path\nPath("marker.txt").write_text("fertig")\n'
    )
    sitzung = DebugSitzung()

    with qtbot.waitSignal(sitzung.angehalten, timeout=DEBUG_ZEITGRENZE) as signal:
        sitzung.starten(skript, arbeitsordner=tmp_path, anfangs_breakpoints={skript: [2]})
    thread_id = signal.args[0]["threadId"]

    with qtbot.waitSignal(sitzung.beendet, timeout=DEBUG_ZEITGRENZE):
        sitzung.fortsetzen(thread_id)

    assert (tmp_path / "marker.txt").read_text(encoding="utf-8") == "fertig"


def test_aufrufstapel_bereit_signal_liefert_den_gefilterten_stapel(qtbot, tmp_path: Path) -> None:
    skript = _skript_schreiben(tmp_path, "marker = 1\n")
    sitzung = DebugSitzung()
    try:
        with qtbot.waitSignal(sitzung.angehalten, timeout=DEBUG_ZEITGRENZE) as signal:
            sitzung.starten(skript, arbeitsordner=tmp_path, anfangs_breakpoints={skript: [1]})
        thread_id = signal.args[0]["threadId"]

        with qtbot.waitSignal(
            sitzung.aufrufstapel_bereit, timeout=DEBUG_ZEITGRENZE
        ) as stapel_signal:
            sitzung.aufrufstapel_lesen(thread_id)

        stapel = stapel_signal.args[0]
        assert len(stapel) == 1
        assert stapel[0]["name"] == "<module>"
    finally:
        sitzung.beenden()


def test_variablen_bereit_signal_liefert_lokale_variablenwerte(qtbot, tmp_path: Path) -> None:
    skript = _skript_schreiben(tmp_path, "zahl = 42\nmarker = 1\n")
    sitzung = DebugSitzung()
    try:
        with qtbot.waitSignal(sitzung.angehalten, timeout=DEBUG_ZEITGRENZE) as signal:
            sitzung.starten(skript, arbeitsordner=tmp_path, anfangs_breakpoints={skript: [2]})
        thread_id = signal.args[0]["threadId"]

        with qtbot.waitSignal(
            sitzung.aufrufstapel_bereit, timeout=DEBUG_ZEITGRENZE
        ) as stapel_signal:
            sitzung.aufrufstapel_lesen(thread_id)
        frame_id = stapel_signal.args[0][0]["id"]

        with qtbot.waitSignal(sitzung.bereiche_bereit, timeout=DEBUG_ZEITGRENZE) as bereiche_signal:
            sitzung.bereiche_lesen(frame_id)
        bereiche = bereiche_signal.args[0]
        locals_referenz = next(b for b in bereiche if b["name"] == "Locals")["variablesReference"]

        with qtbot.waitSignal(sitzung.variablen_bereit, timeout=DEBUG_ZEITGRENZE) as var_signal:
            sitzung.variablen_lesen(locals_referenz)

        werte = {v["name"]: v["value"] for v in var_signal.args[0]}
        assert werte["zahl"] == "42"
    finally:
        sitzung.beenden()


def test_fehler_signal_bei_ungueltigem_thread_id(qtbot, tmp_path: Path) -> None:
    skript = _skript_schreiben(tmp_path, "marker = 1\n")
    sitzung = DebugSitzung()
    try:
        with qtbot.waitSignal(sitzung.angehalten, timeout=DEBUG_ZEITGRENZE):
            sitzung.starten(skript, arbeitsordner=tmp_path, anfangs_breakpoints={skript: [1]})

        with qtbot.waitSignal(sitzung.fehler, timeout=DEBUG_ZEITGRENZE) as signal:
            sitzung.aufrufstapel_lesen(999999)  # existiert nicht -> echte DAP-Fehlerantwort

        assert signal.args[0]
    finally:
        sitzung.beenden()


def test_ungueltiger_skriptpfad_fuehrt_trotzdem_zu_einem_beendet_signal(
    qtbot, tmp_path: Path
) -> None:
    # Eine fehlende Datei ist kein DAP-/Verbindungsfehler (Handshake
    # gelingt trotzdem) - der Absturz passiert erst innerhalb des
    # Schülerprogramm-Prozesses, das "fehler"-Signal ist dafür nicht
    # gedacht (siehe Docstring: DAP-/Verbindungsfehler). Das echte
    # Verhalten für unbehandelte Ausnahmen im Programm selbst - inkl.
    # Fehlerkatalog-Anzeige - ist ein eigener, späterer Schritt. Der
    # Exitcode selbst ist bei einem so frühen Absturz (noch vor Beginn
    # der eigentlichen Debug-Sitzung) über das DAP-"exited"-Event nicht
    # zuverlässig gefüllt - hier wird nur geprüft, dass "beendet"
    # trotzdem zuverlässig feuert (kein hängender DebugSitzung-Zustand).
    sitzung = DebugSitzung()
    with qtbot.waitSignal(sitzung.beendet, timeout=DEBUG_ZEITGRENZE):
        sitzung.starten(
            tmp_path / "gibt_es_nicht.py", arbeitsordner=tmp_path, anfangs_breakpoints={}
        )
