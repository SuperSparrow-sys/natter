"""Abnahme von M9 (Schritt 11): die drei Diagramme des
Abnahmekriteriums aus `beispielprojekte/Ampel/diagramme/` laden und als
PDF exportieren.

Das Abnahmekriterium aus dem Konzept lautet: „UML-Klassendiagramm
`TAmpel`, Struktogramm `ampel_zeichnen` und Entscheidungstabelle der
Ampel von Hand erstellen und als PDF exportieren.“ Die drei `.pdiag`
im Beispielprojekt wurden genau so erzeugt – ausschließlich über die
Editor-Methoden, die auch Maus und Tastatur benutzen.

Die Dateien werden hier nur **gelesen**; exportiert wird nach
`tmp_path`, damit im Beispielprojekt nichts verändert wird (AGENTS.md).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ide.diagramm.datei import Diagramm
from ide.diagramm.export import als_pdf, als_png
from ide.diagramm.hinweise import pruefen

DIAGRAMME = Path(__file__).resolve().parent.parent / "beispielprojekte" / "Ampel" / "diagramme"

ABNAHME = {
    "tampel_klassen.pdiag": "class",
    "ampel_zeichnen.pdiag": "struktogramm",
    "ampel_entscheidung.pdiag": "entscheidungstabelle",
}


@pytest.mark.parametrize(("dateiname", "typ"), sorted(ABNAHME.items()))
def test_abnahmediagramm_laedt_und_hat_den_richtigen_typ(dateiname: str, typ: str) -> None:
    diagramm = Diagramm.laden(DIAGRAMME / dateiname)

    assert diagramm.typ == typ


@pytest.mark.parametrize("dateiname", sorted(ABNAHME))
def test_abnahmediagramm_laesst_sich_als_pdf_exportieren(
    dateiname: str, tmp_path: Path
) -> None:
    pdf = pytest.importorskip("PySide6.QtPdf")
    diagramm = Diagramm.laden(DIAGRAMME / dateiname)

    ziel = als_pdf(diagramm.daten, tmp_path / f"{dateiname}.pdf")

    dokument = pdf.QPdfDocument()
    dokument.load(str(ziel))
    assert dokument.pageCount() == 1
    assert ziel.stat().st_size > 5000


@pytest.mark.parametrize("dateiname", sorted(ABNAHME))
def test_abnahmediagramm_ist_nicht_leer(dateiname: str, tmp_path: Path) -> None:
    """Ein leeres, aber gültiges PDF wäre ein grüner Test ohne Inhalt –
    deshalb wird das Bild auf verschiedene Farben geprüft."""
    from PySide6.QtGui import QImage

    diagramm = Diagramm.laden(DIAGRAMME / dateiname)
    bild = QImage(str(als_png(diagramm.daten, tmp_path / "a.png")))

    farben = {
        bild.pixelColor(x, y).name()
        for x in range(0, bild.width(), 3)
        for y in range(0, bild.height(), 3)
    }
    assert len(farben) > 2


def test_klassendiagramm_bildet_die_echte_ampel_klasse_ab() -> None:
    """Inhaltliche Probe: die Methoden im Diagramm müssen zu
    `beispielprojekte/Ampel/u_ampel.py` passen."""
    daten = Diagramm.laden(DIAGRAMME / "tampel_klassen.pdiag").daten
    ampel = next(f for f in daten["shapes"] if (f.get("text") or {}).get("name") == "Ampel")

    methoden = " ".join(ampel["text"]["methods"])
    for name in ("einschalten", "ausschalten", "umschalten", "get_zustand", "get_eingeschaltet"):
        assert name in methoden


def test_struktogramm_hat_die_drei_ampelphasen() -> None:
    from ide.diagramm.bloecke import alle_bloecke

    daten = Diagramm.laden(DIAGRAMME / "ampel_zeichnen.pdiag").daten
    auswahl = next(
        b for b in alle_bloecke(daten) if b.get("kind") == "multi_branch"
    )

    assert [fall["label"] for fall in auswahl["cases"]] == ["1", "3", "2 oder 4"]


def test_entscheidungstabelle_hat_zu_jeder_regel_eine_aktion() -> None:
    """Fachliche Probe: in jeder Regel-Spalte muss genau ein `X`
    stehen – sonst wäre die Ampel in dieser Lage undefiniert."""
    daten = Diagramm.laden(DIAGRAMME / "ampel_entscheidung.pdiag").daten
    spalten = max(len(z["values"]) for z in daten["actions"])

    for spalte in range(spalten):
        treffer = sum(1 for zeile in daten["actions"] if zeile["values"][spalte] == "X")
        assert treffer == 1, f"Regel R{spalte + 1} hat {treffer} Aktionen"


@pytest.mark.parametrize("dateiname", sorted(ABNAHME))
def test_abnahmediagramm_hat_keine_layout_hinweise(dateiname: str) -> None:
    """Was der Editor selbst bemängeln würde, soll in der mitgelieferten
    Vorlage nicht stehen."""
    daten = Diagramm.laden(DIAGRAMME / dateiname).daten

    assert pruefen(daten) == []
