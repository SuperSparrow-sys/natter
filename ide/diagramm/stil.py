"""Stilvorlagen für Diagramme (Abschnitt 13.6).

Drei umschaltbare Vorlagen, die für das *ganze* Diagramm gelten und
unabhängig vom IDE-Theme sind: der Export nimmt immer die im Diagramm
gewählte Vorlage, damit ein im dunklen Theme gezeichnetes Diagramm
trotzdem als Schwarz-Weiß-Abgabe gedruckt werden kann.

Farben sind an `design/tokens.json` angelehnt (gleiche Akzentfarbe wie
die IDE), aber bewusst eigene Werte: Diagrammflächen brauchen
gedecktere Füllungen als IDE-Oberflächen, und „Schwarz-Weiß“ hat in
den Tokens keine Entsprechung.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Stil:
    name: str
    hintergrund: str
    raster: str
    #: Füllung/Rand/Text der Formen
    fuellung: str
    rand: str
    text: str
    #: Trennlinien innerhalb einer Form (z. B. Klasse: Name/Attribute)
    trennlinie: str
    #: Hinterlegung von Kopfzeilen (Entscheidungstabelle). Bewusst
    #: getrennt von `trennlinie`: in der Schwarz-Weiß-Vorlage ist die
    #: Trennlinie schwarz, eine damit gefüllte Kopfzeile verschluckte den
    #: schwarzen Text darauf vollständig (im PDF aufgefallen).
    kopf: str
    #: Verbindungen (Schritt 4)
    linie: str
    #: Auswahlrahmen und Anfasser
    akzent: str


MODERN_HELL = Stil(
    name="modern-light",
    hintergrund="#ffffff",
    raster="#e4e4e4",
    fuellung="#f7f9fb",
    rand="#5c6b7a",
    text="#1a1a1a",
    trennlinie="#c3cdd6",
    kopf="#e8edf2",
    linie="#3d4c5a",
    akzent="#0067c0",
)

MODERN_DUNKEL = Stil(
    name="modern-dark",
    hintergrund="#1e1e1e",
    raster="#2f2f2f",
    fuellung="#2b3138",
    rand="#8da2b5",
    text="#e8e8e8",
    trennlinie="#48545f",
    kopf="#38414a",
    linie="#a8b8c6",
    akzent="#4cc2ff",
)

SCHWARZ_WEISS = Stil(
    name="black-white",
    hintergrund="#ffffff",
    raster="#e8e8e8",
    fuellung="#ffffff",
    rand="#000000",
    text="#000000",
    trennlinie="#000000",
    kopf="#ffffff",
    linie="#000000",
    akzent="#000000",
)

_STILE = {stil.name: stil for stil in (MODERN_HELL, MODERN_DUNKEL, SCHWARZ_WEISS)}

BESCHRIFTUNGEN = {
    "modern-light": "Modern hell",
    "modern-dark": "Modern dunkel",
    "black-white": "Schwarz-Weiß",
}


def stil(name: str) -> Stil:
    """Stilvorlage zu ihrem Namen aus der `.pdiag` (`style`)."""
    if name not in _STILE:
        raise ValueError(f"Unbekannte Stilvorlage {name!r}.")
    return _STILE[name]
