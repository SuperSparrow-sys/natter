"""ProjektExplorer: Baumansicht mit Formularen und Units.

Siehe README.md, Abschnitt 7.4: „Gruppen Formulare, Units, Assets“.
`Assets` folgt, sobald Bild-/Sound-Komponenten Dateien in `assets/`
erwarten (siehe `pcl.Image`).

Dort stand bis dahin auch „Formular-Units als ein Eintrag“.
Das ist zurückgenommen: ein Formular und seine Unit sind nicht
dasselbe - das eine ist die Oberfläche, das andere der Code, und der
Code ist die Datei, in die der Schüler schreibt. Zusammengefasst nahm
sie ihm genau die aus dem Blick.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHeaderView, QMenu, QToolButton, QTreeWidget, QTreeWidgetItem

from ide.project import Projekt

PFAD_ROLLE = Qt.ItemDataRole.UserRole

#: Einrückung in den Bäumen der IDE. Schmaler als Qts Standard (20 px),
#: weil es meist nur zwei Ebenen gibt und die Docks auf einem
#: 1366×768-Schulrechner schmal bleiben.
#:
#: Hier und nur hier, seit M15: der Komponentenbaum im
#: Objektinspektor stand auf Qts 20 px, der Projekt-Explorer auf 14.
#: Zwei Bäume, gleichzeitig sichtbar, mit verschieden tiefer
#: Einrückung - beim Durchsehen der Abstände als Erstes aufgefallen.
EINRUECKUNG = 14

#: Alter Name, damit nichts umfällt, was ihn noch benutzt.
_EINRUECKUNG = EINRUECKUNG


class ProjektExplorer(QTreeWidget):
    #: Gemeldet: Units umbenennen/löschen über
    #: einen „⋮“-Knopf statt nur über den Windows-Explorer nebenbei.
    umbenennen_angefordert = Signal(Path)
    loeschen_angefordert = Signal(Path)

    def __init__(self) -> None:
        super().__init__()
        self.setHeaderHidden(True)
        self.setColumnCount(2)
        self.header().setStretchLastSection(False)
        self.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(1, 26)
        # QTreeWidgetItem ist standardmäßig per Doppelklick umbenennbar
        # (Qt.ItemIsEditable gehört zu den Standard-Flags) - kollidierte
        # mit unserem eigenen Doppelklick-zum-Öffnen und mit dem
        # dedizierten „⋮ → Umbenennen …“ (Nutzer-Screenshot: ein
        # unstyled, mitten im Baum eingeblendetes Eingabefeld, das gar
        # nicht unsere eigene Umbenennen-Funktion war).
        self.setEditTriggers(QTreeWidget.EditTrigger.NoEditTriggers)
        # Dateien stehen eingerückt unter ihrer Gruppenüberschrift. Die
        # „zwei blauen Balken“, die
        # dabei früher auftraten (Nutzer-Screenshot), lagen nicht an der
        # Einrückung selbst: Qt malt die Hover-/Auswahlfläche einer
        # Zeile zweimal (`::item` und `::branch`), und zwei
        # halbdurchsichtige Schichten übereinander ergaben links ein
        # dunkleres Kästchen. Seit `ide/shell/theme.py` dafür deckende
        # Farben benutzt, ist die Fläche durchgehend gleich hell.
        self.setIndentation(_EINRUECKUNG)

        # Rechte Maustaste öffnet dasselbe Menü wie der „⋮“-Knopf
        # (M11, Abschnitt 3). Der Knopf steht nur in der Zeile, über
        # der die Maus gerade schwebt; wer ihn nicht bemerkt, probiert
        # als Nächstes die rechte Maustaste, und dort liegt dasselbe
        # Menü.
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._kontextmenue_zeigen)

        self.formulare_gruppe = QTreeWidgetItem(["Formulare"])
        self.units_gruppe = QTreeWidgetItem(["Units"])
        self.diagramme_gruppe = QTreeWidgetItem(["Diagramme"])
        fett = QFont()
        fett.setBold(True)
        for gruppe in (self.formulare_gruppe, self.units_gruppe, self.diagramme_gruppe):
            gruppe.setFont(0, fett)
        self.addTopLevelItem(self.formulare_gruppe)
        self.addTopLevelItem(self.units_gruppe)
        self.addTopLevelItem(self.diagramme_gruppe)

    def projekt_anzeigen(self, projekt: Projekt) -> None:
        self.formulare_gruppe.takeChildren()
        self.units_gruppe.takeChildren()
        self.diagramme_gruppe.takeChildren()

        formular_stems = {pfad.stem for pfad in projekt.formulare()}

        for pfad in projekt.formulare():
            # öffnet den Designer (Abschnitt 7.7), nicht den Rohtext.
            # Von dort geht es mit Umschalt+F12 zur Unit und zurück
            # ("Ansicht → Formular und Code wechseln", Abschnitt 7.9)
            self._eintrag_hinzufuegen(self.formulare_gruppe, pfad.stem, pfad)

        for pfad in projekt.units():
            # Auch die Unit zu einem Formular. Sie stand hier bis
            # nicht, weil das Formular schon eine Zeile
            # darüber hat - aber die beiden sind nicht dasselbe: unter
            # „Formulare“ liegt die Oberfläche, hier der Code, und
            # genau der ist die Datei, in die der Schüler schreibt. Wer
            # ein neues Projekt anlegte, sah deshalb nur den Designer
            # und fand nirgends, wo sein Programm hingehört
            # (Gemeldet: „wenn ich ein neues Projekt erstelle muss
            # auch die u_main.py für den code angezeigt werden nicht nur
            # der designer“).
            #
            # Kein „⋮“-Menü für die Unit, die das Programm trägt: bei
            # einem Konsolenprojekt ist das `u_main.py`, und `main.py`
            # importiert genau diesen Namen. „Umbenennen …“ zöge den
            # Import nicht nach, „Löschen …“ nähme dem Projekt seinen
            # ganzen Inhalt.
            #
            # Ebenso wenig für die Unit eines Formulars: sie und die
            # `.pfm` heißen gleich, und das ist keine Schreibweise,
            # sondern die Verbindung zwischen beiden (Abschnitt 4.1).
            # Eine davon allein umzubenennen zerrisse das Paar.
            traegt_das_programm = pfad.stem == projekt.haupt_unit
            gehoert_zu_formular = pfad.stem in formular_stems
            self._eintrag_hinzufuegen(
                self.units_gruppe,
                pfad.name,
                pfad,
                mit_menue=not (traegt_das_programm or gehoert_zu_formular),
            )

        for pfad in projekt.diagramme():
            # öffnet den Diagramm-Editor in einem eigenen Fenster
            # (Abschnitt 13.1), nicht den Rohtext
            self._eintrag_hinzufuegen(self.diagramme_gruppe, pfad.stem, pfad)

        # Eine leere Gruppe wird ausgeblendet. Der Explorer zeigt, was
        # das Projekt hat; eine fette Überschrift ohne einen einzigen
        # Eintrag darunter sieht aus, als wäre etwas kaputtgegangen. Ein
        # Konsolenprojekt kann überhaupt keine Formulare haben, und acht
        # der neun Beispielprojekte haben keine Diagramme - in allen
        # dreien standen trotzdem die Überschriften. Ganz leer wird der
        # Baum dadurch nie: ein Konsolenprojekt hat immer seine
        # `main.py`, ein GUI-Projekt immer sein Hauptformular.
        for gruppe in (self.formulare_gruppe, self.units_gruppe, self.diagramme_gruppe):
            gruppe.setHidden(gruppe.childCount() == 0)

        self.expandAll()

    def _eintrag_hinzufuegen(
        self, gruppe: QTreeWidgetItem, beschriftung: str, pfad: Path, mit_menue: bool = False
    ) -> None:
        eintrag = QTreeWidgetItem([beschriftung])
        eintrag.setData(0, PFAD_ROLLE, str(pfad))
        gruppe.addChild(eintrag)
        if mit_menue:
            self.setItemWidget(eintrag, 1, self._knopf_erzeugen(pfad))

    def _knopf_erzeugen(self, pfad: Path) -> QToolButton:
        """Kleiner „⋮“-Knopf für „Umbenennen …“/„Löschen …“ (nur Units –
        ein Formular besteht aus `.pfm` + `.py` und wird bewusst
        (noch) nicht darüber umbenannt/gelöscht, das bräuchte
        zusätzlich Anpassungen an Imports/Ereignisverknüpfungen)."""
        knopf = QToolButton()
        knopf.setText("⋮")
        knopf.setAutoRaise(True)
        knopf.setFixedSize(22, 22)
        knopf.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        # Als `setItemWidget` eingebettetes Widget bekommt sonst die
        # deckende QWidget-Standardhintergrundfarbe aus dem IDE-Theme -
        # die stimmt bei einer ausgewählten/gehoverten Zeile nicht mehr
        # mit deren (halbtransparenter) Hervorhebungsfarbe überein und
        # wirkt wie ein zu dunkler Fleck (Nutzer-Screenshot). Ohne
        # eigenen Hintergrund scheint die Zeilenfarbe immer durch. Der
        # Dropdown-Pfeil neben dem „⋮“ wird ebenfalls unterdrückt – bei
        # einem reinen Symbolknopf unnötig.
        knopf.setStyleSheet(
            "QToolButton { background: transparent; border: none; }"
            "QToolButton::menu-indicator { image: none; width: 0px; }"
        )

        knopf.setMenu(self.dateimenue(pfad, knopf))
        return knopf

    def dateimenue(self, pfad: Path, eltern=None) -> QMenu:
        """Das Menü zu einer Datei – hinter dem „⋮“-Knopf und hinter
        der rechten Maustaste. Eine Fassung, damit beide Wege nie
        auseinanderlaufen."""
        menue = QMenu(eltern or self)
        menue.addAction("Umbenennen …", lambda: self.umbenennen_angefordert.emit(pfad))
        menue.addAction("Löschen …", lambda: self.loeschen_angefordert.emit(pfad))
        return menue

    def kontextmenue_fuer(self, punkt) -> QMenu | None:
        """Das Menü für die Stelle `punkt` – `None` über einer
        Gruppenüberschrift oder im Leeren, wo es nichts zu tun gäbe.

        Getrennt vom Anzeigen, damit der Rundlauf in
        `tests/test_ide_funktionspruefung.py` jeden Eintrag auslösen
        kann, ohne ein Menü zu öffnen, das auf einen Klick wartet.
        """
        eintrag = self.itemAt(punkt)
        if eintrag is None:
            return None
        pfad = eintrag.data(0, PFAD_ROLLE)
        # Nur Units tragen einen Pfad; die Gruppenüberschriften und die
        # Formulare (die aus .pfm + .py bestehen) nicht.
        if not pfad or self.itemWidget(eintrag, 1) is None:
            return None
        return self.dateimenue(Path(pfad))

    def _kontextmenue_zeigen(self, punkt) -> None:
        menue = self.kontextmenue_fuer(punkt)
        if menue is not None:
            menue.exec(self.viewport().mapToGlobal(punkt))
