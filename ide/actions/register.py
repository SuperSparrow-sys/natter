"""Aktion, Aktionsregister. Siehe ide/actions/__init__.py."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

from PySide6.QtGui import QAction

from ide.assets import symbol as symbol_laden


class AktionsKonfliktError(Exception):
    """Eine Aktions-ID ist bereits vergeben oder ein Tastenkürzel ist
    bereits einer anderen Aktion zugeordnet (Abschnitt 7.9: „Konflikte
    werden angezeigt“)."""


class Aktion:
    """Eine Aktion: ID, deutscher Name, Menüposition, Tastenkürzel,
    Bereich und Symbolname – wie in `docs/aktionen.md` beschrieben. Das
    zugehörige `QAction` wird hier einmal erzeugt und überall
    weiterverwendet (Menü, Werkzeugleiste, Befehlspalette)."""

    def __init__(
        self,
        id: str,
        name: str,
        *,
        menue: str = "",
        tastenkuerzel: str = "",
        bereich: str = "überall",
        symbol: str = "",
        trennlinie_davor: bool = False,
        callback: Callable[[], Any] | None = None,
    ) -> None:
        self.id = id
        self.name = name
        self.menue = menue
        self.tastenkuerzel = tastenkuerzel
        self.bereich = bereich
        self.symbol = symbol
        # nur für die Werkzeugleiste: gruppiert z. B. "Start" optisch von
        # den Datei-Aktionen ab (Abschnitt 7.3, wie in Lazarus üblich)
        self.trennlinie_davor = trennlinie_davor

        self.qaction = QAction(name)
        if tastenkuerzel:
            self.qaction.setShortcut(tastenkuerzel)
        if symbol:
            self.qaction.setIcon(symbol_laden(symbol))
        if callback is not None:
            self.qaction.triggered.connect(callback)


class Aktionsregister:
    def __init__(self) -> None:
        self._aktionen: dict[str, Aktion] = {}

    def registrieren(self, aktion: Aktion) -> Aktion:
        if aktion.id in self._aktionen:
            raise AktionsKonfliktError(f"Aktion {aktion.id!r} ist bereits registriert.")

        konflikt = self._tastenkuerzel_konflikt(aktion.tastenkuerzel)
        if konflikt is not None:
            raise AktionsKonfliktError(
                f"Tastenkürzel {aktion.tastenkuerzel!r} ist bereits durch "
                f"{konflikt.id!r} belegt."
            )

        self._aktionen[aktion.id] = aktion
        return aktion

    def _tastenkuerzel_konflikt(self, tastenkuerzel: str) -> Aktion | None:
        if not tastenkuerzel:
            return None
        for aktion in self._aktionen.values():
            if aktion.tastenkuerzel == tastenkuerzel:
                return aktion
        return None

    def an_hauptfenster_anhaengen(self, hauptfenster: Any) -> None:
        """Fügt jede Aktion mit gesetztem `menue` in das gleichnamige Menü
        des Hauptfensters ein (Abschnitt 7.2); Aktionen mit gesetztem
        `symbol` zusätzlich als Knopf in die Werkzeugleiste, in
        Registrierungsreihenfolge (Abschnitt 7.3: „eine Aktion = Menüeintrag
        + Werkzeugleisten-Button … nur einmal implementiert“)."""
        for aktion in self._aktionen.values():
            if aktion.menue:
                hauptfenster.menue(aktion.menue).addAction(aktion.qaction)
            if aktion.symbol:
                if aktion.trennlinie_davor:
                    hauptfenster.werkzeugleiste.addSeparator()
                hauptfenster.werkzeugleiste.addAction(aktion.qaction)

    def __getitem__(self, id: str) -> Aktion:
        return self._aktionen[id]

    def __iter__(self) -> Iterator[Aktion]:
        return iter(self._aktionen.values())

    def __len__(self) -> int:
        return len(self._aktionen)
