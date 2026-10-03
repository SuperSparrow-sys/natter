"""Erzeugten Quelltext anzeigen und ablegen (M9 Schritt 13 und 14).

Zwei Dinge in einer Datei, weil sie zusammengehören: die Rückfrage
nach Ziel und Umfang, und das Fenster, das den erzeugten Code zeigt.
Beide werden von der Klassen- und der Struktogramm-Ausgabe benutzt.

Das Fenster ist bewusst nur lesbar: es ist eine Vorlage zum
Übernehmen, kein zweiter Editor. Wer daran weiterarbeiten will, kopiert
den Text oder speichert ihn und öffnet ihn im richtigen Editor – sonst
entstünde eine zweite Stelle, an der Quelltext lebt.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, Signal
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ide.atomar import atomar_schreiben
from ide.diagramm import fenstergroesse
from ide.shell.quelltexteditor import QuelltextEditor
from pcl.theme import theme_aufloesen

_GROESSE_SCHLUESSEL = "diagramm/quelltextfenstergroesse"

ZIELE =(("fenster", "In einem Fenster anzeigen"), ("datei", "In eine Datei schreiben"))
UMFAENGE = (("auswahl", "Nur die Auswahl"), ("alles", "Alles"))


def _einstellungen() -> QSettings:
    return QSettings(
        QSettings.Format.IniFormat, QSettings.Scope.UserScope, "Natter", "Natter-IDE"
    )


class CodeOptionenDialog(QDialog):
    """Fragt Ziel und Umfang. Die Wahl wird gemerkt, damit man sie nicht
    bei jedem Mal neu treffen muss."""

    def __init__(self, eltern: QWidget | None = None, umfang_text: str = "Umfang") -> None:
        super().__init__(eltern)
        self.setWindowTitle("Quelltext erzeugen")

        self.ziel = QComboBox()
        for wert, text in ZIELE:
            self.ziel.addItem(text, wert)
        self.umfang = QComboBox()
        for wert, text in UMFAENGE:
            self.umfang.addItem(text, wert)

        gemerkt = _einstellungen()
        self._auswaehlen(self.ziel, gemerkt.value("diagramm/code_ziel", "fenster"))
        self._auswaehlen(self.umfang, gemerkt.value("diagramm/code_umfang", "alles"))

        knoepfe = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        knoepfe.accepted.connect(self.accept)
        knoepfe.rejected.connect(self.reject)

        formular = QFormLayout()
        formular.addRow("Ziel:", self.ziel)
        formular.addRow(f"{umfang_text}:", self.umfang)
        layout = QVBoxLayout(self)
        layout.addLayout(formular)
        layout.addWidget(knoepfe)

    @staticmethod
    def _auswaehlen(feld: QComboBox, wert: object) -> None:
        stelle = feld.findData(wert)
        if stelle >= 0:
            feld.setCurrentIndex(stelle)

    def merken(self) -> tuple[str, str]:
        ziel = self.ziel.currentData()
        umfang = self.umfang.currentData()
        gemerkt = _einstellungen()
        gemerkt.setValue("diagramm/code_ziel", ziel)
        gemerkt.setValue("diagramm/code_umfang", umfang)
        return ziel, umfang


class CodeFenster(QDialog):
    """Zeigt den erzeugten Quelltext, nur lesbar."""

    #: Der Pfad der eben geschriebenen Datei. Das Hauptfenster hängt
    #: sich daran, frischt den Projekt-Explorer auf und öffnet sie als
    #: Reiter - vorher war die Datei geschrieben und danach passierte
    #: nichts, die Schülerin musste sie von Hand suchen.
    datei_geschrieben = Signal(Path)

    def __init__(
        self,
        quelltext: str,
        titel: str,
        eltern: QWidget | None = None,
        vorschlag: Path | None = None,
    ) -> None:
        super().__init__(eltern)
        self.setWindowTitle(titel)
        self.quelltext = quelltext
        #: Wo der Dialog beginnt. Ohne Angabe der Heimatordner - das
        #: ist der Fall, wenn das Fenster ohne Projekt geöffnet wird.
        self.vorschlag = Path(vorschlag) if vorschlag is not None else Path.home()

        gemerkt = _einstellungen()
        # Das Thema wie bei den Editor-Reitern des Hauptfensters. Mit
        # festem „light“ mischte der Editor im dunklen Design helle
        # Farben in den dunklen Dialog (Punkt 305).
        thema = str(gemerkt.value("design/thema", "system"))
        if thema not in ("system", "light", "dark"):
            thema = "system"
        self.ansicht = QuelltextEditor(
            thema=theme_aufloesen(thema),
            schriftart=gemerkt.value("editor/schriftart", "Consolas"),
        )
        self.ansicht.setPlainText(quelltext)
        self.ansicht.setReadOnly(True)

        self.kopieren_knopf = QPushButton("&Kopieren")
        self.speichern_knopf = QPushButton("&Speichern unter …")
        self.schliessen_knopf = QPushButton("S&chließen")
        self.kopieren_knopf.clicked.connect(self.kopieren)
        self.speichern_knopf.clicked.connect(self.speichern_unter)
        self.schliessen_knopf.clicked.connect(self.accept)

        knopfreihe = QHBoxLayout()
        knopfreihe.addWidget(self.kopieren_knopf)
        knopfreihe.addWidget(self.speichern_knopf)
        knopfreihe.addStretch(1)
        knopfreihe.addWidget(self.schliessen_knopf)

        layout = QVBoxLayout(self)
        layout.addWidget(self.ansicht)
        layout.addLayout(knopfreihe)
        # Nicht größer als der Bildschirm, in der zuletzt benutzten
        # Größe (Punkt 304).
        fenstergroesse.einpassen(self, 760, 620, _GROESSE_SCHLUESSEL)

    def done(self, ergebnis: int) -> None:
        fenstergroesse.merken(self, _GROESSE_SCHLUESSEL)
        super().done(ergebnis)

    def kopieren(self) -> None:
        QApplication.clipboard().setText(self.quelltext)

    def speichern_unter(self, pfad: Path | None = None) -> Path | None:
        """Schreibt den Quelltext und meldet, wohin.

        Der Dialog beginnt im Projektordner. Vorher begann er in gar
        keinem, und die erzeugte Klasse landete dann irgendwo - im
        September 2026 in einem eigens angelegten, sonst leeren
        Ordner. Dort sieht das Projekt sie nie: `Projekt.units` liest
        `ordner.glob("*.py")` im Projektordner.

        Geschrieben wird über `in_datei_schreiben()`, das nachfragt
        statt eine vorhandene Datei stillschweigend zu überschreiben -
        wer eine Klasse zweimal erzeugt, soll seine inzwischen
        ausformulierten Methodenrümpfe nicht verlieren.
        """
        if pfad is None:
            gewaehlt, _ = QFileDialog.getSaveFileName(
                self, "Quelltext speichern", str(self.vorschlag), "Python (*.py)"
            )
            if not gewaehlt:
                return None
            pfad = Path(gewaehlt)
        geschrieben = in_datei_schreiben(self.quelltext, Path(pfad), self)
        if geschrieben is not None:
            self.datei_geschrieben.emit(geschrieben)
        return geschrieben


def in_datei_schreiben(
    quelltext: str, pfad: Path, eltern: QWidget | None = None, fragen: bool = True
) -> Path | None:
    """Schreibt den Quelltext – und überschreibt niemals
    stillschweigend.

    Wer eine Klasse zweimal erzeugt, soll nicht seine inzwischen
    ausformulierten Methodenrümpfe verlieren. Deshalb die Rückfrage mit
    drei Möglichkeiten statt eines schlichten „Ja/Nein“.
    """
    pfad = Path(pfad)
    if pfad.exists() and fragen:
        antwort = QMessageBox.question(
            eltern,
            "Datei gibt es schon",
            f"„{pfad.name}“ gibt es bereits.\n\n"
            "Überschreiben? „Nein“ fragt nach einem anderen Namen.",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No
            | QMessageBox.StandardButton.Cancel,
        )
        if antwort == QMessageBox.StandardButton.Cancel:
            return None
        if antwort == QMessageBox.StandardButton.No:
            gewaehlt, _ = QFileDialog.getSaveFileName(
                eltern, "Quelltext speichern unter", str(pfad), "Python (*.py)"
            )
            if not gewaehlt:
                return None
            pfad = Path(gewaehlt)

    try:
        pfad.parent.mkdir(parents=True, exist_ok=True)
        atomar_schreiben(pfad, quelltext, encoding="utf-8")
    except OSError as fehler:
        # Ein Ziel ohne Schreibrecht endete bis 0.4.3 in der allgemeinen
        # Fehlermeldung (Punkt 569).
        schreibfehler_melden(eltern, pfad, fehler)
        return None
    return pfad


def schreibfehler_melden(
    eltern: QWidget | None, pfad: Path, fehler: OSError
) -> None:
    """Meldet, dass sich `pfad` nicht schreiben ließ. Eigene Funktion,
    damit Tests die Meldung abfangen können."""
    QMessageBox.warning(
        eltern,
        "Speichern nicht möglich",
        f"{pfad.name} lässt sich nicht schreiben: "
        f"{fehler.strerror or fehler}.\n\nEinen anderen Ordner wählen, "
        "etwa den des eigenen Projekts.",
    )
