"""Startbild der IDE (M11, Abschnitt 4).

Was sieht jemand beim allerersten Start? Bisher: ein leeres graues
Feld. Wer Natter zum ersten Mal öffnet, findet weder die zehn
mitgelieferten Beispielprojekte noch einen Weg, selbst eines
anzulegen – beides steckt in Menüs, in die man erst hineinschauen
muss.

Das Startbild füllt genau diese Lücke. Es zeigt drei Dinge:

* **Zuletzt geöffnete Projekte** – der häufigste Fall in der zweiten
  Unterrichtsstunde
* **Neues Projekt** und **Projekt öffnen**
* **Die Beispielprojekte**, nach denen sonst niemand sucht

Ein Beispiel wird beim Öffnen **kopiert**, nicht an Ort und Stelle
geöffnet: in einer installierten Natter liegen die Beispiele im
Programmordner, und dort darf eine Schülerin nicht schreiben. Die
Kopie landet in ihrem eigenen Dokumente-Ordner, wo sie sie behält –
und wo ein zweiter Anlauf am nächsten Tag das Angefangene wiederfindet
statt es zu überschreiben.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QSettings, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ide.pfade import daten_ordner
from ide.shell.theme import STARTBILD_EINTRAG

#: Wie viele zuletzt geöffnete Projekte gemerkt werden. Mehr als acht
#: wären auf einem Schulrechner ohnehin nicht wiederzuerkennen.
ZULETZT_MAX = 8

#: Schlüssel in den Einstellungen.
ZULETZT_SCHLUESSEL = "projekt/zuletzt"

#: Wohin eine Kopie eines Beispielprojekts gelegt wird, relativ zum
#: Benutzerordner.
KOPIEN_ORDNER = Path("Documents") / "Natter"

#: Schriftgrößen als **Stylesheet**, nicht über `setFont()`.
#:
#: In der Sichtprüfung stand die Begrüßung genauso groß da wie der
#: Fließtext darunter, obwohl `setPointSize(+8)` gesetzt war: das
#: IDE-weite QSS (`ide_qss_erzeugen`) enthält eine `font-size`-Regel für
#: `QWidget`, und die gewinnt in Qt gegen ein einzelnes `setFont()`.
#: Derselbe Fund war in M7 schon einmal beim Quelltexteditor gemacht
#: worden - dort steht er als Kommentar in `theme.py`. `setBold()`
#: wirkt dagegen weiter, weil das QSS keine `font-weight` setzt.
_GRUSS_STIL = "font-size: 20pt; font-weight: bold;"
_UNTERTITEL_STIL = "font-size: 11pt;"
_UEBERSCHRIFT_STIL = "font-size: 11pt; font-weight: bold; padding-top: 6px;"

#: Die Einträge sollen wie Verweise aussehen, nicht wie Schaltflächen.
#: `setFlat(True)` allein genügt nicht - auch dagegen gewinnt die
#: QSS-Regel für `QPushButton`, und im Bild standen elf Kästen
#: untereinander, die wie gesperrte Eingabefelder wirkten.
#:
#: Hier steht nur, was von den Farben des Themas unabhängig ist. Das
#: Aussehen beim Darüberfahren steht im IDE-weiten QSS unter dem
#: Objektnamen `STARTBILD_EINTRAG` (`ide/shell/theme.py`), weil nur
#: dort die Farben des gerade eingestellten Themas bekannt sind.
#:
#: Ein reiner Zusatz von `text-decoration` genügte hier ausdrücklich
#: **nicht**: `background: transparent` von hier gewann gegen den
#: Akzent-Hintergrund der allgemeinen Hover-Regel, deren weiße Schrift
#: mangels eigener Farbe hier aber durchkam - übrig blieb weiße Schrift
#: auf weißem Grund (Nutzer-Feedback September 2026).
_EINTRAG_STIL = """
QPushButton {
    text-align: left;
    padding: 5px 8px;
    border: none;
    background: transparent;
}
"""


def beispielprojekte() -> list[Path]:
    """Die mitgelieferten Beispielprojekte, alphabetisch.

    Leer, wenn der Ordner fehlt – etwa in einem Bau, der ihn nicht
    mitgenommen hat. Das Startbild lässt den Abschnitt dann weg, statt
    auf einen leeren Bereich zu zeigen.
    """
    ordner = daten_ordner("beispielprojekte")
    if not ordner.is_dir():
        return []
    gefunden = [
        next(iter(unterordner.glob("*.natter")), None)
        for unterordner in sorted(ordner.iterdir())
        if unterordner.is_dir()
    ]
    return [pfad for pfad in gefunden if pfad is not None]


def zuletzt_geoeffnet(einstellungen: QSettings) -> list[Path]:
    """Die zuletzt geöffneten Projekte – ohne die, die es nicht mehr
    gibt. Ein Eintrag, der ins Leere zeigt, wäre schlimmer als keiner:
    man klickt darauf und bekommt eine Fehlermeldung."""
    roh = einstellungen.value(ZULETZT_SCHLUESSEL, [], type=list) or []
    pfade = [Path(eintrag) for eintrag in roh]
    return [pfad for pfad in pfade if pfad.exists()][:ZULETZT_MAX]


def zuletzt_merken(einstellungen: QSettings, pfad: Path) -> list[Path]:
    """Schiebt `pfad` an die erste Stelle der Liste."""
    pfad = Path(pfad).resolve()
    vorhanden = [
        eintrag
        for eintrag in zuletzt_geoeffnet(einstellungen)
        if eintrag.resolve() != pfad
    ]
    neu = [pfad, *vorhanden][:ZULETZT_MAX]
    einstellungen.setValue(ZULETZT_SCHLUESSEL, [str(eintrag) for eintrag in neu])
    return neu


def eindeutige_namen(pfade: list[Path]) -> list[str]:
    """Beschriftungen für die zuletzt geöffneten Projekte.

    Normalerweise der Projektordner. Heißen zwei Projekte gleich – in
    der Sichtprüfung standen zwei „Garten" untereinander, eine Kopie
    des Beispiels und das Original –, kommt der übergeordnete Ordner
    dazu. Zwei gleich beschriftete Einträge wären ein Ratespiel.
    """
    namen = [pfad.parent.name for pfad in pfade]
    return [
        f"{name}  ({pfad.parent.parent.name})" if namen.count(name) > 1 else name
        for name, pfad in zip(namen, pfade, strict=True)
    ]


def beispiel_kopieren(projektdatei: Path, ziel_wurzel: Path | None = None) -> Path:
    """Legt eine Arbeitskopie des Beispiels an und gibt dessen
    `.natter`-Datei zurück.

    Ein vorhandener Ordner wird **nicht** überschrieben – wer gestern
    am Beispiel „Ampel" gearbeitet hat, bekommt heute „Ampel 2" statt
    seine Arbeit zurückgesetzt.
    """
    quelle = Path(projektdatei).parent
    wurzel = Path(ziel_wurzel) if ziel_wurzel else Path.home() / KOPIEN_ORDNER
    wurzel.mkdir(parents=True, exist_ok=True)

    ziel = wurzel / quelle.name
    nummer = 2
    while ziel.exists():
        ziel = wurzel / f"{quelle.name} {nummer}"
        nummer += 1

    shutil.copytree(
        quelle, ziel, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
    )
    return ziel / Path(projektdatei).name


class _Abschnitt(QWidget):
    """Eine Überschrift mit einer Reihe von Knöpfen darunter."""

    def __init__(self, titel: str, eltern: QWidget | None = None) -> None:
        super().__init__(eltern)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 12)
        self._layout.setSpacing(4)

        ueberschrift = QLabel(titel)
        ueberschrift.setStyleSheet(_UEBERSCHRIFT_STIL)
        self._layout.addWidget(ueberschrift)

    def knopf_hinzufuegen(
        self, text: str, tooltip: str, rueckruf: Callable[[], None]
    ) -> QPushButton:
        knopf = QPushButton(text)
        knopf.setToolTip(tooltip)
        knopf.setFlat(True)
        knopf.setCursor(Qt.CursorShape.PointingHandCursor)
        # Der Objektname holt die theme-abhängigen Farben aus dem
        # IDE-weiten QSS dazu - siehe `_EINTRAG_STIL`.
        knopf.setObjectName(STARTBILD_EINTRAG)
        knopf.setStyleSheet(_EINTRAG_STIL)
        knopf.clicked.connect(lambda *_: rueckruf())
        self._layout.addWidget(knopf)
        return knopf


class Startbild(QScrollArea):
    """Das Startbild. Meldet jede Auswahl über ein Signal – es kennt
    weder das Hauptfenster noch den Projektlader."""

    #: Ein zuletzt geöffnetes Projekt bzw. ein per „Öffnen" gewähltes
    projekt_gewaehlt = Signal(Path)
    #: Ein Beispielprojekt (die `.natter` im mitgelieferten Ordner)
    beispiel_gewaehlt = Signal(Path)
    neues_projekt_gewuenscht = Signal()
    projekt_oeffnen_gewuenscht = Signal()
    erste_schritte_gewuenscht = Signal()

    def __init__(
        self, einstellungen: QSettings, eltern: QWidget | None = None
    ) -> None:
        super().__init__(eltern)
        self._einstellungen = einstellungen
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.knoepfe: dict[str, QPushButton] = {}
        self.aufbauen()

    def aufbauen(self) -> None:
        """Baut den Inhalt neu – nach jedem geöffneten Projekt, damit
        die Liste der zuletzt geöffneten stimmt."""
        inhalt = QWidget()
        layout = QVBoxLayout(inhalt)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(0)
        self.knoepfe = {}

        gruss = QLabel("Willkommen bei Natter")
        gruss.setStyleSheet(_GRUSS_STIL)
        layout.addWidget(gruss)

        untertitel = QLabel(
            "Programmieren in Python – mit der Oberfläche, die du aus "
            "Lazarus kennst."
        )
        untertitel.setStyleSheet(_UNTERTITEL_STIL)
        layout.addWidget(untertitel)
        layout.addSpacing(24)

        layout.addWidget(self._abschnitt_anfangen())
        zuletzt = self._abschnitt_zuletzt()
        if zuletzt is not None:
            layout.addWidget(zuletzt)
        beispiele = self._abschnitt_beispiele()
        if beispiele is not None:
            layout.addWidget(beispiele)

        layout.addStretch(1)
        self.setWidget(inhalt)

    def _abschnitt_anfangen(self) -> _Abschnitt:
        abschnitt = _Abschnitt("Anfangen")
        self.knoepfe["neues_projekt"] = abschnitt.knopf_hinzufuegen(
            "Neues Projekt …",
            "Legt einen Ordner mit Formular, Unit und Startdatei an",
            self.neues_projekt_gewuenscht.emit,
        )
        self.knoepfe["projekt_oeffnen"] = abschnitt.knopf_hinzufuegen(
            "Projekt öffnen …",
            "Öffnet eine vorhandene .natter-Datei",
            self.projekt_oeffnen_gewuenscht.emit,
        )
        self.knoepfe["erste_schritte"] = abschnitt.knopf_hinzufuegen(
            "Erste Schritte",
            "Kurze Anleitung: vom leeren Projekt zum laufenden Programm",
            self.erste_schritte_gewuenscht.emit,
        )
        return abschnitt

    def _abschnitt_zuletzt(self) -> _Abschnitt | None:
        zuletzt = zuletzt_geoeffnet(self._einstellungen)
        if not zuletzt:
            return None
        abschnitt = _Abschnitt("Zuletzt geöffnet")
        for pfad, beschriftung in zip(
            zuletzt, eindeutige_namen(zuletzt), strict=True
        ):
            self.knoepfe[f"zuletzt:{pfad.parent.name}"] = abschnitt.knopf_hinzufuegen(
                beschriftung,
                str(pfad),
                lambda p=pfad: self.projekt_gewaehlt.emit(p),
            )
        return abschnitt

    def _abschnitt_beispiele(self) -> _Abschnitt | None:
        beispiele = beispielprojekte()
        if not beispiele:
            return None
        abschnitt = _Abschnitt("Beispiele zum Ausprobieren")
        for pfad in beispiele:
            self.knoepfe[f"beispiel:{pfad.parent.name}"] = abschnitt.knopf_hinzufuegen(
                pfad.parent.name,
                "Wird in deinen Dokumente-Ordner kopiert und dort geöffnet",
                lambda p=pfad: self.beispiel_gewaehlt.emit(p),
            )
        return abschnitt
