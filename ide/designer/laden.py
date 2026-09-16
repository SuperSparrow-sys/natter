"""Lädt ein Formular aus einer `.pfm`-Datei für die Anzeige im Designer.

Siehe konzept-natter.md, Abschnitt 4.2: „Die `.pfm` ist die einzige
Quelle für den Designer.“ Referenzierte Ereignis-Handler (z. B.
`b_ein_click`) müssen für die reine Designer-Vorschau nicht wirklich
etwas tun – anders als beim echten Programmstart, wo die Unterklasse aus
`u_main.py` sie mit echtem Code füllt (Abschnitt 4.3). Hier werden dafür
wirkungslose Platzhaltermethoden erzeugt, damit `self.on_click =
self.b_ein_click` nicht mit `AttributeError` fehlschlägt.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ide.codegen.design import design_code_erzeugen
from pcl.form import Form


def _referenzierte_handler(pfm: dict[str, Any]) -> set[str]:
    handler = set(pfm.get("events", {}).values())
    for kind in pfm.get("children", []):
        handler.update(kind.get("events", {}).values())
    return handler


def platzhalter_erzeugen(name: str):
    # eigene Funktion statt Lambda im Dict-Comprehension, damit
    # `__name__` den echten Handlernamen trägt statt "<lambda>" -
    # sonst schlägt das spätere Zurückschreiben in die .pfm
    # (ide/designer/pfm_schreiben.py, das `handler.__name__` ausliest)
    # mit ungültigem Python fehl.
    def platzhalter(self, sender):
        return None

    platzhalter.__name__ = name
    return platzhalter


def formular_fuer_designer_laden(pfm_pfad: Path) -> Form:
    pfm_pfad = Path(pfm_pfad)
    pfm = json.loads(pfm_pfad.read_text(encoding="utf-8"))
    quelltext = design_code_erzeugen(pfm, pfm_pfad.name)

    namensraum: dict[str, Any] = {}
    exec(compile(quelltext, str(pfm_pfad), "exec"), namensraum)
    design_klasse = namensraum[f"{pfm['class']}Design"]

    platzhalter = {name: platzhalter_erzeugen(name) for name in _referenzierte_handler(pfm)}
    vorschau_klasse = type(pfm["class"], (design_klasse,), platzhalter)
    return vorschau_klasse()
