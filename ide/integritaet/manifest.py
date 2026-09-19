"""Signiertes Prüfsummen-Manifest einer Natter-Installation.

Siehe konzept-natter.md, Abschnitt 17.8: „beim Build SHA-256-Prüfsummen
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
    return relativer_pfad.split("/", 1)[0] not in AUSGENOMMENE_ORDNER


def ist_kerndatei(relativer_pfad: str) -> bool:
    """Die Dateien der schnellen Prüfung bei jedem Start (Abschnitt
    17.8: „Starter-Umfeld, Python, IDE-Code, `pcl` – schnell“): alles
    direkt neben der Exe sowie die gebündelte Python-Standardbibliothek.
    Die vollständige Prüfung über alle Dateien läuft beim ersten Start
    und über „Werkzeuge → Umgebung prüfen“."""
    return "/" not in relativer_pfad or relativer_pfad == "_internal/base_library.zip"


def manifest_erstellen(programmordner: Path) -> dict:
    """SHA-256 je Programmdatei, relativ zu `programmordner`."""
    dateien: dict[str, str] = {}
    for pfad in sorted(Path(programmordner).rglob("*")):
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
    aktuell = manifest_erstellen(programmordner)["dateien"]
    if nur_kern:
        erwartet = {name: wert for name, wert in erwartet.items() if ist_kerndatei(name)}
        aktuell = {name: wert for name, wert in aktuell.items() if ist_kerndatei(name)}

    return PruefErgebnis(
        signatur_gueltig=True,
        fehlend=sorted(set(erwartet) - set(aktuell)),
        fremd=sorted(set(aktuell) - set(erwartet)),
        veraendert=sorted(
            name for name in set(erwartet) & set(aktuell) if erwartet[name] != aktuell[name]
        ),
    )
