"""Baut ein Natter-Projekt mit PyInstaller zu einer einzigen Exe
(README.md, Abschnitt 16 „Export"; M8 Schritt 4, M14).

Nutzt dieselbe Python-Umgebung wie die IDE selbst (`python_befehl`,
siehe `ide/run/interpreter.py`) - PyInstaller liegt der Auslieferung bei
(siehe `tools/ide_paketieren.py`), es ist kein Extra-Download auf dem
Schüler-Rechner nötig.

Eine Datei, kein Ordner (Vorgabe: „es darf
keinen extra Ordner geben, das ganze Programm soll in der exe sein").
Bis dahin baute Natter die Ordner-Variante und packte sie in ein ZIP.
Das ist technisch der robustere Weg, aber für den Zweck der falsche: wer
sein Spiel einem Freund schickt, schickt eine Datei und keine
Anleitung zum Entpacken. Alles, was das Projekt braucht - auch die
Unterordner `daten/`, `bilder/`, `assets/` -, wandert dafür in die
Exe; zur Laufzeit packt PyInstaller sie neben das Skript aus, sodass
`Path(__file__).parent / "bilder"` weiter stimmt. Dasselbe gilt für
Dateien, die direkt im Projektordner liegen, etwa eine `noten.csv`.

Zum Lesen reicht das, zum Schreiben nicht: der Auspackordner liegt
unter `%TEMP%` und wird beim Beenden gelöscht. Eine Datenbank, die
das Programm mit `Path(__file__).parent / "konten.sqlite"` anlegt,
wäre beim nächsten Start leer. Die Exe setzt deshalb beim Start ihr
Arbeitsverzeichnis auf den Ordner, in dem sie liegt
(`_ARBEITSORDNER_HOOK`). Ein Programm, das mit einem relativen Pfad
wie `Path("konten.sqlite")` schreibt, legt die Datei damit neben der
Exe ab, und in Natter, das jedes Programm im Projektordner startet,
im Projektordner. Die Beispiele 06 und 07 schreiben auf diese Weise.

Der Preis ist ein spürbar langsamerer Start (die Exe entpackt sich bei
jedem Lauf) und eine größere Datei. Beides ist hier das kleinere Übel.

Mitgenommen wird nur, was das Projekt wirklich braucht (September
2026, Auftrag: „Schaue wie ich den Export eines Programms als exe
schneller hinbekommen aber trotzdem als Stand alone Datei"). Vorher bekam
jedes Projekt dasselbe Paket: ein Taschenrechner mit vier Knöpfen wog
genauso viel wie das Machine-Learning-Beispiel, nämlich 120,2 MB, und
der Bau dauerte 110 Sekunden. Der Grund ist PyInstaller selbst - es
folgt auch Importen, die tief in einer Funktion stehen, und `pcl` führt
für `Chart` und `regression` numpy, matplotlib und pandas mit. Wer kein
Diagramm zeichnet, schleppt sie trotzdem mit.

`_ueberfluessige_pakete` sieht deshalb in den Quelltexten des Projekts
nach, welche dieser Pakete überhaupt vorkommen, und schließt die
übrigen mit `--exclude-module` aus. Für den Taschenrechner sind das
51 Sekunden und 44,9 MB - weniger als die Hälfte der Zeit und gut
ein Drittel der Größe, bei unverändert einer einzigen Datei. Wer ein
Diagramm oder scikit-learn benutzt, bekommt alles Nötige nach wie vor.

Das Prüfsummen-Manifest kommt nicht mit hinein: es schützt Natter
selbst, nicht das Programm einer Schülerin. Signiert wird die fertige
Exe über `ide/export/signatur.py`.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pcl
from ide.export.signatur import signieren_wenn_moeglich
from ide.project import Projekt
from ide.project.projekt import (
    dateien_im_ordner,
    enthaelt_verknuepfung,
    ist_reiner_dateiname,
    ist_verknuepfung,
)
from ide.project.sicherung import ENDUNG as SICHERUNG_ENDUNG
from ide.prozess import ohne_konsole
from ide.run.interpreter import python_befehl
from ide.schema import json_datei_lesen

_GUI_PROJEKTTYPEN = {"gui"}

#: Pakete, die nur dann in die Exe wandern, wenn das Projekt sie braucht -
#: und die Wörter, an denen sich das im Quelltext erkennen lässt.
#:
#: Die Zuordnung ist bewusst großzügig: taucht eines der Wörter irgendwo
#: in einer `.py` des Projekts auf, bleibt das Paket drin. Ein zu großes
#: Paket kostet Sekunden, ein fehlendes kostet ein Programm, das beim
#: Freund nicht startet. `u_*_design.py` wird mitgelesen - dort steht
#: `Chart(self)`, wenn im Designer ein Diagramm liegt.
#:
#: `numpy` und `pandas` hängen an `Chart`, weil `pcl/components/chart.py`
#: beide importiert; `scipy` und `joblib` hängen an scikit-learn, das sie
#: mitbringt.
_OPTIONALE_PAKETE: dict[str, tuple[str, ...]] = {
    "matplotlib": ("matplotlib", "pyplot", "Chart"),
    "numpy": ("numpy", "Chart", "regression", "sklearn", "pandas", "DataFrame"),
    "pandas": ("pandas", "DataFrame", "to_dataframe", "Chart", "sklearn"),
    "sklearn": ("sklearn", "scikit"),
    "scipy": ("scipy", "sklearn"),
    "joblib": ("joblib", "sklearn"),
    "openpyxl": ("openpyxl", "xlsx"),
    "sqlalchemy": ("sqlalchemy",),
    "PIL": ("PIL", "Pillow"),
    # Werkzeuge der IDE. `pcl` fasst sie nie an, sie liegen nur in
    # derselben Python-Umgebung.
    "debugpy": ("debugpy",),
    "libcst": ("libcst",),
    "jedi": ("jedi",),
    "IPython": ("IPython",),
    "tkinter": ("tkinter",),
    "pytest": ("pytest",),
}

#: Welche der optionalen Pakete ein anderes zum Laufen braucht. Die
#: Stichwörter oben erfassen das nicht vollständig: `to_dataframe()`
#: holt pandas herein, nennt numpy aber nirgends, und ohne numpy
#: bricht pandas schon beim Import ab. Bleibt ein Paket drin, bleiben
#: deshalb auch die Pakete drin, die hier bei ihm stehen.
_BRAUCHT: dict[str, tuple[str, ...]] = {
    "pandas": ("numpy",),
    "matplotlib": ("numpy", "PIL"),
    "scipy": ("numpy",),
    "sklearn": ("numpy", "scipy", "joblib"),
}

#: `pcl.theme` lädt `design/tokens.json` zur Laufzeit (Abschnitt 6) statt
#: es zu importieren – PyInstaller bindet daher nur den Python-Code
#: automatisch ein, nicht diese Datei. Ohne `--add-data` stürzt jede
#: exportierte Exe schon beim Start ab (siehe `pcl/theme/__init__.py`,
#: `_tokens_pfad_ermitteln`, das im Bundle unter `design/` danach sucht).
_DESIGN_ORDNER = Path(pcl.__file__).resolve().parent.parent / "design"

#: Wird der Exe als PyInstaller-Laufzeithaken mitgegeben und läuft
#: beim Start vor dem Programm: das Arbeitsverzeichnis wird der Ordner
#: der Exe. Was das Programm mit relativem Pfad schreibt, bleibt so
#: neben der Exe liegen, statt im Auspackordner mit gelöscht zu werden.
#: Auch ein Start über eine Verknüpfung oder aus einem anderen Ordner
#: landet damit an derselben Stelle.
_ARBEITSORDNER_HOOK = """import os
import sys

if getattr(sys, "frozen", False):
    try:
        os.chdir(os.path.dirname(os.path.abspath(sys.executable)))
    except OSError:
        pass
"""

#: Dateien im Projektordner, die nicht als Daten mitwandern: der
#: Quelltext geht als übersetzter Code in die Exe, der Rest wird nur in
#: Natter gebraucht. Dazu gehört die Sicherung ungespeicherter
#: Änderungen (Punkt 344).
_KEINE_DATEN = {
    ".py", ".pyw", ".pyc", ".natter", ".pfm", ".pdiag", ".spec",
    SICHERUNG_ENDUNG,
}

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
#: „Looking for …" steht bewusst nicht in der Liste, obwohl es
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
        if p.is_dir()
        and not ist_verknuepfung(p)
        and p.name not in _NICHT_MITNEHMEN
        and not p.name.startswith(".")
    )


def _daten_dateien_des_projekts(projekt: Projekt) -> list[Path]:
    """Die Dateien direkt im Projektordner, die mit in die Exe wandern.

    Eine `noten.csv` neben `main.py` gehört genauso zum Programm wie ein
    Ordner `daten/`. Ausgenommen sind Quelltext und Projektdateien von
    Natter (`_KEINE_DATEN`) und versteckte Dateien.
    """
    return sorted(
        p
        for p in projekt.ordner.iterdir()
        if p.is_file()
        and not ist_verknuepfung(p)
        and p.suffix.lower() not in _KEINE_DATEN
        and not p.name.startswith(".")
    )


def _symbol_des_projekts(projekt: Projekt) -> Path | None:
    """Das Symbol, das die Exe tragen soll, oder `None`.

    Es ist das `icon` des Hauptformulars, dasselbe Bild, das im
    laufenden Programm in der Titelleiste steht. Eingestellt wird es im
    Objektinspektor. Eine ältere Projektdatei kann das Symbol noch
    unter `export.icon` nennen; diese Angabe geht vor.

    Ein Bild, das es nicht gibt, wird übergangen: PyInstaller bräche
    sonst den ganzen Bau ab, und eine Exe mit dem Standardsymbol ist
    das kleinere Übel. PNG und andere Formate wandelt PyInstaller
    selbst in ein Windows-Symbol um.
    """
    angabe = projekt.daten.get("export", {}).get("icon")
    if not angabe and ist_reiner_dateiname(projekt.haupt_unit):
        pfm = projekt.ordner / f"{projekt.haupt_unit}.pfm"
        try:
            formular = json_datei_lesen(pfm)
            angabe = formular.get("properties", {}).get("icon")
        except (OSError, ValueError, AttributeError):
            angabe = None
    if not angabe or not isinstance(angabe, str):
        return None
    pfad = projekt.ordner / angabe
    if not _liegt_in(pfad, projekt.ordner):
        return None
    return pfad if pfad.is_file() else None


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


def _ueberfluessige_pakete(projekt: Projekt) -> list[str]:
    """Die Pakete aus `_OPTIONALE_PAKETE`, die in diesem Projekt nirgends
    vorkommen - sie bleiben draußen.

    Gelesen werden alle `.py` des Projekts, auch die erzeugten: im
    `u_*_design.py` steht `Chart(self)`, wenn im Designer ein Diagramm
    liegt, und im Quelltext der Schülerin steht `import sklearn`, wenn
    sie es benutzt.
    """
    quelltext = ""
    for datei in dateien_im_ordner(projekt.ordner):
        if datei.suffix != ".py" or any(
            teil in _NICHT_MITNEHMEN for teil in datei.parts
        ):
            continue
        try:
            quelltext += datei.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            # Eine unlesbare Datei ist kein Grund, den Export abzubrechen -
            # im Zweifel wird eben mehr mitgenommen.
            return []
    gebraucht = {
        paket
        for paket, woerter in _OPTIONALE_PAKETE.items()
        if any(wort in quelltext for wort in woerter)
    }
    offen = list(gebraucht)
    while offen:
        for abhaengig in _BRAUCHT.get(offen.pop(), ()):
            if abhaengig not in gebraucht:
                gebraucht.add(abhaengig)
                offen.append(abhaengig)
    return [paket for paket in _OPTIONALE_PAKETE if paket not in gebraucht]


def _laeuft_noch(exe_pfad: Path) -> str | None:
    """Prüft, ob die Ziel-Exe gerade läuft. Liefert eine deutsche
    Meldung, wenn ja, sonst `None`.

    Der häufigste Fall überhaupt: exportieren, ausprobieren, etwas
    ändern, wieder exportieren - und das Programm von vorhin steht
    noch offen. Windows sperrt die Datei dann, PyInstaller scheitert
    mit einer englischen Meldung irgendwo im Protokoll, und Natter flog
    beim Aufräumen mit einem `PermissionError` heraus. Im Durchgang
    durch den Schülerweg genau so passiert.

    Geprüft wird durch Öffnen zum Schreiben - der einzige Weg, der
    ohne zusätzliche Windows-Bibliothek auskommt und nichts kaputt
    macht.
    """
    if not exe_pfad.is_file():
        return None
    try:
        with exe_pfad.open("ab"):
            return None
    except OSError:
        return (
            f"„{exe_pfad.name}“ läuft gerade noch und lässt sich deshalb nicht "
            f"überschreiben.\n\nBitte das Programm schließen und den Export "
            f"noch einmal starten."
        )


def _liegt_in(pfad: Path, ordner: Path) -> bool:
    try:
        return pfad.resolve().is_relative_to(ordner.resolve())
    except (OSError, ValueError):
        return False


def _pfade_ausserhalb(projekt: Projekt, dist_pfad: Path) -> str | None:
    """Eine Meldung, wenn Exe oder Startdatei nicht dort liegen, wo sie
    hingehören, sonst `None` (Punkt 250).

    `Projekt.laden` lehnt solche Namen schon ab. Ein `Projekt` lässt
    sich aber auch ohne Laden bauen, und bevor hier etwas geschrieben,
    signiert oder gelöscht wird, zählt nur, wohin die Pfade wirklich
    zeigen: die Exe in den Zielordner, die Startdatei in den
    Projektordner.
    """
    name = projekt.daten.get("name")
    exe_pfad = dist_pfad / f"{name}.exe"
    if not ist_reiner_dateiname(name) or exe_pfad.resolve().parent != (
        dist_pfad.resolve()
    ):
        return (
            f"Der Projektname „{name}“ taugt nicht als Name der Exe: er "
            "führt aus dem Zielordner hinaus. Exportiert wird nichts."
        )
    haupt = projekt.daten.get("main")
    if not ist_reiner_dateiname(haupt) or not _liegt_in(
        projekt.ordner / str(haupt), projekt.ordner
    ):
        return (
            f"Die Startdatei „{haupt}“ liegt nicht im Projektordner. "
            "Exportiert wird nichts."
        )
    return None


def exe_exportieren(
    projekt: Projekt,
    ziel_ordner: Path | None = None,
    fortschritt: Callable[[int, str], None] | None = None,
    prozess_gestartet: Callable[[subprocess.Popen], None] | None = None,
    vor_dem_anlegen: Callable[[], None] | None = None,
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

    `prozess_gestartet` bekommt den Prozess von PyInstaller gleich nach
    dem Start, damit ihn das Hauptfenster beim Schließen beenden kann
    (Punkt 254). Endet er so, räumt der Export wie nach jedem anderen
    Fehlschlag auf.

    `vor_dem_anlegen` geht an `signieren_wenn_moeglich` weiter und
    läuft, bevor Natter ein Zertifikat anlegt und Windows dazu fragt
    (Punkt 350).
    """
    dist_pfad = ziel_ordner if ziel_ordner is not None else projekt.ordner / "dist"
    arbeits_pfad = projekt.ordner / "_pyinstaller_build"
    spec_pfad = projekt.ordner / "_pyinstaller_spec"

    abgelehnt = _pfade_ausserhalb(projekt, dist_pfad)
    if abgelehnt is not None:
        return ExportErgebnis(False, None, abgelehnt)

    gesperrt = _laeuft_noch(dist_pfad / f"{projekt.name}.exe")
    if gesperrt is not None:
        return ExportErgebnis(False, None, gesperrt)

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
        if not enthaelt_verknuepfung(ordner):
            befehl += ["--add-data", f"{ordner}{os.pathsep}{ordner.name}"]
            continue
        # PyInstaller folgte einer Junction darin und nähme fremde
        # Dateien mit (Punkt 252). Dann einzeln, ohne die Verknüpfung.
        for datei in dateien_im_ordner(ordner):
            ziel = Path(ordner.name, *datei.relative_to(ordner).parent.parts)
            befehl += ["--add-data", f"{datei}{os.pathsep}{ziel}"]
    for datei in _daten_dateien_des_projekts(projekt):
        befehl += ["--add-data", f"{datei}{os.pathsep}."]

    spec_pfad.mkdir(parents=True, exist_ok=True)
    haken = spec_pfad / "natter_arbeitsordner.py"
    haken.write_text(_ARBEITSORDNER_HOOK, encoding="utf-8")
    befehl += ["--runtime-hook", str(haken)]

    for paket in _ueberfluessige_pakete(projekt):
        befehl += ["--exclude-module", paket]

    if projekt.typ in _GUI_PROJEKTTYPEN:
        befehl.append("--windowed")
    symbol = _symbol_des_projekts(projekt)
    if symbol is not None:
        befehl += ["--icon", str(symbol)]
    befehl.append(str(projekt.haupt_datei))

    melder = _Fortschritt(fortschritt)
    melder(5, "PyInstaller wird gestartet …")

    zeilen: list[str] = []
    lauf = subprocess.Popen(
        befehl,
        **ohne_konsole(
            cwd=projekt.ordner,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        ),
    )
    if prozess_gestartet is not None:
        prozess_gestartet(lauf)
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
        try:
            exe_pfad.unlink(missing_ok=True)
        except OSError as fehler:
            # Aufräumen ist eine Höflichkeit, kein Selbstzweck. Ist die
            # Datei gesperrt, weil das Programm noch läuft, flog hier
            # ein `PermissionError` bis nach oben durch - der Export
            # stürzte ab, statt seinen Fehlschlag zu melden.
            protokoll += f"\nDie alte Exe ließ sich nicht entfernen: {fehler}"
        return ExportErgebnis(False, None, protokoll)

    if not exe_pfad.is_file():
        # Auf anderen Systemen heißt die Datei ohne Endung.
        ohne_endung = dist_pfad / projekt.name
        if ohne_endung.is_file():
            exe_pfad = ohne_endung

    # Signieren, sofern auf diesem Rechner ein Zertifikat liegt.
    # Ohne Signatur nennt Windows die Exe in jedem Dialog
    # „Unbekannter Herausgeber", und eine nachträgliche Veränderung
    # fiele niemandem auf. Gegen eine eingeschaltete intelligente
    # App-Steuerung hilft die Signatur nicht; warum nicht, steht in
    # `ide/export/signatur.py`. Natters eigener Schlüssel liegt
    # ausdrücklich nicht in der Auslieferung.
    melder(98, "Signieren …")
    # `anlegen=True`: findet sich auf dem Rechner kein Zertifikat,
    # legt Natter eines an. Sonst käme aus jedem Export ein Programm
    # ohne erkennbare Herkunft heraus.
    #
    # Der Eingriff bleibt so klein wie möglich: das Zertifikat gilt
    # für das angemeldete Konto, sein Schlüssel ist nicht
    # exportierbar, und es beglaubigt nur, was auf diesem Rechner
    # gebaut wurde. Zurücknehmen lässt es sich in der
    # Zertifikatsverwaltung unter „Natter Programme dieses Rechners".
    signatur = signieren_wenn_moeglich(
        exe_pfad, anlegen=True, vor_dem_anlegen=vor_dem_anlegen
    )
    protokoll += f"\n{signatur.grund}"

    melder(100, "Fertig.")

    return ExportErgebnis(True, exe_pfad, protokoll)
