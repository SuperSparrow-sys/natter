"""Tests für ide/debugger/dap_client.py: Breakpoints und Ausführungs-
steuerung (Abschnitt 8.1). Gegen echtes `debugpy`, kein Mock. Siehe
Arbeitspaket M4, Schritt 4.

Jeder Start eines echten Debuggers kostet ein bis zwei Sekunden. Die
Schritte, die sich in einem Programm nacheinander zeigen lassen, laufen
deshalb in einem Durchgang.
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


def test_haltepunkte_bis_cursor_prozedurschritte_und_fortsetzen(tmp_path: Path) -> None:
    """Ein Durchgang durch ein Programm, das in jeder Zeile den Marker
    neu schreibt; am Marker lässt sich ablesen, welche Zeile zuletzt
    lief.

    - Ein Anfangs-Haltepunkt hält an, bevor seine Zeile läuft.
    - „Bis Cursor“ hält an der Zielzeile und lässt die übrigen
      Haltepunkte stehen: das folgende `fortsetzen()` hält am
      Haltepunkt dahinter.
    - Ein Prozedurschritt führt genau eine Zeile aus, ohne in den
      Aufruf `Path(...).write_text(...)` hineinzusteigen (Abschnitt
      7.9: nur der Einzelschritt steigt hinein).
    - `fortsetzen()` lässt das Programm zu Ende laufen, Exitcode 0.
    """
    skript = _skript_schreiben(
        tmp_path,
        "from pathlib import Path\n"
        'Path("marker.txt").write_text("1", encoding="utf-8")\n'
        'Path("marker.txt").write_text("2", encoding="utf-8")\n'
        'Path("marker.txt").write_text("3", encoding="utf-8")\n'
        'Path("marker.txt").write_text("4", encoding="utf-8")\n'
        'Path("marker.txt").write_text("5", encoding="utf-8")\n'
        'Path("marker.txt").write_text("fertig", encoding="utf-8")\n',
    )
    client = DapClient()
    try:
        client.starten(skript, arbeitsordner=tmp_path, anfangs_breakpoints={skript: [2, 4]})
        ereignis = client.angehalten_abwarten()
        thread_id = ereignis["threadId"]
        assert ereignis["reason"] == "breakpoint"
        assert _marker(tmp_path) is None  # Zeile 2 wurde noch nicht ausgeführt

        cursor_ereignis = client.bis_cursor_ausfuehren(skript, 3, thread_id)
        assert cursor_ereignis["reason"] == "breakpoint"
        assert _marker(tmp_path) == "1"  # Zeile 2 lief, Zeile 3 noch nicht

        client.fortsetzen(thread_id)
        assert client.angehalten_abwarten()["reason"] == "breakpoint"  # Zeile 4 noch da
        assert _marker(tmp_path) == "2"

        client.prozedurschritt(thread_id)
        client.angehalten_abwarten()
        assert _marker(tmp_path) == "3"

        client.prozedurschritt(thread_id)
        client.angehalten_abwarten()
        assert _marker(tmp_path) == "4"

        client.fortsetzen(thread_id)
        client.prozess.wait(timeout=20)
    finally:
        client.beenden()

    assert _marker(tmp_path) == "fertig"
    assert client.prozess.returncode == 0


def test_einzelschritt_steigt_hinein_und_eine_ausnahme_haelt_an(tmp_path: Path) -> None:
    """Abschnitt 7.9: „Einzelschritt in eine andere Unit öffnet diese
    automatisch“ - der Einzelschritt steigt also tatsächlich in f()
    hinein (Zeile 2) und bleibt nicht bei „f()“ stehen. Läuft es dann
    weiter, hält die unbehandelte Ausnahme in f() das Programm an."""
    skript = _skript_schreiben(
        tmp_path,
        "def f():\n"
        "    marker = 1\n"
        "    return marker / 0\n"
        "\n"
        "f()\n",
    )
    client = DapClient()
    try:
        client.starten(skript, arbeitsordner=tmp_path, anfangs_breakpoints={skript: [5]})
        thread_id = client.angehalten_abwarten()["threadId"]

        client.einzelschritt(thread_id)
        client.angehalten_abwarten()
        stapel = client.aufrufstapel_lesen(thread_id)
        assert stapel[0]["name"] == "f"
        assert stapel[0]["line"] == 2

        client.fortsetzen(thread_id)
        assert client.angehalten_abwarten()["reason"] == "exception"
    finally:
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
        client.beenden()
