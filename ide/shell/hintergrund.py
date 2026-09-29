"""Arbeit, die nebenher läuft, ohne die Oberfläche anzuhalten.

Ein Exe-Export dauert eine halbe bis eine Minute, ein Testlauf einige
Sekunden, eine Paketinstallation je nach Netz auch Minuten. Bis hierher
liefen sie alle im Faden der Oberfläche: das Fenster nahm keine Klicks
mehr an, der Editor reagierte nicht, und Windows legte nach ein paar
Sekunden „Keine Rückmeldung" über den Titel. Ein Ladebalken, der sich
über `processEvents()` noch bewegt, ändert daran nichts – bedienen
lässt sich das Programm trotzdem nicht.

Zwei Klassen genügen dafür:

`Hintergrundarbeit` führt eine Funktion in einem eigenen Faden aus und
meldet Fortschritt, Ergebnis und Fehler über Signale. Die Funktion
bekommt einen Melder übergeben, den sie so oft aufrufen darf, wie sie
möchte – der Melder schickt ein Signal, und erst Qt stellt es in den
Faden der Oberfläche zu. Direkt aus einem Nebenfaden an Widgets zu
schreiben, endet sonst irgendwann in einem Absturz, der sich nicht
nachstellen lässt.

`AusgabeLeser` liest die Ausgabe eines gestarteten Programms, teilt
sie in Zeilen und hebt sie auf, bis die Oberfläche sie abholt. Er ist die
Bedingung dafür, dass ein GUI-Programm ohne Konsolenfenster laufen
kann: ohne Fenster muss die Ausgabe in ein Rohr, und ein Rohr, aus dem
niemand liest, läuft voll und hält das Programm an, sobald es genug
geschrieben hat.
"""

from __future__ import annotations

import codecs
import re
import subprocess
import threading
from collections import deque
from collections.abc import Callable, Iterator
from typing import IO, Any

from PySide6.QtCore import QObject, QThread, Signal

from ide.prozess import prozessbaum_beenden

#: Länger wird keine Zeile, die `AusgabeLeser` abgibt. Was ohne
#: Zeilenende weiterläuft, geht nach so vielen Zeichen als eigene
#: Zeile ab (Punkt 275). Bis 0.3.6 las der Leser zeilenweise ohne
#: Grenze: `print(i, end=" ")` in einer Schleife sammelte sich
#: unsichtbar im Speicher und kam erst beim Programmende als eine
#: einzige Zeile mit Millionen Zeichen an, deren Anzeige Natter
#: sekundenlang anhielt.
ZEILEN_GRENZE = 2000

#: So viel liest der Leser höchstens auf einmal aus dem Rohr.
_STUECK = 8192

_ZEILENENDE = re.compile(r"\r\n|\r|\n")


class Hintergrundarbeit(QThread):
    """Führt `arbeit` in einem eigenen Faden aus.

    `arbeit` bekommt einen Melder `(prozent, text)` übergeben und gibt
    ein beliebiges Ergebnis zurück::

        def bauen(melden):
            melden(10, "geht los")
            return exe_exportieren(projekt, fortschritt=melden)

        lauf = Hintergrundarbeit(bauen, self)
        lauf.fertig.connect(self._export_fertig)
        lauf.start()

    Eine Ausnahme in `arbeit` beendet nicht das Programm, sondern kommt
    als `fehlgeschlagen` zurück: ein Fehler beim Export ist ein Fall für
    die Statuszeile, nicht für einen Absturz der IDE.
    """

    fortschritt = Signal(int, str)
    fertig = Signal(object)
    fehlgeschlagen = Signal(str)
    #: Trägt eine Aufgabe ohne Argumente, die im Faden der Oberfläche
    #: laufen soll (`im_vordergrund`).
    vordergrund = Signal(object)

    def __init__(
        self,
        arbeit: Callable[[Callable[[int, str], None]], Any],
        eltern: QObject | None = None,
    ) -> None:
        super().__init__(eltern)
        self._arbeit = arbeit
        # Prozesse, die `arbeit` gestartet und hier gemeldet hat. Sie
        # sind lokale Variablen im Nebenfaden; ohne diese Liste käme
        # beim Schließen des Fensters niemand an sie heran (Punkt 254).
        self._prozesse: list[subprocess.Popen] = []
        self._sperre = threading.Lock()
        self._abgebrochen = False
        # Wer in `im_vordergrund` auf die Oberfläche wartet. `abbrechen`
        # gibt alle frei, damit der Faden zu Ende kommt.
        self._wartende: list[threading.Event] = []

    @property
    def abgebrochen(self) -> bool:
        """Ob `abbrechen()` schon gerufen wurde."""
        return self._abgebrochen

    def prozess_melden(self, prozess: subprocess.Popen) -> None:
        """Meldet einen Prozess an, den `arbeit` gestartet hat.

        Darf aus dem Nebenfaden gerufen werden. Kommt die Meldung erst
        nach `abbrechen()` an, endet der Prozess sofort - sonst liefe
        er an der Stelle vorbei, an der das Abbrechen schon vorüber
        ist.
        """
        with self._sperre:
            if not self._abgebrochen:
                self._prozesse.append(prozess)
                return
        prozessbaum_beenden(prozess)

    def abbrechen(self) -> None:
        """Beendet alle gemeldeten Prozesse samt ihren Kindern.

        Der Faden selbst läuft danach noch bis zum Ende von `arbeit`;
        die wartet in aller Regel nur auf diese Prozesse und kehrt
        zurück, sobald sie weg sind. Wer das Fenster schließt, wartet
        danach mit `wait()` auf das Ende.
        """
        with self._sperre:
            self._abgebrochen = True
            prozesse = list(self._prozesse)
            self._prozesse.clear()
            for wartend in self._wartende:
                wartend.set()
        for prozess in prozesse:
            prozessbaum_beenden(prozess)

    def im_vordergrund(
        self, aufgabe: Callable[[], None], geduld: float
    ) -> None:
        """Lässt `aufgabe` im Faden der Oberfläche laufen und wartet
        darauf, höchstens `geduld` Sekunden lang.

        Aus dem Nebenfaden zu rufen, etwa für ein Fenster, das vor dem
        nächsten Schritt gelesen sein soll (Punkt 350). Gewartet wird
        über ein `threading.Event` und nicht über eine blockierende
        Signalverbindung: schließt jemand Natter, während das Fenster
        noch aussteht, wartet der Faden der Oberfläche in
        `_hintergrund_abbrechen` auf diesen Faden, und beide stünden
        füreinander still. `abbrechen()` gibt das Warten frei; danach
        kehrt der Aufruf sofort zurück.
        """
        erledigt = threading.Event()
        with self._sperre:
            if self._abgebrochen:
                return
            self._wartende.append(erledigt)

        def ausfuehren() -> None:
            try:
                aufgabe()
            finally:
                erledigt.set()

        self.vordergrund.emit(ausfuehren)
        erledigt.wait(geduld)
        with self._sperre:
            self._wartende.remove(erledigt)

    def run(self) -> None:
        try:
            ergebnis = self._arbeit(self._melden)
        except Exception as fehler:  # noqa: BLE001 - siehe Klassendoku
            self.fehlgeschlagen.emit(f"{type(fehler).__name__}: {fehler}")
            return
        self.fertig.emit(ergebnis)

    def _melden(self, prozent: int, text: str) -> None:
        self.fortschritt.emit(int(prozent), str(text))


class AusgabeLeser:
    """Liest die Ausgabe eines laufenden Programms Zeile für Zeile.

    Gedacht für ein GUI-Projekt, das ohne eigenes Konsolenfenster läuft:
    was es mit `print()` schreibt und was an Fehlermeldungen anfällt,
    erscheint im Panel „Ausgabe“ statt in einem Fenster, das gar nicht
    aufgehen soll.

    Die Zeilen landen in einem Zwischenspeicher, den die Oberfläche in
    ihrem eigenen Takt mit `abholen()` leert (Punkt 267). Bis 0.3.6
    ging jede Zeile als eigenes Signal an die Oberfläche; eine Schleife
    mit ein paar tausend `print()` legte so Tausende Aufrufe in ihre
    Warteschlange, und Natter kam minutenlang zu nichts anderem. Der
    Zwischenspeicher behält höchstens `grenze` Zeilen; was darüber
    hinaus ankommt, verdrängt die ältesten und wird mitgezählt. Keine
    Zeile ist länger als `ZEILEN_GRENZE` Zeichen: eine längere, auch
    eine ohne Zeilenende, geht in Stücken dieser Länge ab (Punkt 275).
    So bleibt auch eine Endlosschleife mit `print()` im Speicher
    begrenzt, und das Programm wartet nie auf die Oberfläche.

    Der Faden endet von selbst, wenn das Programm sein Rohr schließt.
    Das Rohr schließt aber erst, wenn jeder Prozess, der es geerbt hat,
    zu Ende ist - auch einer, den das Programm mit `os.system` oder
    `subprocess` gestartet hat und der sein Programm überlebt
    (Punkt 278). Solange so ein Prozess läuft, liest der Leser weiter.
    Deshalb ist er ein Daemon-Faden aus `threading` und kein `QThread`:
    ein `QThread`, dessen Objekt verschwindet, während er noch läuft,
    beendet Natter mit „QThread: Destroyed while thread is still
    running“. Ein Daemon-Faden hält weder das Schließen des Fensters
    noch das Ende von Natter auf.
    """

    def __init__(
        self,
        prozess: subprocess.Popen,
        grenze: int = 5000,
    ) -> None:
        self._prozess = prozess
        self._sperre = threading.Lock()
        self._zeilen: deque[str] = deque(maxlen=grenze)
        self._verdraengt = 0
        self._faden: threading.Thread | None = None

    def start(self) -> None:
        """Beginnt das Lesen in einem eigenen Faden."""
        self._faden = threading.Thread(
            target=self.run, name="AusgabeLeser", daemon=True
        )
        self._faden.start()

    def laeuft(self) -> bool:
        """Ob der Faden gestartet ist und noch liest."""
        return self._faden is not None and self._faden.is_alive()

    def ist_fertig(self) -> bool:
        """Ob der Faden gestartet war und inzwischen zu Ende ist."""
        return self._faden is not None and not self._faden.is_alive()

    def wait(self, millisekunden: int) -> bool:
        """Wartet höchstens `millisekunden` auf das Ende des Fadens.
        Liefert, ob er zu Ende ist (oder nie lief)."""
        if self._faden is None:
            return True
        self._faden.join(millisekunden / 1000)
        return not self._faden.is_alive()

    def abholen(self) -> tuple[list[str], int]:
        """Die seit dem letzten Aufruf gelesenen Zeilen und wie viele
        davon schon wieder verdrängt wurden, bevor sie jemand abholte."""
        with self._sperre:
            zeilen = list(self._zeilen)
            self._zeilen.clear()
            verdraengt, self._verdraengt = self._verdraengt, 0
        return zeilen, verdraengt

    def run(self) -> None:
        strom = self._prozess.stdout
        if strom is None:
            return
        offen = ""
        try:
            for stueck in _stuecke(strom):
                teile = _ZEILENENDE.split(offen + stueck)
                offen = teile.pop()
                for zeile in teile:
                    self._zeile_abgeben(zeile)
                while len(offen) >= ZEILEN_GRENZE:
                    self._aufnehmen(offen[:ZEILEN_GRENZE])
                    offen = offen[ZEILEN_GRENZE:]
        except (ValueError, OSError):
            # Das Rohr wurde zugemacht, während wir daraus lasen - das
            # passiert beim Beenden über „Start -> Stopp" und ist kein
            # Fehler, über den jemand etwas erfahren müsste.
            pass
        self._zeile_abgeben(offen)

    def _zeile_abgeben(self, zeile: str) -> None:
        """Gibt eine vollständige Zeile ab, eine überlange in Stücken
        von höchstens `ZEILEN_GRENZE` Zeichen. Leere Zeilen fallen weg."""
        for anfang in range(0, len(zeile), ZEILEN_GRENZE):
            self._aufnehmen(zeile[anfang:anfang + ZEILEN_GRENZE])

    def _aufnehmen(self, zeile: str) -> None:
        with self._sperre:
            if len(self._zeilen) == self._zeilen.maxlen:
                self._verdraengt += 1
            self._zeilen.append(zeile)


def _stuecke(strom: IO[str]) -> Iterator[str]:
    """Liest `strom` in Stücken, sobald etwas ankommt.

    `for zeile in strom` wartet auf das Zeilenende, `strom.read(n)` auf
    `n` Zeichen; beides hielte Ausgabe ohne Zeilenende beliebig lange
    zurück. `read1` auf dem Byte-Puffer darunter liefert, was gerade im
    Rohr liegt, und wartet nur, solange dort gar nichts liegt. Ein
    Strom ohne solchen Puffer (etwa `io.StringIO`) wird in festen
    Stücken gelesen.
    """
    puffer = getattr(strom, "buffer", None)
    lesen = getattr(puffer, "read1", None)
    if lesen is None:
        while stueck := strom.read(_STUECK):
            yield stueck
        return
    kodierung = getattr(strom, "encoding", None) or "utf-8"
    decoder = codecs.getincrementaldecoder(kodierung)(errors="replace")
    while daten := lesen(_STUECK):
        if stueck := decoder.decode(daten):
            yield stueck
    if rest := decoder.decode(b"", final=True):
        yield rest
