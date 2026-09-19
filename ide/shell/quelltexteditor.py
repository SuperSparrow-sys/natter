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

import re
from pathlib import Path

from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QResizeEvent,
    QTextFormat,
)
from PySide6.QtWidgets import (
    QListWidget,
    QPlainTextEdit,
    QTextEdit,
    QToolTip,
    QWidget,
)

from ide.shell.python_hervorhebung import PythonHervorhebung
from ide.shell.vervollstaendigung import (
    MINDESTZEICHEN,
    Vorschlag,
    parameterhilfe,
    vorschlaege,
)

_SCHRIFT_DATEI = (
    Path(__file__).resolve().parent.parent / "assets" / "fonts" / "CascadiaCode-Regular.ttf"
)
_schriftart_geladen = False


def _cascadia_code_bereitstellen() -> None:
    """Lädt Cascadia Code aus der mitgelieferten Schriftdatei in die
    Qt-Anwendungsschrift-Datenbank (Nutzer-Feedback September 2026:
    „wenn Schriftart nicht installiert, soll diese installiert
    werden“) - ganz ohne Windows-Systeminstallation, passend zur
    portablen, installationsfreien Natter-Philosophie (Abschnitt 17).
    Einmal pro Prozess, danach findet `QFont(["Cascadia Code", ...])`
    sie zuverlässig, unabhängig davon, ob sie auf dem Rechner selbst
    installiert ist."""
    global _schriftart_geladen
    if _schriftart_geladen:
        return
    if _SCHRIFT_DATEI.exists():
        QFontDatabase.addApplicationFont(str(_SCHRIFT_DATEI))
    _schriftart_geladen = True

_RAND_ABSTAND = 12
_BREAKPOINT_FARBE = QColor("#c0392b")
#: Die Eigenschaft, unter der das Hauptfenster den Dateipfad am Editor
#: ablegt. jedi arbeitet damit deutlich besser - es findet dann die
#: Nachbardateien des Projekts.
_PFAD_EIGENSCHAFT = "pfad"
#: Das Wort, das gerade getippt wird.
_WORT_MUSTER = re.compile(r"[A-Za-z_]\w*$")

_EINZUG = "    "
_EINZUG_MUSTER = re.compile(r"[ \t]*")
_BREAKPOINT_DURCHMESSER = 10
_BREAKPOINT_SPALTE_BREITE = _BREAKPOINT_DURCHMESSER + 6

# Rand-/Zeilenhervorhebungsfarben je Thema (Abschnitt 6, „Ansicht →
# Design“, Nutzer-Feedback September 2026: Dark-Mode-Farben sollen zum
# VS-Code-Standardschema passen). Dark+-Zeilennummernfarbe `#858585` und
# Hervorhebung `#2a2d2e` sind VS Codes echte Standardwerte; Hell bleibt
# beim bisherigen, etwas kräftigeren Grauton (kein VS-Code-Feedback dazu).
_RAND_FARBEN = {
    "light": {"hintergrund": "#f0f0f0", "zeilennummer": "#8a8a8a", "aktuelle_zeile": "#eaf2fc"},
    "dark": {"hintergrund": "#252526", "zeilennummer": "#858585", "aktuelle_zeile": "#2a2d2e"},
}

# Farbe der Einrückungslinien (M11, Abschnitt 2.1). Bewusst blass: sie
# sind eine Orientierungshilfe und dürfen den Quelltext nicht
# übertönen. Dieselben Werte benutzt VS Code für `editorIndentGuide`.
_EINZUGSLINIEN_FARBEN = {"light": "#e4e4e4", "dark": "#404040"}

# Nutzer-Feedback (September 2026): Cascadia Code wirkte auf dem
# echten Rechner trotz mitgelieferter Schriftdatei weiterhin wie die
# Standardschrift - Consolas (ein garantierter Windows-Systemfont,
# kein Bundling nötig) steht deshalb an erster Stelle. Zusätzlich
# als Auswahl im Menü „Ansicht → Schriftart“ angeboten (Nutzer-Feedback:
# „soll bei Ansicht eine Auswahl der Schriftarten zum Auswählen“).
SCHRIFTART_OPTIONEN = ("Consolas", "Cascadia Code", "Courier New")
_CODE_SCHRIFTGROESSE = 11


def _schriftart_kette(schriftart: str) -> list[str]:
    """Baut die Ausweich-Kette für `QFont`/die QSS-Regel: die gewählte
    Schrift zuerst, alle übrigen `SCHRIFTART_OPTIONEN` als Ausweich."""
    return [schriftart] + [f for f in SCHRIFTART_OPTIONEN if f != schriftart]


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

    def __init__(
        self,
        parent: QWidget | None = None,
        thema: str = "light",
        schriftart: str = "Consolas",
    ) -> None:
        super().__init__(parent)
        _cascadia_code_bereitstellen()
        self._schriftart = schriftart
        qfont = QFont(_schriftart_kette(schriftart))
        qfont.setPointSize(_CODE_SCHRIFTGROESSE)
        qfont.setFixedPitch(True)
        self.setFont(qfont)
        self._thema = thema
        self._rand_farben = _RAND_FARBEN.get(thema, _RAND_FARBEN["light"])
        self._hervorhebung = PythonHervorhebung(self.document(), thema)

        #: Senkrechte Hilfslinien je Einrückungsebene (M11, 2.1)
        self.einzugslinien_sichtbar = True

        #: Vervollständigung (M11, 2.2)
        self.vervollstaendigung_an = True
        self._vorschlaege: list[Vorschlag] = []
        # Kind des **Viewports**, kein eigenes Fenster. Mit
        # `Qt.WindowType.ToolTip` wäre die Liste ein Fenster für sich -
        # und `setGeometry` rechnete dann in Bildschirmkoordinaten. Beim
        # Bildschirmfoto fiel es auf: die Liste tauchte im Bild des
        # Editors gar nicht auf, weil sie in Wahrheit in der Ecke des
        # Bildschirms stand statt unter der Schreibmarke.
        self.vorschlagsliste = QListWidget(self.viewport())
        self.vorschlagsliste.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        # Keine waagerechte Bildlaufleiste: in einer Vorschlagsliste
        # scrollt niemand zur Seite, um die Erklärung zu Ende zu lesen -
        # er tippt weiter. Zu lange Zeilen werden abgekürzt.
        self.vorschlagsliste.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.vorschlagsliste.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.vorschlagsliste.itemClicked.connect(
            lambda *_: self.vorschlag_uebernehmen()
        )
        self.vorschlagsliste.hide()

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

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Automatischer Einzug (Nutzer-Feedback September 2026: „was
        passiert wenn ich in einer Funktion Enter drücke“ – bisher
        nichts, jede Zeile begann bei Spalte 0). Kein echtes
        Grammatik-Wissen wie bei einer vollständigen Monaco-Integration
        (`prototypes/s2`, noch offen) – nur zwei einfache, zuverlässige
        Regeln wie in den meisten schlanken Editoren: Einzug der
        Vorzeile übernehmen, nach einem ":" am Zeilenende eine Ebene
        mehr einrücken. Tab fügt vier Leerzeichen statt eines
        Tabulatorzeichens ein - sonst mischen sich in Python schnell
        Tabs und Leerzeichen (`TabError`)."""
        # Solange die Vorschlagsliste offen ist, gehören ihr die
        # Pfeiltasten, Eingabe und Escape. Sonst würde Eingabe eine neue
        # Zeile einfügen, statt den markierten Vorschlag zu übernehmen -
        # und die Liste bliebe stehen.
        if self.vorschlagsliste.isVisible():
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Tab):
                if self.vorschlag_uebernehmen():
                    return
            elif event.key() == Qt.Key.Key_Escape:
                self.vorschlagsliste_schliessen()
                return
            elif event.key() in (
                Qt.Key.Key_Up,
                Qt.Key.Key_Down,
                Qt.Key.Key_PageUp,
                Qt.Key.Key_PageDown,
            ):
                self.vorschlagsliste.keyPressEvent(event)
                return

        # Strg+Leertaste erzwingt die Liste - auch direkt nach einem
        # Punkt, wo noch nichts getippt ist.
        if (
            event.key() == Qt.Key.Key_Space
            and event.modifiers() & Qt.KeyboardModifier.ControlModifier
        ):
            self.vorschlaege_anzeigen(erzwungen=True)
            return

        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not event.modifiers():
            self._einrueckende_neue_zeile_einfuegen()
            return
        if event.key() == Qt.Key.Key_Tab and not event.modifiers():
            self.textCursor().insertText(_EINZUG)
            return
        if event.key() == Qt.Key.Key_Backspace and self._einzugsebene_loeschen():
            return
        super().keyPressEvent(event)
        self._nach_der_eingabe(event)

    def _nach_der_eingabe(self, event: QKeyEvent) -> None:
        """Nach jedem getippten Zeichen: Liste auffrischen bzw.
        Parameterhilfe zeigen."""
        if not self.vervollstaendigung_an:
            return
        text = event.text()
        if text == "(":
            self.parameterhilfe_anzeigen()
            return
        if text in (")", ""):
            QToolTip.hideText()
        if text and (text.isalnum() or text in "._"):
            self.vorschlaege_anzeigen()
        elif self.vorschlagsliste.isVisible():
            self.vorschlagsliste_schliessen()

    def _einzugsebene_loeschen(self) -> bool:
        """Rücktaste im Einzug löscht eine **ganze** Ebene.

        Mit vier Leerzeichen je Ebene bräuchte es sonst vier Anschläge,
        um eine Zeile auszurücken – und wer dabei einmal zu oft oder zu
        wenig drückt, bekommt in Python einen `IndentationError`, den er
        nicht sieht. Nur wenn links vom Cursor ausschließlich
        Leerzeichen stehen: mitten im Text bleibt die Rücktaste, was sie
        ist.
        """
        cursor = self.textCursor()
        if cursor.hasSelection():
            return False
        links = cursor.block().text()[: cursor.positionInBlock()]
        if not links or links.strip():
            return False
        zurueck = len(links) % len(_EINZUG) or len(_EINZUG)
        for _ in range(min(zurueck, len(links))):
            cursor.deletePreviousChar()
        return True

    def _einrueckende_neue_zeile_einfuegen(self) -> None:
        cursor = self.textCursor()
        zeile_bis_cursor = cursor.block().text()[: cursor.positionInBlock()]
        einzug = _EINZUG_MUSTER.match(zeile_bis_cursor).group()
        if zeile_bis_cursor.rstrip().endswith(":"):
            einzug += _EINZUG
        cursor.insertText("\n" + einzug)

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

    def thema_setzen(self, thema: str) -> None:
        """„Ansicht → Design“: Rand-/Zeilenhervorhebungsfarben und die
        Syntax-Hervorhebung sofort auf das neue Thema umstellen."""
        if thema == self._thema:
            return
        self._thema = thema
        self._rand_farben = _RAND_FARBEN.get(thema, _RAND_FARBEN["light"])
        self._hervorhebung.thema_setzen(thema)
        self._rand.update()
        self._aktuelle_zeile_hervorheben()

    def schriftart_setzen(self, schriftart: str) -> None:
        """„Ansicht → Schriftart“: wechselt die Editor-Schriftart sofort.
        Das IDE-weite Stylesheet (`ide_qss_erzeugen`) setzt dieselbe
        Schrift ohnehin per QSS-Regel durch, die gegen einen bloßen
        `setFont()`-Aufruf gewinnt (siehe theme.py) - hier trotzdem
        explizit gesetzt, damit der Editor auch außerhalb einer
        HauptFenster-Instanz (z. B. in Tests) korrekt reagiert."""
        if schriftart == self._schriftart:
            return
        self._schriftart = schriftart
        qfont = QFont(_schriftart_kette(schriftart))
        qfont.setPointSize(_CODE_SCHRIFTGROESSE)
        qfont.setFixedPitch(True)
        self.setFont(qfont)

    # -- Einrückung sichtbar machen (M11, Abschnitt 2.1) ----------------

    def einzugslinien_setzen(self, sichtbar: bool) -> None:
        """Schaltet die senkrechten Hilfslinien je Einrückungsebene."""
        if sichtbar == self.einzugslinien_sichtbar:
            return
        self.einzugslinien_sichtbar = sichtbar
        self.viewport().update()

    def einzugstiefe(self, blocknummer: int) -> int:
        """Wie viele Ebenen tief diese Zeile eingerückt ist.

        Eine **leere** Zeile hat für sich genommen keine Einrückung; sie
        übernimmt deshalb die der nächsten Zeile mit Inhalt. Sonst
        rissen die Linien mitten in einem Block ab, gerade dort, wo eine
        Leerzeile zwei Absätze einer Funktion trennt – und genau dann
        braucht man sie am meisten.
        """
        dokument = self.document()
        block = dokument.findBlockByNumber(blocknummer)
        while block.isValid():
            text = block.text()
            if text.strip():
                return len(_EINZUG_MUSTER.match(text).group().expandtabs(4)) // len(
                    _EINZUG
                )
            block = block.next()
        return 0

    def _einzugslinien_zeichnen(self, event: QPaintEvent) -> None:
        """Eine senkrechte Linie je Einrückungsebene.

        Bei Python **ist** die Einrückung die Syntax – wer sie nicht
        sieht, sucht seinen Fehler an der falschen Stelle. Gezeichnet
        wird hinter den Text, damit sie ihn nie verdeckt.
        """
        maler = QPainter(self.viewport())
        maler.setPen(QColor(_EINZUGSLINIEN_FARBEN.get(self._thema, "#e4e4e4")))
        spaltenbreite = self.fontMetrics().horizontalAdvance(_EINZUG)
        links = round(self.contentOffset().x())
        for blocknummer, oben, unten in self._fuer_jeden_sichtbaren_block(event.rect()):
            for ebene in range(1, self.einzugstiefe(blocknummer)):
                x = links + ebene * spaltenbreite
                maler.drawLine(x, oben, x, unten)

    def paintEvent(self, event: QPaintEvent) -> None:
        if self.einzugslinien_sichtbar:
            self._einzugslinien_zeichnen(event)
        super().paintEvent(event)

    # -- Vervollständigung (M11, Abschnitt 2.2) --------------------------

    def vervollstaendigung_setzen(self, an: bool) -> None:
        self.vervollstaendigung_an = an
        if not an:
            self.vorschlagsliste_schliessen()

    def _wort_vor_dem_cursor(self) -> str:
        """Was gerade getippt wird – ohne den Punkt davor."""
        cursor = self.textCursor()
        links = cursor.block().text()[: cursor.positionInBlock()]
        return _WORT_MUSTER.search(links).group() if _WORT_MUSTER.search(links) else ""

    def vorschlaege_anzeigen(self, erzwungen: bool = False) -> int:
        """Baut die Vorschlagsliste und zeigt sie. Liefert, wie viele
        Vorschläge es gab.

        `erzwungen` ist Strg+Leertaste: dann erscheint die Liste auch
        nach einem Punkt, wo noch gar nichts getippt wurde – genau dort
        braucht man sie am meisten.
        """
        if not self.vervollstaendigung_an:
            return 0
        cursor = self.textCursor()
        links = cursor.block().text()[: cursor.positionInBlock()]
        wort = self._wort_vor_dem_cursor()
        nach_punkt = links.rstrip().endswith(".")
        if not erzwungen and not nach_punkt and len(wort) < MINDESTZEICHEN:
            self.vorschlagsliste_schliessen()
            return 0

        gefunden = vorschlaege(
            self.toPlainText(),
            cursor.blockNumber() + 1,
            cursor.positionInBlock(),
            self.property(_PFAD_EIGENSCHAFT),
        )
        if not gefunden:
            self.vorschlagsliste_schliessen()
            return 0

        self._vorschlaege = gefunden
        self.vorschlagsliste.clear()
        for vorschlag in gefunden:
            self.vorschlagsliste.addItem(vorschlag.anzeige)
        self.vorschlagsliste.setCurrentRow(0)
        self._vorschlagsliste_platzieren()
        self.vorschlagsliste.show()
        return len(gefunden)

    def _vorschlagsliste_platzieren(self) -> None:
        """Direkt unter die Schreibmarke, aber immer innerhalb des
        Fensters: am unteren Rand klappt die Liste nach oben auf, sonst
        stünde sie halb außerhalb."""
        rechteck = self.cursorRect()
        sicht = self.viewport()
        breite = min(640, max(320, sicht.width() - rechteck.left() - 8))
        links = min(rechteck.left(), max(0, sicht.width() - breite))

        # Auf die Seite mit mehr Luft, und nur so hoch, wie dort Platz
        # ist. Sonst klappte die Liste bei einem kleinen Editor ganz
        # nach oben und stand weit weg von der Schreibmarke (im
        # Bildschirmfoto so gesehen).
        darunter = sicht.height() - rechteck.bottom() - 4
        darueber = rechteck.top() - 4
        nach_unten = darunter >= darueber
        platz = max(44, darunter if nach_unten else darueber)
        zeilen = min(8, max(1, self.vorschlagsliste.count()))
        hoehe = min(zeilen * 22 + 8, platz)
        oben = rechteck.bottom() + 2 if nach_unten else max(0, rechteck.top() - hoehe - 2)
        self.vorschlagsliste.setGeometry(links, oben, breite, hoehe)
        self.vorschlagsliste.raise_()

    def focusOutEvent(self, event) -> None:
        """Wer woanders hinklickt, meint die Liste nicht mehr. Bliebe
        sie stehen, schwebte sie über einem Editor, in dem gar nicht
        mehr getippt wird."""
        self.vorschlagsliste_schliessen()
        super().focusOutEvent(event)

    def scrollContentsBy(self, dx: int, dy: int) -> None:
        """Beim Rollen wandert die Schreibmarke unter der Liste weg –
        sie zeigte dann auf eine Stelle, die gar nicht mehr da ist."""
        if dy and self.vorschlagsliste.isVisible():
            self.vorschlagsliste_schliessen()
        super().scrollContentsBy(dx, dy)

    def vorschlagsliste_schliessen(self) -> None:
        self.vorschlagsliste.hide()
        self._vorschlaege = []

    def vorschlag_uebernehmen(self, zeile: int | None = None) -> bool:
        """Setzt den gewählten Vorschlag ein. Ersetzt dabei das bereits
        Getippte, statt es zu verdoppeln."""
        if not self._vorschlaege or not self.vorschlagsliste.isVisible():
            return False
        nummer = self.vorschlagsliste.currentRow() if zeile is None else zeile
        if not 0 <= nummer < len(self._vorschlaege):
            return False
        name = self._vorschlaege[nummer].name
        bereits = self._wort_vor_dem_cursor()

        cursor = self.textCursor()
        for _ in range(len(bereits)):
            cursor.deletePreviousChar()
        cursor.insertText(name)
        self.setTextCursor(cursor)
        self.vorschlagsliste_schliessen()
        return True

    def parameterhilfe_anzeigen(self) -> str:
        """Zeigt beim Tippen der öffnenden Klammer, welche Parameter
        erwartet werden – als Kurzhinweis über dem Cursor."""
        if not self.vervollstaendigung_an:
            return ""
        cursor = self.textCursor()
        text = parameterhilfe(
            self.toPlainText(),
            cursor.blockNumber() + 1,
            cursor.positionInBlock(),
            self.property(_PFAD_EIGENSCHAFT),
        )
        if text:
            QToolTip.showText(
                self.mapToGlobal(self.cursorRect().topLeft()), text, self
            )
        else:
            QToolTip.hideText()
        return text

    def _zeilennummern_zeichnen(self, event: QPaintEvent) -> None:
        maler = QPainter(self._rand)
        maler.fillRect(event.rect(), QColor(self._rand_farben["hintergrund"]))
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
            maler.setPen(QColor(self._rand_farben["zeilennummer"]))
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
            auswahl.format.setBackground(QColor(self._rand_farben["aktuelle_zeile"]))
            auswahl.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            auswahl.cursor = self.textCursor()
            auswahl.cursor.clearSelection()
            auswahlen.append(auswahl)
        self.setExtraSelections(auswahlen)
