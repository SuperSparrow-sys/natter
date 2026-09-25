"""Startbild der IDE (M11, Abschnitt 4).

Was sieht jemand beim allerersten Start? Bisher: ein leeres graues
Feld. Wer Natter zum ersten Mal öffnet, findet keinen Weg, ein
Projekt anzulegen – das steckt in einem Menü, in das man erst
hineinschauen muss.

Das Startbild füllt diese Lücke. Es zeigt zwei Dinge:

* Neues Projekt und Projekt öffnen
* Zuletzt geöffnete Projekte – der häufigste Fall in der zweiten
  Unterrichtsstunde

Die neun Beispielprojekte standen zunächst als dritter Abschnitt hier
und stehen seit September 2026 unter „Datei → Beispielprojekte“: auf
der Arbeitsfläche waren sie im Weg, im Menü stehen sie dort, wo auch
sonst gesucht wird.

Ein Beispiel wird beim Öffnen kopiert, nicht an Ort und Stelle
geöffnet: in einer installierten Natter liegen die Beispiele im
Programmordner, und dort darf eine Schülerin nicht schreiben. Die
Kopie landet in ihrem eigenen Dokumente-Ordner, wo sie sie behält –
und wo ein zweiter Anlauf am nächsten Tag das Angefangene wiederfindet
statt es zu überschreiben. Wo dieser Ordner liegt, sagt Windows
selbst; geraten hatte Natter ihn bis September 2026 falsch (siehe
`ide/pfade.py`).
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

from ide.pfade import (
    NATTER_ORDNER,
    beispielkopien_ordner,
    daten_ordner,
    natter_ordner,
)
from ide.shell.theme import STARTBILD_EINTRAG
from pcl.pruefungsmodus import laeuft as pruefungsmodus_laeuft

#: Wie viele zuletzt geöffnete Projekte gemerkt werden. Mehr als acht
#: wären auf einem Schulrechner ohnehin nicht wiederzuerkennen.
ZULETZT_MAX = 8

#: Schlüssel in den Einstellungen.
ZULETZT_SCHLUESSEL = "projekt/zuletzt"

#: Wohin eine Arbeitskopie gehört, unterhalb des Dokumente-Ordners.
#: Der wird bei Windows erfragt und nicht geraten - warum, steht in
#: `ide/pfade.py`.
KOPIEN_ORDNER = NATTER_ORDNER

#: Schriftgrößen als Stylesheet, nicht über `setFont()`.
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
#: nicht: `background: transparent` von hier gewann gegen den
#: Akzent-Hintergrund der allgemeinen Hover-Regel, deren weiße Schrift
#: mangels eigener Farbe hier aber durchkam - übrig blieb weiße Schrift
#: auf weißem Grund (gemeldet).
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


#: Was beim Kopieren eines Beispiels liegen bleibt. Übersetzter
#: Python-Code gehört zu dem Rechner, auf dem er entstand.
_NICHT_MITKOPIEREN = shutil.ignore_patterns("__pycache__", "*.pyc")


def ist_beispiel_original(pfad: Path) -> bool:
    """Ob `pfad` im Ordner der mitgelieferten Beispiele liegt.

    Ein Original wird nie an Ort und Stelle geöffnet. In einer
    installierten Natter liegt es im Programmordner, in den eine
    Schülerin nicht schreiben darf, und im Entwicklungsbaum ist es eine
    eingecheckte Datei.
    """
    ordner = daten_ordner("beispielprojekte").resolve()
    return Path(pfad).resolve().is_relative_to(ordner)


def beispiel_original(projekt_ordner: Path) -> Path | None:
    """Der Ordner des Beispiels, von dem `projekt_ordner` eine Kopie
    ist - oder `None` für ein eigenes Projekt und für das Original
    selbst.

    Erkannt wird eine Kopie an ihrer Projektdatei und nicht am
    Ordnernamen: ein eigenes Projekt kann zufällig „04_CookieKlicker"
    heißen, und eine Kopie aus der Zeit, als jedes Öffnen eine neue
    anlegte, heißt „08_Regression 2".
    """
    projekt_ordner = Path(projekt_ordner)
    if ist_beispiel_original(projekt_ordner):
        return None
    eigene = {datei.name for datei in projekt_ordner.glob("*.natter")}
    for projektdatei in beispielprojekte():
        if projektdatei.name in eigene:
            return projektdatei.parent
    return None


def beispiel_kopieren(projektdatei: Path, ziel_wurzel: Path | None = None) -> Path:
    """Gibt die Arbeitskopie des Beispiels zurück und legt sie an, wenn
    es noch keine gibt.

    Eine vorhandene Kopie wird weiterbenutzt. Früher entstand bei
    jedem Öffnen eine neue daneben - „Ampel 2", „Ampel 3" -, damit die
    Arbeit von gestern nicht überschrieben wird. Überschrieben wurde sie
    nicht, aber geöffnet wurde eine frische Kopie, und die Arbeit lag
    unbemerkt im Ordner nebenan. Wer von vorn anfangen will, nimmt
    „Datei → Beispielprojekte → Auf Original zurücksetzen …".

    Nummeriert wird nur noch, wenn ein fremder Ordner den Namen schon
    belegt, etwa ein eigenes Projekt, das zufällig so heißt.

    Ohne `ziel_wurzel` liegen die Kopien unter
    `Dokumente/Natter/Beispielprojekte`, getrennt von den eigenen
    Projekten.
    """
    projektdatei = Path(projektdatei)
    quelle = projektdatei.parent
    wurzel = Path(ziel_wurzel) if ziel_wurzel else beispielkopien_ordner()

    # Liegt das Entwicklungsverzeichnis unter `Dokumente/Natter`, ist
    # `Natter/Beispielprojekte` der Ordner der Originale, denn Windows
    # unterscheidet keine Groß- und Kleinschreibung. Die Suche nach
    # einer vorhandenen Kopie fände dann das Original selbst, und es
    # würde an Ort und Stelle geöffnet.
    if ist_beispiel_original(wurzel):
        raise ValueError(
            f"Die Kopien der Beispiele würden bei den Originalen landen ({wurzel})."
        )
    if ziel_wurzel is None:
        _alte_kopie_umziehen(projektdatei, wurzel)
    wurzel.mkdir(parents=True, exist_ok=True)

    ziel = wurzel / quelle.name
    nummer = 2
    while ziel.exists():
        if (ziel / projektdatei.name).exists():
            return ziel / projektdatei.name
        ziel = wurzel / f"{quelle.name} {nummer}"
        nummer += 1

    shutil.copytree(quelle, ziel, ignore=_NICHT_MITKOPIEREN)
    return ziel / projektdatei.name


def _alte_kopie_umziehen(projektdatei: Path, wurzel: Path) -> None:
    """Holt eine Kopie von ihrem früheren Platz unter `wurzel`.

    Bis Fassung 0.3.1 lagen die Kopien direkt unter
    `Dokumente/Natter`, zwischen den eigenen Projekten. Wer dort
    gearbeitet hat, findet seine Arbeit nach dem Update am neuen Ort
    wieder. Umgezogen wird nur, was an seiner Projektdatei als Kopie zu
    erkennen ist, und nur, solange am neuen Ort noch keine liegt.
    """
    alt = natter_ordner() / projektdatei.parent.name
    neu = wurzel / projektdatei.parent.name
    if not (alt / projektdatei.name).exists() or neu.exists():
        return
    wurzel.mkdir(parents=True, exist_ok=True)
    shutil.move(alt, neu)


def beispiel_zuruecksetzen(projekt_ordner: Path) -> Path:
    """Setzt die Kopie eines Beispiels auf den Auslieferungszustand
    zurück und gibt ihre Projektdatei zurück.

    Der Inhalt des Ordners wird ersetzt, der Ordner selbst bleibt. So
    zeigt „Zuletzt geöffnet" danach auf dasselbe Projekt, und es
    entsteht kein weiterer Ordner.

    Für ein eigenes Projekt gibt es kein Original. Dann wird nichts
    gelöscht, sondern ein `ValueError` geworfen - diese Funktion räumt
    einen Ordner leer, und das darf nur geschehen, wenn feststeht, was
    danach wieder hineinkommt.
    """
    projekt_ordner = Path(projekt_ordner)
    original = beispiel_original(projekt_ordner)
    if original is None:
        raise ValueError(f"{projekt_ordner} ist keine Kopie eines Beispiels.")

    for eintrag in projekt_ordner.iterdir():
        if eintrag.is_dir():
            shutil.rmtree(eintrag)
        else:
            eintrag.unlink()
    shutil.copytree(
        original, projekt_ordner, ignore=_NICHT_MITKOPIEREN, dirs_exist_ok=True
    )
    return next(projekt_ordner.glob("*.natter"))


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
    neues_projekt_gewuenscht = Signal()
    projekt_oeffnen_gewuenscht = Signal()
    erste_schritte_gewuenscht = Signal()
    #: „Zurück zum Projekt“ - erscheint nur, wenn es eines gibt,
    #: zu dem sich zurückkehren lässt.
    zurueck_gewuenscht = Signal()

    def __init__(
        self, einstellungen: QSettings, eltern: QWidget | None = None
    ) -> None:
        super().__init__(eltern)
        self._einstellungen = einstellungen
        #: Name des offenen Projekts, oder `None`. Steht auf dem Knopf,
        #: mit dem es zurück in die Arbeit geht.
        self.offenes_projekt: str | None = None
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
            "Oberfläche entwerfen, Code schreiben, Programm starten."
        )
        untertitel.setStyleSheet(_UNTERTITEL_STIL)
        layout.addWidget(untertitel)
        layout.addSpacing(24)

        layout.addWidget(self._abschnitt_anfangen())
        zuletzt = self._abschnitt_zuletzt()
        if zuletzt is not None:
            layout.addWidget(zuletzt)
        layout.addStretch(1)
        self.setWidget(inhalt)

    def _abschnitt_anfangen(self) -> _Abschnitt:
        abschnitt = _Abschnitt("Anfangen")
        if self.offenes_projekt:
            # Ganz oben und als Erstes: wer über „Ansicht → Startseite“
            # hierher gekommen ist, will meistens gleich wieder zurück.
            # Ohne diesen Knopf gäbe es dafür keinen sichtbaren Weg -
            # das Startbild verdeckt die Reiter, solange es steht.
            self.knoepfe["zurueck"] = abschnitt.knopf_hinzufuegen(
                f"Zurück zu „{self.offenes_projekt}“",
                "Zeigt wieder die geöffneten Dateien",
                self.zurueck_gewuenscht.emit,
            )
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
        """Die zuletzt geöffneten Projekte - außer im Prüfungsmodus.

        Die Liste führt zu dem, was in der Stunde davor bearbeitet
        wurde, in einer Klausur also möglicherweise zur Lösung der
        Aufgabe, die gerade gestellt ist. Sie fällt deshalb weg,
        solange geprüft wird.
        """
        if pruefungsmodus_laeuft():
            return None
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
