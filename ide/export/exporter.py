"""Baut ein Natter-Projekt mit PyInstaller zu **einer einzigen** Exe
(README.md, Abschnitt 16 „Export"; M8 Schritt 4, M14).

Nutzt dieselbe Python-Umgebung wie die IDE selbst (`python_befehl()`,
siehe `ide/run/interpreter.py`) - PyInstaller liegt der Auslieferung bei
(siehe `tools/ide_paketieren.py`), es ist kein Extra-Download auf dem
Schüler-Rechner nötig.

**Eine Datei, kein Ordner** (Nutzer-Vorgabe September 2026: „es darf
keinen extra Ordner geben, das ganze Programm soll in der exe sein").
Bis dahin baute Natter die Ordner-Variante und packte sie in ein ZIP.
Das ist technisch der robustere Weg, aber für den Zweck der falsche: wer
sein Spiel einem Freund schickt, schickt eine Datei und keine
Anleitung zum Entpacken. Alles, was das Projekt braucht - auch die
Unterordner `daten/`, `bilder/`, `assets/` -, wandert dafür **in** die
Exe; zur Laufzeit packt PyInstaller sie neben das Skript aus, sodass
`Path(__file__).parent / "bilder"` weiter stimmt.

Der Preis ist ein spürbar langsamerer Start (die Exe entpackt sich bei
jedem Lauf) und eine größere Datei. Beides ist hier das kleinere Übel.

Baut absichtlich nicht das Prüfsummen-Manifest/die Authenticode-Signatur
aus `prototypes/s6_signatur` mit ein - eine Signatur braucht ein
gekauftes Zertifikat, das ein Schulprojekt normalerweise nicht hat;
das bleibt ein bewusst manueller, optionaler Schritt, siehe
`docs/arbeitspakete/M8.md`.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pcl
from ide.project import Projekt
from ide.run.interpreter import python_befehl

_GUI_PROJEKTTYPEN = {"gui", "gui_db"}

#: `pcl.theme` lädt `design/tokens.json` zur Laufzeit (Abschnitt 6) statt
#: es zu importieren – PyInstaller bindet daher nur den Python-Code
#: automatisch ein, nicht diese Datei. Ohne `--add-data` stürzt jede
#: exportierte Exe schon beim Start ab (siehe `pcl/theme/__init__.py`,
#: `_tokens_pfad_ermitteln`, das im Bundle unter `design/` danach sucht).
_DESIGN_ORDNER = Path(pcl.__file__).resolve().parent.parent / "design"

#: Unterordner, die nicht ins Programm gehören: Bauabfälle und Material,
#: das nur in der IDE gebraucht wird.
_NICHT_MITNEHMEN = {
    "dist",
    "build",
    "__pycache__",
    "_pyinstaller_build",
    "_pyinstaller_spec",
    "diagramme",
    ".git",
}

#: Woran sich der Fortschritt eines PyInstaller-Laufs ablesen lässt.
#:
#: PyInstaller meldet keinen Prozentwert, wohl aber seine Phasen. Die
#: Zahlen sind an echten Läufen abgeschätzt: das Einsammeln der
#: Abhängigkeiten dauert am längsten, das Schreiben der Exe geht schnell.
#:
#: „Looking for …" steht bewusst **nicht** in der Liste, obwohl es
#: auffällig oft vorkommt: PyInstaller sucht schon in der ersten Sekunde
#: nach der Python-Bibliothek. Als Marke genommen sprang der Balken
#: sofort auf über die Hälfte und stand dann lange still (an einem
#: echten Export gemessen, M14).
_PHASEN: tuple[tuple[str, int, str], ...] = (
    ("Analyzing", 15, "Programm wird durchgesehen …"),
    ("Processing", 40, "Bibliotheken werden eingesammelt …"),
    ("Building PYZ", 70, "Python-Code wird gepackt …"),
    ("Building PKG", 82, "Alles wird zusammengelegt …"),
    ("Building EXE", 92, "Die Exe wird geschrieben …"),
    ("Build complete", 100, "Fertig."),
)


@dataclass
class ExportErgebnis:
    erfolgreich: bool
    ausgabe_pfad: Path | None
    protokoll: str


def _daten_ordner_des_projekts(projekt: Projekt) -> list[Path]:
    """Die Unterordner, die mit in die Exe wandern.

    Absichtlich alles, was nicht ausdrücklich ausgenommen ist: wer einen
    Ordner `bilder/` anlegt und darauf zugreift, erwartet, dass das
    Programm auch beim Freund läuft - und nicht, dass er ihn vorher in
    einer Einstellung anmelden muss.
    """
    return sorted(
        p
        for p in projekt.ordner.iterdir()
        if p.is_dir() and p.name not in _NICHT_MITNEHMEN and not p.name.startswith(".")
    )


class _Fortschritt:
    """Reicht Phasenmeldungen weiter - aber nie rückwärts.

    PyInstaller arbeitet seine Phasen nicht sauber nacheinander ab: nach
    „Looking for ctypes DLLs" kommt noch einmal „Analyzing", und zwar
    mehrfach. Roh weitergereicht sprang der Balken in einem echten Lauf
    zwischen 15 % und 70 % hin und her - das sieht kaputt aus und ist
    schlimmer als gar kein Balken. Gemessen an einem echten Export
    (M14).
    """

    def __init__(self, melden: Callable[[int, str], None] | None) -> None:
        self._melden = melden
        self._hoechster = 0

    def __call__(self, prozent: int, text: str) -> None:
        if self._melden is None or prozent < self._hoechster:
            return
        self._hoechster = prozent
        self._melden(prozent, text)

    def zeile(self, zeile: str) -> None:
        for marke, prozent, text in _PHASEN:
            if zeile.startswith(marke) or f": {marke}" in zeile:
                self(prozent, text)
                return


def exe_exportieren(
    projekt: Projekt,
    ziel_ordner: Path | None = None,
    fortschritt: Callable[[int, str], None] | None = None,
) -> ExportErgebnis:
    """Baut `projekt` mit PyInstaller zu einer einzigen Exe.

    `ziel_ordner` ist der `--distpath` (Standard: `<projekt>/dist`).
    PyInstaller-eigene Zwischenstände (`build/`, `.spec`) landen in
    temporären Unterordnern und werden danach wieder entfernt, damit das
    Projekt sauber bleibt.

    `fortschritt` wird - falls angegeben - während des Baus mit
    `(prozent, text)` aufgerufen, damit die Oberfläche einen Ladebalken
    mitlaufen lassen kann. Ein Export dauert für ein Schulprojekt
    typischerweise eine halbe bis eine Minute; ohne Rückmeldung sieht
    das nach einem Absturz aus.
    """
    export_optionen = projekt.daten.get("export", {})
    dist_pfad = ziel_ordner if ziel_ordner is not None else projekt.ordner / "dist"
    arbeits_pfad = projekt.ordner / "_pyinstaller_build"
    spec_pfad = projekt.ordner / "_pyinstaller_spec"

    befehl = [
        *python_befehl(),
        "-m",
        "PyInstaller",
        "--noconfirm",
        # Eine Datei statt eines Ordners - der Kern der Sache.
        "--onefile",
        "--name",
        projekt.name,
        "--distpath",
        str(dist_pfad),
        "--workpath",
        str(arbeits_pfad),
        "--specpath",
        str(spec_pfad),
        "--add-data",
        f"{_DESIGN_ORDNER}{os.pathsep}design",
    ]

    for ordner in _daten_ordner_des_projekts(projekt):
        befehl += ["--add-data", f"{ordner}{os.pathsep}{ordner.name}"]

    if projekt.typ in _GUI_PROJEKTTYPEN:
        befehl.append("--windowed")
    symbol = export_optionen.get("icon")
    if symbol:
        befehl += ["--icon", str(projekt.ordner / symbol)]
    befehl.append(str(projekt.haupt_datei))

    melder = _Fortschritt(fortschritt)
    melder(5, "PyInstaller wird gestartet …")

    zeilen: list[str] = []
    lauf = subprocess.Popen(
        befehl,
        cwd=projekt.ordner,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    # Zeile für Zeile lesen statt am Ende auf einmal: nur so kann der
    # Ladebalken überhaupt mitlaufen.
    assert lauf.stdout is not None
    for zeile in lauf.stdout:
        zeilen.append(zeile)
        melder.zeile(zeile.strip())
    rueckgabe = lauf.wait()
    protokoll = "".join(zeilen)

    shutil.rmtree(arbeits_pfad, ignore_errors=True)
    shutil.rmtree(spec_pfad, ignore_errors=True)

    exe_pfad = dist_pfad / f"{projekt.name}.exe"

    if rueckgabe != 0:
        exe_pfad.unlink(missing_ok=True)
        return ExportErgebnis(False, None, protokoll)

    if not exe_pfad.is_file():
        # Auf anderen Systemen heißt die Datei ohne Endung.
        ohne_endung = dist_pfad / projekt.name
        if ohne_endung.is_file():
            exe_pfad = ohne_endung

    melder(100, "Fertig.")

    return ExportErgebnis(True, exe_pfad, protokoll)
