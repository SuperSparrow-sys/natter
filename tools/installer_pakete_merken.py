"""Beim Update: welche Pakete sind über „Pakete“ nachinstalliert worden?

Das Setup (tools/natter.iss) ersetzt bei einem Update den Ordner
`python` vollständig. Vorher läuft dieses Skript mit der Python der
alten Installation und schreibt die Namen aller Pakete in eine Datei,
die nicht mit Natter ausgeliefert wurden. Nach dem Kopieren installiert
das Setup sie mit der neuen Python wieder (Punkte 26 und 28).

Was mitgeliefert wurde, steht in `python/requirements-auslieferung.txt`
(seit 0.3.x Teil jeder Installation, siehe tools/ide_paketieren.py).
Fehlt die Datei, lässt sich nicht unterscheiden - dann schreibt das
Skript nichts, statt die ganze Installation als „nachinstalliert“
anzusehen.

Nur Standardbibliothek: es läuft mit der alten Python, und die kann
älter sein als diese Fassung von Natter.

    python.exe installer_pakete_merken.py <zieldatei>
"""

from __future__ import annotations

import re
import sys
from importlib.metadata import distributions
from pathlib import Path

#: Kommen immer mit, stehen aber nicht in der Liste aus `uv.lock`.
IMMER_MITGELIEFERT = {"natter", "pip", "pyinstaller", "setuptools", "wheel"}


def normiert(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def mitgeliefert(python_ordner: Path) -> set[str] | None:
    """Die Namen der mitgelieferten Pakete, oder None ohne Liste."""
    liste = python_ordner / "requirements-auslieferung.txt"
    if not liste.is_file():
        return None
    namen = set(IMMER_MITGELIEFERT)
    for zeile in liste.read_text(encoding="utf-8").splitlines():
        treffer = re.match(r"([A-Za-z0-9][A-Za-z0-9._-]*)\s*(==|>=|;|$)", zeile)
        if treffer:
            namen.add(normiert(treffer.group(1)))
    return namen


def nachinstallierte(python_ordner: Path) -> list[str] | None:
    geliefert = mitgeliefert(python_ordner)
    if geliefert is None:
        return None
    site = python_ordner / "Lib" / "site-packages"
    namen = {
        d.metadata["Name"]
        for d in distributions(path=[str(site)])
        if d.metadata["Name"] and normiert(d.metadata["Name"]) not in geliefert
    }
    return sorted(namen, key=str.lower)


def main(argv: list[str]) -> int:
    ziel = Path(argv[1])
    python_ordner = Path(argv[2]) if len(argv) > 2 else Path(sys.executable).parent
    pakete = nachinstallierte(python_ordner)
    if not pakete:
        return 0
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text("\n".join(pakete) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
