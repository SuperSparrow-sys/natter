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


class SammelKommando:
    """Mehrere Kommandos als ein einziger Undo-Schritt – z. B. eine Form
    zusammen mit ihren Verbindungen löschen, die sonst als Verweise ins
    Leere zurückblieben."""

    def __init__(self, kommandos: list[Any]) -> None:
        self.kommandos = list(kommandos)

    def tun(self) -> None:
        for kommando in self.kommandos:
            kommando.tun()

    def rueckgaengig(self) -> None:
        for kommando in reversed(self.kommandos):
            kommando.rueckgaengig()


class ReihenfolgeKommando:
    """Ändert die Zeichenreihenfolge (Vordergrund/Hintergrund).

    Merkt sich die ganze alte Liste statt einzelner Stellen: wer
    drei Formen auf einmal nach vorn holt, verschiebt damit auch alle
    dazwischenliegenden, und die müssten sonst einzeln nachgehalten
    werden.
    """

    def __init__(
        self, formen: list[dict[str, Any]], neue_reihenfolge: list[dict[str, Any]]
    ) -> None:
        self.formen = formen
        self._neu = list(neue_reihenfolge)
        self._alt = list(formen)

    def tun(self) -> None:
        self.formen[:] = self._neu

    def rueckgaengig(self) -> None:
        self.formen[:] = self._alt
