"""Jede Eigenschaft jeder Komponente einmal von Hand geändert (M11, 3).

Der Arbeitsauftrag lautet wörtlich: „jede `pcl`-Komponente auf ein
Formular setzen, jede ihrer Eigenschaften im Objektinspektor ändern, das
Programm starten und nachsehen, ob die Änderung auch wirklich ankommt“.
Das Platzieren war geprüft, das Ändern jeder einzelnen Eigenschaft
nicht.

Genau diesen Weg gehen die Tests hier – nicht abgekürzt über `setattr`,
sondern über die Zelle im Objektinspektor, weil dazwischen mehr liegt,
als man denkt: die Tabelle wandelt den eingetippten Text in den Typ der
Eigenschaft, setzt ihn live, meldet ihn an den Designer, der schreibt
die `.pfm` und erzeugt daraus `u_*_design.py` neu. Erst diese Datei
führt das Schülerprogramm beim Start aus. Jedes Glied dieser Kette ist
schon einmal gerissen, ohne dass der Designer selbst etwas davon
gemerkt hätte.

Zwei Dinge werden geprüft:

* kommt der Wert im Programm an – die erzeugte Design-Datei wird
  ausgeführt und die entstandene Komponente befragt,
* sieht der Designer aus wie das Programm – das Qt-Widget der
  geänderten Komponente muss Pixel für Pixel dem Widget entsprechen,
  das das Programm baut. Die beiden entstehen auf verschiedenen Wegen
  (`_bei_prop_aenderung` gegen `_qwidget_erzeugen`); fehlt die
  Eigenschaft in einem davon, fällt es genau hier auf.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import date, time
from pathlib import Path
from typing import Any

import pytest
from PySide6.QtCore import Qt

from ide.designer.canvas import DesignerCanvas
from ide.inspector.objektinspektor import Objektinspektor
from ide.palette.palette import ALLE_KOMPONENTEN
from pcl.components.data_controls import (
    DBComboBox,
    DBEdit,
    DBGrid,
    DBNavigator,
    DBText,
)
from pcl.form import Form
from pcl.properties import (
    SAMMLUNGS_EIGENSCHAFTEN,
    VERSCHACHTELTE_EIGENSCHAFTEN,
    eigenschaften,
    text_aus_wert,
    wert_lesen,
)

#: Alle Komponenten, die sich überhaupt auf ein Formular setzen lassen.
#: Über `ALLE_KOMPONENTEN` statt über zwei namentlich genannte Reiter:
#: so läuft eine später ergänzte Komponente hier von selbst mit, statt
#: still durchzurutschen.
#:
#: Die `DB*`-Komponenten stehen in keinem Palettenreiter – sie werden im
#: Code erzeugt –, laufen hier aber seither mit. Vorher
#: konnten sie es nicht: ihr Konstruktor verlangte eine `DataSource`
#: (`DBGrid(parent, data_source)`), der Designer erzeugt Komponenten
#: aber mit `typ(formular)` allein. Genau das war der offene Punkt aus
#: M11; seit die Datenquelle freiwillig ist, fällt er weg.
PALETTE = (*ALLE_KOMPONENTEN, DBGrid, DBText, DBEdit, DBComboBox, DBNavigator)

#: Eigenschaften mit einer festen Auswahl oder einem festen Format. Ein
#: beliebiger Text („shape-neu“) wäre kein Wert, den ein Mensch je
#: eintippen würde, und sagte über den Weg durch die Kette nichts aus.
BESONDERE_WERTE: dict[str, Any] = {
    "shape": "circle",
    "kind": "line",
    "color": "#ffcc00",
    "pen_color": "#3366cc",
    "brush_color": "#22aa55",
    "font_name": "Courier New",
    "decimals": 3,
    # Ein Index braucht einen Eintrag, auf den er zeigt - deshalb
    # bekommt jede Komponente mit `items` unten erst drei Stück.
    "item_index": 1,
}

#: Vorrat für Komponenten mit `items`: ohne Einträge wäre `item_index`
#: nicht sinnvoll prüfbar. `RadioGroup` setzt einen Index ohne Option
#: bewusst auf -1 zurück, weil eine Auswahl, die niemand sieht,
#: schlimmer wäre als keine.
VORRAT = ["Apfel", "Birne", "Kirsche"]


def _probewert(typ: type, name: str, alt: Any) -> Any:
    """Ein Wert, der sich vom bisherigen unterscheidet."""
    if name in BESONDERE_WERTE:
        return BESONDERE_WERTE[name]
    if typ is date:
        # Ein anderer Tag als der Standard (1.1.2026) - und einer mit
        # zweistelligem Tag und Monat, damit ein abgeschnittenes Format
        # auffiele.
        return date(2026, 11, 23)
    if typ is time:
        return time(17, 45)
    if typ is bool:
        return not alt
    if typ is int:
        return (alt or 0) + 7
    if typ is float:
        return (alt or 0.0) + 2.5
    if typ is list:
        return ["eins", "zwei"]
    return f"{name}-neu"


class _LeeresFormular(Form):
    def create_components(self) -> None:
        pass


def _alle_eigenschaften(typ: type) -> list[str]:
    """Alles, was der Objektinspektor zu dieser Komponente anzeigt: die
    echten `Prop`s, die aufklappbaren Untereigenschaften (`font.bold`)
    und die Sammlungen (`items`, `lines`)."""
    # Bewusst an der Klasse abgefragt und nicht an einem Probeobjekt:
    # die Liste entsteht beim Einsammeln der Tests, und ein QWidget darf
    # es zu diesem Zeitpunkt noch nicht geben.
    return sorted(
        [
            *eigenschaften(typ),
            *[
                name
                for name, eintrag in VERSCHACHTELTE_EIGENSCHAFTEN.items()
                if hasattr(typ, eintrag.attribut)
            ],
            *[name for name in SAMMLUNGS_EIGENSCHAFTEN if hasattr(typ, name)],
        ]
    )


def _faelle() -> list[tuple[type, str]]:
    return [(typ, name) for typ in PALETTE for name in _alle_eigenschaften(typ)]


FAELLE = _faelle()
KENNUNGEN = [f"{typ.__name__}.{name}" for typ, name in FAELLE]


def _im_inspektor_aendern(
    tmp_path: Path, typ: type, eigenschaft: str
) -> tuple[Any, Any, Path, DesignerCanvas]:
    """Setzt `eigenschaft` über die Zelle im Objektinspektor – den Weg,
    den auch eine Hand nimmt – und gibt Komponente, neuen Wert und den
    Pfad der `.pfm` zurück."""
    pfm = tmp_path / "u_haupt.pfm"
    formular = _LeeresFormular()
    canvas = DesignerCanvas(formular, pfm_pfad=pfm)
    komponente = canvas.komponente_platzieren(typ, 0, 0)
    if hasattr(typ, "items"):
        komponente.items = VORRAT

    inspektor = Objektinspektor()
    inspektor.formular_anzeigen(formular, canvas)
    inspektor.baum.setCurrentItem(inspektor.baum.topLevelItem(0).child(0))
    tabelle = inspektor.eigenschaften_tabelle

    zeile = next(
        z for z in range(tabelle.rowCount()) if tabelle.item(z, 0).text() == eigenschaft
    )
    art = tabelle._typ_von(eigenschaft)
    neu = _probewert(art, eigenschaft, wert_lesen(komponente, eigenschaft))

    element = tabelle.item(zeile, 1)
    if art is bool:
        element.setCheckState(Qt.CheckState.Checked if neu else Qt.CheckState.Unchecked)
    elif art is list:
        # Sammlungen gehen im Betrieb über den Doppelklick-Dialog; der
        # wartet auf einen Knopfdruck, deshalb hier sein Ergebnis.
        tabelle._wert_setzen(eigenschaft, neu)
    else:
        # `text_aus_wert`, nicht `str`: in die Zelle wird getippt, was
        # ein Mensch tippt - ein Datum also deutsch als `23.11.2026`
        # und nicht als `2026-11-23`.
        element.setText(text_aus_wert(neu))

    assert not tabelle.fehlertext, tabelle.fehlertext
    return komponente, neu, pfm, canvas


def _programm_starten(pfm: Path, zaehler: str) -> tuple[Any, Any]:
    """Führt die erzeugte Design-Datei aus – genau der Code, den das
    Schülerprogramm beim Start ausführt – und liefert das Formular und
    die Komponente darauf.

    Das Formular muss mit heraus: es hält das Qt-Widget der Komponente
    am Leben. Ohne diese Referenz räumt Python es zwischen den beiden
    Zeilen des Tests weg („Internal C++ object already deleted“)."""
    design = pfm.parent / f"{pfm.stem}_design.py"
    assert design.exists(), "Der Designer hat keinen Code erzeugt."
    spec = importlib.util.spec_from_file_location(f"rundlauf_{zaehler}", design)
    modul = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = modul
    try:
        spec.loader.exec_module(modul)
        formular = modul._LeeresFormularDesign()
    finally:
        del sys.modules[spec.name]
    komponente = next(
        wert for wert in vars(formular).values() if hasattr(wert, "_qwidget")
    )
    return formular, komponente


@pytest.mark.parametrize(("typ", "eigenschaft"), FAELLE, ids=KENNUNGEN)
def test_die_aenderung_kommt_im_laufenden_programm_an(
    tmp_path: Path, typ: type, eigenschaft: str
) -> None:
    komponente, neu, pfm, _ = _im_inspektor_aendern(tmp_path, typ, eigenschaft)

    # 1. am Live-Objekt, das der Designer zeigt
    assert wert_lesen(komponente, eigenschaft) == neu

    # 2. in der .pfm, der einzigen Quelle des Designers
    kind = json.loads(pfm.read_text(encoding="utf-8"))["children"][0]
    assert eigenschaft in kind["properties"]

    # 3. im Programm, das aus der erzeugten Design-Datei entsteht
    _, im_programm = _programm_starten(pfm, f"{typ.__name__}_{eigenschaft}")
    assert wert_lesen(im_programm, eigenschaft) == neu


@pytest.mark.parametrize(("typ", "eigenschaft"), FAELLE, ids=KENNUNGEN)
def test_der_designer_zeigt_dasselbe_wie_das_programm(
    tmp_path: Path, typ: type, eigenschaft: str
) -> None:
    """Der Wert kann stimmen und das Bild trotzdem nicht: die Komponente
    im Designer bekommt ihn über `_bei_prop_aenderung`, die im Programm
    über `_qwidget_erzeugen`. Fehlt die Eigenschaft in einem der beiden
    Wege, sieht der Schüler im Designer etwas anderes als später."""
    komponente, _, pfm, canvas = _im_inspektor_aendern(tmp_path, typ, eigenschaft)
    canvas._auswaehlen(canvas.formular)  # Auswahlrahmen weg von der Komponente

    formular, im_programm = _programm_starten(pfm, f"bild_{typ.__name__}_{eigenschaft}")

    assert komponente._qwidget.grab().toImage() == im_programm._qwidget.grab().toImage()
    assert formular is not None  # hält das Widget bis hierher am Leben
