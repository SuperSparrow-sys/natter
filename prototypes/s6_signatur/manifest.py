"""S6, Teil 2: signiertes Prüfsummen-Manifest mit Ed25519.

Siehe prototypes/s6_signatur/README.md.
"""

import base64
import hashlib
import json
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


def schluesselpaar_erzeugen(zielordner: Path) -> None:
    privat = Ed25519PrivateKey.generate()
    oeffentlich = privat.public_key()

    (zielordner / "privat.pem").write_bytes(
        privat.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    (zielordner / "oeffentlich.pem").write_bytes(
        oeffentlich.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    print(f"Schlüsselpaar erzeugt in {zielordner}")


def manifest_erstellen(programmordner: Path) -> dict:
    dateien = {}
    for pfad in sorted(programmordner.rglob("*")):
        if pfad.is_file():
            relativ = pfad.relative_to(programmordner).as_posix()
            dateien[relativ] = hashlib.sha256(pfad.read_bytes()).hexdigest()
    return {"format": "natter-manifest/1", "dateien": dateien}


def manifest_signieren(manifest: dict, privat_pem: Path, ziel: Path) -> None:
    privat = serialization.load_pem_private_key(privat_pem.read_bytes(), password=None)
    if not isinstance(privat, Ed25519PrivateKey):
        raise TypeError("Erwarte einen Ed25519-Schlüssel")

    inhalt = json.dumps(manifest, sort_keys=True, ensure_ascii=False).encode("utf-8")
    signatur = privat.sign(inhalt)

    ziel.write_text(
        json.dumps(
            {
                "manifest": manifest,
                "signatur_base64": base64.b64encode(signatur).decode("ascii"),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"Signiertes Manifest geschrieben nach {ziel}")


def manifest_pruefen(programmordner: Path, signiertes_manifest: Path, oeffentlich_pem: Path) -> bool:
    daten = json.loads(signiertes_manifest.read_text(encoding="utf-8"))
    manifest = daten["manifest"]
    signatur = base64.b64decode(daten["signatur_base64"])

    oeffentlich = serialization.load_pem_public_key(oeffentlich_pem.read_bytes())
    if not isinstance(oeffentlich, Ed25519PublicKey):
        raise TypeError("Erwarte einen Ed25519-Schlüssel")

    inhalt = json.dumps(manifest, sort_keys=True, ensure_ascii=False).encode("utf-8")
    try:
        oeffentlich.verify(signatur, inhalt)
    except Exception:
        print("FEHLGESCHLAGEN: Signatur des Manifests ist ungültig.")
        return False
    print("OK: Signatur des Manifests ist gültig.")

    aktuell = manifest_erstellen(programmordner)["dateien"]
    erwartet = manifest["dateien"]

    fehlend = sorted(set(erwartet) - set(aktuell))
    fremd = sorted(set(aktuell) - set(erwartet))
    veraendert = sorted(d for d in set(erwartet) & set(aktuell) if erwartet[d] != aktuell[d])

    if not (fehlend or fremd or veraendert):
        print("OK: alle Dateien stimmen mit dem Manifest überein.")
        return True

    if fehlend:
        print("Fehlende Dateien:", fehlend)
    if fremd:
        print("Fremde/zusätzliche Dateien:", fremd)
    if veraendert:
        print("Veränderte Dateien:", veraendert)
    return False


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2:
        print("Verwendung: python manifest.py schluessel|erstellen|pruefen <ordner>")
        sys.exit(1)

    befehl = sys.argv[1]
    hier = Path(__file__).resolve().parent

    if befehl == "schluessel":
        schluesselpaar_erzeugen(hier)
    elif befehl == "erstellen":
        ordner = Path(sys.argv[2])
        manifest = manifest_erstellen(ordner)
        manifest_signieren(manifest, hier / "privat.pem", hier / "manifest.signiert.json")
    elif befehl == "pruefen":
        ordner = Path(sys.argv[2])
        ok = manifest_pruefen(ordner, hier / "manifest.signiert.json", hier / "oeffentlich.pem")
        sys.exit(0 if ok else 1)
    else:
        print(f"Unbekannter Befehl: {befehl}")
        sys.exit(1)


if __name__ == "__main__":
    main()
