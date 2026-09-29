r"""Erkennt, dass ein Projekt schon in einem anderen Natter-Fenster
offen ist (Punkt 286), auch an einem anderen Rechner (Punkt 322).

Ein Doppelklick auf die `.natter` im Explorer startet ein weiteres
Natter, auch wenn das Projekt schon offen ist. Beide Fenster schreiben
dann in dieselben Dateien. Natter legt deshalb beim Öffnen eine
Sperrdatei `.natter-sperre` in den Projektordner und entfernt sie beim
Schließen. Sie sieht so aus:

    4712 133900000000000000
    rechner=PC-R12
    konto=mueller.anna
    erneuert=1790000000
    ordner=\\server\tausch\Aufgabe3

Die erste Zeile tragen Prozessnummer und Startzeit des eigenen
Prozesses; eine Sperrdatei aus Natter 0.3.x besteht nur aus ihr und
wird weiter gelesen. Nach einem Absturz oder Stromausfall bleibt die
Datei liegen. Stammt sie von diesem Rechner, zählt sie nur, solange
der eingetragene Prozess noch läuft. Die Startzeit steht dabei, weil
Windows eine Prozessnummer nach einem Neustart wieder vergibt: ein
fremder Prozess mit derselben Nummer hat eine andere Startzeit.

Liegt das Projekt in einem Tauschordner, öffnen oft mehrere
Schülerinnen an verschiedenen Rechnern dasselbe Projekt. Ob ein
Prozess an einem anderen Rechner läuft, lässt sich von hier aus nicht
nachsehen. Dafür steht die Zeit der letzten Erneuerung in der Datei:
das haltende Natter schreibt sie alle `ERNEUERN_MS` neu
(`erneuern()`), und eine Sperre eines anderen Rechners, deren Zeit
älter als `ZEITGRENZE` ist, zählt nicht mehr.

In `ordner` steht, für welchen Projektordner die Sperre gilt (Punkt
327). Wird ein Projekt samt Sperrdatei kopiert, etwa im
Windows-Explorer aus dem Tauschordner nach „Dokumente“, passt die
Angabe nicht zum Ordner der Kopie, und die Sperre zählt dort nicht.
Eine Sperrdatei ohne diese Zeile, geschrieben vor Natter 0.4.0, gilt
wie bisher. Sieht ein anderer Rechner denselben Tauschordner unter
einem anderen Pfad, bleibt der Hinweis aus; aufgehen würde das
Projekt dort ohnehin.

Die Sperre verbietet nichts. Sie führt nur zu einem Hinweis, und das
Projekt geht trotzdem auf. Ein schreibgeschützter Projektordner
bekommt keine Sperrdatei.
"""

from __future__ import annotations

import contextlib
import getpass
import os
import platform
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from ide.pfade import einheitlicher_pfad

SPERRDATEI = ".natter-sperre"

#: Wie oft das haltende Natter die Zeit in seiner Sperrdatei erneuert.
ERNEUERN_MS = 5 * 60 * 1000

#: Nach so vielen Sekunden ohne Erneuerung zählt die Sperre eines
#: anderen Rechners nicht mehr. Sechs verpasste Erneuerungen: ein
#: kurz hängender Netzordner hebt die Sperre damit nicht auf.
ZEITGRENZE = 30 * 60


@dataclass(frozen=True)
class Besitzer:
    """Wer das Projekt laut Sperrdatei offen hält."""

    pid: int
    #: Leer bei einer Sperrdatei aus Natter 0.3.x.
    rechner: str = ""
    konto: str = ""
    #: `True`, wenn die Sperre von einem anderen Rechner stammt.
    anderer_rechner: bool = False


def rechnername() -> str:
    return os.environ.get("COMPUTERNAME") or platform.node()


def kontoname() -> str:
    try:
        return getpass.getuser()
    except (OSError, KeyError):
        return ""


def _startzeit(pid: int) -> int | None:
    """Die Startzeit des Prozesses `pid` in Windows-Zeiteinheiten, oder
    `None`, wenn er nicht (mehr) läuft. Außerhalb von Windows 0 für
    einen laufenden Prozess."""
    if sys.platform != "win32":
        try:
            os.kill(pid, 0)
        except PermissionError:
            return 0
        except OSError:
            return None
        return 0
    import ctypes
    from ctypes import wintypes

    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k.OpenProcess.restype = wintypes.HANDLE
    k.GetExitCodeProcess.argtypes = [
        wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)
    ]
    k.GetProcessTimes.argtypes = [wintypes.HANDLE] + [
        ctypes.POINTER(wintypes.FILETIME)
    ] * 4
    k.CloseHandle.argtypes = [wintypes.HANDLE]
    # PROCESS_QUERY_LIMITED_INFORMATION
    griff = k.OpenProcess(0x1000, False, pid)
    if not griff:
        return None
    try:
        code = wintypes.DWORD()
        if not k.GetExitCodeProcess(griff, ctypes.byref(code)):
            return None
        if code.value != 259:  # STILL_ACTIVE
            return None
        zeiten = [wintypes.FILETIME() for _ in range(4)]
        if not k.GetProcessTimes(griff, *map(ctypes.byref, zeiten)):
            return None
        start = zeiten[0]
        return (start.dwHighDateTime << 32) | start.dwLowDateTime
    finally:
        k.CloseHandle(griff)


def _ordnerangabe(ordner: Path) -> str:
    """Der Projektordner, wie er in der Sperrdatei steht: als Netzpfad
    auch dann, wenn er über ein verbundenes Laufwerk geöffnet wurde
    (`einheitlicher_pfad`)."""
    return str(einheitlicher_pfad(ordner))


def _eintrag(ordner: Path) -> str:
    pid = os.getpid()
    return (
        f"{pid} {_startzeit(pid) or 0}\n"
        f"rechner={rechnername()}\n"
        f"konto={kontoname()}\n"
        f"erneuert={int(time.time())}\n"
        f"ordner={_ordnerangabe(ordner)}\n"
    )


def _lesen(ordner: Path) -> tuple[int, int, dict[str, str]] | None:
    """Prozessnummer, Startzeit und die übrigen Angaben der
    Sperrdatei, oder `None`, wenn es keine lesbare gibt."""
    try:
        zeilen = (Path(ordner) / SPERRDATEI).read_text(
            encoding="utf-8"
        ).splitlines()
        teile = zeilen[0].split()
        pid, start = int(teile[0]), int(teile[1])
    except (OSError, ValueError, IndexError):
        return None
    angaben: dict[str, str] = {}
    for zeile in zeilen[1:]:
        schluessel, gleich, wert = zeile.partition("=")
        if gleich:
            angaben[schluessel.strip()] = wert.strip()
    return pid, start, angaben


def _von_hier(angaben: dict[str, str]) -> bool:
    """Ob die Sperre von diesem Rechner stammt. Eine alte Sperrdatei
    ohne Rechnernamen gilt als hiesige, so wie bisher."""
    rechner = angaben.get("rechner", "")
    return not rechner or rechner.casefold() == rechnername().casefold()


def _anderer_ordner(ordner: Path, angaben: dict[str, str]) -> bool:
    """Ob die Sperrdatei aus einem anderen Ordner hierher kopiert
    wurde. Eine Sperrdatei ohne Ordnerangabe gehört hierher."""
    gespeichert = angaben.get("ordner", "")
    if not gespeichert:
        return False
    return os.path.normcase(gespeichert) != os.path.normcase(
        _ordnerangabe(ordner)
    )


def anderer_besitzer(
    ordner: Path, jetzt: float | None = None
) -> Besitzer | None:
    """Wer das Projekt in `ordner` außer diesem Natter offen hält, oder
    `None`."""
    gelesen = _lesen(ordner)
    if gelesen is None:
        return None
    pid, start, angaben = gelesen
    if _anderer_ordner(ordner, angaben):
        return None
    rechner = angaben.get("rechner", "")
    konto = angaben.get("konto", "")
    if not _von_hier(angaben):
        try:
            erneuert = int(angaben.get("erneuert", ""))
        except ValueError:
            return None
        jetzt = time.time() if jetzt is None else jetzt
        if jetzt - erneuert > ZEITGRENZE:
            return None
        return Besitzer(pid, rechner, konto, anderer_rechner=True)
    if pid == os.getpid():
        return None
    laufend = _startzeit(pid)
    if laufend is None or (start and laufend and laufend != start):
        return None
    return Besitzer(pid, rechner, konto)


def anderer_prozess(ordner: Path) -> int | None:
    """Die Prozessnummer des anderen Natter, in dem das Projekt in
    `ordner` offen ist, oder `None`."""
    besitzer = anderer_besitzer(ordner)
    return None if besitzer is None else besitzer.pid


def _gehoert_mir(ordner: Path) -> bool:
    gelesen = _lesen(ordner)
    return (
        gelesen is not None
        and gelesen[0] == os.getpid()
        and _von_hier(gelesen[2])
        and not _anderer_ordner(ordner, gelesen[2])
    )


def sperren(ordner: Path) -> None:
    """Trägt den eigenen Prozess als Besitzer des Projekts ein."""
    with contextlib.suppress(OSError):
        (Path(ordner) / SPERRDATEI).write_text(
            _eintrag(ordner), encoding="utf-8"
        )


def erneuern(ordner: Path) -> None:
    """Schreibt die Zeit in der eigenen Sperrdatei neu. Eine fremde oder
    fehlende Sperrdatei bleibt, wie sie ist."""
    if _gehoert_mir(ordner):
        sperren(ordner)


def freigeben(ordner: Path) -> None:
    """Entfernt die Sperrdatei, wenn sie vom eigenen Prozess stammt.
    Die eines anderen Fensters oder Rechners bleibt liegen, auch wenn
    dort zufällig dieselbe Prozessnummer eingetragen ist."""
    if _gehoert_mir(ordner):
        with contextlib.suppress(OSError):
            (Path(ordner) / SPERRDATEI).unlink()
