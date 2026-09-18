"""Strukturierte Attribute und Operationen einer UML-Klasse
(Abschnitt 13.4, M9 Schritt 12).

Bis Schritt 11 waren Attribute und Operationen **freier Text**: eine
Liste von Zeichenketten wie `+setzen(farbe: str)`, die zufällig wie UML
aussahen. Seit der Nutzer-Entscheidung im September 2026 werden sie
über einen Eigenschaften-Dialog bearbeitet (Vorbild: Dia), und dafür
braucht jedes Attribut und jede Operation eigene Felder – Name, Typ,
Sichtbarkeit, bei Operationen zusätzlich eine Parameterliste.

Diese Datei kennt nur die Daten: sie liest sie aus dem `.pdiag`-`dict`,
setzt daraus die anzuzeigende UML-Zeile zusammen und rechnet alte
Dateien in die neue Form um. Sie braucht **kein Qt** und ist deshalb
einzeln testbar.
"""

from __future__ import annotations

import re
from typing import Any

#: Sichtbarkeit: interner Wert -> UML-Zeichen (Abschnitt 13.6).
SICHTBARKEITSZEICHEN = {
    "public": "+",
    "private": "-",
    "protected": "#",
    "implementation": "~",
}
#: Umgekehrt, für das Einlesen alter Textzeilen.
ZEICHEN_SICHTBARKEIT = {zeichen: name for name, zeichen in SICHTBARKEITSZEICHEN.items()}

SICHTBARKEITEN = tuple(SICHTBARKEITSZEICHEN)
#: „Typ der Vererbung“ im Dia-Dialog.
VERERBUNGSARTEN = ("abstract", "virtual", "leaf")
#: Richtung eines Parameters.
RICHTUNGEN = ("undefined", "in", "out", "inout")

#: Formen, die Attribute und Operationen haben – nur für sie gibt es den
#: Dialog. Notiz und Paket haben nur einen Namen und werden weiterhin
#: direkt in der Fläche beschriftet (Nutzer-Entscheidung).
KLASSENARTEN = ("class", "abstract_class", "interface")


def ist_klasse(shape: dict[str, Any]) -> bool:
    return shape.get("kind", "class") in KLASSENARTEN


# -- Lesen ---------------------------------------------------------------


def attribute(shape: dict[str, Any]) -> list[dict[str, Any]]:
    return shape.setdefault("attributes", [])


def operationen(shape: dict[str, Any]) -> list[dict[str, Any]]:
    return shape.setdefault("operations", [])


def name(shape: dict[str, Any]) -> str:
    return str(shape.get("name", ""))


def anzeigeschalter(shape: dict[str, Any], schluessel: str, vorgabe: Any) -> Any:
    """Die Schalter aus dem Reiter „Klasse“ (sichtbar/unterdrücken/
    umbrechen). Fehlt der Schlüssel, gilt die Vorgabe."""
    wert = shape.get(schluessel)
    return vorgabe if wert is None else wert


# -- Zeilen zusammensetzen ----------------------------------------------


def attribut_zeile(attribut: dict[str, Any]) -> str:
    """Ein Attribut als UML-Zeile, z. B. `-zustand: int = 1`."""
    zeichen = SICHTBARKEITSZEICHEN.get(str(attribut.get("visibility", "public")), "+")
    text = f"{zeichen}{attribut.get('name', '')}"
    if attribut.get("type"):
        text += f": {attribut['type']}"
    if attribut.get("value") not in (None, ""):
        text += f" = {attribut['value']}"
    return text


def parameter_zeile(parameter: dict[str, Any]) -> str:
    text = str(parameter.get("name", ""))
    if parameter.get("type"):
        text += f": {parameter['type']}"
    if parameter.get("default") not in (None, ""):
        text += f" = {parameter['default']}"
    richtung = parameter.get("direction", "undefined")
    if richtung and richtung != "undefined":
        text = f"{richtung} {text}"
    return text


def operation_zeile(operation: dict[str, Any]) -> str:
    """Eine Operation als UML-Zeile, z. B.
    `+setzen(farbe: str, hell: bool = True): None`."""
    zeichen = SICHTBARKEITSZEICHEN.get(str(operation.get("visibility", "public")), "+")
    parameter = ", ".join(parameter_zeile(p) for p in operation.get("parameters") or [])
    text = f"{zeichen}{operation.get('name', '')}({parameter})"
    if operation.get("type"):
        text += f": {operation['type']}"
    return text


def umbrechen(zeile: str, laenge: int) -> list[str]:
    """Bricht eine zu lange Zeile an einem Komma um und rückt die
    Fortsetzung ein – so bleibt erkennbar, dass sie zusammengehört."""
    if laenge <= 0 or len(zeile) <= laenge:
        return [zeile]

    teile: list[str] = []
    rest = zeile
    while len(rest) > laenge:
        schnitt = rest.rfind(", ", 0, laenge + 1)
        if schnitt == -1:
            break
        teile.append(rest[: schnitt + 1])
        rest = "    " + rest[schnitt + 2 :]
    teile.append(rest)
    return teile


def attributzeilen(shape: dict[str, Any]) -> list[str]:
    if not anzeigeschalter(shape, "attributes_visible", True):
        return []
    return [attribut_zeile(a) for a in attribute(shape)]


def operationszeilen(shape: dict[str, Any]) -> list[str]:
    if not anzeigeschalter(shape, "operations_visible", True):
        return []
    zeilen = [operation_zeile(o) for o in operationen(shape)]
    if not anzeigeschalter(shape, "wrap_operations", False):
        return zeilen
    laenge = int(anzeigeschalter(shape, "wrap_after_operations", 40))
    umbrochen: list[str] = []
    for zeile in zeilen:
        umbrochen.extend(umbrechen(zeile, laenge))
    return umbrochen


def unterstrichene_attribute(shape: dict[str, Any]) -> set[int]:
    """Zeilennummern, die unterstrichen gehören – UML stellt den
    Klassen-Gültigkeitsbereich so dar (Abschnitt 13.6)."""
    return {i for i, a in enumerate(attribute(shape)) if a.get("class_scope")}


def kursive_operationen(shape: dict[str, Any]) -> set[int]:
    """Zeilennummern abstrakter Operationen – die stehen kursiv."""
    return {
        i
        for i, o in enumerate(operationen(shape))
        if o.get("inheritance") == "abstract"
    }


# -- Alte Dateien umrechnen ---------------------------------------------

_OPERATION = re.compile(
    r"^\s*(?P<zeichen>[+\-#~])?\s*(?P<name>[^(]*)"
    r"\((?P<parameter>.*)\)\s*(?::\s*(?P<typ>.+))?\s*$"
)
_ATTRIBUT = re.compile(
    r"^\s*(?P<zeichen>[+\-#~])?\s*(?P<name>[^:=]+?)\s*"
    r"(?::\s*(?P<typ>[^=]+?))?\s*(?:=\s*(?P<wert>.+))?\s*$"
)


def _sichtbarkeit(zeichen: str | None) -> str:
    return ZEICHEN_SICHTBARKEIT.get(zeichen or "", "public")


def parameter_lesen(text: str) -> list[dict[str, Any]]:
    """Zerlegt `farbe: str, hell: bool = True` in einzelne Parameter."""
    ergebnis: list[dict[str, Any]] = []
    for stueck in text.split(","):
        stueck = stueck.strip()
        if not stueck:
            continue
        treffer = _ATTRIBUT.match(stueck)
        if treffer is None:
            ergebnis.append({"name": stueck})
            continue
        parameter: dict[str, Any] = {"name": (treffer["name"] or "").strip()}
        if treffer["typ"]:
            parameter["type"] = treffer["typ"].strip()
        if treffer["wert"]:
            parameter["default"] = treffer["wert"].strip()
        ergebnis.append(parameter)
    return ergebnis


def attribut_lesen(zeile: str) -> dict[str, Any]:
    treffer = _ATTRIBUT.match(zeile)
    if treffer is None:
        return {"name": zeile.strip(), "visibility": "public"}
    attribut: dict[str, Any] = {
        "name": (treffer["name"] or "").strip(),
        "visibility": _sichtbarkeit(treffer["zeichen"]),
    }
    if treffer["typ"]:
        attribut["type"] = treffer["typ"].strip()
    if treffer["wert"]:
        attribut["value"] = treffer["wert"].strip()
    return attribut


def operation_lesen(zeile: str) -> dict[str, Any]:
    treffer = _OPERATION.match(zeile)
    if treffer is None:
        # Keine Klammern – als Operation ohne Parameter übernehmen,
        # damit nichts verloren geht.
        gelesen = attribut_lesen(zeile)
        return {
            "name": gelesen["name"],
            "visibility": gelesen["visibility"],
            "parameters": [],
            **({"type": gelesen["type"]} if "type" in gelesen else {}),
        }
    operation: dict[str, Any] = {
        "name": (treffer["name"] or "").strip(),
        "visibility": _sichtbarkeit(treffer["zeichen"]),
        "parameters": parameter_lesen(treffer["parameter"] or ""),
    }
    if treffer["typ"]:
        operation["type"] = treffer["typ"].strip()
    return operation


def form_umrechnen(shape: dict[str, Any]) -> bool:
    """Rechnet eine Form aus der alten Textform in die neue Struktur um.
    Gibt zurück, ob etwas geändert wurde.

    Alte Dateien müssen ladbar bleiben – sonst wären die drei
    Abnahmediagramme aus Schritt 11 und alles, was Schülerinnen und
    Schüler schon gezeichnet haben, mit einem Schlag unbrauchbar.
    """
    text = shape.get("text")
    if not isinstance(text, dict):
        return False

    geaendert = False
    if "name" not in shape and text.get("name") is not None:
        shape["name"] = str(text["name"])
        geaendert = True
    if ist_klasse(shape):
        if "attributes" not in shape:
            shape["attributes"] = [attribut_lesen(str(z)) for z in text.get("attributes") or []]
            geaendert = True
        if "operations" not in shape:
            shape["operations"] = [operation_lesen(str(z)) for z in text.get("methods") or []]
            geaendert = True

    del shape["text"]
    return geaendert or True


def umrechnen(daten: dict[str, Any]) -> bool:
    """Rechnet ein ganzes `.pdiag` um. Gibt zurück, ob etwas zu tun war."""
    geaendert = False
    for shape in daten.get("shapes") or []:
        if form_umrechnen(shape):
            geaendert = True
    return geaendert


def formname(shape: dict[str, Any]) -> str:
    """Der angezeigte Name einer Form – neu aus `name`, bei noch nicht
    umgerechneten Dateien aus dem alten `text`-Block. Beides zu können
    spart überall sonst eine Fallunterscheidung."""
    if shape.get("name") is not None:
        return str(shape["name"])
    return str((shape.get("text") or {}).get("name", ""))
