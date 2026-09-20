"""Baut die auslieferbare Natter-Installation - Vorstufe für den
Installer aus `tools/natter.iss` (Gewünscht: „Natter als Exe nur zum
Download auf z. B. einer Website, man installiert die Exe").

Seit M13 ist das kein eingefrorenes PyInstaller-Bundle mehr, sondern
eine gewöhnliche, verschiebbare Python-Installation, in die Natter mit
`pip install` hineingelegt wird. Nur so können die Paketverwaltung und
„Als Exe exportieren" in der ausgelieferten Fassung überhaupt arbeiten:
beide brauchen einen Python, den man auseinandernehmen kann (siehe
`docs/arbeitspakete/M13.md`). PyInstaller baut nur noch den schlanken
Starter `Natter.exe` aus `tools/launcher.py`.

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
Signing-Zertifikat (Gemeldet: „Weg A" gegen Windows Smart App
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
from tools.python_beschaffen import python_beschaffen

_PROJEKT_WURZEL = Path(__file__).resolve().parent.parent
_DESIGN_ORDNER = _PROJEKT_WURZEL / "design"
_SCHEMAS_ORDNER = _PROJEKT_WURZEL / "schemas"
_ICONS_ORDNER = _PROJEKT_WURZEL / "ide" / "assets" / "icons"
_TEMPLATES_ORDNER = _PROJEKT_WURZEL / "templates"
_ICON = _ICONS_ORDNER / "app.ico"
_STARTER_SKRIPT = Path(__file__).resolve().parent / "launcher.py"
_DIST_ORDNER = _PROJEKT_WURZEL / "dist"
_AUSGABE = _DIST_ORDNER / "Natter"
_BUILD_ORDNER = _PROJEKT_WURZEL / "_pyinstaller_build_ide"
_SPEC_ORDNER = _PROJEKT_WURZEL / "_pyinstaller_spec_ide"
_BEISPIEL_ORDNER = _PROJEKT_WURZEL / "beispielprojekte"
_DOCS_ORDNER = _PROJEKT_WURZEL / "docs"
_LIZENZ_VORLAGEN = Path(__file__).resolve().parent / "lizenz_vorlagen"
_SIGNIER_SKRIPT = Path(__file__).resolve().parent / "signieren" / "datei_signieren.ps1"
_MANIFEST_SCHLUESSEL = Path(__file__).resolve().parent / "signieren" / "manifest-privat.pem"

# Nur diese Laufzeit-Abhängigkeiten interessieren (nicht pytest oder
# pyinstaller selbst - die stecken nicht in der gebauten Exe).
#
# `ruff` steht seit M12 mit drin: es wird zwar nur als Unterprozess
# aufgerufen, liegt aber seither wirklich in der Exe (die Prüfung vor
# dem Start braucht es), und dann gehört auch sein Lizenztext dazu.
_LAUFZEIT_PAKETE = (
    "pyside6",
    "pyside6-essentials",
    "pyside6-addons",
    "jsonschema",
    "libcst",
    "debugpy",
    "ruff",
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


#: Was aus der mitgelieferten Python fliegt, weil Natter es nie
#: anfasst (Gewünscht: „Tk Inter kann komplett raus aus der
#: Installation").
#:
#: Tcl/Tk ist Pythons zweite Fenstertechnik - Natter baut jede
#: Oberfläche mit Qt, und `pcl` importiert `tkinter` nirgends. Mitgehen
#: würde es trotzdem, weil es zur Standardbibliothek gehört: rund 13 MB
#: im Installationsordner, davon 9 MB Tcl-Skripte und zwei DLLs von
#: zusammen 3,3 MB.
#:
#: Was damit auch geht: `turtle`. Die Schildkrötengrafik steckt auf
#: `tkinter` auf. Für Natter ist das folgerichtig - Zeichnen läuft über
#: `PaintBox` und `Canvas` (M15), und das Konzept sieht Ein- und Ausgabe
#: ausschließlich über `pcl`-Komponenten vor. Wer `import turtle`
#: schreibt, bekommt seit diesem Schritt einen ImportError statt eines
#: Fensters.
OHNE_TCL_TK = (
    "tcl",  # Ordner mit den Tcl/Tk-Skripten
    "Lib/tkinter",
    "Lib/turtledemo",
    "Lib/turtle.py",
    "DLLs/_tkinter.pyd",
    "DLLs/tcl86t.dll",
    "DLLs/tk86t.dll",
    "DLLs/tclive86t.dll",
    "DLLs/tkview86t.dll",
)


def _tcl_tk_entfernen(ziel: Path) -> int:
    """Räumt Tcl/Tk aus der Kopie. Liefert die eingesparten Bytes.

    Was es nicht gibt, wird übergangen: die Standalone-Python liefert je
    nach Fassung nicht immer dieselben Hilfs-DLLs mit, und ein Bau soll
    daran nicht scheitern.
    """
    gespart = 0
    for eintrag in OHNE_TCL_TK:
        pfad = ziel / Path(eintrag)
        if not pfad.exists():
            continue
        if pfad.is_dir():
            gespart += sum(
                datei.stat().st_size for datei in pfad.rglob("*") if datei.is_file()
            )
            shutil.rmtree(pfad)
        else:
            gespart += pfad.stat().st_size
            pfad.unlink()
    return gespart


def _python_bereitstellen() -> Path:
    """Kopiert die Standalone-CPython in den Ausgabeordner und liefert
    den Pfad zu ihrer `python.exe`."""
    ziel = _AUSGABE / "python"
    if ziel.exists():
        shutil.rmtree(ziel)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(python_beschaffen(), ziel)

    gespart = _tcl_tk_entfernen(ziel)
    if gespart:
        print(f"Tcl/Tk entfernt: {gespart / 1024 / 1024:.1f} MB gespart")

    # `uv` legt in seine Python-Installationen einen PEP-668-Vermerk
    # („extern verwaltet“), der jedes `pip install` ablehnt - richtig,
    # solange uv sie verwaltet. Diese Kopie hier gehört aber zu Natter,
    # und Natter verwaltet sie selbst. Bliebe der Vermerk liegen, wäre
    # die Paketverwaltung in der ausgelieferten Fassung wieder tot -
    # also genau das, was M13 beheben soll.
    vermerk = ziel / "Lib" / "EXTERNALLY-MANAGED"
    if vermerk.exists():
        vermerk.unlink()

    return ziel / "python.exe"


#: Umgebungsvariablen, die beim `pip install` in die mitgelieferte
#: Python weg müssen – sie alle zeigen auf eine *andere*
#: Python-Installation auf dem Baurechner.
#:
#: Der teuerste Eintrag ist `PYTHONUSERBASE`. Die gesetzt zu finden ist
#: auf einem Entwicklerrechner normal (hier von der Windows-Store-
#: Python), und sie wirkt an einer Stelle, an der man sie nicht sucht:
#: jede Python 3.13 rechnet ihr Benutzer-Paketverzeichnis daraus
#: aus, also auch die frisch ausgepackte in `dist`. Die sah dadurch die
#: Pakete des Baurechners als ihre eigenen; pip meldete Zeile für Zeile
#: „Requirement already satisfied“, installierte nur Natter selbst und
#: gab 0 zurück. Der Bau lief fehlerfrei durch – heraus kam eine
#: Auslieferung ohne `ruff`, `scipy`, `scikit-learn`, `cryptography`,
#: `setuptools` und ein Dutzend weiterer Pakete, und damit ohne Prüfung
#: vor dem Start, ohne Integritätsprüfung und ohne Exe-Export.
#:
#: Aufgefallen ist es erst beim Nachzählen der Pakete in der fertigen
#: Auslieferung, nicht am Bau (M13).
FREMDE_UMGEBUNG = ("PYTHONPATH", "PYTHONHOME", "PYTHONUSERBASE", "VIRTUAL_ENV")


def _saubere_umgebung() -> dict[str, str]:
    """Die Umgebung für einen `pip install` in die mitgelieferte Python.

    Entfernt die Variablen aus `FREMDE_UMGEBUNG` und schaltet das
    Benutzer-Paketverzeichnis ganz ab. Das Abschalten ist der Gürtel zum
    Hosenträger: `PYTHONUSERBASE` zu löschen genügt für diesen
    Baurechner, aber das Benutzerverzeichnis hat auch ohne sie einen
    Vorgabewert, und dort liegende Pakete würden denselben Schaden
    anrichten (M13).
    """
    umgebung = {
        name: wert
        for name, wert in os.environ.items()
        if name.upper() not in FREMDE_UMGEBUNG
    }
    umgebung["PYTHONNOUSERSITE"] = "1"
    return umgebung


def _gesperrte_versionen(ziel: Path) -> Path | None:
    """Schreibt die Versionen aus `uv.lock` als `requirements.txt`.

 Die Auslieferung muss das enthalten, was geprüft wurde. Bis
 stand hier schlicht `pip install <projekt>`, und pip
 löste die Abhängigkeiten frisch gegen PyPI auf. Herausgekommen ist
 eine Auslieferung mit Paketversionen, gegen die nie ein Test lief -
 real gemessen pandas 3.0.6 in `dist`, während die 3424 Tests gegen
 3.0.5 grün waren.

 Aufgefallen ist es an einer ganz anderen Stelle: Windows Smart App
 Control blockierte fünf der vierzehn `pandas._libs`-Bibliotheken
 („did not meet the Enterprise signing level requirements"). Eine
 Fassung, die erst seit Stunden auf PyPI liegt, hat bei Microsofts
 Reputationsdienst noch nichts vorzuweisen - die getestete, seit
 Wochen verbreitete dagegen schon.

 `uv export` liest `uv.lock`, also genau die Auflösung, gegen die
 entwickelt und getestet wird. Liefert `None`, wenn `uv` auf dem
 Baurechner fehlt; dann bleibt es beim bisherigen Weg, mit einer
 Warnung.
 """
    ergebnis = subprocess.run(
        [
            "uv",
            "export",
            "--format",
            "requirements-txt",
            "--no-dev",
            "--no-emit-project",
        ],
        cwd=_PROJEKT_WURZEL,
        capture_output=True,
        text=True,
    )
    if ergebnis.returncode != 0:
        meldung = ergebnis.stderr.strip().splitlines()[-1:] or ["uv nicht gefunden"]
        print(f"Warnung: Versionen nicht aus uv.lock übernommen ({meldung[0]})")
        return None

    datei = ziel / "requirements-auslieferung.txt"
    datei.write_text(ergebnis.stdout, encoding="utf-8")
    anzahl = sum(1 for zeile in ergebnis.stdout.splitlines() if "==" in zeile)
    print(f"Versionen aus uv.lock übernommen: {anzahl} Pakete")
    return datei


def _natter_installieren(python: Path) -> None:
    """Installiert Natter samt Abhängigkeiten in die mitgelieferte
    Python - ganz gewöhnlich mit `pip install`.

    Dadurch liegt dort alles so, wie es auch im Entwicklungsbaum liegt;
    `pip` und PyInstaller finden in der ausgelieferten Fassung eine
    Umgebung vor, mit der sie arbeiten können (M13).

    Zuerst die gesperrten Versionen (siehe `_gesperrte_versionen`),
    danach Natter selbst. Die Reihenfolge ist der Kern: was aus
    `uv.lock` kommt, steht dann schon da, und pip hat beim Auflösen von
    Natters eigenen Abhängigkeiten nichts mehr nachzuladen.
    """
    gesperrt = _gesperrte_versionen(python.parent)
    schritte: list[tuple[str, list[str]]] = []
    if gesperrt is not None:
        # `--require-hashes` greift von selbst, weil `uv export` die
        # Prüfsummen mitschreibt: ein unterwegs ausgetauschtes Paket
        # fällt damit beim Bau auf, nicht erst beim Schüler.
        schritte.append(("geprüfte Paketversionen", ["-r", str(gesperrt)]))
    schritte.append(("Natter", [str(_PROJEKT_WURZEL)]))
    # Für "Projekt -> Als Exe exportieren": PyInstaller gehört in die
    # ausgelieferte Umgebung, nicht nur in den Entwicklungsbaum. Steht
    # in `uv.lock` und kommt damit schon oben mit; der Schritt bleibt
    # als Netz für den Fall ohne `uv`.
    schritte.append(("PyInstaller", ["pyinstaller"]))

    for schritt, argumente in schritte:
        print(f"Installiere {schritt} in die mitgelieferte Python ...", flush=True)
        # Ausgabe bewusst nicht eingefangen: ein Bau, der Minuten
        # läuft, soll zeigen, wo er steht - und wenn etwas schiefgeht,
        # will man pips eigene Zeilen sehen.
        ergebnis = subprocess.run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--no-warn-script-location",
                "--disable-pip-version-check",
                *argumente,
            ],
            env=_saubere_umgebung(),
        )
        if ergebnis.returncode != 0:
            raise RuntimeError(
                f"pip install {schritt} fehlgeschlagen (Rückgabewert "
                f"{ergebnis.returncode}), siehe Ausgabe oben."
            )


def _datenordner_kopieren(python: Path) -> None:
    """Legt die zur Laufzeit gelesenen Ordner neben die Pakete.

    `ide/pfade.daten_ordner()` sucht sie eine Ebene über dem
    `ide`-Paket - im Entwicklungsbaum ist das die Projektwurzel, in der
    Installation `Lib/site-packages`. PyInstaller brauchte dafür
    `--add-data`; hier genügt Kopieren.
    """
    site_packages = python.parent / "Lib" / "site-packages"
    for quelle in (
        _DESIGN_ORDNER,
        _SCHEMAS_ORDNER,
        _TEMPLATES_ORDNER,
        _DOCS_ORDNER,
        _BEISPIEL_ORDNER,
    ):
        ziel = site_packages / quelle.name
        if ziel.exists():
            shutil.rmtree(ziel)
        shutil.copytree(quelle, ziel)


def _starter_bauen() -> None:
    """Baut `Natter.exe` aus `tools/launcher.py`.

    Eine eigene, kleine Exe statt einer Verknüpfung direkt auf
    `pythonw.exe`: so trägt das Programm sein eigenes Symbol, seine
    Versionsangabe und seine Signatur.
    """
    befehl = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name",
        "Natter",
        "--icon",
        str(_ICON),
        "--distpath",
        str(_DIST_ORDNER / "_starter"),
        "--workpath",
        str(_BUILD_ORDNER),
        "--specpath",
        str(_SPEC_ORDNER),
        str(_STARTER_SKRIPT),
    ]
    ergebnis = subprocess.run(befehl, cwd=_PROJEKT_WURZEL)
    shutil.rmtree(_BUILD_ORDNER, ignore_errors=True)
    shutil.rmtree(_SPEC_ORDNER, ignore_errors=True)
    if ergebnis.returncode != 0:
        raise RuntimeError("Der Bau des Starters ist fehlgeschlagen, siehe Ausgabe oben.")

    quelle = _DIST_ORDNER / "_starter" / "Natter.exe"
    shutil.copy2(quelle, _AUSGABE / "Natter.exe")
    shutil.rmtree(_DIST_ORDNER / "_starter", ignore_errors=True)


def _lizenzen_sammeln(ziel: Path) -> None:
    """Kopiert LGPL-3.0-Text + Qt-Hinweis sowie die von jedem Paket
    selbst mitgelieferten Lizenzdateien (`dist-info/licenses/…` bzw.
    `LICENSE*`/`COPYING*` im Paketordner) in `ziel`."""
    ziel.mkdir(parents=True, exist_ok=True)
    for datei in _LIZENZ_VORLAGEN.iterdir():
        # Die INSTALLER_*-Texte sind Seiten des Installers (Lizenz,
        # Hinweis vor der Installation), keine Lizenz einer Bibliothek -
        # sie gehören nicht in den Lizenzen-Ordner der Installation.
        if datei.name.startswith("INSTALLER_"):
            continue
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
    if _AUSGABE.exists():
        shutil.rmtree(_AUSGABE)
    python = _python_bereitstellen()
    _natter_installieren(python)
    _datenordner_kopieren(python)
    _starter_bauen()
    _lizenzen_sammeln(_AUSGABE / "Lizenzen")
    if signieren:
        _exe_signieren(_AUSGABE / "Natter.exe")
    _manifest_schreiben(_AUSGABE)
    return _AUSGABE


if __name__ == "__main__":
    ausgabe_ordner = paketieren()
    print(f"Natter gebaut nach: {ausgabe_ordner}")
