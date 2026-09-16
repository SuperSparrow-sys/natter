"""QuelltextEditor: `QPlainTextEdit` mit Zeilennummernrand und
hervorgehobener aktueller Zeile.

Standardmuster aus der Qt-Dokumentation („Code Editor Example“), mit
deutschen Bezeichnern. Syntax-Hervorhebung und Monaco-Integration
(Abschnitt 7.5) sind eigene, spätere Schritte – dieser Editor ist der
Zwischenstand, bis dahin nicht mehr blank wie ein reines `QPlainTextEdit`.
"""

from __future__ import annotations

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QTextFormat
from PySide6.QtWidgets import QPlainTextEdit, QTextEdit, QWidget

_RAND_ABSTAND = 12
_RAND_HINTERGRUND = QColor("#f0f0f0")
_ZEILENNUMMER_FARBE = QColor("#8a8a8a")
_AKTUELLE_ZEILE_FARBE = QColor("#eaf2fc")


class _ZeilenNummernRand(QWidget):
    def __init__(self, editor: "QuelltextEditor") -> None:
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self._editor.zeilennummernrand_breite(), 0)

    def paintEvent(self, event) -> None:
        self._editor._zeilennummern_zeichnen(event)


class QuelltextEditor(QPlainTextEdit):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._rand = _ZeilenNummernRand(self)
        self.blockCountChanged.connect(self._breite_aktualisieren)
        self.updateRequest.connect(self._rand_aktualisieren)
        self.cursorPositionChanged.connect(self._aktuelle_zeile_hervorheben)
        self._breite_aktualisieren()
        self._aktuelle_zeile_hervorheben()

    def zeilennummernrand_breite(self) -> int:
        stellen = len(str(max(1, self.blockCount())))
        return _RAND_ABSTAND + self.fontMetrics().horizontalAdvance("9") * stellen

    def _breite_aktualisieren(self, *_werte: int) -> None:
        self.setViewportMargins(self.zeilennummernrand_breite(), 0, 0, 0)

    def _rand_aktualisieren(self, bereich: QRect, dy: int) -> None:
        if dy:
            self._rand.scroll(0, dy)
        else:
            self._rand.update(0, bereich.y(), self._rand.width(), bereich.height())
        if bereich.contains(self.viewport().rect()):
            self._breite_aktualisieren()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        rechteck = self.contentsRect()
        breite = self.zeilennummernrand_breite()
        self._rand.setGeometry(QRect(rechteck.left(), rechteck.top(), breite, rechteck.height()))

    def _zeilennummern_zeichnen(self, event) -> None:
        maler = QPainter(self._rand)
        maler.fillRect(event.rect(), _RAND_HINTERGRUND)

        block = self.firstVisibleBlock()
        blocknummer = block.blockNumber()
        oben = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        unten = oben + round(self.blockBoundingRect(block).height())

        while block.isValid() and oben <= event.rect().bottom():
            if block.isVisible() and unten >= event.rect().top():
                maler.setPen(_ZEILENNUMMER_FARBE)
                maler.drawText(
                    0,
                    oben,
                    self._rand.width() - _RAND_ABSTAND // 2,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    str(blocknummer + 1),
                )
            block = block.next()
            oben = unten
            unten = oben + round(self.blockBoundingRect(block).height())
            blocknummer += 1

    def _aktuelle_zeile_hervorheben(self) -> None:
        auswahlen: list[QTextEdit.ExtraSelection] = []
        if not self.isReadOnly():
            auswahl = QTextEdit.ExtraSelection()
            auswahl.format.setBackground(_AKTUELLE_ZEILE_FARBE)
            auswahl.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            auswahl.cursor = self.textCursor()
            auswahl.cursor.clearSelection()
            auswahlen.append(auswahl)
        self.setExtraSelections(auswahlen)
