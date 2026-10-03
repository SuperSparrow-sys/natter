"""Aus einer modellierten UML-Klasse Python-Quelltext erzeugen
(M9 Schritt 13).

gewünscht. Erst weil Attribute und Operationen seit
Schritt 12 strukturiert vorliegen, lässt sich daraus überhaupt
sinnvoller Code erzeugen – aus freiem Text ginge es nicht.

Maßstab ist `beispielprojekte/Ampel/u_ampel.py`: so sieht in diesem
Projekt handgeschriebener Code aus, und so soll auch der erzeugte
aussehen. Also Typangaben statt Kommentare, Sichtbarkeit über die
Namensschreibweise statt über `#private:`-Abschnitte, und leere Rümpfe
statt `return None` – damit niemand denkt, hier stünde schon Logik.

Dia kann das auch, über `dia-uml2python.xsl`; dessen Ausgabe ist
allerdings von 2003 und sähe in diesem Projekt fremd aus.

Reine Funktionen ohne Qt – einzeln testbar.
"""

from __future__ import annotations

import ast
import keyword
import re
from typing import Any

from ide.diagramm.uml_modell import attribute, formname, ist_klasse, operationen

EINRUECKUNG = "    "

#: Verbindungsarten, die zu einer Basisklasse werden (Abschnitt 13.6).
#: „inheritance“ ist die Art, die die Palette des Klassendiagramms
#: anlegt; sie fehlte bis 0.3.3 in dieser Liste, und eine dort
#: gezogene Vererbung kam nie im Klassenkopf an.
VERERBUNGSARTEN = ("inheritance", "generalization", "realization", "implements")

#: Die Arten davon, die ein Interface umsetzen statt von einer Klasse
#: zu erben. Sie stehen im Klassenkopf hinten (Punkt 605).
REALISIERUNGSARTEN = ("realization", "implements")

#: Aggregation und Komposition sagen „hat ein“, nicht „ist ein“. Das
#: Ganze, die Seite mit der Raute, bekommt ein Attribut mit dem Typ
#: des Teils (`_teilattribute`). Bis Punkt 182 stand das nur in diesem
#: Kommentar, und aus `Auto` ◆→ `Motor` wurden zwei Klassen ohne
#: jede Verbindung.
TEILEARTEN = ("aggregation", "composition")

#: Verbindungsarten, aus denen an der Quelle ein Attribut wird. Neben
#: Aggregation und Komposition gehört die gerichtete Assoziation dazu:
#: `Auto` → `Motor` mit dem Rollennamen „motor“ heißt „ein Auto kennt
#: seinen Motor“, und genau das ist im Code ein Attribut. Bis Punkt 619
#: entstanden daraus zwei Klassen ohne Verbindung. Eine Assoziation
#: ohne Pfeil bleibt außen vor: welche Seite die andere kennt, sagt sie
#: nicht.
ATTRIBUTARTEN = (*TEILEARTEN, "directed_association")

#: Aufrufe, die ein neues, veränderliches Objekt liefern.
_VERAENDERLICHE_AUFRUFE = ("list", "dict", "set", "bytearray")


def _bezeichner(name: str, sichtbarkeit: str) -> str:
    """Sichtbarkeit über die Namensschreibweise statt über Kommentare.

    Trägt der Name die Unterstriche schon (weil er so aus einer alten
    Textzeile übernommen wurde), bleiben sie wie sie sind – sonst
    entstünde aus `__zustand` ein `____zustand`.
    """
    sauber = name.strip()
    if not sauber or sauber.startswith("_"):
        return sauber
    if sichtbarkeit == "private":
        return f"__{sauber}"
    if sichtbarkeit == "protected":
        return f"_{sauber}"
    return sauber


#: Die einfachen Typen aus UML und dem Unterricht und ihr Name in
#: Python (Punkt 483). Im Diagramm steht oft „Integer“ oder „String“;
#: unverändert übernommen hieß es im Kopf der Datei, diese Typen
#: müssten noch importiert werden, und ohne den Kopf brach der Code
#: mit `NameError` ab.
UML_TYPEN = {
    "Integer": "int", "integer": "int", "Int": "int",
    "Real": "float", "real": "float", "Double": "float",
    "double": "float", "Float": "float",
    "String": "str", "string": "str", "Char": "str", "char": "str",
    "Boolean": "bool", "boolean": "bool", "Bool": "bool",
    "Void": "None", "void": "None",
}
_UML_TYP = re.compile(r"\b(" + "|".join(UML_TYPEN) + r")\b")


def python_typ(typ: str | None) -> str:
    """Der Typ, wie er in Python heißt: „Integer“ wird `int`, auch in
    `list[Integer]`. Alles andere bleibt, wie es dasteht."""
    return _UML_TYP.sub(lambda t: UML_TYPEN[t[1]], str(typ or "").strip())


def _mit_typ(name: str, typ: str | None) -> str:
    """Typangabe nur, wenn eine da ist – geraten wird nichts."""
    typ = python_typ(typ)
    return f"{name}: {typ}" if typ else name


def _docstring(text: str, tiefe: int) -> list[str]:
    """Kommentar als Docstring.

    Backslashes, drei Anführungszeichen hintereinander und ein
    Anführungszeichen am Ende werden maskiert (Punkt 178). Ein
    Windows-Pfad im Kommentar ergab sonst einen Fehler im Escape
    hinter dem Backslash, und ein Anführungszeichen am Ende schloss
    den Docstring mit vier Zeichen statt drei.
    """
    if not text or not text.strip():
        return []
    einzug = EINRUECKUNG * tiefe
    sauber = text.strip().replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
    # Ein schon maskiertes `\"` am Ende (aus `"""`) bleibt, wie es ist;
    # maskiert verdoppelte sich sonst der Rückstrich (Punkt 582).
    ohne_quote = sauber[:-1]
    rueckstriche = len(ohne_quote) - len(ohne_quote.rstrip("\\"))
    if sauber.endswith('"') and rueckstriche % 2 == 0:
        sauber = ohne_quote + '\\"'
    zeilen = sauber.splitlines()
    if len(zeilen) == 1:
        return [f'{einzug}"""{zeilen[0]}"""']
    return [f'{einzug}"""{zeilen[0]}', *(f"{einzug}{z}" for z in zeilen[1:]), f'{einzug}"""']


def _basisklassen(daten: dict[str, Any], shape: dict[str, Any]) -> list[str]:
    """Basisklassen aus den Verbindungen: eine Verallgemeinerung oder
    Realisierung, die von dieser Klasse ausgeht, zeigt auf die
    Basisklasse.

    Vererbungen kommen vor Realisierungen, gleich in welcher Reihenfolge
    sie gezogen wurden. Für den Konstruktor zählt die erste Basisklasse;
    war die Realisierung zuerst gezogen, reichte `Vogel` seine Werte an
    das Interface `Fliegend` statt an `Tier` weiter, und das Objekt ließ
    sich nicht anlegen (Punkt 605)."""
    formen = {f.get("id"): f for f in daten.get("shapes") or []}
    erben: list[str] = []
    umsetzen: list[str] = []
    for verbindung in daten.get("connectors") or []:
        if verbindung.get("kind") not in VERERBUNGSARTEN:
            continue
        if verbindung.get("from") != shape.get("id"):
            continue
        ziel = formen.get(verbindung.get("to"))
        if ziel is not None and formname(ziel):
            if verbindung.get("kind") in REALISIERUNGSARTEN:
                umsetzen.append(formname(ziel))
            else:
                erben.append(formname(ziel))
    return erben + umsetzen


#: Ein Parameter des Konstruktors: Name, Text in der Signatur und ob
#: er einen Standardwert hat.
_Parameter = tuple[str, str, bool]


def _ist_veraenderlich(wert: Any) -> bool:
    """Ist der Startwert ein neues veränderliches Objekt, etwa `[]`,
    `{}` oder `set()`?"""
    try:
        knoten = ast.parse(str(wert).strip(), mode="eval").body
    except (SyntaxError, ValueError):
        return False
    if isinstance(
        knoten,
        ast.List | ast.Dict | ast.Set | ast.ListComp | ast.DictComp | ast.SetComp,
    ):
        return True
    return (
        isinstance(knoten, ast.Call)
        and isinstance(knoten.func, ast.Name)
        and knoten.func.id in _VERAENDERLICHE_AUFRUFE
    )


def _ist_vielfach(wort: str) -> bool:
    """Steht die Vielfachheit für mehr als ein Teil, etwa `*`, `0..*`,
    `1..4` oder `4`?"""
    if "*" in wort:
        return True
    treffer = re.fullmatch(r"(?:\d+\.\.)?(\d+)", wort)
    return treffer is not None and int(treffer.group(1)) > 1


def _teilattribute(
    daten: dict[str, Any], shape: dict[str, Any]
) -> list[dict[str, Any]]:
    """Attribute aus Aggregation, Komposition (Punkt 182) und gerichteter
    Assoziation (Punkt 619).

    Die Raute sitzt am Ganzen, also an der Quelle der Verbindung. Das
    Ganze bekommt ein Attribut mit dem Typ des Teils. Der Name kommt
    aus der Beschriftung am Teil, wenn dort ein Rollenname steht,
    sonst aus dem Klassennamen in Kleinbuchstaben: aus `Auto` ◆→
    `Motor` wird der Parameter `motor: Motor` und `self.motor =
    motor`. Steht am Teil eine Vielfachheit wie `*`, `0..*` oder `4`,
    ist es eine Liste, die leer beginnt: `self.rad_liste = []`.

    Beschreibt schon ein eigenes Attribut das Teil (gleicher Name oder
    ein Typ, der die Klasse nennt), entsteht kein zweites.
    """
    formen = {f.get("id"): f for f in daten.get("shapes") or []}
    eigene = attribute(shape)
    namen = {str(a.get("name", "")).strip().lstrip("_") for a in eigene}
    typen = " ".join(str(a.get("type") or "") for a in eigene)
    ergebnis: list[dict[str, Any]] = []
    for verbindung in daten.get("connectors") or []:
        if verbindung.get("kind") not in ATTRIBUTARTEN:
            continue
        if verbindung.get("from") != shape.get("id"):
            continue
        ziel = formen.get(verbindung.get("to"))
        if ziel is None or not ist_klasse(ziel):
            continue
        typ = formname(ziel)
        if not _gueltiger_name(typ):
            continue
        if re.search(rf"\b{re.escape(typ)}\b", typen):
            continue
        woerter = str(
            (verbindung.get("labels") or {}).get("to", "")
        ).split()
        rolle = next(
            (
                w.lstrip("+-#~")
                for w in woerter
                if _gueltiger_name(w.lstrip("+-#~"))
            ),
            "",
        )
        vielfach = any(_ist_vielfach(w) for w in woerter)
        name = rolle or typ.lower()
        if vielfach and not rolle:
            name = f"{name}_liste"
        if not _gueltiger_name(name) or name in namen:
            continue
        namen.add(name)
        if vielfach:
            ergebnis.append(
                {"name": name, "type": f"list[{typ}]", "value": "[]"}
            )
        else:
            ergebnis.append({"name": name, "type": typ})
    return ergebnis


def _instanzattribute(
    shape: dict[str, Any], daten: dict[str, Any] | None
) -> list[dict[str, Any]]:
    """Die Attribute, die jedes Objekt für sich hat: die eigenen ohne
    Klassen-Gültigkeitsbereich und die aus Aggregation und
    Komposition."""
    eigene = [a for a in attribute(shape) if not a.get("class_scope")]
    return eigene + (_teilattribute(daten, shape) if daten else [])


def _eigene_parameter(
    shape: dict[str, Any], daten: dict[str, Any] | None
) -> tuple[list[_Parameter], list[str]]:
    """Parameter und Zuweisungen aus den Instanzattributen der Klasse.

    Ein veränderlicher Startwert wie `[]` wird kein Parameter (Punkt
    161). Als Vorgabe eines Parameters entstünde die Liste ein einziges
    Mal, beim Ausführen des `def`, und alle Objekte teilten sie sich:
    nach `a.schueler.append("Anna")` stand Anna auch in `b.schueler`.
    `self.schueler = []` legt für jedes Objekt eine eigene Liste an
    und ist die Schreibweise, die im Unterricht ohnehin vorkommt.
    """
    parameter: list[_Parameter] = []
    zuweisungen: list[str] = []
    for attribut in _instanzattribute(shape, daten):
        roh = str(attribut.get("name", "")).strip().lstrip("_")
        if not roh:
            continue
        feld = _bezeichner(
            str(attribut.get("name", "")), attribut.get("visibility", "public")
        )
        wert = attribut.get("value")
        if wert and _ist_veraenderlich(wert):
            zuweisungen.append(
                f"{EINRUECKUNG * 2}self.{feld} = {str(wert).strip()}"
            )
            continue
        stueck = _mit_typ(roh, attribut.get("type"))
        if wert:
            stueck += f" = {wert}"
        parameter.append((roh, stueck, bool(wert)))
        zuweisungen.append(f"{EINRUECKUNG * 2}self.{feld} = {roh}")
    return parameter, zuweisungen


def _zusammenfuegen(
    geerbt: list[_Parameter], eigene: list[_Parameter]
) -> list[_Parameter]:
    """Parameter der Basisklasse vorn, dann die eigenen, und alle mit
    Standardwert ans Ende (Punkt 117). In der Reihenfolge des
    Diagramms ergab ein Attribut mit Startwert vor einem ohne
    `def __init__(self, stand: float = 0, inhaber: str)`, und das
    lässt sich nicht übersetzen. Heißt ein eigenes Attribut wie ein
    Parameter der Basisklasse, gibt es den Parameter nur einmal."""
    bekannt = {name for name, _, _ in geerbt}
    alle = [*geerbt, *(p for p in eigene if p[0] not in bekannt)]
    return [p for p in alle if not p[2]] + [p for p in alle if p[2]]


def _modellierter_konstruktor(shape: dict[str, Any]) -> dict[str, Any] | None:
    return next(
        (
            o
            for o in operationen(shape)
            if str(o.get("name", "")).strip() == "__init__"
        ),
        None,
    )


def _basisform(
    daten: dict[str, Any] | None, shape: dict[str, Any]
) -> tuple[str, dict[str, Any] | None]:
    """Name und Form der ersten Basisklasse. Die Form ist `None`, wenn
    die Basisklasse nicht im Diagramm steht; der Name ist leer, wenn
    es keine gibt. Bei mehreren Basisklassen zählt für den Konstruktor
    nur die erste."""
    namen = _basisklassen(daten or {}, shape)
    if not namen:
        return "", None
    klassen = {
        formname(f): f
        for f in (daten or {}).get("shapes") or []
        if ist_klasse(f)
    }
    return namen[0], klassen.get(namen[0])


def _konstruktor_parameter(
    shape: dict[str, Any], daten: dict[str, Any] | None, pfad: frozenset[int]
) -> list[_Parameter]:
    """Die Parameter, die der Konstruktor einer Klasse im Diagramm
    erwartet, ohne `self` und in der Reihenfolge der Signatur."""
    if id(shape) in pfad:
        return []
    modelliert = _modellierter_konstruktor(shape)
    if modelliert is not None:
        ergebnis: list[_Parameter] = []
        for p in modelliert.get("parameters") or []:
            name = str(p.get("name", "")).strip()
            if not name or name == "self":
                continue
            stueck = _mit_typ(name, p.get("type"))
            if p.get("default"):
                stueck += f" = {p['default']}"
            ergebnis.append((name, stueck, bool(p.get("default"))))
        return ergebnis
    _, basis = _basisform(daten, shape)
    geerbt = (
        _konstruktor_parameter(basis, daten, pfad | {id(shape)})
        if basis is not None
        else []
    )
    eigene, zuweisungen = _eigene_parameter(shape, daten)
    if not zuweisungen:
        # Ohne eigenes `__init__` gilt das der Basisklasse.
        return geerbt
    return _zusammenfuegen(geerbt, eigene)


def _init_zeilen(
    shape: dict[str, Any], daten: dict[str, Any] | None = None
) -> list[str]:
    """`__init__` aus den Attributen. Attribute mit
    Klassen-Gültigkeitsbereich gehören nicht hierher – sie stehen als
    Klassenattribut oben.

    Hat die Klasse eine Basisklasse, ruft der Konstruktor zuerst
    `super().__init__(…)` auf (Punkt 149). Steht die Basisklasse im
    Diagramm, kommen ihre Parameter vorn in die eigene Signatur und
    werden weitergereicht: aus `Tier` mit `name` und `Hund` mit
    `rasse` wird `Hund("Bello", "Dackel")`, und `name` setzt der
    Konstruktor von `Tier`. Vorher bekam `Hund` nur `rasse`, und
    `name` ließ sich gar nicht übergeben.
    """
    # Ist der Konstruktor im Diagramm selbst modelliert, gilt dieser –
    # sonst stünde `__init__` zweimal in der Klasse. Genau das ist beim
    # TAmpel-Abnahmediagramm passiert, das `+__init__(...)` als
    # Operation führt.
    if _modellierter_konstruktor(shape) is not None:
        return []

    eigene, zuweisungen = _eigene_parameter(shape, daten)
    if not zuweisungen:
        return []

    basisname, basis = _basisform(daten, shape)
    oben: list[str] = []
    geerbt: list[_Parameter] = []
    if basis is not None:
        geerbt = _konstruktor_parameter(basis, daten, frozenset({id(shape)}))
        argumente = ", ".join(name for name, _, _ in geerbt)
        oben.append(f"{EINRUECKUNG * 2}super().__init__({argumente})")
    elif basisname:
        einzug = EINRUECKUNG * 2
        oben.extend(
            [
                f"{einzug}# „{basisname}“ steht nicht im Diagramm. Braucht",
                f"{einzug}# ihr Konstruktor Werte, gehören sie in die Klammern.",
                f"{einzug}super().__init__()",
            ]
        )

    parameter = ["self", *(t for _, t, _ in _zusammenfuegen(geerbt, eigene))]
    return [
        f"{EINRUECKUNG}def __init__({', '.join(parameter)}) -> None:",
        *oben,
        *zuweisungen,
        "",
    ]


def _klassenattribute(shape: dict[str, Any]) -> list[str]:
    zeilen = []
    for attribut in attribute(shape):
        if not attribut.get("class_scope"):
            continue
        name = _bezeichner(
            str(attribut.get("name", "")), attribut.get("visibility", "public")
        )
        if not name:
            continue
        zeilen.append(
            f"{EINRUECKUNG}{_mit_typ(name, attribut.get('type'))}"
            f" = {attribut.get('value') or 'None'}"
        )
    return [*zeilen, ""] if zeilen else []


def _zuweisungen_fuer_init(
    operation: dict[str, Any],
    shape: dict[str, Any],
    daten: dict[str, Any] | None = None,
) -> list[str]:
    """Die Rumpfzeilen eines selbst modellierten `__init__`.

    Ist der Konstruktor im Diagramm eingetragen, erzeugt
    `_init_zeilen` keinen zweiten - so weit richtig. Bis September
    2026 blieb der Rumpf dann aber bei `...`, und die modellierten
    Attribute standen nirgends: aus einer Klasse `Buchung` mit
    `+datum`, `+zweck`, `+betrag` und `+__init__(datum, zweck,
    betrag)` wurde ein Konstruktor, der nichts tut, und drei
    Attribute, die es nie gibt. Im Durchgang durch den Schülerweg
    aufgefallen.

    Zugewiesen wird nur, was sich eindeutig zuordnen lässt: ein
    Parameter, dessen Name zu einem Attribut passt. Alles andere
    bleibt dem Schüler - hier soll keine Logik entstehen, nur das,
    was er ohnehin abschreiben müsste.

    Ein Attribut mit Startwert, das kein Parameter ist, bekommt diesen
    Startwert: aus `-stand: float = 0` und `__init__(inhaber)` wird
    `self.__stand = 0`. Bis Punkt 606 fehlte die Zeile, und jede
    Methode, die den Kontostand las, brach mit `AttributeError` ab.
    """
    instanz = [
        a for a in _instanzattribute(shape, daten)
        if str(a.get("name", "")).strip()
    ]
    felder = {
        str(a.get("name", "")).strip().lstrip("_"): _bezeichner(
            str(a.get("name", "")), a.get("visibility", "public")
        )
        for a in instanz
    }
    zeilen = []
    belegt = set()
    for parameter in operation.get("parameters") or []:
        roh = str(parameter.get("name", "")).strip().lstrip("_")
        if roh in felder:
            zeilen.append(f"{EINRUECKUNG * 2}self.{felder[roh]} = {roh}")
            belegt.add(roh)
    for attribut in instanz:
        roh = str(attribut.get("name", "")).strip().lstrip("_")
        wert = str(attribut.get("value") or "").strip()
        if roh in belegt or not wert:
            continue
        zeilen.append(f"{EINRUECKUNG * 2}self.{felder[roh]} = {wert}")
    return zeilen


def _basisaufruf_fuer_init(
    operation: dict[str, Any],
    shape: dict[str, Any],
    daten: dict[str, Any] | None = None,
) -> list[str]:
    """`super().__init__(…)` am Anfang eines selbst modellierten
    `__init__` einer Unterklasse (Punkt 283).

    Ohne diesen Aufruf setzte der Konstruktor nur die eigenen
    Attribute: aus `Hund.__init__(name, rasse)` mit der Basisklasse
    `Tier` wurde ein Konstruktor, der `name` annimmt und liegen
    lässt, und `Hund("Bello", "Dackel").name` brach mit
    `AttributeError` ab. Ohne modellierten Konstruktor gilt dasselbe
    wie in `_init_zeilen` (Punkt 149).

    Weitergereicht wird jeder Parameter der Basisklasse, der auch im
    modellierten Konstruktor steht. Fehlt davor einer, gehen die
    folgenden mit Namen hinüber, damit keiner an der falschen Stelle
    landet. Fehlt ein Wert, den die Basisklasse verlangt, sagt das
    ein Kommentar über dem Aufruf.
    """
    basisname, basis = _basisform(daten, shape)
    einzug = EINRUECKUNG * 2
    if basis is None:
        if not basisname:
            return []
        return [
            f"{einzug}# „{basisname}“ steht nicht im Diagramm. Braucht",
            f"{einzug}# ihr Konstruktor Werte, gehören sie in die Klammern.",
            f"{einzug}super().__init__()",
        ]
    vorhanden = {
        str(p.get("name", "")).strip()
        for p in operation.get("parameters") or []
    }
    geerbt = _konstruktor_parameter(basis, daten, frozenset({id(shape)}))
    argumente: list[str] = []
    fehlend: list[str] = []
    mit_namen = False
    for name, _, hat_vorgabe in geerbt:
        if name not in vorhanden:
            mit_namen = True
            if not hat_vorgabe:
                fehlend.append(name)
            continue
        argumente.append(f"{name}={name}" if mit_namen else name)
    zeilen = []
    if fehlend:
        zeilen.append(
            f"{einzug}# Der Konstruktor von „{basisname}“ erwartet "
            f"außerdem: {', '.join(fehlend)}"
        )
    zeilen.append(f"{einzug}super().__init__({', '.join(argumente)})")
    return zeilen


def _operation_zeilen(
    operation: dict[str, Any],
    shape: dict[str, Any] | None = None,
    daten: dict[str, Any] | None = None,
) -> list[str]:
    name = _bezeichner(
        str(operation.get("name", "")), operation.get("visibility", "public")
    )
    if not name:
        return []

    parameter = [p for p in operation.get("parameters") or []]
    klassenweit = bool(operation.get("class_scope"))
    # Eine „Anfrage“ bleibt eine gewöhnliche Methode. Bis 0.4.3 wurde
    # sie ohne Parameter zu `@property`; das Diagramm zeigt sie aber mit
    # Klammern, „+getStand(): float“, und `k.getStand()` endete dann mit
    # „'float' object is not callable“ (Punkt 630).

    zeilen: list[str] = []
    if klassenweit:
        zeilen.append(f"{EINRUECKUNG}@staticmethod")

    argumente = [] if klassenweit else ["self"]
    for p in parameter:
        stueck = _mit_typ(str(p.get("name", "")).strip(), p.get("type"))
        if p.get("default"):
            stueck += f" = {p['default']}"
        if stueck:
            argumente.append(stueck)

    rueckgabe = python_typ(operation.get("type"))
    kopf = f"{EINRUECKUNG}def {name}({', '.join(argumente)})"
    kopf += f" -> {rueckgabe}:" if rueckgabe else ":"
    zeilen.append(kopf)
    zeilen.extend(_docstring(str(operation.get("comment", "")), 2))

    zuweisungen = (
        [
            *_basisaufruf_fuer_init(operation, shape, daten),
            *_zuweisungen_fuer_init(operation, shape, daten),
        ]
        if shape is not None and name == "__init__"
        else []
    )
    if operation.get("inheritance") == "abstract":
        # Abstrakt heißt: muss von einer Unterklasse gefüllt werden.
        # Ein stiller `...`-Rumpf verschluckte den Fehler zur Laufzeit.
        zeilen.append(f"{EINRUECKUNG * 2}raise NotImplementedError")
    elif zuweisungen:
        zeilen.extend(zuweisungen)
    else:
        zeilen.append(f"{EINRUECKUNG * 2}...")
    zeilen.append("")
    return zeilen


def klasse_als_python(shape: dict[str, Any], daten: dict[str, Any] | None = None) -> str:
    """Eine UML-Klasse als Python-Klasse."""
    daten = daten or {}
    name = formname(shape) or "Klasse"

    basis = _basisklassen(daten, shape)
    # Eine Vorlageklasse in der Schreibweise von Python 3.12 an:
    # `class Stapel[T]:` braucht weder `Generic` noch `TypeVar`. Bis
    # Punkt 160 entstand `class Stapel(Generic[T]):` ohne `T`, und der
    # Import brach mit `NameError` ab.
    vorlage = ""
    if shape.get("template") and (shape.get("template_parameters") or []):
        vorlage = "[" + ", ".join(
            str(p.get("name") or "T").strip() or "T"
            for p in shape["template_parameters"]
        ) + "]"
    kopf = f"class {name}{vorlage}"
    kopf += f"({', '.join(basis)}):" if basis else ":"

    rumpf: list[str] = []
    rumpf.extend(_docstring(str(shape.get("comment", "")), 1))
    if rumpf:
        rumpf.append("")
    rumpf.extend(_klassenattribute(shape))
    rumpf.extend(_init_zeilen(shape, daten))
    for operation in operationen(shape):
        rumpf.extend(_operation_zeilen(operation, shape, daten))

    if not rumpf:
        # Eine Klasse ohne Inhalt braucht trotzdem einen Rumpf.
        rumpf = [f"{EINRUECKUNG}..."]
    while rumpf and rumpf[-1] == "":
        rumpf.pop()
    return "\n".join([kopf, *rumpf]) + "\n"


def _gueltiger_name(name: str) -> bool:
    return name.isidentifier() and not keyword.iskeyword(name)


def ungueltige_namen(
    daten: dict[str, Any], shape: dict[str, Any] | None = None
) -> list[str]:
    """Namen im Diagramm, die in Python keine Bezeichner sind, als
    deutsche Meldungen.

    Steht im Feld „Name“ eines Attributs „stand: float“, entstand bis
    0.3.3 die Zeile `self.__stand: float = stand: float`. Das ist ein
    Syntaxfehler in der Unit, und die Prüfung vor dem Start blockierte
    danach jeden Start des Projekts. Ein leerer Name ist kein Fehler,
    den übergeht der Erzeuger ohnehin.

    Seit Punkt 117 prüft sie auch Typen, Startwerte und die
    Reihenfolge der Parameter einer Operation. Ein Typ wie „Liste von
    int“ oder `def f(self, a = 1, b)` ergab eine Unit, die sich nicht
    übersetzen ließ, und hier stand nichts davon. Zum Schluss wird der
    erzeugte Code jeder Klasse übersetzt; was dabei noch scheitert,
    erscheint mit der Zeile.
    """
    if shape is not None and not ist_klasse(shape):
        return []
    klassen = [shape] if shape is not None else [
        f for f in daten.get("shapes") or [] if ist_klasse(f)
    ]
    meldungen: list[str] = []

    def pruefen(name: Any, was: str) -> None:
        text = str(name or "").strip()
        if text and not _gueltiger_name(text):
            meldungen.append(f"{was} „{text}“ ist kein gültiger Python-Name.")

    def ausdruck_pruefen(wert: Any, was: str) -> None:
        text = str(wert or "").strip()
        if text and not _gueltiger_ausdruck(text):
            meldungen.append(f"{was} „{text}“ ist kein gültiger Python-Ausdruck.")

    for klasse in klassen:
        klassenname = formname(klasse)
        pruefen(klassenname, "Die Klasse")
        for attribut in attribute(klasse):
            pruefen(attribut.get("name"), f"{klassenname}: Das Attribut")
            feld = str(attribut.get("name", "")).strip()
            ausdruck_pruefen(
                attribut.get("type"), f"{klassenname}.{feld}: Der Typ"
            )
            ausdruck_pruefen(
                attribut.get("value"), f"{klassenname}.{feld}: Der Startwert"
            )
        for operation in operationen(klasse):
            pruefen(operation.get("name"), f"{klassenname}: Die Operation")
            ort = f"{klassenname}.{str(operation.get('name', '')).strip()}"
            ausdruck_pruefen(operation.get("type"), f"{ort}: Der Rückgabetyp")
            mit_standardwert = ""
            for parameter in operation.get("parameters") or []:
                name = str(parameter.get("name", "")).strip()
                pruefen(name, f"{ort}: Der Parameter")
                ausdruck_pruefen(
                    parameter.get("type"), f"{ort}: Der Typ von „{name}“"
                )
                ausdruck_pruefen(
                    parameter.get("default"),
                    f"{ort}: Der Standardwert von „{name}“",
                )
                if not name:
                    continue
                if parameter.get("default"):
                    mit_standardwert = mit_standardwert or name
                elif mit_standardwert:
                    meldungen.append(
                        f"{ort}: Der Parameter „{name}“ hat keinen "
                        f"Standardwert und steht hinter „{mit_standardwert}“, "
                        "der einen hat. Parameter mit Standardwert gehören "
                        "ans Ende."
                    )
    meldungen.extend(_doppelte_und_kreise(daten, klassen))
    for klasse in klassen:
        meldungen.extend(_gleichnamige_operationen(klasse, daten))
    # Übersetzt wird erst, wenn alle Angaben für sich stimmen. Seit
    # Punkt 149 reicht eine Unterklasse die Parameter ihrer
    # Basisklasse weiter, und ein falscher Name dort erschiene sonst
    # ein zweites Mal als Übersetzungsfehler der Unterklasse.
    if meldungen:
        return meldungen
    for klasse in klassen:
        fehler = _uebersetzungsfehler(klasse_als_python(klasse, daten))
        if fehler:
            meldungen.append(f"{formname(klasse)}: {fehler}")
    return meldungen


def _gleichnamige_operationen(
    klasse: dict[str, Any], daten: dict[str, Any]
) -> list[str]:
    """Eine Operation, die im Code genauso heißt wie ein Attribut.

    Aus dem öffentlichen Attribut `alter` und der Anfrage `alter()`
    entstanden `self.alter = alter` im Konstruktor und `@property def
    alter`, und `Person(3)` scheiterte an der Eigenschaft ohne Setter;
    bei einer gewöhnlichen Methode verdeckte das Attribut sie, und
    `p.alter()` brach ab (Punkt 607). Das übliche Muster ist ein
    privates Attribut `-alter` mit der öffentlichen Anfrage `alter()`:
    dort heißen sie im Code `__alter` und `alter` und vertragen sich.
    """
    felder = {
        _bezeichner(str(a.get("name", "")), a.get("visibility", "public"))
        for a in _instanzattribute(klasse, daten)
        if str(a.get("name", "")).strip()
    }
    meldungen = []
    for operation in operationen(klasse):
        name = _bezeichner(
            str(operation.get("name", "")), operation.get("visibility", "public")
        )
        if name and name != "__init__" and name in felder:
            meldungen.append(
                f"{formname(klasse)}: Die Operation „{name}“ heißt im Code "
                "genauso wie ein Attribut, und eines verdeckt das andere. "
                "Das Attribut privat machen, dann ist die Anfrage der "
                "Lesezugang, oder eines von beiden umbenennen."
            )
    return meldungen


def _doppelte_und_kreise(
    daten: dict[str, Any], klassen: list[dict[str, Any]]
) -> list[str]:
    """Zwei Klassen gleichen Namens und Klassen, die über Vererbung von
    sich selbst erben. Beides ergab Code ohne Meldung: die zweite
    Klasse ersetzte still die erste, und bei einem Kreis stand
    `class B(A)` vor `class A` und endete in `NameError` (Punkt 582).
    Gemeldet wird nur, was die Klassen in `klassen` betrifft."""
    alle = [f for f in daten.get("shapes") or [] if ist_klasse(f)]
    betroffen = {formname(k) for k in klassen}
    meldungen = []
    gezaehlt: dict[str, int] = {}
    for klasse in alle:
        name = formname(klasse)
        if name:
            gezaehlt[name] = gezaehlt.get(name, 0) + 1
    for name, anzahl in sorted(gezaehlt.items()):
        if anzahl > 1 and name in betroffen:
            meldungen.append(
                f"Die Klasse „{name}“ kommt {anzahl}-mal vor. Im Code "
                "ersetzte die letzte die übrigen; jede Klasse braucht "
                "einen eigenen Namen."
            )
    basen = {formname(k): set(_basisklassen(daten, k)) for k in alle}
    for name in sorted(betroffen):
        gesehen: set[str] = set()
        offen = list(basen.get(name, ()))
        while offen:
            basis = offen.pop()
            if basis == name:
                meldungen.append(
                    f"Die Klasse „{name}“ erbt über ihre Basisklassen von "
                    "sich selbst. Eine der Vererbungslinien entfernen."
                )
                break
            if basis not in gesehen:
                gesehen.add(basis)
                offen.extend(basen.get(basis, ()))
    return meldungen


def _gueltiger_ausdruck(text: str) -> bool:
    try:
        compile(text, "<diagramm>", "eval")
    except (SyntaxError, ValueError):
        return False
    return True


def _uebersetzungsfehler(quelltext: str) -> str:
    """Leer, wenn sich `quelltext` übersetzen lässt; sonst eine
    Meldung mit der Zeile, an der es scheitert."""
    try:
        compile(quelltext, "<diagramm>", "exec")
    except (SyntaxError, ValueError) as fehler:
        nummer = getattr(fehler, "lineno", None) or 0
        zeilen = quelltext.splitlines()
        if 0 < nummer <= len(zeilen):
            return (
                "Der erzeugte Code lässt sich nicht übersetzen, "
                f"Zeile {nummer}: {zeilen[nummer - 1].strip()}"
            )
        return "Der erzeugte Code lässt sich nicht übersetzen."
    return ""


def fremde_typen(daten: dict[str, Any], klassen: list[dict[str, Any]]) -> list[str]:
    """Typnamen, die im Diagramm vorkommen, aber von keiner Klasse darin
    beschrieben werden – etwa `Shape` aus `pcl`.

    Das ist kein Fehler des Erzeugers: ein Klassendiagramm verweist
    naturgemäß auf Typen, die anderswo stehen. Nur muss man wissen,
    welche das sind, sonst rätselt man vor einem `NameError`.
    """
    eigene = {formname(f) for f in daten.get("shapes") or [] if ist_klasse(f)}
    eingebaut = {
        "int", "str", "bool", "float", "bytes", "None", "list", "dict",
        "set", "tuple", "object", "Any",
    }
    gefunden: list[str] = []
    for klasse in klassen:
        kandidaten = [a.get("type") for a in attribute(klasse)]
        for operation in operationen(klasse):
            kandidaten.append(operation.get("type"))
            kandidaten.extend(p.get("type") for p in operation.get("parameters") or [])
        for typ in kandidaten:
            # Name für Name: bei `list[Person]` fehlt `Person`, nicht
            # der ganze Ausdruck. `Optional` und Co. kommen aus
            # `typing` und zählen wie die eingebauten Typen.
            for name in re.findall(r"[^\W\d]\w*", python_typ(typ)):
                if (
                    name not in eigene and name not in eingebaut
                    and name not in _TYPING and name not in gefunden
                ):
                    gefunden.append(name)
    return gefunden


#: Namen aus `typing`, die in Typangaben stehen dürfen, ohne dass das
#: Diagramm sie beschreibt.
_TYPING = {"Optional", "Union", "List", "Dict", "Set", "Tuple", "Callable"}


def kopfzeilen(shapes: list[dict[str, Any]], daten: dict[str, Any] | None = None) -> list[str]:
    """Kopf der erzeugten Datei: nötige Importe und der Hinweis auf
    Typen, die von außen kommen."""
    # Ohne diese Zeile wertet Python die Typangaben beim Ausführen des
    # `def` aus. Ein Selbstbezug wie `naechster: Knoten` in der Klasse
    # `Knoten` oder ein Typ, dessen Klasse erst weiter unten steht,
    # brach dann beim Import mit `NameError` ab (Punkt 148).
    zeilen: list[str] = ["from __future__ import annotations", ""]
    fremd = fremde_typen(daten or {}, shapes) if daten is not None else []
    if fremd:
        zeilen.append(
            "# Diese Typen beschreibt das Diagramm nicht selbst und sie müssen"
        )
        zeilen.append(f"# noch importiert werden: {', '.join(fremd)}")
        zeilen.append("")
    return zeilen


def diagramm_als_python(
    daten: dict[str, Any], shape: dict[str, Any] | None = None
) -> str:
    """Eine einzelne Klasse oder alle Klassen des Diagramms.

    Reihenfolge: Basisklassen zuerst, damit der erzeugte Code in einer
    Datei auch wirklich ausführbar ist – eine Unterklasse, die vor ihrer
    Basisklasse steht, wäre ein `NameError`.
    """
    # Eine gewählte Notiz oder ein Paket ist keine Klasse; daraus
    # entstand bis Punkt 179 `class Konto: ...`.
    if shape is not None and not ist_klasse(shape):
        return ""
    klassen = [shape] if shape is not None else [
        f for f in daten.get("shapes") or [] if ist_klasse(f)
    ]
    if not klassen:
        return ""

    if shape is None:
        klassen = _nach_vererbung_sortiert(daten, klassen)

    teile = kopfzeilen(klassen, daten)
    for klasse in klassen:
        teile.append(klasse_als_python(klasse, daten))
        teile.append("")
    return "\n".join(teile).rstrip() + "\n"


def _nach_vererbung_sortiert(
    daten: dict[str, Any], klassen: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Basisklassen vor ihren Unterklassen. Bei einem Zyklus (der in UML
    nicht vorkommen sollte, in einer von Hand bearbeiteten Datei aber
    schon) bleibt die ursprüngliche Reihenfolge – Hauptsache, es fehlt
    nichts."""
    nach_name = {formname(k): k for k in klassen}
    erledigt: list[dict[str, Any]] = []
    gesehen: set[int] = set()

    def einsortieren(klasse: dict[str, Any], pfad: set[int]) -> None:
        if id(klasse) in gesehen or id(klasse) in pfad:
            return
        for basis in _basisklassen(daten, klasse):
            if basis in nach_name:
                einsortieren(nach_name[basis], pfad | {id(klasse)})
        gesehen.add(id(klasse))
        erledigt.append(klasse)

    for klasse in klassen:
        einsortieren(klasse, set())
    return erledigt
