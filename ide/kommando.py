"""Kommando-Muster für Rückgängig/Wiederholen (Abschnitt 7.7, 13.3).

Neutral abgelegt, weil ihn inzwischen zwei Editoren benutzen: der
Formular-Designer (`ide/designer/`) und der Diagramm-Editor
(`ide/diagramm/`). Der Stapel selbst kennt nur `tun()`/`rueckgaengig()`
und weiß nichts über das, was er verändert – die konkreten Kommandos
stehen jeweils beim Editor, weil sie unterschiedliche Datenmodelle
anfassen (`pcl`-Komponenten hier, `dict`-Formen dort).
"""

from __future__ import annotations

from typing import Protocol


class Kommando(Protocol):
    def tun(self) -> None: ...
    def rueckgaengig(self) -> None: ...


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
    def letztes_kommando(self) -> Kommando | None:
        """Das zuletzt ausgeführte (noch nicht rückgängig gemachte)
        Kommando – damit ein Editor nach Rückgängig/Wiederholen die
        Auswahl passend nachziehen kann."""
        return self._rueckgaengig_stapel[-1] if self._rueckgaengig_stapel else None

    @property
    def kann_rueckgaengig(self) -> bool:
        return bool(self._rueckgaengig_stapel)

    @property
    def kann_wiederholen(self) -> bool:
        return bool(self._wiederholen_stapel)
