"""Generator: `.pfm` → `u_*_design.py`.

Siehe konzept-natter.md, Abschnitt 4.2 (Formularbeschreibung) und 4.3
(erzeugter Formular-Code). Die `.pfm` ist die einzige Quelle für den
Designer und wird nie aus dem generierten Code zurückgelesen; die
generierte Datei wird nie von Hand bearbeitet (Kopfzeile, `AGENTS.md`).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema

from ide.pfade import daten_ordner
from pcl.properties import VERSCHACHTELTE_EIGENSCHAFTEN

_EINRUECKUNG = "    "

_SCHEMAS_DIR = daten_ordner("schemas")
_PFM_SCHEMA = json.loads((_SCHEMAS_DIR / "pfm.schema.json").read_text(encoding="utf-8"))


def _eigenschaft_pfad(name: str) -> str:
    verschachtelt = VERSCHACHTELTE_EIGENSCHAFTEN.get(name)
    if verschachtelt is not None:
        return f"{verschachtelt.attribut}.{verschachtelt.unter_attribut}"
    return name


def _python_literal(wert: Any) -> str:
    if isinstance(wert, str):
        escaped = wert.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    if isinstance(wert, list):
        # Sammlungen (`items`/`lines`, pcl.properties.SAMMLUNGS_EIGENSCHAFTEN)
        # stehen in der .pfm als Liste und werden im erzeugten Code am
        # Stück zugewiesen; der Setter überträgt sie in die Strings-Sammlung.
        return "[" + ", ".join(_python_literal(eintrag) for eintrag in wert) + "]"
    return repr(wert)


def _eigenschaften_zeilen(ziel: str, eigenschaften: dict[str, Any]) -> list[str]:
    return [
        f"{_EINRUECKUNG * 2}{ziel}.{_eigenschaft_pfad(name)} = {_python_literal(wert)}"
        for name, wert in eigenschaften.items()
    ]


def _ereignisse_zeilen(ziel: str, ereignisse: dict[str, str]) -> list[str]:
    return [
        f"{_EINRUECKUNG * 2}{ziel}.{name} = self.{handler}" for name, handler in ereignisse.items()
    ]


def design_code_erzeugen(pfm: dict[str, Any], pfm_dateiname: str) -> str:
    """Erzeugt den Python-Quelltext von `u_*_design.py` aus einer bereits
    geladenen `.pfm`. Validiert `pfm` gegen `schemas/pfm.schema.json`."""

    jsonschema.validate(pfm, _PFM_SCHEMA)

    klassenname = f"{pfm['class']}Design"
    basisklasse = pfm["type"]
    kinder: list[dict[str, Any]] = pfm.get("children", [])
    benoetigte_typen = sorted({basisklasse} | {kind["type"] for kind in kinder})

    zeilen: list[str] = [
        f"# Automatisch erzeugt aus {pfm_dateiname} - nicht bearbeiten",
        f"from pcl import {', '.join(benoetigte_typen)}",
        "",
        "",
        f"class {klassenname}({basisklasse}):",
    ]

    for kind in kinder:
        zeilen.append(f"{_EINRUECKUNG}{kind['name']}: {kind['type']}")
    if kinder:
        zeilen.append("")

    zeilen.append(f"{_EINRUECKUNG}def create_components(self):")
    rumpf_start = len(zeilen)

    zeilen.extend(_eigenschaften_zeilen("self", pfm.get("properties", {})))
    zeilen.extend(_ereignisse_zeilen("self", pfm.get("events", {})))

    for kind in kinder:
        if len(zeilen) > rumpf_start:
            zeilen.append("")
        zeilen.append(f"{_EINRUECKUNG * 2}self.{kind['name']} = {kind['type']}(self)")
        zeilen.extend(_eigenschaften_zeilen(f"self.{kind['name']}", kind.get("properties", {})))
        zeilen.extend(_ereignisse_zeilen(f"self.{kind['name']}", kind.get("events", {})))

    if len(zeilen) == rumpf_start:
        zeilen.append(f"{_EINRUECKUNG * 2}pass")

    return "\n".join(zeilen) + "\n"


def design_datei_erzeugen(pfm_pfad: Path, ziel_pfad: Path) -> str:
    """Liest eine `.pfm`-Datei und schreibt die zugehörige
    `u_*_design.py`. Gibt den erzeugten Quelltext zurück."""
    pfm = json.loads(pfm_pfad.read_text(encoding="utf-8"))
    quelltext = design_code_erzeugen(pfm, pfm_pfad.name)
    ziel_pfad.write_text(quelltext, encoding="utf-8")
    return quelltext
