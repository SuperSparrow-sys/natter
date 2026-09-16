"""Führt `harness.py` als eigenen Prozess im Projektordner aus und liefert
strukturierte `Testergebnis`-Objekte statt Text zu parsen (Abschnitt 8.6).
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

_HARNESS_PFAD = Path(__file__).resolve().parent / "harness.py"
_STANDARD_ZEITLIMIT = 60.0


@dataclass(frozen=True)
class Testergebnis:
    id: str
    status: str  # "bestanden" | "fehlgeschlagen" | "fehler"
    dauer: float
    nachricht: str | None = None
    soll: str | None = None
    ist: str | None = None


def tests_ausfuehren(
    projekt_ordner: Path,
    *,
    pattern: str = "test_*.py",
    ziel: str | None = None,
    zeitlimit: float = _STANDARD_ZEITLIMIT,
) -> list[Testergebnis]:
    """Entdeckt und führt Tests im Projektordner aus. `ziel` adressiert
    wie `unittest` selbst ein Modul, eine Klasse oder eine einzelne
    Methode (`test_x`, `test_x.Klasse`, `test_x.Klasse.methode`) – ohne
    `ziel` laufen alle nach `pattern` gefundenen Tests."""
    befehl = [sys.executable, str(_HARNESS_PFAD), "--pattern", pattern]
    if ziel:
        befehl += ["--ziel", ziel]

    ergebnis = subprocess.run(
        befehl,
        cwd=projekt_ordner,
        capture_output=True,
        text=True,
        timeout=zeitlimit,
    )
    if not ergebnis.stdout.strip():
        return []
    return [Testergebnis(**eintrag) for eintrag in json.loads(ergebnis.stdout)]
