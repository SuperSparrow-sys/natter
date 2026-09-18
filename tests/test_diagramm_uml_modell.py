"""Tests für ide/diagramm/uml_modell.py: strukturierte Attribute und
Operationen einer UML-Klasse (M9, Schritt 12).

Braucht kein Qt – hier geht es nur um Daten.
"""

from __future__ import annotations

from ide.diagramm.uml_modell import (
    attribut_lesen,
    attribut_zeile,
    attributzeilen,
    form_umrechnen,
    ist_klasse,
    kursive_operationen,
    operation_lesen,
    operation_zeile,
    operationszeilen,
    umbrechen,
    umrechnen,
    unterstrichene_attribute,
)


def _klasse(**felder) -> dict:
    return {"id": "s1", "kind": "class", "x": 0, "y": 0, "w": 200, "h": 100, **felder}


# -- Zeilen zusammensetzen ----------------------------------------------


def test_attribut_mit_typ_und_wert() -> None:
    zeile = attribut_zeile(
        {"name": "zustand", "type": "int", "value": "1", "visibility": "private"}
    )

    assert zeile == "-zustand: int = 1"


def test_attribut_ohne_typ_laesst_den_doppelpunkt_weg() -> None:
    """Fehlt der Typ, wird er nicht geraten."""
    assert attribut_zeile({"name": "x", "visibility": "public"}) == "+x"


def test_jede_sichtbarkeit_hat_ihr_zeichen() -> None:
    zeichen = {
        attribut_zeile({"name": "a", "visibility": art})[0]
        for art in ("public", "private", "protected", "implementation")
    }

    assert zeichen == {"+", "-", "#", "~"}


def test_operation_mit_parametern_und_rueckgabetyp() -> None:
    zeile = operation_zeile(
        {
            "name": "setzen",
            "type": "None",
            "visibility": "public",
            "parameters": [
                {"name": "farbe", "type": "str"},
                {"name": "hell", "type": "bool", "default": "True"},
            ],
        }
    )

    assert zeile == "+setzen(farbe: str, hell: bool = True): None"


def test_operation_ohne_parameter() -> None:
    assert operation_zeile({"name": "ein", "visibility": "public"}) == "+ein()"


def test_parameterrichtung_steht_vorne() -> None:
    zeile = operation_zeile(
        {
            "name": "f",
            "visibility": "public",
            "parameters": [{"name": "wert", "type": "int", "direction": "out"}],
        }
    )

    assert zeile == "+f(out wert: int)"


# -- Umbrechen -----------------------------------------------------------


def test_kurze_zeile_wird_nicht_umgebrochen() -> None:
    assert umbrechen("+ein()", 40) == ["+ein()"]


def test_lange_zeile_bricht_am_komma_und_rueckt_ein() -> None:
    zeile = "+setzen(farbe: str, hell: bool = True, dauer: int = 1000): None"

    teile = umbrechen(zeile, 30)

    assert len(teile) > 1
    assert teile[0].endswith(",")
    assert all(t.startswith("    ") for t in teile[1:])
    # nichts geht verloren
    assert "".join(t.lstrip() for t in teile).replace(" ", "") == zeile.replace(" ", "")


def test_ohne_komma_bleibt_die_zeile_ganz() -> None:
    """Lieber zu lang als mitten im Bezeichner zerschnitten."""
    lang = "+einesehrlangemethodeohnekomma()"

    assert umbrechen(lang, 10) == [lang]


# -- Anzeigeschalter -----------------------------------------------------


def test_unsichtbare_attribute_liefern_keine_zeilen() -> None:
    form = _klasse(
        attributes=[{"name": "a"}], attributes_visible=False
    )

    assert attributzeilen(form) == []


def test_sichtbar_ist_die_vorgabe() -> None:
    form = _klasse(attributes=[{"name": "a", "visibility": "public"}])

    assert attributzeilen(form) == ["+a"]


def test_umbrechen_wirkt_nur_wenn_eingeschaltet() -> None:
    operation = {
        "name": "f",
        "visibility": "public",
        "parameters": [{"name": f"p{i}", "type": "int"} for i in range(6)],
    }
    ohne = _klasse(operations=[operation])
    mit = _klasse(operations=[operation], wrap_operations=True, wrap_after_operations=20)

    assert len(operationszeilen(ohne)) == 1
    assert len(operationszeilen(mit)) > 1


def test_klassen_gueltigkeitsbereich_wird_gemerkt() -> None:
    """UML stellt ihn unterstrichen dar (Abschnitt 13.6)."""
    form = _klasse(
        attributes=[{"name": "a"}, {"name": "anzahl", "class_scope": True}]
    )

    assert unterstrichene_attribute(form) == {1}


def test_abstrakte_operationen_werden_gemerkt() -> None:
    form = _klasse(
        operations=[{"name": "f"}, {"name": "g", "inheritance": "abstract"}]
    )

    assert kursive_operationen(form) == {1}


# -- Alte Dateien einlesen ----------------------------------------------


def test_attributzeile_wird_zerlegt() -> None:
    gelesen = attribut_lesen("-__zustand: int")

    assert gelesen == {"name": "__zustand", "visibility": "private", "type": "int"}


def test_attributzeile_mit_vorgabewert() -> None:
    gelesen = attribut_lesen("+zaehler: int = 0")

    assert gelesen["value"] == "0"
    assert gelesen["type"] == "int"


def test_attributzeile_ohne_zeichen_ist_oeffentlich() -> None:
    assert attribut_lesen("name: str")["visibility"] == "public"


def test_operationszeile_wird_zerlegt() -> None:
    gelesen = operation_lesen("+get_zustand(): int")

    assert gelesen["name"] == "get_zustand"
    assert gelesen["type"] == "int"
    assert gelesen["parameters"] == []


def test_operationszeile_mit_parametern() -> None:
    gelesen = operation_lesen("+setzen(farbe: str, hell: bool = True)")

    assert [p["name"] for p in gelesen["parameters"]] == ["farbe", "hell"]
    assert gelesen["parameters"][0]["type"] == "str"
    assert gelesen["parameters"][1]["default"] == "True"


def test_operationszeile_ohne_klammern_geht_nicht_verloren() -> None:
    """Eine von Hand getippte Zeile soll beim Umrechnen nichts
    verschlucken."""
    gelesen = operation_lesen("-hilfsmethode")

    assert gelesen["name"] == "hilfsmethode"
    assert gelesen["visibility"] == "private"


def test_hin_und_zurueck_ergibt_dieselbe_zeile() -> None:
    """Die beste Probe für die Migration: einlesen, wieder ausgeben."""
    for zeile in (
        "-__zustand: int",
        "+einschalten()",
        "+setzen(farbe: str, hell: bool = True): None",
        "#zaehler: int = 0",
    ):
        if "(" in zeile:
            assert operation_zeile(operation_lesen(zeile)) == zeile
        else:
            assert attribut_zeile(attribut_lesen(zeile)) == zeile


# -- Ganze Diagramme umrechnen ------------------------------------------


def test_alte_form_wird_umgerechnet() -> None:
    form = _klasse(
        text={
            "name": "TAmpel",
            "attributes": ["-an: bool"],
            "methods": ["+ein()", "+get_zustand(): int"],
        }
    )

    form_umrechnen(form)

    assert "text" not in form
    assert form["name"] == "TAmpel"
    assert form["attributes"][0]["name"] == "an"
    assert [o["name"] for o in form["operations"]] == ["ein", "get_zustand"]


def test_notiz_behaelt_nur_ihren_namen() -> None:
    """Notiz und Paket haben keine Attribute – sie werden weiterhin
    direkt in der Fläche beschriftet (Nutzer-Entscheidung)."""
    notiz = {"id": "s1", "kind": "note", "x": 0, "y": 0, "w": 100, "h": 60,
             "text": {"name": "Hinweis"}}

    form_umrechnen(notiz)

    assert notiz["name"] == "Hinweis"
    assert "attributes" not in notiz
    assert not ist_klasse(notiz)


def test_umrechnen_faesst_das_ganze_diagramm_an() -> None:
    daten = {
        "shapes": [
            _klasse(text={"name": "A", "attributes": [], "methods": []}),
            {"id": "s2", "kind": "note", "x": 0, "y": 0, "w": 9, "h": 9,
             "text": {"name": "B"}},
        ]
    }

    assert umrechnen(daten) is True
    assert all("text" not in f for f in daten["shapes"])


def test_bereits_umgerechnetes_bleibt_unangetastet() -> None:
    form = _klasse(name="TAmpel", attributes=[{"name": "an"}], operations=[])

    assert form_umrechnen(form) is False
    assert form["attributes"] == [{"name": "an"}]
