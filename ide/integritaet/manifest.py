"""Signiertes Prüfsummen-Manifest einer Natter-Installation.

Siehe docs/bericht.md, Abschnitt 7.5: „beim Build SHA-256-Prüfsummen
aller Programmdateien (ohne `benutzer/` und `pakete-zusatz/`) in
`manifest.json`; das Manifest wird mit einem eigenen Ed25519-Schlüssel
signiert, der öffentliche Schlüssel steckt im Starter“ – damit „der
Starter veränderte, fehlende oder fremde Dateien erkennt“.

Hervorgegangen aus dem Machbarkeitstest S6 (M8, Schritt 4; der
Prototyp steht in der Git-Historie). Zwei Änderungen gegenüber dem
Prototyp: das
Prüfergebnis ist ein `PruefErgebnis` statt Konsolenausgabe mit
`sys.exit`, und der öffentliche Schlüssel liegt als Python-Konstante
(`ide/integritaet/schluessel.py`) statt als Datei neben dem Programm.
Eine Datei müsste in der gebauten Exe eigens über `--add-data`
mitgegeben werden – genau das ist bei `design/tokens.json` und den
Symbolen schon zweimal vergessen worden und erst beim Start der
fertigen Exe aufgefallen (siehe Arbeitspaket M8).

Der private Schlüssel gehört nie ins Repository (Abschnitt 17.8); er
wird einmalig mit `tools/signieren/manifest_schluessel_erzeugen.py`
erstellt und bleibt auf dem Rechner des Maintainers.
"""

from __future__ import annotations

import base64
import hashlib
import json
import sys
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from ide.integritaet.schluessel import OEFFENTLICHER_SCHLUESSEL_PEM

MANIFEST_DATEINAME = "manifest.json"
FORMAT = "natter-manifest/1"

#: Ordner, die das Manifest nicht erfasst (Abschnitt 17.8): dort liegen
#: Schülerdateien bzw. selbst nachinstallierte Pakete, die sich
#: bestimmungsgemäß ändern.
AUSGENOMMENE_ORDNER = ("benutzer", "pakete-zusatz")

#: Der Ordner neben `Natter.exe`, aus dem der Starter seine Python und
#: seine DLLs lädt (Punkt 399).
#:
#: Bis 0.3.6 war der Starter eine einzelne Datei, die sich bei jedem
#: Start nach `%TEMP%\_MEI…` entpackte; die Prüfsumme von `Natter.exe`
#: deckte damit alles ab, was er lädt. Seit er als Ordner gebaut wird,
#: liegt dieser Teil hier und gehört deshalb mit in die schnelle
#: Prüfung (`ist_kerndatei`).
STARTER_ORDNER = "starter"

#: Wo `pip` die selbst nachinstallierten Pakete ablegt (M13).
#:
#: Mit dem eingefrorenen Bundle gab es dafür `pakete-zusatz`. Seit M13
#: liegt eine gewöhnliche Python-Installation bei, und was ein Schüler
#: über das Menü „Pakete“ holt, landet ganz normal hier.
SITE_PACKAGES = "python/Lib/site-packages/"

#: Was innerhalb von `site-packages` zu Natter selbst gehört. Nur hier
#: ist eine *zusätzliche* Datei ein Grund zur Sorge; überall sonst in
#: `site-packages` ist sie das erwartete Ergebnis einer Installation.
#:
#: `beispielprojekte` und `docs` fehlten bis 0.3.6 (Punkt 230). Ein
#: verändertes Beispiel ging beim nächsten Öffnen als Kopie an alle,
#: die es öffneten, ohne dass eine Prüfung es meldete.
NATTER_EIGEN = (
    "ide", "pcl", "design", "schemas", "templates", "beispielprojekte",
    "docs",
)

#: Was Python bei jedem Start von sich aus ausführt: `.pth`-Dateien in
#: `site-packages` oder `python/Lib` und die Module `sitecustomize` und
#: `usercustomize` aus jedem Ordner in `STARTORDNER`. Sie laufen vor der
#: Prüfung und in jedem Schülerprogramm und könnten die Prüfung selbst
#: aushebeln. Deshalb stehen sie im Manifest und in der schnellen
#: Prüfung bei jedem Start, obwohl sonst alles Übrige in
#: `site-packages` als nachinstalliert gilt (Punkt 230).
STARTMODULE = ("sitecustomize", "usercustomize")

#: Die Ordner, in denen Python beim Start nach `sitecustomize` und
#: `usercustomize` sucht: alles aus `sys.path` der mitgelieferten
#: Python. Sie beginnt mit `python313.zip`, `python\DLLs`,
#: `python\Lib` und `python` selbst; `site-packages` kommt zuletzt.
#: Bis 0.3.6 standen hier nur `site-packages` und `python\Lib`, und
#: eine `sitecustomize.py` in `python\DLLs` lief bei jedem Start,
#: ohne dass die schnelle Prüfung sie sah (Punkt 253).
STARTORDNER = ("python/", "python/DLLs/", "python/Lib/", SITE_PACKAGES)

#: Module der Standardbibliothek, die Python bei jedem Start lädt,
#: bevor eine Zeile Natter läuft, und `runpy` für `pythonw -m ide`.
#: Die meisten davon bringt `python313.dll` eingefroren mit, und die
#: Datei in `python\Lib` wird dann gar nicht gelesen; `encodings`
#: dagegen kommt immer aus `python\Lib`. Geprüft werden alle, weil
#: nicht jede Python-Fassung dieselben einfriert (Punkt 253).
FRUEHE_MODULE = (
    "_collections_abc", "_sitebuiltins", "abc", "codecs", "encodings",
    "genericpath", "importlib", "io", "ntpath", "os", "posixpath",
    "runpy", "site", "stat",
)

#: Die mitgelieferten Bibliotheken, die Natter selbst lädt. „Umgebung
#: prüfen“ vergleicht ihre Prüfsummen und meldet eine Abweichung als
#: Hinweis, nicht als Fehler: `pip` darf sie beim Nachinstallieren
#: eines anderen Pakets anheben (Punkt 230).
BIBLIOTHEKEN = ("PySide6", "shiboken6", "cryptography", "jsonschema")

#: Der Uninstaller, den Inno Setup neben `Natter.exe` legt
#: (`unins000.exe`, `unins000.dat`, bei mehrfacher Installation auch
#: `unins001.…`).
#:
#: Er entsteht während der Installation und kann deshalb gar nicht
#: im Manifest stehen, das beim Bau geschrieben wird. Ohne diese
#: Ausnahme begrüßte jede frisch installierte Natter den Schüler mit
#: „Natter wurde nach der Erstellung verändert" und der Aufforderung,
#: neu zu installieren - was den Uninstaller prompt wieder anlegt
#: (M13, an einer echten Installation aufgefallen).
UNINSTALLER_ANFANG = "unins"

#: Der Lösungsteil an der Meldung aus Abschnitt 17.8. Dass etwas nicht
#: stimmt, sagt der feste Anfang; wer das an einem Schulrechner liest,
#: weiß ohne diesen Satz nicht, ob er weiterarbeiten kann.
WAS_ZU_TUN_IST = (
    "Eigene Projekte sind davon nicht betroffen – sie liegen außerhalb "
    "des Programmordners. Natter neu installieren und dabei den alten "
    "Programmordner ersetzen; bleibt die Meldung, hilft die "
    "Systembetreuung der Schule weiter."
)


class ManifestFehler(Exception):
    """Das Manifest fehlt, ist unlesbar oder hat ein fremdes Format."""


def _erfasst(relativer_pfad: str) -> bool:
    if relativer_pfad == MANIFEST_DATEINAME:
        return False  # das Manifest kann sich nicht selbst enthalten
    # Die `.pyc` in `__pycache__` zählen mit (Punkt 270). Seit 0.3.7
    # erzeugt der Bau sie mit `unchecked-hash`: Python lädt sie, ohne
    # die `.py` daneben anzusehen, und schreibt sie nie neu. Sie sind
    # also der Code, der tatsächlich läuft, und ändern sich beim
    # Benutzen nicht. Stünden sie nicht im Manifest, prüfte der Start
    # die `.py` von `ide` und `pcl`, während eine veränderte `.pyc`
    # daneben unbemerkt liefe. Was Python selbst neu anlegt, etwa zu
    # einem Modul ohne mitgelieferte `.pyc`, gilt dagegen nicht als
    # zusätzlich (siehe `ist_bytecode`); bis 0.3.6 waren das über
    # achtzig Meldungen nach dem ersten Start (M13).
    if ist_startdatei(relativer_pfad):
        return True
    if ist_nachinstalliert(relativer_pfad):
        return False
    if "/" not in relativer_pfad and relativer_pfad.startswith(UNINSTALLER_ANFANG):
        return False
    return relativer_pfad.split("/", 1)[0] not in AUSGENOMMENE_ORDNER


def ist_bytecode(relativer_pfad: str) -> bool:
    """Ob die Datei übersetzter Code in einem `__pycache__` ist.

    Eine solche Datei zählt als verändert oder fehlend, wenn sie im
    Manifest steht, aber nie als zusätzlich. Python lädt eine `.pyc`
    aus `__pycache__` nur zu einer `.py`, die daneben liegt; eine neue
    `.pyc` bringt also keinen Code ins Spiel, den das Manifest nicht
    schon über seine `.py` kennt. Neu angelegt wird sie, wenn ein
    Modul ohne mitgelieferte `.pyc` zum ersten Mal geladen wird.
    """
    return "__pycache__/" in relativer_pfad


def ist_startdatei(relativer_pfad: str) -> bool:
    """Ob Python die Datei bei jedem Start von sich aus ausführt: eine
    `.pth` unmittelbar in `site-packages` oder in `python/Lib`, oder
    `sitecustomize`/`usercustomize` (als Modul oder als Paket) in einem
    der Ordner aus `STARTORDNER`."""
    for ordner in STARTORDNER:
        if not relativer_pfad.startswith(ordner):
            continue
        rest = relativer_pfad[len(ordner):]
        erster = rest.split("/", 1)[0]
        if (
            ordner in (SITE_PACKAGES, "python/Lib/")
            and "/" not in rest
            and rest.lower().endswith(".pth")
        ):
            return True
        # `sitecustomize.py`, `.pyc`, `.cp313-win_amd64.pyd` oder ein
        # Ordner dieses Namens: importiert wird jede davon.
        if erster.split(".", 1)[0] in STARTMODULE:
            return True
    return False


def ist_fruehes_modul(relativer_pfad: str) -> bool:
    """Ob die Datei zu dem gehört, was Python vor Natter lädt: alles in
    `python/DLLs` und die Module aus `FRUEHE_MODULE` in `python/Lib`
    (Punkt 253)."""
    if relativer_pfad.startswith("python/DLLs/"):
        return True
    if not relativer_pfad.startswith("python/Lib/"):
        return False
    rest = relativer_pfad[len("python/Lib/"):]
    if rest.startswith("__pycache__/") and rest.endswith(".pyc"):
        rest = rest[len("__pycache__/"):]
        return "/" not in rest and rest.split(".", 1)[0] in FRUEHE_MODULE
    if "/" in rest:
        return rest.split("/", 1)[0] in FRUEHE_MODULE
    return rest.endswith(".py") and rest.removesuffix(".py") in FRUEHE_MODULE


def geladene_module(programmordner: Path) -> set[str]:
    """Die Dateien der mitgelieferten Python außerhalb von
    `site-packages`, die in diesem Prozess schon geladen sind, relativ
    zu `programmordner`.

    Die schnelle Prüfung läuft erst, nachdem Natter Qt, `cryptography`
    und gut zweihundert Module der Standardbibliothek geladen hat. Was
    davon aus `python/Lib`, `python/DLLs` oder `python` selbst kam, hat
    schon gewirkt, und eine Veränderung daran soll wenigstens gemeldet
    werden. Dazu zählt auch ein Modul, das dort neu abgelegt wurde und
    ein gleichnamiges aus `site-packages` verdeckt: es steht nicht im
    Manifest und erscheint als zusätzliche Datei. `site-packages`
    bleibt draußen; dort gilt, was `ist_nachinstalliert` sagt.
    """
    python = (Path(programmordner) / "python").resolve()
    gefunden: set[str] = set()
    for modul in list(sys.modules.values()):
        # `__cached__` ist die `.pyc`, aus der das Modul tatsächlich
        # kam (Punkt 270); fehlt sie, bleibt es bei der `.py`.
        for datei in (
            getattr(modul, "__file__", None),
            getattr(modul, "__cached__", None),
        ):
            if not isinstance(datei, str):
                continue
            try:
                relativ = Path(datei).resolve().relative_to(python)
            except (OSError, ValueError):
                continue
            name = f"python/{relativ.as_posix()}"
            if name.startswith(SITE_PACKAGES) or ist_nachinstalliert(name):
                continue
            gefunden.add(name)
    return gefunden


def ist_bibliothek(relativer_pfad: str) -> bool:
    """Ob die Datei zu einer der Bibliotheken aus `BIBLIOTHEKEN`
    gehört."""
    return "__pycache__/" not in relativer_pfad and any(
        relativer_pfad.startswith(f"{SITE_PACKAGES}{name}/")
        for name in BIBLIOTHEKEN
    )


def ist_nachinstalliert(relativer_pfad: str) -> bool:
    """Ob die Datei zu einem Paket gehört, das jemand selbst
    nachinstalliert haben kann.

    Solche Dateien kommen gar nicht erst ins Manifest. `pip` löst beim
    Nachinstallieren Abhängigkeiten mit auf und hebt dabei ohne
    Rückfrage etwa numpy oder setuptools an - eine ganz gewöhnliche
    Folge des Menüs „Pakete“. Stünden die mitgelieferten Bibliotheken
    unter Aufsicht, bekäme der Schüler danach bei jedem Start zu lesen,
    Natter sei verändert worden und müsse neu installiert werden.

    Unter Aufsicht bleibt, was Natter selbst ist: `Natter.exe`, die
    mitgelieferte Python und die Pakete aus `NATTER_EIGEN`. Taucht dort
    etwas Neues auf, hat es jemand hineingelegt.

    Dazu gehören auch die Startdateien, die pip für ein Paket in
    `python/Scripts` ablegt (`cowsay.exe`, `pip.exe`, `ruff.exe` …). Bis
    0.3.3 fehlten sie hier: nach „Pakete → Paket installieren …“
    meldete „Umgebung prüfen“, Natter sei verändert, und riet zur
    Neuinstallation (Punkt 40).
    """
    if relativer_pfad.startswith("python/Scripts/"):
        return True
    if not relativer_pfad.startswith(SITE_PACKAGES):
        return False
    rest = relativer_pfad[len(SITE_PACKAGES) :]
    return rest.split("/", 1)[0] not in NATTER_EIGEN


def ist_kerndatei(relativer_pfad: str) -> bool:
    """Die Dateien der schnellen Prüfung bei jedem Start (Abschnitt
    17.8: „Starter-Umfeld, Python, IDE-Code, `pcl` – schnell“).

    Seit M13 sind das drei Gruppen: `Natter.exe` samt dem Ordner
    `STARTER_ORDNER` (Punkt 399), der Kern der mitgelieferten Python
    (`python.exe`, `pythonw.exe`, `python313.dll` - alles unmittelbar
    in `python\\`) sowie der Programmcode von Natter in `ide` und
    `pcl`. Dazu kommen seit Punkt 230 die Dateien, die
    Python bei jedem Start ausführt (`ist_startdatei`). Die gebündelte
    Standardbibliothek liegt als einzelne Dateien in `python/Lib` und
    wäre für „schnell“ zu viel; sie fällt in die vollständige Prüfung,
    die nur über „Werkzeuge → Umgebung prüfen“ läuft. Ausgenommen davon
    ist seit Punkt 253, was Python vor Natter lädt
    (`ist_fruehes_modul`); was darüber hinaus schon geladen ist, nimmt
    `manifest_pruefen` über `geladene_module` dazu.
    """
    if "/" not in relativer_pfad:
        return True
    if relativer_pfad.startswith(f"{STARTER_ORDNER}/"):
        return True
    if ist_startdatei(relativer_pfad) or ist_fruehes_modul(relativer_pfad):
        return True
    if relativer_pfad.startswith("python/") and relativer_pfad.count("/") == 1:
        return True
    return any(relativer_pfad.startswith(f"{SITE_PACKAGES}{paket}/") for paket in ("ide", "pcl"))


def _kandidaten(
    programmordner: Path,
    *,
    nur_kern: bool,
    geladen: frozenset[str] | set[str] = frozenset(),
) -> Iterator[Path]:
    """Die Dateien, die überhaupt angesehen werden.

    Für die schnelle Prüfung wird hier schon eingeschränkt gesucht,
    nicht erst hinterher gefiltert. Die mitgelieferte Python bringt gut
    dreißigtausend Dateien mit; allein durch die hindurchzulaufen kostet
    Sekunden, und die schnelle Prüfung läuft bei jedem Start (M13).
    """
    if not nur_kern:
        yield from programmordner.rglob("*")
        return
    yield from programmordner.glob("*")
    yield from (programmordner / STARTER_ORDNER).rglob("*")
    yield from (programmordner / "python").glob("*")
    yield from (programmordner / "python/DLLs").rglob("*")
    for paket in ("ide", "pcl"):
        yield from (programmordner / SITE_PACKAGES / paket).rglob("*")
    for ordner in (programmordner / SITE_PACKAGES, programmordner / "python/Lib"):
        yield from ordner.glob("*.pth")
    for ordner in STARTORDNER:
        for name in STARTMODULE:
            yield from (programmordner / ordner).glob(f"{name}.*")
            yield from (programmordner / ordner / name).rglob("*")
    lib = programmordner / "python/Lib"
    for name in FRUEHE_MODULE:
        yield lib / f"{name}.py"
        yield from (lib / "__pycache__").glob(f"{name}.*.pyc")
        yield from (lib / name).rglob("*")
    for relativ in geladen:
        yield programmordner / relativ


#: So viele Dateien liest `manifest_erstellen` zugleich.
_PRUEF_FAEDEN = 16


def _pruefsumme(pfad: Path) -> str:
    return hashlib.sha256(pfad.read_bytes()).hexdigest()


def manifest_erstellen(
    programmordner: Path,
    *,
    nur_kern: bool = False,
    geladen: frozenset[str] | set[str] = frozenset(),
) -> dict:
    """SHA-256 je Programmdatei, relativ zu `programmordner`.

    `nur_kern=True` erfasst nur die Dateien der schnellen Prüfung
    (siehe `ist_kerndatei`) und dazu die aus `geladen`. Ohne das stehen
    unter `bibliotheken` zusätzlich die Prüfsummen der Bibliotheken aus
    `BIBLIOTHEKEN`; eine Abweichung dort ist nur ein Hinweis.
    """
    programmordner = Path(programmordner)
    dateien: dict[str, str] = {}
    bibliotheken: dict[str, str] = {}
    kandidaten = _kandidaten(programmordner, nur_kern=nur_kern, geladen=geladen)
    auftraege: list[tuple[dict[str, str], str, Path]] = []
    for pfad in sorted(set(kandidaten)):
        if not pfad.is_file():
            continue
        relativ = pfad.relative_to(programmordner).as_posix()
        if _erfasst(relativ):
            auftraege.append((dateien, relativ, pfad))
        elif not nur_kern and ist_bibliothek(relativ):
            auftraege.append((bibliotheken, relativ, pfad))
    # Mehrere Dateien zugleich (Punkt 407). Beim ersten Start nach
    # einer Installation prüft der Virenschutz jede Datei beim ersten
    # Öffnen. Die schnelle Prüfung liest rund 860 Dateien, viele davon
    # zum ersten Mal: die `.py` von `ide` und `pcl` (geladen werden nur
    # die `.pyc`), `python\DLLs` und `starter`. Nacheinander wartete
    # der erste Start darauf 9,4 bis 10,3 s, zugleich 1,8 bis 2,2 s.
    # Lesen und `sha256` geben die GIL frei.
    with ThreadPoolExecutor(max_workers=_PRUEF_FAEDEN) as pool:
        summen = pool.map(_pruefsumme, (pfad for _, _, pfad in auftraege))
        for (ziel, relativ, _), summe in zip(auftraege, summen, strict=True):
            ziel[relativ] = summe
    manifest: dict = {"format": FORMAT, "dateien": dateien}
    if not nur_kern:
        manifest["bibliotheken"] = bibliotheken
    return manifest


def _signierbarer_inhalt(manifest: dict) -> bytes:
    return json.dumps(manifest, sort_keys=True, ensure_ascii=False).encode("utf-8")


def manifest_signieren(manifest: dict, privater_schluessel_pem: Path) -> dict:
    privat = serialization.load_pem_private_key(
        Path(privater_schluessel_pem).read_bytes(), password=None
    )
    if not isinstance(privat, Ed25519PrivateKey):
        raise ManifestFehler("Erwartet wird ein Ed25519-Schlüssel.")
    signatur = privat.sign(_signierbarer_inhalt(manifest))
    return {
        "manifest": manifest,
        "signatur_base64": base64.b64encode(signatur).decode("ascii"),
    }


def manifest_schreiben(programmordner: Path, privater_schluessel_pem: Path) -> Path:
    """Erzeugt und signiert das Manifest und legt es als
    `manifest.json` in den Programmordner."""
    programmordner = Path(programmordner)
    signiert = manifest_signieren(manifest_erstellen(programmordner), privater_schluessel_pem)
    ziel = programmordner / MANIFEST_DATEINAME
    ziel.write_text(json.dumps(signiert, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return ziel


@dataclass
class PruefErgebnis:
    signatur_gueltig: bool
    fehlend: list[str] = field(default_factory=list)
    fremd: list[str] = field(default_factory=list)
    veraendert: list[str] = field(default_factory=list)
    #: Warum sich das Manifest selbst nicht prüfen ließ (fehlt, unlesbar,
    #: unbekanntes Format) - leer, wenn es sich prüfen ließ.
    manifest_fehler: str = ""
    #: Abweichungen in den Bibliotheken aus `BIBLIOTHEKEN`, je
    #: Bibliothek ein Satz. Sie ändern nichts an `in_ordnung`.
    hinweise: list[str] = field(default_factory=list)

    @property
    def in_ordnung(self) -> bool:
        return (
            self.signatur_gueltig
            and not self.manifest_fehler
            and not (self.fehlend or self.fremd or self.veraendert)
        )

    @property
    def betroffene_dateien(self) -> list[str]:
        return sorted({*self.fehlend, *self.fremd, *self.veraendert})

    def als_meldung(self) -> str:
        """Die Meldung aus Abschnitt 17.8, wörtlich: „Natter wurde nach
        der Erstellung verändert: …“ mit der Liste der betroffenen
        Dateien – und dahinter, was zu tun ist.

        Der feste Anfang steht so in Abschnitt 17.8 und bleibt. Allein
        sagt er aber nur, dass etwas nicht stimmt; wer das an einem
        Schulrechner liest, weiß ohne den Zusatz nicht, ob er
        weiterarbeiten kann.
        """
        if self.in_ordnung:
            return ""
        if self.manifest_fehler:
            return (
                "Natter wurde nach der Erstellung verändert: "
                f"{self.manifest_fehler} {WAS_ZU_TUN_IST}"
            )
        if not self.signatur_gueltig:
            return (
                "Natter wurde nach der Erstellung verändert: die Signatur des "
                f"Prüfsummen-Manifests ist ungültig. {WAS_ZU_TUN_IST}"
            )
        teile = []
        for beschriftung, dateien in (
            ("verändert", self.veraendert),
            ("fehlt", self.fehlend),
            ("zusätzlich", self.fremd),
        ):
            for datei in dateien:
                teile.append(f"{datei} ({beschriftung})")
        return (
            "Natter wurde nach der Erstellung verändert: "
            + ", ".join(teile)
            + f". {WAS_ZU_TUN_IST}"
        )


def _oeffentlicher_schluessel(pem: str | None = None) -> Ed25519PublicKey:
    schluessel = serialization.load_pem_public_key(
        (pem or OEFFENTLICHER_SCHLUESSEL_PEM).encode("ascii")
    )
    if not isinstance(schluessel, Ed25519PublicKey):
        raise ManifestFehler("Der öffentliche Schlüssel ist kein Ed25519-Schlüssel.")
    return schluessel


def manifest_pruefen(
    programmordner: Path,
    *,
    nur_kern: bool = False,
    oeffentlicher_schluessel_pem: str | None = None,
) -> PruefErgebnis:
    """Prüft die Installation in `programmordner` gegen ihr
    `manifest.json`. `nur_kern=True` beschränkt den Prüfsummen-Vergleich
    auf die Kerndateien (schnelle Prüfung bei jedem Start); die Signatur
    des Manifests wird immer vollständig geprüft.

    `oeffentlicher_schluessel_pem` überschreibt den fest eingebauten
    Schlüssel – nur für Tests, die mit einem Wegwerf-Schlüsselpaar
    arbeiten, damit der echte private Schlüssel nirgends gebraucht wird
    (er liegt bewusst nicht im Repository)."""
    programmordner = Path(programmordner)
    manifest_pfad = programmordner / MANIFEST_DATEINAME
    if not manifest_pfad.exists():
        raise ManifestFehler(f"{MANIFEST_DATEINAME} fehlt in {programmordner}.")

    try:
        daten = json.loads(manifest_pfad.read_text(encoding="utf-8"))
        manifest = daten["manifest"]
        signatur = base64.b64decode(daten["signatur_base64"])
    except (ValueError, KeyError) as fehler:
        raise ManifestFehler(f"{MANIFEST_DATEINAME} ist unlesbar.") from fehler

    if manifest.get("format") != FORMAT:
        raise ManifestFehler(f"{MANIFEST_DATEINAME} hat ein unbekanntes Format.")

    try:
        _oeffentlicher_schluessel(oeffentlicher_schluessel_pem).verify(
            signatur, _signierbarer_inhalt(manifest)
        )
    except Exception:
        return PruefErgebnis(signatur_gueltig=False)

    erwartet: dict[str, str] = manifest["dateien"]
    geladen = geladene_module(programmordner) if nur_kern else set()
    erstellt = manifest_erstellen(
        programmordner, nur_kern=nur_kern, geladen=geladen
    )
    aktuell = erstellt["dateien"]
    hinweise: list[str] = []
    if not nur_kern and isinstance(manifest.get("bibliotheken"), dict):
        hinweise = _bibliotheken_vergleichen(
            manifest["bibliotheken"], erstellt["bibliotheken"]
        )

    if nur_kern:
        # `aktuell` ist schon eingeschränkt eingesammelt worden; hier
        # bleibt die Erwartungsseite zu beschneiden, sonst gälte jede
        # nicht gesuchte Datei als fehlend.
        erwartet = {
            name: wert
            for name, wert in erwartet.items()
            if ist_kerndatei(name) or name in geladen
        }

    return PruefErgebnis(
        signatur_gueltig=True,
        hinweise=hinweise,
        fehlend=sorted(set(erwartet) - set(aktuell)),
        fremd=sorted(
            name for name in set(aktuell) - set(erwartet)
            if not ist_bytecode(name)
            and not _pth_eines_pakets(programmordner, name)
        ),
        veraendert=sorted(
            name for name in set(erwartet) & set(aktuell) if erwartet[name] != aktuell[name]
        ),
    )


def _pth_eines_pakets(programmordner: Path, relativer_pfad: str) -> bool:
    """Ob `relativer_pfad` eine `.pth` in `site-packages` ist, die ein
    über `pip` installiertes Paket mitgebracht hat: sie steht in der
    Datei `RECORD` eines `*.dist-info` daneben, das nicht zu Natter
    gehört.

    Manche Pakete legen eine solche Datei an, `pywin32` etwa
    `pywin32.pth`. Seit Punkt 230 gilt jede `.pth` dort als
    Startdatei; nach „Pakete → Paket installieren …“ meldete Natter
    deshalb bei jedem Start, es sei verändert worden, und riet zur
    Neuinstallation, die das Paket gleich wieder mit einrichtete
    (Punkt 447). Eine `.pth` ohne zugehöriges Paket bleibt ein Befund.
    Was der Schutz dabei aufgibt, steht in `docs/bericht.md`,
    Abschnitt 7.5."""
    if not (
        relativer_pfad.startswith(SITE_PACKAGES)
        and relativer_pfad.lower().endswith(".pth")
    ):
        return False
    name = relativer_pfad[len(SITE_PACKAGES):]
    if "/" in name:
        return False
    site_packages = Path(programmordner) / SITE_PACKAGES
    for record in site_packages.glob("*.dist-info/RECORD"):
        paket = record.parent.name.split("-", 1)[0].lower()
        if paket in NATTER_EIGEN or paket == "natter":
            continue
        try:
            zeilen = record.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        if any(zeile.split(",", 1)[0] == name for zeile in zeilen):
            return True
    return False


def _bibliotheken_vergleichen(
    erwartet: dict[str, str], aktuell: dict[str, str]
) -> list[str]:
    """Je Bibliothek ein Satz, wenn ihre Dateien von der Auslieferung
    abweichen."""
    hinweise: list[str] = []
    for name in BIBLIOTHEKEN:
        vorne = f"{SITE_PACKAGES}{name}/"
        soll = {k: v for k, v in erwartet.items() if k.startswith(vorne)}
        ist = {k: v for k, v in aktuell.items() if k.startswith(vorne)}
        if not soll:
            continue
        abweichend = len(set(soll) ^ set(ist)) + sum(
            1 for k in set(soll) & set(ist) if soll[k] != ist[k]
        )
        if abweichend:
            dateien = "Datei weicht" if abweichend == 1 else "Dateien weichen"
            hinweise.append(
                f"{name}: {abweichend} {dateien} von der Auslieferung ab. "
                "Nach „Pakete → Paket installieren …“ kann das eine "
                "angehobene Fassung sein; sonst Natter neu installieren."
            )
    return hinweise
