"""Woran Natter merkt, dass ein gestartetes Programm geladen ist
(Punkt 271).

Zwischen F5 und dem ersten Fenster eines Programms können Sekunden
vergehen: Python startet, `pcl` und Qt werden geladen, das Programm
liest vielleicht noch eine Datei ein. Bis 0.3.6 stand in dieser Zeit
nur „… gestartet“ in der Statusleiste, und wer ungeduldig war,
startete ein zweites Mal. Das Hauptfenster zeigt deshalb eine
Ladeanzeige, bis eines von zwei Dingen eintritt:

- Das Programm oder einer seiner Kindprozesse zeigt ein sichtbares
  Fenster. Kindprozesse zählen mit, weil der Interpreter einer
  virtuellen Umgebung unter Windows nur ein Starter ist, der das
  eigentliche Python als Kind aufruft; das Fenster gehört dann dem
  Kind.
- Ein Konsolenprogramm schreibt seine erste Zeile oder fragt nach
  einer Eingabe. Sein Konsolenfenster ist sofort da und sagt nichts
  darüber, ob das Programm schon läuft. Die Hülle, die den Starter
  umgibt, legt dafür beim ersten Schreiben eine leere Markendatei an,
  deren Pfad in `LADEMARKE_VARIABLE` steht.

Beides wird im Takt eines Timers abgefragt und kostet je Abfrage nur
wenige Millisekunden; die Oberfläche wartet nie auf das Programm.
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
import uuid
from pathlib import Path

#: Umgebungsvariable mit dem Pfad der Markendatei.
LADEMARKE_VARIABLE = "NATTER_LADEMARKE"

#: Fensterklassen von Konsolenfenstern. Windows ordnet ein
#: Konsolenfenster dem Programm zu, das darin läuft; es ist aber
#: vom ersten Augenblick an sichtbar und zählt deshalb nicht als
#: „das Programm ist geladen“.
_KONSOLENKLASSEN = frozenset(
    {"ConsoleWindowClass", "PseudoConsoleWindow", "CASCADIA_HOSTING_WINDOW_CLASS"}
)

#: Zeilen für die Hüllen in `ide/run/starter.py` und
#: `ide/debugger/dap_client.py`. Setzt voraus, dass `sys` schon
#: importiert ist. Beim ersten Schreiben auf `stdout`/`stderr` oder
#: beim ersten `input()` entsteht die Markendatei, und die
#: ursprünglichen Ströme kommen zurück; danach kostet die Hülle das
#: Programm nichts mehr. Die Variable wird aus der Umgebung entfernt,
#: damit Programme, die das Schülerprogramm selbst startet, sie nicht
#: erben.
#: Was an den Namen der Lademarke angehängt wird, um die Endmarke zu
#: bekommen (`endmarke_zu`).
ENDMARKE_ZUSATZ = ".ende"

#: Legt die Endmarke an. Steht in den Konsolenhüllen im `finally`,
#: vor der Frage nach der Eingabetaste.
ENDMARKE_SETZEN = (
    "    if _endmarke:\n"
    "        try:\n"
    "            open(_endmarke, 'w').close()\n"
    "        except OSError:\n"
    "            pass\n"
)

LADEMARKE_HUELLE = (
    "import os as _os\n"
    f"_marke = _os.environ.pop({LADEMARKE_VARIABLE!r}, '')\n"
    # Die Endmarke daneben legt die Hülle an, wenn das Programm fertig
    # ist und das Fenster nur noch auf die Eingabetaste wartet (Punkt
    # 455). Der Name wird jetzt festgehalten: `_marke` ist nach der
    # ersten Ausgabe leer.
    f"_endmarke = _marke + {ENDMARKE_ZUSATZ!r} if _marke else ''\n"
    "if _marke and sys.stdout is not None and sys.stderr is not None:\n"
    "    import builtins as _eingebaut\n"
    "    _vorher = (sys.stdout, sys.stderr, _eingebaut.input)\n"
    "    def _geladen():\n"
    "        global _marke\n"
    "        if not _marke:\n"
    "            return\n"
    "        pfad, _marke = _marke, ''\n"
    "        if isinstance(sys.stdout, _Erstausgabe):\n"
    "            sys.stdout = _vorher[0]\n"
    "        if isinstance(sys.stderr, _Erstausgabe):\n"
    "            sys.stderr = _vorher[1]\n"
    "        if _eingebaut.input is _eingabe:\n"
    "            _eingebaut.input = _vorher[2]\n"
    "        try:\n"
    "            open(pfad, 'w').close()\n"
    "        except OSError:\n"
    "            pass\n"
    "    class _Erstausgabe:\n"
    "        def __init__(self, strom):\n"
    "            self._strom = strom\n"
    "        def write(self, text):\n"
    "            if text:\n"
    "                _geladen()\n"
    "            return self._strom.write(text)\n"
    "        def __getattr__(self, name):\n"
    "            return getattr(self._strom, name)\n"
    "    def _eingabe(*argumente):\n"
    "        _geladen()\n"
    "        return _vorher[2](*argumente)\n"
    "    sys.stdout = _Erstausgabe(sys.stdout)\n"
    "    sys.stderr = _Erstausgabe(sys.stderr)\n"
    "    _eingebaut.input = _eingabe\n"
)


#: Anfang des Dateinamens jeder Markendatei.
_MARKEN_PRAEFIX = "natter-geladen-"

#: Ab diesem Alter gilt eine Markendatei beim Start von Natter als
#: liegengeblieben (Punkt 314): ein Tag.
MARKEN_HOECHSTALTER_S = 24 * 60 * 60


def lademarken_ordner() -> Path:
    """Der Ordner für die Markendateien, der Temp-Ordner des Benutzers.
    Eine eigene Funktion, damit Tests ihn umlenken können."""
    return Path(tempfile.gettempdir())


def lademarke_anlegen() -> Path:
    """Ein Pfad für die Markendatei. Angelegt wird die Datei erst von
    der Hülle im gestarteten Programm."""
    return lademarken_ordner() / f"{_MARKEN_PRAEFIX}{uuid.uuid4().hex}"


def lademarke_gesetzt(pfad: Path | None) -> bool:
    return pfad is not None and pfad.exists()


def lademarke_entfernen(pfad: Path | None) -> None:
    if pfad is None:
        return
    try:
        pfad.unlink(missing_ok=True)
    except OSError:
        pass


def alte_lademarken_entfernen(
    hoechstalter_s: float = MARKEN_HOECHSTALTER_S,
) -> int:
    """Entfernt Markendateien, die älter als `hoechstalter_s` sind,
    und liefert, wie viele es waren.

    Läuft beim Start von Natter. Übrig bleibt eine Marke nur, wenn
    Natter selbst nicht mehr dazu kam, sie zu entfernen: nach einem
    Absturz oder wenn Windows den Prozess beendet hat. Eine jüngere
    Marke kann einem zweiten, gerade laufenden Natter gehören und
    bleibt deshalb liegen.
    """
    grenze = time.time() - hoechstalter_s
    entfernt = 0
    try:
        eintraege = list(os.scandir(lademarken_ordner()))
    except OSError:
        return 0
    for eintrag in eintraege:
        if not eintrag.name.startswith(_MARKEN_PRAEFIX):
            continue
        try:
            if not eintrag.is_file() or eintrag.stat().st_mtime > grenze:
                continue
            os.unlink(eintrag.path)
        except OSError:
            continue
        entfernt += 1
    return entfernt


def endmarke_zu(lademarke: Path | None) -> Path | None:
    """Die Datei, die die Hülle eines Konsolenprogramms anlegt, wenn
    das Programm zu Ende ist und das Fenster nur noch auf die
    Eingabetaste wartet. Der Prozess lebt dann noch; ohne die Marke
    hielt Natter das Programm für laufend und lehnte den nächsten
    Start mit „läuft bereits“ ab (Punkt 455)."""
    if lademarke is None:
        return None
    return Path(f"{lademarke}{ENDMARKE_ZUSATZ}")


def umgebung_mit_lademarke(
    pfad: Path | None, umgebung: dict[str, str] | None = None
) -> dict[str, str]:
    """Die Umgebung für den Kindprozess, mit dem Pfad der Marke."""
    ergebnis = dict(os.environ if umgebung is None else umgebung)
    if pfad is not None:
        ergebnis[LADEMARKE_VARIABLE] = str(pfad)
    return ergebnis


def _prozessbaum(pid: int) -> set[int]:
    """`pid` und alle seine Nachfahren, laut einer Momentaufnahme der
    Prozessliste."""
    import ctypes
    import ctypes.wintypes as wt

    class Eintrag(ctypes.Structure):
        _fields_ = [
            ("dwSize", wt.DWORD),
            ("cntUsage", wt.DWORD),
            ("th32ProcessID", wt.DWORD),
            ("th32DefaultHeapID", ctypes.c_size_t),
            ("th32ModuleID", wt.DWORD),
            ("cntThreads", wt.DWORD),
            ("th32ParentProcessID", wt.DWORD),
            ("pcPriClassBase", wt.LONG),
            ("dwFlags", wt.DWORD),
            ("szExeFile", wt.WCHAR * 260),
        ]

    kernel32 = ctypes.windll.kernel32
    kernel32.CreateToolhelp32Snapshot.restype = wt.HANDLE
    kernel32.CreateToolhelp32Snapshot.argtypes = [wt.DWORD, wt.DWORD]
    kernel32.Process32FirstW.argtypes = [wt.HANDLE, ctypes.POINTER(Eintrag)]
    kernel32.Process32NextW.argtypes = [wt.HANDLE, ctypes.POINTER(Eintrag)]
    kernel32.CloseHandle.argtypes = [wt.HANDLE]

    aufnahme = kernel32.CreateToolhelp32Snapshot(0x2, 0)  # TH32CS_SNAPPROCESS
    if not aufnahme or aufnahme == ctypes.c_void_p(-1).value:
        return {pid}
    kinder: dict[int, list[int]] = {}
    try:
        eintrag = Eintrag()
        eintrag.dwSize = ctypes.sizeof(Eintrag)
        weiter = kernel32.Process32FirstW(aufnahme, ctypes.byref(eintrag))
        while weiter:
            kinder.setdefault(eintrag.th32ParentProcessID, []).append(
                eintrag.th32ProcessID
            )
            weiter = kernel32.Process32NextW(aufnahme, ctypes.byref(eintrag))
    finally:
        kernel32.CloseHandle(aufnahme)

    baum = {pid}
    offen = [pid]
    while offen:
        for kind in kinder.get(offen.pop(), []):
            # Windows vergibt Prozessnummern neu; ein Kreis in den
            # Elternangaben ist deshalb möglich und wird übergangen.
            if kind not in baum:
                baum.add(kind)
                offen.append(kind)
    return baum


def hat_sichtbares_fenster(pid: int) -> bool:
    """Zeigt der Prozess `pid` oder einer seiner Nachfahren schon ein
    sichtbares Fenster, das kein Konsolenfenster ist?

    Außerhalb von Windows gibt es keinen einfachen Weg, das zu
    erfahren; dort gilt ein Programm sofort als geladen.
    """
    if sys.platform != "win32":
        return True
    import ctypes
    import ctypes.wintypes as wt

    user32 = ctypes.windll.user32
    prozesse = _prozessbaum(pid)
    gefunden: list[int] = []
    klasse = ctypes.create_unicode_buffer(64)

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def pruefen(fenster, _):  # noqa: ANN001, ANN202
        besitzer = wt.DWORD()
        user32.GetWindowThreadProcessId(fenster, ctypes.byref(besitzer))
        if besitzer.value not in prozesse or not user32.IsWindowVisible(fenster):
            return True
        user32.GetClassNameW(fenster, klasse, len(klasse))
        if klasse.value in _KONSOLENKLASSEN:
            return True
        gefunden.append(fenster)
        return False

    user32.EnumWindows(pruefen, 0)
    return bool(gefunden)
