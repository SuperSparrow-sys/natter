"""HTML-Vorschau (Abschnitt 11.3): zeigt eine `.html`-Datei an, mit
automatischer Aktualisierung beim Speichern und „Im Browser öffnen“.

Rendert über `QTextBrowser` (einfaches HTML/CSS) statt eines vollen
Web-Engines – die Monaco/QtWebEngine-Entscheidung aus `prototypes/s2`
ist noch offen (siehe docs/PLAN.md); für die im Kurs erzeugten,
einfachen HTML-Seiten (Abschnitt 11.3-Beispiel: Überschrift, Text,
Tabellen) reicht das.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QFileSystemWatcher
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QTextBrowser, QVBoxLayout, QWidget

from pcl import open_url


class HtmlVorschau(QWidget):
    """Vorschau-Tab für `.html`-Dateien (Abschnitt 11.3): lädt sich
    automatisch neu, sobald sich die Datei auf der Festplatte ändert."""

    def __init__(self, pfad: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pfad = Path(pfad)

        self._browser = QTextBrowser()
        self._browser.setOpenExternalLinks(True)

        self._browser_oeffnen_knopf = QPushButton("Im Browser öffnen")
        self._browser_oeffnen_knopf.clicked.connect(self._im_browser_oeffnen)

        werkzeugleiste = QHBoxLayout()
        werkzeugleiste.addStretch()
        werkzeugleiste.addWidget(self._browser_oeffnen_knopf)

        layout = QVBoxLayout(self)
        layout.addLayout(werkzeugleiste)
        layout.addWidget(self._browser)

        self._beobachter = QFileSystemWatcher([str(self._pfad)])
        self._beobachter.fileChanged.connect(self._neu_laden)

        self._neu_laden()

    @property
    def browser(self) -> QTextBrowser:
        return self._browser

    def _neu_laden(self) -> None:
        self._browser.setSearchPaths([str(self._pfad.parent)])
        self._browser.setHtml(self._pfad.read_text(encoding="utf-8"))
        # Manche Editoren ersetzen die Datei beim Speichern statt sie
        # in-place zu schreiben - QFileSystemWatcher verliert dabei die
        # Beobachtung; erneutes Hinzufügen ist ein No-op, wenn der Pfad
        # schon beobachtet wird.
        if str(self._pfad) not in self._beobachter.files():
            self._beobachter.addPath(str(self._pfad))

    def _im_browser_oeffnen(self) -> None:
        open_url(str(self._pfad))
