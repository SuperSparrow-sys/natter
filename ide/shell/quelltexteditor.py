"""QuelltextEditor: `QPlainTextEdit` mit Zeilennummernrand,
hervorgehobener aktueller Zeile, klickbaren Breakpoints im Rand (wie in
den meisten IDEs, Abschnitt 8.1) und Python-Syntax-Hervorhebung
(`ide.shell.python_hervorhebung`).

Standardmuster aus der Qt-Dokumentation („Code Editor Example“), mit
deutschen Bezeichnern. Monaco war vorgesehen und ist verworfen (siehe
`docs/bericht.md`, Abschnitt 4); die Syntax-Hervorhebung ist
regelbasiert statt über eine vollständige Grammatik.
"""

from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtCore import (
    QEvent,
    QObject,
    QPoint,
    QPointF,
    QRect,
    QSize,
    Qt,
    QTimer,
    Signal,
)
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
    QMenu,
    QPlainTextEdit,
    QTextEdit,
    QToolTip,
    QWidget,
)

from ide.shell.python_hervorhebung import PythonHervorhebung
from ide.shell.tastenkuerzel import EDITORBEFEHLE
from ide.shell.vervollstaendigung import (
    MINDESTZEICHEN,
    Fundstelle,
    Vorschlag,
    definition,
    im_hintergrund,
    parameterhilfe_anzeige,
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
#: Ein Haltepunkt mit Bedingung (Punkt 100): orange statt rot, damit
#: man sieht, dass er nicht immer hält.
_BEDINGT_FARBE = QColor("#e67e22")
#: Die Eigenschaft, unter der das Hauptfenster den Dateipfad am Editor
#: ablegt. jedi arbeitet damit deutlich besser - es findet dann die
#: Nachbardateien des Projekts.
_PFAD_EIGENSCHAFT = "pfad"
#: Das Wort, das gerade getippt wird.
_WORT_MUSTER = re.compile(r"[A-Za-z_]\w*$")
#: So lange nach dem letzten Tastendruck wartet die Vervollständigung,
#: bevor jedi rechnet (Punkt 313). Wer zügig tippt, bekommt die Liste
#: erst in der nächsten Pause; bis dahin kostet ein Tastendruck nichts.
_VORSCHLAG_PAUSE_MS = 150


class _Bote(QObject):
    """Bringt die Vorschläge aus dem Nebenfaden zum Editor.

    Ein Kind des Editors: wird der Editor geschlossen, während jedi
    noch rechnet, verschwindet der Bote mit ihm, und das Ergebnis geht
    ins Leere. Der Nebenfaden hält nur den Boten, nie den Editor selbst;
    sonst könnte der Editor im Nebenfaden abgeräumt werden.
    """

    fertig = Signal(int, object)

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
    "light": {"hintergrund": "#f0f0f0", "zeilennummer": "#8a8a8a", "aktuelle_zeile": "#eaf2fc",
              "klammerpaar": "#c6dcf5"},
    "dark": {"hintergrund": "#252526", "zeilennummer": "#858585", "aktuelle_zeile": "#2a2d2e",
             "klammerpaar": "#3b5570"},
}

#: Klammerpaare für die Hervorhebung am Cursor (Punkt 103).
_AUF_ZU = {"(": ")", "[": "]", "{": "}"}
_ZU_AUF = {zu: auf for auf, zu in _AUF_ZU.items()}
#: So weit wird nach der Gegenklammer gesucht - in einer Schuldatei
#: reicht das weit, und ein Tastendruck bleibt schnell.
_KLAMMER_SUCHWEITE = 20_000

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


def _code_maske(text: str) -> list[bool]:
    """Für jedes Zeichen: gehört es zum Code (nicht zu einem Text in
    Anführungszeichen, nicht zu einem Kommentar)? Grob, aber für das
    Finden einer Gegenklammer genau genug."""
    maske = [True] * len(text)
    i = 0
    while i < len(text):
        zeichen = text[i]
        if zeichen == "#":
            while i < len(text) and text[i] != "\n":
                maske[i] = False
                i += 1
            continue
        if zeichen in "'\"":
            dreifach = text[i : i + 3] == zeichen * 3
            ende = zeichen * 3 if dreifach else zeichen
            j = i + len(ende)
            while j < len(text) and text[j : j + len(ende)] != ende:
                if text[j] == "\\":
                    j += 1
                if not dreifach and j < len(text) and text[j] == "\n":
                    break
                j += 1
            j = min(len(text), j + len(ende))
            for k in range(i, j):
                maske[k] = False
            i = j
            continue
        i += 1
    return maske


def schreibmarke_im_code(links: str, in_dreifach: bool = False) -> bool:
    """Steht die Schreibmarke hinter `links` im Code, also weder in
    einem Kommentar noch in einer Zeichenkette?

    `links` ist die Zeile bis zur Schreibmarke. `in_dreifach` heißt,
    dass die Zeile in einer mehrzeiligen Zeichenkette beginnt; das
    weiß die Hervorhebung aus der Zeile davor. Welches Zeichen sie
    geöffnet hat, merkt sie sich nicht. Genommen wird deshalb das
    erste dreifache Anführungszeichen der Zeile, denn nur das kann
    sie schließen.
    """
    if in_dreifach:
        doppelt, einfach = links.find('"""'), links.find("'''")
        if einfach >= 0 and (doppelt < 0 or einfach < doppelt):
            links = "'''" + links
        else:
            links = '"""' + links
    # Ein Zeichen als Stellvertreter für das nächste, das getippt wird.
    return _code_maske(links + "x")[-1]


def _gegenklammer(text: str, stelle: int) -> int | None:
    anfang = max(0, stelle - _KLAMMER_SUCHWEITE)
    ende = min(len(text), stelle + _KLAMMER_SUCHWEITE)
    ausschnitt = text[anfang:ende]
    maske = _code_maske(ausschnitt)
    i = stelle - anfang
    if not maske[i]:
        return None
    zeichen = ausschnitt[i]
    if zeichen in _AUF_ZU:
        ziel, schritt = _AUF_ZU[zeichen], 1
    else:
        ziel, schritt = _ZU_AUF[zeichen], -1
    tiefe = 0
    while 0 <= i < len(ausschnitt):
        if maske[i]:
            if ausschnitt[i] == zeichen:
                tiefe += 1
            elif ausschnitt[i] == ziel:
                tiefe -= 1
                if tiefe == 0:
                    return anfang + i
        i += schritt
    return None


class _ZeilenNummernRand(QWidget):
    def __init__(self, editor: QuelltextEditor) -> None:
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self._editor.zeilennummernrand_breite(), 0)

    def paintEvent(self, event: QPaintEvent) -> None:
        self._editor._zeilennummern_zeichnen(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self._editor._rand_klick_verarbeiten(
            event.position().x(), event.position().y()
        )

    def contextMenuEvent(self, event) -> None:  # noqa: ANN001
        menue = self._editor.rand_kontextmenue(event.pos().y())
        if menue is not None:
            menue.exec(event.globalPos())


class QuelltextEditor(QPlainTextEdit):
    breakpoint_umgeschaltet = Signal(int, bool)  # (Zeile ab 1, jetzt gesetzt?)
    #: Die Menge der Haltepunkte hat sich geändert, durch Umschalten
    #: oder weil Zeilen darüber eingefügt oder gelöscht wurden. Das
    #: Hauptfenster gibt sie dann an eine laufende Debug-Sitzung weiter
    #: (Punkte 118 und 119).
    breakpoints_geaendert = Signal()
    #: Strg+Mausrad hat die Schriftgröße geändert (neue Größe in pt).
    #: Das Hauptfenster merkt sie sich und gibt sie an alle Editoren
    #: weiter (Punkt 101).
    schriftgroesse_geaendert = Signal(int)

    #: F12. Der Editor kennt weder das Projekt noch die anderen Tabs -
    #: das Springen selbst macht deshalb das Hauptfenster.
    definition_gesucht = Signal()
    #: „Kommentar umschalten“ aus dem Kontextmenü; die Logik dafür
    #: steckt im Hauptfenster (`_kommentar_umschalten_aktion`).
    kommentar_gewuenscht = Signal()
    #: Im Halt: welcher Wert steht hinter dem Namen unter der Maus?
    #: (Name, Bildschirmpunkt) - das Hauptfenster fragt den Debugger
    #: und zeigt die Antwort als Hinweis (Punkt 100).
    wert_gefragt = Signal(str, QPoint)

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
        #: Was die Parameterhilfe zuletzt gezeigt hat, als HTML. Der
        #: Kurzhinweis selbst lässt sich nicht auslesen.
        self.letzte_parameterhilfe = ""
        self._vorschlaege: list[Vorschlag] = []
        #: Wo das Wort beginnt, für das die Liste gerade gilt. Beim
        #: Weitertippen desselben Worts wird sie nur eingeengt.
        self._vorschlaege_ab: int | None = None
        # Anstoß nach der Tipp-Pause (Punkt 313).
        self._vorschlag_uhr = QTimer(self)
        self._vorschlag_uhr.setSingleShot(True)
        self._vorschlag_uhr.setInterval(_VORSCHLAG_PAUSE_MS)
        self._vorschlag_uhr.timeout.connect(self._vorschlaege_anfordern)
        self._vorschlag_bote = _Bote(self)
        self._vorschlag_bote.fertig.connect(self._vorschlaege_eingetroffen)
        #: Nummer der letzten Anfrage an den Nebenfaden. Ein Ergebnis
        #: mit einer älteren Nummer ist überholt.
        self._anfrage = 0
        #: Stand von Text und Schreibmarke bei der letzten Anfrage.
        self._anfrage_stand: tuple[int, int] = (-1, -1)
        #: Ob der Nebenfaden gerade rechnet, und ob danach gleich die
        #: nächste Anfrage fällig ist. Es rechnet nie mehr als einer.
        self._rechnet = False
        self._nachfordern = False
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
        #: Bedingungen je Haltepunktzeile, etwa `i == 5` (Punkt 100).
        self.bedingungen: dict[int, str] = {}
        #: Ob das Programm gerade hält - dann zeigt der Hinweis über
        #: einem Namen dessen Wert. Setzt das Hauptfenster.
        self.debugger_haelt = False
        self._zeilen_vorher = 1
        self.document().contentsChange.connect(self._breakpoints_nachfuehren)

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
            self.bedingungen.pop(zeile, None)
            gesetzt = False
        else:
            self.breakpoints.add(zeile)
            gesetzt = True
        self._rand.update()
        self.breakpoint_umgeschaltet.emit(zeile, gesetzt)
        self.breakpoints_geaendert.emit()

    def haltepunkte_setzen(
        self, zeilen: set[int], bedingungen: dict[int, str]
    ) -> None:
        """Setzt Haltepunkte und Bedingungen auf einmal, etwa beim
        Wiederöffnen einer Datei (Punkt 419). Zeilen jenseits des
        Textendes fallen weg; die Datei kann sich inzwischen geändert
        haben."""
        letzte = self.document().blockCount()
        self.breakpoints = {z for z in zeilen if 1 <= z <= letzte}
        self.bedingungen = {
            z: b for z, b in bedingungen.items() if z in self.breakpoints
        }
        self._rand.update()
        self.breakpoints_geaendert.emit()

    def _breakpoints_nachfuehren(self, position: int, _entfernt: int, _dazu: int) -> None:
        """Haltepunkte wandern mit ihrer Zeile (Punkt 119). Bis 0.3.5
        waren sie feste Zeilennummern: zwei Zeilen darüber eingefügt,
        und der Punkt stand auf einer anderen Anweisung.

        Eine Änderung, die am Anfang einer Zeile beginnt, schiebt diese
        Zeile selbst mit; beginnt sie mitten in der Zeile, bleibt die
        Zeile stehen und erst die folgenden wandern. Gelöschte Zeilen
        nehmen ihre Haltepunkte mit."""
        zeilen = self.document().blockCount()
        unterschied = zeilen - self._zeilen_vorher
        self._zeilen_vorher = zeilen
        if not unterschied or not self.breakpoints:
            return
        block = self.document().findBlock(position)
        erste = block.blockNumber() + 1
        am_anfang = position == block.position()
        ab = erste if am_anfang else erste + 1
        # alte Zeile -> neue Zeile; wer fehlt, lag in gelöschten Zeilen
        zuordnung: dict[int, int] = {}
        for zeile in self.breakpoints:
            if zeile < ab:
                zuordnung[zeile] = zeile
            elif unterschied > 0 or zeile >= ab - unterschied:
                zuordnung[zeile] = zeile + unterschied
        neu = set(zuordnung.values())
        if neu != self.breakpoints:
            self.bedingungen = {
                zuordnung[z]: b for z, b in self.bedingungen.items() if z in zuordnung
            }
            self.breakpoints = neu
            self._rand.update()
            self.breakpoints_geaendert.emit()

    def bedingung_setzen(self, zeile: int, bedingung: str) -> None:
        """Haltepunkt mit Bedingung (Punkt 100): das Programm hält in
        dieser Zeile nur, wenn die Bedingung wahr ist. Leer heißt:
        immer halten. Setzt den Haltepunkt, falls noch keiner da ist."""
        bedingung = bedingung.strip()
        if zeile not in self.breakpoints:
            self.breakpoints.add(zeile)
            self.breakpoint_umgeschaltet.emit(zeile, True)
        if bedingung:
            self.bedingungen[zeile] = bedingung
        else:
            self.bedingungen.pop(zeile, None)
        self._rand.update()
        self.breakpoints_geaendert.emit()

    def rand_kontextmenue(self, y: float) -> QMenu | None:
        """Rechte Maustaste im Zeilenrand: Haltepunkt setzen oder
        entfernen und eine Bedingung festlegen."""
        rect = QRect(0, 0, self._rand.width(), self._rand.height())
        for blocknummer, oben, unten in self._fuer_jeden_sichtbaren_block(rect):
            if oben <= y < unten:
                return self._haltepunkt_menue(blocknummer + 1)
        return None

    def _haltepunkt_menue(self, zeile: int) -> QMenu:
        menue = QMenu(self)
        if zeile in self.breakpoints:
            menue.addAction("Haltepunkt entfernen").triggered.connect(
                lambda *_: self.breakpoint_umschalten(zeile)
            )
        else:
            menue.addAction("Haltepunkt setzen").triggered.connect(
                lambda *_: self.breakpoint_umschalten(zeile)
            )
        menue.addAction("Bedingung festlegen …").triggered.connect(
            lambda *_: self._bedingung_erfragen(zeile)
        )
        if zeile in self.bedingungen:
            menue.addAction("Bedingung entfernen").triggered.connect(
                lambda *_: self.bedingung_setzen(zeile, "")
            )
        return menue

    def _bedingung_erfragen(self, zeile: int) -> None:
        from PySide6.QtWidgets import QInputDialog

        text, ok = QInputDialog.getText(
            self,
            "Bedingung für den Haltepunkt",
            f"Zeile {zeile}: nur anhalten, wenn diese Bedingung wahr ist\n"
            "(zum Beispiel  i == 5  oder  name == \"Ada\"):",
            text=self.bedingungen.get(zeile, ""),
        )
        if ok:
            self.bedingung_setzen(zeile, text)

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
 Grammatik-Wissen wie in einem vollständigen Editor – nur zwei
 einfache, zuverlässige
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
            if self._markierung_ueber_zeilen():
                self.einruecken()
            else:
                self.textCursor().insertText(_EINZUG)
            return
        if event.key() == Qt.Key.Key_Backtab:
            self.einruecken(aus=True)
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
        if self._zeichen_ohne_kuerzel(event) and self._klammer_schliessen(event):
            # Auch nach einer selbst geschlossenen Klammer: an `(`
            # hängt die Parameterhilfe. Bis September 2026 war der
            # Tastendruck hier zu Ende, und die Hilfe erschien nie.
            self._nach_der_eingabe(event)
            return
        super().keyPressEvent(event)
        self._nach_der_eingabe(event)

    @staticmethod
    def _zeichen_ohne_kuerzel(event: QKeyEvent) -> bool:
        """Ob der Tastendruck ein Zeichen schreibt und kein Kürzel ist.

        Auf einer deutschen Tastatur brauchen `(`, `)` und die
        Anführungszeichen die Umschalttaste, `[ ] { }` AltGr. Bis
        September 2026 wurden Klammern nur ohne jede Zusatztaste
        geschlossen und damit auf dieser Tastatur nie. Windows meldet
        AltGr als Strg und Alt zugleich; nur eine der beiden allein
        ist ein Kürzel.
        """
        tasten = event.modifiers()
        strg = bool(tasten & Qt.KeyboardModifier.ControlModifier)
        alt = bool(tasten & Qt.KeyboardModifier.AltModifier)
        return bool(event.text()) and strg == alt

    def _nach_der_eingabe(self, event: QKeyEvent) -> None:
        """Nach jedem getippten Zeichen: Liste vormerken oder einengen
        bzw. Parameterhilfe zeigen."""
        if not self.vervollstaendigung_an:
            return
        text = event.text()
        if text in ("(", ","):
            # Nach dem Komma ist der nächste Parameter dran - die
            # Hervorhebung wandert mit.
            self.vorschlagsliste_schliessen()
            self.parameterhilfe_anzeigen()
            return
        if text in (")", ""):
            QToolTip.hideText()
        if text and (text.isalnum() or text in "._"):
            self._vorschlaege_vormerken(text)
        elif self.vorschlagsliste.isVisible() or self._vorschlag_uhr.isActive():
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

    def _vorschlag_anlass(self, erzwungen: bool = False) -> bool:
        """Ob an der Schreibmarke eine Liste erscheinen soll."""
        # Im Prüfungsmodus gar nicht. Auch ein Name wie
        # `bank_abheben_konto` samt Parametern ist in einer Klausur
        # schon ein Stück Antwort.
        if not self.vervollstaendigung_an or pruefungsmodus_laeuft():
            return False
        cursor = self.textCursor()
        links = cursor.block().text()[: cursor.positionInBlock()]
        # In einem Kommentar oder einer Zeichenkette steht deutscher
        # Text. Eine Liste, die dort von selbst aufgeht, fängt die
        # Eingabetaste ab (Punkt 409). Strg+Leertaste darf trotzdem.
        if not erzwungen:
            # Zustand 1 setzt die Hervorhebung am Ende einer Zeile, in
            # der eine mehrzeilige Zeichenkette offen bleibt.
            davor = cursor.block().previous()
            in_dreifach = davor.isValid() and davor.userState() == 1
            if not schreibmarke_im_code(links, in_dreifach):
                return False
        nach_punkt = links.rstrip().endswith(".")
        return (
            erzwungen
            or nach_punkt
            or len(self._wort_vor_dem_cursor()) >= MINDESTZEICHEN
        )

    def vorschlaege_anzeigen(self, erzwungen: bool = False) -> int:
        """Baut die Vorschlagsliste sofort und zeigt sie. Liefert, wie
        viele Vorschläge es gab.

        Gerechnet wird hier im Hauptfaden: so bei Strg+Leertaste, wo
        jemand ausdrücklich auf die Liste wartet. Beim Tippen läuft es
        über `_vorschlaege_vormerken` im Hintergrund.

        `erzwungen` ist Strg+Leertaste: dann erscheint die Liste auch
        nach einem Punkt, wo noch gar nichts getippt wurde – genau dort
        braucht man sie am meisten.
        """
        if not self._vorschlag_anlass(erzwungen):
            self.vorschlagsliste_schliessen()
            return 0
        self._vorschlag_uhr.stop()
        cursor = self.textCursor()
        gefunden = vorschlaege(
            self.toPlainText(),
            cursor.blockNumber() + 1,
            cursor.positionInBlock(),
            self.property(_PFAD_EIGENSCHAFT),
        )
        return self._liste_zeigen(gefunden)

    def _vorschlaege_vormerken(self, zeichen: str) -> None:
        """Nach einem Buchstaben, Punkt oder Unterstrich (Punkt 313).

        Bis 0.3.6 rechnete jedi hier bei jedem Zeichen und las dafür
        die ganze Datei; in einer Unit mit 5.000 Zeilen kostete jeder
        Tastendruck im Median 310 ms. Jetzt stößt erst eine Pause von
        `_VORSCHLAG_PAUSE_MS` die Rechnung an, und die läuft in einem
        Nebenfaden. Steht die Liste schon, wird sie beim Weitertippen
        desselben Worts sofort eingeengt; nach der Pause kommt die
        genaue Liste von jedi.
        """
        einengen = zeichen != "." and self.vorschlagsliste.isVisible()
        if not (einengen and self._liste_einengen()):
            self.vorschlagsliste_schliessen()
        self._vorschlag_uhr.start()

    def _liste_einengen(self) -> bool:
        """Lässt in der stehenden Liste nur, was zum Wort passt."""
        wort = self._wort_vor_dem_cursor()
        anfang = self.textCursor().position() - len(wort)
        if not wort or anfang != self._vorschlaege_ab:
            return False
        klein = wort.lower()
        passend = [
            vorschlag
            for vorschlag in self._vorschlaege
            if vorschlag.name.lower().startswith(klein)
        ]
        return bool(passend) and self._liste_zeigen(passend) > 0

    def _stand(self) -> tuple[int, int]:
        """Textstand und Schreibmarke; ändert sich eines davon, passt
        ein Ergebnis aus dem Nebenfaden nicht mehr."""
        return self.document().revision(), self.textCursor().position()

    def _vorschlaege_anfordern(self) -> None:
        """Nach der Tipp-Pause: jedi im Nebenfaden rechnen lassen."""
        if not self._vorschlag_anlass():
            self.vorschlagsliste_schliessen()
            return
        if self._rechnet:
            # Die laufende Rechnung ist ohnehin überholt; gleich nach
            # ihr kommt die nächste.
            self._nachfordern = True
            return
        cursor = self.textCursor()
        self._anfrage += 1
        nummer = self._anfrage
        self._anfrage_stand = self._stand()
        text = self.toPlainText()
        zeile = cursor.blockNumber() + 1
        spalte = cursor.positionInBlock()
        pfad = self.property(_PFAD_EIGENSCHAFT)
        bote = self._vorschlag_bote

        def fertig(gefunden: object) -> None:
            try:
                bote.fertig.emit(nummer, gefunden)
            except RuntimeError:
                # Der Editor ist inzwischen geschlossen.
                pass

        self._rechnet = True
        im_hintergrund(lambda: vorschlaege(text, zeile, spalte, pfad), fertig)

    def _vorschlaege_eingetroffen(self, nummer: int, gefunden: object) -> None:
        """Das Ergebnis aus dem Nebenfaden, jetzt im Hauptfaden.
        Verworfen, wenn seitdem getippt, die Schreibmarke bewegt oder
        die Liste geschlossen wurde."""
        self._rechnet = False
        aktuell = nummer == self._anfrage and self._anfrage_stand == self._stand()
        if self._nachfordern:
            self._nachfordern = False
            if not aktuell:
                self._vorschlaege_anfordern()
                return
        if not aktuell or not self._vorschlag_anlass():
            return
        self._liste_zeigen(gefunden if isinstance(gefunden, list) else [])

    def _liste_zeigen(self, gefunden: list[Vorschlag]) -> int:
        """Füllt die Liste mit `gefunden` und zeigt sie unter der
        Schreibmarke. Liefert, wie viele Einträge es sind."""
        if not gefunden:
            self.vorschlagsliste_schliessen()
            return 0

        self._vorschlaege = gefunden
        self._vorschlaege_ab = (
            self.textCursor().position() - len(self._wort_vor_dem_cursor())
        )
        self.vorschlagsliste.clear()
        for vorschlag in gefunden:
            self.vorschlagsliste.addItem(vorschlag.anzeige_text())
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
        """Schließt die Liste. Eine vorgemerkte Anfrage entfällt, und
        was der Nebenfaden noch liefert, verfällt."""
        self._vorschlag_uhr.stop()
        self._anfrage += 1
        self._nachfordern = False
        self.vorschlagsliste.hide()
        self._vorschlaege = []
        self._vorschlaege_ab = None

    def vorschlag_uebernehmen(self, zeile: int | None = None) -> bool:
        """Setzt den gewählten Vorschlag ein. Ersetzt dabei das bereits
        Getippte, statt es zu verdoppeln."""
        if not self._vorschlaege or not self.vorschlagsliste.isVisible():
            return False
        nummer = self.vorschlagsliste.currentRow() if zeile is None else zeile
        if not 0 <= nummer < len(self._vorschlaege):
            return False
        vorschlag = self._vorschlaege[nummer]
        name = vorschlag.name
        bereits = self._wort_vor_dem_cursor()

        cursor = self.textCursor()
        for _ in range(len(bereits)):
            cursor.deletePreviousChar()
        cursor.insertText(name)

        # Eine Funktion kommt mit ihren Klammern, und die Schreibmarke
        # steht gleich dazwischen - aus `pri` wird `print(|)`, und die
        # Parameterhilfe zeigt, was hineingehört. Steht schon eine
        # Klammer da, etwa weil nur der Name ausgetauscht wird, bleibt
        # es beim Namen.
        rechts = cursor.block().text()[cursor.positionInBlock():]
        aufrufbar = vorschlag.art in ("function", "class") or vorschlag.signatur.startswith(
            f"{name}("
        )
        if aufrufbar and not rechts.startswith("("):
            cursor.insertText("()")
            cursor.movePosition(cursor.MoveOperation.Left)
        self.setTextCursor(cursor)
        self.vorschlagsliste_schliessen()
        if aufrufbar and not rechts.startswith("("):
            self.parameterhilfe_anzeigen()
        return True

    def parameterhilfe_anzeigen(self) -> str:
        """Zeigt beim Tippen der öffnenden Klammer und nach jedem Komma,
        welche Parameter erwartet werden – als Kurzhinweis über dem
        Cursor, mit Typ und dem gerade einzugebenden Parameter
        hervorgehoben. Im Prüfungsmodus nicht."""
        if not self.vervollstaendigung_an or pruefungsmodus_laeuft():
            self.letzte_parameterhilfe = ""
            QToolTip.hideText()
            return ""
        cursor = self.textCursor()
        text = parameterhilfe_anzeige(
            self.toPlainText(),
            cursor.blockNumber() + 1,
            cursor.positionInBlock(),
            self.property(_PFAD_EIGENSCHAFT),
        )
        self.letzte_parameterhilfe = text
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

    def _parameterhilfe_sichtbar(self) -> bool:
        """Ob der gerade gezeigte Kurzhinweis die Parameterhilfe ist.

        Ruht die Maus über dem Editor, schickt Qt nach kurzer Zeit ein
        Tooltip-Ereignis, zum Beispiel wenn die Vorschlagsliste unter
        der Maus verschwindet. Steht an der Stelle kein Fund, wurde
        jeder Kurzhinweis ausgeblendet, auch die Parameterhilfe, die
        gerade nach dem Übernehmen eines Vorschlags erschienen war.
        """
        return (
            bool(self.letzte_parameterhilfe)
            and QToolTip.isVisible()
            and QToolTip.text() == self.letzte_parameterhilfe
        )

    def _markierungen_setzen(self) -> None:
        self.setExtraSelections(
            [*self._fundmarkierungen, *self._zeilenmarkierung]
        )

    def event(self, ereignis) -> bool:
        """Tooltip über einer unterringelten Zeile – die deutsche
        Meldung dort, wo der Fehler steht."""
        if ereignis.type() == QEvent.Type.ToolTip and self.debugger_haelt:
            cursor = self.cursorForPosition(ereignis.pos())
            cursor.select(QTextCursor.SelectionType.WordUnderCursor)
            name = cursor.selectedText()
            if name.isidentifier():
                self.wert_gefragt.emit(name, ereignis.globalPos())
                return True
        if ereignis.type() == QEvent.Type.ToolTip and self._funde:
            punkt = ereignis.pos()
            zeile = self.cursorForPosition(punkt).blockNumber() + 1
            meldung = self._funde.get(zeile, "")
            if meldung:
                QToolTip.showText(ereignis.globalPos(), meldung, self)
            elif not self._parameterhilfe_sichtbar():
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

        # Zuerst überspringen, dann erst ein Paar öffnen. Anführungszeichen
        # öffnen und schließen mit demselben Zeichen; stand diese Prüfung
        # hinter dem Öffnen, kam sie für sie nie an die Reihe, und das
        # schließende „"“ öffnete ein neues Paar. Aus x = "a" wurde so
        # x = "a" mit zwei Anführungszeichen zu viel (Punkt 47).
        if zeichen and zeichen in _KLAMMER_ZU and not cursor.hasSelection():
            rechts = cursor.block().text()[cursor.positionInBlock() :]
            if rechts.startswith(zeichen):
                cursor.movePosition(cursor.MoveOperation.Right)
                self.setTextCursor(cursor)
                return True

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
        return False

    def _markierung_ueber_zeilen(self) -> bool:
        cursor = self.textCursor()
        if not cursor.hasSelection():
            return False
        dokument = self.document()
        return (
            dokument.findBlock(cursor.selectionStart()).blockNumber()
            != dokument.findBlock(cursor.selectionEnd()).blockNumber()
        )

    def einruecken(self, *, aus: bool = False) -> None:
        """Rückt die markierten Zeilen um eine Ebene ein oder aus
        (Punkt 88); ohne Markierung die Zeile des Cursors.

        Bis 0.3.5 ersetzte Tab eine Markierung über mehrere Zeilen durch
        vier Leerzeichen, der markierte Code war weg, und Umschalt+Tab
        tat nichts. Eine Zeile, deren Markierung erst am Zeilenanfang
        endet, zählt nicht mit - so markiert, wer ganze Zeilen mit der
        Maus aufzieht. Ein Schritt für Rückgängig."""
        cursor = self.textCursor()
        dokument = self.document()
        anfang = dokument.findBlock(cursor.selectionStart())
        ende = dokument.findBlock(cursor.selectionEnd())
        if (
            cursor.hasSelection()
            and ende.blockNumber() > anfang.blockNumber()
            and cursor.selectionEnd() == ende.position()
        ):
            ende = ende.previous()
        cursor.beginEditBlock()
        block = anfang
        while block.isValid() and block.blockNumber() <= ende.blockNumber():
            zeile = QTextCursor(block)
            if aus:
                text = block.text()
                weg = len(text) - len(text.lstrip(" "))
                zeile.movePosition(
                    QTextCursor.MoveOperation.Right,
                    QTextCursor.MoveMode.KeepAnchor,
                    min(weg, len(_EINZUG)),
                )
                zeile.removeSelectedText()
            elif block.text().strip():
                zeile.insertText(_EINZUG)
            block = block.next()
        cursor.endEditBlock()
        if cursor.hasSelection():
            neu = QTextCursor(dokument)
            neu.setPosition(anfang.position())
            neu.setPosition(
                ende.position() + ende.length() - 1, QTextCursor.MoveMode.KeepAnchor
            )
            self.setTextCursor(neu)

    def _sichtbare_einheit(self, zeile: int) -> tuple[int, int]:
        """Erste und letzte Zeile (ab 1) dessen, was als `zeile` zu
        sehen ist: eine zugeklappte Kopfzeile samt Rumpf, eine Zeile
        im versteckten Rumpf als die äußerste zugeklappte Funktion
        darum, sonst die Zeile allein."""
        faltbar = self.faltbare_zeilen() if self._gefaltet else {}
        for kopf in sorted(self._gefaltet):
            ende = faltbar.get(kopf)
            if ende is not None and kopf <= zeile <= ende:
                return kopf, ende
        return zeile, zeile

    def zeile_duplizieren(self) -> None:
        """Strg+D: die aktuelle Zeile noch einmal darunter. Auf einer
        zugeklappten Funktion die ganze Funktion, so wie sie zu sehen
        ist - vorher kam nur die Kopfzeile ohne Rumpf heraus."""
        cursor = self.textCursor()
        anfang, ende = self._sichtbare_einheit(cursor.blockNumber() + 1)
        if anfang == ende:
            text = cursor.block().text()
            cursor.movePosition(cursor.MoveOperation.EndOfBlock)
            cursor.insertText("\n" + text)
            self.setTextCursor(cursor)
            return
        zeilen = self.toPlainText().split("\n")
        kopie = zeilen[anfang - 1:ende]
        anzahl = len(kopie)
        gefaltet = {
            z + anzahl if z > ende else z for z in self._gefaltet
        } | {anfang + anzahl}
        self._ganzen_text_ersetzen(
            zeilen[:ende] + kopie + zeilen[ende:],
            {z: z + anzahl if z > ende else z for z in range(1, len(zeilen) + 1)},
            gefaltet,
            anfang + anzahl,
            0,
        )

    def zeile_verschieben(self, nach_unten: bool) -> bool:
        """Alt+Pfeil: die aktuelle Zeile eine Position nach oben oder
        unten. Liefert `False`, wenn es dort nicht weitergeht.

        Bewegt wird, was zu sehen ist: eine zugeklappte Funktion als
        Ganzes, und auch die Nachbarzeile, mit der getauscht wird, ist
        gegebenenfalls eine ganze zugeklappte Funktion. Vorher tauschte
        die Kopfzeile mit der ersten versteckten Zeile, und die Datei
        hatte einen Einrückungsfehler. Faltungen und Haltepunkte
        wandern mit ihren Zeilen."""
        cursor = self.textCursor()
        zeile = cursor.blockNumber() + 1
        anzahl = self.document().blockCount()
        anfang, ende = self._sichtbare_einheit(zeile)
        if nach_unten:
            if ende >= anzahl:
                return False
            n_anfang, n_ende = self._sichtbare_einheit(ende + 1)
            oben, unten = (anfang, ende), (n_anfang, n_ende)
        else:
            if anfang <= 1:
                return False
            n_anfang, n_ende = self._sichtbare_einheit(anfang - 1)
            oben, unten = (n_anfang, n_ende), (anfang, ende)

        zeilen = self.toPlainText().split("\n")
        erster = zeilen[oben[0] - 1:oben[1]]
        zweiter = zeilen[unten[0] - 1:unten[1]]
        neu_zeilen = (
            zeilen[:oben[0] - 1] + zweiter + erster + zeilen[unten[1]:]
        )
        # alte Zeile -> neue Zeile
        zuordnung = {z: z for z in range(1, len(zeilen) + 1)}
        for z in range(oben[0], oben[1] + 1):
            zuordnung[z] = z + len(zweiter)
        for z in range(unten[0], unten[1] + 1):
            zuordnung[z] = z - len(erster)
        gefaltet = {zuordnung.get(z, z) for z in self._gefaltet}
        self._ganzen_text_ersetzen(
            neu_zeilen,
            zuordnung,
            gefaltet,
            zuordnung[zeile],
            cursor.positionInBlock(),
        )
        return True

    def _ganzen_text_ersetzen(
        self,
        zeilen: list[str],
        zuordnung: dict[int, int],
        gefaltet: set[int],
        cursor_zeile: int,
        spalte: int,
    ) -> None:
        """Setzt den ganzen Text in einem Bearbeitungsschritt neu und
        führt Faltungen, Haltepunkte und Bedingungen über `zuordnung`
        (alte Zeile -> neue Zeile, ab 1) mit. Das Neusetzen machte
        sonst alle Zeilen sichtbar, während `_gefaltet` weiter die
        alten Faltungen meldete, und ein Haltepunkt blieb an seiner
        Zeilennummer stehen, auf einer anderen Anweisung."""
        dokument = self.document()
        vorher = (set(self.breakpoints), dict(self.bedingungen))
        breakpoints = {zuordnung.get(z, z) for z in self.breakpoints}
        bedingungen = {
            zuordnung.get(z, z): b for z, b in self.bedingungen.items()
        }
        cursor = self.textCursor()
        # In einem Rutsch, damit ein einziges Strg+Z es zurücknimmt -
        # sonst wären es drei Schritte, und man müsste dreimal drücken.
        cursor.beginEditBlock()
        cursor.select(cursor.SelectionType.Document)
        cursor.insertText("\n".join(zeilen))
        cursor.endEditBlock()

        self._gefaltet = gefaltet
        self._alles_sichtbar_machen()
        # Beim Einfügen hat `_breakpoints_nachfuehren` sie schon nach
        # der Zeilenzahl verschoben; maßgeblich ist die Zuordnung.
        self.breakpoints = breakpoints
        self.bedingungen = bedingungen
        self._rand.update()
        if (breakpoints, bedingungen) != vorher:
            self.breakpoints_geaendert.emit()

        block = dokument.findBlockByNumber(cursor_zeile - 1)
        neu = self.textCursor()
        neu.setPosition(block.position() + min(spalte, len(block.text())))
        self.setTextCursor(neu)

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
        self.schriftgroesse_setzen(neu)
        self.schriftgroesse_geaendert.emit(neu)
        return neu

    def schriftgroesse_setzen(self, groesse: int) -> None:
        """Die Größe steht zusätzlich im eigenen Stylesheet des Editors:
        das Stylesheet der IDE legt `QuelltextEditor` auf 11 pt fest und
        gewinnt gegen `setFont`. Bis 0.3.5 wirkte Strg+Mausrad deshalb
        nur in einem einzeln erzeugten Editor, im Hauptfenster nie
        (Punkt 101)."""
        groesse = max(_MIN_SCHRIFT, min(_MAX_SCHRIFT, groesse))
        schrift = self.font()
        schrift.setPointSize(groesse)
        self.setStyleSheet(f"QuelltextEditor {{ font-size: {groesse}pt; }}")
        self.setFont(schrift)
        self._breite_aktualisieren()
        self.viewport().update()

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

    def alles_falten(self) -> None:
        """Jede Klasse und Funktion zuklappen - übrig bleiben die
        Kopfzeilen, als Überblick über die Datei (Punkt 76)."""
        for zeile in sorted(self.faltbare_zeilen()):
            self.falten(zeile)

    def kontextmenue(self) -> QMenu:
        """Das Menü der rechten Maustaste (Punkt 77): Qts Standardmenü
        mit Rückgängig, Ausschneiden, Kopieren und Einfügen, darunter
        die Befehle, die es sonst nur als Tastenkürzel gab. Getrennt von
        `contextMenuEvent`, damit ein Test jeden Eintrag auslösen kann,
        ohne ein Menü zu öffnen, das auf einen Klick wartet."""
        menue = self.createStandardContextMenu()
        menue.addSeparator()
        # (Text, Rückruf, ändert den Text?) - was den Text ändert, ist
        # in einer schreibgeschützten Datei grau.
        # Name und Taste kommen aus `EDITORBEFEHLE`, derselben Quelle
        # wie die Tastenkürzel-Übersicht (Punkt 440).
        def befehl(schluessel: str) -> str:
            eintrag = EDITORBEFEHLE[schluessel]
            return f"{eintrag.name}\t{eintrag.taste}"

        eintraege = (
            (befehl("definition"), self.definition_gesucht.emit, False),
            (befehl("duplizieren"), self.zeile_duplizieren, True),
            (
                befehl("nach_oben"),
                lambda: self.zeile_verschieben(False),
                True,
            ),
            (
                befehl("nach_unten"),
                lambda: self.zeile_verschieben(True),
                True,
            ),
            (befehl("kommentar"), self.kommentar_gewuenscht.emit, True),
            (None, None, False),
            ("Alles zuklappen", self.alles_falten, False),
            ("Alles aufklappen", self.alles_entfalten, False),
        )
        for text, rueckruf, aendert in eintraege:
            if text is None:
                menue.addSeparator()
                continue
            aktion = menue.addAction(text)
            aktion.triggered.connect(lambda _=False, r=rueckruf: r())
            aktion.setEnabled(not (aendert and self.isReadOnly()))
        return menue

    def contextMenuEvent(self, ereignis) -> None:  # noqa: ANN001
        self.kontextmenue().exec(ereignis.globalPos())

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

        Ohne Faltung gibt es nichts zu prüfen. `faltbare_zeilen()` geht
        die ganze Datei durch; bei 5.000 Zeilen kostete das jeden
        Tastendruck rund 15 ms (Punkt 313).
        """
        if not self._gefaltet:
            return
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
                maler.setBrush(
                    _BEDINGT_FARBE if zeile in self.bedingungen else _BREAKPOINT_FARBE
                )
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
        for position in self.klammerpaar_am_cursor():
            klammer = QTextEdit.ExtraSelection()
            klammer.format.setBackground(QColor(self._rand_farben["klammerpaar"]))
            klammer.cursor = QTextCursor(self.document())
            klammer.cursor.setPosition(position)
            klammer.cursor.setPosition(position + 1, QTextCursor.MoveMode.KeepAnchor)
            auswahlen.append(klammer)
        self._zeilenmarkierung = auswahlen
        self._markierungen_setzen()

    def klammerpaar_am_cursor(self) -> tuple[int, ...]:
        """Positionen einer Klammer direkt am Cursor und ihrer
        Gegenklammer - oder nichts (Punkt 103). Klammern in Texten
        zwischen Anführungszeichen und in Kommentaren werden dabei
        nicht mitgezählt, soweit die Zeile das erkennen lässt."""
        text = self.toPlainText()
        position = self.textCursor().position()
        kandidaten = [position - 1, position] if position else [position]
        for stelle in kandidaten:
            if 0 <= stelle < len(text) and text[stelle] in (*_AUF_ZU, *_ZU_AUF):
                gegen = _gegenklammer(text, stelle)
                if gegen is not None:
                    return (stelle, gegen)
        return ()
