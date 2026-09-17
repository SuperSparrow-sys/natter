"""QuelltextEditor: `QPlainTextEdit` mit Zeilennummernrand,
hervorgehobener aktueller Zeile, klickbaren Breakpoints im Rand (wie in
den meisten IDEs, Abschnitt 8.1) und Python-Syntax-Hervorhebung
(`ide.shell.python_hervorhebung`).

Standardmuster aus der Qt-Dokumentation („Code Editor Example“), mit
deutschen Bezeichnern. Eine echte Monaco-Integration (Abschnitt 7.5) ist
ein eigener, späterer Schritt (siehe `prototypes/s2`); die
Syntax-Hervorhebung selbst ist bereits echt, nur regelbasiert statt über
eine vollständige Grammatik.
"""

from __future__ import annotations

from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QResizeEvent,
    QTextFormat,
)
from PySide6.QtWidgets import QPlainTextEdit, QTextEdit, QWidget

from ide.shell.python_hervorhebung import PythonHervorhebung

_RAND_ABSTAND = 12
_RAND_HINTERGRUND = QColor("#f0f0f0")
_ZEILENNUMMER_FARBE = QColor("#8a8a8a")
_AKTUELLE_ZEILE_FARBE = QColor("#eaf2fc")
_BREAKPOINT_FARBE = QColor("#c0392b")
_BREAKPOINT_DURCHMESSER = 10
_BREAKPOINT_SPALTE_BREITE = _BREAKPOINT_DURCHMESSER + 6

# Deckt sich mit design/tokens.json ("family_mono": "Cascadia Code") -
# Consolas/Courier New als Ausweich, falls Cascadia Code auf dem Rechner
# fehlt (Windows bringt Cascadia Code seit Terminal/VS Code meist schon
# mit, ist aber kein garantierter Systemfont wie Consolas).
_CODE_SCHRIFTARTEN = ["Cascadia Code", "Consolas", "Courier New"]
_CODE_SCHRIFTGROESSE = 11


class _ZeilenNummernRand(QWidget):
    def __init__(self, editor: QuelltextEditor) -> None:
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self._editor.zeilennummernrand_breite(), 0)

    def paintEvent(self, event: QPaintEvent) -> None:
        self._editor._zeilennummern_zeichnen(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._editor._rand_klick_verarbeiten(event.position().y())


class QuelltextEditor(QPlainTextEdit):
    breakpoint_umgeschaltet = Signal(int, bool)  # (Zeile ab 1, jetzt gesetzt?)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        schriftart = QFont(_CODE_SCHRIFTARTEN)
        schriftart.setPointSize(_CODE_SCHRIFTGROESSE)
        schriftart.setFixedPitch(True)
        self.setFont(schriftart)
        self._hervorhebung = PythonHervorhebung(self.document())

        self.breakpoints: set[int] = set()
        self._rand = _ZeilenNummernRand(self)
        self.blockCountChanged.connect(self._breite_aktualisieren)
        self.updateRequest.connect(self._rand_aktualisieren)
        self.cursorPositionChanged.connect(self._aktuelle_zeile_hervorheben)
        self._breite_aktualisieren()
        self._aktuelle_zeile_hervorheben()

    def zeilennummernrand_breite(self) -> int:
        stellen = len(str(max(1, self.blockCount())))
        return (
            _BREAKPOINT_SPALTE_BREITE
            + _RAND_ABSTAND
            + self.fontMetrics().horizontalAdvance("9") * stellen
        )

    def breakpoint_umschalten(self, zeile: int) -> None:
        """Setzt/entfernt einen Breakpoint bei `zeile` (ab 1) und meldet
        die Änderung über `breakpoint_umgeschaltet`."""
        if zeile in self.breakpoints:
            self.breakpoints.discard(zeile)
            gesetzt = False
        else:
            self.breakpoints.add(zeile)
            gesetzt = True
        self._rand.update()
        self.breakpoint_umgeschaltet.emit(zeile, gesetzt)

    def _breite_aktualisieren(self, *_werte: int) -> None:
        self.setViewportMargins(self.zeilennummernrand_breite(), 0, 0, 0)

    def _rand_aktualisieren(self, bereich: QRect, dy: int) -> None:
        if dy:
            self._rand.scroll(0, dy)
        else:
            self._rand.update(0, bereich.y(), self._rand.width(), bereich.height())
        if bereich.contains(self.viewport().rect()):
            self._breite_aktualisieren()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        rechteck = self.contentsRect()
        breite = self.zeilennummernrand_breite()
        self._rand.setGeometry(QRect(rechteck.left(), rechteck.top(), breite, rechteck.height()))

    def _fuer_jeden_sichtbaren_block(self, event_rect: QRect):
        """Liefert (blocknummer_ab_0, oben_px, unten_px) für jeden im
        `event_rect` sichtbaren Textblock – gemeinsame Grundlage für
        Zeichnen und Klick-Trefferermittlung im Rand."""
        block = self.firstVisibleBlock()
        blocknummer = block.blockNumber()
        oben = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        unten = oben + round(self.blockBoundingRect(block).height())

        while block.isValid() and oben <= event_rect.bottom():
            if block.isVisible() and unten >= event_rect.top():
                yield blocknummer, oben, unten
            block = block.next()
            oben = unten
            unten = oben + round(self.blockBoundingRect(block).height())
            blocknummer += 1

    def _zeilennummern_zeichnen(self, event: QPaintEvent) -> None:
        maler = QPainter(self._rand)
        maler.fillRect(event.rect(), _RAND_HINTERGRUND)
        maler.setRenderHint(QPainter.RenderHint.Antialiasing)

        hoehe = self.fontMetrics().height()
        for blocknummer, oben, _unten in self._fuer_jeden_sichtbaren_block(event.rect()):
            zeile = blocknummer + 1
            if zeile in self.breakpoints:
                mitte_y = oben + hoehe / 2
                mitte_x = _BREAKPOINT_SPALTE_BREITE / 2
                maler.setBrush(_BREAKPOINT_FARBE)
                maler.setPen(Qt.PenStyle.NoPen)
                maler.drawEllipse(
                    QRect(
                        round(mitte_x - _BREAKPOINT_DURCHMESSER / 2),
                        round(mitte_y - _BREAKPOINT_DURCHMESSER / 2),
                        _BREAKPOINT_DURCHMESSER,
                        _BREAKPOINT_DURCHMESSER,
                    )
                )
            maler.setPen(_ZEILENNUMMER_FARBE)
            maler.drawText(
                0,
                oben,
                self._rand.width() - _RAND_ABSTAND // 2,
                hoehe,
                Qt.AlignmentFlag.AlignRight,
                str(zeile),
            )

    def _rand_klick_verarbeiten(self, y: float) -> None:
        rect = QRect(0, 0, self._rand.width(), self._rand.height())
        for blocknummer, oben, unten in self._fuer_jeden_sichtbaren_block(rect):
            if oben <= y < unten:
                self.breakpoint_umschalten(blocknummer + 1)
                return

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
