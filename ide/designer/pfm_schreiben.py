"""Serialisiert ein im Designer bearbeitetes Formular zurück in eine
`.pfm`-Datei – das Gegenstück zu `ide.codegen.design` (die andere
Richtung, `.pfm` → Python).

Siehe README.md, Abschnitt 4.2: „Gespeichert werden nur
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
from pcl.form import Form
from pcl.properties import (
    BAUM_EIGENSCHAFTEN,
    SAMMLUNGS_EIGENSCHAFTEN,
    VERSCHACHTELTE_EIGENSCHAFTEN,
    eigenschaften,
    ereignisse,
    pfm_wert,
)

_SCHEMAS_DIR = daten_ordner("schemas")
_PFM_SCHEMA = json.loads((_SCHEMAS_DIR / "pfm.schema.json").read_text(encoding="utf-8"))


def _eigenschaften_werte(komponente: Any) -> dict[str, Any]:
    werte: dict[str, Any] = {}
    for name, prop in eigenschaften(type(komponente)).items():
        wert = getattr(komponente, name)
        if wert != prop.standardwert:
            # `pfm_wert`, weil JSON kein Datum kennt: ein `date` steht
            # in der Datei als ISO-Zeichenkette.
            werte[name] = pfm_wert(wert)

    for flacher_name, verschachtelt in VERSCHACHTELTE_EIGENSCHAFTEN.items():
        if not hasattr(komponente, verschachtelt.attribut):
            continue
        wert = getattr(getattr(komponente, verschachtelt.attribut), verschachtelt.unter_attribut)
        if wert != verschachtelt.standardwert:
            werte[flacher_name] = wert

    for name in SAMMLUNGS_EIGENSCHAFTEN:
        sammlung = getattr(komponente, name, None)
        if sammlung:
            werte[name] = list(sammlung)

    for name in BAUM_EIGENSCHAFTEN:
        baum = getattr(komponente, name, None)
        if baum:
            # Knapp statt vollständig: in der `.pfm` soll nur stehen,
            # was jemand wirklich eingestellt hat. Sonst stünde hinter
            # jedem Menüeintrag `"enabled": true, "checked": false,
            # "separator": false` - dreimal die Vorgabe, und die Datei
            # wäre für einen Menschen nicht mehr zu lesen.
            from pcl.components.menus import eintrag_knapp

            werte[name] = [eintrag_knapp(eintrag) for eintrag in baum]

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

    # Ein Behälter trägt seine Kinder in sich - das `children`-Feld gibt
    # es im Schema seit jeher, gefüllt wurde es bis September 2026
    # nicht, weil der Designer gar keine Verschachtelung erzeugen
    # konnte.
    kinder = [_kind_zu_dict(kind_name, kind) for kind_name, kind in kind_komponenten(komponente)]
    if kinder:
        eintrag["children"] = kinder
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
