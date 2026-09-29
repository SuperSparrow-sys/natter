"""Womit Natter Python-Code startet (M12).

Natter startet an fünf Stellen Python in einem eigenen Prozess: das
Schülerprogramm (`ide/run/starter.py`), den Debugger (`debugpy`), die
Prüfung vor dem Start (`ruff`), die Paketverwaltung (`pip`) und den
Exe-Export (PyInstaller). Alle fünf gehen über dieses Modul, statt
selbst `sys.executable` in eine Befehlsliste zu schreiben.

Bis M12 war Natter ein mit PyInstaller eingefrorenes Bundle, und
`sys.executable` war dort die Exe selbst: aus `Natter.exe main.py`
wurde kein Schülerprogramm, sondern ein zweites Natter-Fenster. Seit
M13 wird eine gewöhnliche Python-Installation ausgeliefert, und
`sys.executable` ist in beiden Welten ein echter Interpreter. Einen
Rückweg für eine wieder eingefrorene IDE gibt es seit Punkt 223 nicht
mehr; es wird keine gebaut.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def konsolen_python() -> Path:
    """Der Interpreter mit Konsole.

    Die IDE selbst läuft unter `pythonw.exe` – ohne Konsolenfenster, so
    soll ein Fensterprogramm starten. Ein Konsolenprogramm braucht
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
    """Der Befehlsanfang, mit dem sich Python-Code starten lässt."""
    return [str(konsolen_python())]


def umgebung_mit_utf8() -> dict[str, str]:
    """Die Umgebung für einen Kindprozess, dessen Ausgabe Natter liest.

    Ohne Angabe schreibt Python in ein Rohr in der Kodierung des
    Systems, unter Windows also cp1252. Natter liest die Rohre aber als
    UTF-8, und aus `print("Größe")` wurde im Panel „Ausgabe“ „Gr��e“
    (Punkt 186). `PYTHONIOENCODING` legt nur die Kodierung der drei
    Standardströme fest; wie das Programm selbst Dateien öffnet, bleibt
    unverändert.
    """
    return {**os.environ, "PYTHONIOENCODING": "utf-8"}


def ruff_befehl() -> list[str]:
    """Der Aufruf für `ruff` - die Prüfung vor dem Start.

    Die Binärdatei selbst und nicht `python -m ruff`: das Python-Paket
    `ruff` ist nur ein Finder, der `ruff.exe` sucht und startet. Ihn
    einmal hier zu fragen, spart bei jedem Start einen zweiten
    Python-Prozess.
    """
    from ruff import find_ruff_bin

    return [find_ruff_bin()]
