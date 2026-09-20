"""„Als Tabelle anzeigen“ im Variablen-Panel des Debuggers (Abschnitt
11.6, docs/arbeitspakete/M5.md „Zurückgestellt“).

Die Variablenansicht zeigt bisher nur den `repr` einer Variablen. Für
`DataFrame`s, Listen und Dictionaries ist das unbrauchbar: lange Zeilen,
von `debugpy` gekürzt, keine Spaltenstruktur. Dieses Modul wandelt einen
solchen Wert in eine Tabelle (Spaltennamen + Zeilen) um.

Wie der Wert aus dem angehaltenen Programm kommt: nicht über
`repr`-Text und auch nicht über einen zweiten `variables`-Aufruf pro
Zelle (das wären bei 200 Zeilen hunderte DAP-Anfragen), sondern über
einen einzigen `evaluate`-Aufruf. Dessen Ausdruck trägt die
Umwandlungsfunktion als Quelltext mit und liefert das Ergebnis als JSON
zurück. Damit gibt es genau eine Fassung der Umwandlungsregeln:
`_KONVERTER_QUELLTEXT`. Sie läuft in der IDE (`tabelle_aus_wert`, direkt
testbar) und im Schülerprozess (über `tabellen_ausdruck`) Zeile für
Zeile gleich.

Die Funktion im Quelltext darf deshalb nichts importieren, was ein
Schülerprogramm nicht ohnehin hat – sie erkennt `pandas`-Objekte an
ihren Attributen (`columns`/`itertuples`) statt `pandas` zu importieren.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

#: Was sich anzeigen lässt - als Lösungsteil an jeder Meldung, die
#: sagt, dass es gerade nicht geht. „Geht nicht“ allein lässt jemanden
#: raten, welcher Wert denn dann gemeint war.
GEEIGNETE_WERTE = (
    "Als Tabelle anzeigen lassen sich eine Liste von Listen, eine Liste "
    "von Dictionaries, ein Dictionary, das Ergebnis einer "
    "Datenbankabfrage und ein DataFrame."
)

#: Voreinstellung: so viele Zeilen werden höchstens übertragen. Ein
#: Datensatz mit 100 000 Zeilen soll die IDE nicht blockieren.
MAX_ZEILEN = 200

#: Längster Text je Zelle. Schützt gegen einzelne, sehr lange Werte.
MAX_ZELLENTEXT = 300

_KONVERTER_QUELLTEXT = '''
def natter_tabelle(wert, max_zeilen, max_zellentext):
    """Wandelt `wert` in {"spalten", "zeilen", "gesamt", "art"} um.
    Liefert None, wenn der Wert keine sinnvolle Tabelle ergibt."""

    def text(einzelwert):
        if einzelwert is None:
            return ""
        try:
            gewandelt = str(einzelwert)
        except Exception:
            gewandelt = "<nicht darstellbar>"
        if len(gewandelt) > max_zellentext:
            return gewandelt[:max_zellentext] + " …"
        return gewandelt

    def fertig(spalten, zeilen, gesamt, art):
        return {
            "spalten": [text(spalte) for spalte in spalten],
            "zeilen": [[text(zelle) for zelle in zeile] for zeile in zeilen],
            "gesamt": gesamt,
            "art": art,
        }

    # pandas DataFrame - an den Attributen erkannt, nicht per import
    if hasattr(wert, "columns") and hasattr(wert, "itertuples"):
        spalten = ["index"] + [text(spalte) for spalte in wert.columns]
        ausschnitt = wert.head(max_zeilen) if hasattr(wert, "head") else wert
        zeilen = [list(zeile) for zeile in ausschnitt.itertuples(index=True, name=None)]
        return fertig(spalten, zeilen, len(wert), "DataFrame")

    # pandas Series
    if hasattr(wert, "index") and hasattr(wert, "items") and hasattr(wert, "dtype"):
        paare = list(wert.items())
        return fertig(["index", "Wert"], paare[:max_zeilen], len(paare), "Series")

    if isinstance(wert, dict):
        werte = list(wert.values())
        spaltenweise = (
            bool(werte)
            and all(isinstance(spalte, (list, tuple)) for spalte in werte)
            and len({len(spalte) for spalte in werte}) == 1
        )
        if spaltenweise:
            hoehe = len(werte[0])
            zeilen = [
                [spalte[nummer] for spalte in werte] for nummer in range(min(hoehe, max_zeilen))
            ]
            return fertig(list(wert.keys()), zeilen, hoehe, "Dictionary (spaltenweise)")
        paare = list(wert.items())
        return fertig(
            ["Schlüssel", "Wert"], paare[:max_zeilen], len(paare), "Dictionary"
        )

    if isinstance(wert, (list, tuple, set, frozenset)):
        eintraege = list(wert)
        ausschnitt = eintraege[:max_zeilen]
        if eintraege and all(isinstance(eintrag, dict) for eintrag in eintraege):
            spalten = []
            for eintrag in eintraege:
                for schluessel in eintrag:
                    if schluessel not in spalten:
                        spalten.append(schluessel)
            zeilen = [
                [eintrag.get(spalte) for spalte in spalten] for eintrag in ausschnitt
            ]
            return fertig(spalten, zeilen, len(eintraege), "Liste von Dictionaries")
        if eintraege and all(isinstance(eintrag, (list, tuple)) for eintrag in eintraege):
            breite = max(len(eintrag) for eintrag in eintraege)
            spalten = [str(nummer) for nummer in range(breite)]
            zeilen = [
                list(eintrag) + [None] * (breite - len(eintrag)) for eintrag in ausschnitt
            ]
            return fertig(spalten, zeilen, len(eintraege), "Liste von Listen")
        zeilen = [[nummer, eintrag] for nummer, eintrag in enumerate(ausschnitt)]
        return fertig(["#", "Wert"], zeilen, len(eintraege), "Liste")

    return None
'''

_KONVERTER_RAUM: dict[str, Any] = {}
exec(compile(_KONVERTER_QUELLTEXT, "<natter-tabelle>", "exec"), _KONVERTER_RAUM)


class TabellenFehler(ValueError):
    """Der Wert lässt sich nicht als Tabelle darstellen."""


@dataclass
class Tabelle:
    """Das Ergebnis einer Umwandlung, fertig für `QTableWidget`."""

    spalten: list[str] = field(default_factory=list)
    zeilen: list[list[str]] = field(default_factory=list)
    #: Gesamtzahl der Datensätze im Original (kann größer als
    #: `len(zeilen)` sein, wenn gekürzt wurde).
    gesamt: int = 0
    #: Menschenlesbare Art des Werts, z. B. "DataFrame".
    art: str = ""

    @property
    def gekuerzt(self) -> bool:
        return self.gesamt > len(self.zeilen)


def tabelle_aus_wert(
    wert: Any, max_zeilen: int = MAX_ZEILEN, max_zellentext: int = MAX_ZELLENTEXT
) -> Tabelle:
    """Wandelt einen Python-Wert direkt (in der IDE) in eine `Tabelle`
    um – dieselben Regeln, die `tabellen_ausdruck()` im angehaltenen
    Schülerprogramm ausführen lässt."""
    ergebnis = _KONVERTER_RAUM["natter_tabelle"](wert, max_zeilen, max_zellentext)
    if ergebnis is None:
        raise TabellenFehler(
            f"Ein Wert vom Typ {type(wert).__name__} lässt sich nicht als "
            f"Tabelle anzeigen. {GEEIGNETE_WERTE}"
        )
    return _tabelle_aus_dict(ergebnis)


def _tabelle_aus_dict(ergebnis: dict[str, Any]) -> Tabelle:
    return Tabelle(
        spalten=list(ergebnis["spalten"]),
        zeilen=[list(zeile) for zeile in ergebnis["zeilen"]],
        gesamt=int(ergebnis["gesamt"]),
        art=str(ergebnis["art"]),
    )


def tabellen_ausdruck(
    ausdruck: str, max_zeilen: int = MAX_ZEILEN, max_zellentext: int = MAX_ZELLENTEXT
) -> str:
    """Der Python-Ausdruck für DAP `evaluate`, der `ausdruck` im
    angehaltenen Programm auswertet und das Ergebnis als JSON-Text
    zurückgibt.

    Ein einzelner Ausdruck, kein Statement: `exec(…)` liefert `None`, das
    Tupel `(exec(...), aufruf)[1]` gibt trotzdem den Rückgabewert des
    Aufrufs zurück. `exec` bekommt einen eigenen, leeren Namensraum –
    der Namensraum des Schülerprogramms bleibt unangetastet."""
    quelltext = json.dumps(_KONVERTER_QUELLTEXT)
    return (
        "(lambda _natter_raum: __import__('json').dumps("
        f"(exec({quelltext}, _natter_raum), "
        f"_natter_raum['natter_tabelle']({ausdruck}, {max_zeilen}, {max_zellentext})"
        ")[1], default=str))({})"
    )


def tabelle_aus_antwort(antwort: str) -> Tabelle:
    """Wertet die Antwort von DAP `evaluate` auf `tabellen_ausdruck()`
    aus. `debugpy` liefert den `repr` des Rückgabewerts, also einen
    Python-String in Anführungszeichen – die werden hier entfernt,
    bevor der JSON-Text gelesen wird."""
    text = antwort.strip()
    if len(text) >= 2 and text[0] in "'\"" and text[-1] == text[0]:
        import ast

        text = ast.literal_eval(text)
    if text == "null":
        raise TabellenFehler(
            f"Dieser Wert lässt sich nicht als Tabelle anzeigen. {GEEIGNETE_WERTE}"
        )
    try:
        ergebnis = json.loads(text)
    except json.JSONDecodeError as fehler:
        # Der rohe Antworttext bleibt stehen - er ist das Einzige, was
        # hier weiterhilft, wenn es doch einmal passiert. Davor steht
        # jetzt, was zu tun ist.
        raise TabellenFehler(
            "Der Debugger hat auf diese Anfrage anders geantwortet als "
            "erwartet. Das Programm über „Start → Stopp“ beenden und noch "
            "einmal mit dem Debugger starten. Antwort des Debuggers: "
            f"{antwort}"
        ) from fehler
    if ergebnis is None:
        raise TabellenFehler(
            f"Dieser Wert lässt sich nicht als Tabelle anzeigen. {GEEIGNETE_WERTE}"
        )
    return _tabelle_aus_dict(ergebnis)
