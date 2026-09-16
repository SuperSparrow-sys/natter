"""Projekt: lädt/speichert `.natter`-Projektdateien.

Siehe konzept-natter.md, Abschnitt 4.1, 23.2. Die Liste der Units und
Formulare wird aus dem Ordnerinhalt ermittelt statt nur aus der
`.natter` gelesen, weil beim Einbinden einer Unit (Abschnitt 7.4) keine
zusätzliche Eintragung in der Projektdatei vorgesehen ist.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import jsonschema

_SCHEMAS_DIR = Path(__file__).resolve().parent.parent.parent / "schemas"
_PROJECT_SCHEMA = json.loads((_SCHEMAS_DIR / "project.schema.json").read_text(encoding="utf-8"))


@dataclass
class Projekt:
    ordner: Path
    daten: dict[str, Any]

    @property
    def name(self) -> str:
        return self.daten["name"]

    @property
    def typ(self) -> str:
        return self.daten["type"]

    @property
    def haupt_datei(self) -> Path:
        return self.ordner / self.daten["main"]

    @property
    def haupt_unit(self) -> str | None:
        return self.daten.get("main_form")

    @classmethod
    def laden(cls, pfad: Path) -> Projekt:
        """`pfad` ist entweder die `.natter`-Datei selbst oder ihr
        Ordner (dann wird die erste `.natter`-Datei darin verwendet)."""
        if pfad.is_dir():
            kandidaten = sorted(pfad.glob("*.natter"))
            if not kandidaten:
                raise FileNotFoundError(f"Keine .natter-Datei in {pfad} gefunden.")
            pfad = kandidaten[0]

        daten = json.loads(pfad.read_text(encoding="utf-8"))
        jsonschema.validate(daten, _PROJECT_SCHEMA)
        return cls(ordner=pfad.parent, daten=daten)

    def speichern(self, pfad: Path | None = None) -> None:
        jsonschema.validate(self.daten, _PROJECT_SCHEMA)
        ziel = pfad if pfad is not None else self.ordner / f"{self.name}.natter"
        ziel.write_text(
            json.dumps(self.daten, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    def units(self) -> list[Path]:
        """Alle Python-Units im Projektordner, ohne automatisch erzeugte
        `*_design.py`-Dateien (Abschnitt 4.1: nicht bearbeiten)."""
        return sorted(p for p in self.ordner.glob("*.py") if not p.name.endswith("_design.py"))

    def formulare(self) -> list[Path]:
        """Alle Formularbeschreibungen (`.pfm`) im Projektordner."""
        return sorted(self.ordner.glob("*.pfm"))
