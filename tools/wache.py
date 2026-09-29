"""Wache für lange, unbeaufsichtigte Läufe (Befehl `/freigabe`).

    uv run python -m tools.wache [--still 10] [--aufraeumen]

Prüft einmal und gibt eine Zeile „WACHE ok“ oder „WACHE AUFFAELLIG“
aus, darunter die Einzelheiten. Der Rückgabewert ist 0 bei ok, 1 bei
Auffälligem. Gedacht ist der Aufruf alle zehn Minuten aus einer
Überwachung heraus.

Geprüft wird, was bei den Läufen im September 2026 tatsächlich
schiefging:

- Prozesse aus dem Repository, seinen Arbeitsbäumen oder den
  Probeordnern unter %TEMP%, deren Elternprozess nicht mehr lebt
  (verwaist), dazu Debugger, die auf eine Verbindung warten, die nie
  kommt, Warteschleifen in der Shell und Testläufe, die länger laufen,
  als ein Testlauf je dauern sollte. Einmal waren es über hundert
  solcher Prozesse, und der Speicher wurde knapp.
- Arbeitsbäume unter `.claude/worktrees`, in denen sich seit `--still`
  Minuten keine Datei mehr geändert hat, obwohl dort noch gearbeitet
  werden soll.
- Probeordner `natter_*` unter %TEMP%, die älter als zwei Stunden sind.
- Entpackordner `_MEI*` unter %TEMP%, die eine Natter.exe bis 0.3.6
  hinterlassen hat (Punkt 399).
- freier Arbeitsspeicher.

Mit `--aufraeumen` beendet die Wache verwaiste und hängende Prozesse
samt ihren Kindern und entfernt die Entpackordner alter Starter.
Arbeitsbäume und Probeordner löscht sie nie; die entfernt, wer den
Lauf steuert, wenn der zugehörige Helfer fertig ist.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent

#: Prozessnamen, die ein Lauf hinterlassen kann.
_NAMEN = ("python.exe", "pythonw.exe", "pytest.exe", "bash.exe", "powershell.exe")

#: Wie lange etwas höchstens laufen darf, bevor es als hängend gilt,
#: in Minuten.
GRENZE_DEBUGGER_WARTET = 5
GRENZE_WARTESCHLEIFE = 30
GRENZE_TESTLAUF = 60

#: Ab diesem freien Arbeitsspeicher in MB gilt der Rechner als knapp.
GRENZE_SPEICHER_MB = 2000

#: Ordner, die beim Suchen nach der letzten Änderung übergangen werden.
_UEBERGEHEN = {".venv", "__pycache__", ".git", "build", "dist", "node_modules"}


@dataclass
class Prozess:
    pid: int
    eltern: int
    name: str
    befehl: str
    minuten: float


@dataclass
class Befund:
    art: str
    text: str
    pid: int | None = None
    ordner: Path | None = None


@dataclass
class Bericht:
    befunde: list[Befund] = field(default_factory=list)
    hinweise: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.befunde


def _gehoert_zum_lauf(befehl: str) -> bool:
    befehl = befehl.lower()
    temp = os.environ.get("TEMP", "").lower()
    return (
        str(WURZEL).lower() in befehl
        or "\\natter_" in befehl
        or "/natter_" in befehl
        or (temp != "" and f"{temp}\\natter" in befehl)
    )


def prozesse_lesen() -> list[Prozess]:
    """Die laufenden Prozesse mit den Namen aus `_NAMEN`, über
    PowerShell gelesen (im Projekt gibt es keine Prozessbibliothek)."""
    namen = " or ".join(f"name='{n}'" for n in _NAMEN)
    befehl = (
        f"Get-CimInstance Win32_Process -Filter \"{namen}\" | "
        "Select-Object ProcessId, ParentProcessId, Name, CommandLine, "
        "@{n='Minuten';e={((Get-Date) - $_.CreationDate).TotalMinutes}} | "
        "ConvertTo-Json -Compress"
    )
    ergebnis = subprocess.run(
        ["powershell", "-NoProfile", "-Command", befehl],
        capture_output=True,
        text=True,
        timeout=60,
        encoding="utf-8",
        errors="replace",
    )
    roh = ergebnis.stdout.strip()
    if not roh:
        return []
    daten = json.loads(roh)
    if isinstance(daten, dict):
        daten = [daten]
    return [
        Prozess(
            pid=int(d["ProcessId"]),
            eltern=int(d["ParentProcessId"] or 0),
            name=str(d["Name"]),
            befehl=str(d.get("CommandLine") or ""),
            minuten=float(d.get("Minuten") or 0),
        )
        for d in daten
    ]


def lebende_pids() -> set[int]:
    ergebnis = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "(Get-Process).Id -join ','"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    return {int(x) for x in ergebnis.stdout.strip().split(",") if x.strip().isdigit()}


def prozesse_bewerten(
    prozesse: list[Prozess], lebend: set[int], eigene: set[int]
) -> list[Befund]:
    """Verwaiste und hängende Prozesse des Laufs.

    `eigene` sind die Wache selbst und ihre Vorfahren; sie zählen nie.
    """
    befunde: list[Befund] = []
    for p in prozesse:
        if p.pid in eigene or not _gehoert_zum_lauf(p.befehl):
            continue
        kurz = p.befehl if len(p.befehl) <= 140 else p.befehl[:140] + " …"
        if "debugpy" in p.befehl and "--wait-for-client" in p.befehl:
            if p.minuten > GRENZE_DEBUGGER_WARTET:
                befunde.append(Befund(
                    "hängend",
                    f"Debugger wartet seit {p.minuten:.0f} min: {kurz}",
                    p.pid,
                ))
                continue
        if p.name == "bash.exe" and "until " in p.befehl:
            if p.minuten > GRENZE_WARTESCHLEIFE:
                befunde.append(Befund(
                    "hängend",
                    f"Warteschleife seit {p.minuten:.0f} min: {kurz}",
                    p.pid,
                ))
                continue
        if "pytest" in p.befehl and p.minuten > GRENZE_TESTLAUF:
            befunde.append(Befund(
                "hängend",
                f"Testlauf seit {p.minuten:.0f} min: {kurz}",
                p.pid,
            ))
            continue
        if p.eltern and p.eltern not in lebend:
            befunde.append(Befund(
                "verwaist",
                f"{p.name} ohne Elternprozess seit {p.minuten:.0f} min: {kurz}",
                p.pid,
            ))
    return befunde


def letzte_aenderung(ordner: Path) -> float | None:
    """Zeitpunkt der jüngsten Änderung einer Datei im Ordner (ohne
    `.venv`, Zwischenstände und `.git`), als Epoche."""
    juengste: float | None = None
    for wurzel, unterordner, dateien in os.walk(ordner):
        unterordner[:] = [u for u in unterordner if u not in _UEBERGEHEN]
        for name in dateien:
            try:
                zeit = (Path(wurzel) / name).stat().st_mtime
            except OSError:
                continue
            if juengste is None or zeit > juengste:
                juengste = zeit
    return juengste


def arbeitsbaeume_bewerten(
    ordner: Path, still_minuten: float, jetzt: float | None = None
) -> tuple[list[Befund], list[str]]:
    jetzt = time.time() if jetzt is None else jetzt
    befunde: list[Befund] = []
    hinweise: list[str] = []
    if not ordner.is_dir():
        return befunde, hinweise
    for baum in sorted(p for p in ordner.iterdir() if p.is_dir()):
        zeit = letzte_aenderung(baum)
        if zeit is None:
            continue
        minuten = (jetzt - zeit) / 60
        hinweise.append(f"Arbeitsbaum {baum.name}: letzte Änderung vor {minuten:.0f} min")
        if minuten > still_minuten:
            befunde.append(Befund(
                "still",
                f"Arbeitsbaum {baum.name} seit {minuten:.0f} min unverändert",
            ))
    return befunde, hinweise


def probeordner_bewerten(temp: Path, jetzt: float | None = None) -> list[Befund]:
    jetzt = time.time() if jetzt is None else jetzt
    befunde: list[Befund] = []
    if not temp.is_dir():
        return befunde
    for ordner in temp.glob("natter_*"):
        try:
            minuten = (jetzt - ordner.stat().st_mtime) / 60
        except OSError:
            continue
        if ordner.is_dir() and minuten > 120:
            befunde.append(Befund(
                "liegen geblieben",
                f"Probeordner {ordner} seit {minuten:.0f} min unverändert",
            ))
    return befunde


# -- Entpackordner alter Starter (Punkt 399) ----------------------------
#
# Bis 0.3.6 war `Natter.exe` ein Einzeldatei-Starter, der sich bei
# jedem Start nach `%TEMP%\_MEI…` entpackte. Wurde er hart beendet,
# etwa von `--aufraeumen` mit `taskkill /F`, blieb der Ordner liegen;
# auf dem Entwicklungsrechner waren es 214 mit zusammen 3,85 GB. Seit
# Punkt 399 ist der Starter ein Ordner und entpackt nichts mehr. Eine
# ältere installierte Fassung tut es aber weiter.
#
# `_MEI*` legt jedes Programm an, das mit PyInstaller als einzelne
# Datei gebaut ist, auch jede Exe, die eine Schülerin mit „Als Exe
# exportieren“ baut. Die Ordner selbst tragen keinen Namen. Als
# Natters gilt deshalb nur ein Ordner, dessen Dateien nach Name und
# Größe genau dem entsprechen, was eine vorhandene `Natter.exe` beim
# Start entpackt; das Inhaltsverzeichnis dazu steht in der Exe.

#: Die Einträge im Archiv einer Einzeldatei-Exe, die PyInstaller beim
#: Start als Datei ablegt: Binärdateien, Daten und Zip-Archive.
_ENTPACKT = ("b", "x", "Z")

#: Jünger als so viele Minuten gilt ein Entpackordner als in Gebrauch.
GRENZE_ENTPACKT = 60


def starter_inhalt(exe: Path) -> dict[str, int] | None:
    """Was `exe` beim Start nach `%TEMP%\\_MEI…` entpackt, als Name
    und Größe, oder `None`, wenn sie nichts entpackt: sie ist keine
    Einzeldatei-Exe von PyInstaller, oder sie ist ein Ordner-Starter
    wie `Natter.exe` seit Punkt 399."""
    try:
        from PyInstaller.archive.readers import CArchiveReader

        inhalt = CArchiveReader(str(exe)).toc
    except Exception:
        return None
    entpackt = {
        name.replace("\\", "/"): int(eintrag[2])
        for name, eintrag in inhalt.items()
        if eintrag[-1] in _ENTPACKT
    }
    return entpackt or None


def natter_starter() -> list[Path]:
    """Die `Natter.exe`, deren Entpackordner die Wache erkennt: die der
    installierten Fassungen und die aus `dist\\Natter`."""
    orte = [WURZEL / "dist" / "Natter" / "Natter.exe"]
    for variable, unterordner in (
        ("LOCALAPPDATA", ("Programs", "Natter")),
        ("ProgramFiles", ("Natter",)),
    ):
        wurzel = os.environ.get(variable)
        if wurzel:
            orte.append(Path(wurzel).joinpath(*unterordner, "Natter.exe"))
    return [ort for ort in orte if ort.is_file()]


def _dateien(ordner: Path) -> dict[str, int]:
    return {
        pfad.relative_to(ordner).as_posix(): pfad.stat().st_size
        for pfad in ordner.rglob("*")
        if pfad.is_file()
    }


def entpackordner_bewerten(
    temp: Path,
    bekannt: list[dict[str, int]],
    jetzt: float | None = None,
) -> list[Befund]:
    """Die Ordner `_MEI*` in `temp`, deren Inhalt einem der Starter aus
    `bekannt` entspricht und die älter als `GRENZE_ENTPACKT` sind.

    Ob der Starter dazu noch läuft, sagt erst das Entfernen
    (`entpackordner_entfernen`); ein Natter, das seit dem Vormittag
    offen ist, hat einen ebenso alten Ordner."""
    jetzt = time.time() if jetzt is None else jetzt
    befunde: list[Befund] = []
    if not bekannt or not temp.is_dir():
        return befunde
    for ordner in temp.glob("_MEI*"):
        try:
            if not ordner.is_dir():
                continue
            minuten = (jetzt - ordner.stat().st_mtime) / 60
            if minuten <= GRENZE_ENTPACKT or _dateien(ordner) not in bekannt:
                continue
        except OSError:
            continue
        befunde.append(Befund(
            "entpackt",
            f"Entpackordner eines alten Starters seit {minuten:.0f} min: {ordner}",
            ordner=ordner,
        ))
    return befunde


def entpackordner_entfernen(ordner: Path) -> bool:
    """Entfernt einen Entpackordner, wenn kein Starter ihn mehr
    benutzt, und sagt, ob er weg ist.

    Zuerst geht die `python313.dll`: solange ein Starter läuft, hat er
    sie geladen, und Windows lässt sie nicht löschen. Dann bleibt der
    Ordner unberührt. Umbenennen ließe sich ein solcher Ordner
    dagegen, auch während der Starter läuft (ausprobiert); das taugt
    nicht als Probe."""
    python = sorted(ordner.glob("python3[0-9]*.dll"))
    if not python:
        return False
    try:
        for dll in python:
            dll.unlink()
    except OSError:
        return False
    shutil.rmtree(ordner, ignore_errors=True)
    return not ordner.exists()


def freier_speicher_mb() -> int | None:
    if sys.platform != "win32":
        return None

    class _Status(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    status = _Status()
    status.dwLength = ctypes.sizeof(_Status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return None
    return int(status.ullAvailPhys // (1024 * 1024))


def _vorfahren(pid: int, prozesse: list[Prozess]) -> set[int]:
    eltern = {p.pid: p.eltern for p in prozesse}
    kette = {pid}
    while pid in eltern and eltern[pid] not in kette:
        pid = eltern[pid]
        kette.add(pid)
    return kette


def pruefen(still_minuten: float) -> Bericht:
    bericht = Bericht()
    prozesse = prozesse_lesen()
    eigene = _vorfahren(os.getpid(), prozesse)
    bericht.befunde += prozesse_bewerten(prozesse, lebende_pids(), eigene)
    befunde, hinweise = arbeitsbaeume_bewerten(
        WURZEL / ".claude" / "worktrees", still_minuten
    )
    bericht.befunde += befunde
    bericht.hinweise += hinweise
    temp = os.environ.get("TEMP")
    if temp:
        bericht.befunde += probeordner_bewerten(Path(temp))
        bekannt = [
            inhalt for exe in natter_starter()
            if (inhalt := starter_inhalt(exe)) is not None
        ]
        bericht.befunde += entpackordner_bewerten(Path(temp), bekannt)
    frei = freier_speicher_mb()
    if frei is not None:
        bericht.hinweise.append(f"freier Arbeitsspeicher: {frei} MB")
        if frei < GRENZE_SPEICHER_MB:
            bericht.befunde.append(Befund("Speicher", f"nur {frei} MB frei"))
    return bericht


def aufraeumen(bericht: Bericht) -> list[str]:
    beendet: list[str] = []
    for befund in bericht.befunde:
        if befund.art == "entpackt" and befund.ordner is not None:
            if entpackordner_entfernen(befund.ordner):
                beendet.append(f"entfernt: {befund.ordner}")
            else:
                beendet.append(f"in Gebrauch, belassen: {befund.ordner}")
            continue
        if befund.pid is None or befund.art not in ("verwaist", "hängend"):
            continue
        subprocess.run(
            ["taskkill", "/PID", str(befund.pid), "/T", "/F"],
            capture_output=True,
            timeout=30,
        )
        beendet.append(f"beendet: {befund.pid} ({befund.art})")
    return beendet


def main(argumente: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Wache für lange Läufe")
    parser.add_argument("--still", type=float, default=10.0,
                        help="Minuten ohne Änderung, ab denen ein Arbeitsbaum als still gilt")
    parser.add_argument("--aufraeumen", action="store_true",
                        help="verwaiste und hängende Prozesse beenden, "
                             "Entpackordner alter Starter entfernen")
    optionen = parser.parse_args(argumente)
    # In einer Konsole mit Codepage 850 kämen Umlaute sonst als
    # Ersatzzeichen an.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    bericht = pruefen(optionen.still)
    zeit = datetime.now(UTC).astimezone().strftime("%H:%M")
    if bericht.ok:
        print(f"WACHE ok {zeit}")
    else:
        arten = sorted({b.art for b in bericht.befunde})
        print(f"WACHE AUFFAELLIG {zeit}: {len(bericht.befunde)} Befunde ({', '.join(arten)})")
    for befund in bericht.befunde:
        print(f"  [{befund.art}] {befund.text}")
    for hinweis in bericht.hinweise:
        print(f"  {hinweis}")
    if optionen.aufraeumen:
        for zeile in aufraeumen(bericht):
            print(f"  {zeile}")
    return 0 if bericht.ok else 1


if __name__ == "__main__":
    sys.exit(main())
