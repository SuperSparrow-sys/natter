"""Generator: `.pfm` → `u_*_design.py`.

Siehe README.md, Abschnitt 4.2 (Formularbeschreibung) und 4.3
(erzeugter Formular-Code). Die `.pfm` ist die einzige Quelle für den
Designer und wird nie aus dem generierten Code zurückgelesen; die
generierte Datei wird nie von Hand bearbeitet (Kopfzeile, `AGENTS.md`).
"""

from __future__ import annotations

import json
import keyword
from datetime import date, time
from pathlib import Path
from typing import Any

from ide.atomar import atomar_schreiben
from ide.pfade import daten_ordner
from ide.schema import json_datei_lesen
from ide.schema import pruefen as schema_pruefen
from pcl.properties import (
    BAUM_EIGENSCHAFTEN,
    SAMMLUNGS_EIGENSCHAFTEN,
    VERSCHACHTELTE_EIGENSCHAFTEN,
    VERWEIS_EIGENSCHAFTEN,
    wert_aus_pfm,
)
from pcl.properties import eigenschaften as prop_liste

_EINRUECKUNG = "    "

_SCHEMAS_DIR = daten_ordner("schemas")
_PFM_SCHEMA = json.loads((_SCHEMAS_DIR / "pfm.schema.json").read_text(encoding="utf-8"))


class PfmBeschaedigt(ValueError):
    """An einer Stelle der `.pfm`, an der ein Name stehen muss, steht
    etwas anderes.

    Aus der `.pfm` entsteht Python-Quelltext, den der Designer im
    Prozess der IDE ausführt. Namen gehen dabei ungeschützt in den
    Quelltext ein. Stünde dort statt eines Namens eine Anweisung,
    liefe sie schon beim Öffnen des Formulars, ohne dass das Programm
    gestartet wurde. Natter selbst schreibt nur Bezeichner; alles
    andere stammt aus einer von Hand oder absichtlich veränderten
    Datei und wird abgelehnt.
    """


def _ist_name(text: Any) -> bool:
    return (
        isinstance(text, str)
        and text.isidentifier()
        and not keyword.iskeyword(text)
    )


def _komponenten_typen() -> set[str]:
    """Die Namen aller Komponentenklassen, die `pcl` anbietet."""
    import pcl
    from pcl.properties import Komponente

    typen: set[str] = set()
    for name in pcl.__all__:
        wert = getattr(pcl, name, None)
        if isinstance(wert, type) and issubclass(wert, Komponente):
            typen.add(name)
    return typen


def _kurz(text: Any) -> str:
    """Der beanstandete Wert für die Meldung, auf eine Zeile gekürzt."""
    darstellung = text if isinstance(text, str) else repr(text)
    darstellung = " ".join(darstellung.split())
    if len(darstellung) > 60:
        darstellung = darstellung[:57] + "..."
    return darstellung


def _name_pruefen(text: Any, was: str) -> None:
    if not _ist_name(text):
        raise PfmBeschaedigt(
            f"„{_kurz(text)}“ ist kein zulässiger Name für {was}"
        )


def _eintrag_pruefen(
    eintrag: dict[str, Any], wer: str, typen: set[str]
) -> None:
    if eintrag["type"] not in typen:
        raise PfmBeschaedigt(
            f"„{_kurz(eintrag['type'])}“ bei {wer} ist keine bekannte "
            f"Komponente"
        )
    for eigenschaft in eintrag.get("properties", {}):
        _name_pruefen(eigenschaft, f"eine Eigenschaft von {wer}")
    for ereignis, methode in eintrag.get("events", {}).items():
        _name_pruefen(ereignis, f"ein Ereignis von {wer}")
        _name_pruefen(methode, f"eine Methode von {wer}")


#: So tief dürfen Komponenten ineinander liegen. Ein Formular aus dem
#: Designer kommt kaum über fünf Ebenen; bei einigen hundert brachen
#: Schema-Prüfung, Designer und Codeerzeugung mit `RecursionError` ab
#: (Punkt 548).
MAX_TIEFE = 50


def _tiefe_pruefen(pfm: Any) -> None:
    offen = [(pfm, 0)]
    while offen:
        eintrag, tiefe = offen.pop()
        if tiefe > MAX_TIEFE:
            raise PfmBeschaedigt(
                f"Die Komponenten liegen mehr als {MAX_TIEFE} Ebenen tief "
                "ineinander"
            )
        if isinstance(eintrag, dict):
            for kind in eintrag.get("children") or []:
                offen.append((kind, tiefe + 1))


def pfm_pruefen(pfm: dict[str, Any]) -> None:
    """Prüft eine geladene `.pfm` gegen das Schema und darauf, dass an
    jeder Stelle, die als Name in den erzeugten Quelltext eingeht,
    auch ein Name steht: Klasse, Komponentennamen, Eigenschaften,
    Ereignisse und Methoden. Die Typen müssen Komponenten aus `pcl`
    sein.

    Löst `PfmBeschaedigt` aus, wenn etwas nicht passt; das Schema
    meldet seine Fehler wie bisher über `ide.schema.schema_fehler()`.
    """
    _tiefe_pruefen(pfm)
    schema_pruefen(pfm, _PFM_SCHEMA)
    typen = _komponenten_typen()
    _name_pruefen(pfm["class"], "die Formularklasse")
    _eintrag_pruefen(pfm, "dem Formular", typen)
    for kind in _alle_kinder(pfm):
        _name_pruefen(kind["name"], "eine Komponente")
        _eintrag_pruefen(kind, f"„{kind['name']}“", typen)


def _eigenschaft_pfad(name: str) -> str:
    verschachtelt = VERSCHACHTELTE_EIGENSCHAFTEN.get(name)
    if verschachtelt is not None:
        return f"{verschachtelt.attribut}.{verschachtelt.unter_attribut}"
    return name


def _python_literal(wert: Any, typ: type | None = None) -> str:
    """Der Wert als Python-Quelltext.

    `typ` ist der Typ der Eigenschaft, falls bekannt. Er wird nur für
    Datum und Uhrzeit gebraucht: die stehen in der `.pfm` als
    ISO-Zeichenkette (`"2026-09-20"`), und ohne den Typ ließe sich
    nicht unterscheiden, ob das ein Datum oder eine gewöhnliche
    Beschriftung ist.
    """
    if typ in (date, time) and isinstance(wert, str):
        wert = wert_aus_pfm(typ, wert)
    if isinstance(wert, date):
        return f"date({wert.year}, {wert.month}, {wert.day})"
    if isinstance(wert, time):
        return f"time({wert.hour}, {wert.minute})"
    if isinstance(wert, str):
        return _zeichenkette(wert)
    if isinstance(wert, list):
        # Sammlungen (`items`/`lines`, pcl.properties.SAMMLUNGS_EIGENSCHAFTEN)
        # stehen in der .pfm als Liste und werden im erzeugten Code am
        # Stück zugewiesen; der Setter überträgt sie in die Strings-Sammlung.
        return "[" + ", ".join(_python_literal(eintrag) for eintrag in wert) + "]"
    if isinstance(wert, dict):
        # Bäume (`entries`, pcl.properties.BAUM_EIGENSCHAFTEN): ein
        # Menüeintrag. Die Schlüssel werden sortiert ausgegeben, damit
        # zweimal Erzeugen aus derselben .pfm auch zweimal denselben
        # Quelltext ergibt - sonst meldete Git bei jedem Speichern eine
        # Änderung, die gar keine ist.
        paare = ", ".join(
            f"{_python_literal(schluessel)}: {_python_literal(wert[schluessel])}"
            for schluessel in sorted(wert)
        )
        return "{" + paare + "}"
    return repr(wert)


def _zeichenkette(text: str) -> str:
    """`text` als vollständig maskiertes Python-Literal.

    Die JSON-Schreibweise ist zugleich gültiges Python und maskiert
    neben Anführungszeichen und Rückstrich auch Zeilenumbrüche und
    alle anderen Steuerzeichen. Bis 0.3.6 wurden nur Rückstrich und
    Anführungszeichen maskiert, und eine Beschriftung mit
    Zeilenumbruch ergab einen `SyntaxError`. Einzelne Ersatzzeichen
    (Surrogate) lassen sich nicht als UTF-8 schreiben; sie kommen als
    Unicode-Escape heraus.
    """
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        return json.dumps(text)
    return json.dumps(text, ensure_ascii=False)


def _baum_zeilen(ziel: str, name: str, eintraege: list[Any]) -> list[str]:
    """Ein Baum (`entries`) über mehrere Zeilen statt in einer einzigen.

    Ein Menü mit drei Untermenüs ergibt sonst eine Zeile von über 800
    Zeichen. Gelesen wird `u_*_design.py` zwar selten - Schüler
    bekommen sie gar nicht zu sehen -, aber wenn, dann weil etwas
    klemmt, und dann ist eine Bildschirmbreite voller geschweifter
    Klammern das Letzte, was hilft.

    Ein Eintrag je Zeile, seine Untereinträge eingerückt darunter.
    """
    zeilen = [f"{_EINRUECKUNG * 2}{ziel}.{name} = ["]
    for eintrag in eintraege:
        zeilen.extend(_eintrag_zeilen(eintrag, 3))
    zeilen.append(f"{_EINRUECKUNG * 2}]")
    return zeilen


#: Länger wird eine Zeile im erzeugten Code nicht. Dieselbe Grenze,
#: die Ruff für das ganze Projekt prüft (`pyproject.toml`).
_ZEILENLAENGE = 100


def _eintrag_zeilen(eintrag: Any, tiefe: int) -> list[str]:
    einzug = _EINRUECKUNG * tiefe
    if not isinstance(eintrag, dict) or not eintrag.get("children"):
        zeile = f"{einzug}{_python_literal(eintrag)},"
        if len(zeile) <= _ZEILENLAENGE or not isinstance(eintrag, dict):
            return [zeile]
        # Zu lang für eine Zeile: ein Feld je Zeile. Ein Menüeintrag
        # mit Tastenkürzel und Methodennamen kommt schnell auf mehr
        # als hundert Zeichen.
        return [
            f"{einzug}{{",
            *(
                f"{einzug}{_EINRUECKUNG}{_python_literal(name)}: "
                f"{_python_literal(eintrag[name])},"
                for name in sorted(eintrag)
            ),
            f"{einzug}}},",
        ]

    ohne_kinder = {name: wert for name, wert in eintrag.items() if name != "children"}
    paare = ", ".join(
        f"{_python_literal(name)}: {_python_literal(ohne_kinder[name])}"
        for name in sorted(ohne_kinder)
    )
    kopf = f"{einzug}{{{paare}, \"children\": ["
    if len(kopf) <= _ZEILENLAENGE:
        zeilen = [kopf]
    else:
        zeilen = [
            f"{einzug}{{",
            *(
                f"{einzug}{_EINRUECKUNG}{_python_literal(name)}: "
                f"{_python_literal(ohne_kinder[name])},"
                for name in sorted(ohne_kinder)
            ),
            f"{einzug}{_EINRUECKUNG}\"children\": [",
        ]
    for kind in eintrag["children"]:
        zeilen.extend(_eintrag_zeilen(kind, tiefe + 1))
    zeilen.append(f"{einzug}]}},")
    return zeilen


def _prop_typen(klassenname: str) -> dict[str, type]:
    """Die Typen der Eigenschaften einer Komponentenklasse, nachgesehen
    in `pcl`. Gebraucht nur für Datum und Uhrzeit (siehe
    `_python_literal`); eine unbekannte Klasse liefert nichts, und der
    Rest funktioniert wie zuvor."""
    import pcl

    typ = getattr(pcl, klassenname, None)
    if typ is None:
        return {}
    return {name: prop.typ for name, prop in prop_liste(typ).items()}


def _eigenschaften_zeilen(
    ziel: str, eigenschaften: dict[str, Any], typen: dict[str, type] | None = None
) -> list[str]:
    # Sammlungen (`items`/`lines`) zuerst: sie füllen das Qt-Widget neu und
    # setzen dabei dessen Auswahl zurück. Stünde `items` hinter
    # `item_index`, ginge eine im Designer gesetzte Vorauswahl beim Start
    # wieder verloren - real an der Mehrwertsteuer-Auswahl des
    # Pizza-Beispielprojekts aufgefallen.
    zuerst = SAMMLUNGS_EIGENSCHAFTEN + BAUM_EIGENSCHAFTEN
    namen = sorted(eigenschaften, key=lambda name: name not in zuerst)
    zeilen: list[str] = []
    for name in namen:
        if name in VERWEIS_EIGENSCHAFTEN:
            continue  # am Ende, siehe `_verweis_zeilen`
        if name in BAUM_EIGENSCHAFTEN:
            zeilen.extend(_baum_zeilen(ziel, name, eigenschaften[name]))
            continue
        zeilen.append(
            f"{_EINRUECKUNG * 2}{ziel}.{_eigenschaft_pfad(name)} = "
            f"{_python_literal(eigenschaften[name], (typen or {}).get(name))}"
        )
    return zeilen


def _verweis_zeilen(kinder: list[dict[str, Any]]) -> list[str]:
    """Die Zuweisungen, die auf eine andere Komponente zeigen
    (`popup_menu`).

    Sie stehen hinter allen Komponenten: in der `.pfm` kann das
    Klappmenü auch nach dem Knopf stehen, dem es gehört, und
    ``self.b_ok.popup_menu = self.pm_knopf`` vor der Zeile, die
    `self.pm_knopf` anlegt, bräche beim Start ab. Ein Name, zu dem es
    auf dem Formular keine Komponente gibt, wird übergangen - sonst
    ließe sich eine von Hand verdorbene `.pfm` nicht einmal mehr im
    Designer öffnen, um sie zu reparieren.
    """
    vorhanden = {kind["name"] for kind in kinder}
    zeilen: list[str] = []
    for kind in kinder:
        for name in VERWEIS_EIGENSCHAFTEN:
            ziel = kind.get("properties", {}).get(name)
            if isinstance(ziel, str) and ziel in vorhanden:
                zeilen.append(
                    f"{_EINRUECKUNG * 2}self.{kind['name']}.{name} = self.{ziel}"
                )
    return zeilen


def _ereignisse_zeilen(ziel: str, ereignisse: dict[str, str]) -> list[str]:
    return [
        f"{_EINRUECKUNG * 2}{ziel}.{name} = self.{handler}" for name, handler in ereignisse.items()
    ]


def _kinder_mit_eltern(
    eintrag: dict[str, Any], eltern_ausdruck: str
) -> list[tuple[dict[str, Any], str]]:
    """Alle Komponenten der `.pfm` in Reihenfolge, jede mit dem Python-
    Ausdruck ihrer Eltern (`"self"` oder `"self.p_feld"`).

    Ein Behälter muss vor seinen Kindern stehen: `Button(self.p_feld)`
    setzt voraus, dass `self.p_feld` schon existiert. Die Reihenfolge
    ergibt sich hier von selbst, weil jeder Eintrag vor seinen eigenen
    `children` eingesammelt wird.

    Die Namen bleiben dabei flach - ein Knopf im Panel heißt weiter
    `self.b_ok`. Verschachtelt ist nur, woran er hängt.
    """
    ergebnis: list[tuple[dict[str, Any], str]] = []
    for kind in eintrag.get("children", []):
        ergebnis.append((kind, eltern_ausdruck))
        ergebnis.extend(_kinder_mit_eltern(kind, f"self.{kind['name']}"))
    return ergebnis


def _alle_kinder(eintrag: dict[str, Any]) -> list[dict[str, Any]]:
    """Alle Komponenten der `.pfm`, egal wie tief - für die
    Typannotationen und die Importzeile."""
    return [kind for kind, _ in _kinder_mit_eltern(eintrag, "self")]


def design_code_erzeugen(pfm: dict[str, Any], pfm_dateiname: str) -> str:
    """Erzeugt den Python-Quelltext von `u_*_design.py` aus einer bereits
    geladenen `.pfm`. Validiert `pfm` gegen `schemas/pfm.schema.json`
    und prüft die Namen (`pfm_pruefen`), bevor irgendetwas davon in
    den Quelltext gelangt."""

    pfm_pruefen(pfm)
    # Ein Dateiname steht nur im Kommentar der Kopfzeile. Unter Windows
    # kann er keinen Zeilenumbruch enthalten; aus der Zwischenablage
    # oder einem Test kommt aber ein beliebiger Text.
    pfm_dateiname = " ".join(str(pfm_dateiname).split())

    klassenname = f"{pfm['class']}Design"
    basisklasse = pfm["type"]
    kinder: list[dict[str, Any]] = _alle_kinder(pfm)
    benoetigte_typen = sorted({basisklasse} | {kind["type"] for kind in kinder})

    kopf: list[str] = [
        f"# Automatisch erzeugt aus {pfm_dateiname} - nicht bearbeiten",
        f"from pcl import {', '.join(benoetigte_typen)}",
    ]
    zeilen: list[str] = [
        "",
        "",
        f"class {klassenname}({basisklasse}):",
    ]

    for kind in kinder:
        zeilen.append(f"{_EINRUECKUNG}{kind['name']}: {kind['type']}")
    if kinder:
        zeilen.append("")

    zeilen.append(f"{_EINRUECKUNG}def create_components(self):")
    rumpf_start = len(zeilen)

    zeilen.extend(
        _eigenschaften_zeilen("self", pfm.get("properties", {}), _prop_typen(basisklasse))
    )
    zeilen.extend(_ereignisse_zeilen("self", pfm.get("events", {})))

    for kind, eltern in _kinder_mit_eltern(pfm, "self"):
        if len(zeilen) > rumpf_start:
            zeilen.append("")
        zeilen.append(f"{_EINRUECKUNG * 2}self.{kind['name']} = {kind['type']}({eltern})")
        zeilen.extend(
            _eigenschaften_zeilen(
                f"self.{kind['name']}",
                kind.get("properties", {}),
                _prop_typen(kind["type"]),
            )
        )
        zeilen.extend(_ereignisse_zeilen(f"self.{kind['name']}", kind.get("events", {})))

    verweise = _verweis_zeilen(kinder)
    if verweise:
        zeilen.append("")
        zeilen.extend(verweise)

    if len(zeilen) == rumpf_start:
        zeilen.append(f"{_EINRUECKUNG * 2}pass")

    # `from datetime import ...` nur, wenn wirklich ein Datum oder eine
    # Uhrzeit im Rumpf steht - sonst stünde in jeder erzeugten Datei ein
    # Import, den niemand braucht.
    gebraucht = sorted(
        {
            name
            for name in ("date", "time")
            if any(f"= {name}(" in zeile for zeile in zeilen)
        }
    )
    if gebraucht:
        kopf.insert(1, f"from datetime import {', '.join(gebraucht)}")

    return "\n".join(kopf + zeilen) + "\n"


def design_datei_erzeugen(pfm_pfad: Path, ziel_pfad: Path) -> str:
    """Liest eine `.pfm`-Datei und schreibt die zugehörige
    `u_*_design.py`. Gibt den erzeugten Quelltext zurück."""
    pfm = json_datei_lesen(pfm_pfad)
    quelltext = design_code_erzeugen(pfm, pfm_pfad.name)
    atomar_schreiben(ziel_pfad, quelltext, encoding="utf-8")
    return quelltext
