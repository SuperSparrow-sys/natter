"""Baut die auslieferbare Natter-Installation - Vorstufe für den
Installer aus `tools/natter.iss` (Gewünscht: „Natter als Exe nur zum
Download auf z. B. einer Website, man installiert die Exe").

Seit M13 ist das kein eingefrorenes PyInstaller-Bundle mehr, sondern
eine gewöhnliche, verschiebbare Python-Installation, in die Natter mit
`pip install` hineingelegt wird. Nur so können die Paketverwaltung und
„Als Exe exportieren" in der ausgelieferten Fassung überhaupt arbeiten:
beide brauchen einen Python, den man auseinandernehmen kann (siehe
Arbeitspaket M13). PyInstaller baut nur noch den schlanken
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

import hashlib
import os
import re
import shutil
import subprocess
import sys
from importlib.metadata import distributions
from pathlib import Path

from ide.integritaet import manifest_schreiben
from tools.fortschritt import KonsolenMelder, ausfuehren
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

#: Aus `docs/` kommen nur die Seiten mit, die die IDE zur Laufzeit
#: oeffnet: "Hilfe -> Erste Schritte" und die Komponenten-Referenz
#: (`ide/shell/hauptfenster.py`, `_hilfedatei_zeigen`). Alles
#: uebrige in `docs/` sind Planungsunterlagen - `PLAN.md`,
#: `entwicklung.md` und die Arbeitspakete -, die auf einem
#: Schulrechner nichts verloren haben. Bis September 2026 wurde der
#: Ordner vollstaendig kopiert, und damit lag die halbe
#: Projektplanung in jeder Installation.
_HILFESEITEN = ("erste_schritte.md", "komponenten.md")
_LIZENZ_VORLAGEN = Path(__file__).resolve().parent / "lizenz_vorlagen"
#: Natters eigene Lizenz. Die Lizenzseite des Installers verweist auf
#: sie, deshalb liegt sie im Programmordner.
_NATTER_LIZENZ = _PROJEKT_WURZEL / "LICENSE"
_SIGNIER_SKRIPT = Path(__file__).resolve().parent / "signieren" / "datei_signieren.ps1"
_ALLES_SIGNIEREN = Path(__file__).resolve().parent / "signieren" / "alles_signieren.ps1"
_MANIFEST_SCHLUESSEL = Path(__file__).resolve().parent / "signieren" / "manifest-privat.pem"

#: Was Windows lädt und deshalb signiert sein muss. Dieselbe Liste
#: steht in `tools/signieren/alles_signieren.ps1`, und Schritt 10 von
#: `tools/auslieferung_bauen.py` prüft genau diese Endungen;
#: `tests/test_auslieferung_bauen.py` hält die beiden zusammen.
SIGNIERTE_ENDUNGEN = (".exe", ".dll", ".pyd", ".sys", ".cat", ".ocx")

#: Die signierten Fassungen unveränderter Dateien, siehe
#: `_signieren_mit_zwischenspeicher`.
_SIGNATUR_ABLAGE = _PROJEKT_WURZEL / "build" / "bau-cache" / "signaturen"

#: Wohin Ausgaben und Fortschritt gehen. `paketieren()` setzt ihn; ohne
#: Anzeige schreibt er wie früher in die Konsole.
_melder: object = KonsolenMelder()

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
        _melder.zeile(f"Tcl/Tk entfernt: {gespart / 1024 / 1024:.1f} MB gespart")

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
        _melder.zeile(f"Warnung: Versionen nicht aus uv.lock übernommen ({meldung[0]})")
        return None

    datei = ziel / "requirements-auslieferung.txt"
    datei.write_text(ergebnis.stdout, encoding="utf-8")
    anzahl = sum(1 for zeile in ergebnis.stdout.splitlines() if "==" in zeile)
    _melder.zeile(f"Versionen aus uv.lock übernommen: {anzahl} Pakete")
    return datei


def _pakete_zaehlen(gesamt: int):  # noqa: ANN202
    """Zählt die Pakete, die pip meldet, für den Balken."""
    geholt = 0

    def auswerten(zeile: str) -> None:
        nonlocal geholt
        if gesamt and zeile.startswith(("Collecting ", "Requirement already satisfied")):
            geholt += 1
            _melder.stand(min(geholt, gesamt), gesamt, "Pakete")

    return auswerten


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

    # Für den Balken: wie viele Pakete pip anfassen wird. Jede Zeile in
    # der Liste, die mit einem Paketnamen beginnt, ist eines; darunter
    # stehen eingerückt die Prüfsummen.
    anzahl = 0
    if gesperrt is not None:
        anzahl = sum(
            1
            for zeile in gesperrt.read_text(encoding="utf-8").splitlines()
            if re.match(r"[A-Za-z0-9]", zeile)
        )

    for schritt, argumente in schritte:
        _melder.zeile(f"Installiere {schritt} in die mitgelieferte Python ...")
        # Gezählt wird nur bei der Liste aus `uv.lock`; bei Natter selbst
        # und PyInstaller steht die Gesamtzahl nicht fest.
        auswerten = _pakete_zaehlen(anzahl if argumente[:1] == ["-r"] else 0)

        # Jede Zeile von pip geht sofort weiter: ins Protokoll und als
        # Hinweis unter den Balken. Ein Bau, der Minuten läuft, soll
        # zeigen, wo er steht - und wenn etwas schiefgeht, will man
        # pips eigene Zeilen sehen.
        code, ausgabe = ausfuehren(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--no-warn-script-location",
                "--disable-pip-version-check",
                *argumente,
            ],
            _melder,
            zeile_auswerten=auswerten,
            env=_saubere_umgebung(),
        )
        if code != 0:
            letzte = "\n".join(ausgabe.strip().splitlines()[-15:])
            raise RuntimeError(
                f"pip install {schritt} fehlgeschlagen (Rückgabewert {code}):\n{letzte}"
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
        _BEISPIEL_ORDNER,
    ):
        ziel = site_packages / quelle.name
        if ziel.exists():
            shutil.rmtree(ziel)
        shutil.copytree(quelle, ziel)

    docs = site_packages / _DOCS_ORDNER.name
    if docs.exists():
        shutil.rmtree(docs)
    docs.mkdir(parents=True)
    for name in _HILFESEITEN:
        shutil.copy(_DOCS_ORDNER / name, docs / name)


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
    code, ausgabe = ausfuehren(befehl, _melder, cwd=_PROJEKT_WURZEL)
    shutil.rmtree(_BUILD_ORDNER, ignore_errors=True)
    shutil.rmtree(_SPEC_ORDNER, ignore_errors=True)
    if code != 0:
        letzte = "\n".join(ausgabe.strip().splitlines()[-15:])
        raise RuntimeError(f"Der Bau des Starters ist fehlgeschlagen:\n{letzte}")

    quelle = _DIST_ORDNER / "_starter" / "Natter.exe"
    shutil.copy2(quelle, _AUSGABE / "Natter.exe")
    shutil.rmtree(_DIST_ORDNER / "_starter", ignore_errors=True)


#: Die Qt-Module, die es nur unter GPL gibt, nicht unter LGPL: Charts,
#: Data Visualization und Graphs. PySide6-Addons bringt sie mit, Natter
#: benutzt keines davon (Diagramme zeichnet matplotlib). Mit ihnen im
#: Paket müsste Natter selbst unter GPL stehen.
#:
#: Das Muster trifft die DLLs, die Python-Module, ihre .pyi-Dateien und
#: die zugehörigen Ordner unter glue, include, metatypes, qml und
#: typesystems - nachgezählt an 0.3.2: 35 Einträge, rund 13 MB.
_QT_NUR_GPL = re.compile(
    r"(?i)^(qt6?(charts|datavisualization|graphs)"
    r"|typesystem_(charts|datavisualization|graphs)"
    r"|datavisualization_common)"
)


def _qt_nur_gpl_entfernen(site_packages: Path) -> list[Path]:
    """Löscht die Qt-Module unter GPL aus der mitgelieferten PySide6.

    `PySide6/__init__.py` ermittelt die vorhandenen Module erst beim
    Zugriff auf `__all__`; ein fehlendes Modul stört dort nicht. Gibt
    die gelöschten Pfade zurück.
    """
    pyside = site_packages / "PySide6"
    if not pyside.is_dir():
        return []
    geloescht: list[Path] = []
    # Von oben nach unten: ein Ordner wie include/QtCharts geht als
    # Ganzes weg, sein Inhalt wird danach nicht mehr betrachtet.
    offen = [pyside]
    while offen:
        ordner = offen.pop()
        for eintrag in sorted(ordner.iterdir()):
            if _QT_NUR_GPL.match(eintrag.name):
                if eintrag.is_dir():
                    shutil.rmtree(eintrag)
                else:
                    eintrag.unlink()
                geloescht.append(eintrag)
            elif eintrag.is_dir():
                offen.append(eintrag)
    return geloescht


#: Pakete, die trotz GPL ausgeliefert werden dürfen, mit Begründung.
#:
#: PyInstaller steht unter GPL-2.0 mit einer Ausnahme für das, was es
#: baut: die erzeugte Exe darf unter beliebiger Lizenz stehen. Natter
#: liefert es mit, damit "Projekt -> Als Exe exportieren" in der
#: installierten Fassung funktioniert; es wird dort als eigenständiges
#: Programm aufgerufen und nicht in Natter eingebunden.
LIZENZ_AUSNAHMEN: dict[str, str] = {
    "pyinstaller": "GPL-2.0 mit Ausnahme für erzeugte Programme",
}

#: Natter selbst - sein Lizenztext liegt als LICENSE im Programmordner.
_EIGENES_PAKET = "natter"

_ERLAUBT = re.compile(
    r"(?i)\b(MIT|BSD|0BSD|Apache|PSF|Python Software Foundation|ISC"
    r"|Zlib|CC0|HPND)\b"
)
_LGPL = re.compile(r"(?i)LGPL|Lesser General Public")
_GPL = re.compile(r"(?i)(?<!L)GPL|General Public License")


def _begriff_einordnen(begriff: str) -> str:
    """Ordnet einen einzelnen Lizenznamen ein: "erlaubt", "gpl" oder
    "unbekannt". LGPL zählt als erlaubt und wird vor GPL geprüft,
    weil "LGPL" die Buchstaben "GPL" enthält."""
    if _LGPL.search(begriff):
        return "erlaubt"
    if _GPL.search(begriff):
        return "gpl"
    if _ERLAUBT.search(begriff):
        return "erlaubt"
    return "unbekannt"


def _ausdruck_einordnen(ausdruck: str) -> str:
    """Ordnet einen Lizenzausdruck wie "Apache-2.0 OR BSD-3-Clause"
    oder "MIT AND PSF-2.0" ein.

    Bei OR genügt eine erlaubte Wahl, bei AND muss jeder Teil erlaubt
    sein. Getrennt wird nur an großgeschriebenem OR/AND: in einem
    Fließtext wie "GPLv2-or-later with a special exception" ist das
    kleine "or" Teil des Namens.
    """
    ausdruck = ausdruck.replace("(", " ").replace(")", " ")
    ergebnisse = []
    for wahl in re.split(r"\s+OR\s+", ausdruck):
        teile = [
            _begriff_einordnen(teil)
            for teil in re.split(r"\s+AND\s+", wahl)
            if teil.strip()
        ]
        if not teile:
            continue
        if "gpl" in teile:
            ergebnisse.append("gpl")
        elif "unbekannt" in teile:
            ergebnisse.append("unbekannt")
        else:
            ergebnisse.append("erlaubt")
    if "erlaubt" in ergebnisse:
        return "erlaubt"
    if "gpl" in ergebnisse:
        return "gpl"
    return "unbekannt"


def lizenz_einordnen(metadaten) -> str:  # noqa: ANN001
    """Ordnet die Lizenz eines Pakets anhand seiner Metadaten ein:
    "erlaubt", "gpl" oder "unbekannt".

    Gelesen wird der Reihe nach das, was die Pakete tatsächlich
    angeben: das Feld License-Expression (neuere Pakete), die erste
    Zeile von License und die Klassifikatoren "License :: ...". Die
    erste Quelle, aus der sich etwas ablesen lässt, gilt. Bei
    matplotlib steht in License zum Beispiel der Anfang des ganzen
    Lizenztexts, die Einordnung kommt dann aus dem Klassifikator.
    Mehrere Klassifikatoren gelten als Wahl zwischen den Lizenzen, so
    wie PyPI sie auch darstellt.
    """
    quellen = []
    if metadaten.get("License-Expression"):
        quellen.append(metadaten["License-Expression"])
    zeilen = (metadaten.get("License") or "").strip().splitlines()
    if zeilen:
        quellen.append(zeilen[0])
    klassifikatoren = [
        k.split("::")[-1].strip()
        for k in metadaten.get_all("Classifier") or []
        if k.startswith("License ::")
    ]
    if klassifikatoren:
        quellen.append(" OR ".join(klassifikatoren))

    for quelle in quellen:
        einordnung = _ausdruck_einordnen(quelle)
        if einordnung != "unbekannt":
            return einordnung
    return "unbekannt"


def lizenzen_pruefen(site_packages: Path) -> list[str]:
    """Prüft jedes Paket in `site_packages` auf eine Lizenz, die sich
    mit der Weitergabe von Natter verträgt. Gibt eine Zeile je
    Beanstandung zurück; eine leere Liste heißt: alles in Ordnung."""
    beanstandungen = []
    for dist in distributions(path=[str(site_packages)]):
        name = (dist.metadata["Name"] or "").strip()
        normalisiert = re.sub(r"[-_.]+", "-", name).lower()
        if not name or normalisiert == _EIGENES_PAKET:
            continue
        if normalisiert in LIZENZ_AUSNAHMEN:
            continue
        einordnung = lizenz_einordnen(dist.metadata)
        if einordnung == "gpl":
            beanstandungen.append(f"{name}: steht unter GPL")
        elif einordnung == "unbekannt":
            beanstandungen.append(
                f"{name}: Lizenz lässt sich aus den Metadaten nicht ablesen"
            )
    return sorted(beanstandungen)


def _lizenzen_sammeln(site_packages: Path, ziel: Path) -> None:
    """Kopiert LGPL-3.0-Text + Qt-Hinweis sowie die von jedem Paket
    selbst mitgelieferten Lizenzdateien (`dist-info/licenses/…` bzw.
    `LICENSE*`/`COPYING*` im Paketordner) in `ziel`.

    Gesammelt wird aus der mitgelieferten Python, nicht aus der
    Umgebung, in der gebaut wird: bis 0.3.2 las diese Funktion die
    Bauumgebung und nahm daraus nur eine feste Liste von 18 Paketen.
    Die rund 30 Pakete, die als deren Abhängigkeiten mitkamen (jedi,
    pillow, cryptography, ...), lagen ohne Lizenztext in der
    Installation.

    Bricht ab, wenn ein Paket unter GPL steht oder seine Lizenz sich
    nicht ablesen lässt (siehe `lizenzen_pruefen`).
    """
    beanstandungen = lizenzen_pruefen(site_packages)
    if beanstandungen:
        raise RuntimeError(
            "Diese Pakete dürfen so nicht ausgeliefert werden:\n  "
            + "\n  ".join(beanstandungen)
            + "\nEntweder das Paket entfernen oder, nach Prüfung der "
            "Lizenz, in LIZENZ_AUSNAHMEN in tools/ide_paketieren.py "
            "eintragen."
        )

    ziel.mkdir(parents=True, exist_ok=True)
    for datei in _LIZENZ_VORLAGEN.iterdir():
        # Die INSTALLER_*-Texte sind Seiten des Installers (Lizenz,
        # Hinweis vor der Installation), keine Lizenz einer Bibliothek -
        # sie gehören nicht in den Lizenzen-Ordner der Installation.
        if datei.name.startswith("INSTALLER_"):
            continue
        shutil.copy2(datei, ziel / datei.name)

    gesehen: set[str] = set()
    for dist in distributions(path=[str(site_packages)]):
        name = (dist.metadata["Name"] or "").strip()
        normalisiert = re.sub(r"[-_.]+", "-", name).lower()
        if not name or normalisiert in gesehen or normalisiert == _EIGENES_PAKET:
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
            # Neuere Pakete tragen die Lizenz nur noch in
            # License-Expression ein, ältere nur in License oder in
            # den Klassifikatoren.
            lizenzfeld = (
                dist.metadata.get("License-Expression")
                or (dist.metadata.get("License") or "").strip()
                or ", ".join(
                    k.split("::")[-1].strip()
                    for k in dist.metadata.get_all("Classifier") or []
                    if k.startswith("License ::")
                )
                or "unbekannt"
            )
            paket_ordner.mkdir(exist_ok=True)
            (paket_ordner / "LIZENZ_HINWEIS.txt").write_text(
                f"{name}: keine eigene Lizenzdatei im Paket gefunden.\n"
                f"Laut Paket-Metadaten: {lizenzfeld}\n"
                f"Siehe https://pypi.org/project/{name}/ für Details.\n",
                encoding="utf-8",
            )


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
        _melder.zeile(f"Warnung: Signieren übersprungen ({meldung})")
        return
    _melder.zeile(ergebnis.stdout.strip())


def _alles_signieren(ordner: Path) -> None:
    """Signiert jede Binärdatei im Ordner, die noch keine gültige
    Signatur trägt.

    Bis September 2026 signierte der Bau nur `Natter.exe`; von 820
    Binärdateien blieben 377 ohne Signatur, darunter die gesamte
    mitgelieferte Python samt numpy, scipy, pandas und sklearn. Eine
    Auslieferung, bei der fast jede zweite Datei keine Herkunft nennt,
    ist keine signierte Auslieferung. Gegen eine eingeschaltete
    intelligente App-Steuerung hilft das Signieren dagegen nicht; die
    Messung dazu steht in `tools/signieren/README.md`.

    Läuft vor `_manifest_schreiben()`: jede Signatur ändert die Bytes
    der Datei, und ein Manifest, das davor entsteht, meldet beim
    ersten Start 377 veränderte Dateien.
    """
    gesamt = 0

    def auswerten(zeile: str) -> None:
        nonlocal gesamt
        treffer = re.match(r"\s*Signiere (\d+) Dateien", zeile)
        if treffer:
            gesamt = int(treffer.group(1))
            return
        treffer = re.match(r"\s*(\d+)/(\d+)\b", zeile)
        if treffer:
            _melder.stand(int(treffer.group(1)), int(treffer.group(2)), "Dateien")

    code, ausgabe = ausfuehren(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(_ALLES_SIGNIEREN),
            "-Ordner",
            str(ordner),
        ],
        _melder,
        zeile_auswerten=auswerten,
    )
    if code != 0:
        letzte = ausgabe.strip().splitlines()[-1:] or ["kein Grund gemeldet"]
        _melder.zeile(f"Warnung: Massensignierung übersprungen ({letzte[0]})")


# ------------------------------------------ Signaturen wiederverwenden
#
# Von den 377 Dateien, die der Bau signiert, stammen fast alle aus
# Paketen von PyPI und sind von Bau zu Bau Byte für Byte gleich. Sie
# jedes Mal neu zu signieren kostete gut drei Minuten, fast nur für
# die Anfrage beim Zeitstempeldienst.
#
# Aufgehoben wird deshalb die signierte Fassung, abgelegt unter der
# Prüfsumme der unsignierten. Trifft der nächste Bau auf eine Datei
# mit derselben Prüfsumme, kommt die aufgehobene Fassung an ihre
# Stelle - sie ist genau das, was das Signieren dieser Datei mit
# diesem Zertifikat ergeben hat, und der Zeitstempel darin bleibt
# gültig. Was sich geändert hat, hat eine andere Prüfsumme und wird
# neu signiert.
#
# Abgelegt wird je Zertifikat getrennt: mit einem neuen Zertifikat
# passt keine alte Signatur mehr. Und nichts davon ersetzt die
# Prüfung: Schritt 10 von `tools/auslieferung_bauen.py` sieht jede
# einzelne Signatur nach, auch die aus dem Zwischenspeicher.


def _pruefsumme(datei: Path) -> str:
    rechner = hashlib.sha256()
    with datei.open("rb") as strom:
        for block in iter(lambda: strom.read(1 << 20), b""):
            rechner.update(block)
    return rechner.hexdigest()


def _fingerabdruck_des_zertifikats() -> str | None:
    ergebnis = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-ChildItem Cert:\\CurrentUser\\My -CodeSigningCert | "
            "Where-Object { $_.Subject -eq 'CN=Natter Codesignatur' } | "
            "Select-Object -First 1 -ExpandProperty Thumbprint",
        ],
        capture_output=True,
        text=True,
    )
    fingerabdruck = ergebnis.stdout.strip()
    return fingerabdruck if re.fullmatch(r"[0-9A-F]{40}", fingerabdruck) else None


def ausgenommen_vom_signieren(datei: Path) -> bool:
    """Ob `datei` zu den Vorlagen gehört, die unsigniert bleiben müssen.

    PyInstaller baut „Als Exe exportieren" aus diesen Vorlagen: es
    kopiert `run.exe`/`runw.exe` und hängt das Programmarchiv an. Trägt
    die Vorlage schon eine Signatur, steht sie danach mitten in der
    Datei, und Windows lehnt die fertige Exe beim Signieren ab („%1 ist
    keine zulässige Win32-Anwendung"). So war es von 0.3.1 bis 0.3.3:
    keine einzige exportierte Schüler-Exe ließ sich signieren.
    """
    teile = [t.lower() for t in datei.parts]
    return any(
        teile[i : i + 2] == ["pyinstaller", "bootloader"] for i in range(len(teile) - 1)
    )


#: Dieselbe Ausnahme als Pfadstück, für das Signierskript und Schritt
#: 10 von `tools/auslieferung_bauen.py`; ein Test hält alle drei
#: zusammen.
NICHT_SIGNIERT = "\\PyInstaller\\bootloader\\"


def _binaerdateien(ordner: Path) -> list[Path]:
    return sorted(
        datei
        for datei in ordner.rglob("*")
        if datei.suffix.lower() in SIGNIERTE_ENDUNGEN
        and datei.is_file()
        and not ausgenommen_vom_signieren(datei)
    )


def _signieren_mit_zwischenspeicher(ordner: Path) -> None:
    fingerabdruck = _fingerabdruck_des_zertifikats()
    if fingerabdruck is None:
        _alles_signieren(ordner)
        return

    ablage = _SIGNATUR_ABLAGE / fingerabdruck
    ablage.mkdir(parents=True, exist_ok=True)
    vorher = {datei: _pruefsumme(datei) for datei in _binaerdateien(ordner)}

    uebernommen = 0
    for datei, summe in vorher.items():
        eintrag = ablage / f"{summe}.bin"
        if eintrag.is_file():
            shutil.copyfile(eintrag, datei)
            uebernommen += 1
    _melder.zeile(f"Aus dem Zwischenspeicher übernommen: {uebernommen} Signaturen")

    _alles_signieren(ordner)

    gebraucht: set[str] = set()
    neu = 0
    for datei, summe in vorher.items():
        eintrag = ablage / f"{summe}.bin"
        if eintrag.is_file():
            gebraucht.add(summe)
            continue
        if _pruefsumme(datei) != summe:
            # Erst unter einem Zwischennamen, dann umbenennen: ein
            # abgebrochener Bau hinterlässt sonst eine halbe Datei, die
            # beim nächsten Mal als fertig signiert gälte.
            halb = eintrag.with_suffix(".tmp")
            shutil.copyfile(datei, halb)
            os.replace(halb, eintrag)
            gebraucht.add(summe)
            neu += 1

    # Was dieser Bau nicht gebraucht hat, gehört zu einer älteren
    # Paketversion. Ohne das Aufräumen wüchse die Ablage mit jedem
    # Update um die nächsten paar hundert Megabyte.
    for eintrag in ablage.glob("*.bin"):
        if eintrag.stem not in gebraucht:
            eintrag.unlink()
    _melder.zeile(f"Neu im Zwischenspeicher: {neu} Signaturen")


def _manifest_schreiben(ordner: Path) -> None:
    """Signiertes Prüfsummen-Manifest über den fertigen Programmordner
    (Abschnitt 17.8). Muss nach dem Signieren laufen, weil die
    Authenticode-Signatur die Bytes von `Natter.exe` verändert - sonst
    meldet schon der erste Start eine veränderte Datei. Ohne privaten
    Schlüssel nur eine Warnung, wie beim Signieren auch."""
    if not _MANIFEST_SCHLUESSEL.exists():
        _melder.zeile(
            f"Warnung: Prüfsummen-Manifest übersprungen ({_MANIFEST_SCHLUESSEL.name} fehlt - "
            "einmalig mit tools/signieren/manifest_schluessel_erzeugen.py anlegen)"
        )
        return
    ziel = manifest_schreiben(ordner, _MANIFEST_SCHLUESSEL)
    _melder.zeile(f"Prüfsummen-Manifest geschrieben: {ziel}")


#: Die Abschnitte des Baus mit ihrer ungefähren Dauer in Sekunden.
#: Nur ein Ausgangswert für die Fortschrittsanzeige; nach dem ersten
#: Lauf gilt die gemessene Dauer.
_PHASEN: tuple[tuple[str, float], ...] = (
    ("Python bereitstellen", 15),
    ("Pakete installieren", 240),
    ("Daten kopieren", 15),
    ("Starter bauen", 60),
    ("Lizenzen sammeln", 5),
    ("Signieren", 190),
    ("Prüfsummen", 20),
)


def paketieren(*, signieren: bool = True, melder: object | None = None) -> Path:
    """Baut `dist/Natter`. Mit `melder` (siehe `tools/fortschritt.py`)
    gehen Ausgaben und Fortschritt an eine Anzeige statt direkt in die
    Konsole."""
    global _melder
    _melder = melder if melder is not None else KonsolenMelder()
    _melder.phasen_ankuendigen(list(_PHASEN))

    _melder.phase("Python bereitstellen")
    if _AUSGABE.exists():
        shutil.rmtree(_AUSGABE)
    python = _python_bereitstellen()
    _melder.phase("Pakete installieren")
    _natter_installieren(python)
    site_packages = python.parent / "Lib" / "site-packages"
    geloescht = _qt_nur_gpl_entfernen(site_packages)
    _melder.zeile(f"{len(geloescht)} Qt-Einträge unter GPL entfernt")
    _melder.phase("Daten kopieren")
    _datenordner_kopieren(python)
    _melder.phase("Starter bauen")
    _starter_bauen()
    _melder.phase("Lizenzen sammeln")
    _lizenzen_sammeln(site_packages, _AUSGABE / "Lizenzen")
    shutil.copy2(_NATTER_LIZENZ, _AUSGABE / "LICENSE")
    _melder.phase("Signieren")
    if signieren:
        _exe_signieren(_AUSGABE / "Natter.exe")
        _signieren_mit_zwischenspeicher(_AUSGABE)
    _melder.phase("Prüfsummen")
    _manifest_schreiben(_AUSGABE)
    return _AUSGABE


if __name__ == "__main__":
    ausgabe_ordner = paketieren()
    print(f"Natter gebaut nach: {ausgabe_ordner}")
