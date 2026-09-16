"""Kommando-Muster für Rückgängig/Wiederholen im Designer.

Siehe konzept-natter.md, Abschnitt 7.7: „Kopieren/Einfügen, Rückgängig/
Wiederholen (Command-Pattern)“. `Kommando` ist die gemeinsame
Schnittstelle (`tun`/`rueckgaengig`); `Kommandostapel` verwaltet die
beiden Stapel. `EigenschaftKommando` deckt reine Eigenschaftsänderungen
(Verschieben, Größe ändern, …) generisch ab, indem es die vorherigen
Werte selbst ermittelt statt Deltas zu verrechnen – robust auch dort, wo
eine Änderung intern begrenzt wird (z. B. Mindestgröße 1 px).
"""

from __future__ import annotations

from typing import Any, Protocol


class Kommando(Protocol):
    def tun(self) -> None: ...
    def rueckgaengig(self) -> None: ...


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
            else {name: getattr(komponente, name) for name in neue_werte}
        )

    def tun(self) -> None:
        for name, wert in self._neue_werte.items():
            setattr(self.komponente, name, wert)

    def rueckgaengig(self) -> None:
        for name, wert in self._alte_werte.items():
            setattr(self.komponente, name, wert)


class Kommandostapel:
    def __init__(self) -> None:
        self._rueckgaengig_stapel: list[Kommando] = []
        self._wiederholen_stapel: list[Kommando] = []

    def ausfuehren(self, kommando: Kommando) -> None:
        kommando.tun()
        self._rueckgaengig_stapel.append(kommando)
        self._wiederholen_stapel.clear()

    def rueckgaengig(self) -> None:
        if not self._rueckgaengig_stapel:
            return
        kommando = self._rueckgaengig_stapel.pop()
        kommando.rueckgaengig()
        self._wiederholen_stapel.append(kommando)

    def wiederholen(self) -> None:
        if not self._wiederholen_stapel:
            return
        kommando = self._wiederholen_stapel.pop()
        kommando.tun()
        self._rueckgaengig_stapel.append(kommando)

    @property
    def kann_rueckgaengig(self) -> bool:
        return bool(self._rueckgaengig_stapel)

    @property
    def kann_wiederholen(self) -> bool:
        return bool(self._wiederholen_stapel)
