"""Startet ein Natter-Projekt als eigenen Prozess (Strg+F5, ohne
Debugger).

Siehe konzept-natter.md, Abschnitt 7.8:

- GUI-Projekte: eigenes Programmfenster, keine Konsole, IDE bleibt
  bedienbar
- Konsolenprojekte: eigenes Konsolenfenster unter Windows
  (`CREATE_NEW_CONSOLE`); auf anderen Plattformen (Entwicklung/Tests)
  läuft die Konsole im aktuellen Terminal weiter, da es dort kein
  Äquivalent gibt

Startet nicht blockierend (`subprocess.Popen`) – die IDE wartet nicht
auf das Programmende.
"""

from __future__ import annotations

import subprocess
import sys

from ide.project import Projekt
from ide.run.interpreter import python_befehl

#: Hülle für Konsolenprogramme: führt das Schülerprogramm aus und hält
#: das Fenster danach offen.
#:
#: Ohne sie schließt Windows das mit `CREATE_NEW_CONSOLE` geöffnete
#: Fenster in dem Augenblick, in dem das Programm endet – die Ausgabe
#: ist dann weg, bevor jemand sie lesen konnte. Genau deshalb hatte der
#: Nutzer angefangen, `input()` von Hand ans Ende seiner Beispiele zu
#: schreiben; das gehört aber in den Starter und nicht in jedes
#: Programm. Lazarus und Delphi machen es genauso.
#:
#: Die Pause kommt **auch nach einem Absturz** – gerade dann will man
#: den Fehler lesen können. Deshalb `finally` und nicht nur der
#: Erfolgsfall.
#:
#: Als `-c`-Text statt als eigene Datei, damit es auch in der mit
#: PyInstaller gebauten IDE funktioniert: dort liegt kein Python-
#: Quelltext auf der Platte, den man als Pfad übergeben könnte.
_KONSOLEN_HUELLE = (
    "import runpy, sys, traceback\n"
    # argv[1] ist der Fenstertitel, argv[2] das Programm. Beide werden
    # danach aus sys.argv entfernt, damit das Schülerprogramm sein
    # eigenes argv sieht und nicht das der Hülle.
    "titel, skript = sys.argv[1], sys.argv[2]\n"
    "sys.argv = sys.argv[2:]\n"
    # Fenstertitel setzen, sonst steht dort der ganze Python-Aufruf mit
    # dem Hüllen-Quelltext darin. Lazarus benennt sein Konsolenfenster
    # genauso nach dem Programm.
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
    # Dieselbe Wo/Was/Prüfe-Meldung wie im Debugger und im GUI-Programm
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
    "    try:\n"
    "        input('\\nProgramm beendet. Eingabetaste zum Schließen ...')\n"
    "    except (EOFError, KeyboardInterrupt):\n"
    "        pass\n"
    "sys.exit(rueckgabe)\n"
)


def projekt_starten(projekt: Projekt) -> subprocess.Popen:
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

    return subprocess.Popen(befehl, cwd=projekt.ordner, **zusatz_optionen)
