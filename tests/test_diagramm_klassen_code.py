"""Tests für ide/diagramm/klassen_code.py: aus einer UML-Klasse
Python-Quelltext erzeugen (M9, Schritt 13).

Der wichtigste Test ist der langweiligste: das Ergebnis muss immer
gültiges Python sein. Alles andere nützt nichts, wenn der erzeugte Code
sich nicht ausführen lässt.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from ide.diagramm.datei import Diagramm
from ide.diagramm.klassen_code import diagramm_als_python, klasse_als_python


def _klasse(name: str = "Ampel", **felder) -> dict:
    return {
        "id": felder.pop("id", "s1"),
        "kind": "class",
        "x": 0,
        "y": 0,
        "w": 200,
        "h": 100,
        "name": name,
        "attributes": [],
        "operations": [],
        **felder,
    }


def _gueltig(quelltext: str) -> ast.Module:
    """Hebt den Test von „sieht richtig aus“ auf „ist richtig“."""
    return ast.parse(quelltext)


# -- Grundgerüst ---------------------------------------------------------


def test_leere_klasse_hat_trotzdem_einen_rumpf() -> None:
    code = klasse_als_python(_klasse())

    assert code.startswith("class Ampel:")
    _gueltig(code)


def test_kommentar_wird_zum_docstring() -> None:
    code = klasse_als_python(_klasse(comment="Eine Ampel mit vier Zuständen."))

    assert '"""Eine Ampel mit vier Zuständen."""' in code
    _gueltig(code)


def test_umlaute_im_namen_bleiben_erhalten() -> None:
    """Python erlaubt sie, und in dieser Zielgruppe kommen sie vor."""
    code = klasse_als_python(_klasse("Fußgängerampel"))

    assert "class Fußgängerampel:" in code
    _gueltig(code)


# -- Attribute -----------------------------------------------------------


def test_attribute_werden_zum_init() -> None:
    klasse = _klasse(
        attributes=[
            {"name": "eingeschaltet", "type": "bool", "visibility": "private"},
            {"name": "zustand", "type": "int", "visibility": "private"},
        ]
    )

    code = klasse_als_python(klasse)

    assert "def __init__(self, eingeschaltet: bool, zustand: int) -> None:" in code
    assert "self.__eingeschaltet = eingeschaltet" in code
    _gueltig(code)


def test_sichtbarkeit_steht_in_der_namensschreibweise() -> None:
    """Nicht als `#private:`-Kommentar wie bei Dia."""
    klasse = _klasse(
        attributes=[
            {"name": "a", "visibility": "private"},
            {"name": "b", "visibility": "protected"},
            {"name": "c", "visibility": "public"},
        ]
    )

    code = klasse_als_python(klasse)

    assert "self.__a = a" in code
    assert "self._b = b" in code
    assert "self.c = c" in code


def test_vorhandene_unterstriche_werden_nicht_verdoppelt() -> None:
    """Aus einer alten Textzeile kommt der Name schon mit Unterstrichen –
    sonst entstünde `____zustand`."""
    klasse = _klasse(attributes=[{"name": "__zustand", "visibility": "private"}])

    code = klasse_als_python(klasse)

    assert "self.__zustand = zustand" in code
    assert "____" not in code


def test_vorgabewert_landet_im_init() -> None:
    klasse = _klasse(
        attributes=[{"name": "zaehler", "type": "int", "value": "0"}]
    )

    code = klasse_als_python(klasse)

    assert "def __init__(self, zaehler: int = 0) -> None:" in code
    _gueltig(code)


def test_fehlender_typ_wird_nicht_geraten() -> None:
    klasse = _klasse(attributes=[{"name": "wert"}])

    code = klasse_als_python(klasse)

    assert "def __init__(self, wert) -> None:" in code
    _gueltig(code)


def test_klassen_gueltigkeitsbereich_wird_zum_klassenattribut() -> None:
    klasse = _klasse(
        attributes=[{"name": "anzahl", "type": "int", "value": "0", "class_scope": True}]
    )

    code = klasse_als_python(klasse)

    assert "    anzahl: int = 0" in code
    assert "__init__" not in code  # gehört nicht in den Konstruktor
    _gueltig(code)


# -- Operationen ---------------------------------------------------------


def test_operation_mit_parametern_und_rueckgabetyp() -> None:
    klasse = _klasse(
        operations=[
            {
                "name": "setzen",
                "type": "None",
                "visibility": "public",
                "parameters": [
                    {"name": "farbe", "type": "str"},
                    {"name": "hell", "type": "bool", "default": "True"},
                ],
            }
        ]
    )

    code = klasse_als_python(klasse)

    assert "def setzen(self, farbe: str, hell: bool = True) -> None:" in code
    _gueltig(code)


def test_rumpf_bleibt_leer() -> None:
    """Damit niemand denkt, hier stünde schon Logik."""
    klasse = _klasse(operations=[{"name": "ein"}])

    code = klasse_als_python(klasse)

    assert "        ..." in code
    assert "return None" not in code


def test_abstrakte_operation_wirft() -> None:
    """Ein stiller `...`-Rumpf verschluckte den Fehler zur Laufzeit."""
    klasse = _klasse(operations=[{"name": "zeichnen", "inheritance": "abstract"}])

    code = klasse_als_python(klasse)

    assert "raise NotImplementedError" in code
    _gueltig(code)


def test_klassenweite_operation_wird_statisch() -> None:
    klasse = _klasse(operations=[{"name": "erzeugen", "class_scope": True}])

    code = klasse_als_python(klasse)

    assert "@staticmethod" in code
    assert "def erzeugen()" in code
    _gueltig(code)


def test_anfrage_ohne_parameter_wird_eigenschaft() -> None:
    klasse = _klasse(
        operations=[{"name": "zustand", "type": "int", "query": True, "parameters": []}]
    )

    code = klasse_als_python(klasse)

    assert "@property" in code
    _gueltig(code)


def test_anfrage_mit_parameter_bleibt_methode() -> None:
    klasse = _klasse(
        operations=[
            {"name": "hole", "query": True, "parameters": [{"name": "nummer"}]}
        ]
    )

    code = klasse_als_python(klasse)

    assert "@property" not in code


def test_operationskommentar_wird_docstring() -> None:
    klasse = _klasse(operations=[{"name": "ein", "comment": "Schaltet die Ampel ein."}])

    code = klasse_als_python(klasse)

    assert '"""Schaltet die Ampel ein."""' in code
    _gueltig(code)


# -- Vererbung -----------------------------------------------------------


def _diagramm(*formen, verbindungen=()) -> dict:
    return {
        "format": "pdiag/1",
        "type": "class",
        "page": {"size": "A4", "orientation": "landscape"},
        "style": "modern-light",
        "shapes": list(formen),
        "connectors": list(verbindungen),
    }


def test_verallgemeinerung_wird_zur_basisklasse() -> None:
    basis = _klasse("Fahrzeug", id="s1")
    unter = _klasse("Auto", id="s2")
    daten = _diagramm(
        basis,
        unter,
        verbindungen=[{"id": "c1", "kind": "generalization", "from": "s2", "to": "s1"}],
    )

    code = klasse_als_python(unter, daten)

    assert "class Auto(Fahrzeug):" in code
    _gueltig(code)


def test_realisierung_zaehlt_auch() -> None:
    schnittstelle = _klasse("ISchaltbar", id="s1")
    klasse = _klasse("Lampe", id="s2")
    daten = _diagramm(
        schnittstelle,
        klasse,
        verbindungen=[{"id": "c1", "kind": "realization", "from": "s2", "to": "s1"}],
    )

    assert "class Lampe(ISchaltbar):" in klasse_als_python(klasse, daten)


def test_aggregation_wird_keine_basisklasse() -> None:
    """Aggregation sagt „hat ein“, nicht „ist ein“."""
    teil = _klasse("Lampe", id="s1")
    ganzes = _klasse("Ampel", id="s2")
    daten = _diagramm(
        teil,
        ganzes,
        verbindungen=[{"id": "c1", "kind": "aggregation", "from": "s2", "to": "s1"}],
    )

    assert "class Ampel:" in klasse_als_python(ganzes, daten)


def test_zwei_basisklassen_ergeben_mehrfachvererbung() -> None:
    a = _klasse("A", id="s1")
    b = _klasse("B", id="s2")
    c = _klasse("C", id="s3")
    daten = _diagramm(
        a,
        b,
        c,
        verbindungen=[
            {"id": "c1", "kind": "generalization", "from": "s3", "to": "s1"},
            {"id": "c2", "kind": "generalization", "from": "s3", "to": "s2"},
        ],
    )

    assert "class C(A, B):" in klasse_als_python(c, daten)


def test_vorlageklasse_wird_generisch() -> None:
    klasse = _klasse("Behaelter", template=True, template_parameters=[{"name": "T"}])

    code = diagramm_als_python(_diagramm(klasse))

    assert "from typing import Generic" in code
    assert "class Behaelter(Generic[T]):" in code


# -- Ganzes Diagramm -----------------------------------------------------


def test_alle_klassen_kommen_vor() -> None:
    daten = _diagramm(_klasse("A", id="s1"), _klasse("B", id="s2"))

    code = diagramm_als_python(daten)

    assert "class A:" in code and "class B:" in code
    _gueltig(code)


def test_basisklasse_steht_vor_ihrer_unterklasse() -> None:
    """Sonst wäre der erzeugte Code ein `NameError`."""
    unter = _klasse("Auto", id="s1")
    basis = _klasse("Fahrzeug", id="s2")
    daten = _diagramm(
        unter,  # steht absichtlich zuerst im Diagramm
        basis,
        verbindungen=[{"id": "c1", "kind": "generalization", "from": "s1", "to": "s2"}],
    )

    code = diagramm_als_python(daten)

    assert code.index("class Fahrzeug") < code.index("class Auto")
    _gueltig(code)


def test_notizen_erzeugen_keinen_code() -> None:
    notiz = {"id": "s9", "kind": "note", "x": 0, "y": 0, "w": 9, "h": 9, "name": "Hinweis"}
    daten = _diagramm(_klasse("A", id="s1"), notiz)

    code = diagramm_als_python(daten)

    assert "Hinweis" not in code


def test_leeres_diagramm_ergibt_leeren_text() -> None:
    assert diagramm_als_python(_diagramm()) == ""


# -- Am echten Abnahmediagramm -------------------------------------------

DIAGRAMME = (
    Path(__file__).resolve().parent.parent / "beispielprojekte" / "06_Kontoverwaltung" / "diagramme"
)


def test_das_abnahmediagramm_erzeugt_gueltiges_python() -> None:
    daten = Diagramm.laden(DIAGRAMME / "konto_klassen.pdiag").daten

    code = diagramm_als_python(daten)

    _gueltig(code)


def test_die_erzeugte_klasse_hat_die_methoden_des_echten_programms() -> None:
    """Probe gegen `beispielprojekte/06_Kontoverwaltung/u_konto.py`.

    Das Klassendiagramm ist dort kein Beiwerk: es ist die Stufe, auf
    der Lernende zum ersten Mal eine eigene Klasse zeichnen und
    schreiben. Läuft es auseinander, lernt jemand etwas Falsches.
    """
    daten = Diagramm.laden(DIAGRAMME / "konto_klassen.pdiag").daten
    konto = next(f for f in daten["shapes"] if f.get("name") == "Konto")

    code = klasse_als_python(konto, daten)
    baum = _gueltig(code)
    klassendefinition = baum.body[0]
    methoden = {
        knoten.name
        for knoten in klassendefinition.body
        if isinstance(knoten, ast.FunctionDef)
    }

    for name in ("__init__", "einzahlen", "abheben"):
        assert name in methoden


def test_das_diagramm_passt_zur_echten_klasse() -> None:
    """Die Gegenrichtung: was in `u_konto.py` steht, muss auch im
    Diagramm stehen."""
    import ast as _ast

    quelle = (DIAGRAMME.parent / "u_konto.py").read_text(encoding="utf-8")
    echte = next(
        k
        for k in _ast.parse(quelle).body
        if isinstance(k, _ast.ClassDef) and k.name == "Konto"
    )
    echte_methoden = {
        knoten.name for knoten in echte.body if isinstance(knoten, _ast.FunctionDef)
    }

    daten = Diagramm.laden(DIAGRAMME / "konto_klassen.pdiag").daten
    konto = next(f for f in daten["shapes"] if f.get("name") == "Konto")
    gezeichnete = {o["name"] for o in konto["operations"]}

    assert echte_methoden - {"__repr__"} == gezeichnete


@pytest.mark.parametrize("dateiname", ["konto_klassen.pdiag"])
def test_erzeugter_code_besteht_ruff(dateiname: str, tmp_path: Path) -> None:
    """Gültiges Python allein reicht nicht – es soll auch den Linter des
    Projekts überstehen.

    `F821` ist dabei ausgenommen: ein Klassendiagramm verweist
    naturgemäß auf Typen, die anderswo stehen (im Konto-Diagramm etwa
    `SQLQuery` aus `pcl`). Der erzeugte Kopf nennt sie namentlich, damit
    man weiß, was noch zu importieren ist – siehe den Test darunter.
    """
    import subprocess
    import sys

    daten = Diagramm.laden(DIAGRAMME / dateiname).daten
    ziel = tmp_path / "erzeugt.py"
    ziel.write_text(diagramm_als_python(daten), encoding="utf-8")

    ergebnis = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--ignore", "F821", str(ziel)],
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert ergebnis.returncode == 0, ergebnis.stdout


def test_der_kopf_nennt_die_typen_von_ausserhalb() -> None:
    """Sonst rätselt man vor einem `NameError`."""
    daten = Diagramm.laden(DIAGRAMME / "konto_klassen.pdiag").daten

    code = diagramm_als_python(daten)

    assert "noch importiert werden" in code
    assert "SQLQuery" in code.splitlines()[1]
