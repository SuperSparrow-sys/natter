"""Signiertes Prüfsummen-Manifest einer Natter-Installation.

Siehe docs/entwicklung.md, Abschnitt 17.8: „beim Build SHA-256-Prüfsummen
aller Programmdateien (ohne `benutzer/` und `pakete-zusatz/`) in
`manifest.json`; das Manifest wird mit einem eigenen Ed25519-Schlüssel
signiert, der öffentliche Schlüssel steckt im Starter“ – damit „der
Starter veränderte, fehlende oder fremde Dateien erkennt“.

Aus `prototypes/s6_signatur/manifest.py` produktiv gemacht (M8,
Schritt 4). Zwei bewusste Änderungen gegenüber dem Prototyp: das
Prüfergebnis ist ein `PruefErgebnis` statt Konsolenausgabe mit
`sys.exit`, und der öffentliche Schlüssel liegt als Python-Konstante
(`ide/integritaet/schluessel.py`) statt als Datei neben dem Programm.
Eine Datei müsste in der gebauten Exe eigens über `--add-data`
mitgegeben werden – genau das ist bei `design/tokens.json` und den
Symbolen schon zweimal vergessen worden und erst beim Start der
fertigen Exe aufgefallen (siehe docs/arbeitspakete/M8.md).

Der private Schlüssel gehört nie ins Repository (Abschnitt 17.8); er
wird einmalig mit `tools/signieren/manifest_schluessel_erzeugen.py`
erstellt und bleibt auf dem Rechner des Maintainers.
"""

from __future__ import annotations

import base64
import hashlib
import json
from collections.abc import Iterator
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

#: Wo `pip` die selbst nachinstallierten Pakete ablegt (M13).
#:
#: Mit dem eingefrorenen Bundle gab es dafür `pakete-zusatz`. Seit M13
#: liegt eine gewöhnliche Python-Installation bei, und was ein Schüler
#: über das Menü „Pakete“ holt, landet ganz normal hier.
SITE_PACKAGES = "python/Lib/site-packages/"

#: Was innerhalb von `site-packages` zu Natter selbst gehört. Nur hier
#: ist eine *zusätzliche* Datei ein Grund zur Sorge; überall sonst in
#: `site-packages` ist sie das erwartete Ergebnis einer Installation.
NATTER_EIGEN = ("ide", "pcl", "design", "schemas", "templates")

#: Der Uninstaller, den Inno Setup neben `Natter.exe` legt
#: (`unins000.exe`, `unins000.dat`, bei mehrfacher Installation auch
#: `unins001.…`).
#:
#: Er entsteht **während** der Installation und kann deshalb gar nicht
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
    # Python legt neben jedem Modul die übersetzte Fassung ab, sobald es
    # das erste Mal importiert wird. Das ist abgeleitetes Zeug, das beim
    # bloßen Benutzen von Natter entsteht - stünde es im Manifest, wäre
    # die Installation schon nach dem ersten Start „verändert“ (M13, in
    # der gebauten Auslieferung nachgemessen: über achtzig Meldungen,
    # bevor überhaupt ein Fenster offen war).
    if "__pycache__/" in relativer_pfad:
        return False
    if ist_nachinstalliert(relativer_pfad):
        return False
    if "/" not in relativer_pfad and relativer_pfad.startswith(UNINSTALLER_ANFANG):
        return False
    return relativer_pfad.split("/", 1)[0] not in AUSGENOMMENE_ORDNER


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
    """
    if not relativer_pfad.startswith(SITE_PACKAGES):
        return False
    rest = relativer_pfad[len(SITE_PACKAGES) :]
    return rest.split("/", 1)[0] not in NATTER_EIGEN


def ist_kerndatei(relativer_pfad: str) -> bool:
    """Die Dateien der schnellen Prüfung bei jedem Start (Abschnitt
    17.8: „Starter-Umfeld, Python, IDE-Code, `pcl` – schnell“).

    Seit M13 sind das drei Gruppen: `Natter.exe` selbst, der Kern der
    mitgelieferten Python (`python.exe`, `pythonw.exe`, `python313.dll`
    - alles unmittelbar in `python\\`) sowie der Programmcode von Natter
    in `ide` und `pcl`. Die gebündelte Standardbibliothek liegt jetzt
    als einzelne Dateien in `python/Lib` statt als eine Zip-Datei und
    wäre für „schnell“ zu viel; sie fällt in die vollständige Prüfung,
    die beim ersten Start und über „Werkzeuge → Umgebung prüfen“ läuft.
    """
    if "/" not in relativer_pfad:
        return True
    if relativer_pfad.startswith("python/") and relativer_pfad.count("/") == 1:
        return True
    return any(relativer_pfad.startswith(f"{SITE_PACKAGES}{paket}/") for paket in ("ide", "pcl"))


def _kandidaten(programmordner: Path, *, nur_kern: bool) -> Iterator[Path]:
    """Die Dateien, die überhaupt angesehen werden.

    Für die schnelle Prüfung wird hier schon **eingeschränkt gesucht**,
    nicht erst hinterher gefiltert. Die mitgelieferte Python bringt gut
    dreißigtausend Dateien mit; allein durch die hindurchzulaufen kostet
    Sekunden, und die schnelle Prüfung läuft bei jedem Start (M13).
    """
    if not nur_kern:
        yield from programmordner.rglob("*")
        return
    yield from programmordner.glob("*")
    yield from (programmordner / "python").glob("*")
    for paket in ("ide", "pcl"):
        yield from (programmordner / SITE_PACKAGES / paket).rglob("*")


def manifest_erstellen(programmordner: Path, *, nur_kern: bool = False) -> dict:
    """SHA-256 je Programmdatei, relativ zu `programmordner`.

    `nur_kern=True` erfasst nur die Dateien der schnellen Prüfung
    (siehe `ist_kerndatei`).
    """
    programmordner = Path(programmordner)
    dateien: dict[str, str] = {}
    for pfad in sorted(_kandidaten(programmordner, nur_kern=nur_kern)):
        if not pfad.is_file():
            continue
        relativ = pfad.relative_to(programmordner).as_posix()
        if _erfasst(relativ):
            dateien[relativ] = hashlib.sha256(pfad.read_bytes()).hexdigest()
    return {"format": FORMAT, "dateien": dateien}


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

    @property
    def in_ordnung(self) -> bool:
        return self.signatur_gueltig and not (self.fehlend or self.fremd or self.veraendert)

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
        raise ManifestFehler(f"{MANIFEST_DATEINAME} ist unlesbar: {fehler}") from fehler

    if manifest.get("format") != FORMAT:
        raise ManifestFehler(f"Unbekanntes Manifest-Format: {manifest.get('format')!r}")

    try:
        _oeffentlicher_schluessel(oeffentlicher_schluessel_pem).verify(
            signatur, _signierbarer_inhalt(manifest)
        )
    except Exception:
        return PruefErgebnis(signatur_gueltig=False)

    erwartet: dict[str, str] = manifest["dateien"]
    aktuell = manifest_erstellen(programmordner, nur_kern=nur_kern)["dateien"]

    if nur_kern:
        # `aktuell` ist schon eingeschränkt eingesammelt worden; hier
        # bleibt die Erwartungsseite zu beschneiden, sonst gälte jede
        # nicht gesuchte Datei als fehlend.
        erwartet = {name: wert for name, wert in erwartet.items() if ist_kerndatei(name)}

    return PruefErgebnis(
        signatur_gueltig=True,
        fehlend=sorted(set(erwartet) - set(aktuell)),
        fremd=sorted(set(aktuell) - set(erwartet)),
        veraendert=sorted(
            name for name in set(erwartet) & set(aktuell) if erwartet[name] != aktuell[name]
        ),
    )
