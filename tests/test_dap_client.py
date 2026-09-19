"""Tests für ide/debugger/dap_client.py: DAP-Client-Grundgerüst gegen
echtes `debugpy` (kein Mock, kein VS Code nötig – siehe
docs/arbeitspakete/M4.md, Schritt 3). Startet echte Unterprozesse, daher
langsamer als reine Unit-Tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ide.debugger import DapClient, DapFehler


def _skript_schreiben(tmp_path: Path, inhalt: str) -> Path:
    skript = tmp_path / "ziel.py"
    skript.write_text(inhalt, encoding="utf-8")
    return skript


def test_handshake_gelingt_und_der_debuggee_terminiert(tmp_path: Path) -> None:
    skript = _skript_schreiben(
        tmp_path, 'from pathlib import Path\nPath("lief.txt").write_text("ja")\n'
    )
    client = DapClient()
    try:
        client.starten(skript, arbeitsordner=tmp_path)
        assert client.prozess is not None
        client.prozess.wait(timeout=20)
    finally:
        client.beenden()

    assert (tmp_path / "lief.txt").exists()


def test_prozess_endet_mit_code_0_bei_erfolgreichem_lauf(tmp_path: Path) -> None:
    skript = _skript_schreiben(tmp_path, "pass\n")
    client = DapClient()
    try:
        client.starten(skript, arbeitsordner=tmp_path)
        client.prozess.wait(timeout=20)
    finally:
        client.beenden()

    assert client.prozess.returncode == 0


def test_anfrage_mit_unbekanntem_command_loest_dap_fehler_aus(tmp_path: Path) -> None:
    skript = _skript_schreiben(tmp_path, "import time\ntime.sleep(2)\n")
    client = DapClient()
    try:
        client.starten(skript, arbeitsordner=tmp_path)
        with pytest.raises(DapFehler):
            client.anfrage("einBefehlDenEsNichtGibt")
    finally:
        client.prozess.kill()
        client.beenden()


def test_ereignisse_werden_waehrend_des_handshakes_gesammelt(tmp_path: Path) -> None:
    # output/telemetry-Events (Abschnitt 8.1: pcl-/Qt-Interna später
    # ausblenden) treffen schon vor "initialized" ein und dürfen den
    # Handshake nicht stören, sondern landen in self.ereignisse.
    skript = _skript_schreiben(tmp_path, "pass\n")
    client = DapClient()
    try:
        client.starten(skript, arbeitsordner=tmp_path)
        client.prozess.wait(timeout=20)
        assert any(e.get("event") == "output" for e in client.ereignisse)
    finally:
        client.beenden()


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


def test_ein_belegter_port_fuehrt_zu_einem_zweiten_versuch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`_freien_port_finden()` gibt die Nummer wieder frei, bevor
    `debugpy` sie bindet – in dieser Lücke kann sie ein anderer Prozess
    bekommen. Der Start gibt dann nicht auf, sondern nimmt eine neue
    Nummer (M11, Abschnitt 5)."""
    import ide.debugger.dap_client as modul

    skript = _skript_schreiben(tmp_path, "marker = 1" + chr(10))
    echtes_verbinden = modul.DapClient._verbinden
    versuche: list[int] = []

    def _einmal_scheitern(selbst, port, zeitlimit):
        versuche.append(port)
        if len(versuche) == 1:
            raise DapFehler("Port schon belegt")
        return echtes_verbinden(selbst, port, zeitlimit)

    monkeypatch.setattr(modul.DapClient, "_verbinden", _einmal_scheitern)

    client = DapClient()
    try:
        client.starten(skript, arbeitsordner=tmp_path)

        assert len(versuche) == 2
        assert versuche[0] != versuche[1]  # neue Nummer, nicht dieselbe
        assert client.prozess is not None
    finally:
        if client.prozess is not None:
            client.prozess.kill()
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

    def _merken(*args, **kwargs):
        prozess = echtes_popen(*args, **kwargs)
        prozesse.append(prozess)
        return prozess

    monkeypatch.setattr(modul.subprocess, "Popen", _merken)
    monkeypatch.setattr(
        modul.DapClient,
        "_verbinden",
        lambda selbst, port, zeitlimit: (_ for _ in ()).throw(DapFehler("nichts da")),
    )

    client = DapClient()
    with pytest.raises(DapFehler, match="Versuchen"):
        client.starten(skript, arbeitsordner=tmp_path)

    assert len(prozesse) == modul._STARTVERSUCHE
    for prozess in prozesse:
        prozess.wait(timeout=10)
        assert prozess.poll() is not None
    assert client.prozess is None
