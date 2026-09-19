"""Formen-Katalog je Diagrammtyp (Abschnitt 13.4).

Beschreibt nur, *was* es gibt (Name, Beschriftung, Startgröße) – das
*Zeichnen* steht in `ide/diagramm/zeichnen.py`, die Bedienung in
`ide/diagramm/canvas.py`.

Alle Formen-Diagramme teilen sich dieselbe Zeichenfläche und dieselbe
Verbindungs-Maschinerie; ein neuer Diagrammtyp ist deshalb im
Wesentlichen ein Eintrag in `FORMEN_JE_TYP` und `VERBINDUNGEN_JE_TYP`
plus seine Darstellung in `zeichnen.py`.
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
    #: Vorbelegter Name, sobald die Form platziert wird. Attribute und
    #: Operationen bleiben leer – sie kommen über den Eigenschaften-
    #: Dialog dazu (M9 Schritt 12).
    standardname: str


#: Mindestgröße jeder Form – verhindert, dass beim späteren
#: Größenziehen (Schritt 3) Text abgeschnitten wird (Abschnitt 13.6:
#: „automatische Mindestgröße, damit Text nie abgeschnitten wird“).
MINDESTGROESSE = (72, 40)

#: Formen und Verbindungen, die in mehreren Diagrammarten vorkommen –
#: **ein** Objekt, nicht zwei gleich aussehende: `form_art()` sucht über
#: `kind`, und zwei Einträge mit derselben Kennung würden sich sonst
#: gegenseitig überschreiben, ohne dass es auffällt.
NOTIZ = FormArt(
    kind="note",
    beschriftung="Notiz",
    beschreibung="Freitext-Notiz mit umgeknickter Ecke",
    breite=160,
    hoehe=80,
    standardname="Notiz",
)

KLASSENDIAGRAMM_FORMEN: tuple[FormArt, ...] = (
    FormArt(
        kind="class",
        beschriftung="Klasse",
        beschreibung="Klasse mit Name, Attributen und Methoden",
        breite=184,
        hoehe=128,
        standardname="Klasse",
    ),
    FormArt(
        kind="abstract_class",
        beschriftung="Abstrakte Klasse",
        beschreibung="Klasse mit {abstract}, Name kursiv",
        breite=184,
        hoehe=128,
        standardname="AbstrakteKlasse",
    ),
    FormArt(
        kind="interface",
        beschriftung="Interface",
        beschreibung="Schnittstelle mit «interface»",
        breite=184,
        hoehe=104,
        standardname="Interface",
    ),
    NOTIZ,
    FormArt(
        kind="package",
        beschriftung="Paket",
        beschreibung="Paket mit Reiter oben links",
        breite=176,
        hoehe=112,
        standardname="Paket",
    ),
)

@dataclass(frozen=True)
class VerbindungsArt:
    """Eine Verbindungsart, wie sie in der Palette steht
    (Abschnitt 13.4). `spitze_am_ziel`/`raute_an_quelle` beschreiben die
    UML-Notation, `gestrichelt` die Linienart."""

    kind: str
    beschriftung: str
    beschreibung: str
    gestrichelt: bool = False
    #: "keine" | "offen" (Pfeil) | "dreieck" (leeres Dreieck)
    spitze_am_ziel: str = "keine"
    #: "keine" | "leer" (Aggregation ◇) | "gefuellt" (Komposition ◆)
    raute_an_quelle: str = "keine"
    #: Text, der ohne Zutun in der Mitte der Linie steht – bei
    #: «include»/«extend» gehört er zur Notation und nicht zur
    #: Beschriftung, die die Bedienerin selbst setzt.
    stereotyp: str = ""


ASSOZIATION = VerbindungsArt(
    kind="association",
    beschriftung="Assoziation",
    beschreibung="einfache Verbindung ohne Richtung",
)

KLASSENDIAGRAMM_VERBINDUNGEN: tuple[VerbindungsArt, ...] = (
    ASSOZIATION,
    VerbindungsArt(
        kind="directed_association",
        beschriftung="Gerichtete Assoziation",
        beschreibung="Assoziation mit offener Pfeilspitze",
        spitze_am_ziel="offen",
    ),
    VerbindungsArt(
        kind="aggregation",
        beschriftung="Aggregation",
        beschreibung="leere Raute an der Ganzes-Seite",
        raute_an_quelle="leer",
    ),
    VerbindungsArt(
        kind="composition",
        beschriftung="Komposition",
        beschreibung="gefüllte Raute an der Ganzes-Seite",
        raute_an_quelle="gefuellt",
    ),
    VerbindungsArt(
        kind="inheritance",
        beschriftung="Vererbung",
        beschreibung="leeres Dreieck an der Oberklasse",
        spitze_am_ziel="dreieck",
    ),
    VerbindungsArt(
        kind="dependency",
        beschriftung="Abhängigkeit",
        beschreibung="gestrichelt mit offener Pfeilspitze",
        gestrichelt=True,
        spitze_am_ziel="offen",
    ),
    VerbindungsArt(
        kind="realization",
        beschriftung="Realisierung",
        beschreibung="gestrichelt mit leerem Dreieck",
        gestrichelt=True,
        spitze_am_ziel="dreieck",
    ),
)

USE_CASE_FORMEN: tuple[FormArt, ...] = (
    FormArt(
        kind="actor",
        beschriftung="Akteur",
        beschreibung="Strichmännchen mit Namen darunter",
        breite=80,
        hoehe=104,
        standardname="Akteur",
    ),
    FormArt(
        kind="use_case",
        beschriftung="Anwendungsfall",
        beschreibung="Ellipse mit dem Namen des Falls",
        breite=176,
        hoehe=72,
        standardname="Anwendungsfall",
    ),
    FormArt(
        kind="system_boundary",
        beschriftung="Systemgrenze",
        beschreibung="Rahmen um die Fälle, Name oben",
        breite=360,
        hoehe=280,
        standardname="System",
    ),
    NOTIZ,
)

USE_CASE_VERBINDUNGEN: tuple[VerbindungsArt, ...] = (
    ASSOZIATION,
    VerbindungsArt(
        kind="include",
        beschriftung="«include»",
        beschreibung="der Fall benutzt einen anderen immer",
        gestrichelt=True,
        spitze_am_ziel="offen",
        stereotyp="include",
    ),
    VerbindungsArt(
        kind="extend",
        beschriftung="«extend»",
        beschreibung="der Fall erweitert einen anderen manchmal",
        gestrichelt=True,
        spitze_am_ziel="offen",
        stereotyp="extend",
    ),
    VerbindungsArt(
        kind="generalization",
        beschriftung="Generalisierung",
        beschreibung="leeres Dreieck am allgemeineren Element",
        spitze_am_ziel="dreieck",
    ),
)

ZUSTANDSDIAGRAMM_FORMEN: tuple[FormArt, ...] = (
    FormArt(
        kind="initial_state",
        beschriftung="Startzustand",
        beschreibung="ausgefüllter Kreis, wo der Ablauf beginnt",
        breite=32,
        hoehe=32,
        standardname="",
    ),
    FormArt(
        kind="state",
        beschriftung="Zustand",
        beschreibung="abgerundetes Rechteck; weitere Zeilen sind entry/do/exit",
        breite=176,
        hoehe=72,
        standardname="Zustand",
    ),
    FormArt(
        kind="composite_state",
        beschriftung="Zusammengesetzter Zustand",
        beschreibung="Zustand, der weitere Zustände enthält",
        breite=360,
        hoehe=240,
        standardname="Oberzustand",
    ),
    FormArt(
        kind="decision",
        beschriftung="Entscheidung",
        beschreibung="Raute, an der sich der Ablauf teilt",
        breite=96,
        hoehe=72,
        standardname="",
    ),
    FormArt(
        kind="final_state",
        beschriftung="Endzustand",
        beschreibung="Ring mit ausgefülltem Kern",
        breite=36,
        hoehe=36,
        standardname="",
    ),
    NOTIZ,
)

ZUSTANDSDIAGRAMM_VERBINDUNGEN: tuple[VerbindungsArt, ...] = (
    VerbindungsArt(
        kind="transition",
        beschriftung="Übergang",
        beschreibung="Pfeil mit „Ereignis [Bedingung] / Aktion“ in der Mitte",
        spitze_am_ziel="offen",
    ),
)

#: Diagrammtyp -> Formen der Palette (Abschnitt 13.2: Gruppen je
#: Diagrammtyp).
FORMEN_JE_TYP: dict[str, tuple[FormArt, ...]] = {
    "class": KLASSENDIAGRAMM_FORMEN,
    "use_case": USE_CASE_FORMEN,
    "state": ZUSTANDSDIAGRAMM_FORMEN,
}

#: Diagrammtyp -> Verbindungsarten der Palette.
VERBINDUNGEN_JE_TYP: dict[str, tuple[VerbindungsArt, ...]] = {
    "class": KLASSENDIAGRAMM_VERBINDUNGEN,
    "use_case": USE_CASE_VERBINDUNGEN,
    "state": ZUSTANDSDIAGRAMM_VERBINDUNGEN,
}

_NACH_KIND = {form.kind: form for formen in FORMEN_JE_TYP.values() for form in formen}
_VERBINDUNG_NACH_KIND = {
    art.kind: art for arten in VERBINDUNGEN_JE_TYP.values() for art in arten
}


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


def verbindungen_fuer(diagrammtyp: str) -> tuple[VerbindungsArt, ...]:
    """Die Verbindungsarten der Palette für `diagrammtyp`."""
    return VERBINDUNGEN_JE_TYP.get(diagrammtyp, ())


def verbindungs_art(kind: str) -> VerbindungsArt:
    """Die `VerbindungsArt` zu einem `connector["kind"]` aus der
    `.pdiag`."""
    if kind not in _VERBINDUNG_NACH_KIND:
        raise ValueError(f"Unbekannte Verbindungsart {kind!r}.")
    return _VERBINDUNG_NACH_KIND[kind]


def ist_verbindungsart(kind: str) -> bool:
    return kind in _VERBINDUNG_NACH_KIND
