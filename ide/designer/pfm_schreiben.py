"""Serialisiert ein im Designer bearbeitetes Formular zurück in eine
`.pfm`-Datei – das Gegenstück zu `ide.codegen.design` (die andere
Richtung, `.pfm` → Python).

Siehe konzept-natter.md, Abschnitt 4.2: „Gespeichert werden nur
Eigenschaften, die vom Standardwert abweichen (wie in `.lfm`).“ und
Abschnitt 4.4: „Komponente hinzufügen/verschieben/Eigenschaft ändern →
`.pfm` speichern, `u_main_design.py` neu erzeugen.“ Das Neuerzeugen der
`_design.py` erledigt weiterhin `ide.codegen.design` (Schritt 4 löst
hier nur das Zurückschreiben der `.pfm`).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema

from ide.inspector.komponentenbaum import kind_komponenten
from ide.pfade import daten_ordner
from pcl.components.additional import _STANDARD_BRUSH_FARBE
from pcl.form import Form
from pcl.properties import VERSCHACHTELTE_EIGENSCHAFTEN, eigenschaften, ereignisse

_SCHEMAS_DIR = daten_ordner("schemas")
_PFM_SCHEMA = json.loads((_SCHEMAS_DIR / "pfm.schema.json").read_text(encoding="utf-8"))

# Standardwerte der verschachtelten Eigenschaften aus
# `pcl.properties.VERSCHACHTELTE_EIGENSCHAFTEN`, um sie beim Speichern
# weglassen zu können, wenn sie unverändert sind (Abschnitt 4.2).
_STANDARDWERTE_VERSCHACHTELT = {"brush_color": _STANDARD_BRUSH_FARBE}


def _eigenschaften_werte(komponente: Any) -> dict[str, Any]:
    werte: dict[str, Any] = {}
    for name, prop in eigenschaften(type(komponente)).items():
        wert = getattr(komponente, name)
        if wert != prop.standardwert:
            werte[name] = wert

    for flacher_name, (attribut, unter_attribut) in VERSCHACHTELTE_EIGENSCHAFTEN.items():
        if not hasattr(komponente, attribut):
            continue
        wert = getattr(getattr(komponente, attribut), unter_attribut)
        if wert != _STANDARDWERTE_VERSCHACHTELT.get(flacher_name):
            werte[flacher_name] = wert

    return werte


def _ereignisse_werte(objekt: Any) -> dict[str, str]:
    werte = {}
    for name in ereignisse(type(objekt)):
        handler = getattr(objekt, name)
        if handler is not None:
            werte[name] = handler.__name__
    return werte


def _kind_zu_dict(name: str, komponente: Any) -> dict[str, Any]:
    eintrag: dict[str, Any] = {
        "name": name,
        "type": type(komponente).__name__,
        "properties": _eigenschaften_werte(komponente),
    }
    ereignis_werte = _ereignisse_werte(komponente)
    if ereignis_werte:
        eintrag["events"] = ereignis_werte
    return eintrag


def pfm_aus_formular(formular: Form) -> dict[str, Any]:
    daten: dict[str, Any] = {
        "format": "pfm/1",
        "class": type(formular).__name__,
        "type": "Form",
        "properties": _eigenschaften_werte(formular),
    }
    ereignis_werte = _ereignisse_werte(formular)
    if ereignis_werte:
        daten["events"] = ereignis_werte

    kinder = [_kind_zu_dict(name, komponente) for name, komponente in kind_komponenten(formular)]
    if kinder:
        daten["children"] = kinder

    jsonschema.validate(daten, _PFM_SCHEMA)
    return daten


def formular_als_pfm_speichern(formular: Form, pfad: Path) -> None:
    daten = pfm_aus_formular(formular)
    Path(pfad).write_text(
        json.dumps(daten, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
