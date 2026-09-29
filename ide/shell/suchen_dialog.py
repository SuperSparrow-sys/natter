"""„Suchen …“/„Ersetzen …“-Dialog (Abschnitt 7.2): sucht und ersetzt im
aktiven Editor-Tab über die eingebauten `QPlainTextEdit`/`QTextCursor`-
Operationen. Die Suche über alle Dateien des Projekts steht in
`ide/shell/in_dateien_suchen.py`.

Suchen und Ersetzen vergleichen nach derselben Regel (Punkt 129): bis
0.3.5 suchte „Weitersuchen“ ohne Rücksicht auf Groß- und
Kleinschreibung, „Ersetzen“ verglich aber genau und übersprang deshalb
Treffer, die „Alle ersetzen“ ersetzte.
"""

from __future__ import annotations

import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor, QTextDocument
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
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
        super().__init__(parent, Qt.WindowType.Tool)
        self.setWindowTitle("Suchen und Ersetzen")
        self._editor = editor

        self.suchfeld = QLineEdit()
        self.suchfeld.returnPressed.connect(self.suchen)
        self.ersetzenfeld = QLineEdit()
        self.gross_klein = QCheckBox("Groß- und Kleinschreibung beachten")
        self.ganze_woerter = QCheckBox("Nur ganze Wörter")

        self.zurueck_knopf = QPushButton("Zurück")
        self.zurueck_knopf.clicked.connect(lambda: self.suchen(rueckwaerts=True))
        self.suchen_knopf = QPushButton("Weitersuchen")
        self.suchen_knopf.clicked.connect(lambda: self.suchen())
        self.ersetzen_knopf = QPushButton("Ersetzen")
        self.ersetzen_knopf.clicked.connect(self.ersetzen)
        self.alle_ersetzen_knopf = QPushButton("Alle ersetzen")
        self.alle_ersetzen_knopf.clicked.connect(self.alle_ersetzen)
        #: Rückmeldung im Dialog: kein Treffer, Zahl der Ersetzungen.
        self.meldung = QLabel("")

        formular = QFormLayout()
        formular.addRow("Suchen:", self.suchfeld)
        formular.addRow("Ersetzen durch:", self.ersetzenfeld)
        formular.addRow("", self.gross_klein)
        formular.addRow("", self.ganze_woerter)

        knopfzeile = QHBoxLayout()
        for knopf in (
            self.zurueck_knopf, self.suchen_knopf, self.ersetzen_knopf, self.alle_ersetzen_knopf
        ):
            knopfzeile.addWidget(knopf)

        schliessen_knopf = QPushButton("Schließen")
        schliessen_knopf.clicked.connect(self.close)
        schliessen = QHBoxLayout()
        schliessen.addWidget(self.meldung, 1)
        schliessen.addWidget(schliessen_knopf)

        layout = QVBoxLayout(self)
        layout.addLayout(formular)
        layout.addLayout(knopfzeile)
        layout.addLayout(schliessen)

    def editor_setzen(self, editor: QPlainTextEdit) -> None:
        """Weitergesucht wird im Editor, der gerade vorn ist, auch wenn
        der Dialog für einen anderen geöffnet wurde."""
        self._editor = editor

    def markierung_uebernehmen(self) -> None:
        """Eine Markierung innerhalb einer Zeile wird zum Suchtext."""
        text = self._editor.textCursor().selectedText()
        if text and " " not in text:
            self.suchfeld.setText(text)
        self.suchfeld.selectAll()

    def _flags(self, rueckwaerts: bool = False) -> QTextDocument.FindFlag:
        flags = QTextDocument.FindFlag(0)
        if self.gross_klein.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        if self.ganze_woerter.isChecked():
            flags |= QTextDocument.FindFlag.FindWholeWords
        if rueckwaerts:
            flags |= QTextDocument.FindFlag.FindBackward
        return flags

    def _passt(self, gefunden: str) -> bool:
        """Dieselbe Regel wie beim Suchen: gilt die Markierung als
        Treffer?"""
        text = self.suchfeld.text()
        if self.gross_klein.isChecked():
            return gefunden == text
        return gefunden.casefold() == text.casefold()

    def suchen(self, rueckwaerts: bool = False) -> bool:
        """Sucht ab der aktuellen Cursorposition; am Ende der Datei geht
        es am Anfang weiter (rückwärts entsprechend am Ende)."""
        text = self.suchfeld.text()
        if not text:
            return False
        flags = self._flags(rueckwaerts)
        if self._editor.find(text, flags):
            self.meldung.setText("")
            return True
        cursor = self._editor.textCursor()
        cursor.movePosition(
            QTextCursor.MoveOperation.End if rueckwaerts else QTextCursor.MoveOperation.Start
        )
        self._editor.setTextCursor(cursor)
        if self._editor.find(text, flags):
            self.meldung.setText("")
            return True
        self.meldung.setText(f"„{text}“ kommt nicht vor.")
        return False

    def ersetzen(self) -> None:
        """Ersetzt die aktuelle Auswahl, falls sie ein Treffer ist, und
        springt zum nächsten."""
        cursor = self._editor.textCursor()
        if cursor.hasSelection() and self._passt(cursor.selectedText()):
            cursor.insertText(self.ersetzenfeld.text())
        self.suchen()

    def alle_ersetzen(self) -> int:
        """Ersetzt jeden Treffer im ganzen Dokument, in einem Schritt für
        Rückgängig. Liefert die Anzahl und nennt sie im Dialog."""
        text = self.suchfeld.text()
        if not text:
            return 0
        cursor = self._editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self._editor.setTextCursor(cursor)

        anzahl = 0
        bearbeitungs_cursor = self._editor.textCursor()
        bearbeitungs_cursor.beginEditBlock()
        while self._editor.find(text, self._flags()):
            fund_cursor = self._editor.textCursor()
            fund_cursor.insertText(self.ersetzenfeld.text())
            anzahl += 1
        bearbeitungs_cursor.endEditBlock()
        self.meldung.setText(
            "1 Stelle ersetzt." if anzahl == 1 else f"{anzahl} Stellen ersetzt."
        )
        return anzahl


def treffer_in_text(
    text: str, suchtext: str, *, gross_klein: bool = False, ganze_woerter: bool = False
) -> list[tuple[int, str]]:
    """(Zeilennummer ab 1, Zeile) für jede Zeile mit Treffer - nach
    derselben Regel wie im Dialog. Für „In allen Dateien suchen“."""
    if not suchtext:
        return []
    muster = re.escape(suchtext)
    if ganze_woerter:
        muster = rf"\b{muster}\b"
    regel = re.compile(muster, 0 if gross_klein else re.IGNORECASE)
    return [
        (nummer, zeile)
        for nummer, zeile in enumerate(text.splitlines(), start=1)
        if regel.search(zeile)
    ]
