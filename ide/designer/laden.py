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
from pathlib import Path
from typing import Any

from ide import dateistand
from ide.codegen.design import PfmBeschaedigt, design_code_erzeugen
from ide.schema import json_datei_lesen
from pcl.errors import NatterUnbekannteEigenschaftError
from pcl.form import Form


def unit_lesen(pfad: Path | str) -> str:
    """Der Quelltext einer Unit, mit oder ohne Byte-Order-Markierung.

    Gelesen wird als `utf-8-sig`. Der Editor von Windows speichert mit
    „UTF-8 mit BOM“ drei Bytes vor den Text, die Python beim Start
    überspringt. Mit `utf-8` blieben sie als unsichtbares Zeichen
    U+FEFF stehen, und `ast.parse` meldete einen Syntaxfehler in
    Zeile 1, in der nichts zu sehen ist (Punkt 256). Zurückgeschrieben
    wird ohne Markierung; Python und Natter brauchen sie nicht.

    Eine Unit in einer anderen Kodierung löst `UnicodeDecodeError`
    aus, eine fehlende oder gesperrte `OSError`. Der Aufrufer
    entscheidet, ob das gemeldet oder übergangen wird.
    """
    return Path(pfad).read_text(encoding="utf-8-sig")


def _referenzierte_handler(pfm: dict[str, Any]) -> set[str]:
    """Alle Methodennamen, auf die die `.pfm` verweist, auch die der
    Komponenten in Behältern. Bis Punkt 115 ging das nur eine Ebene
    tief: fehlte einem Knopf in einem Panel seine Methode in der Unit,
    ließ sich das Formular im Designer nicht mehr öffnen."""
    handler = set(pfm.get("events", {}).values())
    for kind in pfm.get("children", []):
        handler.update(_referenzierte_handler(kind))
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


def methoden_im_quelltext(
    quelltext: str, klassenname: str
) -> dict[str, inspect.Signature] | None:
    """Die Methoden, die in `quelltext` in der Klasse `klassenname`
    stehen. `None`, wenn sich der Quelltext nicht übersetzen lässt:
    dann ist nicht bekannt, welche Methoden es gibt, und das ist etwas
    anderes als „keine“."""
    try:
        baum = ast.parse(quelltext)
    except (SyntaxError, ValueError):
        return None
    for knoten in baum.body:
        if isinstance(knoten, ast.ClassDef) and knoten.name == klassenname:
            return {
                f.name: _signatur(f)
                for f in knoten.body
                if isinstance(f, ast.FunctionDef | ast.AsyncFunctionDef)
            }
    return {}


def unit_methoden(
    unit_pfad: Path, klassenname: str
) -> dict[str, inspect.Signature]:
    """Die Methoden, die in der Unit in der Formularklasse stehen.

    Eine Unit, die sich gerade nicht übersetzen lässt, liefert nichts:
    die Auswahl im Objektinspektor zeigt dann nur, was die `.pfm`
    kennt, statt mit einem Fehler abzubrechen.
    """
    try:
        quelltext = unit_lesen(unit_pfad)
    except (OSError, ValueError):
        return {}
    return methoden_im_quelltext(quelltext, klassenname) or {}


def unit_methoden_ergaenzen(klasse: type) -> None:
    """Nimmt die Methoden aus der Unit als Platzhalter in die
    Vorschauklasse auf.

    Der Designer baut das Formular nur aus der `.pfm`. Methoden, die
    in der Unit stehen, aber noch mit keinem Ereignis verknüpft sind,
    fehlten der Klasse deshalb, und der Reiter „Ereignisse“ bot sie
    nicht an. Die Platzhalter tragen die Signatur aus der Unit, damit
    die Auswahl nach der Zahl der Parameter filtern kann.

    Zwischendurch kommen im Editor Methoden dazu. Gelesen wird die
    Unit aber nur, wenn sich Änderungszeit oder Größe der Datei seit
    dem letzten Lesen geändert haben; sonst bleibt die Klasse, wie sie
    ist. Bis Punkt 354 las und übersetzte jeder Aufruf die Datei, und
    der Objektinspektor ruft nach jedem Schritt mit der Pfeiltaste.
    Auf einem Netzlaufwerk mit einer langen Unit dauerte ein Schritt
    so eine halbe Sekunde. `_unit_stand` hält fest, welcher Stand
    zuletzt gelesen wurde; der Objektinspektor erkennt daran, ob sich
    die Auswahl geändert haben kann.
    """
    unit_pfad = getattr(klasse, "_unit_pfad", None)
    if unit_pfad is None:
        return
    stand = dateistand.kennung(unit_pfad)
    if not stand or stand == getattr(klasse, "_unit_stand", None):
        return
    try:
        quelltext = unit_lesen(unit_pfad)
    except (OSError, ValueError):
        return
    klasse._unit_stand = stand
    methoden = methoden_im_quelltext(quelltext, klasse.__name__)
    if methoden is None:
        # Syntaxfehler: welche Methoden es gibt, ist gerade nicht zu
        # sagen. Die Auswahl bleibt dann, wie sie zuletzt war.
        return
    # Platzhalter für Methoden, die nicht mehr in der Unit stehen,
    # fallen heraus (Punkt 150). Sonst bot die Auswahl nach dem
    # Umbenennen einer Komponente weiter den alten Methodennamen an,
    # und wer ihn wählte, bekam ein Programm, das mit `AttributeError`
    # abbrach.
    for name, wert in list(vars(klasse).items()):
        if getattr(wert, "_natter_platzhalter", False) and name not in methoden:
            delattr(klasse, name)
    for name, signatur in methoden.items():
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


#: Größer nimmt Qt keine Zahl für Größe, Lage oder Schrift. Eine
#: größere stieg erst in der Ereignisschleife als `OverflowError`
#: ohne Text aus, also nach dem Bauen des Formulars.
_GROESSTE_ZAHL = 2**31 - 1


def _zahlen_pruefen(eintrag: dict[str, Any], name: str) -> None:
    """Löst `PfmBeschaedigt` aus, wenn eine ganze Zahl in den
    Eigenschaften von `eintrag` oder seinen Kindern zu groß ist."""
    for eigenschaft, wert in (eintrag.get("properties") or {}).items():
        if (
            isinstance(wert, int)
            and not isinstance(wert, bool)
            and abs(wert) > _GROESSTE_ZAHL
        ):
            raise PfmBeschaedigt(
                f"Die Zahl bei {name}.{eigenschaft} ist zu groß."
            )
    for kind in eintrag.get("children") or []:
        if isinstance(kind, dict):
            _zahlen_pruefen(kind, str(kind.get("name", "?")))


def formular_fuer_designer_laden(pfm_pfad: Path) -> Form:
    pfm_pfad = Path(pfm_pfad)
    pfm = json_datei_lesen(pfm_pfad)
    _zahlen_pruefen(pfm, str(pfm.get("class", "Formular")))
    quelltext = design_code_erzeugen(pfm, pfm_pfad.name)

    namensraum: dict[str, Any] = {}
    exec(compile(quelltext, str(pfm_pfad), "exec"), namensraum)
    design_klasse = namensraum[f"{pfm['class']}Design"]

    platzhalter = {name: platzhalter_erzeugen(name) for name in _referenzierte_handler(pfm)}
    vorschau_klasse = type(pfm["class"], (design_klasse,), platzhalter)
    vorschau_klasse._unit_pfad = pfm_pfad.with_suffix(".py")
    # Im Designer bleibt eine Komponente mit `visible = False`
    # sichtbar, sonst ließe sie sich nicht mehr anklicken (`pcl/form.py`).
    vorschau_klasse._entwurfsansicht = True
    # Ein Bild steht in der `.pfm` relativ zum Projektordner; der
    # Designer läuft nicht dort und sucht es über diese Angabe.
    vorschau_klasse._projektordner = pfm_pfad.parent.resolve()
    vorschau_klasse._methoden_nachladen = classmethod(
        unit_methoden_ergaenzen
    )
    # Erst das Formular bauen, dann mit der Unit abgleichen: der
    # erzeugte Code verknüpft die Ereignisse aus der `.pfm` und braucht
    # dafür die Platzhalter, auch für Methoden, die in der Unit fehlen
    # (Punkt 115). Der Abgleich nimmt sie danach aus der Klasse.
    #
    # Werte prüft erst das Bauen: das Schema lässt unter `properties`
    # jedes Objekt zu. Ein falscher Werttyp oder eine Eigenschaft, die
    # diese Fassung nicht kennt (etwa aus einer neueren zu Hause),
    # endete vorher in der allgemeinen Fehlermeldung statt in
    # „beschädigt“.
    try:
        formular = vorschau_klasse()
    except NatterUnbekannteEigenschaftError as fehler:
        raise PfmBeschaedigt(
            f"{fehler} Vielleicht stammt die Datei aus einer neueren "
            "Fassung von Natter."
        ) from fehler
    except OverflowError as fehler:
        raise PfmBeschaedigt("Eine Zahl darin ist zu groß.") from fehler
    except (TypeError, ValueError) as fehler:
        raise PfmBeschaedigt(str(fehler)) from fehler
    unit_methoden_ergaenzen(vorschau_klasse)
    return formular
