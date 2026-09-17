"""Erzeugt einmalig das Ed25519-Schlüsselpaar für das signierte
Prüfsummen-Manifest (konzept-natter.md, Abschnitt 17.8).

Der private Schlüssel bleibt auf dem Rechner des Maintainers und ist
über `.gitignore` ausgeschlossen; der öffentliche Teil wird als
Python-Konstante nach `ide/integritaet/schluessel.py` geschrieben, damit
er fest im Starter steckt und in der gebauten Exe nicht fehlen kann.

    uv run python -m tools.signieren.manifest_schluessel_erzeugen
"""

from __future__ import annotations

import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

_PROJEKT_WURZEL = Path(__file__).resolve().parent.parent.parent
PRIVATER_SCHLUESSEL = Path(__file__).resolve().parent / "manifest-privat.pem"
_SCHLUESSEL_MODUL = _PROJEKT_WURZEL / "ide" / "integritaet" / "schluessel.py"

_VORLAGE = '''"""Öffentlicher Ed25519-Schlüssel für das Prüfsummen-Manifest.

Erzeugt von `tools/signieren/manifest_schluessel_erzeugen.py` – nicht von
Hand bearbeiten. Der öffentliche Teil gehört bewusst ins Repository und
in die gebaute Exe (Abschnitt 17.8: „der öffentliche Schlüssel steckt im
Starter“); der private Teil nie.
"""

OEFFENTLICHER_SCHLUESSEL_PEM = """\\
{pem}"""
'''


def schluesselpaar_erzeugen() -> None:
    if PRIVATER_SCHLUESSEL.exists():
        print(f"Abbruch: {PRIVATER_SCHLUESSEL} existiert bereits.")
        print("Ein neuer Schlüssel macht alle bisher signierten Manifeste ungültig.")
        sys.exit(1)

    privat = Ed25519PrivateKey.generate()
    PRIVATER_SCHLUESSEL.write_bytes(
        privat.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    pem = (
        privat.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("ascii")
    )
    _SCHLUESSEL_MODUL.write_text(_VORLAGE.format(pem=pem), encoding="utf-8")

    print(f"Privater Schlüssel: {PRIVATER_SCHLUESSEL} (bleibt lokal, nicht committen)")
    print(f"Öffentlicher Schlüssel eingetragen in: {_SCHLUESSEL_MODUL}")


if __name__ == "__main__":
    schluesselpaar_erzeugen()
