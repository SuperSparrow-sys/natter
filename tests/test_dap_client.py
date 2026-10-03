"""Tests für ide/debugger/dap_client.py: DAP-Client-Grundgerüst gegen
echtes `debugpy` (kein Mock, kein VS Code nötig – siehe
Arbeitspaket M4, Schritt 3). Startet echte Unterprozesse, daher
langsamer als reine Unit-Tests.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

from ide.debugger import DapClient, DapFehler
from ide.prozess import prozessbaum_beenden


def _skript_schreiben(tmp_path: Path, inhalt: str) -> Path:
    skript = tmp_path / "ziel.py"
    skript.write_text(inhalt, encoding="utf-8")
    return skript


def test_handshake_gelingt_und_der_debuggee_endet_mit_code_0(tmp_path: Path) -> None:
    """Nach dem Handshake läuft das Programm zu Ende, mit Exitcode 0.
    Die Ereignisse, die debugpy schon vor „initialized“ schickt
    (`output`, Telemetrie; Abschnitt 8.1), stören den Handshake nicht,
    sondern landen in `ereignisse`."""
    skript = _skript_schreiben(
        tmp_path, 'from pathlib import Path\nPath("lief.txt").write_text("ja")\n'
    )
    client = DapClient()
    try:
        client.starten(skript, arbeitsordner=tmp_path)
        assert client.prozess is not None
        client.prozess.wait(timeout=20)
        assert any(e.get("event") == "output" for e in client.ereignisse)
    finally:
        client.beenden()

    assert (tmp_path / "lief.txt").exists()
    assert client.prozess.returncode == 0


def test_projektdateien_wie_random_py_stoeren_den_debugger_nicht(
    tmp_path: Path,
) -> None:
    """Eine `random.py` oder `string.py` im Projektordner ersetzte das
    gleichnamige Modul, solange debugpy lud, und der Debugger kam nach
    drei Versuchen zu je 30 Sekunden nicht hoch. Das Programm findet
    seine eigenen Dateien trotzdem."""
    for name in ("random.py", "string.py", "queue.py"):
        (tmp_path / name).write_text(
            "raise SystemExit('falsches Modul')\n", encoding="utf-8"
        )
    (tmp_path / "u_hilfe.py").write_text("WERT = 'ja'\n", encoding="utf-8")
    skript = _skript_schreiben(
        tmp_path,
        "from pathlib import Path\n"
        "import u_hilfe\n"
        "Path('lief.txt').write_text(u_hilfe.WERT)\n",
    )
    client = DapClient()
    try:
        client.starten(skript, arbeitsordner=tmp_path)
        assert client.prozess is not None
        client.prozess.wait(timeout=30)
    finally:
        client.beenden()

    assert (tmp_path / "lief.txt").read_text() == "ja"


def test_fehlerantwort_und_beenden_eines_laufenden_programms(tmp_path: Path) -> None:
    """Eine Anfrage, die debugpy nicht kennt, endet in `DapFehler`.

    Danach beendet `beenden()` das noch laufende Programm (Punkt 222).
    Bis 0.3.5 schloss es nur die Verbindung; debugpy löste sich
    daraufhin vom Programm, und das lief weiter, bis `wait()` nach der
    Zeitgrenze mit einer Ausnahme aufgab. Jetzt geht zuerst ein
    `disconnect` mit `terminateDebuggee` hinaus."""
    skript = _skript_schreiben(tmp_path, "import time\ntime.sleep(120)\n")
    client = DapClient()
    try:
        client.starten(skript, arbeitsordner=tmp_path)
        with pytest.raises(DapFehler):
            client.anfrage("einBefehlDenEsNichtGibt")

        anfang = time.monotonic()
        client.beenden(zeitlimit=15)
        dauer = time.monotonic() - anfang
    finally:
        if client.prozess is not None:
            prozessbaum_beenden(client.prozess)

    assert client.prozess.poll() is not None
    assert dauer < 15, "Erst die Zeitgrenze hat das Programm beendet."


def test_zwei_clients_koennen_unabhaengig_gleichzeitig_laufen(tmp_path: Path) -> None:
    ordner_a = tmp_path / "a"
    ordner_b = tmp_path / "b"
    ordner_a.mkdir()
    ordner_b.mkdir()
    skript_a = _skript_schreiben(
        ordner_a, 'from pathlib import Path\nPath("a.txt").write_text("a")\n'
    )
    skript_b = _skript_schreiben(
        ordner_b, 'from pathlib import Path\nPath("b.txt").write_text("b")\n'
    )

    client_a = DapClient()
    client_b = DapClient()
    try:
        client_a.starten(skript_a, arbeitsordner=ordner_a)
        client_b.starten(skript_b, arbeitsordner=ordner_b)
        client_a.prozess.wait(timeout=20)
        client_b.prozess.wait(timeout=20)
    finally:
        client_a.beenden()
        client_b.beenden()

    assert (ordner_a / "a.txt").exists()
    assert (ordner_b / "b.txt").exists()


def test_ein_gescheiterter_versuch_fuehrt_zu_einem_zweiten(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scheitert ein Start, gibt `starten` nicht auf, sondern versucht
    es mit einem neuen Adapter und einer neuen Kennung (M11,
    Abschnitt 5)."""
    import ide.debugger.dap_client as modul

    skript = _skript_schreiben(tmp_path, "marker = 1" + chr(10))
    echter_handshake = modul.DapClient._handshake
    versuche: list[int] = []

    def _einmal_scheitern(selbst, *args, **kwargs):
        versuche.append(selbst._adapter.pid)
        if len(versuche) == 1:
            raise DapFehler("Adapter antwortet nicht")
        return echter_handshake(selbst, *args, **kwargs)

    monkeypatch.setattr(modul.DapClient, "_handshake", _einmal_scheitern)

    client = DapClient()
    try:
        client.starten(skript, arbeitsordner=tmp_path)

        assert 2 <= len(versuche) <= modul._STARTVERSUCHE
        assert len(set(versuche)) == len(versuche)  # jedes Mal ein neuer Adapter
        assert client.prozess is not None
    finally:
        client.beenden()


def test_ein_fehlstart_laesst_keinen_debugpy_prozess_zurueck(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sonst sammelten sich genau die Waisen an, die beim Aufräumen nach
    der Funktionsprüfung schon einmal zu neunundvierzig wartenden
    `debugpy`-Prozessen geführt haben."""
    import ide.debugger.dap_client as modul

    skript = _skript_schreiben(tmp_path, "marker = 1" + chr(10))
    prozesse = []
    echtes_popen = modul.subprocess.Popen

    def _merken(befehl, *args, **kwargs):
        prozess = echtes_popen(befehl, *args, **kwargs)
        if any("debugpy" in teil for teil in befehl):
            prozesse.append(prozess)
        return prozess

    monkeypatch.setattr(modul.subprocess, "Popen", _merken)
    monkeypatch.setattr(
        modul.DapClient,
        "_handshake",
        lambda selbst, *a, **k: (_ for _ in ()).throw(DapFehler("nichts da")),
    )

    client = DapClient()
    with pytest.raises(DapFehler, match="Versuchen"):
        client.starten(skript, arbeitsordner=tmp_path)

    assert len(prozesse) == modul._STARTVERSUCHE
    for prozess in prozesse:
        prozess.wait(timeout=10)
        assert prozess.poll() is not None
    assert client.prozess is None


def test_eine_fremde_verbindung_bekommt_keine_sitzung(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Punkt 542: ein Programm, das sich ohne die Kennung zum Adapter
    verbindet, wird nicht angenommen und läuft nicht; die Sitzung
    bekommt das richtige Programm. Für die IDE selbst lauscht kein
    Port mehr: der Adapter spricht über Standardein- und -ausgabe."""
    import subprocess

    import ide.debugger.dap_client as modul

    skript = _skript_schreiben(
        tmp_path,
        "from pathlib import Path" + chr(10)
        + "Path('echt.txt').write_text('1')" + chr(10),
    )
    echter_aufruf = modul.debugpy_aufruf
    fremde: list[subprocess.Popen] = []

    def _vorher_ein_fremder(port, *args, **kwargs):
        befehl, optionen = echter_aufruf(port, *args, **kwargs)
        fremd = [
            teil if teil != kwargs.get("kennung", args[-1] if args else "")
            else "falsch"
            for teil in befehl
        ]
        fremd[-1] = str(tmp_path / "fremd.py")
        (tmp_path / "fremd.py").write_text(
            "from pathlib import Path" + chr(10)
            + "Path('fremd.txt').write_text('1')" + chr(10),
            encoding="utf-8",
        )
        fremde.append(subprocess.Popen(fremd, **modul.ohne_konsole(cwd=tmp_path)))
        time.sleep(1.5)
        return befehl, optionen

    monkeypatch.setattr(modul, "debugpy_aufruf", _vorher_ein_fremder)
    client = DapClient()
    try:
        befehl, _optionen = modul.adapter_aufruf("abc", tmp_path)
        assert "--listen" not in befehl and "--port" not in befehl
        client.starten(skript, arbeitsordner=tmp_path)
        client.prozess.wait(timeout=20)
    finally:
        client.beenden()
        for prozess in fremde:
            prozessbaum_beenden(prozess)

    assert (tmp_path / "echt.txt").exists()
    assert not (tmp_path / "fremd.txt").exists()


def _prozess_lebt(pid: int) -> bool:
    import ctypes

    kernel32 = ctypes.windll.kernel32
    griff = kernel32.OpenProcess(0x1000, False, pid)
    if not griff:
        return False
    try:
        code = ctypes.c_ulong()
        kernel32.GetExitCodeProcess(griff, ctypes.byref(code))
        return code.value == 259  # STILL_ACTIVE
    finally:
        kernel32.CloseHandle(griff)


@pytest.mark.skipif(sys.platform != "win32", reason="prüft Windows-Prozesse")
def test_beenden_erreicht_den_enkel_eines_beendeten_programms(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Punkt 281: das Programm startet `ping` und endet sofort. Mit
    dem Ende der Sitzung endet auch `ping`, obwohl es keinen lebenden
    Elternprozess mehr hat, über den `taskkill /T` es fände.

    Gestartet wird der Interpreter hinter dem der virtuellen Umgebung;
    der Starter von uv hätte sonst mit seinem eigenen Auftragsobjekt
    schon alles beendet. `debugpy` findet er über `PYTHONPATH`."""
    import sysconfig

    import ide.debugger.dap_client as dap_client

    basis = getattr(sys, "_base_executable", sys.executable)
    monkeypatch.setattr(dap_client, "python_befehl", lambda: [basis])
    monkeypatch.setenv("PYTHONPATH", sysconfig.get_paths()["purelib"])
    skript = _skript_schreiben(
        tmp_path,
        "import subprocess\n"
        "from pathlib import Path\n"
        "kind = subprocess.Popen(\n"
        "    ['ping', '-n', '60', '127.0.0.1'],\n"
        "    stdout=subprocess.DEVNULL,\n"
        "    creationflags=subprocess.CREATE_NO_WINDOW,\n"
        ")\n"
        "Path('kind.pid').write_text(str(kind.pid))\n",
    )
    client = DapClient()
    kind_pid: int | None = None
    try:
        client.starten(skript, arbeitsordner=tmp_path)
        assert client.prozess is not None
        client.prozess.wait(timeout=30)
        kind_pid = int((tmp_path / "kind.pid").read_text())
        assert _prozess_lebt(kind_pid)

        client.beenden(zeitlimit=15)

        ende = time.monotonic() + 10
        while _prozess_lebt(kind_pid) and time.monotonic() < ende:
            time.sleep(0.1)
        assert not _prozess_lebt(kind_pid), "ping läuft noch."
    finally:
        if client.prozess is not None:
            prozessbaum_beenden(client.prozess)
        if kind_pid is not None and _prozess_lebt(kind_pid):
            import subprocess

            subprocess.run(
                ["taskkill", "/PID", str(kind_pid), "/F"],
                capture_output=True,
                check=False,
                timeout=30,
            )
