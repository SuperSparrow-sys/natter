"""Baut Natter selbst (nicht ein Schülerprojekt) mit PyInstaller zu
einer eigenständigen Exe - Vorstufe für den Installer aus
`tools/natter.iss` (Nutzer-Feedback September 2026: „Natter als Exe
nur zum Download auf z. B. einer Website, man installiert die Exe").

Anders als `ide/export/exporter.py` (baut ein in der laufenden IDE
offenes Schülerprojekt, Menü „Projekt → Als Exe exportieren") baut
dieses Skript die IDE selbst und läuft nie aus der laufenden IDE
heraus - reines Entwicklungswerkzeug für den Maintainer, siehe
`tools/README.md`-Konvention (kein Teil des gebauten `pcl`/`ide`-
Pakets, siehe `pyproject.toml`).

Sammelt zusätzlich die Lizenztexte der mitgelieferten Bibliotheken in
einen `Lizenzen`-Ordner neben `Natter.exe` (Abschnitt „Lizenz" der
Nutzeranfrage: PySide6/Qt steht unter LGPL-3.0, das verlangt u. a.
den Lizenztext beizulegen - siehe `tools/lizenz_vorlagen/`).

Signiert `Natter.exe` anschließend mit dem selbst erstellten Code-
Signing-Zertifikat (Nutzer-Feedback: „Weg A" gegen Windows Smart App
Control, siehe `tools/signieren/`) - ohne vorher per
`zertifikat_einrichten.ps1` erzeugtes Zertifikat wird das Signieren
übersprungen (Warnung statt Abbruch), damit ein Bau auch auf einem
Rechner ohne dieses Zertifikat funktioniert. Der Installer
(`tools/natter.iss`) muss danach separat signiert werden, siehe
`tools/signieren/README.md`.

Beispiel:
    uv run python -m tools.ide_paketieren
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from importlib.metadata import distributions
from pathlib import Path

from ide.integritaet import manifest_schreiben

_PROJEKT_WURZEL = Path(__file__).resolve().parent.parent
_DESIGN_ORDNER = _PROJEKT_WURZEL / "design"
_SCHEMAS_ORDNER = _PROJEKT_WURZEL / "schemas"
_ICONS_ORDNER = _PROJEKT_WURZEL / "ide" / "assets" / "icons"
_ICON = _ICONS_ORDNER / "app.ico"
_HAUPTSKRIPT = _PROJEKT_WURZEL / "ide" / "__main__.py"
_DIST_ORDNER = _PROJEKT_WURZEL / "dist"
_AUSGABE = _DIST_ORDNER / "Natter"
_BUILD_ORDNER = _PROJEKT_WURZEL / "_pyinstaller_build_ide"
_SPEC_ORDNER = _PROJEKT_WURZEL / "_pyinstaller_spec_ide"
_LIZENZ_VORLAGEN = Path(__file__).resolve().parent / "lizenz_vorlagen"
_SIGNIER_SKRIPT = Path(__file__).resolve().parent / "signieren" / "datei_signieren.ps1"
_MANIFEST_SCHLUESSEL = Path(__file__).resolve().parent / "signieren" / "manifest-privat.pem"

# Nur diese Laufzeit-Abhängigkeiten interessieren (nicht pytest/ruff/
# pyinstaller selbst - die stecken nicht in der gebauten Exe).
_LAUFZEIT_PAKETE = (
    "pyside6",
    "pyside6-essentials",
    "pyside6-addons",
    "jsonschema",
    "libcst",
    "debugpy",
    "pymysql",
    "sqlalchemy",
    "pandas",
    "numpy",
    "openpyxl",
    "matplotlib",
    # M10: scikit-learn liegt bei, damit Fortgeschrittene damit arbeiten
    # können; Natter selbst rechnet die Regression über numpy. scipy,
    # joblib und threadpoolctl kommen als seine Abhängigkeiten mit -
    # alle vier stehen unter BSD-3 und müssen ihren Lizenztext beilegen.
    "scikit-learn",
    "scipy",
    "joblib",
    "threadpoolctl",
)


def _pyinstaller_bauen() -> None:
    befehl = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--windowed",
        "--name",
        "Natter",
        "--icon",
        str(_ICON),
        "--distpath",
        str(_DIST_ORDNER),
        "--workpath",
        str(_BUILD_ORDNER),
        "--specpath",
        str(_SPEC_ORDNER),
        "--add-data",
        f"{_DESIGN_ORDNER}{os.pathsep}design",
        "--add-data",
        f"{_SCHEMAS_ORDNER}{os.pathsep}schemas",
        # ide/assets/symbole.py liest Symbole über einen quellcode-
        # relativen Pfad (Path(__file__).resolve().parent / "icons"),
        # nicht über einen Import - PyInstaller bindet solche
        # Datendateien nie automatisch ein (dieselbe Art Fund wie bei
        # design/tokens.json und schemas/*.json). Ziel entspricht
        # exakt dem Paketpfad, damit __file__ im gebauten Bundle
        # weiterhin dorthin zeigt.
        "--add-data",
        f"{_ICONS_ORDNER}{os.pathsep}ide/assets/icons",
        # scikit-learn kommt sonst gar nicht mit. Nachgemessen (M10):
        # steht es nur in pyproject.toml, zieht PyInstaller allein
        # `scipy` hinein - weil numpy/matplotlib es über ihre Hooks
        # finden -, und die Exe wächst um 70 MB, ohne dass `import
        # sklearn` im gebauten Programm funktioniert. Das wäre das
        # Schlechteste aus beiden Welten: der Platz weg, der Nutzen
        # nicht da. Natter selbst braucht sklearn nicht (die Regression
        # rechnet über numpy.polyfit); es liegt für Fortgeschrittene
        # bei, so wie im Arbeitspaket M10 entschieden.
        "--collect-all",
        "sklearn",
        "--collect-all",
        "joblib",
        "--collect-all",
        "threadpoolctl",
        str(_HAUPTSKRIPT),
    ]
    ergebnis = subprocess.run(befehl, cwd=_PROJEKT_WURZEL)
    shutil.rmtree(_BUILD_ORDNER, ignore_errors=True)
    shutil.rmtree(_SPEC_ORDNER, ignore_errors=True)
    if ergebnis.returncode != 0:
        raise RuntimeError("PyInstaller-Build fehlgeschlagen, siehe Ausgabe oben.")


def _lizenzen_sammeln(ziel: Path) -> None:
    """Kopiert LGPL-3.0-Text + Qt-Hinweis sowie die von jedem Paket
    selbst mitgelieferten Lizenzdateien (`dist-info/licenses/…` bzw.
    `LICENSE*`/`COPYING*` im Paketordner) in `ziel`."""
    ziel.mkdir(parents=True, exist_ok=True)
    for datei in _LIZENZ_VORLAGEN.iterdir():
        shutil.copy2(datei, ziel / datei.name)

    gesehen: set[str] = set()
    for dist in distributions():
        name = (dist.metadata["Name"] or "").strip()
        normalisiert = name.lower().replace("_", "-")
        if not name or normalisiert in gesehen or normalisiert not in _LAUFZEIT_PAKETE:
            continue
        gesehen.add(normalisiert)

        paket_ordner = ziel / name
        dateien = dist.files or []
        gefunden = False
        for eintrag in dateien:
            dateiname = Path(str(eintrag)).name
            if not dateiname.upper().startswith(("LICENSE", "LICENCE", "COPYING", "NOTICE")):
                continue
            quelle = dist.locate_file(eintrag)
            if quelle is None or not Path(quelle).is_file():
                continue
            paket_ordner.mkdir(exist_ok=True)
            shutil.copy2(Path(quelle), paket_ordner / dateiname)
            gefunden = True
        if not gefunden:
            lizenzfeld = dist.metadata.get("License", "unbekannt")
            paket_ordner.mkdir(exist_ok=True)
            (paket_ordner / "LIZENZ_HINWEIS.txt").write_text(
                f"{name}: keine eigene Lizenzdatei im Paket gefunden.\n"
                f"Laut Paket-Metadaten: {lizenzfeld}\n"
                f"Siehe https://pypi.org/project/{name}/ für Details.\n",
                encoding="utf-8",
            )

    fehlend = set(_LAUFZEIT_PAKETE) - gesehen
    if fehlend:
        print(f"Warnung: keine Lizenzinformation gefunden für: {sorted(fehlend)}")


def _exe_signieren(datei: Path) -> None:
    """Signiert `datei` mit dem selbst erstellten Zertifikat (siehe
    `tools/signieren/zertifikat_einrichten.ps1`). Kein Abbruch des
    Baus, falls kein Zertifikat vorhanden ist - nur eine Warnung, die
    unsignierte Exe funktioniert weiterhin (nur ggf. von Windows Smart
    App Control blockiert, siehe `tools/signieren/README.md`)."""
    ergebnis = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(_SIGNIER_SKRIPT),
            "-Datei",
            str(datei),
        ],
        capture_output=True,
        text=True,
    )
    if ergebnis.returncode != 0:
        meldung = ergebnis.stderr.strip() or ergebnis.stdout.strip()
        print(f"Warnung: Signieren übersprungen ({meldung})")
        return
    print(ergebnis.stdout.strip())


def _manifest_schreiben(ordner: Path) -> None:
    """Signiertes Prüfsummen-Manifest über den fertigen Programmordner
    (Abschnitt 17.8). Muss nach dem Signieren laufen, weil die
    Authenticode-Signatur die Bytes von `Natter.exe` verändert - sonst
    meldet schon der erste Start eine veränderte Datei. Ohne privaten
    Schlüssel nur eine Warnung, wie beim Signieren auch."""
    if not _MANIFEST_SCHLUESSEL.exists():
        print(
            f"Warnung: Prüfsummen-Manifest übersprungen ({_MANIFEST_SCHLUESSEL.name} fehlt - "
            "einmalig mit tools/signieren/manifest_schluessel_erzeugen.py anlegen)"
        )
        return
    ziel = manifest_schreiben(ordner, _MANIFEST_SCHLUESSEL)
    print(f"Prüfsummen-Manifest geschrieben: {ziel}")


def paketieren(*, signieren: bool = True) -> Path:
    _pyinstaller_bauen()
    _lizenzen_sammeln(_AUSGABE / "Lizenzen")
    if signieren:
        _exe_signieren(_AUSGABE / "Natter.exe")
    _manifest_schreiben(_AUSGABE)
    return _AUSGABE


if __name__ == "__main__":
    ausgabe_ordner = paketieren()
    print(f"Natter gebaut nach: {ausgabe_ordner}")
