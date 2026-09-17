"""Kommandos des Diagramm-Editors für Rückgängig/Wiederholen
(Abschnitt 13.3: „unbegrenzt innerhalb der Sitzung“).

Gegenstück zu `ide/designer/kommando.py`: derselbe Stapel aus
`ide/kommando.py`, aber auf `dict`-Formen statt auf `pcl`-Komponenten.
Formen werden beim Löschen mitsamt ihrer Position in der Liste gemerkt,
damit `rueckgaengig()` die Zeichenreihenfolge (wer liegt oben)
wiederherstellt statt die Form ans Ende zu hängen.
"""

from __future__ import annotations

import copy
from typing import Any


class WerteKommando:
    """Ändert Werte einer Form (Verschieben, Größe, Text …) und merkt
    sich die vorherigen. `alte_werte` explizit angeben, wenn die Form
    durch eine Live-Vorschau (Ziehen) bereits verändert wurde."""

    def __init__(
        self,
        form: dict[str, Any],
        neue_werte: dict[str, Any],
        alte_werte: dict[str, Any] | None = None,
    ) -> None:
        self.form = form
        self._neue_werte = copy.deepcopy(neue_werte)
        self._alte_werte = copy.deepcopy(
            alte_werte
            if alte_werte is not None
            else {name: form.get(name) for name in neue_werte}
        )

    def tun(self) -> None:
        self.form.update(copy.deepcopy(self._neue_werte))

    def rueckgaengig(self) -> None:
        self.form.update(copy.deepcopy(self._alte_werte))


class EinfuegenKommando:
    """Fügt eine Form hinzu (Platzieren, Duplizieren)."""

    def __init__(self, formen: list[dict[str, Any]], form: dict[str, Any]) -> None:
        self.formen = formen
        self.form = form

    def tun(self) -> None:
        self.formen.append(self.form)

    def rueckgaengig(self) -> None:
        if self.form in self.formen:
            self.formen.remove(self.form)


class LoeschenKommando:
    """Löscht eine Form und stellt sie an derselben Stelle der
    Zeichenreihenfolge wieder her."""

    def __init__(self, formen: list[dict[str, Any]], form: dict[str, Any]) -> None:
        self.formen = formen
        self.form = form
        self._index = formen.index(form)

    def tun(self) -> None:
        if self.form in self.formen:
            self._index = self.formen.index(self.form)
            self.formen.remove(self.form)

    def rueckgaengig(self) -> None:
        self.formen.insert(self._index, self.form)
