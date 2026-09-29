"""Die Komponenten-Referenz stimmt mit dem Code überein (offener
Punkt 80).

`docs/komponenten.md` erscheint in der IDE unter Hilfe →
Komponenten-Referenz. Sie nannte Komponenten „folgt später“, die es
längst gab, und ließ Eigenschaften wie `Edit.read_only` weg. Dieser
Test vergleicht jede Eigenschaft und jedes Ereignis jeder Komponente
der Palette mit der Seite; eine neue Eigenschaft ohne Eintrag fällt
damit sofort auf.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import pcl
from ide.palette.palette import ALLE_KOMPONENTEN
from pcl import crt
from pcl.control import Control
from pcl.form import Form
from pcl.properties import (
    BAUM_EIGENSCHAFTEN,
    SAMMLUNGS_EIGENSCHAFTEN,
    VERSCHACHTELTE_EIGENSCHAFTEN,
    VERWEIS_EIGENSCHAFTEN,
    eigenschaften,
    ereignisse,
)

_SEITE = (Path(__file__).resolve().parents[1] / "docs" / "komponenten.md").read_text(
    encoding="utf-8"
)

#: Der Abschnitt mit allem, was jede Komponente von `Control` erbt.
_GEMEINSAM = "Was jede Komponente hat"


def _abschnitt(titel: str) -> str:
    """Der Text unter `## titel` bis zur nächsten Überschrift dieser
    Ebene; Unterabschnitte (`###`) gehören dazu."""
    treffer = re.search(
        rf"^## {re.escape(titel)}\s*$(.*?)(?=^## |\Z)", _SEITE, re.M | re.S
    )
    assert treffer is not None, f"Kein Abschnitt „## {titel}“ in komponenten.md"
    return treffer.group(1)


def _kommt_vor(name: str, text: str) -> bool:
    return re.search(rf"(?<![\w.]){re.escape(name)}(?!\w)", text) is not None


def _alle_namen(typ: type) -> set[str]:
    """Alles, was der Objektinspektor zu `typ` anzeigt, plus die
    Ereignisse."""
    namen = set(eigenschaften(typ)) | set(ereignisse(typ))
    namen |= {
        name
        for name, eintrag in VERSCHACHTELTE_EIGENSCHAFTEN.items()
        if hasattr(typ, eintrag.attribut)
    }
    namen |= {name for name in SAMMLUNGS_EIGENSCHAFTEN if hasattr(typ, name)}
    namen |= {name for name in BAUM_EIGENSCHAFTEN if hasattr(typ, name)}
    if not getattr(typ, "nur_im_designer", False):
        namen |= {name for name in VERWEIS_EIGENSCHAFTEN if hasattr(typ, name)}
    return namen


def _geerbt_und_gleich(typ: type, name: str) -> bool:
    """Ob `name` unverändert von `Control` kommt - dann steht es im
    gemeinsamen Abschnitt und muss nicht bei jeder Komponente stehen.
    Eine Komponente, die etwa `width` mit eigener Vorgabe neu
    deklariert, muss es selbst nennen."""
    if typ is Form or not issubclass(typ, Control):
        return False
    von_control = (
        {**eigenschaften(Control), **ereignisse(Control)}.get(name)
    )
    eigen = {**eigenschaften(typ), **ereignisse(typ)}.get(name)
    if von_control is not None:
        return eigen is von_control
    # Untereigenschaften und Verweise gibt es an jeder Komponente.
    return name in VERSCHACHTELTE_EIGENSCHAFTEN and name.startswith(
        ("font_", "anchors_")
    ) or (
        name in VERWEIS_EIGENSCHAFTEN
    )


KOMPONENTEN = (Form, *ALLE_KOMPONENTEN)


@pytest.mark.parametrize("typ", KOMPONENTEN, ids=[t.__name__ for t in KOMPONENTEN])
def test_jede_eigenschaft_und_jedes_ereignis_steht_in_der_referenz(typ) -> None:
    eigener = _abschnitt(typ.__name__)
    gemeinsam = _abschnitt(_GEMEINSAM)

    fehlt = sorted(
        name
        for name in _alle_namen(typ)
        if not _kommt_vor(name, eigener)
        and not (_geerbt_und_gleich(typ, name) and _kommt_vor(name, gemeinsam))
    )

    assert not fehlt, f"{typ.__name__}: in komponenten.md fehlt {fehlt}"


def test_der_gemeinsame_abschnitt_nennt_alles_von_control() -> None:
    gemeinsam = _abschnitt(_GEMEINSAM)
    for name in (*eigenschaften(Control), *ereignisse(Control), "popup_menu"):
        assert _kommt_vor(name, gemeinsam), name


@pytest.mark.parametrize(
    "name",
    [
        name
        for name in pcl.__all__
        if name[0].islower() and callable(getattr(pcl, name)) and name != "analyse"
    ],
)
def test_jede_funktion_aus_pcl_steht_in_der_referenz(name) -> None:
    assert _kommt_vor(name, _SEITE), name


@pytest.mark.parametrize(
    "name",
    [
        name
        for name in vars(crt)
        if not name.startswith("_")
        and callable(getattr(crt, name))
        and getattr(getattr(crt, name), "__module__", "") == "pcl.crt"
        and name != "virtuelles_terminal_einschalten"
    ],
)
def test_jede_funktion_aus_crt_steht_in_der_referenz(name) -> None:
    assert _kommt_vor(name, _abschnitt("Konsolenprogramme: `pcl.crt`")), name


def test_die_feldwerte_der_datenbank_stehen_drin() -> None:
    for name in ("as_string", "as_integer", "as_float", "field_by_name"):
        assert _kommt_vor(name, _SEITE), name


@pytest.mark.parametrize(
    "text",
    [
        "folgt später",
        "## Offene Punkte",
        "Wirklich noch offen",
        "Vorlage pro Komponente",
        "Arbeitspaket",
        "M15",
    ],
)
def test_keine_internen_abschnitte(text) -> None:
    assert text not in _SEITE
