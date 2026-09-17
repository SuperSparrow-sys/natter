"""Strings: zeilenweise Textsammlung, wie `TStrings` in Lazarus.

Trägt `items` (ComboBox, ListBox, RadioGroup) und `lines` (Memo) –
verschachtelte, aufklappbare Untereigenschaften (Abschnitt 5.0), kein
eigenständiges `Prop`. Siehe auch Abschnitt 11.2 (Datei-Methoden).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from pathlib import Path

from pcl.errors import NatterPropertyError
from pcl.properties import typ_beschreibung


class Strings:
    def __init__(self, bei_aenderung: Callable[[], None] | None = None) -> None:
        self._zeilen: list[str] = []
        self._bei_aenderung = bei_aenderung

    def add(self, text: str) -> None:
        if not isinstance(text, str):
            raise NatterPropertyError(
                f"Strings.add erwartet {typ_beschreibung(str)}, "
                f"erhalten wurde {typ_beschreibung(type(text))}."
            )
        self._zeilen.append(text)
        self._aendern()

    def clear(self) -> None:
        self._zeilen.clear()
        self._aendern()

    def zuweisen(self, werte: Iterable[str]) -> None:
        """Ersetzt den gesamten Inhalt auf einmal (wie `Items.Assign` in
        Lazarus). Der Setter von `ListBox.items`/`Memo.lines` ruft das
        auf, damit sowohl der erzeugte Formularcode
        (``self.lb.items = ["a", "b"]``) als auch der Objektinspektor die
        Sammlung in einem Schritt setzen können."""
        neu = list(werte)
        for zeile in neu:
            if not isinstance(zeile, str):
                raise NatterPropertyError(
                    f"Strings erwartet {typ_beschreibung(str)} je Zeile, "
                    f"erhalten wurde {typ_beschreibung(type(zeile))}."
                )
        self._zeilen = neu
        self._aendern()

    def load_from_file(self, pfad: str | Path, encoding: str = "utf-8") -> None:
        with open(pfad, encoding=encoding) as datei:
            self._zeilen = [zeile.rstrip("\n") for zeile in datei]
        self._aendern()

    def save_to_file(self, pfad: str | Path, encoding: str = "utf-8") -> None:
        with open(pfad, "w", encoding=encoding) as datei:
            for zeile in self._zeilen:
                datei.write(zeile + "\n")

    def __len__(self) -> int:
        return len(self._zeilen)

    def __getitem__(self, index: int) -> str:
        return self._zeilen[index]

    def __setitem__(self, index: int, wert: str) -> None:
        self._zeilen[index] = wert
        self._aendern()

    def __delitem__(self, index: int) -> None:
        del self._zeilen[index]
        self._aendern()

    def __iter__(self) -> Iterator[str]:
        return iter(self._zeilen)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Strings):
            return self._zeilen == other._zeilen
        if isinstance(other, list):
            return self._zeilen == other
        return NotImplemented

    def __repr__(self) -> str:
        return f"Strings({self._zeilen!r})"

    def _aendern(self) -> None:
        if self._bei_aenderung is not None:
            self._bei_aenderung()
