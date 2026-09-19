"""Beschriften einer Notiz oder eines Pakets direkt auf der
Zeichenfläche (Abschnitt 13.3).

Ein Doppelklick legt ein Eingabefeld genau über die Form. Escape bricht
ab, Eingabe bzw. Strg+Eingabe übernimmt, der Verlust des Fokus
ebenfalls.

**Nur für Notiz und Paket.** Klassen, abstrakte Klassen und Interfaces
werden seit M9 Schritt 12 über den Eigenschaften-Dialog bearbeitet
(`ide/diagramm/klassendialog.py`): ihre Attribute und Operationen sind
strukturierte Datensätze mit Name, Typ, Sichtbarkeit und Parametern und
kein freier Text mehr. Notiz und Paket haben dagegen nur ein einziges
Textfeld – dafür wäre ein Dialog mit fünf Reitern überzogen
(Nutzer-Entscheidung September 2026).

Der Text wird bewusst **nicht** auf Richtigkeit geprüft
(Abschnitt 13.4).
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QEvent, QObject, QRectF, Qt, Signal
from PySide6.QtGui import QFont, QKeyEvent
from PySide6.QtWidgets import QApplication, QPlainTextEdit, QWidget

from ide.diagramm.zeichnen import form_rechteck


def _skaliert(rechteck: QRectF, zoom: float) -> QRectF:
    return QRectF(
        rechteck.left() * zoom,
        rechteck.top() * zoom,
        rechteck.width() * zoom,
        rechteck.height() * zoom,
    )


class FormEditor(QWidget):
    """Ein Eingabefeld über einer Form. Liegt als Kind-Widget auf der
    Zeichenfläche und meldet das Ergebnis über `fertig`."""

    fertig = Signal(dict)
    abgebrochen = Signal()

    def __init__(self, form: dict[str, Any], eltern: QWidget, zoom: float = 1.0) -> None:
        super().__init__(eltern)
        self.form = form
        # Die Zeichenfläche skaliert beim Malen, dieses Widget nicht -
        # Feld und Schrift müssen den Zoom deshalb selbst einrechnen,
        # sonst läge der Editor bei 200 % neben seiner Form.
        self.zoom = zoom
        # Nach dem Abschließen dürfen sterbende Felder nichts mehr
        # auslösen: beim Abräumen schickt Qt noch FocusOut, das sonst
        # erneut „übernehmen -> abräumen“ anstößt und auf bereits
        # gelöschte Widgets zugreift (Absturz in einem anderen Test,
        # Windows: access violation).
        self._beendet = False

        rechteck = form_rechteck(form)
        self.setGeometry(_skaliert(rechteck, zoom).toRect())

        feld = QPlainTextEdit(str(form.get("name", "")))
        feld.setFont(QFont("Segoe UI", max(1, round(10 * zoom))))
        feld.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        feld.setParent(self)
        feld.setGeometry(0, 0, self.width(), self.height())
        feld.installEventFilter(self)
        self._felder: dict[str, QWidget] = {"name": feld}
        self.setFocusProxy(feld)

    # -- Ergebnis -------------------------------------------------------

    def neuer_text(self) -> dict[str, Any]:
        """Der eingegebene Inhalt im Format, das die Zeichenfläche
        erwartet."""
        return {"name": self._felder["name"].toPlainText().strip()}

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
        elif ereignis.type() == QEvent.Type.FocusOut:
            # Nur übernehmen, wenn der Fokus das ganze Feld verlässt.
            neuer_fokus = QApplication.focusWidget()
            if neuer_fokus is None or not self.isAncestorOf(neuer_fokus):
                self.uebernehmen()
        return False
