"""DapClient: Debug Adapter Protocol (DAP)-Client gegen ein per `debugpy`
gestartetes Schülerprogramm (Abschnitt 8.1, 7.8). Prozess starten,
Socket-Verbindung, Handshake, Breakpoints, Ausführungssteuerung,
Variablen und Aufrufstapel.

Nachrichtenrahmen: `Content-Length: N\\r\\n\\r\\n` + N Bytes JSON (DAP-
Standard), siehe `_naechste_nachricht`.

Aufgeschobene Antwort auf „attach“: `debugpy` beantwortet den
`attach`-Request nicht sofort, sondern erst nachdem der Client
anschließend `configurationDone` gesendet hat (siehe
`debugpy/adapter/clients.py`, `_start_message_handler`:
``return messaging.NO_RESPONSE  # will respond on "configurationDone"``).
Der korrekte Ablauf ist deshalb: `initialize` (mit Antwort) → `attach`
senden (Antwort kommt später) → auf das Event `initialized` warten →
`configurationDone` senden → jetzt treffen die Antworten auf
`configurationDone` und die aufgeschobene `attach`-Antwort ein, in
beliebiger Reihenfolge. `_antwort_abwarten` sammelt deshalb jede Antwort,
die nicht zur gerade erwarteten `seq` passt, statt sie zu verwerfen.
"""

from __future__ import annotations

import json
import socket
import subprocess
import time
from pathlib import Path
from typing import Any

from ide.run.interpreter import python_befehl
from pcl.eigener_code import ist_eigener_code

# Großzügig bemessen: schadet der echten Nutzung nicht (ein einzelner
# Start dauert praktisch immer < 5s), macht die Testsuite aber robuster
# gegen Zeitüberschreitungen unter Last, wenn viele DAP-Tests kurz
# hintereinander eigene debugpy-Unterprozesse starten (siehe
# docs/arbeitspakete/M4.md, Hinweis zu den DAP-Tests).
_STANDARD_ZEITLIMIT = 30.0

#: So oft wird ein Start versucht, bevor aufgegeben wird.
#:
#: `_freien_port_finden()` bindet Port 0, liest die vergebene Nummer und
#: gibt sie wieder frei – erst danach bindet `debugpy` sie. In dieser
#: Lücke kann ein anderer Prozess dieselbe Nummer bekommen; dann verbindet
#: sich Natter entweder gar nicht oder mit dem Falschen, und der
#: Handshake geht schief. Das ist selten, aber real: in langen
#: Testläufen, in denen viele `debugpy`-Prozesse kurz hintereinander
#: starten, fiel mehrfach genau einer der DAP-Tests aus und lief einzeln
#: sofort wieder durch. Ein zweiter Versuch mit einer neuen Nummer kostet
#: nichts und nimmt dem Zufall die Gelegenheit.
_STARTVERSUCHE = 3


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
        self._breakpoints: dict[str, list[int]] = {}

    def starten(
        self,
        skriptpfad: Path,
        *,
        arbeitsordner: Path,
        anfangs_breakpoints: dict[Path, list[int]] | None = None,
        zeitlimit: float = _STANDARD_ZEITLIMIT,
    ) -> None:
        """Startet `skriptpfad` als eigenen Prozess unter `debugpy`
        (`--listen`/`--wait-for-client`), verbindet sich und führt den
        `initialize`/`attach`-Handshake durch. `anfangs_breakpoints`
        (Datei → Zeilennummern) wird noch während der Konfigurations-
        phase gesetzt, damit ein Breakpoint auf der allerersten
        ausgeführten Zeile nicht verpasst wird. Nach Rückkehr ist die
        Sitzung konfiguriert (`configurationDone` bereits gesendet) und
        der Debuggee läuft (bzw. steht bereits an einem Breakpoint)."""
        letzter_fehler: Exception | None = None
        for _ in range(_STARTVERSUCHE):
            port = _freien_port_finden()
            self.prozess = subprocess.Popen(
                [
                    *python_befehl(),
                    "-m",
                    "debugpy",
                    "--listen",
                    str(port),
                    "--wait-for-client",
                    str(skriptpfad),
                ],
                cwd=arbeitsordner,
            )
            try:
                self._socket = self._verbinden(port, zeitlimit)
                self._socket.settimeout(zeitlimit)
                self._handshake(anfangs_breakpoints or {})
                return
            except (DapFehler, OSError) as fehler:
                letzter_fehler = fehler
                self._fehlstart_aufraeumen()
        raise DapFehler(
            f"Der Debugger ließ sich nach {_STARTVERSUCHE} Versuchen nicht starten: "
            f"{letzter_fehler}"
        ) from letzter_fehler

    def _fehlstart_aufraeumen(self) -> None:
        """Räumt einen missglückten Startversuch weg, damit der nächste
        auf einem sauberen Zustand aufsetzt – und vor allem, damit kein
        `debugpy`-Prozess zurückbleibt, der weiter auf einen Debugger
        wartet, der nie kommt."""
        if self._socket is not None:
            self._socket.close()
            self._socket = None
        if self.prozess is not None and self.prozess.poll() is None:
            self.prozess.kill()
        self.prozess = None
        self._puffer = b""
        self._naechste_seq = 1
        self._aufgehobene_antworten.clear()
        self.ereignisse.clear()

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

    def _handshake(self, anfangs_breakpoints: dict[Path, list[int]]) -> None:
        self.anfrage(
            "initialize",
            {"adapterID": "natter", "linesStartAt1": True, "columnsStartAt1": True},
        )
        attach_seq = self._senden("attach", {"justMyCode": False})
        self._ereignis_abwarten("initialized")

        for pfad, zeilen in anfangs_breakpoints.items():
            self.breakpoints_setzen(pfad, zeilen)
        # unbehandelte Ausnahmen halten immer an (Abschnitt 8.1), auch
        # innerhalb von Ereignis-Handlern
        self.anfrage("setExceptionBreakpoints", {"filters": ["uncaught"]})

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

    def _naechste_nachricht(self, *, nachsichtig: bool = False) -> dict[str, Any] | None:
        """Liest eine vollständige DAP-Nachricht. Bei `nachsichtig=True`
        liefert eine Zeitüberschreitung `None` statt `DapFehler` auszulösen
        – genutzt von `naechstes_ereignis_abfragen()` für kurze,
        nicht-blockierende Abfragen (Abschnitt 8.1: DAP-Client darf die
        GUI nicht einfrieren)."""
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
            if nachsichtig:
                return None
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

    def naechstes_ereignis_abfragen(self, zeitlimit: float) -> dict[str, Any] | None:
        """Nicht-blockierend (bis zu `zeitlimit` Sekunden): liefert das
        nächste Event (volles DAP-Objekt, u. a. `event`/`body`) oder
        `None`, wenn nichts ankam. Erst bereits gesammelte Events aus
        `self.ereignisse` (FIFO), erst danach neue vom Socket – für die
        Warteschlangen-Verarbeitung in `DebugSitzung` (Abschnitt 8.1):
        die GUI darf nicht einfrieren, während das Schülerprogramm frei
        läuft."""
        if self.ereignisse:
            return self.ereignisse.pop(0)

        assert self._socket is not None
        urspruengliches_zeitlimit = self._socket.gettimeout()
        self._socket.settimeout(zeitlimit)
        try:
            nachricht = self._naechste_nachricht(nachsichtig=True)
        finally:
            self._socket.settimeout(urspruengliches_zeitlimit)

        if nachricht is None:
            return None
        if nachricht.get("type") == "event":
            return nachricht
        if nachricht.get("type") == "response":
            seq = nachricht.get("request_seq")
            if seq is not None:
                self._aufgehobene_antworten[seq] = nachricht
        return None

    def beenden(self, zeitlimit: float = _STANDARD_ZEITLIMIT) -> None:
        """Schließt die Verbindung und wartet auf das Prozessende."""
        if self._socket is not None:
            self._socket.close()
            self._socket = None
        if self.prozess is not None:
            self.prozess.wait(timeout=zeitlimit)

    # -- Breakpoints und Ausführungssteuerung (Abschnitt 8.1) ---------------

    def breakpoints_setzen(self, pfad: Path, zeilen: list[int]) -> list[dict[str, Any]]:
        """Ersetzt die Breakpoints für `pfad` durch `zeilen` (DAP-Standard:
        `setBreakpoints` ersetzt immer die vollständige Menge für eine
        Datei). Jederzeit nach `starten()` aufrufbar, nicht nur während der
        Konfigurationsphase."""
        self._breakpoints[str(pfad)] = list(zeilen)
        body = self.anfrage(
            "setBreakpoints",
            {"source": {"path": str(pfad)}, "breakpoints": [{"line": z} for z in zeilen]},
        )
        return body.get("breakpoints", [])

    def angehalten_abwarten(self) -> dict[str, Any]:
        """Wartet auf das Event `stopped` (Breakpoint, Schritt oder
        unbehandelte Ausnahme) und liefert dessen Inhalt, u. a. `threadId`
        und `reason` (`"breakpoint"`/`"step"`/`"exception"`)."""
        return self._ereignis_abwarten("stopped")

    def thread_id_abwarten(self) -> int:
        """Wartet auf das Event `thread` (`reason: "started"`) und liefert
        dessen `threadId` – nötig, um ein frei laufendes (noch nicht an
        einem Breakpoint angehaltenes) Programm gezielt zu pausieren."""
        return self._ereignis_abwarten("thread")["threadId"]

    def fortsetzen(self, thread_id: int) -> None:
        self.anfrage("continue", {"threadId": thread_id})

    def pausieren(self, thread_id: int) -> None:
        self.anfrage("pause", {"threadId": thread_id})

    def einzelschritt(self, thread_id: int) -> None:
        """Steigt in einen Funktionsaufruf hinein, öffnet dabei bei Bedarf
        automatisch eine andere Unit (DAP: `stepIn`, F11, Abschnitt 7.9:
        „Einzelschritt in eine andere Unit öffnet diese automatisch“)."""
        self.anfrage("stepIn", {"threadId": thread_id})

    def prozedurschritt(self, thread_id: int) -> None:
        """Ein Schritt innerhalb derselben Funktion, überspringt
        Funktionsaufrufe ohne hineinzusteigen (DAP: `next`, F10)."""
        self.anfrage("next", {"threadId": thread_id})

    def bis_ruecksprung(self, thread_id: int) -> None:
        """Läuft bis zum Ende der aktuellen Funktion (DAP: `stepOut`)."""
        self.anfrage("stepOut", {"threadId": thread_id})

    def bis_cursor_ausfuehren(self, pfad: Path, zeile: int, thread_id: int) -> dict[str, Any]:
        """„Ausführen bis Cursor“ (Abschnitt 8.1): kein eigener DAP-Request
        (Standard kennt nur echte Breakpoints) – setzt vorübergehend einen
        zusätzlichen Breakpoint bei `zeile`, läuft weiter, entfernt ihn nach
        dem Anhalten wieder, ohne die übrigen Breakpoints der Datei zu
        verändern."""
        vorherige = list(self._breakpoints.get(str(pfad), []))
        self.breakpoints_setzen(pfad, sorted(set(vorherige) | {zeile}))
        self.fortsetzen(thread_id)
        ereignis = self.angehalten_abwarten()
        self.breakpoints_setzen(pfad, vorherige)
        return ereignis

    # -- Variablen und Aufrufstapel (Abschnitt 8.1) --------------------------

    def aufrufstapel_lesen(self, thread_id: int) -> list[dict[str, Any]]:
        """DAP `stackTrace`, gefiltert auf eigenen Code (Abschnitt 8.1:
        „nur mit eigenem Code“) – Frames aus `pcl`/Qt/der
        Standardbibliothek werden ausgeblendet."""
        body = self.anfrage("stackTrace", {"threadId": thread_id})
        return [
            frame
            for frame in body.get("stackFrames", [])
            if ist_eigener_code(frame.get("source", {}).get("path", ""))
        ]

    def bereiche_lesen(self, frame_id: int) -> list[dict[str, Any]]:
        """DAP `scopes` für einen Frame aus `aufrufstapel_lesen()`, z. B.
        „Locals“/„Globals“ mit je einer `variablesReference`."""
        return self.anfrage("scopes", {"frameId": frame_id}).get("scopes", [])

    def variablen_lesen(self, variablen_referenz: int) -> list[dict[str, Any]]:
        """DAP `variables` für einen Bereich oder ein aufklappbares Objekt
        (`variablesReference` aus `bereiche_lesen()` oder einer anderen
        Variable). Ungefiltert – für `pcl`-Komponentenobjekte siehe
        `komponenten_variablen_lesen()`."""
        return self.anfrage("variables", {"variablesReference": variablen_referenz}).get(
            "variables", []
        )

    def komponenten_variablen_lesen(self, variablen_referenz: int) -> list[dict[str, Any]]:
        """Wie `variablen_lesen()`, aber auf die bekannten `Prop`-/
        `Event`-Namen aller `pcl`-Komponententypen gefiltert (Abschnitt
        8.1: „nur relevante Eigenschaften wie `text`, `caption`,
        `checked`, `item_index`“), siehe `komponenten_variablen.py`."""
        from ide.debugger.komponenten_variablen import komponenten_variablen_filtern

        return komponenten_variablen_filtern(self.variablen_lesen(variablen_referenz))

    def auswerten(self, ausdruck: str, frame_id: int) -> dict[str, Any]:
        """Überwachter Ausdruck (DAP `evaluate`, `context: "watch"`,
        Abschnitt 8.1): liefert u. a. `result` (Text) und `type`."""
        return self.anfrage(
            "evaluate", {"expression": ausdruck, "frameId": frame_id, "context": "watch"}
        )

    def exceptioninfo_lesen(self, thread_id: int) -> dict[str, Any]:
        """Details zur unbehandelten Ausnahme, die `thread_id` gerade
        angehalten hat (DAP `exceptionInfo`) – u. a. `exceptionId`,
        `description`, `details.message`/`stackTrace`. Grundlage für
        `pcl.fehlerkatalog.fehlermeldung_aus_dap_erzeugen()`."""
        return self.anfrage("exceptionInfo", {"threadId": thread_id})
