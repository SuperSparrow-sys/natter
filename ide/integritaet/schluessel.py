"""Öffentlicher Ed25519-Schlüssel für das Prüfsummen-Manifest.

Erzeugt von `tools/signieren/manifest_schluessel_erzeugen.py` – nicht von
Hand bearbeiten. Der öffentliche Teil gehört bewusst ins Repository und
in die gebaute Exe (Abschnitt 17.8: „der öffentliche Schlüssel steckt im
Starter“); der private Teil nie.
"""

OEFFENTLICHER_SCHLUESSEL_PEM = """\
-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEAlcAeW0VDNUbrN1MZAREhIDc2luVyP+rH/AvQhB02DSI=
-----END PUBLIC KEY-----
"""
