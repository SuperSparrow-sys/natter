"""Paketverwaltung (Abschnitt 7.2, 18: `ide/env/`): installierte Pakete
anzeigen, ein Paket installieren, die Paketliste als `requirements.txt`
exportieren – über `pip` als Subprozess.

Vereinfachung, bewusst dokumentiert (siehe Arbeitspaket M7,
Schritt 3): arbeitet auf dem aktuell aktiven Python-Interpreter
(`sys.executable`), nicht auf den getrennten Paketordnern
`pakete-ide`/`pakete-projekt`/`pakete-zusatz` aus Abschnitt 17.6 – die
brauchen den noch nicht gebauten Starter/Launcher aus M8, der beim Start
jeweils nur den passenden Ordner in den Suchpfad hängt.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from ide.prozess import ohne_konsole


@dataclass(frozen=True)
class Paket:
    name: str
    version: str


#: Ergänzung zur pip-Meldung, wenn das Installationsverzeichnis
#: schreibgeschützt ist.
#:
#: Natter liegt seit M13 als gewöhnliche Python-Installation vor, pip
#: arbeitet also wieder ganz normal. Nur: wer Natter systemweit nach
#: `C:\Programme` installiert hat, darf dort ohne Administratorrechte
#: nicht hineinschreiben. Die Voreinstellung des Installers ist deshalb
#: die Installation nur für den angemeldeten Nutzer.
KEIN_SCHREIBRECHT_HINWEIS = (
    " Natter ist in einem Ordner installiert, in den ohne "
    "Administratorrechte nicht geschrieben werden darf. Pakete lassen "
    "sich nur nachinstallieren, wenn Natter nur für den angemeldeten "
    "Nutzer installiert ist."
)


class PaketFehler(RuntimeError):
    """`pip` meldete einen Fehler.

    Die Nachricht ist deutsch, sofern sich der Fehler erkennen lässt
    (`paket_installieren`), sonst `pip`s eigene Fehlerausgabe.
    `rohausgabe` enthält, was `pip` geschrieben hat, für das Panel
    „Meldungen“; leer, wenn die Nachricht sie schon ist.
    """

    def __init__(self, meldung: str, rohausgabe: str = "") -> None:
        super().__init__(meldung)
        self.rohausgabe = rohausgabe


#: Sekunden, die `pip` auf eine Antwort des Paketverzeichnisses
#: wartet, und wie oft es danach neu ansetzt. Die Vorgaben von `pip`
#: sind 15 Sekunden und fünf Wiederholungen. Ohne Netz, oder hinter
#: einem Proxy, der Verbindungen stumm verwirft, dauerte eine
#: Installation damit 106 Sekunden, bevor überhaupt eine Meldung kam,
#: und so lange waren Testlauf und Exe-Export gesperrt (Punkt 424).
#: Mit diesen Werten sind es rund 12 Sekunden. Eine Wiederholung
#: bleibt, weil `pip` nur bei einer Wiederholung den Verbindungsfehler
#: überhaupt ausgibt; ohne sie stünde da nur, das Paket gebe es
#: nicht. Die Wartezeit gilt je Antwort, nicht für den ganzen
#: Download: ein großes Paket über eine langsame Leitung bricht
#: deshalb nicht ab.
_PIP_WARTEZEIT_SEKUNDEN = 5
_PIP_WIEDERHOLUNGEN = 1

#: Woran in der Ausgabe von `pip` zu erkennen ist, dass keine
#: Verbindung zum Paketverzeichnis zustande kam: die Warnung vor einer
#: Wiederholung und die Namen der Fehler aus `urllib3`.
_VERBINDUNGSZEICHEN = (
    "Retrying (Retry(",
    "ConnectTimeoutError",
    "NewConnectionError",
    "ProxyError",
    "Max retries exceeded",
    "Failed to establish a new connection",
    "getaddrinfo failed",
    "ReadTimeoutError",
)

#: Woran zu erkennen ist, dass es keine passende Fassung gibt.
_UNBEKANNT_ZEICHEN = "No matching distribution found for"


def installierte_pakete() -> list[Paket]:
    """Liste aller installierten Pakete (`pip list --format=json`).
 Löst `PaketFehler` aus, wenn `pip` fehlschlägt (Rückmeldung,
 echter Absturz: `check=True` ließ eine unbehandelte
 `CalledProcessError` bis zur IDE durchschlagen, statt wie
 `paket_installieren` einen sauberen Fehler mit `pip`s eigener
 Meldung zu liefern)."""
    ergebnis = subprocess.run(
        [sys.executable, "-m", "pip", "list", "--format=json"],
        **ohne_konsole(capture_output=True, text=True),
    )
    if ergebnis.returncode != 0:
        raise PaketFehler(ergebnis.stderr.strip() or ergebnis.stdout.strip())
    daten = json.loads(ergebnis.stdout)
    return [Paket(eintrag["name"], eintrag["version"]) for eintrag in daten]


#: Ein Paketname wie `requests` oder `scikit-learn`, wahlweise mit
#: Versionsangabe wie `numpy==2.1` oder `pandas>=2,<3` (PEP 508 ohne
#: Adressen und Pfade).
_PAKETNAME = re.compile(
    r"^[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?"
    r"(?:\[[A-Za-z0-9._,-]+\])?"
    r"(?:\s*(?:==|>=|<=|~=|!=|<|>)\s*[A-Za-z0-9.*+!_-]+"
    r"(?:\s*,\s*(?:==|>=|<=|~=|!=|<|>)\s*[A-Za-z0-9.*+!_-]+)*)?$"
)


def paketname_fehler(name: str) -> str | None:
    """Was gegen `name` als Paketname spricht, oder `None`.

    Die Eingabe ging bis 0.4.3 unverändert an `pip`: mit `-` am Anfang
    las es sie als Schalter, etwa als Anforderungsdatei mit eigenem
    Paketverzeichnis, und Adressen oder Pfade galten als Quelle
    (Punkt 543)."""
    if not _PAKETNAME.match(name.strip()):
        return (
            f"„{name.strip()}“ ist kein Paketname. Erwartet wird ein Name wie "
            "„requests“ oder „scikit-learn“, wahlweise mit Version wie "
            "„numpy==2.1“ - keine Adresse, kein Pfad und nichts, was mit "
            "einem Minus beginnt."
        )
    return None


def paket_installieren(name: str) -> str:
    """Installiert `name` per `pip install`. Liefert `pip`s Ausgabe bei
    Erfolg, löst `PaketFehler` bei Misserfolg aus.

    Bei fehlender Verbindung und bei einem unbekannten Namen ist die
    Nachricht des Fehlers ein deutscher Satz (`_fehler_deuten`), und
    `pip`s Ausgabe steht in `rohausgabe`. Die Versionsprüfung von
    `pip` selbst bleibt aus: sie ginge ein weiteres Mal ins Netz.
    """
    fehler = paketname_fehler(name)
    if fehler is not None:
        raise PaketFehler(fehler)
    ergebnis = subprocess.run(
        [
            sys.executable, "-m", "pip", "install",
            "--timeout", str(_PIP_WARTEZEIT_SEKUNDEN),
            "--retries", str(_PIP_WIEDERHOLUNGEN),
            "--disable-pip-version-check",
            "--no-input",
            "--",
            name.strip(),
        ],
        **ohne_konsole(capture_output=True, text=True),
    )
    if ergebnis.returncode != 0:
        raise _fehler_deuten(name, ergebnis)
    return ergebnis.stdout


def _fehler_deuten(
    name: str, ergebnis: subprocess.CompletedProcess
) -> PaketFehler:
    """Macht aus der Ausgabe eines gescheiterten `pip install` einen
    Fehler mit deutscher Nachricht.

    Ohne Verbindung endet `pip` mit „No matching distribution found“,
    derselben Zeile wie bei einem falsch geschriebenen Namen. Dass
    keine Verbindung zustande kam, steht nur englisch in den Zeilen
    davor. Deshalb wird zuerst nach der Verbindung gesehen.
    """
    roh = "\n".join(
        teil.strip() for teil in (ergebnis.stderr, ergebnis.stdout)
        if teil and teil.strip()
    )
    if any(zeichen in roh for zeichen in _VERBINDUNGSZEICHEN):
        return PaketFehler(
            "Keine Verbindung zum Paketverzeichnis. "
            f"„{name}“ wurde nicht installiert. Ohne Netz, oder wenn "
            "ein Proxy die Verbindung nicht durchlässt, lassen sich "
            "keine Pakete nachinstallieren.",
            roh,
        )
    if _UNBEKANNT_ZEICHEN in roh:
        return PaketFehler(
            f"Ein Paket „{name}“ gibt es im Paketverzeichnis nicht, "
            "jedenfalls nicht für diese Python-Fassung. Die "
            "Schreibweise des Namens prüfen.",
            roh,
        )
    return PaketFehler(_mit_rechtehinweis(ergebnis))


def _mit_rechtehinweis(ergebnis: subprocess.CompletedProcess) -> str:
    """`pip`s eigene Meldung, bei fehlenden Schreibrechten ergänzt.

    `pip` schreibt in diesem Fall nur „Could not install packages due to
    an OSError: [Errno 13] Permission denied“ - richtig, aber ohne den
    entscheidenden Hinweis, woran es liegt (M13).
    """
    meldung = ergebnis.stderr.strip() or ergebnis.stdout.strip()
    zeichen = ("Permission denied", "Errno 13", "WinError 5", "Zugriff verweigert")
    if any(z in meldung for z in zeichen):
        return meldung + KEIN_SCHREIBRECHT_HINWEIS
    return meldung


def paketliste_exportieren(pfad: str | Path) -> None:
    """Schreibt `pip freeze` nach `pfad` (Abschnitt 7.2: „Paketliste
    exportieren (requirements.txt)“). Löst `PaketFehler` aus, wenn `pip`
    fehlschlägt (siehe `installierte_pakete`)."""
    ergebnis = subprocess.run(
        [sys.executable, "-m", "pip", "freeze"],
        **ohne_konsole(capture_output=True, text=True),
    )
    if ergebnis.returncode != 0:
        raise PaketFehler(ergebnis.stderr.strip() or ergebnis.stdout.strip())
    Path(pfad).write_text(ergebnis.stdout, encoding="utf-8")
