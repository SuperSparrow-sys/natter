"""Text so sortieren, wie ein deutsches Wörterbuch es tut.

`sorted()` ordnet nach Zeichennummern: „Ärger“ und „Özdemir“ landen
hinter „Zimmer“, und mit `str.casefold` bleibt es dabei. Eine nach
Namen sortierte Klassenliste hatte so alle Namen mit Umlaut am Ende.

Hier zählt ä wie a, ö wie o, ü wie u und ß wie ss, Groß- und
Kleinschreibung zählen nicht (DIN 5007, Variante 1). Erst wo zwei
Texte danach gleich sind, entscheidet der Text selbst, damit die
Reihenfolge immer dieselbe ist.
"""

from __future__ import annotations

_UMSCHREIBUNG = str.maketrans({"ä": "a", "ö": "o", "ü": "u", "ß": "ss"})


def sortierschluessel(text: str) -> str:
    """Der Schlüssel für `sorted(..., key=sortierschluessel)`."""
    return text.casefold().translate(_UMSCHREIBUNG) + "\0" + text
