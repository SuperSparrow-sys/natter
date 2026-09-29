"""DebugSitzung: Qt-Wrapper um `DapClient` (Abschnitt 8.1, 7.8).

`DapClient` blockiert bei jeder Anfrage und bei jedem Warten auf ein
Event – direkt im Qt-GUI-Thread aufgerufen würde das die IDE einfrieren,
sobald das Schülerprogramm frei läuft (z. B. bis zum nächsten
Breakpoint). `DebugSitzung` führt jede Interaktion mit `DapClient` auf
einem eigenen Thread aus: GUI-Methoden legen nur einen Befehl in eine
Warteschlange, der Worker-Thread arbeitet sie ab und meldet Ergebnisse
über Qt-Signale zurück. Qt marschalliert Signal-`emit()`-Aufrufe
automatisch sicher über Thread-Grenzen zum Thread, in dem der Empfänger
lebt (Queued Connection) – deshalb reicht ein einfacher `emit()` aus dem
Worker-Thread, ohne selbst zu sperren.
"""

from __future__ import annotations

import queue
import threading
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal

from ide.debugger.dap_client import DapClient, DapFehler

_ABFRAGE_INTERVALL = 0.05


class DebugSitzung(QObject):
    angehalten = Signal(dict)
    fortgesetzt = Signal()
    beendet = Signal(int)
    fehler = Signal(str)
    aufrufstapel_bereit = Signal(list)
    bereiche_bereit = Signal(list)
    variablen_bereit = Signal(list)
    ausgewertet = Signal(dict)
    exceptioninfo_bereit = Signal(dict)
    #: Kennung des Programmfadens, sobald debugpy ihn meldet. Damit
    #: lässt sich ein frei laufendes Programm anhalten, das noch nie an
    #: einem Haltepunkt stand (Punkt 56).
    faden_bekannt = Signal(int)
    #: Antwort auf eine Anfrage mit Zweck: (Zweck, Ergebnis). Das
    #: Hauptfenster erkennt daran, wofür die Antwort ist - die Kinder
    #: einer aufgeklappten Variable, die globalen Variablen, ein
    #: überwachter Ausdruck oder der Wert unter der Maus (Punkte 99,
    #: 100). Ein Fehler kommt als `{"fehler": Text}`.
    antwort = Signal(str, object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.client = DapClient()
        self._befehle: queue.Queue[tuple[str, tuple[Any, ...]]] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._laeuft = False
        self._letzter_exitcode = 0
        #: Nach „Ausführen bis Cursor“: Datei, Zeile und ob die Zeile
        #: vorher schon einen Haltepunkt hatte. Beim nächsten Halt wird
        #: der vorübergehende Haltepunkt wieder entfernt.
        self._voruebergehend: tuple[Path, int, bool] | None = None

    # -- von der GUI aufgerufen ---------------------------------------------

    def starten(
        self,
        skriptpfad: Path,
        *,
        arbeitsordner: Path,
        anfangs_breakpoints: dict[Path, list[int]] | None = None,
        halten_bei: tuple[Path, int] | None = None,
        konsole_titel: str | None = None,
        anfangs_bedingungen: dict[Path, dict[int, str]] | None = None,
    ) -> None:
        """`halten_bei` ist „Ausführen bis Cursor“ vor dem Start: ein
        Haltepunkt, der nach dem ersten Halt wieder verschwindet.
        `anfangs_bedingungen` sind die Bedingungen der Haltepunkte
        (Punkt 100)."""
        for pfad, bedingungen in (anfangs_bedingungen or {}).items():
            self.client._bedingungen[str(pfad)] = dict(bedingungen)
        if halten_bei is not None:
            pfad, zeile = halten_bei
            anfangs_breakpoints = dict(anfangs_breakpoints or {})
            vorher = list(anfangs_breakpoints.get(pfad, []))
            anfangs_breakpoints[pfad] = sorted(set(vorher) | {zeile})
            self._voruebergehend = (pfad, zeile, zeile in vorher)
        self._thread = threading.Thread(
            target=self._worker,
            args=(skriptpfad, arbeitsordner, anfangs_breakpoints, konsole_titel),
            daemon=True,
        )
        self._thread.start()

    def fortsetzen(self, thread_id: int) -> None:
        self._befehle.put(("fortsetzen", (thread_id,)))

    def pausieren(self, thread_id: int) -> None:
        self._befehle.put(("pausieren", (thread_id,)))

    def einzelschritt(self, thread_id: int) -> None:
        self._befehle.put(("einzelschritt", (thread_id,)))

    def prozedurschritt(self, thread_id: int) -> None:
        self._befehle.put(("prozedurschritt", (thread_id,)))

    def bis_ruecksprung(self, thread_id: int) -> None:
        self._befehle.put(("bis_ruecksprung", (thread_id,)))

    def bis_cursor(self, pfad: Path, zeile: int, thread_id: int) -> None:
        """„Ausführen bis Cursor“ aus einem Halt heraus (Punkt 78).

        `DapClient.bis_cursor_ausfuehren` wartet blockierend auf den
        nächsten Halt; im Worker würde das jeden weiteren Befehl, auch
        „Stopp“, bis dahin aufhalten. Hier wird nur der vorübergehende
        Haltepunkt gesetzt und fortgesetzt, entfernt wird er beim
        nächsten Halt in `_ereignis_verarbeiten`."""
        self._befehle.put(("_bis_cursor", (pfad, zeile, thread_id)))

    def breakpoints_setzen(
        self, pfad: Path, zeilen: list[int], bedingungen: dict[int, str] | None = None
    ) -> None:
        self._befehle.put(("breakpoints_setzen", (pfad, zeilen, bedingungen)))

    def variablen_lesen_fuer(self, variablen_referenz: int, zweck: str) -> None:
        self._befehle.put(("_variablen_fuer", (variablen_referenz, zweck)))

    def auswerten_fuer(self, ausdruck: str, frame_id: int, zweck: str) -> None:
        self._befehle.put(("_auswerten_fuer", (ausdruck, frame_id, zweck)))

    def aufrufstapel_lesen(self, thread_id: int) -> None:
        self._befehle.put(("_aufrufstapel_lesen", (thread_id,)))

    def bereiche_lesen(self, frame_id: int) -> None:
        self._befehle.put(("_bereiche_lesen", (frame_id,)))

    def variablen_lesen(self, variablen_referenz: int, *, nur_komponente: bool = False) -> None:
        self._befehle.put(("_variablen_lesen", (variablen_referenz, nur_komponente)))

    def auswerten(self, ausdruck: str, frame_id: int) -> None:
        self._befehle.put(("_auswerten", (ausdruck, frame_id)))

    def exceptioninfo_lesen(self, thread_id: int) -> None:
        self._befehle.put(("_exceptioninfo_lesen", (thread_id,)))

    def beenden(self) -> None:
        """Beendet die Sitzung sofort (z. B. „Stopp“ in der IDE) statt auf
        ein reguläres Programmende zu warten.

        Auch während des Starts: dann bricht `DapClient.stoppen()` den
        Start im Hintergrundfaden ab, und der Faden endet, ohne die
        Sitzung noch einmal anlaufen zu lassen (Punkt 222). Ein
        gestoppter Lauf meldet weder `fehler` noch `beendet`: das
        Hauptfenster hat die Sitzung zu diesem Zeitpunkt schon
        verworfen."""
        self._laeuft = False
        self.client.stoppen()

    # -- Worker-Thread --------------------------------------------------------

    def _worker(
        self,
        skriptpfad: Path,
        arbeitsordner: Path,
        anfangs_breakpoints: dict[Path, list[int]] | None,
        konsole_titel: str | None = None,
    ) -> None:
        try:
            self.client.starten(
                skriptpfad,
                arbeitsordner=arbeitsordner,
                anfangs_breakpoints=anfangs_breakpoints,
                konsole_titel=konsole_titel,
            )
        except DapFehler as fehler:
            if not self.client.gestoppt:
                self.fehler.emit(str(fehler))
            return

        # Ein Stopp zwischen dem Ende von `starten()` und hier darf die
        # Sitzung nicht wieder in Gang setzen (Punkt 222).
        self._laeuft = not self.client.gestoppt
        while self._laeuft and not self.client.gestoppt:
            self._ausstehende_befehle_abarbeiten()
            if not self._laeuft:
                break
            try:
                ereignis = self.client.naechstes_ereignis_abfragen(_ABFRAGE_INTERVALL)
            except DapFehler:
                # Verbindung weg (z. B. nach einem harten Stopp/`kill()`) -
                # kein Protokollfehler, sondern das erwartete Ende der
                # Sitzung; "beendet" muss trotzdem zuverlässig feuern,
                # sonst bleibt die IDE im Glauben, es laufe noch etwas.
                break
            if ereignis is not None:
                self._ereignis_verarbeiten(ereignis)

        if self._laeuft and not self.client.gestoppt:
            self._laeuft = False
            self.beendet.emit(self._letzter_exitcode)

    def _ausstehende_befehle_abarbeiten(self) -> None:
        while not self.client.gestoppt:
            try:
                name, argumente = self._befehle.get_nowait()
            except queue.Empty:
                return
            self._befehl_ausfuehren(name, argumente)

    def _befehl_ausfuehren(self, name: str, argumente: tuple[Any, ...]) -> None:
        if name in ("_variablen_fuer", "_auswerten_fuer"):
            *eingabe, zweck = argumente
            try:
                if name == "_variablen_fuer":
                    ergebnis = self.client.variablen_lesen(*eingabe)
                else:
                    ergebnis = self.client.auswerten(*eingabe)
            except DapFehler as fehler:
                ergebnis = {"fehler": str(fehler)}
            self.antwort.emit(zweck, ergebnis)
            return
        try:
            if name == "_aufrufstapel_lesen":
                self.aufrufstapel_bereit.emit(self.client.aufrufstapel_lesen(*argumente))
            elif name == "_bereiche_lesen":
                self.bereiche_bereit.emit(self.client.bereiche_lesen(*argumente))
            elif name == "_variablen_lesen":
                variablen_referenz, nur_komponente = argumente
                if nur_komponente:
                    ergebnis = self.client.komponenten_variablen_lesen(variablen_referenz)
                else:
                    ergebnis = self.client.variablen_lesen(variablen_referenz)
                self.variablen_bereit.emit(ergebnis)
            elif name == "_auswerten":
                self.ausgewertet.emit(self.client.auswerten(*argumente))
            elif name == "_exceptioninfo_lesen":
                self.exceptioninfo_bereit.emit(self.client.exceptioninfo_lesen(*argumente))
            elif name == "_bis_cursor":
                pfad, zeile, thread_id = argumente
                vorher = self.client.gesetzte_breakpoints(pfad)
                self.client.breakpoints_setzen(pfad, sorted(set(vorher) | {zeile}))
                self._voruebergehend = (pfad, zeile, zeile in vorher)
                self.client.fortsetzen(thread_id)
            else:
                getattr(self.client, name)(*argumente)
        except DapFehler as fehler:
            # Nach einem Stopp scheitert eine noch laufende Anfrage an
            # der geschlossenen Leitung; das ist kein Fehler.
            if not self.client.gestoppt:
                self.fehler.emit(str(fehler))

    def _voruebergehenden_haltepunkt_entfernen(self) -> None:
        """Nimmt den Haltepunkt von „Ausführen bis Cursor“ wieder weg -
        aus dem aktuellen Stand der Datei, damit Haltepunkte, die
        inzwischen im Editor gesetzt wurden, erhalten bleiben."""
        if self._voruebergehend is None:
            return
        pfad, zeile, war_schon_da = self._voruebergehend
        self._voruebergehend = None
        if war_schon_da:
            return
        aktuell = self.client.gesetzte_breakpoints(pfad)
        try:
            self.client.breakpoints_setzen(pfad, [z for z in aktuell if z != zeile])
        except DapFehler as fehler:
            self.fehler.emit(str(fehler))

    def _ereignis_verarbeiten(self, ereignis: dict[str, Any]) -> None:
        name = ereignis.get("event")
        if name == "stopped":
            self._voruebergehenden_haltepunkt_entfernen()
            self.angehalten.emit(ereignis.get("body") or {})
        elif name == "thread":
            body = ereignis.get("body") or {}
            if body.get("reason") == "started" and body.get("threadId") is not None:
                self.faden_bekannt.emit(int(body["threadId"]))
        elif name == "continued":
            self.fortgesetzt.emit()
        elif name == "exited":
            self._letzter_exitcode = (ereignis.get("body") or {}).get("exitCode", 0)
        elif name == "terminated":
            self._laeuft = False
            self.beendet.emit(self._letzter_exitcode)
