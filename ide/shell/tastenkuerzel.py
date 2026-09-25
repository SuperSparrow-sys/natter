"""Tastenkürzel-Übersicht unter „Hilfe“ (M11, Abschnitt 4).

Die Kürzel gab es alle schon – sie standen nur nirgends zusammen. Wer
sie nicht in den Menüs entdeckt, benutzt sie nie, und gerade die Kürzel
im Editor (Zeile verschieben, Zeile duplizieren, Vervollständigung
erzwingen) stehen in gar keinem Menü.

Die Liste wird aus dem Aktionsregister erzeugt, nicht von Hand
gepflegt. Eine von Hand gepflegte Liste ist nach der dritten neuen
Aktion falsch, und eine falsche Übersicht ist schlimmer als keine.

Dazu kommen die Tasten, die kein Menüeintrag sind und deshalb auch in
keinem Register stehen: sie sind hier als `EDITORTASTEN` und
`DESIGNERTASTEN` aufgeschrieben und werden von Tests gegen den Editor
und den Designer gehalten, damit sie nicht still veralten.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from PySide6.QtGui import QKeySequence

#: Die Reihenfolge der Menüs in der Übersicht – dieselbe wie in der
#: Menüleiste, damit man das Gesuchte dort sucht, wo man es kennt.
MENUE_REIHENFOLGE = (
    "Datei",
    "Bearbeiten",
    "Suchen",
    "Ansicht",
    "Quelltext",
    "Projekt",
    "Start",
    "Pakete",
    "Werkzeuge",
    "Fenster",
    "Hilfe",
)

#: Was nur im Editor gilt und in keinem Menü steht. Der Test
#: `tests/test_tastenkuerzel.py` hält jede dieser Zeilen gegen den
#: Editor – eine Übersicht, die etwas Falsches verspricht, schickt
#: jemanden auf die Suche nach einem Fehler, den es nicht gibt.
EDITORTASTEN = (
    ("Strg+Leertaste", "Vervollständigung auch ohne angefangenes Wort"),
    ("Strg+D", "Zeile darunter noch einmal einfügen"),
    ("Alt+Pfeil hoch/runter", "Zeile nach oben oder unten schieben"),
    ("F12", "Zur Definition des Namens unter dem Cursor springen"),
    ("Strg+Mausrad", "Schrift größer oder kleiner"),
    ("Tab", "Vier Leerzeichen – nie ein Tabulatorzeichen"),
    ("Rücktaste im Einzug", "Eine ganze Einrückungsebene zurück"),
    ("Klick rechts im Zeilenrand", "Klasse oder Funktion zuklappen"),
    ("Klick links im Zeilenrand", "Haltepunkt setzen oder entfernen"),
)

#: Was nur im Designer gilt. Bis September 2026 stand keine dieser
#: Tasten in der Übersicht: sie sind weder ein Menüeintrag noch eine
#: Editortaste, und wer sie nicht zufällig ausprobiert, schiebt jede
#: Komponente mit der Maus. Aufgefallen ist die Lücke beim Durchgehen
#: der Texte - `docs/handbuch.md` beschreibt sie, und die
#: Übersicht daneben schwieg.
#:
#: Geschrieben wie in `docs/handbuch.md` - zwei Schreibweisen
#: für dieselbe Taste wären zwei Tasten.
DESIGNERTASTEN = (
    ("Pfeiltasten", "Ausgewählte Komponente um einen Rasterschritt verschieben"),
    ("Alt+Pfeil", "Um genau einen Bildpunkt verschieben, am Raster vorbei"),
    ("Umschalt+Pfeil", "Größe ändern statt verschieben"),
    ("Strg+D", "Komponente verdoppeln"),
    ("Entf", "Komponente löschen"),
    ("F2", "Menü-Editor öffnen, bei einem MainMenu oder PopupMenu"),
)


def deutsche_taste(kuerzel: str) -> str:
    """Ein Kürzel so, wie es im Menü steht: „Strg+S“, nicht „Ctrl+S“.

    Qt schreibt die Namen selbst, sobald seine deutsche Übersetzung
    geladen ist (`ide/deutsch.py`). Die Übersicht fragt deshalb Qt und
    schreibt nicht ihre eigene Tabelle – sonst stünde in der Übersicht
    etwas anderes als im Menü daneben.
    """
    return QKeySequence(kuerzel).toString(QKeySequence.SequenceFormat.NativeText)


@dataclass(frozen=True)
class Gruppe:
    """Ein Menü mit seinen Kürzeln."""

    titel: str
    eintraege: tuple[tuple[str, str], ...]


def uebersicht(aktionen: Iterable) -> list[Gruppe]:
    """Alle Aktionen mit Tastenkürzel, nach Menü gruppiert.

    Aktionen ohne Kürzel bleiben draußen: die Übersicht soll die Tasten
    zeigen, nicht die Menüs noch einmal abschreiben.
    """
    je_menue: dict[str, list[tuple[str, str]]] = {}
    for aktion in aktionen:
        if not aktion.tastenkuerzel:
            continue
        je_menue.setdefault(aktion.menue or "Ohne Menü", []).append(
            (deutsche_taste(aktion.tastenkuerzel), aktion.name)
        )

    gruppen = []
    bekannt = [m for m in MENUE_REIHENFOLGE if m in je_menue]
    uebrig = sorted(m for m in je_menue if m not in MENUE_REIHENFOLGE)
    for titel in [*bekannt, *uebrig]:
        eintraege = sorted(je_menue[titel], key=lambda e: e[1].lower())
        gruppen.append(Gruppe(titel, tuple(eintraege)))
    return gruppen


def als_markdown(aktionen: Iterable) -> str:
    """Die Übersicht als Hilfeseite."""
    zeilen = [
        "# Tastenkürzel",
        "",
        "Alles, was Natter kann, geht auch über die Menüs. Die folgenden",
        "Tasten sind die Abkürzungen dorthin.",
        "",
    ]
    for gruppe in uebersicht(aktionen):
        zeilen += [f"## {gruppe.titel}", "", "| Taste | Was passiert |", "| --- | --- |"]
        zeilen += [f"| `{taste}` | {name} |" for taste, name in gruppe.eintraege]
        zeilen.append("")

    zeilen += [
        "## Nur im Quelltexteditor",
        "",
        "Diese Tasten stehen in keinem Menü – sie wirken dort, wo der",
        "Cursor steht.",
        "",
        "| Taste | Was passiert |",
        "| --- | --- |",
    ]
    zeilen += [f"| `{taste}` | {was} |" for taste, was in EDITORTASTEN]
    zeilen.append("")

    zeilen += [
        "## Nur im Formular-Designer",
        "",
        "Diese Tasten wirken auf die ausgewählte Komponente.",
        "",
        "| Taste | Was passiert |",
        "| --- | --- |",
    ]
    zeilen += [f"| `{taste}` | {was} |" for taste, was in DESIGNERTASTEN]
    zeilen.append("")
    return "\n".join(zeilen)
