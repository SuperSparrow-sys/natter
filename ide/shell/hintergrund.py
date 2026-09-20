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

`AusgabeLeser` liest die Ausgabe eines gestarteten Programms Zeile für
Zeile. Er ist die Bedingung dafür, dass ein GUI-Programm ohne
Konsolenfenster laufen kann: ohne Fenster muss die Ausgabe in ein Rohr,
und ein Rohr, aus dem niemand liest, läuft voll und hält das Programm
an, sobald es genug geschrieben hat.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QThread, Signal


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

    def __init__(
        self,
        arbeit: Callable[[Callable[[int, str], None]], Any],
        eltern: QObject | None = None,
    ) -> None:
        super().__init__(eltern)
        self._arbeit = arbeit

    def run(self) -> None:
        try:
            ergebnis = self._arbeit(self._melden)
        except Exception as fehler:  # noqa: BLE001 - siehe Klassendoku
            self.fehlgeschlagen.emit(f"{type(fehler).__name__}: {fehler}")
            return
        self.fertig.emit(ergebnis)

    def _melden(self, prozent: int, text: str) -> None:
        self.fortschritt.emit(int(prozent), str(text))


class AusgabeLeser(QThread):
    """Liest die Ausgabe eines laufenden Programms Zeile für Zeile.

    Gedacht für ein GUI-Projekt, das ohne eigenes Konsolenfenster läuft:
    was es mit `print()` schreibt und was an Fehlermeldungen anfällt,
    erscheint im Panel „Ausgabe“ statt in einem Fenster, das gar nicht
    aufgehen soll.

    Der Faden endet von selbst, wenn das Programm sein Rohr schließt.
    """

    zeile = Signal(str)

    def __init__(self, prozess: subprocess.Popen, eltern: QObject | None = None) -> None:
        super().__init__(eltern)
        self._prozess = prozess

    def run(self) -> None:
        strom = self._prozess.stdout
        if strom is None:
            return
        try:
            for text in strom:
                gestutzt = text.rstrip("\r\n")
                if gestutzt:
                    self.zeile.emit(gestutzt)
        except (ValueError, OSError):
            # Das Rohr wurde zugemacht, während wir daraus lasen - das
            # passiert beim Beenden über „Start -> Stopp" und ist kein
            # Fehler, über den jemand etwas erfahren müsste.
            return
