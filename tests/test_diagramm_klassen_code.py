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

    assert "class Behaelter[T]:" in code
    assert "Generic" not in code
    # Punkt 160: bis dahin fehlte `T`, und der Import brach mit
    # `NameError` ab.
    namensraum: dict = {}
    exec(compile(code, "<test>", "exec"), namensraum)
    assert namensraum["Behaelter"].__type_params__[0].__name__ == "T"


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
    kopf = "\n".join(code.splitlines()[:4])
    assert "SQLQuery" in kopf


# -- Schülerweg 0.3.3 (Punkt 35 der offenen Punkte) ------------------------


def _bank(attribut: str = "stand") -> dict:
    """Das Diagramm aus der Auswertung: Sparkonto erbt von Konto, die
    Verbindung so, wie die Palette des Klassendiagramms sie anlegt."""
    return {
        "format": "pdiag/1",
        "type": "class",
        "name": "Bank",
        "shapes": [
            _klasse(
                "Sparkonto",
                id="s2",
                attributes=[{"name": "zins", "type": "float", "visibility": "private"}],
            ),
            _klasse(
                "Konto",
                id="s1",
                attributes=[{"name": attribut, "type": "float", "visibility": "private"}],
            ),
        ],
        "connectors": [{"id": "c1", "kind": "inheritance", "from": "s2", "to": "s1"}],
    }


def test_vererbung_aus_der_palette_landet_im_klassenkopf() -> None:
    quelltext = diagramm_als_python(_bank())

    _gueltig(quelltext)
    assert "class Sparkonto(Konto):" in quelltext
    assert quelltext.index("class Konto") < quelltext.index("class Sparkonto")


def test_ungueltige_namen_werden_gemeldet() -> None:
    from ide.diagramm.klassen_code import ungueltige_namen

    assert ungueltige_namen(_bank()) == []
    meldungen = ungueltige_namen(_bank("stand: float"))

    assert meldungen == ["Konto: Das Attribut „stand: float“ ist kein gültiger Python-Name."]
    assert ungueltige_namen({"shapes": [_klasse("class")]})


def test_mit_ungueltigem_namen_entsteht_keine_datei(tmp_path: Path) -> None:
    """Bis 0.3.3 stand danach `self.__stand: float = stand: float` in der
    Unit, und die Prüfung vor dem Start blockierte jeden Start."""
    from ide.diagramm import DiagrammFenster, diagramm_erzeugen

    diagramm = diagramm_erzeugen("class", tmp_path / "bank.pdiag")
    bank = _bank("stand: float")
    diagramm.daten["shapes"] = bank["shapes"]
    diagramm.daten["connectors"] = bank["connectors"]
    fenster = DiagrammFenster(diagramm)
    ziel = tmp_path / "u_bank.py"

    ergebnis = fenster.quelltext_erzeugen("datei", "alles", ziel)

    assert ergebnis is None
    assert not ziel.exists()
    assert "stand: float" in fenster.statusBar().currentMessage()


# -- Punkt 117: erzeugter Code lässt sich übersetzen ------------------------


def _konto(attributes: list[dict], operations: list[dict] | None = None) -> dict:
    return {
        "format": "pdiag/1",
        "type": "class",
        "name": "Bank",
        "shapes": [
            _klasse("Konto", attributes=attributes, operations=operations or [])
        ],
        "connectors": [],
    }


def test_startwert_vor_attribut_ohne_startwert_wird_umgestellt() -> None:
    """Vorher `def __init__(self, stand: float = 0, inhaber: str)`."""
    from ide.diagramm.klassen_code import ungueltige_namen

    daten = _konto(
        [
            {"name": "stand", "type": "float", "value": "0"},
            {"name": "inhaber", "type": "str"},
        ]
    )

    code = diagramm_als_python(daten)

    compile(code, "<test>", "exec")
    assert "def __init__(self, inhaber: str, stand: float = 0) -> None:" in code
    assert code.index("self.stand = stand") < code.index("self.inhaber = inhaber")
    assert ungueltige_namen(daten) == []


def test_parameter_ohne_standardwert_hinter_einem_mit_wird_gemeldet() -> None:
    from ide.diagramm.klassen_code import ungueltige_namen

    daten = _konto(
        [],
        [
            {
                "name": "f",
                "parameters": [
                    {"name": "a", "default": "1"},
                    {"name": "b"},
                ],
            }
        ],
    )

    meldungen = ungueltige_namen(daten)

    assert len(meldungen) == 1
    assert meldungen[0].startswith("Konto.f: Der Parameter „b“")
    assert "„a“" in meldungen[0]


def test_typ_der_kein_python_ist_wird_gemeldet() -> None:
    from ide.diagramm.klassen_code import ungueltige_namen

    daten = _konto([{"name": "stand", "type": "Liste von int"}])

    assert ungueltige_namen(daten) == [
        "Konto.stand: Der Typ „Liste von int“ ist kein gültiger Python-Ausdruck."
    ]


def test_ungueltiger_code_entsteht_nicht_als_datei(tmp_path: Path) -> None:
    """Alle drei Fälle aus Punkt 117 im Fenster: die Unit wird nicht
    geschrieben, und die Meldung nennt Klasse und Feld."""
    from ide.diagramm import DiagrammFenster, diagramm_erzeugen

    faelle = [
        (
            [{"name": "stand", "type": "Liste von int"}],
            [],
            "Konto.stand: Der Typ",
        ),
        (
            [],
            [{"name": "f", "parameters": [{"name": "a", "default": "1"}, {"name": "b"}]}],
            "Konto.f: Der Parameter",
        ),
        (
            [{"name": "stand", "type": "float", "value": "1 +"}],
            [],
            "Konto.stand: Der Startwert",
        ),
    ]
    for nummer, (attribute, operationen, erwartet) in enumerate(faelle):
        diagramm = diagramm_erzeugen("class", tmp_path / f"bank{nummer}.pdiag")
        diagramm.daten["shapes"] = _konto(attribute, operationen)["shapes"]
        fenster = DiagrammFenster(diagramm)
        ziel = tmp_path / "u_bank.py"

        assert fenster.quelltext_erzeugen("datei", "alles", ziel) is None
        assert not ziel.exists()
        assert erwartet in fenster.statusBar().currentMessage()


def test_uebersetzung_als_letzte_pruefung(monkeypatch) -> None:  # noqa: ANN001
    """Was die einzelnen Prüfungen nicht kennen, fällt beim Übersetzen
    der ganzen Klasse auf und erscheint mit der Zeile."""
    import ide.diagramm.klassen_code as klassen_code

    monkeypatch.setattr(
        klassen_code,
        "klasse_als_python",
        lambda klasse, daten=None: "class Konto:\n    def f(self)\n",
    )

    assert klassen_code.ungueltige_namen(_konto([])) == [
        "Konto: Der erzeugte Code lässt sich nicht übersetzen, "
        "Zeile 2: def f(self)"
    ]


# -- Durchsicht September 2026 (Punkte 148 bis 182) ----------------------


def _ausfuehren(quelltext: str) -> dict:
    """Übersetzt und führt den erzeugten Code aus, wie ein Import es
    täte. Erst dabei zeigen sich `NameError` und fehlende
    Konstruktorparameter."""
    namensraum: dict = {"__name__": "erzeugt"}
    exec(compile(quelltext, "<erzeugt>", "exec"), namensraum)
    return namensraum


def test_selbst_und_vorwaertsbezug_im_typ() -> None:
    """Punkt 148: `naechster: Knoten` in `Knoten` und ein Typ, dessen
    Klasse erst danach steht, brachen beim Import mit `NameError`
    ab."""
    knoten = _klasse(
        "Knoten",
        id="s1",
        attributes=[
            {"name": "wert", "type": "int"},
            {"name": "naechster", "type": "Knoten", "value": "None"},
        ],
        operations=[{"name": "weiter", "type": "Knoten"}],
    )
    kunde = _klasse(
        "Kunde", id="s2", attributes=[{"name": "konto", "type": "Konto"}]
    )
    konto = _klasse("Konto", id="s3")

    code = diagramm_als_python(_diagramm(knoten, kunde, konto))

    assert code.startswith("from __future__ import annotations\n")
    namensraum = _ausfuehren(code)
    assert namensraum["Knoten"](1).naechster is None
    assert namensraum["Kunde"](namensraum["Konto"]()).konto is not None


def _tier_und_hund(**tier: object) -> dict:
    return _diagramm(
        _klasse(
            "Hund", id="s2", attributes=[{"name": "rasse", "type": "str"}]
        ),
        _klasse(
            "Tier",
            id="s1",
            attributes=tier.pop(
                "attributes", [{"name": "name", "type": "str"}]
            ),
        ),
        verbindungen=[
            {"id": "c1", "kind": "inheritance", "from": "s2", "to": "s1"}
        ],
    )


def test_unterklasse_ruft_den_konstruktor_der_basisklasse() -> None:
    """Punkt 149: `Hund` bekam nur `rasse`, und `name` ließ sich gar
    nicht übergeben."""
    code = diagramm_als_python(_tier_und_hund())

    assert "def __init__(self, name: str, rasse: str) -> None:" in code
    assert "        super().__init__(name)" in code
    hund = _ausfuehren(code)["Hund"]("Bello", "Dackel")
    assert hund.name == "Bello"
    assert hund.rasse == "Dackel"


def test_parameter_mit_startwert_der_basisklasse_stehen_hinten() -> None:
    daten = _tier_und_hund(
        attributes=[
            {"name": "name", "type": "str"},
            {"name": "alter", "type": "int", "value": "0"},
        ]
    )

    code = diagramm_als_python(daten)

    assert (
        "def __init__(self, name: str, rasse: str, alter: int = 0)" in code
    )
    assert "super().__init__(name, alter)" in code
    hund = _ausfuehren(code)["Hund"]("Bello", "Dackel", 3)
    assert (hund.name, hund.rasse, hund.alter) == ("Bello", "Dackel", 3)


def test_basisklasse_ausserhalb_des_diagramms() -> None:
    """Steht die Basisklasse nicht im Diagramm, gibt es wenigstens
    `super().__init__()` mit einem Hinweis."""
    hund = _klasse(
        "Hund", id="s2", attributes=[{"name": "rasse", "type": "str"}]
    )
    fremd = {
        "id": "s9", "kind": "note", "name": "Tier",
        "x": 0, "y": 0, "w": 10, "h": 10,
    }
    daten = _diagramm(
        hund,
        fremd,
        verbindungen=[
            {"id": "c1", "kind": "inheritance", "from": "s2", "to": "s9"}
        ],
    )

    code = klasse_als_python(hund, daten)

    assert "# „Tier“ steht nicht im Diagramm." in code
    assert "        super().__init__()" in code
    namensraum = _ausfuehren("class Tier:\n    pass\n\n" + code)
    assert namensraum["Hund"]("Dackel").rasse == "Dackel"


def test_leere_liste_als_startwert_gehoert_jedem_objekt_allein() -> None:
    """Punkt 161: `schueler: list = []` wurde zur Vorgabe eines
    Parameters, und alle Objekte teilten sich eine Liste."""
    klasse = _klasse(
        "Kurs",
        attributes=[
            {"name": "name", "type": "str"},
            {"name": "schueler", "type": "list", "value": "[]"},
            {"name": "noten", "type": "dict", "value": "dict()"},
        ],
    )

    code = diagramm_als_python(_diagramm(klasse))

    assert "def __init__(self, name: str) -> None:" in code
    assert "        self.schueler = []" in code
    kurs = _ausfuehren(code)["Kurs"]
    a, b = kurs("Informatik"), kurs("Mathematik")
    a.schueler.append("Anna")
    a.noten["Anna"] = 1
    assert b.schueler == []
    assert b.noten == {}


def test_kommentare_mit_anfuehrungszeichen_und_backslash() -> None:
    """Punkt 178: ein `"` am Ende ergab vier Anführungszeichen, ein
    Pfad mit Backslash einen Fehler im Escape `\\U`."""
    klasse = _klasse(
        "Speicher",
        comment="Legt die Datei unter C:\\Users\\schule ab.",
        operations=[
            {"name": "sagen", "comment": 'Gibt "Hallo"'},
            {"name": "zitat", "comment": 'Drei """ im Text'},
        ],
    )
    from ide.diagramm.klassen_code import ungueltige_namen

    daten = _diagramm(klasse)
    assert ungueltige_namen(daten) == []
    speicher = _ausfuehren(diagramm_als_python(daten))["Speicher"]
    assert speicher.__doc__ == "Legt die Datei unter C:\\Users\\schule ab."
    assert speicher.sagen.__doc__ == 'Gibt "Hallo"'
    assert speicher.zitat.__doc__ == 'Drei """ im Text'


def test_gewaehlte_notiz_ergibt_keinen_code(tmp_path: Path) -> None:
    """Punkt 179: aus einer Notiz „Konto“ wurde `class Konto: ...`, und
    die Notiz bekam nebenbei leere Attributlisten."""
    import copy

    from ide.diagramm import DiagrammFenster, diagramm_erzeugen

    fenster = DiagrammFenster(
        diagramm_erzeugen("class", tmp_path / "bank.pdiag", "bank")
    )
    flaeche = fenster.zeichenflaeche
    flaeche.form_platzieren("class", 500, 200)["name"] = "Bank"
    notiz = flaeche.form_platzieren("note", 200, 200)
    notiz["name"] = "Konto"
    flaeche._auswaehlen(notiz)
    vorher = copy.deepcopy(notiz)
    ziel = tmp_path / "u_bank.py"

    assert fenster.quelltext_code("auswahl") == ""
    assert fenster.quelltext_erzeugen("datei", "auswahl", ziel) is None

    assert not ziel.exists()
    assert "Nichts zu erzeugen" in fenster.statusBar().currentMessage()
    assert notiz == vorher
    assert "attributes" not in notiz and "operations" not in notiz


def test_komposition_wird_zum_attribut() -> None:
    """Punkt 182: aus `Auto` ◆→ `Motor` wurden zwei Klassen ohne
    Verbindung, obwohl der Kommentar ein Attribut versprach."""
    daten = _diagramm(
        _klasse("Motor", id="s1"),
        _klasse("Rad", id="s3"),
        _klasse("Auto", id="s2"),
        verbindungen=[
            {"id": "c1", "kind": "composition", "from": "s2", "to": "s1"},
            {
                "id": "c2", "kind": "aggregation", "from": "s2", "to": "s3",
                "labels": {"from": "1", "to": "4"},
            },
        ],
    )

    code = diagramm_als_python(daten)

    assert "class Auto:" in code
    assert "def __init__(self, motor: Motor) -> None:" in code
    assert "        self.motor = motor" in code
    assert "        self.rad_liste = []" in code
    namensraum = _ausfuehren(code)
    auto = namensraum["Auto"](namensraum["Motor"]())
    assert isinstance(auto.motor, namensraum["Motor"])
    assert auto.rad_liste == []


def test_rollenname_und_vorhandenes_attribut_bei_komposition() -> None:
    """Ein Rollenname am Teil wird zum Attributnamen; ein Attribut, das
    das Teil schon beschreibt, wird nicht verdoppelt."""
    daten = _diagramm(
        _klasse("Motor", id="s1"),
        _klasse("Lampe", id="s3"),
        _klasse(
            "Auto",
            id="s2",
            attributes=[{"name": "antrieb", "type": "Motor"}],
        ),
        verbindungen=[
            {"id": "c1", "kind": "composition", "from": "s2", "to": "s1"},
            {
                "id": "c2", "kind": "composition", "from": "s2", "to": "s3",
                "labels": {"to": "scheinwerfer 0..2"},
            },
        ],
    )

    code = diagramm_als_python(daten)

    assert "def __init__(self, antrieb: Motor) -> None:" in code
    assert "self.motor" not in code
    assert "        self.scheinwerfer = []" in code
    _ausfuehren(code)


def _hund_mit_konstruktor(*parameter: dict) -> dict:
    daten = _tier_und_hund(
        attributes=[
            {"name": "name", "type": "str"},
            {"name": "alter", "type": "int", "value": "0"},
        ]
    )
    daten["shapes"][0]["operations"] = [
        {"name": "__init__", "parameters": list(parameter)}
    ]
    return daten


def test_modellierter_konstruktor_der_unterklasse_ruft_die_basisklasse() -> None:
    """Punkt 283: ein selbst eingetragenes `Hund.__init__(name, rasse)`
    wies nur `rasse` zu, und `name` ging verloren."""
    code = diagramm_als_python(
        _hund_mit_konstruktor(
            {"name": "name", "type": "str"},
            {"name": "rasse", "type": "str"},
        )
    )

    assert "        super().__init__(name)" in code
    hund = _ausfuehren(code)["Hund"]("Bello", "Dackel")
    assert (hund.name, hund.rasse, hund.alter) == ("Bello", "Dackel", 0)


def test_modellierter_konstruktor_reicht_spaetere_werte_mit_namen() -> None:
    """Fehlt ein Parameter der Basisklasse, landet der nächste nicht
    an dessen Stelle, und ein fehlender Pflichtwert wird benannt."""
    code = diagramm_als_python(
        _hund_mit_konstruktor(
            {"name": "rasse", "type": "str"},
            {"name": "alter", "type": "int"},
        )
    )

    assert "# Der Konstruktor von „Tier“ erwartet außerdem: name" in code
    assert "        super().__init__(alter=alter)" in code
    _gueltig(code)


def test_modellierter_konstruktor_bei_fremder_basisklasse() -> None:
    hund = _klasse(
        "Hund",
        id="s2",
        attributes=[{"name": "rasse", "type": "str"}],
        operations=[
            {"name": "__init__", "parameters": [{"name": "rasse"}]}
        ],
    )
    fremd = {
        "id": "s9", "kind": "note", "name": "Tier",
        "x": 0, "y": 0, "w": 10, "h": 10,
    }
    daten = _diagramm(
        hund,
        fremd,
        verbindungen=[
            {"id": "c1", "kind": "inheritance", "from": "s2", "to": "s9"}
        ],
    )

    code = klasse_als_python(hund, daten)

    assert "        super().__init__()" in code
    namensraum = _ausfuehren("class Tier:\n    pass\n\n" + code)
    assert namensraum["Hund"]("Dackel").rasse == "Dackel"


def test_uml_typen_werden_zu_python_typen() -> None:
    """Punkt 483: „Integer“, „Real“, „String“ und „Boolean“ standen
    unverändert im Code, und der Kopf der Datei verlangte, sie zu
    importieren. Eine eigene Klasse bleibt, wie sie heißt."""
    klasse = _klasse(
        "Konto",
        attributes=[
            {"name": "stand", "type": "Real", "visibility": "public"},
            {"name": "buchungen", "type": "list[Integer]", "visibility": "public"},
            {"name": "inhaber", "type": "Person", "visibility": "public"},
        ],
        operations=[
            {
                "name": "gesperrt",
                "visibility": "public",
                "parameters": [{"name": "grund", "type": "String"}],
                "type": "Boolean",
            }
        ],
    )

    code = diagramm_als_python({"shapes": [klasse]})

    assert "stand: float" in code
    assert "buchungen: list[int]" in code
    assert "inhaber: Person" in code
    assert "def gesperrt(self, grund: str) -> bool:" in code
    assert "importiert werden: Person" in code
    _gueltig(code)
