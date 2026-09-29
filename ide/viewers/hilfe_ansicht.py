"""Hilfeseiten im Programm selbst anzeigen (M11, Abschnitt 4).

Die Hilfetexte von Natter liegen als Markdown in `docs/`. Bis jetzt
wurden sie auf zwei Wegen gezeigt, und beide waren für die Zielgruppe
unbrauchbar:

* „Erste Schritte“ öffnete die `.md`-Datei im Quelltexteditor –
  eine Anleitung mit `##` und `*` davor, in einem Fenster, das nach
  Programmieren aussieht und in dem man sie versehentlich ändern kann
* die Komponenten-Referenz gab die Datei an Windows weiter. Dort
  ist für `.md` meist gar nichts eingetragen; im besten Fall öffnete
  sich der Editor, im Normalfall passierte nichts

Beides zeigt jetzt dieselbe Ansicht: lesbar gesetzt, im Programm, in
einem eigenen Reiter neben dem Quelltext.
"""

from __future__ import annotations

from PySide6.QtGui import (
    QFontDatabase,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
)
from PySide6.QtWidgets import QTextBrowser, QWidget

#: Schriftarten für Code-Stellen, in der Reihenfolge der Vorliebe. Die
#: erste, die es auf dem Rechner gibt, wird genommen.
#:
#: Qt setzt beim Umwandeln von Markdown alles in `…` und jeden
#: Code-Block auf die Familie „monospace“ - einen Gattungsnamen, den
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


#: Breiteste Textspalte in Punkten. Rund 80 Zeichen der
#: Fließtextschrift - darüber verliert das Auge beim Zeilenwechsel den
#: Anschluss und findet den Zeilenanfang nicht wieder. Was breiter
#: ist, bleibt Rand.
HOECHSTBREITE = 720

#: Zeilenabstand in Prozent. 160 statt Qts 100: ein Text, dessen
#: Zeilen aufeinanderkleben, sieht aus wie eine Fehlermeldung.
ZEILENABSTAND = 160


def stilvorlage(dunkel: bool, code_schrift: str) -> str:
    """Die Gestaltung der Hilfeseiten als Stylesheet.

    Keine Farben außer der Fläche hinter Codeblöcken: die Schrift- und
    Hintergrundfarbe kommt vom Thema der IDE, und eine Vorlage, die
    sie festschriebe, sähe im jeweils anderen Thema falsch aus.

    Die Schriftstärke ist die eine Ausnahme, die vom Thema abhängt.
    Helle Schrift auf dunklem Grund wirkt dünner als dieselbe Schrift
    umgekehrt; 500 gleicht das aus, ohne fett zu wirken. Qt nimmt die
    Zwischenwerte an - nachgemessen ergeben 500 und 600 auch 500 und
    600 und nicht 700 wie „bold".
    """
    stufe = 500 if dunkel else 400
    # Die Fläche hinter Codeblöcken muss sich vom Grund abheben und
    # darf ihn in keinem Thema übertönen, deshalb zwei feste Werte.
    flaeche = "#2b3136" if dunkel else "#f2f4f6"
    rahmen = "#4a545c" if dunkel else "#d5dade"
    return f"""
        body {{ font-weight: {stufe}; line-height: {ZEILENABSTAND}%; }}
        p {{ line-height: {ZEILENABSTAND}%; margin-top: 8px; margin-bottom: 8px; }}
        li {{ line-height: {ZEILENABSTAND}%; margin-bottom: 4px; }}
        h1, h2, h3 {{ margin-top: 20px; margin-bottom: 8px; font-weight: 600; }}
        code {{ font-family: {code_schrift}; }}
        pre {{
            font-family: {code_schrift};
            background-color: {flaeche};
            border: 1px solid {rahmen};
            padding: 10px;
            margin-top: 10px;
            margin-bottom: 10px;
        }}
        table {{ border-collapse: collapse; margin-top: 10px; margin-bottom: 10px; }}
        th, td {{ border: 1px solid {rahmen}; padding: 5px 10px; }}
        th {{ font-weight: 600; }}
    """


class HilfeAnsicht(QTextBrowser):
    """Eine Hilfeseite aus Markdown. Nur lesen, nicht ändern."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setOpenExternalLinks(True)
        self.setReadOnly(True)
        self.document().setDocumentMargin(20)
        self._markdown = ""
        self._rand = -1

    def markdown_setzen(self, text: str) -> None:
        """Setzt den Inhalt aus Markdown.

        Der Umweg über HTML ist nötig, damit die Vorlage überhaupt
        greift: `document().setDefaultStyleSheet()` wirkt nur beim
        Einlesen von HTML, und `setMarkdown()` geht daran vorbei
        (nachgemessen - mit `setMarkdown` blieb alles bei Qts
        Vorgaben). Was Qt aus dem Markdown gemacht hat, übersteht den
        Umweg vollständig: Überschriften, Tabellen, Listen, Verweise
        und Codeblöcke sind danach alle noch da.
        """
        self._markdown = text
        zwischen = QTextDocument()
        zwischen.setMarkdown(text)
        self.document().setDefaultStyleSheet(
            stilvorlage(self._ist_dunkel(), code_schriftart())
        )
        self.setHtml(zwischen.toHtml())
        self._code_schrift_setzen()
        self._breite_begrenzen()

    def _ist_dunkel(self) -> bool:
        """Dunkles Thema? Gefragt wird die eigene Hintergrundfarbe und
        nicht die Einstellung: die Ansicht kennt die Einstellungen der
        IDE nicht, und ihre Farbe hat sie von dort ohnehin schon."""
        return self.palette().base().color().lightness() < 128

    def resizeEvent(self, ereignis) -> None:  # noqa: N802 - Qt-Name
        super().resizeEvent(ereignis)
        self._breite_begrenzen()

    def _breite_begrenzen(self) -> None:
        """Hält die Textspalte schmal genug zum Lesen.

        Über die Ränder des Sichtbereichs und nicht über `max-width`:
        Qts Rich-Text kennt die Angabe nicht. In einem breiten Fenster
        liefe der Text sonst über die ganze Breite, und bei 200
        Zeichen je Zeile findet niemand mehr den nächsten Zeilenanfang.

        Gerechnet wird mit der Breite des Widgets und nicht mit der
        des Sichtbereichs: `setViewportMargins()` ändert dessen
        Breite, das löst wieder `resizeEvent` aus, und die Rechnung
        liefe sich im Kreis, bis der Stapel überläuft. Der Vergleich
        mit dem zuletzt gesetzten Wert ist der zweite Riegel.
        """
        rand = max(0, (self.width() - HOECHSTBREITE) // 2)
        if rand == self._rand:
            return
        self._rand = rand
        self.setViewportMargins(rand, 0, rand, 0)

    def _code_schrift_setzen(self) -> None:
        """Ersetzt die Gattungsfamilie „monospace“ durch eine, die es
        wirklich gibt.

        Seit die Seiten über HTML eingelesen werden, steht
        `code { font-family: … }` in der Vorlage - und trotzdem
        bleibt dieser Durchlauf nötig. Nachgezählt an den
        Hilfeseiten, was die Vorlage allein übrig lässt:

            komponenten.md      673 Stellen auf „monospace"
            handbuch.md          61
            erste_schritte.md    25

        Qt schreibt beim Umwandeln von Markdown die Familie als
        Inline-Angabe in das Zeichenformat, und die gewinnt gegen die
        Vorlage. In einem kurzen Beispiel fällt das nicht auf, weil
        dort `<code>`-Elemente entstehen; in einer langen Seite mit
        Tabellen ist es die Regel.
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
