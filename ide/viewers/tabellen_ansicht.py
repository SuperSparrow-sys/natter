"""Fenster „Als Tabelle anzeigen“ (Abschnitt 11.6): zeigt eine Variable
des angehaltenen Schülerprogramms als Tabelle statt als `repr`-Zeile im
Variablen-Panel.

Die Umwandlung selbst steht in `ide.debugger.tabellenansicht`; hier nur
die Anzeige. Wie die CSV-Ansicht (Abschnitt 11.5) ist die Tabelle
sortierbar und filterbar und ändert nie etwas am Programm.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ide.debugger.tabellenansicht import Tabelle


class TabellenAnsicht(QDialog):
    """Eigenes Fenster mit der Tabelle zu einer Variablen."""

    def __init__(self, name: str, tabelle: Tabelle, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{name} als Tabelle")
        self.resize(720, 460)
        self._tabelle = QTableWidget()
        self._tabelle.setSortingEnabled(False)
        self._tabelle.setColumnCount(len(tabelle.spalten))
        self._tabelle.setHorizontalHeaderLabels(tabelle.spalten)
        self._tabelle.setRowCount(len(tabelle.zeilen))
        for zeilen_nummer, zeile in enumerate(tabelle.zeilen):
            for spalten_nummer, zelle in enumerate(zeile):
                self._tabelle.setItem(
                    zeilen_nummer, spalten_nummer, QTableWidgetItem(str(zelle))
                )
        self._tabelle.setSortingEnabled(True)
        # Beim Bildschirmfoto gefunden: neben der Spalte „index“ bzw.
        # „#“ zählte Qts eigene Zeilenleiste ein zweites Mal mit (0,1,2
        # neben 1,2,3) - für den Unterricht nur verwirrend.
        self._tabelle.verticalHeader().setVisible(False)
        self._tabelle.resizeColumnsToContents()
        self._tabelle.horizontalHeader().setStretchLastSection(True)

        self._filter = QLineEdit()
        self._filter.setPlaceholderText("Filtern …")
        self._filter.textChanged.connect(self._filtern)

        self._kopfzeile = QLabel(self._beschreibung(name, tabelle))

        layout = QVBoxLayout(self)
        layout.addWidget(self._kopfzeile)
        layout.addWidget(self._filter)
        layout.addWidget(self._tabelle)

    @property
    def tabelle_widget(self) -> QTableWidget:
        return self._tabelle

    @property
    def beschreibung(self) -> str:
        return self._kopfzeile.text()

    @staticmethod
    def _anzahl(zahl: int, einzahl: str, mehrzahl: str) -> str:
        """„1 Zeile“ statt „1 Zeile(n)“.

        Klammerformen wie „Zeile(n)“ sind in einer deutschen Oberfläche
        für Schülerinnen und Schüler fehl am Platz – der Rest von Natter
        unterscheidet Ein- und Mehrzahl ebenfalls (siehe
        „Layout-Hinweis“/„Layout-Hinweise“ in der Statusleiste des
        Diagramm-Editors).
        """
        return f"{zahl} {einzahl if zahl == 1 else mehrzahl}"

    @classmethod
    def _beschreibung(cls, name: str, tabelle: Tabelle) -> str:
        text = (
            f"{name} ({tabelle.art}): "
            f"{cls._anzahl(tabelle.gesamt, 'Zeile', 'Zeilen')}, "
            f"{cls._anzahl(len(tabelle.spalten), 'Spalte', 'Spalten')}"
        )
        if tabelle.gekuerzt:
            text += f" – angezeigt werden die ersten {len(tabelle.zeilen)}."
        return text

    def _filtern(self, text: str) -> None:
        text = text.lower()
        for zeile in range(self._tabelle.rowCount()):
            treffer = not text or any(
                text in self._tabelle.item(zeile, spalte).text().lower()
                for spalte in range(self._tabelle.columnCount())
                if self._tabelle.item(zeile, spalte) is not None
            )
            self._tabelle.setRowHidden(zeile, not treffer)
