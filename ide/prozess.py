"""Unterprozesse ohne Konsolenfenster starten.

Natter läuft als Fensterprogramm und hat deshalb keine Konsole.
Startet es einen Unterprozess, der zum Konsolen-Subsystem gehört –
`python.exe`, `pip`, `ruff`, PyInstaller, der Debugger –, legt Windows
dafür ein eigenes Konsolenfenster an. Das blitzt auf, steht im Weg und
hat mit dem zu tun, was jemand gerade macht, überhaupt nichts. Selbst
wenn die Ausgabe über Rohre eingesammelt wird, erscheint das Fenster:
es hängt am Subsystem des gestarteten Programms, nicht an den Rohren.

Dagegen hilft nur `CREATE_NO_WINDOW` an jedem einzelnen Aufruf. Damit
es nicht siebenmal einzeln dasteht und beim achten Aufruf vergessen
wird, steht es hier.

Zwei Ausnahmen bleiben, und beide sind Absicht: ein Konsolenprojekt
einer Schülerin braucht sein Fenster, denn dort steht die Ausgabe
(`ide/run/starter.py` setzt dafür `CREATE_NEW_CONSOLE`), und beim
Bauen aus der Kommandozeile gibt es ohnehin eine Konsole, in der alles
erscheinen darf.

Außerdem steht hier das Auftragsobjekt (Job Object), in dem die
Schülerprogramme laufen; siehe `Auftrag`.
"""

from __future__ import annotations

import ctypes
import subprocess
import sys
import weakref
from typing import Any

#: Unter Windows das Kennzeichen, das kein Konsolenfenster anlegt.
#: `getattr`, weil es die Flagge auf anderen Plattformen nicht gibt und
#: die Module auch dort importierbar bleiben sollen.
_OHNE_FENSTER = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def ohne_konsole(**weitere: Any) -> dict[str, Any]:
    """Die Argumente für `subprocess`, die kein Fenster aufgehen lassen.

    Gedacht zum Auspacken in den Aufruf::

        subprocess.run(befehl, **ohne_konsole(capture_output=True))

    Übergebene `creationflags` bleiben erhalten und werden ergänzt, statt
    überschrieben zu werden.
    """
    argumente = dict(weitere)
    if sys.platform == "win32":
        argumente["creationflags"] = int(argumente.get("creationflags", 0)) | _OHNE_FENSTER
    return argumente


# -- Auftragsobjekt (Punkt 281) ---------------------------------------

_JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
_JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION = 1
_JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
_PROCESS_TERMINATE = 0x0001
_PROCESS_SET_QUOTA = 0x0100


class _GrundGrenzen(ctypes.Structure):
    """JOBOBJECT_BASIC_LIMIT_INFORMATION"""

    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_int64),
        ("PerJobUserTimeLimit", ctypes.c_int64),
        ("LimitFlags", ctypes.c_uint32),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", ctypes.c_uint32),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", ctypes.c_uint32),
        ("SchedulingClass", ctypes.c_uint32),
    ]


class _ErweiterteGrenzen(ctypes.Structure):
    """JOBOBJECT_EXTENDED_LIMIT_INFORMATION"""

    _fields_ = [
        ("BasicLimitInformation", _GrundGrenzen),
        ("IoInfo", ctypes.c_uint64 * 6),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


class _Abrechnung(ctypes.Structure):
    """JOBOBJECT_BASIC_ACCOUNTING_INFORMATION"""

    _fields_ = [
        ("TotalUserTime", ctypes.c_int64),
        ("TotalKernelTime", ctypes.c_int64),
        ("ThisPeriodTotalUserTime", ctypes.c_int64),
        ("ThisPeriodTotalKernelTime", ctypes.c_int64),
        ("TotalPageFaultCount", ctypes.c_uint32),
        ("TotalProcesses", ctypes.c_uint32),
        ("ActiveProcesses", ctypes.c_uint32),
        ("TotalTerminatedProcesses", ctypes.c_uint32),
    ]


_KERNEL32: Any = None


def _kernel32() -> Any:
    """kernel32 mit Typangaben, damit Griffe unter 64 Bit nicht auf
    32 Bit gekürzt werden. Ein eigenes `WinDLL`, damit die Angaben
    nicht in `ctypes.windll` für andere Aufrufer mitgelten."""
    global _KERNEL32
    if _KERNEL32 is not None:
        return _KERNEL32
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    griff = ctypes.c_void_p
    k.CreateJobObjectW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p]
    k.CreateJobObjectW.restype = griff
    k.SetInformationJobObject.argtypes = [
        griff, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32
    ]
    k.SetInformationJobObject.restype = ctypes.c_int
    k.QueryInformationJobObject.argtypes = [
        griff, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32,
        ctypes.c_void_p,
    ]
    k.QueryInformationJobObject.restype = ctypes.c_int
    k.AssignProcessToJobObject.argtypes = [griff, griff]
    k.AssignProcessToJobObject.restype = ctypes.c_int
    k.TerminateJobObject.argtypes = [griff, ctypes.c_uint]
    k.TerminateJobObject.restype = ctypes.c_int
    k.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    k.OpenProcess.restype = griff
    k.CloseHandle.argtypes = [griff]
    k.CloseHandle.restype = ctypes.c_int
    _KERNEL32 = k
    return k


class Auftrag:
    """Ein Windows-Auftragsobjekt (Job Object) für ein Schülerprogramm.

    `taskkill /T` findet die Kindprozesse über den Elternprozess.
    Startet ein Programm einen Prozess und endet dann, hat dieser
    Prozess keinen lebenden Elternteil mehr, und „Stopp“ oder das
    Schließen von Natter erreichten ihn nicht (Punkt 281). Ein
    Prozess in einem Auftrag bleibt darin, und alles, was er startet,
    kommt ebenfalls hinein, auch nachdem er selbst zu Ende ist.

    Der Auftrag trägt `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`: wird der
    letzte Griff darauf geschlossen, endet alles darin. Das geschieht
    in `beenden()`, wenn das Objekt verworfen wird, und spätestens
    dann, wenn Natter selbst endet, auch nach einem Absturz, weil
    Windows dabei alle Griffe schließt.
    """

    def __init__(self, griff: int) -> None:
        self._griff: int | None = griff

    def aufnehmen(self, prozess: subprocess.Popen) -> bool:
        """Nimmt einen laufenden Prozess in den Auftrag auf."""
        if self._griff is None:
            return False
        k = _kernel32()
        prozessgriff = k.OpenProcess(
            _PROCESS_SET_QUOTA | _PROCESS_TERMINATE, False, prozess.pid
        )
        if not prozessgriff:
            return False
        try:
            return bool(
                k.AssignProcessToJobObject(self._griff, prozessgriff)
            )
        finally:
            k.CloseHandle(prozessgriff)

    def laeuft_noch(self) -> bool:
        """Ob im Auftrag noch ein Prozess lebt."""
        if self._griff is None:
            return False
        info = _Abrechnung()
        if not _kernel32().QueryInformationJobObject(
            self._griff,
            _JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION,
            ctypes.byref(info),
            ctypes.sizeof(info),
            None,
        ):
            return False
        return info.ActiveProcesses > 0

    def beenden(self) -> None:
        """Beendet alle Prozesse im Auftrag und gibt ihn frei."""
        griff, self._griff = self._griff, None
        if griff is None:
            return
        k = _kernel32()
        k.TerminateJobObject(griff, 1)
        k.CloseHandle(griff)

    def __del__(self) -> None:
        try:
            self.beenden()
        except Exception:
            pass


#: Welcher Prozess in welchem Auftrag läuft. Schwach gehalten, damit
#: der Eintrag mit dem `Popen`-Objekt verschwindet.
_AUFTRAEGE: weakref.WeakKeyDictionary[subprocess.Popen, Auftrag] = (
    weakref.WeakKeyDictionary()
)


def auftrag_zuweisen(prozess: subprocess.Popen) -> Auftrag | None:
    """Legt einen Auftrag an und nimmt `prozess` darin auf.

    Aufzurufen gleich nach `Popen`, bevor das Programm dazu kommt,
    selbst etwas zu starten; der Python-Interpreter braucht für
    seinen Start ein Vielfaches der Zeit, die das dauert.

    Läuft Natter selbst schon in einem Auftrag (etwa unter einem
    Startprogramm wie dem von uv), wird der neue darin verschachtelt;
    das kann Windows seit Version 8. Klappt das nicht, liefert die
    Funktion `None`, und `prozessbaum_beenden` fällt auf
    `taskkill /T` zurück, das den Baum abgeht, solange das Programm
    lebt.
    """
    if sys.platform != "win32":
        return None
    try:
        k = _kernel32()
        griff = k.CreateJobObjectW(None, None)
        if not griff:
            return None
        auftrag = Auftrag(griff)
        grenzen = _ErweiterteGrenzen()
        grenzen.BasicLimitInformation.LimitFlags = (
            _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        )
        eingerichtet = k.SetInformationJobObject(
            griff,
            _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
            ctypes.byref(grenzen),
            ctypes.sizeof(grenzen),
        )
        if not eingerichtet or not auftrag.aufnehmen(prozess):
            # Darin läuft noch nichts; der Griff kann einfach zu.
            auftrag.beenden()
            return None
    except (OSError, AttributeError, TypeError, ctypes.ArgumentError):
        return None
    _AUFTRAEGE[prozess] = auftrag
    return auftrag


def auftrag_von(prozess: subprocess.Popen) -> Auftrag | None:
    """Der Auftrag, in dem `prozess` läuft, falls es einen gibt."""
    try:
        return _AUFTRAEGE.get(prozess)
    except TypeError:
        # Kein `Popen`, sondern etwa ein Ersatz in einem Test, auf den
        # sich kein schwacher Verweis setzen lässt.
        return None


def prozessbaum_beenden(prozess: subprocess.Popen, zeitlimit: float = 5.0) -> None:
    """Beendet `prozess` samt allen Prozessen, die er gestartet hat.

    `Popen.kill()` trifft unter Windows nur den einen Prozess. Der
    Debugger startet neben dem Schülerprogramm einen eigenen
    Adapter-Prozess, und ein Programm kann selbst weitere starten; die
    blieben ohne Elternteil zurück (Punkt 222).

    Läuft der Prozess in einem Auftrag (`auftrag_zuweisen`), endet mit
    dem Auftrag alles darin, auch wenn `prozess` selbst schon beendet
    ist und nur noch ein Enkel lebt (Punkt 281). Ohne Auftrag geht
    `taskkill /T` den Baum ab, solange der oberste Prozess noch lebt,
    und `kill()` bleibt als Rückfallebene, falls `taskkill` fehlt oder
    scheitert.
    """
    auftrag = auftrag_von(prozess)
    if auftrag is not None:
        _AUFTRAEGE.pop(prozess, None)
        auftrag.beenden()
    if prozess.poll() is not None:
        return
    if auftrag is not None:
        try:
            prozess.wait(timeout=zeitlimit)
            return
        except subprocess.TimeoutExpired:
            pass
    if sys.platform == "win32":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(prozess.pid), "/T", "/F"],
                **ohne_konsole(capture_output=True, timeout=zeitlimit),
            )
        except (OSError, subprocess.TimeoutExpired):
            pass
    if prozess.poll() is None:
        try:
            prozess.kill()
        except OSError:
            pass
    try:
        prozess.wait(timeout=zeitlimit)
    except subprocess.TimeoutExpired:
        pass
