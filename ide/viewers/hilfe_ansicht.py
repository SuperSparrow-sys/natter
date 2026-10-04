"""Hilfeseiten im Programm selbst anzeigen (M11, Abschnitt 4).

Die Hilfetexte von Natter liegen als Markdown in `docs/`. Bis jetzt
wurden sie auf zwei Wegen gezeigt, und beide waren für die Zielgruppe
unbrauchbar:

* „Erste Schritte“ öffnete die `.md`-Datei im Quelltexteditor –
  eine Anleitung mit `##` und `*` davor, in einem Fenster, das nach
  Programmieren aussieht und in dem man sie versehentlich ändern kann
* die Komponenten-Referenz gab die Datei an Windows weiter. Dort
  ist für `.md` meist gar nichts eingetragen; im besten Fall öffnete
  sich der Editor, im Normalfall passierte nichts

Beides zeigt jetzt dieselbe Ansicht: lesbar gesetzt, im Programm, in
einem eigenen Reiter neben dem Quelltext.
"""

from __future__ import annotations

import re

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import (
    QFont,
    QFontDatabase,
    QKeyEvent,
    QTextBlock,
    QTextBlockFormat,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
    QTextFormat,
    QTextList,
    QTextListFormat,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextBrowser,
    QToolButton,
    QWidget,
)

#: Schriftarten für Code-Stellen, in der Reihenfolge der Vorliebe. Die
#: erste, die es auf dem Rechner gibt, wird genommen.
#:
#: Qt setzt beim Umwandeln von Markdown alles in `…` und jeden
#: Code-Block auf die Familie „monospace“ - einen Gattungsnamen, den
#: es unter Windows nicht als Schriftart gibt (`QFontDatabase.families()`
#: kennt ihn selbst dann nicht, wenn alle 255 Windows-Schriften geladen
#: sind). Qt muss dann irgendetwas einsetzen, und heraus kam
#: unleserliches Zeug: aus `u_main_design.py` wurde „u_m⌐H h_desig⌐h py“.
#: Betroffen war jede Hilfeseite - die Komponenten-Referenz besteht fast
#: nur aus solchen Stellen (M12, am Bildschirmfoto gefunden).
CODE_SCHRIFTEN = ("Consolas", "Courier New", "DejaVu Sans Mono", "Courier")

#: Der Gattungsname, den Qt beim Umwandeln von Markdown einsetzt.
_IST_CODE = "monospace"


def code_schriftart(bevorzugt: str | None = None) -> str:
    """`bevorzugt`, wenn es die Schrift gibt - das ist die Schrift des
    Quelltexteditors aus „Ansicht → Schriftart“ -, sonst die erste
    vorhandene aus `CODE_SCHRIFTEN`."""
    vorhanden = set(QFontDatabase.families())
    if bevorzugt and bevorzugt in vorhanden:
        return bevorzugt
    for name in CODE_SCHRIFTEN:
        if name in vorhanden:
            return name
    return CODE_SCHRIFTEN[-1]


#: Breiteste Textspalte in Punkten. Rund 80 Zeichen der
#: Fließtextschrift - darüber verliert das Auge beim Zeilenwechsel den
#: Anschluss und findet den Zeilenanfang nicht wieder. Was breiter
#: ist, bleibt Rand.
HOECHSTBREITE = 720

#: Zeilenabstand in Prozent. 160 statt Qts 100: ein Text, dessen
#: Zeilen aufeinanderkleben, sieht aus wie eine Fehlermeldung.
ZEILENABSTAND = 160

#: Zeilenabstand in Codeblöcken. Enger als im Fließtext, damit ein
#: Block als eine Fläche erscheint und nicht als Stapel einzelner
#: Streifen: jede Codezeile ist für Qt ein eigener Absatz, und mit
#: 160 % blieb zwischen den grauen Flächen je ein weißer Spalt.
CODE_ZEILENABSTAND = 125

#: Sprachen, deren Codeblöcke wie im Quelltexteditor eingefärbt werden.
#: Ein Block ohne Angabe bleibt einfarbig - in den Hilfeseiten stehen
#: darin Pfade und Registry-Schlüssel, und in einem Pfad fände die
#: Hervorhebung Zahlen und Schlüsselwörter, wo keine sind.
PYTHON_SPRACHEN = {"python", "py"}

#: Grenzen für Strg+Mausrad, wie im Quelltexteditor.
KLEINSTE_SCHRIFT = 7
GROESSTE_SCHRIFT = 32


def stilvorlage(dunkel: bool, code_schrift: str) -> str:
    """Die Gestaltung der Hilfeseiten als Stylesheet.

    Keine Farben außer der Fläche hinter Codeblöcken: die Schrift- und
    Hintergrundfarbe kommt vom Thema der IDE, und eine Vorlage, die
    sie festschriebe, sähe im jeweils anderen Thema falsch aus.

    Die Schriftstärke ist die eine Ausnahme, die vom Thema abhängt.
    Helle Schrift auf dunklem Grund wirkt dünner als dieselbe Schrift
    umgekehrt; 500 gleicht das aus, ohne fett zu wirken. Qt nimmt die
    Zwischenwerte an - nachgemessen ergeben 500 und 600 auch 500 und
    600 und nicht 700 wie „bold".
    """
    stufe = 500 if dunkel else 400
    rahmen = coderahmen(dunkel)
    return f"""
        body {{ font-weight: {stufe}; line-height: {ZEILENABSTAND}%; }}
        p {{ line-height: {ZEILENABSTAND}%; margin-top: 8px; margin-bottom: 8px; }}
        li {{ line-height: {ZEILENABSTAND}%; margin-bottom: 4px; }}
        h1, h2, h3 {{ margin-top: 20px; margin-bottom: 8px; font-weight: 600; }}
        code {{ font-family: {code_schrift}; }}
        pre {{ font-family: {code_schrift}; }}
        table {{ border-collapse: collapse; margin-top: 10px; margin-bottom: 10px; }}
        th, td {{ border: 1px solid {rahmen}; padding: 5px 10px; }}
        th {{ font-weight: 600; }}
    """


def codeflaeche(dunkel: bool) -> str:
    """Die Fläche hinter Codeblöcken. Sie muss sich vom Grund abheben
    und darf ihn in keinem Thema übertönen, deshalb zwei feste
    Werte."""
    return "#2b3136" if dunkel else "#f2f4f6"


def coderahmen(dunkel: bool) -> str:
    """Der Rahmen um Codeblöcke und Tabellen."""
    return "#4a545c" if dunkel else "#d5dade"


def _code_einfaerben(dokument: QTextDocument, dunkel: bool) -> None:
    """Färbt Python-Codeblöcke ein wie im Quelltexteditor und gibt
    allen Codeblöcken einen engeren Zeilenabstand als dem Fließtext.

    Eingefärbt wird mit derselben `PythonHervorhebung` wie im Editor,
    in einem Hilfsdokument je Block. Die Farben gehen als feste
    Zeichenformate ins Dokument und überstehen so den Umweg über HTML.
    """
    from ide.shell.python_hervorhebung import PythonHervorhebung

    # Zwei Codeblöcke, zwischen denen nur eine Leerzeile steht, liegen
    # im Dokument direkt hintereinander. Getrennt werden sie dann am
    # Wechsel der Sprache - sonst erbte ein Pfad unter einem
    # Python-Block dessen Farben.
    laeufe: list[list[QTextBlock]] = []
    block = dokument.begin()
    vorher: str | None = None
    while block.isValid():
        format_ = block.blockFormat()
        sprache = (
            format_.stringProperty(QTextFormat.Property.BlockCodeLanguage)
            if format_.hasProperty(QTextFormat.Property.BlockCodeFence)
            else None
        )
        if sprache is not None:
            if sprache != vorher:
                laeufe.append([])
            laeufe[-1].append(block)
        vorher = sprache
        block = block.next()
    if not laeufe:
        return

    thema = "dark" if dunkel else "light"
    zeilen = QTextBlockFormat()
    zeilen.setLineHeight(
        CODE_ZEILENABSTAND,
        QTextBlockFormat.LineHeightTypes.ProportionalHeight.value,
    )
    cursor = QTextCursor(dokument)
    cursor.beginEditBlock()
    for lauf in laeufe:
        for block in lauf:
            cursor.setPosition(block.position())
            cursor.mergeBlockFormat(zeilen)

        sprache = lauf[0].blockFormat().stringProperty(
            QTextFormat.Property.BlockCodeLanguage
        )
        if sprache.lower() not in PYTHON_SPRACHEN:
            continue
        hilfe = QTextDocument()
        hilfe.setPlainText("\n".join(b.text() for b in lauf))
        hervorhebung = PythonHervorhebung(hilfe, thema)
        hervorhebung.rehighlight()
        quelle = hilfe.begin()
        for block in lauf:
            for bereich in quelle.layout().formats():
                anfang = block.position() + bereich.start
                cursor.setPosition(anfang)
                cursor.setPosition(
                    anfang + bereich.length, QTextCursor.MoveMode.KeepAnchor
                )
                cursor.mergeCharFormat(bereich.format)
            quelle = quelle.next()
    cursor.endEditBlock()


#: Aufeinanderfolgende `<pre>`-Zeilen in `toHtml()` - ein Codeblock.
_CODEZEILEN = re.compile(r"(?:<pre\b[^>]*>.*?</pre>\n?)+")


def _codeflaechen(html: str, dunkel: bool) -> str:
    """Legt jeden Codeblock in eine einzellige Tabelle mit Fläche,
    Rahmen und Innenabstand.

    Qt macht aus jeder Zeile eines Codeblocks einen eigenen Absatz.
    Eine Vorlage für `pre` mit Fläche und Rahmen galt deshalb je Zeile,
    und heraus kam ein Stapel einzelner Streifen mit weißen Spalten:
    die Fläche eines Absatzes reicht nicht über den Zeilenabstand, und
    einen Innenabstand kennen Absätze in Qt nicht. Eine Tabellenzelle
    kennt beides. Ein `QTextFrame` am Dokument wäre der andere Weg,
    aber Qt lässt dabei einen leeren Absatz davor stehen und verliert
    den Innenabstand auf dem Weg über HTML.
    """
    flaeche = codeflaeche(dunkel)
    rahmen = coderahmen(dunkel)
    kopf = (
        f'<table width="100%" cellspacing="0" cellpadding="0">'
        f'<tr><td bgcolor="{flaeche}" style="border: 1px solid {rahmen}; '
        f'padding: 8px 12px;">'
    )
    return _CODEZEILEN.sub(
        lambda treffer: kopf + treffer.group(0) + "</td></tr></table>\n",
        html,
    )


#: Schriftangaben im `<body>` von `toHtml()`. Qt schreibt dort die
#: Schrift des Hilfsdokuments fest hin, und als Inline-Angabe schlug
#: sie sowohl die Vorlage als auch die Schriftgröße des Widgets:
#: Strg+Plus und Strg+Mausrad blieben in Hilfeseiten ohne Wirkung, und
#: die kräftigere Schrift im dunklen Thema kam nie an.
_KOERPERSCHRIFT = re.compile(r"\s*font-(?:family|size|weight|style):[^;]*;")


def _koerperschrift_entfernen(html: str) -> str:
    return re.sub(
        r'<body style="([^"]*)"',
        lambda treffer: '<body style="'
        + _KOERPERSCHRIFT.sub("", treffer.group(1))
        + '"',
        html,
        count=1,
    )


_UMLAUTE = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


def anker_name(titel: str) -> str:
    """Der Name eines Sprungziels zu einer Überschrift: „Behälter“
    wird zu „behaelter“, „Auswertung: pcl.analyse“ zu
    „auswertung-pcl-analyse“. Nur ASCII, weil ein Umlaut im Verweis
    als %C3%A4 ankäme und dann zu keinem Ziel mehr passte."""
    name = titel.lower().translate(_UMLAUTE)
    return re.sub(r"[^a-z0-9]+", "-", name).strip("-") or "abschnitt"


def _anker_setzen(dokument: QTextDocument) -> list[tuple[int, str, str]]:
    """Gibt jeder Überschrift der Ebenen 2 und 3 ein Sprungziel und
    liefert (Ebene, Titel, Anker) in der Reihenfolge der Seite."""
    abschnitte: list[tuple[int, str, str]] = []
    vergeben: set[str] = set()
    cursor = QTextCursor(dokument)
    block = dokument.begin()
    while block.isValid():
        ebene = block.blockFormat().headingLevel()
        titel = block.text().strip()
        if ebene in (2, 3) and titel:
            anker = basis = anker_name(titel)
            zaehler = 2
            while anker in vergeben:
                anker = f"{basis}-{zaehler}"
                zaehler += 1
            vergeben.add(anker)
            format_ = QTextCharFormat()
            format_.setAnchor(True)
            format_.setAnchorNames([anker])
            cursor.setPosition(block.position())
            cursor.setPosition(
                block.position() + block.length() - 1,
                QTextCursor.MoveMode.KeepAnchor,
            )
            cursor.mergeCharFormat(format_)
            abschnitte.append((ebene, titel, anker))
        block = block.next()
    return abschnitte


def _inhaltsverzeichnis_einfuegen(
    dokument: QTextDocument, abschnitte: list[tuple[int, str, str]]
) -> None:
    """Setzt vor den ersten Abschnitt, also unter die Einleitung, eine
    Liste mit Verweisen auf alle Abschnitte. Erzeugt aus den
    Überschriften der Seite, damit es mit jedem neuen Abschnitt
    stimmt, ohne dass jemand es pflegt."""
    if not abschnitte:
        return
    block = dokument.begin()
    while block.isValid() and block.blockFormat().headingLevel() not in (
        2,
        3,
    ):
        block = block.next()
    if block.previous().isValid():
        block = block.previous()
    cursor = QTextCursor(block)
    cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
    absatz = QTextBlockFormat()
    zeichen = QTextCharFormat()
    fett = QTextCharFormat()
    fett.setFontWeight(QFont.Weight.Bold)
    cursor.insertBlock(absatz, zeichen)
    cursor.insertText("Inhalt", fett)
    listen: dict[int, QTextList] = {}
    for ebene, titel, anker in abschnitte:
        cursor.insertBlock(absatz, zeichen)
        liste = listen.get(ebene)
        if liste is None:
            art = QTextListFormat()
            art.setStyle(
                QTextListFormat.Style.ListDisc
                if ebene == 2
                else QTextListFormat.Style.ListCircle
            )
            art.setIndent(ebene - 1)
            listen[ebene] = cursor.createList(art)
        else:
            liste.add(cursor.block())
        if ebene == 2:
            # Unterpunkte beginnen unter jedem Abschnitt eine eigene
            # Liste.
            listen.pop(3, None)
        verweis = QTextCharFormat()
        verweis.setAnchor(True)
        verweis.setAnchorHref(f"#{anker}")
        cursor.insertText(titel, verweis)


class HilfeAnsicht(QTextBrowser):
    """Eine Hilfeseite aus Markdown. Nur lesen, nicht ändern.

    Strg+F blendet unten eine Suchleiste ein, die in der Seite sucht.
    Vorher meldete Strg+F in einer Hilfeseite nur, es sei kein
    Quelltext-Reiter vorn, und die Komponenten-Referenz mit rund 90
    Bildschirmseiten ließ sich allein durch Rollen durchsehen
    (Punkt 438)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setOpenExternalLinks(True)
        self.setReadOnly(True)
        self.document().setDocumentMargin(20)
        self._markdown = ""
        self._inhaltsverzeichnis = False
        #: Dunkles Design, wie es das Hauptfenster vorgibt, oder `None`:
        #: dann gilt die eigene Hintergrundfarbe (`_ist_dunkel`).
        self.dunkel: bool | None = None
        self._rand = -1
        self._unten = 0
        self._abschnitte: list[tuple[int, str, str]] = []
        #: Schrift des Quelltexteditors („Ansicht → Schriftart“), die
        #: auch Code-Stellen hier bekommen. `None`: die erste vorhandene
        #: aus `CODE_SCHRIFTEN`.
        self.code_schrift: str | None = None
        #: Grundgröße in Punkt, wie sie das Hauptfenster vorgibt, und
        #: was Strg+Mausrad in dieser Seite dazugedreht hat.
        self._grundgroesse: int | None = None
        self._zoom = 0
        self._suchleiste_bauen()

    # -- Schrift --------------------------------------------------------

    def einstellen(self, dunkel: bool, code_schrift: str, groesse: int) -> None:
        """Design, Codeschrift und Schriftgröße, wie sie das
        Hauptfenster vorgibt, in einem Schritt - eine Seite, die schon
        Inhalt hat, wird dabei nur einmal neu gesetzt."""
        self._grundgroesse = groesse
        self._groesse_anwenden()
        if dunkel == self.dunkel and code_schrift == self.code_schrift:
            return
        self.dunkel = dunkel
        self.code_schrift = code_schrift
        self._neu_setzen()

    def code_schrift_setzen(self, schrift: str) -> None:
        """Nach „Ansicht → Schriftart“: Code-Stellen in der Schrift des
        Editors, an derselben Stelle der Seite."""
        if schrift == self.code_schrift:
            return
        self.code_schrift = schrift
        self._neu_setzen()

    def grundgroesse_setzen(self, groesse: int) -> None:
        """Die Schriftgröße, die das Hauptfenster vorgibt (Strg+Plus,
        Strg+Minus). Was Strg+Mausrad in der Seite verstellt hat,
        bleibt als Abstand dazu erhalten."""
        self._grundgroesse = groesse
        self._groesse_anwenden()

    def schriftgroesse(self) -> int:
        """Die Schriftgröße der Seite in Punkt."""
        grund = self._grundgroesse
        if grund is None:
            grund = self.font().pointSize()
            if grund <= 0:
                grund = 10
            self._grundgroesse = grund
        return max(KLEINSTE_SCHRIFT, min(GROESSTE_SCHRIFT, grund + self._zoom))

    def _groesse_anwenden(self) -> None:
        self.setStyleSheet(
            f"HilfeAnsicht {{ font-size: {self.schriftgroesse()}pt; }}"
        )

    def wheelEvent(self, ereignis) -> None:  # noqa: N802 - Qt-Name
        """Strg+Mausrad macht die Schrift größer oder kleiner, wie im
        Quelltexteditor."""
        if ereignis.modifiers() & Qt.KeyboardModifier.ControlModifier:
            schritt = 1 if ereignis.angleDelta().y() > 0 else -1
            vorher = self.schriftgroesse()
            self._zoom += schritt
            if self.schriftgroesse() == vorher:
                # An der Grenze nicht weiterzählen, sonst bräuchte der
                # Weg zurück ebenso viele Drehungen ins Leere.
                self._zoom -= schritt
            self._groesse_anwenden()
            ereignis.accept()
            return
        super().wheelEvent(ereignis)

    def _neu_setzen(self) -> None:
        """Setzt die Seite neu, an derselben Stelle."""
        if not self._markdown:
            return
        stelle = self.verticalScrollBar().value()
        self.markdown_setzen(self._markdown, self._inhaltsverzeichnis)
        self.verticalScrollBar().setValue(stelle)

    # -- Suchleiste -----------------------------------------------------

    def _suchleiste_bauen(self) -> None:
        self.suchleiste = QFrame(self)
        self.suchleiste.setFrameShape(QFrame.Shape.StyledPanel)
        self.suchleiste.setAutoFillBackground(True)
        zeile = QHBoxLayout(self.suchleiste)
        zeile.setContentsMargins(6, 4, 6, 4)
        zeile.addWidget(QLabel("Suchen:"))
        self.suchfeld = QLineEdit()
        self.suchfeld.setPlaceholderText("Text in dieser Seite")
        self.suchfeld.setClearButtonEnabled(True)
        self.suchfeld.textEdited.connect(self._beim_tippen)
        self.suchfeld.installEventFilter(self)
        zeile.addWidget(self.suchfeld, 1)
        self.weitersuchen_knopf = QPushButton("Weitersuchen")
        self.weitersuchen_knopf.setAutoDefault(False)
        self.weitersuchen_knopf.clicked.connect(lambda: self.weitersuchen())
        zeile.addWidget(self.weitersuchen_knopf)
        self.suchhinweis = QLabel("")
        zeile.addWidget(self.suchhinweis)
        schliessen = QToolButton()
        schliessen.setText("×")
        schliessen.setToolTip("Suchleiste schließen (Esc)")
        schliessen.setAutoRaise(True)
        schliessen.clicked.connect(self.suche_schliessen)
        zeile.addWidget(schliessen)
        self.suchleiste.hide()

    def suche_zeigen(self) -> None:
        """Strg+F: Suchleiste einblenden. Ein markiertes Wort wird
        zum Suchtext."""
        markiert = self.textCursor().selectedText()
        if markiert and " " not in markiert:
            self.suchfeld.setText(markiert)
        self.suchleiste.show()
        self._raender_setzen()
        self.suchfeld.setFocus()
        self.suchfeld.selectAll()

    def suche_schliessen(self) -> None:
        self.suchleiste.hide()
        self.suchhinweis.setText("")
        self._raender_setzen()
        self.setFocus()

    def weitersuchen(self, rueckwaerts: bool = False) -> bool:
        """Der nächste Treffer; am Seitenende geht es oben weiter.
        Liefert `False`, wenn der Text nirgends vorkommt."""
        return self._suchen(self.suchfeld.text(), rueckwaerts, False)

    def _beim_tippen(self, text: str) -> None:
        # Beim Tippen bleibt der Treffer stehen, solange er noch passt.
        self._suchen(text, rueckwaerts=False, am_treffer=True)

    def _suchen(self, text: str, rueckwaerts: bool, am_treffer: bool) -> bool:
        if not text:
            self.suchhinweis.setText("")
            return False
        schalter = QTextDocument.FindFlag(0)
        if rueckwaerts:
            schalter |= QTextDocument.FindFlag.FindBackward
        if am_treffer:
            cursor = self.textCursor()
            cursor.setPosition(cursor.selectionStart())
            self.setTextCursor(cursor)
        if not self.find(text, schalter):
            cursor = self.textCursor()
            cursor.movePosition(
                QTextCursor.MoveOperation.End
                if rueckwaerts
                else QTextCursor.MoveOperation.Start
            )
            self.setTextCursor(cursor)
            if not self.find(text, schalter):
                self.suchhinweis.setText("Nicht gefunden")
                return False
        self.suchhinweis.setText("")
        return True

    def eventFilter(self, objekt: QObject, ereignis: QEvent) -> bool:  # noqa: N802 - Qt-Name
        """Esc schließt die Suchleiste, Eingabe sucht weiter und
        Umschalt+Eingabe zurück."""
        if objekt is self.suchfeld and isinstance(ereignis, QKeyEvent):
            taste = ereignis.key()
            gedrueckt = ereignis.type() == QEvent.Type.KeyPress
            if taste == Qt.Key.Key_Escape:
                # Auch beim ShortcutOverride annehmen, sonst griffe ein
                # Esc-Kürzel des Fensters vor der Suchleiste zu.
                ereignis.accept()
                if gedrueckt:
                    self.suche_schliessen()
                return True
            if gedrueckt and taste in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                umschalt = bool(
                    ereignis.modifiers() & Qt.KeyboardModifier.ShiftModifier
                )
                self.weitersuchen(rueckwaerts=umschalt)
                return True
        return super().eventFilter(objekt, ereignis)

    # -- Abschnitte -----------------------------------------------------

    def abschnitte(self) -> list[tuple[int, str, str]]:
        """(Ebene, Titel, Anker) aller Überschriften der Ebenen 2
        und 3."""
        return list(self._abschnitte)

    def zu_abschnitt(self, name: str) -> bool:
        """Rollt zum Abschnitt über `name`, etwa „Button“ oder
        „SQLQuery“. Passt keine Überschrift genau, zählt eine, in der
        der Name als eigenes Wort vorkommt („SQLQuery und
        DataSource“). Liefert `False`, wenn es keine gibt."""
        ziel = next(
            (anker for _, titel, anker in self._abschnitte if titel == name),
            None,
        )
        if ziel is None:
            ziel = next(
                (
                    anker
                    for _, titel, anker in self._abschnitte
                    if name in re.findall(r"\w+", titel)
                ),
                None,
            )
        if ziel is None:
            return False
        self.scrollToAnchor(ziel)
        return True

    def markdown_setzen(
        self, text: str, inhaltsverzeichnis: bool = False
    ) -> None:
        """Setzt den Inhalt aus Markdown.

        Der Umweg über HTML ist nötig, damit die Vorlage überhaupt
        greift: `document().setDefaultStyleSheet()` wirkt nur beim
        Einlesen von HTML, und `setMarkdown()` geht daran vorbei
        (nachgemessen - mit `setMarkdown` blieb alles bei Qts
        Vorgaben). Was Qt aus dem Markdown gemacht hat, übersteht den
        Umweg vollständig: Überschriften, Tabellen, Listen, Verweise
        und Codeblöcke sind danach alle noch da.
        """
        self._markdown = text
        self._inhaltsverzeichnis = inhaltsverzeichnis
        zwischen = QTextDocument()
        zwischen.setMarkdown(text)
        # Sprungziele an den Überschriften: für das Inhaltsverzeichnis
        # und für F1, das die Referenz an der Stelle einer Komponente
        # öffnet.
        self._abschnitte = _anker_setzen(zwischen)
        if inhaltsverzeichnis:
            _inhaltsverzeichnis_einfuegen(zwischen, self._abschnitte)
        dunkel = self._ist_dunkel()
        _code_einfaerben(zwischen, dunkel)
        self.document().setDefaultStyleSheet(
            stilvorlage(dunkel, code_schriftart(self.code_schrift))
        )
        html = _koerperschrift_entfernen(zwischen.toHtml())
        self.setHtml(_codeflaechen(html, dunkel))
        self._code_schrift_setzen()
        self._breite_begrenzen()

    def _ist_dunkel(self) -> bool:
        """Dunkles Thema? Vorrang hat, was das Hauptfenster über
        `dunkel` vorgibt. Das dunkle Design von Natter kommt allein aus
        dem Stylesheet, die Palette bleibt hell; nach ihr gefragt,
        standen die Codeblöcke im dunklen Design auf hellgrauen
        Streifen in hellgrauer Schrift (Punkt 460). Ohne Vorgabe, etwa
        allein in einem Test, gilt die eigene Hintergrundfarbe."""
        if self.dunkel is not None:
            return self.dunkel
        return self.palette().base().color().lightness() < 128

    def thema_setzen(self, dunkel: bool) -> None:
        """Nach „Ansicht → Design“: setzt die Seite im neuen Design
        neu, an derselben Stelle."""
        if dunkel == self.dunkel:
            return
        self.dunkel = dunkel
        self._neu_setzen()

    def resizeEvent(self, ereignis) -> None:  # noqa: N802 - Qt-Name
        super().resizeEvent(ereignis)
        self._breite_begrenzen()
        self._suchleiste_legen()

    def _raender_setzen(self) -> None:
        """Nach dem Ein- oder Ausblenden der Suchleiste: der
        Sichtbereich macht ihr unten Platz, damit sie keinen Treffer
        verdeckt."""
        self._breite_begrenzen()
        self._suchleiste_legen()

    def _suchleiste_legen(self) -> None:
        """Die Suchleiste liegt im freigehaltenen unteren Rand des
        Sichtbereichs, über der waagerechten und links neben der
        senkrechten Bildlaufleiste."""
        if self.suchleiste.isHidden():
            return
        sicht = self.viewport().geometry()
        rahmen = self.frameWidth()
        breite = self.width() - 2 * rahmen
        leiste = self.verticalScrollBar()
        if leiste.isVisible():
            breite -= leiste.width()
        self.suchleiste.setGeometry(
            rahmen, sicht.bottom() + 1, breite, self._unten
        )
        self.suchleiste.raise_()

    def _breite_begrenzen(self) -> None:
        """Hält die Textspalte schmal genug zum Lesen.

        Über die Ränder des Sichtbereichs und nicht über `max-width`:
        Qts Rich-Text kennt die Angabe nicht. In einem breiten Fenster
        liefe der Text sonst über die ganze Breite, und bei 200
        Zeichen je Zeile findet niemand mehr den nächsten Zeilenanfang.

        Gerechnet wird mit der Breite des Widgets und nicht mit der
        des Sichtbereichs: `setViewportMargins()` ändert dessen
        Breite, das löst wieder `resizeEvent` aus, und die Rechnung
        liefe sich im Kreis, bis der Stapel überläuft. Der Vergleich
        mit dem zuletzt gesetzten Wert ist der zweite Riegel.
        """
        rand = max(0, (self.width() - HOECHSTBREITE) // 2)
        # Unten bekommt die Suchleiste Platz, solange sie offen ist.
        unten = (
            0
            if self.suchleiste.isHidden()
            else self.suchleiste.sizeHint().height()
        )
        if rand == self._rand and unten == self._unten:
            return
        self._rand = rand
        self._unten = unten
        self.setViewportMargins(rand, 0, rand, unten)

    def _code_schrift_setzen(self) -> None:
        """Ersetzt die Gattungsfamilie „monospace“ durch eine, die es
        wirklich gibt.

        Seit die Seiten über HTML eingelesen werden, steht
        `code { font-family: … }` in der Vorlage - und trotzdem
        bleibt dieser Durchlauf nötig. Nachgezählt an den
        Hilfeseiten, was die Vorlage allein übrig lässt:

            komponenten.md      673 Stellen auf „monospace"
            handbuch.md          61
            erste_schritte.md    25

        Qt schreibt beim Umwandeln von Markdown die Familie als
        Inline-Angabe in das Zeichenformat, und die gewinnt gegen die
        Vorlage. In einem kurzen Beispiel fällt das nicht auf, weil
        dort `<code>`-Elemente entstehen; in einer langen Seite mit
        Tabellen ist es die Regel.
        """
        schrift = code_schriftart(self.code_schrift)
        dokument = self.document()
        stellen: list[tuple[int, int]] = []

        block = dokument.begin()
        while block.isValid():
            teil = block.begin()
            while not teil.atEnd():
                stueck = teil.fragment()
                if stueck.isValid() and _IST_CODE in (
                    stueck.charFormat().fontFamilies() or []
                ):
                    stellen.append((stueck.position(), stueck.length()))
                teil += 1
            block = block.next()

        if not stellen:
            return

        # Erst sammeln, dann ändern: ein Eingriff ins Dokument macht die
        # Durchlaufzeiger oben ungültig.
        format_ = QTextCharFormat()
        format_.setFontFamilies([schrift])
        cursor = QTextCursor(dokument)
        cursor.beginEditBlock()
        for anfang, laenge in stellen:
            cursor.setPosition(anfang)
            cursor.setPosition(anfang + laenge, QTextCursor.MoveMode.KeepAnchor)
            cursor.mergeCharFormat(format_)
        cursor.endEditBlock()
