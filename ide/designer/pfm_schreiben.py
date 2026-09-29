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

from ide.atomar import atomar_schreiben
from ide.inspector.komponentenbaum import kind_komponenten
from ide.pfade import daten_ordner
from ide.schema import pruefen as schema_pruefen
from pcl.control import Control
from pcl.form import Form
from pcl.properties import (
    BAUM_EIGENSCHAFTEN,
    SAMMLUNGS_EIGENSCHAFTEN,
    VERSCHACHTELTE_EIGENSCHAFTEN,
    VERWEIS_EIGENSCHAFTEN,
    eigenschaften,
    ereignisse,
    pfm_wert,
)

_SCHEMAS_DIR = daten_ordner("schemas")
_PFM_SCHEMA = json.loads((_SCHEMAS_DIR / "pfm.schema.json").read_text(encoding="utf-8"))


def _bildpfad_relativ(pfad: str, basis: Path | None) -> str:
    """Ein Bild im Projektordner steht in der `.pfm` relativ zu ihm.

    Der Designer lädt ein abgelegtes Bild über seinen absoluten Pfad,
    denn er läuft nicht im Projektordner. In der Datei hätte dieser
    Pfad nichts zu suchen: auf dem Rechner der Lehrkraft oder im
    exportierten Programm gibt es ihn nicht.
    """
    if basis is None or not pfad:
        return pfad
    kandidat = Path(pfad)
    if not kandidat.is_absolute():
        return pfad
    try:
        return kandidat.resolve().relative_to(basis.resolve()).as_posix()
    except ValueError:
        return pfad


def _namen_der_komponenten(formular: Form) -> dict[int, str]:
    """Wie jede Komponente im Code heißt, nach ihrer Identität.

    Für die Verweise (`popup_menu`): am Knopf hängt das Menü als
    Objekt, in die `.pfm` gehört sein Name. Die Namen sind flach,
    auch für Komponenten in einem Behälter, und stehen deshalb alle
    am Formular.
    """
    return {
        id(wert): name
        for name, wert in vars(formular).items()
        if isinstance(wert, Control)
    }


def _eigenschaften_werte(
    komponente: Any,
    basis: Path | None = None,
    namen: dict[int, str] | None = None,
) -> dict[str, Any]:
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
            if flacher_name == "picture":
                wert = _bildpfad_relativ(wert, basis)
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

    if isinstance(komponente, Control) and not type(komponente).nur_im_designer:
        for name in VERWEIS_EIGENSCHAFTEN:
            ziel = getattr(komponente, name, None)
            # Ein Menü, das es auf dem Formular nicht mehr gibt, fällt
            # hier weg: es hat keinen Namen, unter dem der erzeugte
            # Code es finden könnte.
            ziel_name = (namen or {}).get(id(ziel)) if ziel is not None else None
            if ziel_name is not None:
                werte[name] = ziel_name

    return werte


def _ereignisse_werte(objekt: Any) -> dict[str, str]:
    werte = {}
    for name in ereignisse(type(objekt)):
        handler = getattr(objekt, name)
        if handler is not None:
            werte[name] = handler.__name__
    return werte


def _kind_zu_dict(
    name: str,
    komponente: Any,
    basis: Path | None = None,
    namen: dict[int, str] | None = None,
) -> dict[str, Any]:
    eintrag: dict[str, Any] = {
        "name": name,
        "type": type(komponente).__name__,
        "properties": _eigenschaften_werte(komponente, basis, namen),
    }
    ereignis_werte = _ereignisse_werte(komponente)
    if ereignis_werte:
        eintrag["events"] = ereignis_werte

    # Ein Behälter trägt seine Kinder in sich - das `children`-Feld gibt
    # es im Schema seit jeher, gefüllt wurde es bis dahin
    # nicht, weil der Designer gar keine Verschachtelung erzeugen
    # konnte.
    kinder = [
        _kind_zu_dict(kind_name, kind, basis, namen)
        for kind_name, kind in kind_komponenten(komponente)
    ]
    if kinder:
        eintrag["children"] = kinder
    return eintrag


def kind_als_dict(
    name: str, komponente: Any, namen: dict[int, str] | None = None
) -> dict[str, Any]:
    """Eine Komponente samt Inhalt als Eintrag, wie er unter
    `children` einer `.pfm` steht - für die Zwischenablage des
    Designers. `namen` ordnet Komponenten ihren Namen zu, damit
    Verweise wie `popup_menu` mitkommen."""
    return _kind_zu_dict(name, komponente, None, namen)


def pfm_aus_formular(formular: Form, basis: Path | None = None) -> dict[str, Any]:
    """Die `.pfm` zum Formular. `basis` ist der Ordner der Datei;
    Bildpfade darunter werden relativ zu ihm gespeichert."""
    daten: dict[str, Any] = {
        "format": "pfm/1",
        "class": type(formular).__name__,
        "type": "Form",
        "properties": _eigenschaften_werte(formular, basis),
    }
    ereignis_werte = _ereignisse_werte(formular)
    if ereignis_werte:
        daten["events"] = ereignis_werte

    namen = _namen_der_komponenten(formular)
    kinder = [
        _kind_zu_dict(name, komponente, basis, namen)
        for name, komponente in kind_komponenten(formular)
    ]
    if kinder:
        daten["children"] = kinder

    schema_pruefen(daten, _PFM_SCHEMA)
    return daten


def formular_als_pfm_speichern(formular: Form, pfad: Path) -> None:
    daten = pfm_aus_formular(formular, Path(pfad).parent)
    atomar_schreiben(
        Path(pfad),
        json.dumps(daten, indent=2, ensure_ascii=False) + "\n",
    )
