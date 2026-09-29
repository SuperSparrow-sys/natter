"""Tests für ide/debugger/dap_client.py: DapClient.naechstes_ereignis_
abfragen() – nicht-blockierendes Abfragen, Grundlage für DebugSitzung
(Abschnitt 8.1: die GUI darf nicht einfrieren). Gegen echtes `debugpy`,
kein Mock. Siehe Arbeitspaket M4, Schritt 6.
"""

from __future__ import annotations

import time
from pathlib import Path

from ide.debugger import DapClient

#: So oft wird höchstens nach einem Nachzügler-Ereignis gesehen, bevor
#: der Test misst. Eine Obergrenze, damit ein Debugger, der unerwartet
#: ununterbrochen sendet, den Test scheitern lässt statt ihn hängen zu
#: lassen.
_HOECHSTENS_NACHZUEGLER = 10


def _skript_schreiben(tmp_path: Path, inhalt: str) -> Path:
    skript = tmp_path / "ziel.py"
    skript.write_text(inhalt, encoding="utf-8")
    return skript


def test_abfragen_von_halt_bis_programmende(tmp_path: Path) -> None:
    """Ein Lauf, drei Eigenschaften von `naechstes_ereignis_abfragen`:
    solange das Programm angehalten steht, kommt nach kurzer Zeit
    `None` zurück, ohne auf das volle `time.sleep` im Programm zu
    warten; schon gesammelte Ereignisse kommen vor neuen vom Socket;
    und nach dem Fortsetzen kommt am Ende `terminated`."""
    skript = _skript_schreiben(tmp_path, "import time\nmarker = 1\ntime.sleep(2)\n")
    client = DapClient()
    try:
        client.starten(skript, arbeitsordner=tmp_path, anfangs_breakpoints={skript: [2]})
        # jetzt angehalten, keine weiteren Events zu erwarten
        thread_id = client.angehalten_abwarten()["threadId"]
        client.ereignisse.clear()  # Telemetrie-Events aus dem Handshake verwerfen
        # `debugpy` schickt noch eine Weile Nachzügler (geladene Module,
        # Telemetrie). Auf einem ausgelasteten Rechner trafen die
        # gelegentlich genau in der Messung unten ein und machten den
        # Test wackelig - er fiel im Gesamtlauf durch und lief einzeln
        # sofort wieder. Deshalb erst leerlaufen lassen.
        for _ in range(_HOECHSTENS_NACHZUEGLER):
            if client.naechstes_ereignis_abfragen(0.2) is None:
                break

        anfang = time.monotonic()
        ergebnis = client.naechstes_ereignis_abfragen(0.2)
        dauer = time.monotonic() - anfang
        assert ergebnis is None
        assert dauer < 1.0  # darf nicht auf das volle time.sleep(2) warten

        client.ereignisse.append({"type": "event", "event": "kuenstlich", "body": {}})
        ergebnis = client.naechstes_ereignis_abfragen(1.0)
        assert ergebnis == {"type": "event", "event": "kuenstlich", "body": {}}

        client.fortsetzen(thread_id)
        ereignis = None
        for _ in range(100):  # bis zu 20 s in kleinen Schritten abfragen
            ereignis = client.naechstes_ereignis_abfragen(0.2)
            if ereignis is not None and ereignis.get("event") == "terminated":
                break
        assert ereignis is not None
        assert ereignis["event"] == "terminated"
    finally:
        client.beenden()
