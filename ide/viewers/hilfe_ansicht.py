"""Hilfeseiten im Programm selbst anzeigen (M11, Abschnitt 4).

Die Hilfetexte von Natter liegen als Markdown in `docs/`. Bis jetzt
wurden sie auf zwei Wegen gezeigt, und beide waren für die Zielgruppe
unbrauchbar:

* „Erste Schritte“ öffnete die `.md`-Datei im **Quelltexteditor** –
  eine Anleitung mit `##` und `*` davor, in einem Fenster, das nach
  Programmieren aussieht und in dem man sie versehentlich ändern kann
* die Komponenten-Referenz gab die Datei an **Windows** weiter. Dort
  ist für `.md` meist gar nichts eingetragen; im besten Fall öffnete
  sich der Editor, im Normalfall passierte nichts

Beides zeigt jetzt dieselbe Ansicht: lesbar gesetzt, im Programm, in
einem eigenen Reiter neben dem Quelltext.
"""

from __future__ import annotations

from PySide6.QtGui import QFontDatabase, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QTextBrowser, QWidget

#: Schriftarten für Code-Stellen, in der Reihenfolge der Vorliebe. Die
#: erste, die es auf dem Rechner gibt, wird genommen.
#:
#: Qt setzt beim Umwandeln von Markdown alles in `…` und jeden
#: Code-Block auf die Familie **„monospace“** - einen Gattungsnamen, den
#: es unter Windows nicht als Schriftart gibt (`QFontDatabase.families()`
#: kennt ihn selbst dann nicht, wenn alle 255 Windows-Schriften geladen
#: sind). Qt muss dann irgendetwas einsetzen, und heraus kam
#: unleserliches Zeug: aus `u_main_design.py` wurde „u_m⌐H h_desig⌐h py“.
#: Betroffen war jede Hilfeseite - die Komponenten-Referenz besteht fast
#: nur aus solchen Stellen (M12, am Bildschirmfoto gefunden).
CODE_SCHRIFTEN = ("Consolas", "Courier New", "DejaVu Sans Mono", "Courier")

#: Der Gattungsname, den Qt beim Umwandeln von Markdown einsetzt.
_IST_CODE = "monospace"


def code_schriftart() -> str:
    """Die erste vorhandene Schriftart aus `CODE_SCHRIFTEN`."""
    vorhanden = set(QFontDatabase.families())
    for name in CODE_SCHRIFTEN:
        if name in vorhanden:
            return name
    return CODE_SCHRIFTEN[-1]


class HilfeAnsicht(QTextBrowser):
    """Eine Hilfeseite aus Markdown. Nur lesen, nicht ändern."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setOpenExternalLinks(True)
        self.setReadOnly(True)

    def markdown_setzen(self, text: str) -> None:
        """Setzt den Inhalt aus Markdown."""
        self.setMarkdown(text)
        self._code_schrift_setzen()

    def _code_schrift_setzen(self) -> None:
        """Ersetzt die Gattungsfamilie „monospace“ durch eine, die es
        wirklich gibt.

        Bewusst **nach** `setMarkdown` und nicht über
        `document().setDefaultStyleSheet()`: die Vorlage greift nur beim
        Einlesen von HTML, `setMarkdown` geht daran vorbei (nachgemessen,
        die Familie blieb „monospace“).
        """
        schrift = code_schriftart()
        dokument = self.document()
        stellen: list[tuple[int, int]] = []

        block = dokument.begin()
        while block.isValid():
            teil = block.begin()
            while not teil.atEnd():
                stueck = teil.fragment()
                if stueck.isValid() and _IST_CODE in (
                    stueck.charFormat().fontFamilies() or []
                ):
                    stellen.append((stueck.position(), stueck.length()))
                teil += 1
            block = block.next()

        if not stellen:
            return

        # Erst sammeln, dann ändern: ein Eingriff ins Dokument macht die
        # Durchlaufzeiger oben ungültig.
        format_ = QTextCharFormat()
        format_.setFontFamilies([schrift])
        cursor = QTextCursor(dokument)
        cursor.beginEditBlock()
        for anfang, laenge in stellen:
            cursor.setPosition(anfang)
            cursor.setPosition(anfang + laenge, QTextCursor.MoveMode.KeepAnchor)
            cursor.mergeCharFormat(format_)
        cursor.endEditBlock()
