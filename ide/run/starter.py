"""Startet ein Natter-Projekt als eigenen Prozess (Strg+F5, ohne
Debugger).

Siehe README.md, Abschnitt 7.8:

- GUI-Projekte: eigenes Programmfenster, keine Konsole, IDE bleibt
  bedienbar. Die Ausgabe des Programms geht durch ein Rohr ins Panel
  „Ausgabe“ - ohne Konsole gäbe es sonst keinen Ort dafür.
- Konsolenprojekte: eigenes Konsolenfenster unter Windows
  (`CREATE_NEW_CONSOLE`); auf anderen Plattformen (Entwicklung/Tests)
  läuft die Konsole im aktuellen Terminal weiter, da es dort kein
  Äquivalent gibt

Startet nicht blockierend (`subprocess.Popen`) – die IDE wartet nicht
auf das Programmende.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

from ide.project import Projekt
from ide.prozess import auftrag_zuweisen, ohne_konsole
from ide.run.interpreter import python_befehl, umgebung_mit_utf8
from ide.run.ladeanzeige import (
    ENDMARKE_SETZEN,
    LADEMARKE_HUELLE,
    umgebung_mit_lademarke,
)

#: Hülle für Konsolenprogramme: führt das Schülerprogramm aus und hält
#: das Fenster danach offen.
#:
#: Ohne sie schließt Windows das mit `CREATE_NEW_CONSOLE` geöffnete
#: Fenster in dem Augenblick, in dem das Programm endet – die Ausgabe
#: ist dann weg, bevor jemand sie lesen konnte. Genau deshalb hatte der
#: Nutzer angefangen, `input()` von Hand ans Ende seiner Beispiele zu
#: schreiben; das gehört aber in den Starter und nicht in jedes
#: Programm.
#:
#: Die Pause kommt auch nach einem Absturz – gerade dann will man
#: den Fehler lesen können. Deshalb `finally` und nicht nur der
#: Erfolgsfall.
#:
#: Als `-c`-Text statt als eigene Datei, damit es auch in der mit
#: PyInstaller gebauten IDE funktioniert: dort liegt kein Python-
#: Quelltext auf der Platte, den man als Pfad übergeben könnte.
_KONSOLEN_HUELLE = (
    "import runpy, sys, traceback\n"
    # Legt bei der ersten Ausgabe die Marke an, auf die die
    # Ladeanzeige im Hauptfenster wartet (Punkt 271).
    + LADEMARKE_HUELLE
    +
    # argv[1] ist der Fenstertitel, argv[2] das Programm. Beide werden
    # danach aus sys.argv entfernt, damit das Schülerprogramm sein
    # eigenes argv sieht und nicht das der Hülle.
    "titel, skript = sys.argv[1], sys.argv[2]\n"
    "sys.argv = sys.argv[2:]\n"
    # Fenstertitel setzen, sonst steht dort der ganze Python-Aufruf mit
    # dem Hüllen-Quelltext darin; im Titel steht der Programmname.
    "if sys.platform == 'win32':\n"
    "    try:\n"
    "        import ctypes\n"
    "        ctypes.windll.kernel32.SetConsoleTitleW(titel)\n"
    "    except Exception:\n"
    "        pass\n"
    "rueckgabe = 0\n"
    "try:\n"
    "    runpy.run_path(skript, run_name='__main__')\n"
    "except SystemExit as beendet:\n"
    "    rueckgabe = beendet.code if isinstance(beendet.code, int) else 0\n"
    # Dieselbe Meldung (Wo, Was, Zu prüfen) wie im Debugger und im GUI-Programm
    # (M12). Ohne sie stand hier der rohe englische Traceback, in dem vor
    # der einen wichtigen Zeile ein Dutzend Zeilen aus `pcl` und Qt
    # stehen. Fällt der Import aus, bleibt der Traceback als Rückfall -
    # eine Meldung ist besser als keine.
    "except BaseException:\n"
    "    try:\n"
    "        from pcl.fehleranzeige import fehlertext\n"
    "        print(fehlertext(*sys.exc_info()), file=sys.stderr)\n"
    "    except Exception:\n"
    "        traceback.print_exc()\n"
    "    rueckgabe = 1\n"
    "finally:\n"
    + ENDMARKE_SETZEN
    + "    try:\n"
    "        input('\\nProgramm beendet. Eingabetaste zum Schließen ...')\n"
    "    except (EOFError, KeyboardInterrupt):\n"
    "        pass\n"
    "sys.exit(rueckgabe)\n"
)


def projekt_starten(
    projekt: Projekt, lademarke: Path | None = None
) -> subprocess.Popen:
    """Startet das Projekt als eigenen Prozess und liefert ihn zurück.

    Ein GUI-Programm bekommt kein Konsolenfenster. Das klang oben seit
    jeher so, stimmte aber nicht: `python_befehl()` liefert den
    Interpreter mit Konsole, und weil Natter selbst als Fensterprogramm
    ohne Konsole läuft, legte Windows für das Schülerprogramm eine neue
    an. Hinter dem Fenster des Programms stand also ein schwarzer
    Kasten, den niemand bestellt hatte.

    Weil ein Programm ohne Konsole nirgendwohin schreiben könnte, geht
    seine Ausgabe stattdessen durch ein Rohr - der Aufrufer liest sie
    mit `ide/shell/hintergrund.AusgabeLeser` und zeigt sie im Panel
    „Ausgabe“, wo sie ohnehin hingehört. Das gilt auch für
    Fehlermeldungen: `stderr` läuft in dasselbe Rohr, damit ein Absturz
    nicht spurlos bleibt.

    `lademarke` ist die Datei, die ein Konsolenprogramm bei seiner
    ersten Ausgabe anlegt (`ide/run/ladeanzeige.py`). Ein Programm mit
    Fenster braucht sie nicht; dort zählt das erste Fenster.

    Der Prozess läuft in einem Windows-Auftragsobjekt
    (`ide.prozess.auftrag_zuweisen`), damit „Stopp“ und das Schließen
    von Natter auch erreichen, was das Programm gestartet hat, wenn
    es selbst schon zu Ende ist (Punkt 281).
    """
    zusatz_optionen: dict[str, object] = {}
    befehl = [*python_befehl(), projekt.haupt_datei.name]

    if projekt.typ == "console":
        # Die Hülle hält das Fenster offen; sie kostet auf anderen
        # Plattformen nichts, weil die Eingabeaufforderung dort im
        # bestehenden Terminal erscheint.
        befehl = [
            *python_befehl(),
            "-c",
            _KONSOLEN_HUELLE,
            f"Natter – {projekt.name}",
            projekt.haupt_datei.name,
        ]
        if sys.platform == "win32":
            zusatz_optionen["creationflags"] = subprocess.CREATE_NEW_CONSOLE
        prozess = subprocess.Popen(
            befehl,
            cwd=projekt.ordner,
            env=umgebung_mit_lademarke(lademarke),
            **zusatz_optionen,
        )
        auftrag_zuweisen(prozess)
        return prozess

    prozess = subprocess.Popen(
        befehl,
        **ohne_konsole(
            cwd=projekt.ordner,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            env=umgebung_mit_utf8(),
        ),
    )
    auftrag_zuweisen(prozess)
    return prozess


def erste_zeile_der_haupt_unit(projekt: Projekt) -> tuple[Path, int]:
    """Datei und Zeile, in der ein Einzelschritt vor dem Start hält
    (Punkt 295).

    Bei einem Konsolenprojekt die erste Anweisung in `main()` der
    Haupt-Unit: die Anweisungen davor legen nur Funktionen an, und
    `main.py` ruft `main()` bloß auf. Sonst, oder wenn es kein
    `main()` gibt, die erste Anweisung der Haupt-Unit, zuletzt die
    der Startdatei."""
    unit = projekt.haupt_unit
    if unit:
        datei = projekt.ordner / f"{unit}.py"
        baum = _baum_oder_none(datei)
        if baum is not None:
            if projekt.typ == "console":
                main = next(
                    (
                        knoten
                        for knoten in baum.body
                        if isinstance(knoten, ast.FunctionDef)
                        and knoten.name == "main"
                    ),
                    None,
                )
                zeile = _erste_anweisung(main.body) if main else None
                if zeile is not None:
                    return datei, zeile
            zeile = _erste_anweisung(baum.body)
            if zeile is not None:
                return datei, zeile
    baum = _baum_oder_none(projekt.haupt_datei)
    zeile = _erste_anweisung(baum.body) if baum is not None else None
    return projekt.haupt_datei, zeile or 1


def _baum_oder_none(datei: Path) -> ast.Module | None:
    try:
        return ast.parse(datei.read_bytes(), str(datei))
    except (OSError, SyntaxError, ValueError):
        return None


def _erste_anweisung(anweisungen: list[ast.stmt]) -> int | None:
    """Zeile der ersten Anweisung, die etwas tut. Ein Docstring am
    Anfang zählt nicht mit; an ihm hält der Debugger nicht."""
    for anweisung in anweisungen:
        if isinstance(anweisung, ast.Expr) and isinstance(
            anweisung.value, ast.Constant
        ) and isinstance(anweisung.value.value, str):
            continue
        return anweisung.lineno
    return None
