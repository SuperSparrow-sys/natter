"""Vorschläge für die Quelltext-Vervollständigung (M11, Abschnitt 2.2).

Gerechnet wird mit **jedi** – es versteht Python wirklich, also auch
Typen und Importe. Der Nutzer hat das im September 2026 unter einer
Bedingung entschieden: keine Lizenz, die zu kaufen ist, und keine
sichtbare Veränderung der Oberfläche. Beides geprüft (jedi 0.20.0 und
parso 0.8.7 stehen unter MIT, 13,9 MB, kein Namenszug, keine
Netzverbindung).

Zwei Dinge macht dieses Modul zusätzlich, und das sind die, auf die es
im Unterricht ankommt:

**Die Reihenfolge.** jedi liefert alles alphabetisch. Für jemanden, der
gerade anfängt, ist aber nicht alles gleich wichtig. Ganz oben stehen
deshalb die **eigenen Komponenten des Formulars** (`self.b_start`) –
der häufigste Fall überhaupt –, dann die Eigenschaften und Ereignisse
der `pcl`-Komponenten, dann was sonst in der Datei steht, und zuletzt
Schlüsselwörter und eingebaute Funktionen.

**Die Erklärung.** jedi findet zu `caption` **keinen** Hilfetext: die
`pcl`-Eigenschaften sind Deskriptoren, ihr `doc=` steht nicht im
Docstring. Genau dort liegt aber der deutsche Text, den eine Schülerin
braucht. Dieses Modul holt ihn direkt aus `pcl.properties`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path

#: Ab wie vielen getippten Zeichen die Liste erscheint. Ab einem Zeichen
#: springt sie ständig auf und stört mehr, als sie hilft.
MINDESTZEICHEN = 2

#: Wie viele Vorschläge höchstens angezeigt werden. Eine Liste mit
#: dreihundert Einträgen liest niemand.
HOECHSTZAHL = 40

#: Rangstufen – kleiner ist weiter oben.
RANG_KOMPONENTE = 0
RANG_PCL = 1
RANG_DATEI = 2
RANG_PYTHON = 3

#: `self.<name> = ` – so entsteht in einem Natter-Formular eine
#: Komponente. Gesucht wird im Quelltext selbst, weil jedi zwar den
#: Namen kennt, aber nicht, dass er im Unterricht der wichtigste ist.
_KOMPONENTEN_MUSTER = re.compile(
    r"^\s*self\.([A-Za-z_]\w*)\s*=\s*([A-Za-z_]\w*)\s*\(", re.MULTILINE
)

#: Deutsche Erklärungen zu den Schlüsselwörtern, die im Unterricht
#: vorkommen. Pythons eigene Hilfe ist englisch und für die Zielgruppe
#: unbrauchbar.
SCHLUESSELWORT_HILFE: dict[str, str] = {
    "and": "logisches Und: beide Bedingungen müssen zutreffen",
    "as": "gibt einem Import oder einem Kontext einen anderen Namen",
    "assert": "bricht ab, wenn die Bedingung nicht stimmt",
    "break": "verlässt die Schleife sofort",
    "class": "beginnt eine Klasse",
    "continue": "springt zum nächsten Schleifendurchlauf",
    "def": "beginnt eine Funktion oder Methode",
    "del": "löscht einen Namen oder einen Listeneintrag",
    "elif": "weiterer Fall, wenn das vorige „if“ nicht zutraf",
    "else": "was sonst passieren soll",
    "except": "fängt einen Fehler ab",
    "False": "der Wahrheitswert „falsch“",
    "finally": "läuft in jedem Fall, auch nach einem Fehler",
    "for": "Zählschleife über eine Liste oder einen Bereich",
    "from": "holt einzelne Namen aus einem Modul",
    "global": "greift auf eine Variable außerhalb der Funktion zu",
    "if": "führt etwas nur unter einer Bedingung aus",
    "import": "bindet ein Modul ein",
    "in": "prüft, ob etwas enthalten ist – oder gehört zu „for“",
    "is": "prüft, ob es **dasselbe** Objekt ist (nicht: der gleiche Wert)",
    "lambda": "kurze Funktion ohne Namen",
    "None": "„nichts“ – der leere Wert",
    "not": "kehrt eine Bedingung um",
    "or": "logisches Oder: eine der Bedingungen genügt",
    "pass": "tut nichts – Platzhalter, wo Python etwas erwartet",
    "raise": "löst selbst einen Fehler aus",
    "return": "gibt einen Wert zurück und verlässt die Funktion",
    "self": "das eigene Objekt – darüber erreichst du deine Komponenten",
    "True": "der Wahrheitswert „wahr“",
    "try": "versucht etwas, das schiefgehen kann",
    "while": "Schleife, solange die Bedingung zutrifft",
    "with": "öffnet etwas und schließt es zuverlässig wieder",
}


@dataclass(frozen=True)
class Vorschlag:
    """Ein Eintrag der Vorschlagsliste."""

    name: str
    art: str
    erklaerung: str
    signatur: str
    rang: int

    @property
    def anzeige(self) -> str:
        """Die Zeile, wie sie in der Liste steht.

        Die Signatur nur, wenn sie auch mit dem Namen anfängt: bei einem
        Ereignis wie `on_click` liefert jedi `NoneType()` – der Typ des
        Standardwerts, nicht der Name. Im Bildschirmfoto stand dort
        wirklich „NoneType()   –   Wird beim Klicken ausgelöst“, und
        niemand hätte erraten, dass das `on_click` ist.
        """
        links = self.signatur if self.signatur.startswith(self.name) else self.name
        return f"{links}   –   {self.erklaerung}" if self.erklaerung else links


@cache
def _pcl_hilfetexte() -> dict[str, str]:
    """Name einer `pcl`-Eigenschaft oder eines Ereignisses → deutscher
    Hilfetext.

    Über alle Komponenten hinweg: `caption` heißt überall dasselbe, und
    eine Liste je Komponente wäre beim Tippen ohnehin nicht zu
    unterscheiden. Wo sich zwei Texte unterscheiden, gewinnt der erste –
    besser ein leicht unscharfer Hinweis als gar keiner.
    """
    import pcl
    from pcl.control import Control
    from pcl.properties import eigenschaften, ereignisse

    texte: dict[str, str] = {}
    for name in dir(pcl):
        typ = getattr(pcl, name)
        if not isinstance(typ, type) or not issubclass(typ, Control):
            continue
        for feldname, feld in eigenschaften(typ).items():
            texte.setdefault(feldname, getattr(feld, "doc", "") or "")
        for feldname, feld in ereignisse(typ).items():
            texte.setdefault(feldname, getattr(feld, "doc", "") or "")
    return {name: text for name, text in texte.items() if text}


def eigene_komponenten(quelltext: str) -> dict[str, str]:
    """Die Namen, die im Formular als `self.<name> = Typ(...)`
    entstehen, mit ihrem Typ.

    Der Typ ist die Erklärung, die im Unterricht zählt: „b_start“ sagt
    einer Schülerin wenig, „Button auf diesem Formular“ sagt ihr, was
    sie damit machen kann.
    """
    return dict(_KOMPONENTEN_MUSTER.findall(quelltext))


def _erklaerung(
    name: str, art: str, docstring: str, komponenten: dict[str, str]
) -> str:
    """Eine **kurze deutsche** Erklärung. Eine Liste aus nackten Namen
    hilft niemandem, der gerade erst anfängt."""
    if name in komponenten:
        return f"{komponenten[name]} auf diesem Formular"
    if name in SCHLUESSELWORT_HILFE:
        return SCHLUESSELWORT_HILFE[name]
    aus_pcl = _pcl_hilfetexte().get(name)
    if aus_pcl:
        return aus_pcl
    erste_zeile = (docstring or "").strip().splitlines()
    return erste_zeile[0].strip() if erste_zeile else ""


def _rang(name: str, art: str, komponenten: dict[str, str]) -> int:
    if name in komponenten:
        return RANG_KOMPONENTE
    if name in _pcl_hilfetexte():
        return RANG_PCL
    if art in ("keyword", "instance") or name in SCHLUESSELWORT_HILFE:
        return RANG_PYTHON
    if art == "module":
        return RANG_PYTHON
    return RANG_DATEI


def vorschlaege(
    quelltext: str,
    zeile: int,
    spalte: int,
    pfad: Path | str | None = None,
    hoechstzahl: int = HOECHSTZAHL,
) -> list[Vorschlag]:
    """Vorschläge für die Stelle (`zeile` ab 1, `spalte` ab 0).

    Eine leere Liste bedeutet „nichts anzubieten“ – auch dann, wenn
    jedi selbst stolpert. Eine halb getippte Zeile ist syntaktisch fast
    immer kaputt; ein Fehler darf die Eingabe nie unterbrechen.
    """
    try:
        import jedi

        skript = jedi.Script(code=quelltext, path=str(pfad) if pfad else None)
        gefunden = skript.complete(zeile, spalte)
    except Exception:  # noqa: BLE001 - beim Tippen darf nichts hochgehen
        return []

    komponenten = eigene_komponenten(quelltext)
    ergebnis: list[Vorschlag] = []
    for eintrag in gefunden:
        # Alles mit führendem Unterstrich bleibt draußen. In Python
        # heißt das „geht dich nichts an“, und für die Zielgruppe wären
        # `_qwidget` oder `_bei_prop_aenderung` zwischen `caption` und
        # `width` nicht nur Rauschen, sondern eine Einladung, an den
        # Innereien zu drehen.
        if eintrag.name.startswith("_"):
            continue
        try:
            docstring = eintrag.docstring(raw=True)
            signatur = eintrag.name
            unterschriften = eintrag.get_signatures()
            if unterschriften:
                signatur = unterschriften[0].to_string()
        except Exception:  # noqa: BLE001
            docstring, signatur = "", eintrag.name
        ergebnis.append(
            Vorschlag(
                name=eintrag.name,
                art=eintrag.type,
                erklaerung=_erklaerung(
                    eintrag.name, eintrag.type, docstring, komponenten
                ),
                signatur=signatur,
                rang=_rang(eintrag.name, eintrag.type, komponenten),
            )
        )

    ergebnis.sort(key=lambda v: (v.rang, v.name.lower()))
    return ergebnis[:hoechstzahl]


def parameterhilfe(
    quelltext: str, zeile: int, spalte: int, pfad: Path | str | None = None
) -> str:
    """Welche Parameter hier erwartet werden – für die Anzeige beim
    Tippen der öffnenden Klammer. Leer, wenn es nichts zu sagen gibt."""
    try:
        import jedi

        skript = jedi.Script(code=quelltext, path=str(pfad) if pfad else None)
        unterschriften = skript.get_signatures(zeile, spalte)
    except Exception:  # noqa: BLE001
        return ""
    if not unterschriften:
        return ""
    return unterschriften[0].to_string()
