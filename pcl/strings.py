"""Strings: zeilenweise Textsammlung.

Trägt `items` (ComboBox, ListBox, RadioGroup) und `lines` (Memo) –
verschachtelte, aufklappbare Untereigenschaften (Abschnitt 5.0), kein
eigenständiges `Prop`. Siehe auch Abschnitt 11.2 (Datei-Methoden).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from pathlib import Path

from pcl.errors import NatterEintragError, NatterPropertyError
from pcl.properties import typ_beschreibung


def _zeile_pruefen(wert: object, wo: str) -> None:
    if not isinstance(wert, str):
        raise NatterPropertyError(
            f"{wo} {typ_beschreibung(str, akkusativ=True)}, "
            f"erhalten wurde {typ_beschreibung(type(wert))}."
        )


class Strings:
    def __init__(
        self,
        bei_aenderung: Callable[[], None] | None = None,
        bei_anhaengen: Callable[[str], None] | None = None,
        *,
        auswahlliste: bool = False,
    ) -> None:
        """`bei_aenderung` baut die Anzeige der Komponente neu auf.
        `bei_anhaengen` bekommt nur die neue Zeile, wenn `add` sie ans
        Ende hängt.

        Ohne den zweiten Weg schrieb jedes `add` den ganzen Inhalt neu
        ins Widget. 4000 Zeilen in einer Schleife dauerten in einem
        `Memo` 30 Sekunden, in denen das Programm stand.

        `auswahlliste` gilt für die Einträge einer Komponente mit
        `item_index` (`ListBox`, `ComboBox`, `RadioGroup`). Dort lehnt
        das Lesen einen negativen Index ab (Punkt 475): -1 heißt dort
        „nichts ausgewählt“, und `items[self.lb_x.item_index]` gab
        ohne Auswahl still den letzten Eintrag zurück. In `Memo.lines`
        bleibt `lines[-1]` die letzte Zeile, wie bei einer Liste.
        """
        self._zeilen: list[str] = []
        self._auswahlliste = auswahlliste
        self._bei_aenderung = bei_aenderung
        self._bei_anhaengen = bei_anhaengen

    def add(self, text: str) -> None:
        _zeile_pruefen(text, "Strings.add erwartet")
        self._zeilen.append(text)
        if self._bei_anhaengen is not None:
            self._bei_anhaengen(text)
        else:
            self._aendern()

    def append(self, text: str) -> None:
        """Dasselbe wie `add`, unter dem Namen, den Python-Listen
        dafür haben."""
        self.add(text)

    def extend(self, texte: Iterable[str]) -> None:
        """Hängt mehrere Zeilen ans Ende."""
        neu = texte.splitlines() if isinstance(texte, str) else list(texte)
        for zeile in neu:
            _zeile_pruefen(zeile, "Strings.extend erwartet je Zeile")
        self._zeilen.extend(neu)
        self._aendern()

    def reverse(self) -> None:
        """Kehrt die Reihenfolge der Zeilen um."""
        self._zeilen.reverse()
        self._aendern()

    def __iadd__(self, texte: Iterable[str]) -> Strings:
        # `items += ["x"]` wie bei einer Liste. Ohne diese Methode
        # versuchte Python `items + ["x"]` und scheiterte englisch.
        self.extend(texte)
        return self

    def clear(self) -> None:
        self._zeilen.clear()
        self._aendern()

    # Die übrigen Listenbefehle. Im Unterricht wird `items` wie eine
    # Liste behandelt, und `items.insert(0, "x")` soll nicht an einem
    # AttributeError scheitern.

    def insert(self, index: int, text: str) -> None:
        _zeile_pruefen(text, "Strings.insert erwartet")
        self._zeilen.insert(index, text)
        self._aendern()

    def remove(self, text: str) -> None:
        """Entfernt die erste Zeile mit diesem Text."""
        _zeile_pruefen(text, "Strings.remove erwartet")
        if text not in self._zeilen:
            raise ValueError(f"„{text}“ steht nicht in der Liste.")
        self._zeilen.remove(text)
        self._aendern()

    def index(self, text: str) -> int:
        """Die Nummer der ersten Zeile mit diesem Text, gezählt ab 0."""
        _zeile_pruefen(text, "Strings.index erwartet")
        if text not in self._zeilen:
            raise ValueError(f"„{text}“ steht nicht in der Liste.")
        return self._zeilen.index(text)

    def count(self, text: str) -> int:
        """Wie oft eine Zeile mit genau diesem Text vorkommt."""
        _zeile_pruefen(text, "Strings.count erwartet")
        return self._zeilen.count(text)

    def pop(self, index: int | None = None) -> str:
        """Entfernt eine Zeile, ohne Angabe die letzte, und gibt sie
        zurück."""
        if not self._zeilen:
            raise IndexError("Die Liste ist leer.")
        if index is None:
            index = -1
        else:
            self._negativ_pruefen(index)
        try:
            zeile = self._zeilen.pop(index)
        except IndexError:
            raise IndexError(
                f"Eine Zeile {index} gibt es nicht, die Liste hat "
                f"{len(self._zeilen)} Zeilen (0 bis {len(self._zeilen) - 1})."
            ) from None
        self._aendern()
        return zeile

    def sort(
        self, *, key: Callable[[str], object] | None = None, reverse: bool = False
    ) -> None:
        self._zeilen.sort(key=key, reverse=reverse)  # type: ignore[arg-type]
        self._aendern()

    def zuweisen(self, werte: Iterable[str] | str) -> None:
        """Ersetzt den gesamten Inhalt auf einmal. Der Setter von
        `ListBox.items`/`Memo.lines` ruft das auf, damit sowohl der
        erzeugte Formularcode
        (``self.lb.items = ["a", "b"]``) als auch der Objektinspektor die
        Sammlung in einem Schritt setzen können.

        Eine Zeichenkette wird an den Zeilenumbrüchen getrennt. Ohne
        diese Regel zerfiele
        ``self.rg.items = "rot
gelb"`` in acht einzelne Einträge – einen
        je Buchstabe –, weil Python eine Zeichenkette gern Zeichen für
        Zeichen hergibt. Das ist in der Sichtprüfung real passiert: eine
        `RadioGroup` zeigte vierzehn Optionsfelder mit je einem
        Buchstaben.
        """
        if werte is self:
            # `items += [...]` weist die Sammlung sich selbst zu; sie
            # ist dann schon auf dem neuen Stand.
            return
        if isinstance(werte, str):
            werte = werte.splitlines()
        neu = list(werte)
        for zeile in neu:
            _zeile_pruefen(zeile, "Strings erwartet je Zeile")
        self._zeilen = neu
        self._aendern()

    def still_uebernehmen(self, zeilen: list[str]) -> None:
        """Ersetzt den Inhalt, ohne die Komponente zu benachrichtigen.

        Für den Rückweg vom Widget: hat jemand im `Memo` getippt, steht
        der Text dort schon. Ihn noch einmal hineinzuschreiben setzte
        die Schreibmarke an den Anfang zurück.
        """
        self._zeilen = list(zeilen)

    def load_from_file(self, pfad: str | Path, encoding: str | None = None) -> None:
        """Liest die Zeilen einer Textdatei.

        Ohne `encoding` wird die Datei als UTF-8 gelesen, auch mit der
        Markierung am Anfang, die Excel beim Speichern als „CSV UTF-8“
        voranstellt. Sie landete sonst als unsichtbares Zeichen vor der
        ersten Zeile, und ``items[0] == "Name"`` war falsch, obwohl die
        Anzeige stimmte. Ist die Datei kein UTF-8, wird sie in der
        Windows-Kodierung cp1252 gelesen, in der ältere Programme
        Umlaute speichern.
        """
        if encoding is None:
            try:
                zeilen = _zeilen_lesen(pfad, "utf-8-sig")
            except UnicodeDecodeError:
                zeilen = _zeilen_lesen(pfad, "cp1252")
        else:
            zeilen = _zeilen_lesen(pfad, encoding)
        self._zeilen = zeilen
        self._aendern()

    def save_to_file(self, pfad: str | Path, encoding: str = "utf-8") -> None:
        """Schreibt die Zeilen in eine Textdatei.

        Erst wird alles kodiert, dann über eine Zwischendatei
        geschrieben und diese an die Stelle der alten gesetzt. Ein
        Zeichen, das es in `encoding` nicht gibt, eine volle Platte
        oder ein abgezogener Stick hinterließen sonst eine
        abgeschnittene Datei, und der alte Stand war verloren
        (Punkt 547)."""
        import os
        import tempfile

        text = "".join(zeile + "\n" for zeile in self._zeilen)
        daten = text.replace("\n", os.linesep).encode(encoding)
        ziel = Path(pfad)
        griff, zwischen = tempfile.mkstemp(
            prefix=f".{ziel.name}.", suffix=".tmp", dir=ziel.parent or None
        )
        try:
            with os.fdopen(griff, "wb") as datei:
                datei.write(daten)
                datei.flush()
                os.fsync(datei.fileno())
            os.replace(zwischen, ziel)
        except BaseException:
            Path(zwischen).unlink(missing_ok=True)
            raise

    def __len__(self) -> int:
        return len(self._zeilen)

    def __getitem__(self, index: int) -> str:
        if isinstance(index, slice):
            return self._zeilen[index]
        self._negativ_pruefen(index)
        try:
            return self._zeilen[index]
        except IndexError:
            raise NatterEintragError(self._ausserhalb(index)) from None

    def _negativ_pruefen(self, index: object) -> None:
        """In einer Auswahlliste gibt es keine negativen Nummern: -1 ist
        dort `item_index` ohne Auswahl. Geprüft beim Lesen, Schreiben,
        Löschen und `pop`; bis 0.4.3 nur beim Lesen, und ein Knopf
        „Eintrag löschen“ ohne Auswahl löschte still den letzten
        (Punkt 571)."""
        if not (self._auswahlliste and isinstance(index, int) and index < 0):
            return
        if index == -1:
            raise NatterEintragError(
                "Einen Eintrag -1 gibt es nicht. item_index ist -1, "
                "solange in der Liste nichts ausgewählt ist."
            )
        raise NatterEintragError(
            f"Einen Eintrag {index} gibt es nicht. Die Einträge "
            "zählen ab 0."
        )

    def _ausserhalb(self, index: int) -> str:
        anzahl = len(self._zeilen)
        if not anzahl:
            return f"Einen Eintrag {index} gibt es nicht, die Liste ist leer."
        return (
            f"Einen Eintrag {index} gibt es nicht, die Liste hat "
            f"{anzahl} Einträge (0 bis {anzahl - 1})."
        )

    def __setitem__(self, index: int | slice, wert: str | Iterable[str]) -> None:
        # Erst prüfen, dann ändern: sonst stand eine Zahl schon in der
        # Sammlung, bevor die Anzeige an ihr scheiterte, und jede
        # weitere Änderung scheiterte erneut.
        if isinstance(index, slice):
            wert = list(wert)
            for zeile in wert:
                _zeile_pruefen(zeile, "Strings erwartet je Zeile")
        else:
            _zeile_pruefen(wert, "Strings erwartet je Zeile")
            self._negativ_pruefen(index)
        try:
            self._zeilen[index] = wert
        except IndexError:
            raise NatterEintragError(self._ausserhalb(index)) from None
        self._aendern()

    def __delitem__(self, index: int | slice) -> None:
        if not isinstance(index, slice):
            self._negativ_pruefen(index)
        try:
            del self._zeilen[index]
        except IndexError:
            raise NatterEintragError(self._ausserhalb(index)) from None
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


def _zeilen_lesen(pfad: str | Path, kodierung: str) -> list[str]:
    with open(pfad, encoding=kodierung) as datei:
        return [zeile.rstrip("\n") for zeile in datei]
