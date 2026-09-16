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
