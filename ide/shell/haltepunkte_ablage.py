"""Haltepunkte je Projekt in den Einstellungen des Benutzers (Punkt 419).

Haltepunkte überstehen das Schließen eines Projekts und einen
Neustart von Natter. Sie stehen in den Einstellungen der IDE und nicht
im Projektordner oder in der `.natter`-Datei: ein Projektordner wird
zwischen Lehrkraft und Klasse kopiert, und die Haltepunkte der
Lehrkraft sollen in den Kopien nicht auftauchen. Das Dateiformat des
Projekts bleibt dadurch unverändert.

Schlüssel ist der aufgelöste Pfad der `.natter`-Datei. Eine Kopie des
Ordners an anderer Stelle hat einen anderen Pfad und damit keine
Haltepunkte. Darunter stehen je Datei, relativ zum Projektordner, die
Zeilen und Bedingungen. Gemerkt werden höchstens `HALTEPUNKTE_MAX`
Projekte, das zuletzt benutzte zuerst; ältere fallen heraus.

Abgelegt wird alles als ein JSON-Text unter einem Schlüssel. Listen
und verschachtelte Wörterbücher kommen aus einer INI-Datei von
`QSettings` je nach Inhalt als Text, Liste oder gar nicht zurück; ein
einzelner Text kommt immer so zurück, wie er hineinging.
"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QSettings

from ide.pfade import einheitlicher_pfad

HALTEPUNKTE_SCHLUESSEL = "debugger/haltepunkte"
HALTEPUNKTE_MAX = 20

#: Haltepunkte je Datei: absoluter Pfad als Text, dazu Zeilen und
#: Bedingungen, wie sie `HauptFenster._gemerkte_haltepunkte` führt.
Stand = dict[str, tuple[set[int], dict[int, str]]]


def _alle(einstellungen: QSettings) -> list[dict]:
    roh = einstellungen.value(HALTEPUNKTE_SCHLUESSEL, "")
    if not isinstance(roh, str) or not roh:
        return []
    try:
        eintraege = json.loads(roh)
    except ValueError:
        return []
    if not isinstance(eintraege, list):
        return []
    return [
        e
        for e in eintraege
        if isinstance(e, dict)
        and isinstance(e.get("projekt"), str)
        and isinstance(e.get("dateien"), dict)
    ]


def _schluessel(projektdatei: Path) -> str:
    # Groß- und Kleinschreibung zählt unter Windows nicht; „K:\Ampel“
    # und „k:\ampel“ sind dasselbe Projekt.
    return str(einheitlicher_pfad(projektdatei)).casefold()


def haltepunkte_laden(
    einstellungen: QSettings, projektdatei: Path, ordner: Path
) -> Stand:
    """Die gemerkten Haltepunkte des Projekts, je Datei mit Pfad unter
    `ordner`. Leer, wenn für diese `.natter`-Datei nichts gemerkt ist."""
    schluessel = _schluessel(projektdatei)
    for eintrag in _alle(einstellungen):
        if eintrag["projekt"].casefold() != schluessel:
            continue
        stand: Stand = {}
        for relativ, werte in eintrag["dateien"].items():
            if not isinstance(werte, dict):
                continue
            try:
                zeilen = {int(z) for z in werte.get("zeilen", [])}
                bedingungen = {
                    int(z): str(b)
                    for z, b in dict(werte.get("bedingungen", {})).items()
                }
            except (TypeError, ValueError):
                continue
            if zeilen:
                stand[str(Path(ordner) / relativ)] = (
                    zeilen,
                    {z: b for z, b in bedingungen.items() if z in zeilen},
                )
        return stand
    return {}


def haltepunkte_speichern(
    einstellungen: QSettings, projektdatei: Path, ordner: Path, stand: Stand
) -> None:
    """Merkt `stand` für das Projekt und rückt es an die erste Stelle.

    Dateien außerhalb von `ordner` gehören zu keinem Projekt und
    bleiben weg. Ohne einen einzigen Haltepunkt verschwindet der
    Eintrag des Projekts, statt einen der Plätze zu belegen."""
    wurzel = einheitlicher_pfad(ordner)
    dateien: dict[str, dict] = {}
    for pfad, (zeilen, bedingungen) in stand.items():
        if not zeilen:
            continue
        voll = einheitlicher_pfad(pfad)
        if not voll.is_relative_to(wurzel):
            continue
        dateien[voll.relative_to(wurzel).as_posix()] = {
            "zeilen": sorted(zeilen),
            "bedingungen": {
                str(z): b for z, b in sorted(bedingungen.items()) if z in zeilen
            },
        }
    schluessel = _schluessel(projektdatei)
    uebrige = [
        e
        for e in _alle(einstellungen)
        if e["projekt"].casefold() != schluessel
    ]
    if dateien:
        eintrag = {
            "projekt": str(einheitlicher_pfad(projektdatei)),
            "dateien": dateien,
        }
        uebrige.insert(0, eintrag)
    einstellungen.setValue(
        HALTEPUNKTE_SCHLUESSEL,
        json.dumps(uebrige[:HALTEPUNKTE_MAX], ensure_ascii=False),
    )
