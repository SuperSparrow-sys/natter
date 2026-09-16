"""CSV-Tabellenansicht (Abschnitt 11.5): erkennt Trennzeichen und
Zeichensatz automatisch (Excel-Export: Semikolon, Windows-1252), zeigt
wahlweise als sortierbare Tabelle oder als Rohtext an, mit Filterzeile.
Ändert die Datei nie.
"""

from __future__ import annotations

import csv
from pathlib import Path

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

_ZEICHENSAETZE = ("utf-8", "cp1252")


def csv_erkennen(pfad: Path) -> tuple[str, str]:
    """Liefert (Trennzeichen, Zeichensatz) für `pfad` (Abschnitt 11.5):
    UTF-8 wird zuerst versucht, `cp1252` (Windows-1252, typischer
    Excel-Export) als Ausweich bei einem Dekodierfehler; das
    Trennzeichen wird aus der ersten Zeile zwischen ";" und ","
    entschieden (";" gewinnt bei Gleichstand, wie im deutschen
    Excel-Export üblich)."""
    rohdaten = Path(pfad).read_bytes()
    for zeichensatz in _ZEICHENSAETZE:
        try:
            text = rohdaten.decode(zeichensatz)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = rohdaten.decode("utf-8", errors="replace")
        zeichensatz = "utf-8"

    erste_zeile = text.split("\n", 1)[0]
    trennzeichen = ";" if erste_zeile.count(";") >= erste_zeile.count(",") else ","
    return trennzeichen, zeichensatz


class CsvAnsicht(QWidget):
    """Zeigt eine CSV-Datei als sortierbare, filterbare Tabelle oder als
    Rohtext (Abschnitt 11.5)."""

    def __init__(self, pfad: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pfad = Path(pfad)
        self._delimiter, self._encoding = csv_erkennen(self._pfad)

        self._tabelle = QTableWidget()
        self._tabelle.setSortingEnabled(True)
        self._text = QPlainTextEdit()
        self._text.setReadOnly(True)

        self._stapel = QStackedWidget()
        self._stapel.addWidget(self._tabelle)
        self._stapel.addWidget(self._text)

        self._filter = QLineEdit()
        self._filter.setPlaceholderText("Filtern …")
        self._filter.textChanged.connect(self._filtern)
        self._umschalt_knopf = QPushButton("Als Text anzeigen")
        self._umschalt_knopf.setCheckable(True)
        self._umschalt_knopf.toggled.connect(self._ansicht_umschalten)

        werkzeugleiste = QHBoxLayout()
        werkzeugleiste.addWidget(self._filter)
        werkzeugleiste.addWidget(self._umschalt_knopf)

        layout = QVBoxLayout(self)
        layout.addLayout(werkzeugleiste)
        layout.addWidget(self._stapel)

        self._laden()

    @property
    def delimiter(self) -> str:
        return self._delimiter

    @property
    def encoding(self) -> str:
        return self._encoding

    @property
    def tabelle(self) -> QTableWidget:
        return self._tabelle

    def _laden(self) -> None:
        self._text.setPlainText(self._pfad.read_text(encoding=self._encoding))

        with open(self._pfad, encoding=self._encoding, newline="") as datei:
            zeilen = list(csv.reader(datei, delimiter=self._delimiter))

        self._tabelle.setSortingEnabled(False)
        if not zeilen:
            self._tabelle.setRowCount(0)
            self._tabelle.setColumnCount(0)
        else:
            kopf, *rest = zeilen
            self._tabelle.setColumnCount(len(kopf))
            self._tabelle.setHorizontalHeaderLabels(kopf)
            self._tabelle.setRowCount(len(rest))
            for zeile_index, zeile in enumerate(rest):
                for spalten_index, wert in enumerate(zeile):
                    self._tabelle.setItem(zeile_index, spalten_index, QTableWidgetItem(wert))
        self._tabelle.setSortingEnabled(True)

    def _ansicht_umschalten(self, als_text: bool) -> None:
        self._stapel.setCurrentWidget(self._text if als_text else self._tabelle)

    def _filtern(self, text: str) -> None:
        text = text.lower()
        for zeile in range(self._tabelle.rowCount()):
            treffer = not text or any(
                text in self._tabelle.item(zeile, spalte).text().lower()
                for spalte in range(self._tabelle.columnCount())
                if self._tabelle.item(zeile, spalte) is not None
            )
            self._tabelle.setRowHidden(zeile, not treffer)
