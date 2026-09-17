"""Kommandos des Formular-Designers für Rückgängig/Wiederholen.

Siehe konzept-natter.md, Abschnitt 7.7: „Kopieren/Einfügen, Rückgängig/
Wiederholen (Command-Pattern)“. Der Stapel selbst steht neutral in
`ide/kommando.py`, weil ihn auch der Diagramm-Editor benutzt; hier
stehen nur die Kommandos, die `pcl`-Komponenten verändern.

`EigenschaftKommando` deckt reine Eigenschaftsänderungen (Verschieben,
Größe ändern, …) generisch ab, indem es die vorherigen Werte selbst
ermittelt statt Deltas zu verrechnen – robust auch dort, wo eine
Änderung intern begrenzt wird (z. B. Mindestgröße 1 px).
"""

from __future__ import annotations

from typing import Any

from ide.kommando import Kommando, Kommandostapel
from pcl.properties import wert_lesen, wert_setzen

__all__ = ["EigenschaftKommando", "Kommando", "Kommandostapel"]


class EigenschaftKommando:
    """Setzt mehrere Eigenschaften auf einer Komponente und merkt sich
    die vorherigen Werte für `rueckgaengig()`. `alte_werte` kann explizit
    angegeben werden, wenn die Komponente zwischen dem eigentlichen
    Vorgang (z. B. einer Live-Vorschau beim Ziehen) und dem Erzeugen des
    Kommandos schon verändert wurde – sonst würde der bereits geänderte
    Wert fälschlich als „alt“ übernommen."""

    def __init__(
        self,
        komponente: Any,
        neue_werte: dict[str, Any],
        alte_werte: dict[str, Any] | None = None,
    ) -> None:
        self.komponente = komponente
        self._neue_werte = dict(neue_werte)
        self._alte_werte = (
            dict(alte_werte)
            if alte_werte is not None
            else {name: wert_lesen(komponente, name) for name in neue_werte}
        )

    def tun(self) -> None:
        for name, wert in self._neue_werte.items():
            wert_setzen(self.komponente, name, wert)

    def rueckgaengig(self) -> None:
        for name, wert in self._alte_werte.items():
            wert_setzen(self.komponente, name, wert)
