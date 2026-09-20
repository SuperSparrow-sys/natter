"""Markdown-Ansicht (Abschnitt 11.6): zeigt eine `.md`-Datei gesetzt
an statt als Rohtext.

Bis September 2026 landete jede `.md`-Datei im **Quelltexteditor**.
Wer die `README.md` eines Beispielprojekts anklickte, bekam
`## Überschrift`, `**fett**` und Tabellen aus Strichen und
Senkrechtstrichen zu sehen - in einem Fenster mit Zeilennummern und
Syntaxhervorhebung, das nach Programmieren aussieht. Genau dieselbe
Beobachtung hatte in M11 schon zur `HilfeAnsicht` geführt; die galt
aber nur für die vier eingebauten Hilfeseiten, nicht für eine Datei,
die jemand selbst öffnet.

Der Unterschied zur `HilfeAnsicht`: eine Hilfeseite ist fertig und
gehört Natter, eine `.md`-Datei im Projekt gehört dem Schüler. Deshalb
steht hier ein Knopf **„Quelltext bearbeiten"** daneben, und die
Ansicht lädt sich neu, sobald die Datei sich ändert - wer im Editor
schreibt und zurückwechselt, sieht das Ergebnis.

Gerendert wird mit `QTextBrowser.setMarkdown` (GitHub-Dialekt:
Überschriften, Listen, Tabellen, Code-Blöcke, Links, Bilder). Kein
Web-Engine - für Anleitungen und Projektbeschreibungen reicht das, und
die Entscheidung gegen QtWebEngine steht seit `HtmlVorschau`.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QFileSystemWatcher, QUrl, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ide.viewers.hilfe_ansicht import HilfeAnsicht
from pcl import open_url

#: Was als Markdown gilt. `.markdown` kommt selten vor, kostet aber
#: nichts - und wer eine so benannte Datei anklickt, meint dasselbe.
MARKDOWN_ENDUNGEN = {".md", ".markdown"}

#: Wie viele Zeilen am Anfang nach der Überschrift abgesucht werden.
#: Genug für eine Kopfzeile aus Metadaten, wenig genug, um bei einer
#: Datei ohne Überschrift nicht das ganze Dokument zu lesen.
_ZEILEN_FUER_TITEL = 20


def ueberschrift_lesen(text: str) -> str | None:
    """Die erste `#`-Überschrift, oder `None`.

    Der Reiter trägt sie statt des Dateinamens. Zwei Reiter mit der
    Aufschrift „README.md" - einer gesetzt, einer als Quelltext - sind
    nicht auseinanderzuhalten; „Obstsortierer" und „README.md" schon.
    """
    for zeile in text.splitlines()[:_ZEILEN_FUER_TITEL]:
        nackt = zeile.strip()
        if nackt.startswith("# "):
            return nackt[2:].strip() or None
    return None


class MarkdownAnsicht(QWidget):
    """Betrachter-Reiter für eine `.md`-Datei.

    `datei_angefordert` wird ausgelöst, wenn jemand im Text auf einen
    Verweis zu einer anderen Datei des Projekts klickt; das Hauptfenster
    öffnet sie dann in der Ansicht, die dazu passt. Ohne das führte ein
    Verweis auf `u_main.py` entweder ins Leere oder - schlimmer - an
    Windows vorbei in irgendein fremdes Programm.

    `bearbeiten_angefordert` trägt denselben Pfad und hängt am Knopf
    „Quelltext bearbeiten".
    """

    datei_angefordert = Signal(Path)
    bearbeiten_angefordert = Signal(Path)

    def __init__(self, pfad: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pfad = Path(pfad)

        self._ansicht = HilfeAnsicht()
        # `HilfeAnsicht` überlässt Links dem Browser. Hier nicht: ein
        # Verweis auf eine Nachbardatei soll in Natter aufgehen, nicht
        # in Windows. Was wohin gehört, entscheidet `_verweis_geklickt`.
        self._ansicht.setOpenExternalLinks(False)
        self._ansicht.setOpenLinks(False)
        self._ansicht.anchorClicked.connect(self._verweis_geklickt)

        self._titel = QLabel(self._pfad.name)
        self._bearbeiten_knopf = QPushButton("Quelltext bearbeiten")
        self._bearbeiten_knopf.setToolTip(
            "Öffnet die Datei zusätzlich im Editor. Diese Ansicht "
            "aktualisiert sich, sobald du dort speicherst."
        )
        self._bearbeiten_knopf.clicked.connect(
            lambda: self.bearbeiten_angefordert.emit(self._pfad)
        )

        werkzeugleiste = QHBoxLayout()
        werkzeugleiste.addWidget(self._titel)
        werkzeugleiste.addStretch()
        werkzeugleiste.addWidget(self._bearbeiten_knopf)

        layout = QVBoxLayout(self)
        layout.addLayout(werkzeugleiste)
        layout.addWidget(self._ansicht)

        self._beobachter = QFileSystemWatcher([str(self._pfad)])
        self._beobachter.fileChanged.connect(self._neu_laden)

        self._neu_laden()

    @property
    def ansicht(self) -> HilfeAnsicht:
        return self._ansicht

    @property
    def pfad(self) -> Path:
        return self._pfad

    def text(self) -> str:
        """Der gesetzte Text ohne Auszeichnung - für Tests und für die
        Suche."""
        return self._ansicht.toPlainText()

    def _neu_laden(self) -> None:
        """Liest die Datei neu ein.

        Der Suchpfad muss **vor** dem Setzen stehen: `![Bild](bild.png)`
        ist relativ zur `.md`-Datei, nicht zum Arbeitsverzeichnis von
        Natter. Ohne ihn blieb an der Stelle ein leerer Kasten.
        """
        self._ansicht.setSearchPaths([str(self._pfad.parent)])
        try:
            text = self._pfad.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Eine von Hand angelegte Datei kann in der
            # Windows-Codepage geschrieben sein. Lieber mit falschen
            # Umlauten anzeigen als den Reiter leer lassen.
            text = self._pfad.read_text(encoding="cp1252", errors="replace")
        except OSError as fehler:
            self._ansicht.markdown_setzen(
                f"**„{self._pfad.name}“ lässt sich nicht lesen:** {fehler}"
            )
            return

        self._ansicht.markdown_setzen(text)
        # Manche Editoren ersetzen die Datei beim Speichern, statt sie
        # zu überschreiben - `QFileSystemWatcher` verliert dabei die
        # Beobachtung. Erneutes Hinzufügen ist folgenlos, wenn der Pfad
        # schon beobachtet wird.
        if str(self._pfad) not in self._beobachter.files():
            self._beobachter.addPath(str(self._pfad))

    def _verweis_geklickt(self, adresse: QUrl) -> None:
        """Entscheidet, wohin ein angeklickter Verweis führt.

        Drei Fälle, und alle drei kommen in den mitgelieferten Texten
        vor: eine Internetadresse gehört in den Browser, eine Sprungmarke
        (`#abschnitt`) bleibt in dieser Ansicht, und ein Verweis auf eine
        Datei daneben - `docs/komponenten.md`, `u_main.py` - gehört nach
        Natter.
        """
        if adresse.scheme() in ("http", "https", "mailto"):
            open_url(adresse.toString())
            return

        marke = adresse.fragment()
        ziel_text = adresse.path()
        if not ziel_text and marke:
            self._ansicht.scrollToAnchor(marke)
            return

        ziel = (self._pfad.parent / ziel_text).resolve()
        if ziel.is_file():
            self.datei_angefordert.emit(ziel)
            return

        self._melden(f"„{ziel_text}“ gibt es neben „{self._pfad.name}“ nicht.")

    def _melden(self, text: str) -> None:
        """Eine Zeile in die Statusleiste, sofern es eine gibt.

        In einem Test hängt die Ansicht an keinem Hauptfenster; dann
        soll ein ins Leere führender Verweis trotzdem nicht abstürzen.
        """
        fenster = self.window()
        statusleiste = getattr(fenster, "statusBar", None)
        if statusleiste is not None:
            statusleiste().showMessage(text)
