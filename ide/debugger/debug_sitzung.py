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

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.client = DapClient()
        self._befehle: queue.Queue[tuple[str, tuple[Any, ...]]] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._laeuft = False
        self._letzter_exitcode = 0

    # -- von der GUI aufgerufen ---------------------------------------------

    def starten(
        self,
        skriptpfad: Path,
        *,
        arbeitsordner: Path,
        anfangs_breakpoints: dict[Path, list[int]] | None = None,
    ) -> None:
        self._thread = threading.Thread(
            target=self._worker,
            args=(skriptpfad, arbeitsordner, anfangs_breakpoints),
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

    def breakpoints_setzen(self, pfad: Path, zeilen: list[int]) -> None:
        self._befehle.put(("breakpoints_setzen", (pfad, zeilen)))

    def aufrufstapel_lesen(self, thread_id: int) -> None:
        self._befehle.put(("_aufrufstapel_lesen", (thread_id,)))

    def bereiche_lesen(self, frame_id: int) -> None:
        self._befehle.put(("_bereiche_lesen", (frame_id,)))

    def variablen_lesen(self, variablen_referenz: int, *, nur_komponente: bool = False) -> None:
        self._befehle.put(("_variablen_lesen", (variablen_referenz, nur_komponente)))

    def auswerten(self, ausdruck: str, frame_id: int) -> None:
        self._befehle.put(("_auswerten", (ausdruck, frame_id)))

    def beenden(self) -> None:
        """Beendet die Sitzung sofort (z. B. „Stopp“ in der IDE) statt auf
        ein reguläres Programmende zu warten."""
        self._laeuft = False
        if self.client.prozess is not None and self.client.prozess.poll() is None:
            self.client.prozess.kill()

    # -- Worker-Thread --------------------------------------------------------

    def _worker(
        self,
        skriptpfad: Path,
        arbeitsordner: Path,
        anfangs_breakpoints: dict[Path, list[int]] | None,
    ) -> None:
        try:
            self.client.starten(
                skriptpfad, arbeitsordner=arbeitsordner, anfangs_breakpoints=anfangs_breakpoints
            )
        except DapFehler as fehler:
            self.fehler.emit(str(fehler))
            return

        self._laeuft = True
        while self._laeuft:
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

        if self._laeuft:
            self._laeuft = False
            self.beendet.emit(self._letzter_exitcode)

    def _ausstehende_befehle_abarbeiten(self) -> None:
        while True:
            try:
                name, argumente = self._befehle.get_nowait()
            except queue.Empty:
                return
            self._befehl_ausfuehren(name, argumente)

    def _befehl_ausfuehren(self, name: str, argumente: tuple[Any, ...]) -> None:
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
            else:
                getattr(self.client, name)(*argumente)
        except DapFehler as fehler:
            self.fehler.emit(str(fehler))

    def _ereignis_verarbeiten(self, ereignis: dict[str, Any]) -> None:
        name = ereignis.get("event")
        if name == "stopped":
            self.angehalten.emit(ereignis.get("body") or {})
        elif name == "continued":
            self.fortgesetzt.emit()
        elif name == "exited":
            self._letzter_exitcode = (ereignis.get("body") or {}).get("exitCode", 0)
        elif name == "terminated":
            self._laeuft = False
            self.beendet.emit(self._letzter_exitcode)
