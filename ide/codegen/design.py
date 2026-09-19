"""Generator: `.pfm` → `u_*_design.py`.

Siehe README.md, Abschnitt 4.2 (Formularbeschreibung) und 4.3
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
from pcl.properties import (
    BAUM_EIGENSCHAFTEN,
    SAMMLUNGS_EIGENSCHAFTEN,
    VERSCHACHTELTE_EIGENSCHAFTEN,
)

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
    if isinstance(wert, dict):
        # Bäume (`entries`, pcl.properties.BAUM_EIGENSCHAFTEN): ein
        # Menüeintrag. Die Schlüssel werden sortiert ausgegeben, damit
        # zweimal Erzeugen aus derselben .pfm auch zweimal denselben
        # Quelltext ergibt - sonst meldete Git bei jedem Speichern eine
        # Änderung, die gar keine ist.
        paare = ", ".join(
            f"{_python_literal(schluessel)}: {_python_literal(wert[schluessel])}"
            for schluessel in sorted(wert)
        )
        return "{" + paare + "}"
    return repr(wert)


def _baum_zeilen(ziel: str, name: str, eintraege: list[Any]) -> list[str]:
    """Ein Baum (`entries`) über mehrere Zeilen statt in einer einzigen.

    Ein Menü mit drei Untermenüs ergibt sonst eine Zeile von über 800
    Zeichen. Gelesen wird `u_*_design.py` zwar selten - Schüler
    bekommen sie gar nicht zu sehen -, aber wenn, dann weil etwas
    klemmt, und dann ist eine Bildschirmbreite voller geschweifter
    Klammern das Letzte, was hilft.

    Ein Eintrag je Zeile, seine Untereinträge eingerückt darunter.
    """
    zeilen = [f"{_EINRUECKUNG * 2}{ziel}.{name} = ["]
    for eintrag in eintraege:
        zeilen.extend(_eintrag_zeilen(eintrag, 3))
    zeilen.append(f"{_EINRUECKUNG * 2}]")
    return zeilen


def _eintrag_zeilen(eintrag: Any, tiefe: int) -> list[str]:
    if not isinstance(eintrag, dict) or not eintrag.get("children"):
        return [f"{_EINRUECKUNG * tiefe}{_python_literal(eintrag)},"]

    ohne_kinder = {name: wert for name, wert in eintrag.items() if name != "children"}
    paare = ", ".join(
        f"{_python_literal(name)}: {_python_literal(ohne_kinder[name])}"
        for name in sorted(ohne_kinder)
    )
    zeilen = [f"{_EINRUECKUNG * tiefe}{{{paare}, \"children\": ["]
    for kind in eintrag["children"]:
        zeilen.extend(_eintrag_zeilen(kind, tiefe + 1))
    zeilen.append(f"{_EINRUECKUNG * tiefe}]}},")
    return zeilen


def _eigenschaften_zeilen(ziel: str, eigenschaften: dict[str, Any]) -> list[str]:
    # Sammlungen (`items`/`lines`) zuerst: sie füllen das Qt-Widget neu und
    # setzen dabei dessen Auswahl zurück. Stünde `items` hinter
    # `item_index`, ginge eine im Designer gesetzte Vorauswahl beim Start
    # wieder verloren - real an der Mehrwertsteuer-Auswahl des
    # Pizza-Beispielprojekts aufgefallen.
    zuerst = SAMMLUNGS_EIGENSCHAFTEN + BAUM_EIGENSCHAFTEN
    namen = sorted(eigenschaften, key=lambda name: name not in zuerst)
    zeilen: list[str] = []
    for name in namen:
        if name in BAUM_EIGENSCHAFTEN:
            zeilen.extend(_baum_zeilen(ziel, name, eigenschaften[name]))
            continue
        zeilen.append(
            f"{_EINRUECKUNG * 2}{ziel}.{_eigenschaft_pfad(name)} = "
            f"{_python_literal(eigenschaften[name])}"
        )
    return zeilen


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
