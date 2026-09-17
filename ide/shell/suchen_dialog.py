"""„Suchen …“/„Ersetzen …“-Dialog (Abschnitt 7.2): sucht und ersetzt im
aktiven Editor-Tab über die eingebauten `QPlainTextEdit`/`QTextCursor`-
Operationen. Kein eigenes Suchfenster über mehrere Dateien hinweg (das
wäre „In Dateien suchen …“, ein eigener, größerer Schritt).
"""

from __future__ import annotations

from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class SuchenErsetzenDialog(QWidget):
    """Kein modaler `QDialog`, sondern ein dauerhaft nutzbares
    Werkzeugfenster – wie in den meisten Editoren lässt sich zwischen
    „Weitersuchen“-Klicks weiter im Editor gearbeitet werden."""

    def __init__(self, editor: QPlainTextEdit, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Suchen und Ersetzen")
        self._editor = editor

        self.suchfeld = QLineEdit()
        self.ersetzenfeld = QLineEdit()

        self.suchen_knopf = QPushButton("Weitersuchen")
        self.suchen_knopf.clicked.connect(self.suchen)
        self.ersetzen_knopf = QPushButton("Ersetzen")
        self.ersetzen_knopf.clicked.connect(self.ersetzen)
        self.alle_ersetzen_knopf = QPushButton("Alle ersetzen")
        self.alle_ersetzen_knopf.clicked.connect(self.alle_ersetzen)

        formular = QFormLayout()
        formular.addRow("Suchen:", self.suchfeld)
        formular.addRow("Ersetzen durch:", self.ersetzenfeld)

        knopfzeile = QHBoxLayout()
        knopfzeile.addWidget(self.suchen_knopf)
        knopfzeile.addWidget(self.ersetzen_knopf)
        knopfzeile.addWidget(self.alle_ersetzen_knopf)

        schliessen = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        schliessen.rejected.connect(self.close)
        schliessen.button(QDialogButtonBox.StandardButton.Close).clicked.connect(self.close)

        layout = QVBoxLayout(self)
        layout.addLayout(formular)
        layout.addLayout(knopfzeile)
        layout.addWidget(schliessen)

    def suchen(self) -> bool:
        """Sucht vorwärts ab der aktuellen Cursorposition; springt bei
        Erreichen des Dateiendes an den Anfang zurück (einfaches
        Umlaufen statt eines eigenen „Weitersuchen“-Zustands)."""
        text = self.suchfeld.text()
        if not text:
            return False
        if self._editor.find(text):
            return True
        cursor = self._editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self._editor.setTextCursor(cursor)
        return self._editor.find(text)

    def ersetzen(self) -> None:
        """Ersetzt die aktuelle Auswahl, falls sie zum Suchtext passt,
        und springt zum nächsten Treffer."""
        text = self.suchfeld.text()
        cursor = self._editor.textCursor()
        if cursor.hasSelection() and cursor.selectedText() == text:
            cursor.insertText(self.ersetzenfeld.text())
        self.suchen()

    def alle_ersetzen(self) -> int:
        """Ersetzt jedes Vorkommen im gesamten Dokument, vom Anfang an.
        Liefert die Anzahl der ersetzten Stellen."""
        text = self.suchfeld.text()
        if not text:
            return 0
        cursor = self._editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self._editor.setTextCursor(cursor)

        anzahl = 0
        bearbeitungs_cursor = self._editor.textCursor()
        bearbeitungs_cursor.beginEditBlock()
        while self._editor.find(text):
            fund_cursor = self._editor.textCursor()
            fund_cursor.insertText(self.ersetzenfeld.text())
            anzahl += 1
        bearbeitungs_cursor.endEditBlock()
        return anzahl
