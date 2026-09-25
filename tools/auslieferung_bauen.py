"""Baut aus dem Entwicklungsbaum eine fertige, signierte
`Natter-Setup.exe` - in einem Durchgang, mit allen Prüfungen dazwischen.

Früher war das eine Handvoll Befehle aus
`tools/signieren/README.md`, die jemand in der richtigen Reihenfolge
abtippen musste. Das ging zweimal schief, und beide Male nicht an einem
Befehl, sondern zwischen ihnen:

- Der Installer wurde aus einem `dist\\Natter` gebaut, das noch vom
 vorigen Stand stammte. Niemand sieht einer `Natter-Setup.exe` an, aus
 welchem Quelltext sie gebaut wurde.
- Die Auslieferung enthielt Paketversionen, gegen die nie ein Test
 gelaufen war (pandas 3.0.6 in `dist`, 3.0.5 in den Tests) - siehe
 Arbeitspaket M13. Dass Windows Smart App Control daran
 Anstoß nahm, war Zufall; aufgefallen wäre es sonst erst beim Schüler.

Deshalb führt dieses Skript die Schritte nicht nur aus, sondern prüft
nach jedem, ob das Ergebnis stimmt - und bricht ab, statt eine kaputte
Auslieferung fertigzubauen:

1. Arbeitsbaum ansehen (nicht eingecheckte Änderungen melden)
2. Versionsnummern abgleichen (`pyproject.toml`, `tools/natter.iss`,
   `ide/main.py`)
3. `ruff check`
4. `pytest`
5. `dist\\Natter` bauen (`tools.ide_paketieren`)
6. Rauchprobe in der gebauten Python, nicht im Entwicklungsbaum
7. Prüfsummen-Manifest gegenprüfen
8. Installer kompilieren (Inno Setup)
9. Installer signieren
10. Beide Signaturen prüfen
11. Paket für die Schule packen (`tools.paket_bauen`)
12. Auf GitHub veröffentlichen (`tools.veroeffentlichen`)

Beispiel:

 uv run python -m tools.auslieferung_bauen
 uv run python -m tools.auslieferung_bauen --version 0.2.0

Die Versionsnummer gehört zu einem Update dazu: Windows erkennt eine
neue Fassung über `AppVersion`, und bleibt die gleich, zeigt „Apps &
Features" nach dem Update weiter die alte Nummer an. `--version` setzt
sie in `pyproject.toml`, `tools/natter.iss` und `ide/main.py`; ohne
die Angabe prüft Schritt 2 nur, dass alle drei übereinstimmen.

Reines Entwicklungswerkzeug für den Maintainer - kein Teil des
gebauten `pcl`/`ide`-Pakets, läuft nie aus der laufenden IDE heraus.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
import time
import traceback
from importlib.metadata import distributions
from pathlib import Path

from ide.integritaet import ManifestFehler, manifest_pruefen
from tools.fortschritt import Anzeige, Bauzeiten, ausfuehren
from tools.ide_paketieren import SIGNIERTE_ENDUNGEN, paketieren
from tools.veroeffentlichen import (
    SchonVeroeffentlicht,
    VeroeffentlichungFehler,
    veroeffentlichen,
    vorbedingungen_pruefen,
)

_PROJEKT_WURZEL = Path(__file__).resolve().parent.parent

#: Was von Bau zu Bau aufgehoben wird: die gemessenen Schrittzeiten,
#: der Stempel des letzten grünen Testlaufs und die signierten
#: Fassungen unveränderter Dateien. Der Ordner trägt eine eigene
#: `.gitignore`, wie `build/python-download`.
_BAU_CACHE = _PROJEKT_WURZEL / "build" / "bau-cache"
_TEST_STEMPEL = _BAU_CACHE / "tests.json"
_PROTOKOLL = _PROJEKT_WURZEL / "dist" / "auslieferung.log"
_PYPROJECT = _PROJEKT_WURZEL / "pyproject.toml"
_ISS = _PROJEKT_WURZEL / "tools" / "natter.iss"
_MAIN = _PROJEKT_WURZEL / "ide" / "main.py"
_AUSGABE = _PROJEKT_WURZEL / "dist" / "Natter"
_INSTALLER = _PROJEKT_WURZEL / "dist" / "installer" / "Natter-Setup.exe"
_SIGNIER_SKRIPT = _PROJEKT_WURZEL / "tools" / "signieren" / "datei_signieren.ps1"

#: Wo Inno Setup 6 üblicherweise liegt. `ISCC.exe` aus dem `PATH` hat
#: Vorrang, damit eine abweichende Installation nicht ausgeschlossen
#: ist.
_ISCC_ORTE = (
    Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
    Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
)

#: Die Rauchprobe läuft in der gebauten Python, nicht in der des
#: Entwicklungsbaums. Genau dort hat sich der pandas-Fehler versteckt:
#: im Entwicklungsbaum lief alles, in `dist` nicht. Geprüft wird, was
#: der Schüler am ersten Tag anfasst, plus die drei Stellen, die schon
#: einmal still kaputt waren (pandas-Bibliotheken, fehlende Pakete,
#: Tcl/Tk-Reste).
_RAUCHPROBE = r"""
import importlib, sys

fehler = []


def pruefe(name, was):
    try:
        was()
    except Exception as ausnahme:
        fehler.append(f"{name}: {ausnahme}")


# Die IDE selbst und die Laufzeit der Schuelerprogramme.
for modul in ("ide.shell.hauptfenster", "pcl", "PySide6.QtWidgets"):
    pruefe(modul, lambda m=modul: importlib.import_module(m))

# pandas wird erst *innerhalb* der Funktionen importiert, die es
# brauchen - ein Fehler hier faellt im Betrieb erst beim Diagramm auf.
def pandas_pruefen():
    import pandas

    for teil in (
        "algos", "byteswap", "groupby", "hashtable", "index", "internals",
        "interval", "join", "lib", "missing", "ops", "parsers", "reshape",
        "tslib",
    ):
        importlib.import_module(f"pandas._libs.{teil}")
    if pandas.DataFrame({"a": [1, 2, 3]}).mean().iloc[0] != 2.0:
        raise AssertionError("DataFrame rechnet falsch")
    print(f"pandas {pandas.__version__}")


pruefe("pandas", pandas_pruefen)

# Die uebrigen Pakete, ohne die Teile der IDE still ausfallen.
for modul in ("jsonschema", "libcst", "debugpy", "ruff", "scipy",
              "sklearn", "matplotlib", "PyInstaller"):
    pruefe(modul, lambda m=modul: importlib.import_module(m))

# Tcl/Tk ist bewusst ausgebaut (M13) - taucht es wieder auf, hat das
# Bauskript es nicht mehr gefunden.
try:
    import tkinter  # noqa: F401
except ImportError:
    pass
else:
    fehler.append("tkinter: ist wieder in der Auslieferung")

if fehler:
    for zeile in fehler:
        print(f"FEHLER {zeile}")
    sys.exit(1)
print("Rauchprobe bestanden")
"""


#: Wie viele Schritte der Bau hat. Steht in der Zeile, die jeder
#: Schritt ausgibt - wer zusieht, will wissen, wie weit es noch ist.
_SCHRITTE = 12

#: Was Windows lädt und deshalb signiert sein muss - dieselbe Liste,
#: nach der der Bau signiert. Stünde sie hier ein zweites Mal, prüfte
#: Schritt 10 womöglich etwas anderes, als signiert wurde.
_SIGNIERTE_ENDUNGEN = SIGNIERTE_ENDUNGEN


class BauFehler(RuntimeError):
    """Ein Schritt ist fehlgeschlagen; der Bau wird abgebrochen."""


class _StillerMelder:
    """Nimmt Ausgaben entgegen und tut nichts damit - so verhalten
    sich die Schritte, wenn sie einzeln aufgerufen werden, etwa aus
    den Tests heraus: wie früher, ohne Zwischenzeilen."""

    def zeile(self, text: str) -> None:
        pass

    def stand(self, erledigt: int, gesamt: int, einheit: str = "") -> None:
        pass

    def anteil(self, wert: float) -> None:
        pass


#: Die Anzeige des laufenden Baus. Außerhalb von `auslieferung_bauen()`
#: der stille Melder.
_anzeige: Anzeige | _StillerMelder = _StillerMelder()
_uebersprungen_markiert = False


class _Zeilenweiche(io.TextIOBase):
    """Leitet `print()` während des Baus zur Anzeige um. Jede Zeile,
    die ein Schritt ausgibt, ist sein Ergebnis und soll über den
    Balken stehen bleiben - ohne dass jede Stelle im Skript davon
    wissen muss."""

    def __init__(self, ziel) -> None:  # noqa: ANN001
        super().__init__()
        self._ziel = ziel
        self._rest = ""

    def write(self, text: str) -> int:
        self._rest += text
        while "\n" in self._rest:
            zeile, self._rest = self._rest.split("\n", 1)
            if zeile.strip():
                self._ziel(zeile)
        return len(text)

    def flush(self) -> None:
        pass


def _schritt(nummer: int, text: str) -> None:
    _schritt_beenden()
    if isinstance(_anzeige, Anzeige):
        _anzeige.schritt(nummer, text)
    else:
        print(f"\n[{nummer}/{_SCHRITTE}] {text}", flush=True)


def _schritt_beenden() -> None:
    global _uebersprungen_markiert
    if isinstance(_anzeige, Anzeige) and _anzeige.schritt_offen:
        _anzeige.schritt_beendet(uebersprungen=_uebersprungen_markiert)
    _uebersprungen_markiert = False


def _ueberspringen(grund: str) -> None:
    """Der laufende Schritt findet nicht statt. Seine Dauer geht dann
    nicht in die Schätzung für den nächsten Lauf ein."""
    global _uebersprungen_markiert
    _uebersprungen_markiert = True
    print(f"  {grund}")


def _laufen_lassen(
    befehl: list[str],
    *,
    was: str,
    cwd: Path | None = None,
    auswerten=None,  # noqa: ANN001
) -> str:
    """Führt `befehl` aus und gibt die Ausgabe zurück. Jede Zeile geht
    sofort an die Anzeige und ins Protokoll. Bei einem Fehlschlag wird
    die Ausgabe mit in die Meldung genommen - wer den Bau nachts
    anstößt, soll am Morgen sehen, woran es lag."""
    code, ausgabe = ausfuehren(
        befehl, _anzeige, zeile_auswerten=auswerten, cwd=str(cwd or _PROJEKT_WURZEL)
    )
    if code != 0:
        letzte = "\n".join(ausgabe.strip().splitlines()[-25:])
        raise BauFehler(f"{was} fehlgeschlagen:\n{letzte}")
    return ausgabe.strip()


# --------------------------------------------------------------- 1


def _git(*argumente: str) -> str | None:
    """Die Ausgabe eines Git-Befehls, oder `None` ohne Git oder
    Arbeitsbaum. Nur `stdout`: Git schreibt Hinweise wie „LF will be
    replaced by CRLF" auf `stderr`, und die zählten sonst als
    geänderte Dateien."""
    try:
        ergebnis = subprocess.run(
            ["git", *argumente],
            cwd=_PROJEKT_WURZEL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        return None
    return ergebnis.stdout.strip() if ergebnis.returncode == 0 else None


def _arbeitsbaum_ansehen() -> None:
    """Meldet nicht eingecheckte Änderungen - ohne Abbruch.

    Ein Bau aus einem unsauberen Baum ist beim Ausprobieren der
    Normalfall. Für eine Auslieferung, die aus dem Haus geht, ist er
    es nicht: welcher Stand darin steckt, lässt sich hinterher nicht
    mehr feststellen. Deshalb steht es hier deutlich in der Ausgabe.
    """
    offen = _git("status", "--porcelain")
    if offen is None:
        print("  Kein Git-Arbeitsbaum - übersprungen.")
        return

    if not offen:
        print("  Arbeitsbaum ist sauber.")
        return

    zeilen = offen.splitlines()
    print(f"  Achtung: {len(zeilen)} nicht eingecheckte Änderung(en):")
    for zeile in zeilen[:10]:
        print(f"    {zeile}")
    if len(zeilen) > 10:
        print(f"    … und {len(zeilen) - 10} weitere")
    print("  Der Bau läuft trotzdem - der ausgelieferte Stand steht dann")
    print("  aber in keinem Commit.")


# --------------------------------------------------------------- 2


def _version_aus_pyproject() -> str:
    text = _PYPROJECT.read_text(encoding="utf-8")
    treffer = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if treffer is None:
        raise BauFehler("In pyproject.toml steht keine Versionsnummer.")
    return treffer.group(1)


def _version_aus_iss() -> str:
    text = _ISS.read_text(encoding="utf-8")
    treffer = re.search(r'^#define MyAppVersion "([^"]+)"', text, re.MULTILINE)
    if treffer is None:
        raise BauFehler("In tools/natter.iss steht kein MyAppVersion.")
    return treffer.group(1)


def _version_aus_main() -> str:
    text = _MAIN.read_text(encoding="utf-8")
    treffer = re.search(r'^VERSION\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if treffer is None:
        raise BauFehler("In ide/main.py steht keine VERSION.")
    return treffer.group(1)


def _version_setzen(neu: str) -> None:
    """Schreibt `neu` an alle drei Stellen.

    Alle drei, weil sie unterschiedliche Aufgaben haben und trotzdem
    zusammengehören: `pyproject.toml` bestimmt, was `pip` in die
    Auslieferung legt, `natter.iss` das, was Windows in „Apps &
    Features" anzeigt, und `ide/main.py` das, was beim Start auf dem
    Ladebild steht.

    Die dritte Stelle fehlte bis zum Bau von 0.3.0. Die Auslieferung
    war als 0.3.0 registriert und begrüßte den Benutzer mit 0.2.1 -
    aufgefallen erst beim Durchgehen der installierten Fassung, weil
    hier nur die ersten beiden abgeglichen wurden.
    """
    if not re.fullmatch(r"\d+\.\d+\.\d+", neu):
        raise BauFehler(f"Versionsnummer {neu!r} ist nicht im Format 1.2.3.")

    text = _PYPROJECT.read_text(encoding="utf-8")
    text, anzahl = re.subn(
        r'^version\s*=\s*"[^"]+"', f'version = "{neu}"', text, count=1, flags=re.MULTILINE
    )
    if anzahl != 1:
        raise BauFehler("Versionszeile in pyproject.toml nicht gefunden.")
    _PYPROJECT.write_text(text, encoding="utf-8")

    text = _ISS.read_text(encoding="utf-8")
    text, anzahl = re.subn(
        r'^#define MyAppVersion "[^"]+"',
        f'#define MyAppVersion "{neu}"',
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if anzahl != 1:
        raise BauFehler("MyAppVersion in tools/natter.iss nicht gefunden.")
    _ISS.write_text(text, encoding="utf-8")

    text = _MAIN.read_text(encoding="utf-8")
    text, anzahl = re.subn(
        r'^VERSION\s*=\s*"[^"]+"', f'VERSION = "{neu}"', text, count=1, flags=re.MULTILINE
    )
    if anzahl != 1:
        raise BauFehler("VERSION in ide/main.py nicht gefunden.")
    _MAIN.write_text(text, encoding="utf-8")


def _versionen_abgleichen(gewuenscht: str | None) -> str:
    if gewuenscht is not None:
        vorher = _version_aus_pyproject()
        _version_setzen(gewuenscht)
        print(
            f"  Version {vorher} → {gewuenscht} "
            f"(pyproject.toml, natter.iss und ide/main.py)"
        )
        return gewuenscht

    gefunden = {
        "pyproject.toml": _version_aus_pyproject(),
        "tools/natter.iss": _version_aus_iss(),
        "ide/main.py": _version_aus_main(),
    }
    if len(set(gefunden.values())) != 1:
        aufzaehlung = ", ".join(f"{datei} sagt {nummer}" for datei, nummer in gefunden.items())
        raise BauFehler(
            f"Versionsnummern laufen auseinander: {aufzaehlung}. Mit "
            f"--version alle auf denselben Stand bringen."
        )
    nummer = next(iter(gefunden.values()))
    print(f"  Version {nummer}, in allen drei Dateien gleich.")
    return nummer


# --------------------------------------------------------------- 3/4


def _ruff_pruefen() -> None:
    _laufen_lassen([sys.executable, "-m", "ruff", "check", "."], was="ruff check")
    print("  Keine Beanstandungen.")


def _prozent_von_pytest(zeile: str) -> None:
    """pytest schreibt hinter jede Zeile Punkte seinen Stand, etwa
    „[ 58%]". Daraus wird der Balken."""
    treffer = re.search(r"\[\s*(\d+)%\]\s*$", zeile)
    if treffer:
        _anzeige.anteil(int(treffer.group(1)) / 100)


def _teststand() -> str | None:
    """Ein Fingerabdruck dessen, was die Tests prüfen, oder `None`,
    wenn er sich nicht sicher bestimmen lässt.

    Er besteht aus dem Git-Baum des eingecheckten Stands und den
    installierten Paketen samt Versionen. Liegt irgendetwas nicht
    eingecheckt im Arbeitsbaum - geändert oder neu -, gibt es keinen
    Fingerabdruck: dann ist nicht sicher, was die Tests sähen, und sie
    laufen.
    """
    offen = _git("status", "--porcelain")
    baum = _git("rev-parse", "HEAD^{tree}")
    if offen is None or offen or not baum:
        return None
    pakete = sorted(
        f"{verteilung.metadata['Name']}=={verteilung.version}"
        for verteilung in distributions()
    )
    inhalt = "\n".join([baum, sys.version, *pakete])
    return hashlib.sha256(inhalt.encode("utf-8")).hexdigest()


def _tests_schon_gruen(stand: str | None) -> str | None:
    """Wann derselbe Stand zuletzt grün getestet wurde, oder `None`."""
    if stand is None:
        return None
    try:
        gemerkt = json.loads(_TEST_STEMPEL.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return gemerkt.get("zeit") if gemerkt.get("stand") == stand else None


def _tests_gruen_merken(stand: str | None, ergebnis: str) -> None:
    if stand is None:
        return
    _TEST_STEMPEL.parent.mkdir(parents=True, exist_ok=True)
    (_TEST_STEMPEL.parent / ".gitignore").write_text("*\n", encoding="utf-8")
    _TEST_STEMPEL.write_text(
        json.dumps(
            {"stand": stand, "zeit": time.strftime("%d.%m.%Y %H:%M"), "ergebnis": ergebnis},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _tests_laufen_lassen(*, immer: bool = False) -> None:
    """Lässt pytest laufen - es sei denn, genau dieser Stand war schon
    grün.

    Ein Bau, der hinter den Tests scheitert, an einer Zeitstempel-
    Anfrage etwa oder an Inno Setup, wird ohne jede Änderung am Code
    neu gestartet. Die gut dreizehn Minuten Tests brächten dann
    dasselbe Ergebnis wie beim ersten Mal. Übersprungen wird nur, wenn
    sich das sicher sagen lässt, siehe `_teststand()`; mit
    `--alle-tests` nie.
    """
    stand = _teststand()
    zuletzt = None if immer else _tests_schon_gruen(stand)
    if zuletzt is not None:
        _ueberspringen(
            f"Übersprungen: derselbe eingecheckte Stand mit denselben Paketen "
            f"war am {zuletzt} grün."
        )
        return

    ausgabe = _laufen_lassen(
        [sys.executable, "-m", "pytest", "-q"], was="pytest", auswerten=_prozent_von_pytest
    )
    letzte = ausgabe.strip().splitlines()[-1] if ausgabe.strip() else "(keine Ausgabe)"
    print(f"  {letzte}")
    _tests_gruen_merken(stand, letzte)


# --------------------------------------------------------------- 6


def _rauchprobe(python: Path) -> None:
    """Startet die gebaute Python und lässt sie sich selbst prüfen.

    Bewusst als eigener Prozess und nicht als Import hier: sonst
    würde die Prüfung im Entwicklungsbaum laufen, und genau dort war
    ja immer alles in Ordnung.
    """
    from tools.ide_paketieren import _saubere_umgebung

    ergebnis = subprocess.run(
        [str(python), "-c", _RAUCHPROBE],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=_saubere_umgebung(),
    )
    for zeile in (ergebnis.stdout or "").strip().splitlines():
        print(f"  {zeile}")
    if ergebnis.returncode != 0:
        raise BauFehler(
            "Rauchprobe in der gebauten Python fehlgeschlagen - siehe oben. "
            "Die Auslieferung ist nicht brauchbar, auch wenn alle Tests "
            "grün waren."
        )


# --------------------------------------------------------------- 7


def _manifest_gegenpruefen(ordner: Path) -> None:
    """Prüft die fertige Installation gegen ihr eigenes Manifest -
    dieselbe Prüfung, die beim Schüler bei jedem Start läuft.

    Sie hier zu wiederholen kostet Sekunden und fängt die Fälle ab, in
    denen nach dem Signieren noch etwas an den Dateien geändert wurde:
    beim Schüler gäbe das eine Manipulationswarnung beim ersten Start.
    """
    try:
        ergebnis = manifest_pruefen(ordner)
    except ManifestFehler as fehler:
        print(f"  Warnung: nicht geprüft ({fehler})")
        return

    if not ergebnis.signatur_gueltig:
        raise BauFehler("Die Signatur des Prüfsummen-Manifests stimmt nicht.")
    if not ergebnis.in_ordnung:
        namen = ", ".join(ergebnis.betroffene_dateien[:5])
        raise BauFehler(f"Dateien weichen vom Manifest ab: {namen}")
    print("  Manifest gültig, keine Abweichungen.")


# --------------------------------------------------------------- 8/9/10


def _iscc_finden() -> Path:
    aus_pfad = shutil.which("ISCC")
    if aus_pfad:
        return Path(aus_pfad)
    for ort in _ISCC_ORTE:
        if ort.exists():
            return ort
    raise BauFehler(
        "ISCC.exe nicht gefunden. Inno Setup 6 installieren "
        "(https://jrsoftware.org/isdl.php) oder in den PATH aufnehmen."
    )


def _installer_bauen() -> Path:
    iscc = _iscc_finden()
    if _INSTALLER.exists():
        # Sonst bleibt bei einem Fehlschlag die alte Datei liegen und
        # sieht aus wie das Ergebnis dieses Baus.
        _INSTALLER.unlink()
    print("  Inno Setup packt und komprimiert - das dauert einige Minuten.", flush=True)
    # `/Snatter=…` belegt den Signierbefehl, auf den sich `SignTool=natter`
    # in der `.iss` bezieht. Inno ruft ihn für den Uninstaller auf, den es
    # erst beim Installieren erzeugt - ohne das bliebe er als einzige
    # unsignierte Datei auf dem Rechner des Schülers zurück. `$f` ersetzt
    # Inno durch den Dateinamen.
    # `$q` ist in einem Inno-Signierbefehl das Anführungszeichen, `$f`
    # der Dateiname. Ein echtes `"` schreibt Inno wörtlich durch, und
    # PowerShell bekam daraus einen Pfad mit Backslashes davor und
    # dahinter („Das angegebene Pfadformat wird nicht unterstützt").
    signierbefehl = (
        "powershell.exe -NoProfile -ExecutionPolicy Bypass "
        f"-File $q{_SIGNIER_SKRIPT}$q -Datei $f"
    )
    # Inno meldet jede Datei mit „Compressing: …". Gezählt gegen die
    # Dateien in `dist\Natter` ergibt das einen echten Balken statt
    # einer Schätzung - dieser Schritt ist nach den Tests der längste.
    gesamt = sum(1 for pfad in _AUSGABE.rglob("*") if pfad.is_file())
    gepackt = 0

    def auswerten(zeile: str) -> None:
        nonlocal gepackt
        if zeile.lstrip().startswith("Compressing:"):
            gepackt += 1
            _anzeige.stand(min(gepackt, gesamt), gesamt, "Dateien")

    _laufen_lassen(
        [str(iscc), f"/Snatter={signierbefehl}", str(_ISS)],
        was="Inno Setup",
        auswerten=auswerten,
    )
    if not _INSTALLER.exists():
        raise BauFehler(f"Inno Setup meldete Erfolg, aber {_INSTALLER.name} fehlt.")
    # Die Größe steht erst im Schlussbericht: das Signieren im nächsten
    # Schritt verändert die Datei noch, und zwei leicht verschiedene
    # Zahlen in einer Ausgabe liest niemand gern.
    print(f"  {_INSTALLER}")
    return _INSTALLER


def _installer_signieren(datei: Path) -> None:
    """Inno Setup erzeugt den Installer erst nach
    `ide_paketieren.py`; deshalb wird er hier separat signiert und
    nicht dort mit."""
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
        encoding="utf-8",
        errors="replace",
    )
    if ergebnis.returncode != 0:
        meldung = (ergebnis.stderr or ergebnis.stdout or "").strip()
        print(f"  Warnung: Signieren übersprungen ({meldung})")
        return
    print(f"  {(ergebnis.stdout or '').strip()}")


def _luecken_in_den_signaturen(ordner: Path) -> list[str]:
    """Jede Binärdatei im Ordner, die keine gültige Signatur trägt.

    Das Gate gegen den Fehler, der im September 2026 durchgerutscht
    ist: der Bau signierte nur `Natter.exe`, und die übrigen 377
    unsignierten Dateien fielen erst auf, als Smart App Control auf
    einem fremden Rechner den Start abschoss. Eine Empfehlung im Text
    hätte das nicht verhindert - beim nächsten Release wäre wieder
    eine Datei durchgerutscht.
    """
    # Gefiltert wird über `Where-Object` und nicht über `-Include`:
    # zusammen mit `-LiteralPath` lässt PowerShell `-Include` ohne ein
    # Wort fallen und liefert jede Datei. Der erste Lauf dieses Gates
    # meldete deshalb 29341 Lücken, angeführt von `manifest.json` und
    # den Lizenztexten.
    endungen = ", ".join(f"'{e}'" for e in _SIGNIERTE_ENDUNGEN)
    # Eine Zeile je geprüfter Datei: „OK" oder „LUECKE <Pfad>". Die
    # OK-Zeilen braucht niemand zu lesen, aber an ihnen zählt die
    # Anzeige mit, wie weit die Prüfung ist.
    befehl = (
        f"Get-ChildItem -LiteralPath '{ordner}' -Recurse -File "
        "-ErrorAction SilentlyContinue | "
        f"Where-Object {{ $_.Extension -in {endungen} }} | "
        "ForEach-Object { $s = Get-AuthenticodeSignature $_.FullName; "
        "if ($s.Status -ne 'Valid') { Write-Output ('LUECKE ' + $_.FullName) } "
        "else { Write-Output 'OK' } }"
    )
    gesamt = sum(
        1
        for pfad in ordner.rglob("*")
        if pfad.suffix.lower() in _SIGNIERTE_ENDUNGEN and pfad.is_file()
    )
    geprueft = 0
    luecken: list[str] = []

    def auswerten(zeile: str) -> None:
        nonlocal geprueft
        zeile = zeile.strip()
        if zeile == "OK" or zeile.startswith("LUECKE "):
            geprueft += 1
            _anzeige.stand(min(geprueft, gesamt), gesamt, "Dateien")
        if zeile.startswith("LUECKE "):
            luecken.append(zeile.removeprefix("LUECKE "))

    ausfuehren(
        ["powershell", "-NoProfile", "-Command", befehl],
        _StillerMelder(),
        zeile_auswerten=auswerten,
    )
    return luecken


def _alle_signaturen_pruefen(ordner: Path) -> None:
    """Bricht ab, wenn im Ordner etwas ohne gültige Signatur liegt."""
    luecken = _luecken_in_den_signaturen(ordner)
    if not luecken:
        print("  Jede Binärdatei trägt eine gültige Signatur.")
        return

    beispiele = "\n".join(f"    {pfad}" for pfad in luecken[:10])
    weitere = (
        f"\n    … und {len(luecken) - 10} weitere" if len(luecken) > 10 else ""
    )
    raise BauFehler(
        f"{len(luecken)} Datei(en) ohne gültige Signatur:\n"
        f"{beispiele}{weitere}\n\n"
        "Eine unsignierte Datei nennt keinen Herausgeber, und eine "
        "nachträgliche Veränderung fiele an ihr nicht auf. Erst "
        "tools/signieren/alles_signieren.ps1 laufen lassen."
    )


def _signaturen_pruefen(dateien: list[Path]) -> None:
    """Fragt Windows selbst, was es von den Signaturen hält.

    Eine Signatur zu setzen und eine, die Windows auch annimmt, sind
    zwei verschiedene Dinge - ein abgelaufenes Zertifikat etwa wird
    ohne Fehler gesetzt und beim Start trotzdem abgelehnt.
    """
    befehl = "; ".join(
        f"$s = Get-AuthenticodeSignature '{datei}'; "
        f"Write-Output \"{datei.name}|$($s.Status)\""
        for datei in dateien
    )
    ergebnis = subprocess.run(
        ["powershell", "-NoProfile", "-Command", befehl],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    ungueltig = []
    for zeile in (ergebnis.stdout or "").strip().splitlines():
        name, _, status = zeile.partition("|")
        print(f"  {name}: {status}")
        if status.strip() != "Valid":
            ungueltig.append(f"{name} ({status.strip()})")
    if ungueltig:
        print(
            "  Warnung: nicht jede Datei ist gültig signiert: "
            + ", ".join(ungueltig)
            + ". Ohne Zertifikat ist das erwartet (siehe "
            "tools/signieren/README.md); auf einem Rechner mit "
            "Zertifikat wäre es ein Fehler."
        )


# ---------------------------------------------------------------


def _paket_packen(version: str) -> None:
    """Stellt das Paket für die Schule zusammen und packt es.

    Gehört in den Bau und nicht dahinter: das Paket zur Fassung 0.3.0
    war von Hand gepackt, und zwei der neun Dateien fehlten darin.
    Einem ZIP sieht man nicht an, was nicht darin ist.
    """
    from tools.paket_bauen import PaketFehler, paket_bauen, zip_bauen

    try:
        ordner = paket_bauen(version=version)
    except PaketFehler as fehler:
        raise BauFehler(str(fehler)) from fehler

    archiv = zip_bauen(
        version,
        ordner=ordner,
        fortschritt=lambda fertig, gesamt: _anzeige.stand(
            fertig // (1024 * 1024), gesamt // (1024 * 1024), "MB"
        ),
    )
    groesse = archiv.stat().st_size / 1024 / 1024
    print(f"  {ordner}")
    print(f"  {archiv.name} ({groesse:.0f} MB)")


def auslieferung_bauen(
    *,
    version: str | None = None,
    mit_tests: bool = True,
    nur_installer: bool = False,
    alle_tests: bool = False,
    veroeffentlichen_: bool = True,
    live: bool | None = None,
) -> Path:
    """Führt den kompletten Bau aus und liefert den Pfad der fertigen
    `Natter-Setup.exe`.

    Während des Baus zeigt eine Anzeige den Fortschritt (siehe
    `tools/fortschritt.py`), und jede Zeile aller beteiligten Programme
    landet in `dist/auslieferung.log`. Bei einem Fehler steht das Ende
    des Protokolls in der Meldung, der Rest in der Datei.
    """
    global _anzeige
    _BAU_CACHE.mkdir(parents=True, exist_ok=True)
    (_BAU_CACHE / ".gitignore").write_text("*\n", encoding="utf-8")
    anzeige = Anzeige(
        _SCHRITTE, _PROTOKOLL, Bauzeiten(_BAU_CACHE / "bauzeiten.json"), live=live
    )
    vorher = sys.stdout
    _anzeige = anzeige
    sys.stdout = _Zeilenweiche(anzeige.ergebnis)
    try:
        installer, nummer, dauer = _alle_schritte(
            version=version,
            mit_tests=mit_tests,
            nur_installer=nur_installer,
            alle_tests=alle_tests,
            veroeffentlichen_=veroeffentlichen_,
        )
    except BauFehler as fehler:
        anzeige.fehler(str(fehler))
        raise
    except Exception as fehler:
        # Alles, was keine erwartete Bau-Meldung ist - ein Fehler in
        # pip, in PyInstaller oder in diesem Skript selbst. Die Balken
        # verschwinden trotzdem sauber, und der vollständige
        # Stapelverlauf steht im Protokoll.
        anzeige.fehler(f"{type(fehler).__name__}: {fehler}\n\n{traceback.format_exc()}")
        raise BauFehler(str(fehler)) from fehler
    finally:
        sys.stdout = vorher
        _anzeige = _StillerMelder()

    anzeige.beenden(
        f"\nFertig: Natter {nummer} als {installer} "
        f"({installer.stat().st_size / 1024 / 1024:.1f} MB) "
        f"in {dauer / 60:.1f} Minuten.\n"
        f"Protokoll: {_PROTOKOLL}"
    )
    return installer


def _alle_schritte(
    *,
    version: str | None,
    mit_tests: bool,
    nur_installer: bool,
    alle_tests: bool,
    veroeffentlichen_: bool,
) -> tuple[Path, str, float]:
    beginn = time.monotonic()

    # Eine Auslieferung ohne Tests geht nicht aus dem Haus.
    veroeffentlichen_ = veroeffentlichen_ and mit_tests

    _schritt(1, "Arbeitsbaum ansehen")
    _arbeitsbaum_ansehen()
    if veroeffentlichen_:
        # Jetzt und nicht erst in Schritt 12: fehlt `gh` oder liegt
        # etwas nicht eingecheckt herum, soll das nach Sekunden
        # auffallen und nicht nach einer halben Stunde.
        try:
            vorbedingungen_pruefen()
        except VeroeffentlichungFehler as fehler:
            raise BauFehler(f"Veröffentlichen ginge nicht: {fehler}") from fehler
        print("  Veröffentlichen möglich: gh angemeldet, Baum eingecheckt.")

    _schritt(2, "Versionsnummern abgleichen")
    nummer = _versionen_abgleichen(version)

    _schritt(3, "ruff check")
    if nur_installer:
        _ueberspringen("Übersprungen (--nur-installer).")
    else:
        _ruff_pruefen()

    _schritt(4, "pytest")
    if nur_installer or not mit_tests:
        _ueberspringen("Übersprungen.")
    else:
        _tests_laufen_lassen(immer=alle_tests)

    _schritt(5, "dist\\Natter bauen")
    if nur_installer:
        if not _AUSGABE.exists():
            raise BauFehler(f"{_AUSGABE} fehlt - ohne --nur-installer starten.")
        _ueberspringen(f"Vorhandenen Ordner benutzt: {_AUSGABE}")
    else:
        try:
            paketieren(melder=_anzeige)
        except RuntimeError as fehler:
            raise BauFehler(str(fehler)) from fehler
        print(f"  {_AUSGABE}")

    _schritt(6, "Rauchprobe in der gebauten Python")
    _rauchprobe(_AUSGABE / "python" / "python.exe")

    _schritt(7, "Prüfsummen-Manifest gegenprüfen")
    _manifest_gegenpruefen(_AUSGABE)

    _schritt(8, "Installer kompilieren")
    installer = _installer_bauen()

    _schritt(9, "Installer signieren")
    _installer_signieren(installer)

    _schritt(10, "Signaturen prüfen")
    _signaturen_pruefen([_AUSGABE / "Natter.exe", installer])
    # Nicht nur die beiden, die der Bau selbst angefasst hat: Smart App
    # Control prüft jede Datei, die geladen wird.
    _alle_signaturen_pruefen(_AUSGABE)

    _schritt(11, "Paket für die Schule packen")
    _paket_packen(nummer)

    _schritt(12, "Auf GitHub veröffentlichen")
    if not veroeffentlichen_:
        _ueberspringen(
            "Übersprungen (--nicht-veroeffentlichen)."
            if mit_tests
            else "Übersprungen: ohne Tests gebaut."
        )
    else:
        try:
            adresse = veroeffentlichen(nummer, melden=print)
        except SchonVeroeffentlicht as fehler:
            # Ein Probebau mit einer schon vergebenen Nummer ist kein
            # Fehler - er bleibt nur lokal.
            _ueberspringen(f"Nicht veröffentlicht: {fehler}")
        except VeroeffentlichungFehler as fehler:
            raise BauFehler(str(fehler)) from fehler
        else:
            print(f"  {adresse}")
    _schritt_beenden()

    return installer, nummer, time.monotonic() - beginn


def main(argumente: list[str] | None = None) -> int:
    zerleger = argparse.ArgumentParser(
        prog="python -m tools.auslieferung_bauen",
        description="Baut aus dem Entwicklungsbaum eine signierte Natter-Setup.exe.",
    )
    zerleger.add_argument(
        "--version",
        metavar="1.2.3",
        help=(
            "Neue Versionsnummer; wird in pyproject.toml und "
            "tools/natter.iss gesetzt. Ohne die Angabe wird nur "
            "geprüft, dass beide übereinstimmen."
        ),
    )
    zerleger.add_argument(
        "--ohne-tests",
        action="store_true",
        help=(
            "pytest überspringen. Nur zum Ausprobieren des Bauwegs - "
            "eine so gebaute Auslieferung geht nicht aus dem Haus."
        ),
    )
    zerleger.add_argument(
        "--nur-installer",
        action="store_true",
        help=(
            "Vorhandenes dist\\Natter wiederverwenden und nur den "
            "Installer neu bauen. Spart die Minuten für pip und "
            "PyInstaller, wenn nur an natter.iss etwas geändert wurde."
        ),
    )
    zerleger.add_argument(
        "--alle-tests",
        action="store_true",
        help=(
            "pytest auch dann laufen lassen, wenn derselbe eingecheckte "
            "Stand schon grün war."
        ),
    )
    zerleger.add_argument(
        "--nicht-veroeffentlichen",
        action="store_true",
        help=(
            "Nach dem Bau nichts auf GitHub stellen. Für Probebauten; "
            "ohne den Schalter kommen Setup-Datei und ZIP als Release "
            "auf GitHub."
        ),
    )
    zerleger.add_argument(
        "--ohne-balken",
        action="store_true",
        help="Einfache Zeilen statt Fortschrittsbalken, auch in einer Konsole.",
    )
    werte = zerleger.parse_args(argumente)

    if werte.version and werte.nur_installer:
        # Die neue Nummer käme nur in den Installer, nicht in das schon
        # gebaute `dist\Natter`: Windows zeigte 0.2.0 an, `pip list` in
        # der Installation weiterhin 0.1.0. Genau das Auseinanderlaufen,
        # das Schritt 2 verhindern soll.
        print(
            "Abgebrochen: --version und --nur-installer schließen einander aus. "
            "Eine neue Versionsnummer muss mit in die Auslieferung, nicht nur "
            "auf den Installer.",
            file=sys.stderr,
        )
        return 1

    try:
        auslieferung_bauen(
            version=werte.version,
            mit_tests=not werte.ohne_tests,
            nur_installer=werte.nur_installer,
            alle_tests=werte.alle_tests,
            veroeffentlichen_=not werte.nicht_veroeffentlichen,
            live=False if werte.ohne_balken else None,
        )
    except BauFehler:
        # Die Meldung hat die Anzeige schon ausgegeben, mit dem Ende
        # des Protokolls und dem Pfad dorthin.
        return 1
    return 0


if __name__ == "__main__":
    # Der ganze Bericht ist deutsch, und eine Windows-Konsole steht
    # ohne Zutun auf Codepage 850: „Prüfsummen" käme dort als
    # „Pr?fsummen" heraus, und bei umgeleiteter Ausgabe bricht es sogar
    # mit einem UnicodeEncodeError ab.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
