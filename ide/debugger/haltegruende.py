"""Deutsche Fassung der DAP-Haltegründe (M11, Abschnitt 4).

Das Debug-Adapter-Protokoll nennt den Grund, aus dem ein Programm
stehengeblieben ist, auf Englisch: `breakpoint`, `step`, `exception`,
`pause`. In der Statusleiste stand das bisher wörtlich so da –
„Angehalten (breakpoint)“. Wer im ersten Python-Jahr sitzt, liest dort
ein Wort, das ihm nichts sagt, an genau der Stelle, an der er wissen
will, warum das Programm gerade nicht weiterläuft.

Unbekannte Gründe werden unverändert durchgereicht: debugpy kann
Gründe melden, die hier noch nicht stehen, und ein englisches Wort ist
immer noch besser als gar keines.
"""

from __future__ import annotations

#: Die Gründe, die debugpy im Unterricht tatsächlich schickt.
HALTEGRUENDE = {
    "breakpoint": "an einem Haltepunkt",
    "step": "nach einem Einzelschritt",
    "pause": "angehalten über „Start → Pause“",
    "exception": "wegen eines Fehlers im Programm",
    "entry": "gleich zu Beginn des Programms",
    "goto": "an der angesprungenen Zeile",
    "function breakpoint": "am Anfang einer Funktion mit Haltepunkt",
    "data breakpoint": "weil sich ein beobachteter Wert geändert hat",
    "instruction breakpoint": "an einem Haltepunkt im Maschinencode",
}


def haltegrund_deutsch(grund: str) -> str:
    """Warum das Programm steht, auf Deutsch.

    Ein unbekannter Grund kommt unverändert zurück – lieber das
    englische Wort des Debuggers als gar keine Angabe.
    """
    return HALTEGRUENDE.get(grund, grund)
