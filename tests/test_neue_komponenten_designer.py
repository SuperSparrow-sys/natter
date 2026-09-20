"""Designer-Rundreise für die Komponenten aus Schritt 6: platzieren →
`.pfm` → `u_main_design.py` → wieder laden. Headless.

Ohne diese Kette wäre eine Komponente zwar im Designer ablegbar, beim
nächsten Öffnen aber verschwunden. Geprüft wird für jede neue
`Control`-Komponente einzeln, weil Serialisierung und Codeerzeugung zwar
allgemein über `pcl.properties.eigenschaften()` laufen, eine Komponente
aber trotzdem durchfallen kann - etwa wenn ein Wert kein JSON-Typ ist
oder der Name nicht aus `pcl` importierbar ist.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ide.codegen.design import design_code_erzeugen, design_datei_erzeugen
from ide.designer import formular_fuer_designer_laden
from ide.designer.canvas import DesignerCanvas
from ide.designer.pfm_schreiben import formular_als_pfm_speichern, pfm_aus_formular
from pcl import (
    FloatSpinEdit,
    Form,
    GroupBox,
    Panel,
    ProgressBar,
    RadioGroup,
    SpinEdit,
    TrackBar,
)


class _LeeresFormular(Form):
    pass


NEU = (SpinEdit, FloatSpinEdit, TrackBar, ProgressBar, GroupBox, Panel, RadioGroup)


@pytest.mark.parametrize("typ", NEU, ids=lambda typ: typ.__name__)
def test_platzieren_erzeugt_den_erwarteten_pfm_eintrag(typ: type) -> None:
    formular = _LeeresFormular()
    canvas = DesignerCanvas(formular)

    komponente = canvas.komponente_platzieren(typ, 40, 60)

    daten = pfm_aus_formular(formular)
    kind = next(k for k in daten["children"] if k["type"] == typ.__name__)
    assert kind["name"] == canvas._attributname(komponente)
    assert kind["properties"]["left"] == 40
    assert kind["properties"]["top"] == 64  # am Raster


@pytest.mark.parametrize("typ", NEU, ids=lambda typ: typ.__name__)
def test_erzeugter_code_importiert_und_erzeugt_die_komponente(typ: type) -> None:
    formular = _LeeresFormular()
    canvas = DesignerCanvas(formular)
    canvas.komponente_platzieren(typ, 10, 20)

    quelltext = design_code_erzeugen(pfm_aus_formular(formular), "u_main.pfm")

    assert f"from pcl import {typ.__name__}" in quelltext or f", {typ.__name__}" in quelltext
    assert f"= {typ.__name__}(self)" in quelltext


@pytest.mark.parametrize("typ", NEU, ids=lambda typ: typ.__name__)
def test_rundreise_speichern_laden_erhaelt_die_komponente(typ: type, tmp_path: Path) -> None:
    formular = _LeeresFormular()
    canvas = DesignerCanvas(formular)
    komponente = canvas.komponente_platzieren(typ, 33, 44)
    name = canvas._attributname(komponente)
    pfm_pfad = tmp_path / "u_main.pfm"
    formular_als_pfm_speichern(formular, pfm_pfad)

    wieder_geladen = formular_fuer_designer_laden(pfm_pfad)

    zurueck = getattr(wieder_geladen, name)
    assert type(zurueck) is typ
    # Abgelegt bei (33, 44), eingerastet auf (32, 48).
    assert (zurueck.left, zurueck.top) == (32, 48)
    assert (zurueck.width, zurueck.height) == (komponente.width, komponente.height)


def test_eigenschaften_ueberstehen_die_rundreise(tmp_path: Path) -> None:
    """Nicht nur Lage und Größe: jede im Designer gesetzte Eigenschaft
    muss in der `.pfm` landen und beim Laden wieder ankommen."""
    formular = _LeeresFormular()
    canvas = DesignerCanvas(formular)
    spin = canvas.komponente_platzieren(SpinEdit, 0, 0)
    spin.minimum, spin.maximum, spin.increment = 5, 50, 5
    spin.value = 25
    regler = canvas.komponente_platzieren(TrackBar, 0, 40)
    regler.maximum, regler.frequency, regler.position = 20, 4, 8
    balken = canvas.komponente_platzieren(ProgressBar, 0, 80)
    balken.position, balken.show_text = 42, False
    kasten = canvas.komponente_platzieren(GroupBox, 0, 120)
    kasten.caption = "Zahlungsart"

    pfm_pfad = tmp_path / "u_main.pfm"
    formular_als_pfm_speichern(formular, pfm_pfad)
    wieder = formular_fuer_designer_laden(pfm_pfad)

    assert (wieder.spinedit.minimum, wieder.spinedit.maximum) == (5, 50)
    assert (wieder.spinedit.increment, wieder.spinedit.value) == (5, 25)
    assert (wieder.trackbar.maximum, wieder.trackbar.frequency) == (20, 4)
    assert wieder.trackbar.position == 8
    assert wieder.progressbar.position == 42
    assert wieder.progressbar.show_text is False
    assert wieder.groupbox.caption == "Zahlungsart"


def test_radiogroup_items_ueberstehen_die_rundreise(tmp_path: Path) -> None:
    """`items` ist eine Sammlung (`SAMMLUNGS_EIGENSCHAFTEN`) und wird im
    erzeugten Code vor `item_index` zugewiesen - sonst setzte das
    Füllen der Gruppe die Vorauswahl wieder zurück."""
    formular = _LeeresFormular()
    canvas = DesignerCanvas(formular)
    gruppe = canvas.komponente_platzieren(RadioGroup, 10, 10)
    gruppe.items = ["Klein", "Mittel", "Groß"]
    gruppe.item_index = 2
    gruppe.caption = "Größe"

    pfm_pfad = tmp_path / "u_main.pfm"
    formular_als_pfm_speichern(formular, pfm_pfad)
    daten = json.loads(pfm_pfad.read_text(encoding="utf-8"))
    wieder = formular_fuer_designer_laden(pfm_pfad)

    kind = daten["children"][0]
    assert kind["properties"]["items"] == ["Klein", "Mittel", "Groß"]
    assert kind["properties"]["item_index"] == 2
    assert list(wieder.radiogroup.items) == ["Klein", "Mittel", "Groß"]
    assert wieder.radiogroup.item_index == 2


def test_erzeugte_design_datei_ist_ausfuehrbarer_python(tmp_path: Path) -> None:
    """Die `u_main_design.py` wird wirklich geschrieben und lässt sich
    ausführen - der Weg, den ein gestartetes Schülerprogramm geht."""
    formular = _LeeresFormular()
    canvas = DesignerCanvas(formular)
    for typ in NEU:
        canvas.komponente_platzieren(typ, 5, 5)
    pfm_pfad = tmp_path / "u_main.pfm"
    formular_als_pfm_speichern(formular, pfm_pfad)

    ziel = tmp_path / "u_main_design.py"
    quelltext = design_datei_erzeugen(pfm_pfad, ziel)

    namensraum: dict[str, object] = {}
    exec(compile(quelltext, str(ziel), "exec"), namensraum)
    klasse = namensraum["_LeeresFormularDesign"]
    erzeugt = klasse()
    for typ in NEU:
        assert isinstance(getattr(erzeugt, typ.__name__.lower()), typ)


def test_alle_neuen_sichtbaren_komponenten_sind_in_der_palette() -> None:
    from ide.palette.palette import ALLE_KOMPONENTEN

    in_der_palette = set(ALLE_KOMPONENTEN)
    for typ in NEU:
        assert typ in in_der_palette, typ.__name__
