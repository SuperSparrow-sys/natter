"""Tests für ide/debugger/dap_client.py: Breakpoints und Ausführungs-
steuerung (Abschnitt 8.1). Gegen echtes `debugpy`, kein Mock. Siehe
docs/arbeitspakete/M4.md, Schritt 4.
"""

from __future__ import annotations

from pathlib import Path

from ide.debugger import DapClient


def _skript_schreiben(tmp_path: Path, inhalt: str) -> Path:
    skript = tmp_path / "ziel.py"
    skript.write_text(inhalt, encoding="utf-8")
    return skript


def _marker(tmp_path: Path) -> str | None:
    pfad = tmp_path / "marker.txt"
    return pfad.read_text(encoding="utf-8") if pfad.exists() else None


def test_anfangs_breakpoint_haelt_das_programm_an(tmp_path: Path) -> None:
    skript = _skript_schreiben(
        tmp_path,
        'from pathlib import Path\n'
        'Path("marker.txt").write_text("1", encoding="utf-8")\n'
        'Path("marker.txt").write_text("2", encoding="utf-8")\n',
    )
    client = DapClient()
    try:
        client.starten(skript, arbeitsordner=tmp_path, anfangs_breakpoints={skript: [2]})
        ereignis = client.angehalten_abwarten()

        assert ereignis["reason"] == "breakpoint"
        assert _marker(tmp_path) is None  # Zeile 2 wurde noch nicht ausgeführt
    finally:
        if client.prozess is not None:
            client.prozess.kill()
        client.beenden()


def test_fortsetzen_laesst_das_programm_zu_ende_laufen(tmp_path: Path) -> None:
    skript = _skript_schreiben(
        tmp_path,
        'from pathlib import Path\n'
        'Path("marker.txt").write_text("fertig", encoding="utf-8")\n',
    )
    client = DapClient()
    try:
        client.starten(skript, arbeitsordner=tmp_path, anfangs_breakpoints={skript: [2]})
        ereignis = client.angehalten_abwarten()

        client.fortsetzen(ereignis["threadId"])
        client.prozess.wait(timeout=10)
    finally:
        client.beenden()

    assert _marker(tmp_path) == "fertig"
    assert client.prozess.returncode == 0


def test_einzelschritt_fuehrt_genau_eine_zeile_aus(tmp_path: Path) -> None:
    skript = _skript_schreiben(
        tmp_path,
        'from pathlib import Path\n'
        'Path("marker.txt").write_text("1", encoding="utf-8")\n'
        'Path("marker.txt").write_text("2", encoding="utf-8")\n'
        'Path("marker.txt").write_text("3", encoding="utf-8")\n',
    )
    client = DapClient()
    try:
        client.starten(skript, arbeitsordner=tmp_path, anfangs_breakpoints={skript: [2]})
        ereignis = client.angehalten_abwarten()
        thread_id = ereignis["threadId"]
        assert _marker(tmp_path) is None

        client.einzelschritt(thread_id)
        client.angehalten_abwarten()
        assert _marker(tmp_path) == "1"

        client.einzelschritt(thread_id)
        client.angehalten_abwarten()
        assert _marker(tmp_path) == "2"
    finally:
        if client.prozess is not None:
            client.prozess.kill()
        client.beenden()


def test_pause_haelt_ein_frei_laufendes_programm_an(tmp_path: Path) -> None:
    skript = _skript_schreiben(
        tmp_path, "import time\nwhile True:\n    time.sleep(0.05)\n"
    )
    client = DapClient()
    try:
        client.starten(skript, arbeitsordner=tmp_path)
        thread_id = client.thread_id_abwarten()

        client.pausieren(thread_id)
        ereignis = client.angehalten_abwarten()

        assert ereignis["reason"] == "pause"
    finally:
        if client.prozess is not None:
            client.prozess.kill()
        client.beenden()


def test_unbehandelte_ausnahme_haelt_das_programm_an(tmp_path: Path) -> None:
    skript = _skript_schreiben(tmp_path, "def f():\n    return 1 / 0\n\nf()\n")
    client = DapClient()
    try:
        client.starten(skript, arbeitsordner=tmp_path)
        ereignis = client.angehalten_abwarten()

        assert ereignis["reason"] == "exception"
    finally:
        if client.prozess is not None:
            client.prozess.kill()
        client.beenden()


def test_bis_cursor_ausfuehren_behaelt_andere_breakpoints(tmp_path: Path) -> None:
    # Breakpoints bei Zeile 2 und 4; "bis Cursor" zu Zeile 3 darf den
    # Breakpoint bei Zeile 4 nicht mitentfernen - danach muss ein
    # "fortsetzen()" dort erneut anhalten.
    skript = _skript_schreiben(
        tmp_path,
        'from pathlib import Path\n'
        'Path("marker.txt").write_text("1", encoding="utf-8")\n'
        'Path("marker.txt").write_text("2", encoding="utf-8")\n'
        'Path("marker.txt").write_text("3", encoding="utf-8")\n',
    )
    client = DapClient()
    try:
        client.starten(skript, arbeitsordner=tmp_path, anfangs_breakpoints={skript: [2, 4]})
        ereignis = client.angehalten_abwarten()
        thread_id = ereignis["threadId"]

        cursor_ereignis = client.bis_cursor_ausfuehren(skript, 3, thread_id)
        assert cursor_ereignis["reason"] == "breakpoint"
        assert _marker(tmp_path) == "1"  # Zeile 2 lief, Zeile 3 noch nicht

        client.fortsetzen(thread_id)
        letztes_ereignis = client.angehalten_abwarten()

        assert letztes_ereignis["reason"] == "breakpoint"  # Breakpoint bei Zeile 4 noch da
        assert _marker(tmp_path) == "2"  # Zeile 3 lief, Zeile 4 noch nicht
    finally:
        if client.prozess is not None:
            client.prozess.kill()
        client.beenden()
