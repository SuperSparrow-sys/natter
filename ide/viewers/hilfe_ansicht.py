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

from pathlib import Path

from PySide6.QtWidgets import QTextBrowser, QWidget


class HilfeAnsicht(QTextBrowser):
    """Eine Hilfeseite aus Markdown. Nur lesen, nicht ändern."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setOpenExternalLinks(True)
        self.setReadOnly(True)

    def markdown_setzen(self, text: str) -> None:
        """Setzt den Inhalt aus Markdown."""
        self.setMarkdown(text)

    def datei_laden(self, pfad: Path | str) -> bool:
        """Lädt eine `.md`-Datei. Liefert `False`, wenn es sie nicht
        gibt – der Aufrufer sagt dann, wo sie liegen müsste."""
        pfad = Path(pfad)
        if not pfad.exists():
            return False
        self.markdown_setzen(pfad.read_text(encoding="utf-8"))
        return True
