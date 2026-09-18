"""Beschriften einer Form direkt auf der Zeichenfläche
(Abschnitt 13.3, 13.4).

Ein Doppelklick legt Eingabefelder genau über die Bereiche der Form:
Name oben, darunter Attribute und Methoden, je eine Zeile pro Eintrag.
Tab springt zum nächsten Feld, Escape bricht ab, Strg+Eingabe
übernimmt. Der Text wird bewusst **nicht** auf Richtigkeit geprüft
(Abschnitt 13.4) – auch `+foo(` bleibt stehen, wenn jemand das so
zeichnen will.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QEvent, QObject, QRectF, Qt, Signal
from PySide6.QtGui import QFont, QKeyEvent
from PySide6.QtWidgets import QApplication, QLineEdit, QPlainTextEdit, QWidget

from ide.diagramm.zeichnen import form_rechteck, klassen_bereiche


def _skaliert(rechteck: QRectF, zoom: float) -> QRectF:
    return QRectF(
        rechteck.left() * zoom,
        rechteck.top() * zoom,
        rechteck.width() * zoom,
        rechteck.height() * zoom,
    )

#: Reihenfolge, in der Tab durch die Felder springt (Abschnitt 13.3:
#: „Name → Attribute → Methoden“).
FELDER = ("name", "attributes", "methods")


class FormEditor(QWidget):
    """Eingabefelder über einer Form. Liegt als Kind-Widget auf der
    Zeichenfläche und meldet das Ergebnis über `fertig`."""

    fertig = Signal(dict)
    abgebrochen = Signal()

    def __init__(self, form: dict[str, Any], eltern: QWidget, zoom: float = 1.0) -> None:
        super().__init__(eltern)
        self.form = form
        # Die Zeichenfläche skaliert beim Malen, dieses Widget nicht -
        # Felder und Schrift müssen den Zoom deshalb selbst einrechnen,
        # sonst läge der Editor bei 200 % neben seiner Form.
        self.zoom = zoom
        self._felder: dict[str, QWidget] = {}
        # Nach dem Abschließen dürfen sterbende Felder nichts mehr
        # auslösen: beim Abräumen schickt Qt noch FocusOut, das sonst
        # erneut „übernehmen -> abräumen“ anstößt und auf bereits
        # gelöschte Widgets zugreift (Absturz in einem anderen Test,
        # Windows: access violation).
        self._beendet = False

        rechteck = form_rechteck(form)
        self.setGeometry(_skaliert(rechteck, zoom).toRect())
        bereiche = klassen_bereiche(form)
        text = form.get("text") or {}

        for name in FELDER:
            if name not in bereiche:
                continue
            bereich = bereiche[name].translated(-rechteck.left(), -rechteck.top())
            feld = self._feld_erzeugen(name, text)
            feld.setParent(self)
            feld.setGeometry(_skaliert(bereich, zoom).toRect())
            feld.installEventFilter(self)
            self._felder[name] = feld

        self.setFocusProxy(self._felder["name"])

    def _feld_erzeugen(self, name: str, text: dict[str, Any]) -> QWidget:
        if name == "name":
            feld = QLineEdit(str(text.get("name", "")))
            feld.setAlignment(Qt.AlignmentFlag.AlignCenter)
            feld.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            return feld

        feld = QPlainTextEdit("\n".join(str(z) for z in (text.get(name) or [])))
        feld.setFont(QFont("Consolas", 9))
        feld.setPlaceholderText(
            "+attribut: typ" if name == "attributes" else "+methode()"
        )
        feld.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        feld.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        return feld

    def _schriftgroesse(self, punkte: int) -> int:
        """Schrift wächst mit dem Zoom mit, damit der Text im Feld genauso
        groß ist wie der gezeichnete darunter."""
        return max(1, round(punkte * self.zoom))

    # -- Ergebnis -------------------------------------------------------

    def neuer_text(self) -> dict[str, Any]:
        """Der eingegebene Inhalt im `shape["text"]`-Format. Leere Zeilen
        fallen weg, damit ein versehentliches Enter am Ende keine leere
        Attributzeile hinterlässt."""
        text: dict[str, Any] = dict(self.form.get("text") or {})
        for name, feld in self._felder.items():
            if isinstance(feld, QLineEdit):
                text[name] = feld.text().strip()
            else:
                zeilen = [z.strip() for z in feld.toPlainText().splitlines()]
                text[name] = [z for z in zeilen if z]
        return text

    def uebernehmen(self) -> None:
        if self._beendet:
            return
        text = self.neuer_text()
        self.stilllegen()
        self.fertig.emit(text)

    def abbrechen(self) -> None:
        if self._beendet:
            return
        self.stilllegen()
        self.abgebrochen.emit()

    def stilllegen(self) -> None:
        """Meldet die Ereignisfilter ab und schaltet den Editor
        endgültig stumm – wird vor dem Abräumen aufgerufen."""
        self._beendet = True
        for feld in self._felder.values():
            feld.removeEventFilter(self)

    # -- Tastatur -------------------------------------------------------

    def eventFilter(self, beobachtet: QObject, ereignis: QEvent) -> bool:
        if self._beendet:
            return False
        if ereignis.type() == QEvent.Type.KeyPress:
            taste: QKeyEvent = ereignis
            if taste.key() == Qt.Key.Key_Escape:
                self.abbrechen()
                return True
            strg = bool(taste.modifiers() & Qt.KeyboardModifier.ControlModifier)
            if strg and taste.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self.uebernehmen()
                return True
            if strg and taste.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down):
                if self._zeile_verschieben(beobachtet, -1 if taste.key() == Qt.Key.Key_Up else 1):
                    return True
        elif ereignis.type() == QEvent.Type.FocusOut:
            # Nur übernehmen, wenn der Fokus das ganze Feld verlässt -
            # beim Tab-Sprung zwischen den eigenen Feldern nicht.
            neuer_fokus = QApplication.focusWidget()
            if neuer_fokus is None or not self.isAncestorOf(neuer_fokus):
                self.uebernehmen()
        return False

    def _zeile_verschieben(self, feld: QObject, richtung: int) -> bool:
        """Strg+Pfeil sortiert Attribute/Methoden um (Abschnitt 13.4)."""
        if not isinstance(feld, QPlainTextEdit):
            return False
        zeilen = feld.toPlainText().splitlines()
        cursor = feld.textCursor()
        nummer = cursor.blockNumber()
        ziel = nummer + richtung
        if not (0 <= nummer < len(zeilen)) or not (0 <= ziel < len(zeilen)):
            return False

        zeilen[nummer], zeilen[ziel] = zeilen[ziel], zeilen[nummer]
        feld.setPlainText("\n".join(zeilen))
        neuer_cursor = feld.textCursor()
        neuer_cursor.movePosition(neuer_cursor.MoveOperation.Start)
        for _ in range(ziel):
            neuer_cursor.movePosition(neuer_cursor.MoveOperation.NextBlock)
        feld.setTextCursor(neuer_cursor)
        return True
