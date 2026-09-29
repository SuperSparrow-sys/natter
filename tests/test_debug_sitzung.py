"""Tests für ide/debugger/debug_sitzung.py: Qt-Wrapper um DapClient, der
jede DAP-Interaktion auf einem eigenen Thread ausführt und über Signale
zurückmeldet (Abschnitt 8.1) – die GUI darf beim Warten auf das
Schülerprogramm nicht einfrieren. Gegen echtes `debugpy`, kein Mock.
Siehe Arbeitspaket M4, Schritt 6. `qtbot.waitSignal()` pumpt
dabei die Qt-Ereignisschleife, die Queued-Connection-Signale aus dem
Worker-Thread brauchen, um im Test (Hauptthread) anzukommen.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import pytest

from ide.debugger import DebugSitzung
from ide.prozess import ohne_konsole, prozessbaum_beenden
from tests.conftest import DEBUG_ZEITGRENZE


def _skript_schreiben(tmp_path: Path, inhalt: str) -> Path:
    skript = tmp_path / "ziel.py"
    skript.write_text(inhalt, encoding="utf-8")
    return skript


def test_ein_lauf_vom_haltepunkt_bis_zum_ende(qtbot, tmp_path: Path) -> None:  # noqa: ANN001
    """Die Signale einer Sitzung der Reihe nach: `angehalten` am
    Anfangs-Haltepunkt, bevor die Zeile lief; `aufrufstapel_bereit`
    mit dem auf eigenen Code gefilterten Stapel; `bereiche_bereit`
    und `variablen_bereit` mit den Werten; `fehler` bei einer
    Anfrage, die debugpy ablehnt; nach `fortsetzen` schließlich
    `beendet` mit dem Exitcode 0."""
    skript = _skript_schreiben(
        tmp_path,
        "from pathlib import Path\n"
        "zahl = 42\n"
        'Path("marker.txt").write_text("fertig")\n',
    )
    sitzung = DebugSitzung()
    try:
        with qtbot.waitSignal(sitzung.angehalten, timeout=DEBUG_ZEITGRENZE) as signal:
            sitzung.starten(
                skript, arbeitsordner=tmp_path, anfangs_breakpoints={skript: [3]}
            )
        assert signal.args[0]["reason"] == "breakpoint"
        assert not (tmp_path / "marker.txt").exists()
        thread_id = signal.args[0]["threadId"]

        with qtbot.waitSignal(
            sitzung.aufrufstapel_bereit, timeout=DEBUG_ZEITGRENZE
        ) as stapel_signal:
            sitzung.aufrufstapel_lesen(thread_id)
        stapel = stapel_signal.args[0]
        assert len(stapel) == 1
        assert stapel[0]["name"] == "<module>"

        with qtbot.waitSignal(
            sitzung.bereiche_bereit, timeout=DEBUG_ZEITGRENZE
        ) as bereiche_signal:
            sitzung.bereiche_lesen(stapel[0]["id"])
        locals_referenz = next(
            b for b in bereiche_signal.args[0] if b["name"] == "Locals"
        )["variablesReference"]

        with qtbot.waitSignal(
            sitzung.variablen_bereit, timeout=DEBUG_ZEITGRENZE
        ) as var_signal:
            sitzung.variablen_lesen(locals_referenz)
        werte = {v["name"]: v["value"] for v in var_signal.args[0]}
        assert werte["zahl"] == "42"

        with qtbot.waitSignal(sitzung.fehler, timeout=DEBUG_ZEITGRENZE) as fehler:
            # existiert nicht -> echte DAP-Fehlerantwort
            sitzung.aufrufstapel_lesen(999999)
        assert fehler.args[0]

        with qtbot.waitSignal(sitzung.beendet, timeout=DEBUG_ZEITGRENZE) as ende:
            sitzung.fortsetzen(thread_id)
        assert ende.args[0] == 0
        assert (tmp_path / "marker.txt").read_text(encoding="utf-8") == "fertig"
    finally:
        sitzung.beenden()


def test_ungueltiger_skriptpfad_fuehrt_trotzdem_zu_einem_beendet_signal(
    qtbot, tmp_path: Path  # noqa: ANN001
) -> None:
    # Eine fehlende Datei ist kein DAP-/Verbindungsfehler (Handshake
    # gelingt trotzdem) - der Absturz passiert erst innerhalb des
    # Schülerprogramm-Prozesses, das "fehler"-Signal ist dafür nicht
    # gedacht (siehe Docstring: DAP-/Verbindungsfehler). Der Exitcode
    # selbst ist bei einem so frühen Absturz (noch vor Beginn der
    # eigentlichen Debug-Sitzung) über das DAP-"exited"-Event nicht
    # zuverlässig gefüllt - hier wird nur geprüft, dass "beendet"
    # trotzdem zuverlässig feuert (kein hängender DebugSitzung-Zustand).
    sitzung = DebugSitzung()
    try:
        with qtbot.waitSignal(sitzung.beendet, timeout=DEBUG_ZEITGRENZE):
            sitzung.starten(
                tmp_path / "gibt_es_nicht.py",
                arbeitsordner=tmp_path,
                anfangs_breakpoints={},
            )
    finally:
        sitzung.beenden()


# -- Stopp während des Starts (Punkt 222) ---------------------------------


def _kinder_von(pids: set[int]) -> list[tuple[int, str]]:
    """Lebende Prozesse, deren Elternprozess in `pids` liegt, mit
    Kennung und Befehlszeile. Der Elternprozess darf schon beendet
    sein: Windows führt seine Kennung weiter an den Kindern."""
    abfrage = (
        "Get-CimInstance Win32_Process | ForEach-Object "
        '{ "$($_.ProcessId)`t$($_.ParentProcessId)`t$($_.CommandLine)" }'
    )
    # PowerShell schreibt in der OEM-Codepage. Eine Befehlszeile mit
    # Umlaut in einem fremden Prozess ließ die Abfrage sonst mit
    # UnicodeDecodeError scheitern und `stdout` bei None stehen.
    ausgabe = subprocess.run(
        ["powershell", "-NoProfile", "-Command", abfrage],
        **ohne_konsole(
            capture_output=True, encoding="oem",
            errors="replace", timeout=60,
        ),
    ).stdout
    kinder = []
    for zeile in ausgabe.splitlines():
        teile = zeile.split("\t", 2)
        if len(teile) == 3 and teile[1].isdigit() and int(teile[1]) in pids:
            kinder.append((int(teile[0]), teile[2]))
    return kinder


@pytest.mark.skipif(sys.platform != "win32", reason="Prozessliste über Windows")
@pytest.mark.parametrize("zeitpunkt", ["sofort", "nach_dem_prozessstart"])
def test_ein_stopp_waehrend_des_starts_laesst_nichts_zurueck(
    qtbot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, zeitpunkt: str  # noqa: ANN001
) -> None:
    """Punkt 222: wurde eine Sitzung beendet, während der Debugger
    noch startete (F9 und gleich wieder Stopp, oder das Fenster wurde
    geschlossen), startete der Hintergrundfaden danach einen neuen
    Debugger, der ewig auf eine Verbindung wartete, oder das Programm
    lief unsichtbar weiter.

    Geprüft an zwei Stellen des Starts: bevor der Prozess überhaupt
    läuft, und während er läuft, die Verbindung aber noch nicht steht.
    Danach muss der Faden zu Ende sein, jeder gestartete Prozess
    beendet und keiner seiner Kindprozesse mehr am Leben - und ein
    Stopp ist kein Fehler, den die IDE melden müsste."""
    import ide.debugger.dap_client as modul

    gestartet: list[subprocess.Popen] = []
    echtes_popen = modul.subprocess.Popen

    def _merken(befehl, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003, ANN202
        prozess = echtes_popen(befehl, *args, **kwargs)
        if "debugpy" in befehl:
            gestartet.append(prozess)
        return prozess

    monkeypatch.setattr(modul.subprocess, "Popen", _merken)

    skript = _skript_schreiben(
        tmp_path,
        "import time\n"
        "from pathlib import Path\n"
        'Path("lief.txt").write_text("ja")\n'
        "time.sleep(120)\n",
    )
    sitzung = DebugSitzung()
    fehler: list[str] = []
    beendet: list[int] = []
    sitzung.fehler.connect(fehler.append)
    sitzung.beendet.connect(beendet.append)
    try:
        sitzung.starten(skript, arbeitsordner=tmp_path)
        if zeitpunkt == "nach_dem_prozessstart":
            qtbot.waitUntil(lambda: bool(gestartet), timeout=DEBUG_ZEITGRENZE)
        sitzung.beenden()

        sitzung._thread.join(timeout=20)
        assert not sitzung._thread.is_alive(), "Der Faden startet weiter."

        # Ein Nachzügler aus dem Baum braucht einen Augenblick.
        ende = time.monotonic() + 10
        pids = {p.pid for p in gestartet}
        uebrig = _kinder_von(pids)
        while uebrig and time.monotonic() < ende:
            time.sleep(0.5)
            uebrig = _kinder_von(pids)
        assert [p.pid for p in gestartet if p.poll() is None] == []
        assert uebrig == []
        qtbot.wait(100)  # Signale aus dem Faden zustellen
        assert fehler == []
        assert beendet == []
    finally:
        sitzung.beenden()
        for prozess in gestartet:
            prozessbaum_beenden(prozess)
