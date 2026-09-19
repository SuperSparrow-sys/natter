"""Neue `.pdiag`-Datei anlegen (Abschnitt 13.2, „Datei → Neu“).

Jeder Diagrammtyp startet mit dem kleinsten gültigen Inhalt, den das
Schema verlangt – Formen-Diagramme mit leeren `shapes`/`connectors`,
ein Struktogramm mit leerem Wurzelblock, eine Entscheidungstabelle mit
je einer leeren Bedingungs- und Aktionszeile und einer Regel-Spalte
(eine völlig leere Tabelle hätte keine sichtbare Struktur zum
Weiterarbeiten).
"""

from __future__ import annotations

from pathlib import Path

from ide.diagramm.datei import FORMEN_TYPEN, Diagramm

#: Typen, die „Datei → Neu“ anbietet. Die ersten drei stammen aus dem
#: M9-Abnahmekriterium, die übrigen aus Abschnitt 13.4.
MVP_TYPEN = (
    "class",
    "struktogramm",
    "entscheidungstabelle",
    "use_case",
    "state",
)

TYP_BESCHRIFTUNGEN = {
    "class": "Klassendiagramm",
    "struktogramm": "Struktogramm",
    "entscheidungstabelle": "Entscheidungstabelle",
    "use_case": "Use-Case-Diagramm",
    "activity": "Aktivitätsdiagramm",
    "state": "Zustandsdiagramm",
    "sequence": "Sequenzdiagramm",
}

_STANDARD_SEITE = {"size": "A4", "orientation": "landscape"}
_STANDARD_STIL = "modern-light"


def leeres_diagramm(typ: str, name: str) -> dict:
    """Kleinster gültiger `.pdiag`-Inhalt für `typ`."""
    if typ not in TYP_BESCHRIFTUNGEN:
        raise ValueError(f"Unbekannter Diagrammtyp {typ!r}.")

    daten: dict = {
        "format": "pdiag/1",
        "type": typ,
        "name": name,
        "page": dict(_STANDARD_SEITE),
        "style": _STANDARD_STIL,
    }
    if typ in FORMEN_TYPEN:
        daten["shapes"] = []
        daten["connectors"] = []
    elif typ == "struktogramm":
        # Hochformat: Struktogramme wachsen nach unten, nicht zur Seite.
        daten["page"]["orientation"] = "portrait"
        daten["root"] = {"id": "root", "kind": "sequence", "children": []}
    elif typ == "entscheidungstabelle":
        daten["conditions"] = [{"text": "", "values": [""]}]
        daten["actions"] = [{"text": "", "values": [""]}]
    return daten


def diagramm_erzeugen(typ: str, pfad: Path, name: str | None = None) -> Diagramm:
    """Legt `pfad` mit einem leeren Diagramm vom Typ `typ` an und lädt
    es. Ein vorhandener Pfad wird nicht überschrieben."""
    pfad = Path(pfad)
    if pfad.exists():
        raise FileExistsError(f"{pfad} gibt es schon.")

    diagramm = Diagramm(pfad=pfad, daten=leeres_diagramm(typ, name or pfad.stem))
    diagramm.speichern()
    return diagramm
