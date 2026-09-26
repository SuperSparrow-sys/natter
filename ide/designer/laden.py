"""Lädt ein Formular aus einer `.pfm`-Datei für die Anzeige im Designer.

Siehe README.md, Abschnitt 4.2: „Die `.pfm` ist die einzige
Quelle für den Designer.“ Referenzierte Ereignis-Handler (z. B.
`b_ein_click`) müssen für die reine Designer-Vorschau nicht wirklich
etwas tun – anders als beim echten Programmstart, wo die Unterklasse aus
`u_main.py` sie mit echtem Code füllt (Abschnitt 4.3). Hier werden dafür
wirkungslose Platzhaltermethoden erzeugt, damit `self.on_click =
self.b_ein_click` nicht mit `AttributeError` fehlschlägt.
"""

from __future__ import annotations

import ast
import inspect
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
    def platzhalter(self, sender, *zusatz):
        # `*zusatz` wegen der Maus-Ereignisse, die zusätzlich x und y
        # mitbringen (siehe `pcl.control.EREIGNIS_PARAMETER`). Ohne das
        # flöge im Designer ein TypeError, sobald die Maus über eine
        # Komponente mit zugewiesenem, aber noch leerem Handler fährt.
        return None

    platzhalter.__name__ = name
    platzhalter._natter_platzhalter = True
    return platzhalter


def _signatur(funktion: ast.FunctionDef) -> inspect.Signature:
    """Die Signatur einer Methode, wie sie in der Unit steht."""
    art = inspect.Parameter
    argumente = funktion.args
    parameter = [
        art(a.arg, art.POSITIONAL_ONLY) for a in argumente.posonlyargs
    ]
    parameter += [
        art(a.arg, art.POSITIONAL_OR_KEYWORD) for a in argumente.args
    ]
    if argumente.vararg is not None:
        parameter.append(art(argumente.vararg.arg, art.VAR_POSITIONAL))
    parameter += [
        art(a.arg, art.KEYWORD_ONLY) for a in argumente.kwonlyargs
    ]
    if argumente.kwarg is not None:
        parameter.append(art(argumente.kwarg.arg, art.VAR_KEYWORD))
    return inspect.Signature(parameter)


def unit_methoden(
    unit_pfad: Path, klassenname: str
) -> dict[str, inspect.Signature]:
    """Die Methoden, die in der Unit in der Formularklasse stehen.

    Eine Unit, die sich gerade nicht übersetzen lässt, liefert nichts:
    die Auswahl im Objektinspektor zeigt dann nur, was die `.pfm`
    kennt, statt mit einem Fehler abzubrechen.
    """
    try:
        baum = ast.parse(Path(unit_pfad).read_text(encoding="utf-8"))
    except (OSError, SyntaxError, ValueError):
        return {}
    for knoten in baum.body:
        if isinstance(knoten, ast.ClassDef) and knoten.name == klassenname:
            return {
                f.name: _signatur(f)
                for f in knoten.body
                if isinstance(f, ast.FunctionDef | ast.AsyncFunctionDef)
            }
    return {}


def unit_methoden_ergaenzen(klasse: type) -> None:
    """Nimmt die Methoden aus der Unit als Platzhalter in die
    Vorschauklasse auf.

    Der Designer baut das Formular nur aus der `.pfm`. Methoden, die
    in der Unit stehen, aber noch mit keinem Ereignis verknüpft sind,
    fehlten der Klasse deshalb, und der Reiter „Ereignisse“ bot sie
    nicht an. Die Platzhalter tragen die Signatur aus der Unit, damit
    die Auswahl nach der Zahl der Parameter filtern kann. Gelesen
    wird bei jedem Aufruf neu, weil zwischendurch im Editor Methoden
    dazukommen.
    """
    unit_pfad = getattr(klasse, "_unit_pfad", None)
    if unit_pfad is None:
        return
    for name, signatur in unit_methoden(unit_pfad, klasse.__name__).items():
        if name.startswith("_"):
            continue
        vorhanden = getattr(klasse, name, None)
        if vorhanden is not None and not getattr(
            vorhanden, "_natter_platzhalter", False
        ):
            continue
        platzhalter = platzhalter_erzeugen(name)
        platzhalter.__signature__ = signatur
        setattr(klasse, name, platzhalter)


def formular_fuer_designer_laden(pfm_pfad: Path) -> Form:
    pfm_pfad = Path(pfm_pfad)
    pfm = json.loads(pfm_pfad.read_text(encoding="utf-8"))
    quelltext = design_code_erzeugen(pfm, pfm_pfad.name)

    namensraum: dict[str, Any] = {}
    exec(compile(quelltext, str(pfm_pfad), "exec"), namensraum)
    design_klasse = namensraum[f"{pfm['class']}Design"]

    platzhalter = {name: platzhalter_erzeugen(name) for name in _referenzierte_handler(pfm)}
    vorschau_klasse = type(pfm["class"], (design_klasse,), platzhalter)
    vorschau_klasse._unit_pfad = pfm_pfad.with_suffix(".py")
    vorschau_klasse._methoden_nachladen = classmethod(
        unit_methoden_ergaenzen
    )
    unit_methoden_ergaenzen(vorschau_klasse)
    return vorschau_klasse()
