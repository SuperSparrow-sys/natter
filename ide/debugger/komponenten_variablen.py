"""Filtert die Variablenliste eines `pcl`-Komponentenobjekts auf seine
`Prop`/`Event`-Namen (Abschnitt 8.1: „`self` mit Komponenten (nur
relevante Eigenschaften wie `text`, `caption`, `checked`, `item_index`),
eigene Objekte aufklappbar“).

Der DAP-Client läuft im IDE-Prozess, das untersuchte Objekt aber im
Schülerprogramm-Prozess – nur der Typname (ein String wie `"Form1"` oder
`"MeinFormular"`) kommt über DAP herüber, nicht die tatsächliche Klasse.
Eine 1:1-Zuordnung zur genauen Unterklasse ist deshalb nicht möglich.
Stattdessen wird eine Positivliste aus allen `Prop`-/`Event`-Namen aller
bekannten `pcl`-Komponententypen gebildet: Attribute mit einem dieser
Namen werden angezeigt, alles andere (private Attribute, Qt-Interna,
pydevds „special variables“/„class variables“-Pseudogruppen) wird
ausgeblendet.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import pcl
from pcl.properties import Komponente, eigenschaften, ereignisse


@lru_cache(maxsize=1)
def _bekannte_eigenschaften_und_ereignisse() -> frozenset[str]:
    namen: set[str] = set()
    for exportname in pcl.__all__:
        wert = getattr(pcl, exportname)
        if isinstance(wert, type) and issubclass(wert, Komponente):
            namen.update(eigenschaften(wert))
            namen.update(ereignisse(wert))
    return frozenset(namen)


def komponenten_variablen_filtern(variablen: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Behält aus `variablen` (Ergebnis eines DAP-`variables`-Requests)
    nur die Einträge, deren Name eine bekannte `Prop`- oder
    `Event`-Eigenschaft ist."""
    bekannt = _bekannte_eigenschaften_und_ereignisse()
    return [v for v in variablen if v.get("name") in bekannt]
