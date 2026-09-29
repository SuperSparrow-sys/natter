"""HTML-Vorschau (Abschnitt 11.3): zeigt eine `.html`-Datei an, mit
automatischer Aktualisierung beim Speichern und „Im Browser öffnen“.

Rendert über `QTextBrowser` (einfaches HTML/CSS) statt einer vollen
Web-Engine – QtWebEngine hätte rund 100 MB gekostet, siehe
`docs/bericht.md`, Abschnitt 4; für die im Kurs erzeugten,
einfachen HTML-Seiten (Abschnitt 11.3-Beispiel: Überschrift, Text,
Tabellen) reicht das.
"""

from __future__ import annotations

import html
import os
from pathlib import Path

from PySide6.QtCore import QFileSystemWatcher, QUrl
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QTextBrowser, QVBoxLayout, QWidget

from ide.viewers.ordnergrenze import (
    NurAusDemOrdner,
    grenze_waehlen,
    pfad_im_ordner,
    text_lesen,
    verweis_meldung,
)
from pcl import open_url


def _ist_seite(pfad: Path) -> bool:
    """Ob die Vorschau `pfad` als Seite zeigen kann."""
    return pfad.suffix.lower() in (".html", ".htm") and pfad.is_file()


class _VorschauBrowser(NurAusDemOrdner, QTextBrowser):
    """Lädt Bilder nur aus dem Ordner, den `ordnergrenze` erlaubt."""


class HtmlVorschau(QWidget):
    """Vorschau-Tab für `.html`-Dateien (Abschnitt 11.3): lädt sich
    automatisch neu, sobald sich die Datei auf der Festplatte ändert.

    `projektordner` ist der Ordner des geöffneten Projekts, falls eins
    offen ist. Liegt die Datei darin, dürfen Bilder und Verweise
    überall ins Projekt zeigen, sonst nur in den Ordner der Datei
    (siehe `ordnergrenze`)."""

    def __init__(
        self,
        pfad: Path,
        parent: QWidget | None = None,
        projektordner: Path | None = None,
    ) -> None:
        super().__init__(parent)
        # Nur am Text vervollständigt: der Vergleich mit einem Verweis
        # in `_verweis_geklickt` braucht dieselbe Schreibweise, und
        # `resolve()` fragte einen Netzpfad schon an.
        self._pfad = Path(os.path.normpath(os.path.abspath(pfad)))
        self._grenze = grenze_waehlen(self._pfad, projektordner)
        # Die gerade gezeigte Seite. Anfangs die geöffnete Datei, nach
        # einem Verweis eine andere Seite innerhalb der Grenze.
        self._seite = self._pfad

        self._browser = _VorschauBrowser()
        # Verweise entscheidet `_verweis_geklickt`. Mit
        # `setOpenExternalLinks(True)` ging jedes Schema außer `file`
        # und `qrc` an Windows, auch `ms-settings:` oder ein Schema, das
        # ein installiertes Programm angemeldet hat. Eine HTML-Datei aus
        # fremder Hand hätte so mit einem Klick ein Programm gestartet.
        self._browser.setOpenExternalLinks(False)
        self._browser.setOpenLinks(False)
        self._browser.anchorClicked.connect(self._verweis_geklickt)

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
        self._seite_zeigen(self._pfad)
        # Manche Editoren ersetzen die Datei beim Speichern statt sie
        # in-place zu schreiben - QFileSystemWatcher verliert dabei die
        # Beobachtung; erneutes Hinzufügen ist ein No-op, wenn der Pfad
        # schon beobachtet wird.
        if str(self._pfad) not in self._beobachter.files():
            self._beobachter.addPath(str(self._pfad))

    def _seite_zeigen(self, seite: Path, marke: str = "") -> None:
        """Zeigt eine Seite und merkt sie sich als Bezug für relative
        Verweise. Geladen wird jede Seite mit `setHtml`, auch die
        zweite und dritte: nach `setSource` löste `QTextBrowser` jeden
        Verweis selbst zu einer `file`-Adresse auf, und `setHtml`
        setzt diese Quelle nicht zurück. So kommen Verweise immer so
        an, wie sie in der Datei stehen.

        Bilder lädt der Browser nur aus dem Ordner in `_grenze`;
        relative Pfade gelten ab dieser Seite. Fehlt die Datei
        (gelöscht oder umbenannt, während die Vorschau offen ist),
        steht ein Hinweis in der Vorschau."""
        self._seite = seite
        self._browser.ordner_setzen(self._grenze, seite.parent)
        try:
            text = text_lesen(seite)
        except OSError as fehler:
            self._browser.setHtml(
                f"<p><b>„{html.escape(seite.name)}“ lässt sich nicht "
                f"lesen:</b> {html.escape(str(fehler))}</p>"
            )
            return
        self._browser.setHtml(text)
        if marke:
            self._browser.scrollToAnchor(marke)

    def _verweis_geklickt(self, adresse: QUrl) -> None:
        """Internetadressen und `mailto` gehen an den Browser, eine
        Sprungmarke bleibt in der Vorschau, eine HTML-Datei innerhalb
        der Grenze wird in der Vorschau angezeigt. Alles andere wird
        abgewiesen, mit denselben Sätzen wie in der Markdown-Ansicht:
        aus der Grenze hinaus, Datei fehlt, keine HTML-Seite."""
        if adresse.scheme() in ("http", "https", "mailto"):
            open_url(adresse.toString())
            return

        ziel = self._lokales_ziel(adresse)
        if ziel is not None:
            marke = adresse.fragment()
            if ziel == self._seite:
                if marke:
                    self._browser.scrollToAnchor(marke)
                return
            if _ist_seite(ziel):
                self._seite_zeigen(ziel, marke)
                return

        meldung = verweis_meldung(
            adresse, ziel, self._grenze, self._seite, _ist_seite
        )
        if ziel is not None and ziel.is_file() and not _ist_seite(ziel):
            # Eine PDF oder ein Bild zeigt der Browser, und aus der
            # Seite dort heraus öffnet der Verweis auch.
            meldung += (
                " Mit „Im Browser öffnen“ lässt sich die Seite samt "
                "Verweis im Browser ansehen."
            )
        self._melden(meldung)

    def _lokales_ziel(self, adresse: QUrl) -> Path | None:
        """Die Datei, auf die ein Verweis zeigt, oder `None`, wenn er
        aus dem Ordner in `_grenze` hinausführt. Ein relativer Pfad
        gilt ab der gerade gezeigten Seite, ein leerer Pfad (nur eine
        Sprungmarke) meint diese Seite selbst. Geprüft wird nur am
        Text, siehe `ordnergrenze`; ein Netzpfad wird so gar nicht erst
        angefragt."""
        if not adresse.scheme() and not adresse.host() and not adresse.path():
            return self._seite
        return pfad_im_ordner(adresse, self._grenze, self._seite.parent)

    def _melden(self, text: str) -> None:
        """Eine Zeile in die Statusleiste, sofern es eine gibt."""
        fenster = self.window()
        statusleiste = getattr(fenster, "statusBar", None)
        if statusleiste is not None:
            statusleiste().showMessage(text)

    def _im_browser_oeffnen(self) -> None:
        open_url(str(self._seite))
