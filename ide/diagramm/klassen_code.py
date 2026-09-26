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

import keyword
from typing import Any

from ide.diagramm.uml_modell import attribute, formname, ist_klasse, operationen

EINRUECKUNG = "    "

#: Verbindungsarten, die zu einer Basisklasse werden (Abschnitt 13.6).
#: Aggregation und Komposition werden dagegen zu Attributen – sie sagen
#: „hat ein“, nicht „ist ein“.
#: „inheritance“ ist die Art, die die Palette des Klassendiagramms
#: anlegt; sie fehlte bis 0.3.3 in dieser Liste, und eine dort
#: gezogene Vererbung kam nie im Klassenkopf an.
VERERBUNGSARTEN = ("inheritance", "generalization", "realization", "implements")


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


def _mit_typ(name: str, typ: str | None) -> str:
    """Typangabe nur, wenn eine da ist – geraten wird nichts."""
    return f"{name}: {typ.strip()}" if typ and typ.strip() else name


def _docstring(text: str, tiefe: int) -> list[str]:
    if not text or not text.strip():
        return []
    einzug = EINRUECKUNG * tiefe
    zeilen = text.strip().splitlines()
    if len(zeilen) == 1:
        return [f'{einzug}"""{zeilen[0]}"""']
    return [f'{einzug}"""{zeilen[0]}', *(f"{einzug}{z}" for z in zeilen[1:]), f'{einzug}"""']


def _basisklassen(daten: dict[str, Any], shape: dict[str, Any]) -> list[str]:
    """Basisklassen aus den Verbindungen: eine Verallgemeinerung oder
    Realisierung, die von dieser Klasse ausgeht, zeigt auf die
    Basisklasse."""
    formen = {f.get("id"): f for f in daten.get("shapes") or []}
    namen = []
    for verbindung in daten.get("connectors") or []:
        if verbindung.get("kind") not in VERERBUNGSARTEN:
            continue
        if verbindung.get("from") != shape.get("id"):
            continue
        ziel = formen.get(verbindung.get("to"))
        if ziel is not None and formname(ziel):
            namen.append(formname(ziel))
    return namen


def _init_zeilen(shape: dict[str, Any]) -> list[str]:
    """`__init__` aus den Attributen. Attribute mit
    Klassen-Gültigkeitsbereich gehören nicht hierher – sie stehen als
    Klassenattribut oben."""
    # Ist der Konstruktor im Diagramm selbst modelliert, gilt dieser –
    # sonst stünde `__init__` zweimal in der Klasse. Genau das ist beim
    # TAmpel-Abnahmediagramm passiert, das `+__init__(...)` als
    # Operation führt.
    if any(str(o.get("name", "")).strip() == "__init__" for o in operationen(shape)):
        return []

    eigene = [a for a in attribute(shape) if not a.get("class_scope")]
    if not eigene:
        return []

    parameter = ["self"]
    zuweisungen = []
    for attribut in eigene:
        roh = str(attribut.get("name", "")).lstrip("_")
        if not roh:
            continue
        feld = _bezeichner(str(attribut.get("name", "")), attribut.get("visibility", "public"))
        stueck = _mit_typ(roh, attribut.get("type"))
        if attribut.get("value"):
            stueck += f" = {attribut['value']}"
        parameter.append(stueck)
        zuweisungen.append(f"{EINRUECKUNG * 2}self.{feld} = {roh}")

    if not zuweisungen:
        return []
    return [
        f"{EINRUECKUNG}def __init__({', '.join(parameter)}) -> None:",
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
    operation: dict[str, Any], shape: dict[str, Any]
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
    """
    felder = {
        str(a.get("name", "")).lstrip("_"): _bezeichner(
            str(a.get("name", "")), a.get("visibility", "public")
        )
        for a in attribute(shape)
        if not a.get("class_scope") and str(a.get("name", "")).strip()
    }
    zeilen = []
    for parameter in operation.get("parameters") or []:
        roh = str(parameter.get("name", "")).strip().lstrip("_")
        if roh in felder:
            zeilen.append(f"{EINRUECKUNG * 2}self.{felder[roh]} = {roh}")
    return zeilen


def _operation_zeilen(
    operation: dict[str, Any], shape: dict[str, Any] | None = None
) -> list[str]:
    name = _bezeichner(
        str(operation.get("name", "")), operation.get("visibility", "public")
    )
    if not name:
        return []

    parameter = [p for p in operation.get("parameters") or []]
    klassenweit = bool(operation.get("class_scope"))
    # „Anfrage“ ohne Parameter ist im Python-Sinn eine Eigenschaft.
    eigenschaft = bool(operation.get("query")) and not parameter and not klassenweit

    zeilen: list[str] = []
    if klassenweit:
        zeilen.append(f"{EINRUECKUNG}@staticmethod")
    elif eigenschaft:
        zeilen.append(f"{EINRUECKUNG}@property")

    argumente = [] if klassenweit else ["self"]
    for p in parameter:
        stueck = _mit_typ(str(p.get("name", "")).strip(), p.get("type"))
        if p.get("default"):
            stueck += f" = {p['default']}"
        if stueck:
            argumente.append(stueck)

    rueckgabe = str(operation.get("type") or "").strip()
    kopf = f"{EINRUECKUNG}def {name}({', '.join(argumente)})"
    kopf += f" -> {rueckgabe}:" if rueckgabe else ":"
    zeilen.append(kopf)
    zeilen.extend(_docstring(str(operation.get("comment", "")), 2))

    zuweisungen = (
        _zuweisungen_fuer_init(operation, shape)
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
    if shape.get("template") and (shape.get("template_parameters") or []):
        basis.append(
            "Generic[" + ", ".join(
                str(p.get("name", "T")) for p in shape["template_parameters"]
            ) + "]"
        )
    kopf = f"class {name}({', '.join(basis)}):" if basis else f"class {name}:"

    rumpf: list[str] = []
    rumpf.extend(_docstring(str(shape.get("comment", "")), 1))
    if rumpf:
        rumpf.append("")
    rumpf.extend(_klassenattribute(shape))
    rumpf.extend(_init_zeilen(shape))
    for operation in operationen(shape):
        rumpf.extend(_operation_zeilen(operation, shape))

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
    """
    klassen = [shape] if shape is not None else [
        f for f in daten.get("shapes") or [] if ist_klasse(f)
    ]
    meldungen: list[str] = []

    def pruefen(name: Any, was: str) -> None:
        text = str(name or "").strip()
        if text and not _gueltiger_name(text):
            meldungen.append(f"{was} „{text}“ ist kein gültiger Python-Name.")

    for klasse in klassen:
        klassenname = formname(klasse)
        pruefen(klassenname, "Die Klasse")
        for attribut in attribute(klasse):
            pruefen(attribut.get("name"), f"{klassenname}: Das Attribut")
        for operation in operationen(klasse):
            pruefen(operation.get("name"), f"{klassenname}: Die Operation")
            for parameter in operation.get("parameters") or []:
                pruefen(
                    parameter.get("name"),
                    f"{klassenname}.{operation.get('name', '')}: Der Parameter",
                )
    return meldungen


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
            name = str(typ or "").strip()
            if name and name not in eigene and name not in eingebaut and name not in gefunden:
                gefunden.append(name)
    return gefunden


def kopfzeilen(shapes: list[dict[str, Any]], daten: dict[str, Any] | None = None) -> list[str]:
    """Kopf der erzeugten Datei: nötige Importe und der Hinweis auf
    Typen, die von außen kommen."""
    zeilen: list[str] = []
    fremd = fremde_typen(daten or {}, shapes) if daten is not None else []
    if fremd:
        zeilen.append(
            "# Diese Typen beschreibt das Diagramm nicht selbst und sie müssen"
        )
        zeilen.append(f"# noch importiert werden: {', '.join(fremd)}")
        zeilen.append("")
    if any(s.get("template") and (s.get("template_parameters") or []) for s in shapes):
        zeilen.extend(["from typing import Generic", ""])
    return zeilen


def diagramm_als_python(
    daten: dict[str, Any], shape: dict[str, Any] | None = None
) -> str:
    """Eine einzelne Klasse oder alle Klassen des Diagramms.

    Reihenfolge: Basisklassen zuerst, damit der erzeugte Code in einer
    Datei auch wirklich ausführbar ist – eine Unterklasse, die vor ihrer
    Basisklasse steht, wäre ein `NameError`.
    """
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
