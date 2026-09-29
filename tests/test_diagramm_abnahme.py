"""Abnahme von M9 (Schritt 11): die drei Diagramme des
Abnahmekriteriums aus `beispielprojekte/06_Kontoverwaltung/diagramme/`
laden und als PDF exportieren.

Das Abnahmekriterium verlangt je ein Klassendiagramm, ein Struktogramm
und eine Entscheidungstabelle, von Hand erstellt und als PDF
exportiert. Bis M14 hingen sie am Beispielprojekt „Ampel"; seit der
Lehrgang steht, gehören sie zur Kontoverwaltung - dort ist die eigene
Klasse das Thema der Stufe, und ein Klassendiagramm gehört genau
dorthin.

Die Dateien werden hier nur gelesen; exportiert wird nach
`tmp_path`, damit im Beispielprojekt nichts verändert wird (AGENTS.md).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ide.diagramm.datei import Diagramm
from ide.diagramm.export import als_pdf, als_png
from ide.diagramm.hinweise import pruefen

DIAGRAMME = (
    Path(__file__).resolve().parent.parent
    / "beispielprojekte"
    / "06_Kontoverwaltung"
    / "diagramme"
)

ABNAHME = {
    "konto_klassen.pdiag": "class",
    "konto_abheben.pdiag": "struktogramm",
    "konto_entscheidung.pdiag": "entscheidungstabelle",
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


def test_klassendiagramm_bildet_die_echte_klasse_ab() -> None:
    """Inhaltliche Probe: die Methoden im Diagramm müssen zu
    `beispielprojekte/06_Kontoverwaltung/u_konto.py` passen."""
    daten = Diagramm.laden(DIAGRAMME / "konto_klassen.pdiag").daten
    konto = next(f for f in daten["shapes"] if f.get("name") == "Konto")

    methoden = " ".join(o["name"] for o in konto["operations"])
    for name in ("__init__", "einzahlen", "abheben"):
        assert name in methoden


def test_struktogramm_bildet_das_abheben_ab() -> None:
    """Zwei geschachtelte Verzweigungen - genau die beiden Regeln, die
    `Konto.abheben` prüft: Betrag über null, und genug Geld da."""
    from ide.diagramm.bloecke import alle_bloecke

    daten = Diagramm.laden(DIAGRAMME / "konto_abheben.pdiag").daten
    verzweigungen = [b for b in alle_bloecke(daten) if b.get("kind") == "branch"]

    assert len(verzweigungen) == 2
    texte = " ".join(b["text"] for b in verzweigungen)
    assert "null" in texte
    assert "Kontostand" in texte


def test_entscheidungstabelle_hat_zu_jeder_regel_eine_aktion() -> None:
    """Fachliche Probe: in jeder Regel-Spalte muss genau ein `X`
    stehen – sonst wäre die Buchung in dieser Lage undefiniert."""
    daten = Diagramm.laden(DIAGRAMME / "konto_entscheidung.pdiag").daten
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
