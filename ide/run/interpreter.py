"""Womit Natter Python-Code startet (M12).

Natter startet an fünf Stellen Python in einem eigenen Prozess: das
Schülerprogramm (`ide/run/starter.py`), den Debugger (`debugpy`), die
Prüfung vor dem Start (`ruff`), die Paketverwaltung (`pip`) und den
Exe-Export (PyInstaller). Alle fünf schrieben dafür `sys.executable`.

Im Entwicklungsbaum ist das der Python aus `.venv` und damit richtig.
**In der mit PyInstaller gebauten `Natter.exe` ist `sys.executable` die
Exe selbst** – aus `Natter.exe main.py` wurde dort also nicht das
Schülerprogramm, sondern ein zweites Natter-Fenster. Vom Nutzer im
installierten Programm gemeldet: „die Konsole und die GUI sind beim
Start nicht aufgegangen, sondern nur ein weiteres Fenster von Natter.“
Betroffen waren alle fünf Stellen, nicht nur die auffälligste.

Eine eigene Python-Installation daneben zu verlangen, wäre für einen
Schulrechner der falsche Weg – der ganze Sinn der Exe ist, dass nichts
weiter installiert werden muss. Die gebaute Exe **enthält** aber einen
vollständigen Python. Sie muss ihn nur herausreichen: mit der Flagge
`--python` davor verhält sich `Natter.exe` wie ein Python-Aufruf und
führt aus, was dahinter steht, statt die IDE zu öffnen.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

#: Steht als erstes Argument vor einem Python-Aufruf an `Natter.exe`.
#: Absichtlich sperrig: ein Schüler soll nicht versehentlich darauf
#: stoßen, und eine `.natter`-Datei kann so nie damit verwechselt werden.
PYTHON_FLAGGE = "--python"

#: So heißt die Ruff-Binärdatei im Bundle der gebauten Exe.
RUFF_DATEINAME = "ruff.exe" if sys.platform == "win32" else "ruff"


def ist_gebaut() -> bool:
    """Ob Natter als PyInstaller-Exe läuft."""
    return bool(getattr(sys, "frozen", False))


def konsolen_python() -> Path:
    """Der Interpreter **mit** Konsole.

    Die IDE selbst läuft unter `pythonw.exe` – ohne Konsolenfenster, so
    soll ein Fensterprogramm starten. Ein **Konsolen**programm braucht
    dagegen `python.exe`: unter `pythonw` hätte es keine Konsole, in die
    es schreiben könnte, und `print()` liefe ins Leere (M13).
    """
    pfad = Path(sys.executable)
    if pfad.name.lower() == "pythonw.exe":
        mit_konsole = pfad.with_name("python.exe")
        if mit_konsole.is_file():
            return mit_konsole
    return pfad


def python_befehl() -> list[str]:
    """Der Befehlsanfang, mit dem sich Python-Code starten lässt.

    Seit M13 wird eine gewöhnliche Python-Installation ausgeliefert –
    hier steht also in beiden Welten ein echter Interpreter. Die Flagge
    `--python` bleibt als Rückfallebene für den Fall, dass doch wieder
    ein eingefrorenes Bundle gebaut wird.
    """
    if ist_gebaut():
        return [sys.executable, PYTHON_FLAGGE]
    return [str(konsolen_python())]


def ruff_befehl() -> list[str]:
    """Der Aufruf für `ruff` – die Prüfung vor dem Start.

    Bewusst die Binärdatei selbst und nicht `python -m ruff`: das
    Python-Paket `ruff` ist nur ein **Finder**, der `ruff.exe` in den
    `Scripts`-Ordnern der Python-Installation sucht und startet. In der
    gebauten Exe gibt es diese Ordner nicht; `--collect-all ruff`
    brachte nur den Finder mit, nicht die Binärdatei, und die Prüfung
    vor dem Start endete in `RuffNotFound` (M12, in der gebauten Exe
    nachgemessen).

    In der Exe liegt `ruff.exe` deshalb im Bundle (`--add-binary`),
    im Entwicklungsbaum fragen wir das Paket selbst.
    """
    if ist_gebaut():
        return [str(Path(getattr(sys, "_MEIPASS", ".")) / RUFF_DATEINAME)]
    from ruff import find_ruff_bin

    return [find_ruff_bin()]


def als_python_ausfuehren(argumente: list[str]) -> int:
    """Führt `argumente` aus, als wäre Natter der Python-Aufruf.

    Versteht dieselben drei Formen, die Natter selbst benutzt:

    * `<skript.py> [argumente]` – wie `python skript.py`
    * `-m <modul> [argumente]` – wie `python -m modul`
    * `-c <quelltext> [argumente]` – wie `python -c "…"`

    Liefert den Rückgabewert für `sys.exit()`.
    """
    if not argumente:
        print("Nach --python fehlt der Aufruf.", file=sys.stderr)
        return 2

    # Die Fehleranzeige gleich hier: ein Schülerprogramm, das nicht
    # über `Application.run()` läuft (jedes Konsolenprogramm), hätte
    # sonst keine. In der gebauten Exe kommt dazu, dass ein Fehler
    # **niemals** bis nach oben durchfliegen darf: PyInstallers
    # Bootloader fängt ihn dort selbst ab und wartet auf einen Klick in
    # ein Fenster, das hinter dem Programm liegt - das sah wie ein
    # Hänger aus (in der gebauten Exe nachgemessen, M12).
    from pcl.fehleranzeige import einhaengen, fehler_zeigen

    einhaengen()

    erstes, rest = argumente[0], argumente[1:]
    try:
        if erstes == "-m":
            if not rest:
                print("Nach -m fehlt der Modulname.", file=sys.stderr)
                return 2
            # `sys.argv` so setzen, wie das Modul es erwartet: der
            # Modulname steht an Stelle 0, nicht der Natter-Aufruf.
            sys.argv = [rest[0], *rest[1:]]
            runpy.run_module(rest[0], run_name="__main__", alter_sys=True)
        elif erstes == "-c":
            if not rest:
                print("Nach -c fehlt der Quelltext.", file=sys.stderr)
                return 2
            sys.argv = ["-c", *rest[1:]]
            exec(compile(rest[0], "<string>", "exec"), {"__name__": "__main__"})  # noqa: S102
        else:
            sys.argv = [erstes, *rest]
            runpy.run_path(erstes, run_name="__main__")
    except SystemExit as beendet:
        return beendet.code if isinstance(beendet.code, int) else 0
    except BaseException:  # noqa: BLE001 - hier endet das Schülerprogramm
        fehler_zeigen(*sys.exc_info())
        return 1
    return 0
