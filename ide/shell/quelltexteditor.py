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

from PySide6.QtCore import QEvent, QPointF, QRect, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QResizeEvent,
    QTextCharFormat,
    QTextCursor,
    QTextFormat,
    QTextOption,
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
    Fundstelle,
    Vorschlag,
    definition,
    parameterhilfe,
    vorschlaege,
)
from pcl.pruefungsmodus import laeuft as pruefungsmodus_laeuft

_SCHRIFT_DATEI = (
    Path(__file__).resolve().parent.parent / "assets" / "fonts" / "CascadiaCode-Regular.ttf"
)
_schriftart_geladen = False


def _cascadia_code_bereitstellen() -> None:
    """Lädt Cascadia Code aus der mitgelieferten Schriftdatei in die
    Anwendungsschrift-Datenbank von Qt. Gewünscht war: „wenn Schriftart
    nicht installiert, soll diese installiert werden“ - ohne
    Systeminstallation, passend dazu, dass Natter portabel bleibt
    (Abschnitt 17).

    Einmal pro Prozess; danach findet `QFont(["Cascadia Code", ...])`
    sie zuverlässig, gleichgültig ob sie auf dem Rechner selbst
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

#: Was beim Tippen selbst geschlossen wird (M11, 2.3).
_KLAMMER_PAARE = {"(": ")", "[": "]", "{": "}", '"': '"', "'": "'"}
_KLAMMER_ZU = set(_KLAMMER_PAARE.values())

#: Grenzen der Schriftgröße für Strg+Mausrad. Wer sich auf 2 pt
#: herunterdreht, findet den Weg zurück nicht mehr.
_MIN_SCHRIFT = 7
_MAX_SCHRIFT = 32

#: Farbe der Wellenlinie unter einem Fund (M11, 2.3). Dieselbe wie im
#: Design-Prüfer der Formulare: ein Hinweis, kein Fehler.
_FUND_FARBE = "#d97706"

_EINZUG = "    "
_EINZUG_MUSTER = re.compile(r"[ \t]*")
_BREAKPOINT_DURCHMESSER = 10
_BREAKPOINT_SPALTE_BREITE = _BREAKPOINT_DURCHMESSER + 6

#: Streifen rechts im Rand für die Faltzeichen (M11, 2.3).
_FALT_SPALTE_BREITE = 14

#: Zeilen, die eine Klasse oder Funktion eröffnen. Nur diese lassen
#: sich falten. Die Wortgrenze am Ende ist nötig, damit
#: `definiere = 1` nicht als Funktionskopf durchgeht.
_KOPF_MUSTER = re.compile(r"^[ \t]*(class|async def|def)\b")

# Rand-/Zeilenhervorhebungsfarben je Thema (Abschnitt 6, „Ansicht →
# Design“, Gewünscht: Dark-Mode-Farben sollen zum
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

# Gemeldet: Cascadia Code wirkte auf dem
# echten Rechner trotz mitgelieferter Schriftdatei weiterhin wie die
# Standardschrift - Consolas (ein garantierter Windows-Systemfont,
# kein Bundling nötig) steht deshalb an erster Stelle. Zusätzlich
# als Auswahl im Menü „Ansicht → Schriftart“ angeboten (Gemeldet: 
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
        self._editor._rand_klick_verarbeiten(
            event.position().x(), event.position().y()
        )


class QuelltextEditor(QPlainTextEdit):
    breakpoint_umgeschaltet = Signal(int, bool)  # (Zeile ab 1, jetzt gesetzt?)

    #: F12. Der Editor kennt weder das Projekt noch die anderen Tabs -
    #: das Springen selbst macht deshalb das Hauptfenster.
    definition_gesucht = Signal()

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

        # Kein Zeilenumbruch (M11, Abschnitt 2.3). Qt
        # bricht von sich aus um; in Python trägt die Einrückung aber
        # Bedeutung, und eine umgebrochene Zeile sieht aus wie zwei -
        # mitsamt einer Einrückung, die gar nicht im Text steht.
        # Über „Ansicht → Zeilenumbruch“ schaltbar.
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        #: Leerzeichen und Tabulatoren sichtbar (M11, 2.1)
        self.leerzeichen_sichtbar = False

        #: Funde aus ruff und dem Fehlerkatalog (M11, 2.3)
        self._funde: dict[int, str] = {}
        self._fundmarkierungen: list[QTextEdit.ExtraSelection] = []
        self._zeilenmarkierung: list[QTextEdit.ExtraSelection] = []

        #: Vervollständigung (M11, 2.2)
        self.vervollstaendigung_an = True
        self._vorschlaege: list[Vorschlag] = []
        # Kind des Viewports, kein eigenes Fenster. Mit
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

        #: Zugeklappte Klassen und Funktionen, je Kopfzeile (M11, 2.3)
        self._gefaltet: set[int] = set()
        self._rand = _ZeilenNummernRand(self)
        self.blockCountChanged.connect(self._breite_aktualisieren)
        self.updateRequest.connect(self._rand_aktualisieren)
        self.cursorPositionChanged.connect(self._aktuelle_zeile_hervorheben)
        self.textChanged.connect(self._faltungen_pruefen)
        self._breite_aktualisieren()
        self._aktuelle_zeile_hervorheben()

    def zeilennummernrand_breite(self) -> int:
        stellen = len(str(max(1, self.blockCount())))
        return (
            _BREAKPOINT_SPALTE_BREITE
            + _RAND_ABSTAND
            + _FALT_SPALTE_BREITE
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
        """Automatischer Einzug (Gewünscht: „was
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

        strg = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        alt = bool(event.modifiers() & Qt.KeyboardModifier.AltModifier)
        if strg and event.key() == Qt.Key.Key_D:
            self.zeile_duplizieren()
            return
        if alt and event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            self.zeile_verschieben(event.key() == Qt.Key.Key_Down)
            return
        if event.key() == Qt.Key.Key_F12 and not event.modifiers():
            self.definition_gesucht.emit()
            return
        if not event.modifiers() and self._klammer_schliessen(event):
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
        """Rücktaste im Einzug löscht eine ganze Ebene.

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

        Eine leere Zeile hat für sich genommen keine Einrückung; sie
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

        Bei Python ist die Einrückung die Syntax – wer sie nicht
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
        # Im Prüfungsmodus ohne die deutschen Erklärungen (M11,
        # Abschnitt 6). Die Liste selbst bleibt an - sie ist
        # Schreibhilfe; „Wird beim Klicken ausgelöst“ neben
        # `on_click` ist dagegen nah an
        # der Antwort auf genau die Frage, die in der Klausur steht.
        mit_erklaerung = not pruefungsmodus_laeuft()
        for vorschlag in gefunden:
            self.vorschlagsliste.addItem(vorschlag.anzeige_text(mit_erklaerung))
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

    # -- Funde direkt im Quelltext (M11, Abschnitt 2.3) ------------------

    def funde_setzen(self, funde: dict[int, str]) -> int:
        """Unterringelt die genannten Zeilen (ab 1) und legt die
        deutsche Meldung als Tooltip darunter.

        Bis jetzt stand ein Fund nur in der Meldungsliste unter dem
        Editor. Wer ihn dort nicht anklickt, sieht nichts – und gerade
        wer gerade erst anfängt, schaut nicht nach unten, sondern auf
        die Zeile, die er eben getippt hat.
        """
        self._funde = dict(funde)
        self._funde_anwenden()
        return len(self._funde)

    def funde_loeschen(self) -> None:
        self.funde_setzen({})

    def fund_bei(self, zeile: int) -> str:
        """Die Meldung zu einer Zeile (ab 1), oder leer."""
        return self._funde.get(zeile, "")

    def _funde_anwenden(self) -> None:
        """Malt die Wellenlinien. Zusammen mit der Hervorhebung der
        aktuellen Zeile, weil Qt beide über dieselbe Liste führt – sie
        getrennt zu setzen löschte jeweils die andere."""
        dokument = self.document()
        markierungen: list[QTextEdit.ExtraSelection] = []
        for zeile in sorted(self._funde):
            block = dokument.findBlockByNumber(zeile - 1)
            if not block.isValid():
                continue
            auswahl = QTextEdit.ExtraSelection()
            auswahl.format.setUnderlineColor(QColor(_FUND_FARBE))
            auswahl.format.setUnderlineStyle(
                QTextCharFormat.UnderlineStyle.WaveUnderline
            )
            auswahl.format.setToolTip(self._funde[zeile])
            cursor = QTextCursor(block)
            # Erst ab dem ersten sichtbaren Zeichen: eine Wellenlinie
            # unter der Einrückung sieht aus, als wäre die Einrückung
            # das Problem - und genau da sucht ein Anfänger dann.
            text = block.text()
            cursor.setPosition(block.position() + len(text) - len(text.lstrip()))
            cursor.movePosition(
                QTextCursor.MoveOperation.EndOfBlock,
                QTextCursor.MoveMode.KeepAnchor,
            )
            if not cursor.hasSelection():
                # Leerzeile: nichts zu unterringeln, der Tooltip bleibt
                continue
            auswahl.cursor = cursor
            markierungen.append(auswahl)
        self._fundmarkierungen = markierungen
        self._markierungen_setzen()

    def _markierungen_setzen(self) -> None:
        self.setExtraSelections(
            [*self._fundmarkierungen, *self._zeilenmarkierung]
        )

    def event(self, ereignis) -> bool:
        """Tooltip über einer unterringelten Zeile – die deutsche
        Meldung dort, wo der Fehler steht."""
        if ereignis.type() == QEvent.Type.ToolTip and self._funde:
            punkt = ereignis.pos()
            zeile = self.cursorForPosition(punkt).blockNumber() + 1
            meldung = self._funde.get(zeile, "")
            if meldung:
                QToolTip.showText(ereignis.globalPos(), meldung, self)
            else:
                QToolTip.hideText()
            return True
        return super().event(ereignis)

    # -- Weitere Hilfen im Editor (M11, Abschnitt 2.3) -------------------

    def _klammer_schliessen(self, event: QKeyEvent) -> bool:
        """Schließt Klammern und Anführungszeichen selbst.

        Zwei Regeln, die sich im Unterricht bewähren und nicht im Weg
        stehen:

        * Ist gerade Text markiert, wird er umschlossen statt
          ersetzt – wer `name` markiert und `"` tippt, will
          `"name"`, nicht den Text weg
        * Ein schließendes Zeichen, das ohnehin schon dasteht, wird
          übersprungen statt verdoppelt. Sonst entstünde bei jedem
          getippten `)` ein `))`, und das ist der Fehler, den man am
          Bildschirm am schlechtesten sieht
        """
        zeichen = event.text()
        cursor = self.textCursor()

        if zeichen in _KLAMMER_PAARE:
            partner = _KLAMMER_PAARE[zeichen]
            if cursor.hasSelection():
                text = cursor.selectedText()
                cursor.insertText(f"{zeichen}{text}{partner}")
                self.setTextCursor(cursor)
                return True
            cursor.insertText(zeichen + partner)
            cursor.movePosition(cursor.MoveOperation.Left)
            self.setTextCursor(cursor)
            return True

        if zeichen and zeichen in _KLAMMER_ZU and not cursor.hasSelection():
            rechts = cursor.block().text()[cursor.positionInBlock() :]
            if rechts.startswith(zeichen):
                cursor.movePosition(cursor.MoveOperation.Right)
                self.setTextCursor(cursor)
                return True
        return False

    def zeile_duplizieren(self) -> None:
        """Strg+D: die aktuelle Zeile noch einmal darunter."""
        cursor = self.textCursor()
        text = cursor.block().text()
        cursor.movePosition(cursor.MoveOperation.EndOfBlock)
        cursor.insertText("\n" + text)
        self.setTextCursor(cursor)

    def zeile_verschieben(self, nach_unten: bool) -> bool:
        """Alt+Pfeil: die aktuelle Zeile eine Position nach oben oder
        unten. Liefert `False`, wenn es dort nicht weitergeht."""
        dokument = self.document()
        cursor = self.textCursor()
        nummer = cursor.blockNumber()
        ziel = nummer + (1 if nach_unten else -1)
        if not 0 <= ziel < dokument.blockCount():
            return False

        spalte = cursor.positionInBlock()
        zeilen = self.toPlainText().split("\n")
        zeilen[nummer], zeilen[ziel] = zeilen[ziel], zeilen[nummer]

        # In einem Rutsch, damit ein einziges Strg+Z es zurücknimmt -
        # sonst wären es drei Schritte, und man müsste dreimal drücken.
        cursor.beginEditBlock()
        cursor.select(cursor.SelectionType.Document)
        cursor.insertText("\n".join(zeilen))
        cursor.endEditBlock()

        neu = self.textCursor()
        neu.setPosition(dokument.findBlockByNumber(ziel).position() + spalte)
        self.setTextCursor(neu)
        return True

    def zeilenumbruch_setzen(self, an: bool) -> None:
        """„Ansicht → Zeilenumbruch“: lange Zeilen umbrechen statt
        waagerecht zu rollen."""
        self.setLineWrapMode(
            QPlainTextEdit.LineWrapMode.WidgetWidth
            if an
            else QPlainTextEdit.LineWrapMode.NoWrap
        )

    def schriftgroesse_aendern(self, schritte: int) -> int:
        """Strg+Mausrad: größer oder kleiner. Begrenzt, damit sich
        niemand aus Versehen auf 2 pt herunterdreht und den Weg zurück
        nicht mehr findet."""
        schrift = self.font()
        neu = max(_MIN_SCHRIFT, min(_MAX_SCHRIFT, schrift.pointSize() + schritte))
        if neu == schrift.pointSize():
            return neu
        schrift.setPointSize(neu)
        self.setFont(schrift)
        self._breite_aktualisieren()
        self.viewport().update()
        return neu

    def wheelEvent(self, event) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.schriftgroesse_aendern(1 if event.angleDelta().y() > 0 else -1)
            event.accept()
            return
        super().wheelEvent(event)

    # -- Leerzeichen sichtbar machen (M11, Abschnitt 2.1) ----------------

    def leerzeichen_setzen(self, sichtbar: bool) -> None:
        """Zeigt Leerzeichen als Punkte und Tabulatoren als Pfeile.

        Normalerweise aus: das Bild wird unruhig, und wer es nicht
        braucht, soll es nicht sehen. Gebraucht wird es an genau einer
        Stelle, dort aber dringend – wenn eine aus dem Netz kopierte
        Zeile Tabulatoren mitbringt und Python mit `TabError` abbricht,
        ohne dass am Bildschirm irgendetwas anders aussieht.
        """
        self.leerzeichen_sichtbar = sichtbar
        einstellung = self.document().defaultTextOption()
        marke = QTextOption.Flag.ShowTabsAndSpaces
        vorher = einstellung.flags()
        einstellung.setFlags(vorher | marke if sichtbar else vorher & ~marke)
        self.document().setDefaultTextOption(einstellung)
        self.viewport().update()

    # -- Einfügen mit passender Einrückung (M11, Abschnitt 2.1) ----------

    def insertFromMimeData(self, quelle) -> None:
        """Beim Einfügen die Einrückung an die Zielstelle anpassen.

        Aus einer Aufgabenstellung kopierter Quelltext bringt die
        Einrückung seiner alten Umgebung mit. Eingefügt in eine
        Methode, stand er dann auf der falschen Ebene – und in Python
        ist das kein Schönheitsfehler, sondern ein `IndentationError`.
        Die relative Einrückung innerhalb des eingefügten Stücks
        bleibt erhalten; verschoben wird der Block als Ganzes.

        Angefasst wird nur mehrzeiliger Text. Ein einzelnes Wort oder
        eine Zeile aus dem Browser geht unverändert durch.
        """
        if not quelle.hasText():
            super().insertFromMimeData(quelle)
            return
        text = quelle.text().replace("\r\n", "\n").replace("\r", "\n")
        if "\n" not in text:
            super().insertFromMimeData(quelle)
            return
        self.textCursor().insertText(self.eingefuegt_einruecken(text))

    def eingefuegt_einruecken(self, text: str) -> str:
        """Der einzufügende Text, auf die Einrückung der Zielstelle
        gebracht. Eigene Methode, damit sich die Rechnung ohne
        Zwischenablage prüfen lässt."""
        # Tabulatoren zuerst: gemischte Einrückung ist der Fehler, den
        # man am Bildschirm am schlechtesten sieht.
        zeilen = [zeile.replace("\t", _EINZUG) for zeile in text.split("\n")]
        inhalt = [zeile for zeile in zeilen if zeile.strip()]
        if not inhalt:
            return "\n".join(zeilen)

        gemeinsam = min(len(zeile) - len(zeile.lstrip()) for zeile in inhalt)
        cursor = self.textCursor()
        links = cursor.block().text()[: cursor.positionInBlock()]
        ziel = _EINZUG_MUSTER.match(cursor.block().text()).group()

        ergebnis = []
        for nummer, zeile in enumerate(zeilen):
            rest = zeile[gemeinsam:] if zeile.strip() else ""
            if nummer == 0:
                # Die erste Zeile schließt dort an, wo der Cursor steht
                # - was links davon steht, steht schon im Text. Ein
                # Einzug davor käme zu dem bereits vorhandenen hinzu.
                ergebnis.append(zeile.strip() if links.strip() else rest)
            else:
                ergebnis.append(ziel + rest if rest else "")
        return "\n".join(ergebnis)

    # -- Zu einer Definition springen (M11, Abschnitt 2.3) ---------------

    def definition_unter_cursor(
        self, projekt: Path | str | None = None
    ) -> Fundstelle | None:
        """Wo der Name unter dem Cursor definiert wurde, oder `None`.

        F12. In einer Klasse mit zehn Methoden ist das Blättern nach
        „wo steht das eigentlich“ der häufigste Grund, den Faden zu
        verlieren.
        """
        cursor = self.textCursor()
        return definition(
            self.toPlainText(),
            cursor.blockNumber() + 1,
            cursor.positionInBlock(),
            pfad=self.property(_PFAD_EIGENSCHAFT),
            projekt=projekt,
        )

    def zu_zeile_springen(self, zeile: int, spalte: int = 0) -> None:
        """Setzt den Cursor auf `zeile` (ab 1) und rollt sie in die
        Mitte – am oberen Rand sieht man den Zusammenhang nicht."""
        block = self.document().findBlockByNumber(max(0, zeile - 1))
        if not block.isValid():
            return
        cursor = self.textCursor()
        cursor.setPosition(block.position() + min(spalte, len(block.text())))
        self.setTextCursor(cursor)
        self.centerCursor()

    # -- Code falten (M11, Abschnitt 2.3) --------------------------------

    def faltbare_zeilen(self) -> dict[int, int]:
        """Zu jeder Zeile, die eine Klasse oder Funktion eröffnet, die
        letzte Zeile ihres Rumpfes (beides ab 1).

        Nur `class` und `def`: bei einer Datei mit zehn Methoden ist
        das der Grund, warum man den Überblick verliert. Eine
        zusammengeklappte `if`-Abfrage dagegen versteckte gerade das,
        worauf es im Unterricht ankommt.
        """
        zeilen = self.toPlainText().split("\n")
        anfaenge: dict[int, int] = {}
        for nummer, zeile in enumerate(zeilen):
            if not _KOPF_MUSTER.match(zeile):
                continue
            einzug = len(zeile) - len(zeile.lstrip())
            letzte = nummer
            for weiter in range(nummer + 1, len(zeilen)):
                folge = zeilen[weiter]
                if not folge.strip():
                    continue
                if len(folge) - len(folge.lstrip()) <= einzug:
                    break
                letzte = weiter
            if letzte > nummer:
                anfaenge[nummer + 1] = letzte + 1
        return anfaenge

    def falt_umschalten(self, zeile: int) -> bool:
        """Klappt die Klasse oder Funktion in `zeile` zu oder auf.
        Liefert, ob sie danach zugeklappt ist."""
        if zeile not in self.faltbare_zeilen():
            return False
        if zeile in self._gefaltet:
            self.entfalten(zeile)
            return False
        self.falten(zeile)
        return True

    def falten(self, zeile: int) -> None:
        """Versteckt den Rumpf der Klasse oder Funktion in `zeile`."""
        ende = self.faltbare_zeilen().get(zeile)
        if ende is None:
            return
        self._gefaltet.add(zeile)
        self._sichtbarkeit_setzen(zeile + 1, ende, sichtbar=False)

    def entfalten(self, zeile: int) -> None:
        """Zeigt den Rumpf wieder."""
        ende = self.faltbare_zeilen().get(zeile)
        self._gefaltet.discard(zeile)
        if ende is None:
            return
        self._sichtbarkeit_setzen(zeile + 1, ende, sichtbar=True)
        # Eine innen liegende Faltung bleibt zu: wer eine Klasse
        # aufklappt, will nicht alle ihre Methoden offen haben.
        for innen in sorted(self._gefaltet):
            if zeile < innen <= ende:
                self.falten(innen)

    def alles_entfalten(self) -> None:
        """Alles wieder aufklappen – der Ausweg, wenn man den Überblick
        verloren hat, welche Zeile wo versteckt ist."""
        for zeile in sorted(self._gefaltet):
            self.entfalten(zeile)
        self._gefaltet.clear()

    def _sichtbarkeit_setzen(self, von: int, bis: int, *, sichtbar: bool) -> None:
        dokument = self.document()
        for nummer in range(von - 1, bis):
            block = dokument.findBlockByNumber(nummer)
            if not block.isValid():
                continue
            block.setVisible(sichtbar)
            # Ohne `setLineCount(0)` behält Qt die Höhe der Zeile bei,
            # und die zugeklappte Funktion hinterlässt eine Lücke.
            block.setLineCount(1 if sichtbar else 0)
        dokument.markContentsDirty(0, dokument.characterCount())
        self._breite_aktualisieren()
        self.viewport().update()
        self._rand.update()

    def _faltungen_pruefen(self) -> None:
        """Nach jeder Änderung: eine Faltung, deren Kopfzeile keine mehr
        ist, wird aufgehoben.

        Sonst bliebe Text unsichtbar, den es gar nicht mehr zu falten
        gibt – und niemand käme auf die Idee, dass da noch etwas steht.
        """
        faltbar = self.faltbare_zeilen()
        for zeile in sorted(self._gefaltet):
            if zeile not in faltbar:
                self._gefaltet.discard(zeile)
                self._alles_sichtbar_machen()
                return

    def _alles_sichtbar_machen(self) -> None:
        dokument = self.document()
        for nummer in range(dokument.blockCount()):
            block = dokument.findBlockByNumber(nummer)
            block.setVisible(True)
            block.setLineCount(1)
        dokument.markContentsDirty(0, dokument.characterCount())
        self.viewport().update()
        self._rand.update()
        for zeile in sorted(self._gefaltet):
            self.falten(zeile)

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
                self._rand.width() - _FALT_SPALTE_BREITE - _RAND_ABSTAND // 2,
                hoehe,
                Qt.AlignmentFlag.AlignRight,
                str(zeile),
            )
            if zeile in self.faltbare_zeilen():
                self._faltzeichen_zeichnen(maler, oben, hoehe, zeile in self._gefaltet)

    def _faltzeichen_zeichnen(
        self, maler: QPainter, oben: float, hoehe: float, zugeklappt: bool
    ) -> None:
        """Ein kleines Dreieck: nach rechts für „zugeklappt“, nach unten
        für „offen“ – dieselbe Sprache wie im Projekt-Explorer daneben.

        Filigran, nicht als Kasten mit Plus darin: der Rand soll die
        Zeilennummern nicht überstimmen.
        """
        mitte_x = self._rand.width() - _FALT_SPALTE_BREITE / 2
        mitte_y = oben + hoehe / 2
        halb = 3.5
        maler.setBrush(QColor(self._rand_farben["zeilennummer"]))
        maler.setPen(Qt.PenStyle.NoPen)
        if zugeklappt:
            ecken = [
                QPointF(mitte_x - halb / 2, mitte_y - halb),
                QPointF(mitte_x - halb / 2, mitte_y + halb),
                QPointF(mitte_x + halb, mitte_y),
            ]
        else:
            ecken = [
                QPointF(mitte_x - halb, mitte_y - halb / 2),
                QPointF(mitte_x + halb, mitte_y - halb / 2),
                QPointF(mitte_x, mitte_y + halb),
            ]
        maler.drawPolygon(ecken)

    def _rand_klick_verarbeiten(self, x: float, y: float) -> None:
        """Links im Rand der Haltepunkt, rechts das Falten.

        Der Streifen ganz rechts gehört dem Falten, alles übrige dem
        Haltepunkt, der damit direkt neben der Zeilennummer sitzt.
        """
        rect = QRect(0, 0, self._rand.width(), self._rand.height())
        falten = x >= self._rand.width() - _FALT_SPALTE_BREITE
        for blocknummer, oben, unten in self._fuer_jeden_sichtbaren_block(rect):
            if oben <= y < unten:
                if falten:
                    self.falt_umschalten(blocknummer + 1)
                else:
                    self.breakpoint_umschalten(blocknummer + 1)
                return

    def _aktuelle_zeile_hervorheben(self) -> None:
        """Qt führt Zeilenhervorhebung und Wellenlinien über eine
        Liste. Sie getrennt zu setzen löschte jeweils die andere: die
        Unterringelungen verschwanden beim ersten Cursorwechsel wieder.
        Beide gehen deshalb über `_markierungen_setzen`."""
        auswahlen: list[QTextEdit.ExtraSelection] = []
        if not self.isReadOnly():
            auswahl = QTextEdit.ExtraSelection()
            auswahl.format.setBackground(QColor(self._rand_farben["aktuelle_zeile"]))
            auswahl.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            auswahl.cursor = self.textCursor()
            auswahl.cursor.clearSelection()
            auswahlen.append(auswahl)
        self._zeilenmarkierung = auswahlen
        self._markierungen_setzen()
