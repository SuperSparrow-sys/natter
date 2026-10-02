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

@dataclass(frozen=True)
class Editorbefehl:
    """Ein Befehl im Kontextmenü des Editors mit seiner Taste."""

    name: str
    taste: str


#: Die Befehle, die das Kontextmenü des Editors unter Qts
#: Standardeinträgen zeigt. Kontextmenü und Übersicht lesen Name und
#: Taste hier. Vorher standen sie an beiden Stellen getrennt, und
#: dieselbe Taste hieß im Menü „Alt+Pfeil oben“, in der Übersicht
#: „Alt+Pfeil hoch“ (Punkt 440). „Kommentar umschalten“ steht dazu im
#: Menü „Quelltext“ und kommt dort in die Übersicht; Name und Taste
#: sind dieselben wie im Aktionsregister.
EDITORBEFEHLE = {
    "definition": Editorbefehl("Zur Definition springen", "F12"),
    "duplizieren": Editorbefehl("Zeile duplizieren", "Strg+D"),
    "nach_oben": Editorbefehl("Zeile nach oben schieben", "Alt+Pfeil hoch"),
    "nach_unten": Editorbefehl(
        "Zeile nach unten schieben", "Alt+Pfeil runter"
    ),
    "kommentar": Editorbefehl("Kommentar umschalten", "Strg+#"),
}

#: Was nur im Editor gilt und in keinem Menü steht. Der Test
#: `tests/test_tastenkuerzel.py` hält jede dieser Zeilen gegen den
#: Editor – eine Übersicht, die etwas Falsches verspricht, schickt
#: jemanden auf die Suche nach einem Fehler, den es nicht gibt.
EDITORTASTEN = (
    ("Strg+Leertaste", "Vervollständigung auch ohne angefangenes Wort"),
    *(
        (befehl.taste, befehl.name)
        for schluessel, befehl in EDITORBEFEHLE.items()
        if schluessel != "kommentar"
    ),
    ("Strg+Mausrad", "Schrift größer oder kleiner, für alle Editoren gemerkt"),
    ("Strg+Plus/Minus", "Schrift größer oder kleiner"),
    ("Strg+0", "Normale Schriftgröße"),
    ("Tab", "Vier Leerzeichen – nie ein Tabulatorzeichen"),
    ("Umschalt+Tab", "Markierte Zeilen oder die Zeile um eine Ebene ausrücken"),
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
    ("Strg+D", "Komponente duplizieren"),
    ("Entf", "Komponente löschen"),
    ("F2", "Menü-Editor öffnen, bei einem MainMenu oder PopupMenu"),
)


#: Die Tasten des Diagramm-Editors. Er ist ein eigenes Fenster mit
#: eigenen Menüs, die Übersicht kannte nur die des Hauptfensters
#: (Punkt 466), während „Erste Schritte“ Strg+Umschalt+E und Strg+G
#: nannte.
DIAGRAMMTASTEN = (
    ("F1", "Handbuch beim Abschnitt über Diagramme"),
    ("Strg+Umschalt+E", "Quelltext aus dem Diagramm erzeugen"),
    ("F2", "Gewählte Form oder gewählten Block beschriften"),
    ("Entf", "Gewählte Formen oder Blöcke löschen"),
    ("Strg+D", "Duplizieren"),
    ("Strg+G", "Gruppieren"),
    ("Strg+Umschalt+G", "Gruppierung aufheben"),
    ("Strg+1", "Alles anzeigen"),
    ("Strg+0", "Zoom 100 %"),
    ("+ / -", "Im Struktogramm einen Fall oder Strang dazu bzw. weg"),
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

    zeilen += [
        "## Diagramm-Editor",
        "",
        "Diese Tasten gelten im eigenen Fenster des Diagramm-Editors.",
        "",
        "| Taste | Was passiert |",
        "| --- | --- |",
    ]
    zeilen += [f"| `{taste}` | {was} |" for taste, was in DIAGRAMMTASTEN]
    zeilen.append("")
    return "\n".join(zeilen)
