"""Ruff-Prüfung vor dem Start (Abschnitt 8.2): Syntaxfehler, unbekannte
Namen, fehlende/ungenutzte Importe, ungenutzte Variablen. Läuft vor jedem
Start; bei Funden wird nicht gestartet, die Funde erscheinen im Panel
„Meldungen“ (Abschnitt 8.2).

`--isolated` ignoriert eine eventuell vorhandene `pyproject.toml`/
`ruff.toml` in der Ordnerhierarchie über dem Projekt (z. B. die von
Natter selbst, wenn ein Beispielprojekt zufällig innerhalb dieses
Repositorys liegt) – die Vorstart-Prüfung soll für jedes Schülerprojekt
gleich streng sein, unabhängig vom Speicherort. Syntaxfehler werden von
Ruff immer gemeldet, auch außerhalb der ausgewählten Regeln.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from ide.project import Projekt

_AUSGEWAEHLTE_REGELN = "E9,F821,F401,F841"


@dataclass(frozen=True)
class RuffFund:
    datei: Path
    zeile: int
    spalte: int
    code: str
    meldung: str

    def __str__(self) -> str:
        return f"{self.datei.name}:{self.zeile}:{self.spalte}: {self.code} {self.meldung}"


def projekt_pruefen(projekt: Projekt) -> list[RuffFund]:
    """Führt `ruff check` gegen den Projektordner aus. Leere Liste bei
    sauberem Projekt."""
    ergebnis = subprocess.run(
        [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "--isolated",
            f"--select={_AUSGEWAEHLTE_REGELN}",
            "--output-format=json",
            str(projekt.ordner),
        ],
        capture_output=True,
        text=True,
    )
    if not ergebnis.stdout.strip():
        return []

    return [
        RuffFund(
            datei=Path(fund["filename"]),
            zeile=fund["location"]["row"],
            spalte=fund["location"]["column"],
            code=fund["code"] or fund["name"],
            meldung=fund["message"],
        )
        for fund in json.loads(ergebnis.stdout)
    ]
