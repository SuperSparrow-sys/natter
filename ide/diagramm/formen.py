"""Formen-Katalog je Diagrammtyp (Abschnitt 13.4).

Beschreibt nur, *was* es gibt (Name, Beschriftung, Startgröße) – das
*Zeichnen* steht in `ide/diagramm/zeichnen.py`, die Bedienung in
`ide/diagramm/canvas.py`. Stand M9, Schritt 2: nur das
Klassendiagramm; die übrigen Formen-Diagramme aus Abschnitt 13.4
kommen als eigene Schritte dazu (siehe M9.md, „Danach“).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FormArt:
    """Eine Form, wie sie in der Palette steht und auf der
    Zeichenfläche entsteht."""

    kind: str
    beschriftung: str
    beschreibung: str
    breite: int
    hoehe: int
    #: Vorbelegung für `shape["text"]`, sobald die Form platziert wird.
    standardtext: dict


#: Mindestgröße jeder Form – verhindert, dass beim späteren
#: Größenziehen (Schritt 3) Text abgeschnitten wird (Abschnitt 13.6:
#: „automatische Mindestgröße, damit Text nie abgeschnitten wird“).
MINDESTGROESSE = (72, 40)

KLASSENDIAGRAMM_FORMEN: tuple[FormArt, ...] = (
    FormArt(
        kind="class",
        beschriftung="Klasse",
        beschreibung="Klasse mit Name, Attributen und Methoden",
        breite=184,
        hoehe=128,
        standardtext={"name": "Klasse", "attributes": [], "methods": []},
    ),
    FormArt(
        kind="abstract_class",
        beschriftung="Abstrakte Klasse",
        beschreibung="Klasse mit {abstract}, Name kursiv",
        breite=184,
        hoehe=128,
        standardtext={"name": "AbstrakteKlasse", "attributes": [], "methods": []},
    ),
    FormArt(
        kind="interface",
        beschriftung="Interface",
        beschreibung="Schnittstelle mit «interface»",
        breite=184,
        hoehe=104,
        standardtext={"name": "Interface", "attributes": [], "methods": []},
    ),
    FormArt(
        kind="note",
        beschriftung="Notiz",
        beschreibung="Freitext-Notiz mit umgeknickter Ecke",
        breite=160,
        hoehe=80,
        standardtext={"name": "Notiz"},
    ),
    FormArt(
        kind="package",
        beschriftung="Paket",
        beschreibung="Paket mit Reiter oben links",
        breite=176,
        hoehe=112,
        standardtext={"name": "Paket"},
    ),
)

#: Diagrammtyp -> Formen der Palette (Abschnitt 13.2: Gruppen je
#: Diagrammtyp).
FORMEN_JE_TYP: dict[str, tuple[FormArt, ...]] = {
    "class": KLASSENDIAGRAMM_FORMEN,
}

_NACH_KIND = {form.kind: form for formen in FORMEN_JE_TYP.values() for form in formen}


def formen_fuer(diagrammtyp: str) -> tuple[FormArt, ...]:
    """Die Palettenformen für `diagrammtyp`; leer, solange ein Typ noch
    keine eigenen Formen hat (Struktogramm/Entscheidungstabelle haben
    bewusst keine, sie arbeiten nicht mit frei platzierten Formen)."""
    return FORMEN_JE_TYP.get(diagrammtyp, ())


def form_art(kind: str) -> FormArt:
    """Die `FormArt` zu einem `shape["kind"]` aus der `.pdiag`."""
    if kind not in _NACH_KIND:
        raise ValueError(f"Unbekannte Formart {kind!r}.")
    return _NACH_KIND[kind]
