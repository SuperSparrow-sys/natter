"""Baut ein Natter-Projekt mit PyInstaller zu einer eigenständigen Exe
(Abschnitt 16 „Export“, 23.3 „Portabilität“; M8 Schritt 4).

Nutzt dieselbe portable Python-Umgebung wie die IDE selbst
(`sys.executable`, siehe `ide/run/starter.py`) – PyInstaller ist Teil
der normalen Abhängigkeiten (`pyproject.toml`), kein Extra-Download auf
dem Schüler-Rechner nötig. Standard ist die Ordner-Variante (kein
`--onefile`): startet zuverlässiger und schneller, siehe
`prototypes/s5_pyinstaller/README.md`. Die `export`-Einstellungen einer
`.natter`-Datei (`schemas/project.schema.json`) steuern Produktname,
Icon, ob ein `daten/`-Ordner mitkopiert wird, und ob am Ende ein
Ordner oder ein ZIP herauskommt.

Baut absichtlich nicht das Prüfsummen-Manifest/die Authenticode-Signatur
aus `prototypes/s6_signatur` mit ein – eine Signatur braucht ein
gekauftes Zertifikat, das ein Schulprojekt normalerweise nicht hat;
das bleibt ein bewusst manueller, optionaler Schritt für wer ihn
braucht, siehe `docs/arbeitspakete/M8.md`.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pcl
from ide.project import Projekt
from ide.run.interpreter import ist_gebaut

_GUI_PROJEKTTYPEN = {"gui", "gui_db"}

#: `pcl.theme` lädt `design/tokens.json` zur Laufzeit (Abschnitt 6) statt
#: es zu importieren – PyInstaller bindet daher nur den Python-Code
#: automatisch ein, nicht diese Datei. Ohne `--add-data` stürzt jede
#: exportierte Exe schon beim Start ab (siehe `pcl/theme/__init__.py`,
#: `_tokens_pfad_ermitteln`, das im Bundle unter `design/` danach sucht).
_DESIGN_ORDNER = Path(pcl.__file__).resolve().parent.parent / "design"


@dataclass
class ExportErgebnis:
    erfolgreich: bool
    ausgabe_pfad: Path | None
    protokoll: str


def exe_exportieren(projekt: Projekt, ziel_ordner: Path | None = None) -> ExportErgebnis:
    """Baut `projekt` mit PyInstaller. `ziel_ordner` ist der `--distpath`
    (Standard: `<projekt>/dist`). PyInstaller-eigene Zwischenstände
    (`build/`, `.spec`) landen in temporären Unterordnern und werden
    danach wieder entfernt, damit das Projekt sauber bleibt."""
    if ist_gebaut():
        # PyInstaller braucht eine vollständige Python-Installation samt
        # Paketordnern. Die `Natter.exe` hat ihren Python fest eingebaut
        # und kann ihn nicht wieder auseinandernehmen. Bis M12 rief der
        # Export `sys.executable` auf - in der Exe also sich selbst, und
        # es ging bloß ein zweites Natter-Fenster auf (M12).
        return ExportErgebnis(
            erfolgreich=False,
            ausgabe_pfad=None,
            protokoll=(
                "Der Exe-Export braucht eine eigene Python-Installation und steht "
                "in der installierten Natter-Version nicht zur Verfügung. Er "
                "funktioniert, wenn Natter aus dem Quelltext gestartet wird."
            ),
        )

    export_optionen = projekt.daten.get("export", {})
    dist_pfad = ziel_ordner if ziel_ordner is not None else projekt.ordner / "dist"
    arbeits_pfad = projekt.ordner / "_pyinstaller_build"
    spec_pfad = projekt.ordner / "_pyinstaller_spec"

    befehl = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
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
    if projekt.typ in _GUI_PROJEKTTYPEN:
        befehl.append("--windowed")
    symbol = export_optionen.get("icon")
    if symbol:
        befehl += ["--icon", str(projekt.ordner / symbol)]
    befehl.append(str(projekt.haupt_datei))

    ergebnis = subprocess.run(befehl, cwd=projekt.ordner, capture_output=True, text=True)
    protokoll = ergebnis.stdout + ergebnis.stderr

    shutil.rmtree(arbeits_pfad, ignore_errors=True)
    shutil.rmtree(spec_pfad, ignore_errors=True)

    if ergebnis.returncode != 0:
        shutil.rmtree(dist_pfad / projekt.name, ignore_errors=True)
        return ExportErgebnis(False, None, protokoll)

    ausgabe_ordner = dist_pfad / projekt.name

    if export_optionen.get("include_data_dir", False):
        daten_ordner = projekt.ordner / "daten"
        if daten_ordner.is_dir():
            shutil.copytree(daten_ordner, ausgabe_ordner / "daten", dirs_exist_ok=True)

    if export_optionen.get("target", "zip") == "zip":
        zip_pfad = _als_zip_packen(ausgabe_ordner)
        shutil.rmtree(ausgabe_ordner, ignore_errors=True)
        return ExportErgebnis(True, zip_pfad, protokoll)

    return ExportErgebnis(True, ausgabe_ordner, protokoll)


def _als_zip_packen(ordner: Path) -> Path:
    archiv = shutil.make_archive(
        str(ordner), "zip", root_dir=ordner.parent, base_dir=ordner.name
    )
    return Path(archiv)
