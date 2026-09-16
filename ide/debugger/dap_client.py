"""DapClient: Debug Adapter Protocol (DAP)-Client gegen ein per `debugpy`
gestartetes Schülerprogramm (Abschnitt 8.1, 7.8). Grundgerüst: Prozess
starten, Socket-Verbindung, Handshake. Breakpoints/Ausführungssteuerung
und Variablen/Aufrufstapel folgen in M4, Schritt 4–5.

Nachrichtenrahmen: `Content-Length: N\\r\\n\\r\\n` + N Bytes JSON (DAP-
Standard), siehe `_naechste_nachricht`.

**Aufgeschobene Antwort auf „attach“:** `debugpy` beantwortet den
`attach`-Request nicht sofort, sondern erst nachdem der Client
anschließend `configurationDone` gesendet hat (siehe
`debugpy/adapter/clients.py`, `_start_message_handler`:
``return messaging.NO_RESPONSE  # will respond on "configurationDone"``).
Der korrekte Ablauf ist deshalb: `initialize` (mit Antwort) → `attach`
senden (Antwort kommt später) → auf das Event `initialized` warten →
`configurationDone` senden → jetzt treffen die Antworten auf
`configurationDone` **und** die aufgeschobene `attach`-Antwort ein, in
beliebiger Reihenfolge. `_antwort_abwarten` sammelt deshalb jede Antwort,
die nicht zur gerade erwarteten `seq` passt, statt sie zu verwerfen.
"""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

_STANDARD_ZEITLIMIT = 15.0


class DapFehler(Exception):
    """Verbindungsfehler oder eine Fehlerantwort (`success: false`) vom
    Debug-Adapter."""


def _freien_port_finden() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as temp:
        temp.bind(("127.0.0.1", 0))
        return temp.getsockname()[1]


class DapClient:
    def __init__(self) -> None:
        self.prozess: subprocess.Popen | None = None
        self.ereignisse: list[dict[str, Any]] = []
        self._socket: socket.socket | None = None
        self._puffer = b""
        self._naechste_seq = 1
        self._aufgehobene_antworten: dict[int, dict[str, Any]] = {}

    def starten(
        self,
        skriptpfad: Path,
        *,
        arbeitsordner: Path,
        zeitlimit: float = _STANDARD_ZEITLIMIT,
    ) -> None:
        """Startet `skriptpfad` als eigenen Prozess unter `debugpy`
        (`--listen`/`--wait-for-client`), verbindet sich und führt den
        `initialize`/`attach`-Handshake durch. Nach Rückkehr ist die
        Sitzung konfiguriert (`configurationDone` bereits gesendet) und
        der Debuggee läuft."""
        port = _freien_port_finden()
        self.prozess = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "debugpy",
                "--listen",
                str(port),
                "--wait-for-client",
                str(skriptpfad),
            ],
            cwd=arbeitsordner,
        )
        self._socket = self._verbinden(port, zeitlimit)
        self._socket.settimeout(zeitlimit)
        self._handshake()

    def _verbinden(self, port: int, zeitlimit: float) -> socket.socket:
        ende = time.monotonic() + zeitlimit
        letzter_fehler: OSError | None = None
        while time.monotonic() < ende:
            try:
                return socket.create_connection(("127.0.0.1", port), timeout=1)
            except OSError as fehler:
                letzter_fehler = fehler
                time.sleep(0.1)
        raise DapFehler(f"Konnte nicht mit debugpy auf Port {port} verbinden.") from letzter_fehler

    def _handshake(self) -> None:
        self.anfrage(
            "initialize",
            {"adapterID": "natter", "linesStartAt1": True, "columnsStartAt1": True},
        )
        attach_seq = self._senden("attach", {"justMyCode": False})
        self._ereignis_abwarten("initialized")
        self.anfrage("configurationDone")
        if attach_seq not in self._aufgehobene_antworten:
            self._antwort_abwarten(attach_seq)  # sonst bereits eingetroffen

    def _senden(self, command: str, arguments: dict[str, Any] | None = None) -> int:
        if self._socket is None:
            raise DapFehler("Nicht verbunden.")
        seq = self._naechste_seq
        self._naechste_seq += 1
        nachricht: dict[str, Any] = {"seq": seq, "type": "request", "command": command}
        if arguments is not None:
            nachricht["arguments"] = arguments
        daten = json.dumps(nachricht).encode("utf-8")
        kopf = f"Content-Length: {len(daten)}\r\n\r\n".encode("ascii")
        self._socket.sendall(kopf + daten)
        return seq

    def _naechste_nachricht(self) -> dict[str, Any]:
        assert self._socket is not None
        try:
            while b"\r\n\r\n" not in self._puffer:
                stueck = self._socket.recv(4096)
                if not stueck:
                    raise DapFehler("Verbindung zu debugpy wurde geschlossen.")
                self._puffer += stueck
            kopf, rest = self._puffer.split(b"\r\n\r\n", 1)
            laenge = int(kopf.split(b":")[1].strip())
            while len(rest) < laenge:
                stueck = self._socket.recv(4096)
                if not stueck:
                    raise DapFehler("Verbindung zu debugpy wurde geschlossen.")
                rest += stueck
        except TimeoutError as fehler:
            raise DapFehler("Zeitüberschreitung beim Warten auf debugpy.") from fehler

        self._puffer = rest[laenge:]
        return json.loads(rest[:laenge])

    def anfrage(self, command: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        """Sendet `command` und wartet auf die zugehörige Antwort.
        Zwischendurch empfangene Events landen in `self.ereignisse`."""
        seq = self._senden(command, arguments)
        return self._antwort_abwarten(seq)

    def _antwort_abwarten(self, seq: int) -> dict[str, Any]:
        if seq in self._aufgehobene_antworten:
            return self._auswerten(self._aufgehobene_antworten.pop(seq))

        while True:
            nachricht = self._naechste_nachricht()
            if nachricht.get("type") == "event":
                self.ereignisse.append(nachricht)
                continue
            if nachricht.get("type") != "response":
                continue
            if nachricht.get("request_seq") == seq:
                return self._auswerten(nachricht)
            # Antwort auf eine andere, noch offene Anfrage (z. B. die
            # aufgeschobene "attach"-Antwort) - für später aufheben.
            andere_seq = nachricht.get("request_seq")
            if andere_seq is not None:
                self._aufgehobene_antworten[andere_seq] = nachricht

    def _auswerten(self, antwort: dict[str, Any]) -> dict[str, Any]:
        if not antwort.get("success", True):
            raise DapFehler(antwort.get("message") or f"{antwort.get('command')} fehlgeschlagen")
        return antwort.get("body") or {}

    def _ereignis_abwarten(self, name: str) -> dict[str, Any]:
        for index, ereignis in enumerate(self.ereignisse):
            if ereignis.get("event") == name:
                return self.ereignisse.pop(index).get("body") or {}

        while True:
            nachricht = self._naechste_nachricht()
            if nachricht.get("type") == "event":
                if nachricht.get("event") == name:
                    return nachricht.get("body") or {}
                self.ereignisse.append(nachricht)
            elif nachricht.get("type") == "response":
                andere_seq = nachricht.get("request_seq")
                if andere_seq is not None:
                    self._aufgehobene_antworten[andere_seq] = nachricht

    def beenden(self, zeitlimit: float = 10.0) -> None:
        """Schließt die Verbindung und wartet auf das Prozessende."""
        if self._socket is not None:
            self._socket.close()
            self._socket = None
        if self.prozess is not None:
            self.prozess.wait(timeout=zeitlimit)
