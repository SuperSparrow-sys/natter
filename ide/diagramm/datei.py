"""Diagramm: lädt/speichert `.pdiag`-Dateien (Abschnitt 13.7).

Aufbau wie `ide/project/projekt.py` (Dateipfad + rohes `dict`, gegen
`schemas/pdiag.schema.json` validiert) – die einzelnen Diagrammtypen
greifen unterschiedlich auf `daten` zu: Formen-Diagramme über
`shapes`/`connectors`, Struktogramme über den Blockbaum `root`,
Entscheidungstabellen über `conditions`/`actions`. Die Typprüfung
übernimmt bewusst das JSON-Schema statt eigener Python-Klassen je
Diagrammtyp, damit ein von Hand bearbeitetes `.pdiag` dieselben
Fehlermeldungen liefert wie ein in der IDE erzeugtes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ide.diagramm.uml_modell import umrechnen
from ide.pfade import daten_ordner
from ide.schema import pruefen as schema_pruefen

_SCHEMAS_DIR = daten_ordner("schemas")
_PDIAG_SCHEMA = json.loads((_SCHEMAS_DIR / "pdiag.schema.json").read_text(encoding="utf-8"))

#: Diagrammtypen, die die Zeichenfläche über Formen und Verbindungen
#: beschreiben (Abschnitt 13.4). Struktogramm und Entscheidungstabelle
#: haben eigene Strukturen und sind deshalb nicht dabei.
FORMEN_TYPEN = ("class", "use_case", "activity", "state", "sequence")


@dataclass
class Diagramm:
    pfad: Path
    daten: dict[str, Any]

    @property
    def typ(self) -> str:
        return self.daten["type"]

    @property
    def name(self) -> str:
        """Anzeigename; ohne eigenen Eintrag der Dateiname ohne Endung."""
        return self.daten.get("name") or self.pfad.stem

    @property
    def stil(self) -> str:
        return self.daten["style"]

    @property
    def hat_formen(self) -> bool:
        return self.typ in FORMEN_TYPEN

    @classmethod
    def laden(cls, pfad: Path) -> Diagramm:
        pfad = Path(pfad)
        daten = json.loads(pfad.read_text(encoding="utf-8"))
        schema_pruefen(daten, _PDIAG_SCHEMA)
        # Seit M9 Schritt 12 sind Attribute und Operationen strukturiert
        # statt freier Text. Ältere Dateien werden beim Laden einmalig
        # umgerechnet - sonst wären die Abnahmediagramme aus Schritt 11
        # und alles, was Schülerinnen und Schüler schon gezeichnet
        # haben, mit einem Schlag unbrauchbar. Geschrieben wird die neue
        # Form erst beim nächsten Speichern.
        umrechnen(daten)
        return cls(pfad=pfad, daten=daten)

    def speichern(self, pfad: Path | None = None) -> None:
        schema_pruefen(self.daten, _PDIAG_SCHEMA)
        ziel = Path(pfad) if pfad is not None else self.pfad
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(
            json.dumps(self.daten, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        self.pfad = ziel
