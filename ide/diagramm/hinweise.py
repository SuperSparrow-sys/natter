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


def _rechteck(shape: dict[str, Any]) -> tuple[float, float, float, float]:
    return float(shape["x"]), float(shape["y"]), float(shape["w"]), float(shape["h"])


def _beschriftung(shape: dict[str, Any]) -> str:
    return formname(shape) or str(shape.get("kind", "Form"))


def _ueberschneidung(a: dict[str, Any], b: dict[str, Any]) -> float:
    """Fläche, die sich beide Formen teilen – 0, wenn sie sich nicht
    berühren."""
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
                    Hinweis(
                        "ueberlappung",
                        f"„{_beschriftung(erste)}“ und „{_beschriftung(zweite)}“ "
                        f"überlappen sich.",
                        (erste["id"], zweite["id"]),
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
                Hinweis(
                    "abgeschnittener_text",
                    f"„{_beschriftung(form)}“ ist zu schmal, der Text wird "
                    f"abgeschnitten.",
                    (form["id"],),
                )
            )
        elif hoehe + 0.5 < mindesthoehe(form):
            hinweise.append(
                Hinweis(
                    "abgeschnittener_text",
                    f"„{_beschriftung(form)}“ ist zu niedrig, die letzten Zeilen "
                    f"werden abgeschnitten.",
                    (form["id"],),
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
                    Hinweis(
                        "loses_ende",
                        f"Verbindung „{verbindung.get('kind', '?')}“ hängt an keiner "
                        f"Form ({'Quelle' if ende == 'from' else 'Ziel'}).",
                        (verbindung["id"],),
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
                Hinweis(
                    "ausserhalb_der_seite",
                    f"„{_beschriftung(form)}“ liegt außerhalb des Seitenbereichs "
                    f"und fehlt im Ausdruck.",
                    (form["id"],),
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
