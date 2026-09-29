"""Tests für das Lesen von Nachrichten im DAP-Client und für das Ende
einer `DebugSitzung`, wenn der Lesefaden an einer Nachricht scheitert
(Punkt 428).

Ohne debugpy: der Client bekommt ein Ende eines Socket-Paars, über
das andere schickt der Test die Nachrichten selbst.
"""

from __future__ import annotations

import json
import socket
import threading
import time
from pathlib import Path

import pytest

from ide.debugger import DapClient, DebugSitzung


def _rahmen(nachricht: dict) -> bytes:
    daten = json.dumps(nachricht).encode("utf-8")
    return f"Content-Length: {len(daten)}\r\n\r\n".encode("ascii") + daten


@pytest.fixture
def socket_paar():
    client_seite, test_seite = socket.socketpair()
    yield client_seite, test_seite
    client_seite.close()
    test_seite.close()


def test_stockend_gesendete_grosse_nachricht_kommt_vollstaendig_an(
    socket_paar,  # noqa: ANN001
) -> None:
    """Eine Nachricht über 4 KB kommt in zwei Teilen mit einer Pause
    dazwischen, die länger ist als die Zeitgrenze der Abfrage. Bis
    0.4.2 gingen dabei schon empfangene Bytes verloren."""
    client_seite, test_seite = socket_paar
    ereignis = {
        "seq": 7,
        "type": "event",
        "event": "output",
        "body": {"output": "x" * 20000 + "Ende"},
    }
    daten = _rahmen(ereignis)
    teilung = len(daten) // 2
    client = DapClient()
    client._socket = client_seite

    def senden() -> None:
        test_seite.sendall(daten[:teilung])
        time.sleep(0.3)
        test_seite.sendall(daten[teilung:])

    sender = threading.Thread(target=senden, daemon=True)
    sender.start()
    ende = time.monotonic() + 10
    erhalten = None
    leere_abfragen = 0
    while erhalten is None and time.monotonic() < ende:
        erhalten = client.naechstes_ereignis_abfragen(0.05)
        if erhalten is None:
            leere_abfragen += 1
    sender.join(timeout=5)

    assert erhalten == ereignis
    # Die Pause fiel tatsächlich in eine Abfrage mit abgelaufener
    # Zeitgrenze, sonst bewiese der Test nichts.
    assert leere_abfragen > 0


@pytest.mark.parametrize(
    "ursache",
    ["ungueltiges_json", "unerwartete_ausnahme"],
)
def test_fehler_im_lesefaden_beendet_die_sitzung(
    qtbot, socket_paar, ursache: str, tmp_path: Path  # noqa: ANN001
) -> None:
    """Scheitert der Lesefaden an einer Nachricht oder an einer
    beliebigen anderen Ausnahme, meldet die Sitzung das auf Deutsch
    und sendet `beendet`. Bis 0.4.2 endete der Faden still, und Start
    und Stopp blieben im Zustand des laufenden Debuggers."""
    client_seite, test_seite = socket_paar
    sitzung = DebugSitzung()
    client = sitzung.client

    def starten(*_argumente, **_schluessel) -> None:  # noqa: ANN002, ANN003
        client._socket = client_seite

    client.starten = starten
    if ursache == "ungueltiges_json":
        test_seite.sendall(b"Content-Length: 7\r\n\r\n{kaput}")
        erwartet = "kein gültiges JSON"
    else:
        def abfragen(_zeitlimit: float) -> None:
            raise RuntimeError("unerwartet")

        client.naechstes_ereignis_abfragen = abfragen
        erwartet = "RuntimeError: unerwartet"

    meldungen: list[str] = []
    sitzung.fehler.connect(meldungen.append)
    with qtbot.waitSignal(sitzung.beendet, timeout=10000):
        sitzung.starten(
            tmp_path / "ziel.py", arbeitsordner=tmp_path
        )
    sitzung._thread.join(timeout=10)

    assert not sitzung._thread.is_alive()
    qtbot.waitUntil(lambda: bool(meldungen), timeout=5000)
    assert len(meldungen) == 1
    assert meldungen[0].startswith(
        "Die Debug-Sitzung wurde wegen eines Fehlers beendet."
    )
    assert erwartet in meldungen[0]
