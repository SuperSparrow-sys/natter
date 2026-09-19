"""Layout-Hinweise für Diagramme (Abschnitt 13.6, sinngemäß
Abschnitt 14).

Dasselbe Versprechen wie beim Design-Prüfer der Formulare
(`ide/lint/regeln.py`): **Hinweise, keine Fehler** – nichts wird
blockiert, nichts automatisch geändert, und die Prüfung lässt sich
abschalten. Geprüft wird ausschließlich die *Darstellung*, nie der
Inhalt: ob eine Klasse `TAmpel` heißen sollte oder ob eine Vererbung
fachlich sinnvoll ist, geht den Editor nichts an (Abschnitt 13.4).

Gearbeitet wird auf dem rohen `.pdiag`-`dict`, nicht auf der
Zeichenfläche – die Prüfung braucht also kein geöffnetes Fenster und
ist einzeln testbar.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ide.diagramm.seite import satzspiegel
from ide.diagramm.uml_modell import formname
from ide.diagramm.zeichnen import mindestbreite, mindesthoehe

#: Wie weit sich zwei Formen überlappen dürfen, bevor es gemeldet wird.
#: Eine Form, die eine andere nur um wenige Pixel touchiert, ist meist
#: Absicht (z. B. ein bewusst angelegtes Paket).
UEBERLAPPUNG_TOLERANZ = 4.0


@dataclass(frozen=True)
class Hinweis:
    regel: str
    meldung: str
    #: `id`s aller betroffenen Formen bzw. Verbindungen, für das
    #: Hervorheben auf der Zeichenfläche. Eine Überlappung betrifft
    #: immer **beide** Formen – würde nur die erste markiert, wäre nicht
    #: zu sehen, womit sie sich überlappt (im Screenshot aufgefallen).
    elemente: tuple[str, ...] = ()
    #: Was man tun kann. Jeder Hinweis hat einen solchen Teil (M11,
    #: Abschnitt 4: „jede Meldung mit Lösungen“) – ein Hinweis, der nur
    #: sagt, dass etwas nicht stimmt, hilft niemandem beim Aufräumen
    #: eines Diagramms. `meldung` endet immer damit, damit die
    #: Statusleiste und der Tooltip des Diagrammfensters nichts
    #: zusammensetzen müssen und der Prüfungsmodus (M11, Abschnitt 6)
    #: den Teil an einer einzigen Stelle abschneiden kann.
    loesung: str = ""


def _hinweis(regel: str, was: str, elemente: tuple[str, ...], loesung: str) -> Hinweis:
    """Baut einen `Hinweis`, dessen `meldung` mit dem Lösungsteil endet."""
    return Hinweis(regel, f"{was} {loesung}", elemente, loesung)


def _rechteck(shape: dict[str, Any]) -> tuple[float, float, float, float]:
    return float(shape["x"]), float(shape["y"]), float(shape["w"]), float(shape["h"])


def _beschriftung(shape: dict[str, Any]) -> str:
    """Wie die Form in einer Meldung heißt.

    Nur die **erste** Zeile: der Name eines Zustands trägt darunter noch
    seine Aktionen, und eine dreizeilige Meldung in der Liste war
    unlesbar (in der Sichtprüfung aufgefallen).
    """
    name = formname(shape).splitlines()
    return (name[0].strip() if name else "") or str(shape.get("kind", "Form"))


#: Formen, die andere Formen **umschließen sollen**. Eine Systemgrenze
#: voller Anwendungsfälle ist kein Layout-Fehler, sondern genau ihr
#: Zweck; ein Paket kann ebenso Klassen enthalten.
BEHAELTERFORMEN = (
    "system_boundary",
    "package",
    "composite_state",
    "swimlane",
    "fragment",
    "lifeline",
)


def _umschliesst(aussen: dict[str, Any], innen: dict[str, Any]) -> bool:
    """Ob `innen` vollständig in `aussen` liegt."""
    ax, ay, aw, ah = _rechteck(aussen)
    bx, by, bw, bh = _rechteck(innen)
    return ax <= bx and ay <= by and bx + bw <= ax + aw and by + bh <= ay + ah


def _ueberschneidung(a: dict[str, Any], b: dict[str, Any]) -> float:
    """Fläche, die sich beide Formen teilen – 0, wenn sie sich nicht
    berühren.

    Ein Behälter, der die andere Form ganz enthält, zählt nicht: eine
    Systemgrenze voller Anwendungsfälle wurde sonst als Überlappung
    gemeldet, und ein Use-Case-Diagramm hatte von Anfang an so viele
    Warnungen wie Fälle (in der Sichtprüfung aufgefallen). Ein Behälter,
    der eine Form nur **anschneidet**, wird weiterhin gemeldet – das ist
    dann wirklich ein Versehen.
    """
    if a.get("kind") in BEHAELTERFORMEN and _umschliesst(a, b):
        return 0.0
    if b.get("kind") in BEHAELTERFORMEN and _umschliesst(b, a):
        return 0.0

    ax, ay, aw, ah = _rechteck(a)
    bx, by, bw, bh = _rechteck(b)
    breite = min(ax + aw, bx + bw) - max(ax, bx)
    hoehe = min(ay + ah, by + bh) - max(ay, by)
    if breite <= UEBERLAPPUNG_TOLERANZ or hoehe <= UEBERLAPPUNG_TOLERANZ:
        return 0.0
    return breite * hoehe


def ueberlappende_formen(daten: dict[str, Any]) -> list[Hinweis]:
    """Zwei Formen liegen übereinander – im Ausdruck ist dann eine von
    beiden nicht mehr vollständig lesbar."""
    formen = daten.get("shapes") or []
    hinweise: list[Hinweis] = []
    for i, erste in enumerate(formen):
        for zweite in formen[i + 1 :]:
            if _ueberschneidung(erste, zweite):
                hinweise.append(
                    _hinweis(
                        "ueberlappung",
                        f"„{_beschriftung(erste)}“ und „{_beschriftung(zweite)}“ "
                        f"überlappen sich.",
                        (erste["id"], zweite["id"]),
                        "Eine der beiden zur Seite ziehen oder das Diagramm neu "
                        "anordnen lassen - im Ausdruck ist sonst eine von beiden "
                        "verdeckt.",
                    )
                )
    return hinweise


def abgeschnittener_text(daten: dict[str, Any]) -> list[Hinweis]:
    """Die Form ist zu klein für ihren eigenen Text. Die Höhe wird beim
    Bearbeiten automatisch nachgezogen, die Breite bewusst nicht –
    deshalb ist das hier meist ein zu schmaler Kasten."""
    hinweise = []
    for form in daten.get("shapes") or []:
        _, _, breite, hoehe = _rechteck(form)
        if breite + 0.5 < mindestbreite(form):
            hinweise.append(
                _hinweis(
                    "abgeschnittener_text",
                    f"„{_beschriftung(form)}“ ist zu schmal, der Text wird "
                    f"abgeschnitten.",
                    (form["id"],),
                    "Die Form am rechten Anfasser breiter ziehen oder die "
                    "Beschriftung kürzer fassen.",
                )
            )
        elif hoehe + 0.5 < mindesthoehe(form):
            hinweise.append(
                _hinweis(
                    "abgeschnittener_text",
                    f"„{_beschriftung(form)}“ ist zu niedrig, die letzten Zeilen "
                    f"werden abgeschnitten.",
                    (form["id"],),
                    "Die Form am unteren Anfasser höher ziehen oder Zeilen aus "
                    "der Beschriftung herausnehmen.",
                )
            )
    return hinweise


def lose_verbindungsenden(daten: dict[str, Any]) -> list[Hinweis]:
    """Eine Verbindung zeigt auf eine Form, die es nicht (mehr) gibt.
    Beim Löschen räumt der Editor das selbst auf – in einer von Hand
    bearbeiteten oder importierten Datei kann es trotzdem vorkommen."""
    vorhanden = {form["id"] for form in daten.get("shapes") or []}
    hinweise = []
    for verbindung in daten.get("connectors") or []:
        for ende in ("from", "to"):
            if verbindung.get(ende) not in vorhanden:
                hinweise.append(
                    _hinweis(
                        "loses_ende",
                        f"Verbindung „{verbindung.get('kind', '?')}“ hängt an keiner "
                        f"Form ({'Quelle' if ende == 'from' else 'Ziel'}).",
                        (verbindung["id"],),
                        "Das lose Ende auf eine Form ziehen oder die Verbindung "
                        "löschen - so gezeichnet ergibt sie keinen Sinn.",
                    )
                )
    return hinweise


def ausserhalb_der_seite(daten: dict[str, Any]) -> list[Hinweis]:
    """Die Form liegt ganz oder teilweise außerhalb des bedruckbaren
    Bereichs und fehlt deshalb im PDF-Export und im Ausdruck."""
    links, oben, breite, hoehe = satzspiegel(daten.get("page") or {})
    hinweise = []
    for form in daten.get("shapes") or []:
        x, y, w, h = _rechteck(form)
        if x < links or y < oben or x + w > links + breite or y + h > oben + hoehe:
            hinweise.append(
                _hinweis(
                    "ausserhalb_der_seite",
                    f"„{_beschriftung(form)}“ liegt außerhalb des Seitenbereichs "
                    f"und fehlt im Ausdruck.",
                    (form["id"],),
                    "Die Form in den Seitenbereich schieben oder unter "
                    "„Seite einrichten“ ein größeres Format bzw. Querformat "
                    "wählen.",
                )
            )
    return hinweise


#: Alle Regeln in der Reihenfolge, in der sie gemeldet werden.
REGELN = (
    ueberlappende_formen,
    abgeschnittener_text,
    lose_verbindungsenden,
    ausserhalb_der_seite,
)


def pruefen(daten: dict[str, Any]) -> list[Hinweis]:
    """Alle Layout-Regeln auf ein `.pdiag`-`dict` anwenden."""
    return [hinweis for regel in REGELN for hinweis in regel(daten)]
