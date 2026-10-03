"""Den Quelltext eines Projekts als PDF ausgeben.

Punkt 16 der offenen Punkte. Wer sein Programm abgibt, gibt heute
entweder den ganzen Ordner ab oder druckt aus dem Editor - und ein
`.py` im Anhang lässt sich weder anstreichen noch mit einer Note
versehen. Ein PDF ist das Format, das eine Lehrkraft erwartet, und es
zeigt den Code so, wie die Schülerin ihn vor sich hatte.

Ausgegeben wird das ganze Projekt, eine Datei je Seite, mit
Zeilennummern und der Hervorhebung aus dem Editor. Vier
Entscheidungen stecken darin:

Nur die u_*-Dateien. `main.py` ist der Starter, den Natter schreibt,
und die `u_*_design.py` erzeugt der Designer. `Projekt.units()`
liefert genau diese Auswahl schon.

Immer das helle Thema, unabhängig von der Einstellung in der IDE.
Die Farben des dunklen Themas sind auf weißem Papier unlesbar.

Mit Zeilennummern, sonst lässt sich in der Besprechung nicht auf
eine Stelle zeigen.

Umbrechen statt abschneiden. Ein Blatt ist schmaler als ein
Bildschirm. Was fehlt, fällt nicht auf - siehe Punkt 12 der offenen
Punkte, wo genau das einem Label passiert ist. Der umgebrochene Rest
steht eingerückt unter seiner Zeile und ist dadurch als Fortsetzung
zu erkennen.

Eine Kopfzeile auf jeder Seite. Projekt, Datei, Name, Datum und
„Seite n von m“ stehen oben auf jedem Blatt, auch auf der zweiten
und dritten Seite einer langen Datei - lose Blätter aus zwanzig
Abgaben lassen sich sonst nicht zuordnen. `QTextDocument.print_()`
kennt keine Kopfzeilen, deshalb zeichnet `quelltext_als_pdf` die
Seiten selbst: je Seite die Kopfzeile und darunter den passenden
Ausschnitt des Dokuments.

Dass dabei die Formate des `QSyntaxHighlighter` mitkommen, ist nicht
selbstverständlich - sie hängen am Layout des Blocks und nicht am
Zeichenformat des Dokuments, und `toHtml()` verliert sie. Gezeichnet
wird über dasselbe Layout, deshalb trägt der Weg.
"""

from __future__ import annotations

import getpass
import os
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QMarginsF, QPointF, QRectF, QSizeF, Qt
from PySide6.QtGui import (
    QAbstractTextDocumentLayout,
    QColor,
    QFont,
    QFontMetricsF,
    QPageSize,
    QPainter,
    QPdfWriter,
    QPen,
    QTextBlockFormat,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
    QTextFormat,
    QTextOption,
)

from ide.shell.python_hervorhebung import PythonHervorhebung

if TYPE_CHECKING:  # pragma: no cover - nur für die Typangaben
    from ide.project.projekt import Projekt

#: Die Schrift des Editors, kleiner gesetzt. Nachgemessen mit
#: `QFontMetricsF` auf A4 bei 96 dpi und 20 mm Rand:
#:
#:      8 pt -> 106 Zeichen je Zeile, davon 99 für den Code
#:      9 pt ->  92 Zeichen je Zeile, davon 85 für den Code
#:
#: Genommen wird 8 pt: damit passt so gut wie die ganze Zeilenlänge
#: aufs Blatt, auf die `pyproject.toml` den Quelltext begrenzt. Bei 9
#: Punkt bräche jede zweite längere Zeile um, und ein Ausdruck voller
#: Fortsetzungszeilen liest sich schlecht.
CODE_SCHRIFT = "Consolas"
CODE_GROESSE = 8

#: Die Nummernspalte: vier Stellen und ein senkrechter Strich. Vier
#: reichen für 9999 Zeilen; eine Schülerdatei mit mehr hat andere
#: Probleme. Wird eine Datei doch länger, wächst die Spalte mit,
#: statt die Nummer abzuschneiden.
_ZIFFERN = 4
_TRENNER = " │ "

#: Auflösung wie beim Diagramm-Export: bei 96 dpi entspricht eine
#: PDF-Einheit einem Bildschirmpunkt, und die Maße stimmen mit dem
#: überein, was am Bildschirm zu sehen war.
_AUFLOESUNG = 96

#: Seitenrand in Millimetern. 20 mm ist der übliche Rand für ein
#: Schriftstück und liegt auf jedem Bürodrucker im bedruckbaren
#: Bereich - ein schmalerer Rand sieht am Bildschirm besser aus und
#: wird beim Drucken beschnitten. Zum Anstreichen ist er außerdem
#: gerade recht.
_RAND_MM = 20

#: Grau für die Nummernspalte - lesbar, aber nicht so kräftig, dass
#: sie mit dem Code konkurriert.
_NUMMERNFARBE = "#8a8a8a"

#: Höhe der Kopfzeile samt Abstand zum Code, in Millimetern. Sie geht
#: von der Fläche für den Code ab, damit der Rand zum Drucken bleibt.
_KOPF_MM = 8

#: Am Überschriftsblock jeder Datei hängt ihr Name. Daran findet
#: `seitenkoepfe` heraus, welche Datei auf welcher Seite steht.
_DATEI_EIGENSCHAFT = QTextFormat.Property.UserProperty + 1


class _MitNummern(PythonHervorhebung):
    """Färbt den Code ein und die Zeilennummern grau.

    Die Nummern stehen im Text und nicht neben ihm: nur so wandern
    sie beim Seitenumbruch mit ihrer Zeile mit. Der Preis ist, dass
    die Muster der Hervorhebung auch über sie laufen und in „  12 │"
    eine Zahl finden. Deshalb wird die Spalte hinterher übermalt -
    das ist einfacher und zuverlässiger, als jedes Muster um einen
    Versatz zu ergänzen.
    """

    def __init__(self, document: QTextDocument, ueberschriften: set[int]) -> None:
        super().__init__(document, "light")
        self._ueberschriften = ueberschriften
        self._nummernformat = QTextCharFormat()
        self._nummernformat.setForeground(QColor(_NUMMERNFARBE))

    def highlightBlock(self, text: str) -> None:  # noqa: N802 - Qt-Name
        if self.currentBlock().blockNumber() in self._ueberschriften:
            # Eine Überschrift ist kein Python. Der Blockzustand wird
            # dabei zurückgesetzt, damit ein offener Docstring aus der
            # Datei davor nicht in die nächste hineinfärbt.
            self.setCurrentBlockState(-1)
            return
        super().highlightBlock(text)
        # Bis zum Trennstrich, nicht über eine feste Zahl von Zeichen:
        # eine Datei mit mehr als 9999 Zeilen hat eine breitere Spalte,
        # und dann bliebe der Strich in der Farbe des Codes stehen.
        trenner = text.find("│")
        if trenner > 0 and text[:trenner].strip().isdigit():
            self.setFormat(0, trenner + 1, self._nummernformat)


def _nummeriert(quelltext: str) -> list[str]:
    """Jede Zeile mit ihrer Nummer davor."""
    zeilen = quelltext.splitlines() or [""]
    return [
        f"{nummer:>{_ZIFFERN}}{_TRENNER}{zeile}"
        for nummer, zeile in enumerate(zeilen, 1)
    ]


def dokument_erzeugen(projekt: Projekt, jetzt: date | None = None) -> QTextDocument:
    """Das fertige Dokument - eine Datei je Seite.

    Getrennt vom Schreiben, damit sich der Inhalt prüfen lässt, ohne
    eine PDF-Datei anzulegen und wieder zu lesen.
    """
    heute = jetzt or date.today()
    dokument = QTextDocument()
    dokument.setDefaultFont(QFont(CODE_SCHRIFT, CODE_GROESSE))
    dokument.setDocumentMargin(0)
    # Auch mitten im Wort umbrechen. Der Standard bricht nur an
    # Leerzeichen, und ausgerechnet die Zeilen, die zu lang werden -
    # eine lange Zeichenkette, ein zusammengesetzter Pfad - haben oft
    # keins. Sie liefen sonst über den Rand hinaus und wären auf dem
    # Papier abgeschnitten.
    optionen = QTextOption()
    optionen.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
    dokument.setDefaultTextOption(optionen)

    cursor = QTextCursor(dokument)
    ueberschriften: set[int] = set()
    erste = True

    for datei in projekt.units():
        if not erste:
            cursor.insertBlock()
        block = QTextBlockFormat()
        if not erste:
            # Jede Datei beginnt auf einem neuen Blatt. Zwei Dateien
            # auf einem Blatt liest niemand auseinander.
            block.setPageBreakPolicy(
                QTextBlockFormat.PageBreakFlag.PageBreak_AlwaysBefore
            )
        block.setProperty(_DATEI_EIGENSCHAFT, datei.name)
        cursor.setBlockFormat(block)

        kopf = QTextCharFormat()
        kopf.setFontFamilies([CODE_SCHRIFT])
        kopf.setFontPointSize(CODE_GROESSE + 2)
        kopf.setFontWeight(QFont.Weight.Bold)
        # Projektname, Dateiname und Datum in einer Zeile: bei einer
        # eingesammelten Abgabe ist sonst nicht erkennbar, wessen
        # Datei das ist und von wann.
        cursor.insertText(
            f"{projekt.name} – {datei.name} – {heute.strftime('%d.%m.%Y')}", kopf
        )
        ueberschriften.add(cursor.blockNumber())

        # Eine leere Zeile zwischen Überschrift und Code. Sie zählt
        # als Überschrift, damit die Hervorhebung sie nicht anfasst.
        cursor.insertBlock(QTextBlockFormat(), QTextCharFormat())
        ueberschriften.add(cursor.blockNumber())

        try:
            inhalt = datei.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError as fehler:
            raise ValueError(
                f"„{datei.name}“ ist nicht als UTF-8 gespeichert und lässt sich "
                "nicht ausgeben. Zum Ausgeben die Datei in einem Editor als "
                "UTF-8 speichern."
            ) from fehler
        _code_einfuegen(cursor, inhalt)
        erste = False

    _MitNummern(dokument, ueberschriften).rehighlight()
    return dokument


def _code_einfuegen(cursor: QTextCursor, quelltext: str) -> None:
    """Die Zeilen einer Datei, jede als eigener Block."""
    zeilen = _nummeriert(quelltext)
    # Der umgebrochene Rest einer Zeile beginnt unter dem Code, nicht
    # unter der Nummer (Punkt 518). Bis 0.4.3 stand er ganz links,
    # die Nummernspalte riss auf, und die Fortsetzung sah aus wie
    # eine eigene Zeile ohne Einrückung, was in Python etwas anderes
    # bedeutet. Linker Rand und negativer Einzug der ersten Zeile
    # heben sich auf: die erste Zeile behält ihre volle Breite.
    spalte = zeilen[-1][: zeilen[-1].index(_TRENNER) + len(_TRENNER)]
    breite = QFontMetricsF(QFont(CODE_SCHRIFT, CODE_GROESSE)).horizontalAdvance(
        spalte
    )
    zeilenformat = QTextBlockFormat()
    zeilenformat.setLeftMargin(breite)
    zeilenformat.setTextIndent(-breite)

    code = QTextCharFormat()
    code.setFontFamilies([CODE_SCHRIFT])
    code.setFontPointSize(CODE_GROESSE)

    for zeile in zeilen:
        cursor.insertBlock()
        cursor.setBlockFormat(zeilenformat)
        cursor.insertText(zeile, code)


def anmeldename() -> str:
    """Der Name der angemeldeten Person für die Kopfzeile.

    Zuerst der ausgeschriebene Name aus der Windows-Anmeldung („Anna
    Müller“), den Schulrechner in einer Domäne kennen. Fehlt er, der
    Anmeldename selbst. Eine Klasse bearbeitet meist dieselbe Aufgabe
    unter demselben Projektnamen; ohne Namen der Schülerin ließen
    sich die Ausdrucke nicht auseinanderhalten.
    """
    if os.name == "nt":
        try:
            import ctypes

            name_display = 3
            groesse = ctypes.c_ulong(256)
            puffer = ctypes.create_unicode_buffer(groesse.value)
            secur32 = ctypes.WinDLL("secur32")
            if secur32.GetUserNameExW(
                name_display, puffer, ctypes.byref(groesse)
            ) and puffer.value.strip():
                return puffer.value.strip()
        except (OSError, AttributeError):
            pass
    try:
        return getpass.getuser()
    except (OSError, KeyError):
        return ""


def _kopfhoehe() -> float:
    return _KOPF_MM / 25.4 * _AUFLOESUNG


def seitenkoepfe(
    projekt: Projekt,
    dokument: QTextDocument,
    jetzt: date | None = None,
    name: str = "",
) -> list[tuple[str, str]]:
    """Die Kopfzeile jeder Seite als `(links, rechts)`, in der
    Reihenfolge der Seiten: links Projekt, Datei, Name und Datum,
    rechts „Seite n von m“.

    `dokument` muss seine Seitengröße schon haben; welche Datei auf
    einer Seite steht, ergibt sich erst aus dem Layout.
    """
    heute = (jetzt or date.today()).strftime("%d.%m.%Y")
    seitenhoehe = dokument.pageSize().height()
    seiten = dokument.pageCount()
    layout = dokument.documentLayout()

    datei_je_seite = [""] * seiten
    block = dokument.begin()
    while block.isValid():
        datei = block.blockFormat().property(_DATEI_EIGENSCHAFT)
        if datei:
            oben = layout.blockBoundingRect(block).top()
            erste = min(int(oben // seitenhoehe), seiten - 1)
            for seite in range(erste, seiten):
                datei_je_seite[seite] = str(datei)
        block = block.next()

    koepfe = []
    for nummer, datei in enumerate(datei_je_seite, 1):
        teile = [projekt.name, datei, name, heute]
        links = " – ".join(teil for teil in teile if teil)
        koepfe.append((links, f"Seite {nummer} von {seiten}"))
    return koepfe


def _kopfzeile_zeichnen(
    maler: QPainter, breite: float, links: str, rechts: str
) -> None:
    """Eine Kopfzeile mit einem dünnen Strich darunter."""
    schrift = QFont(CODE_SCHRIFT)
    schrift.setPointSizeF(CODE_GROESSE)
    maler.setFont(schrift)
    maler.setPen(QColor("#444444"))
    zeile = QRectF(0, 0, breite, _kopfhoehe() * 0.6)
    senkrecht = Qt.AlignmentFlag.AlignVCenter
    maler.drawText(zeile, Qt.AlignmentFlag.AlignLeft | senkrecht, links)
    maler.drawText(zeile, Qt.AlignmentFlag.AlignRight | senkrecht, rechts)
    maler.setPen(QPen(QColor(_NUMMERNFARBE), 0.5))
    maler.drawLine(
        QPointF(0, zeile.bottom()), QPointF(breite, zeile.bottom())
    )


def quelltext_als_pdf(
    projekt: Projekt,
    ziel: Path,
    jetzt: date | None = None,
    name: str | None = None,
) -> Path:
    """Schreibt den Quelltext des Projekts nach `ziel` und gibt den
    Pfad zurück. Ohne `name` steht der Name aus der Windows-Anmeldung
    in der Kopfzeile."""
    ziel = Path(ziel)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    if name is None:
        name = anmeldename()

    schreiber = QPdfWriter(str(ziel))
    schreiber.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    schreiber.setPageMargins(QMarginsF(_RAND_MM, _RAND_MM, _RAND_MM, _RAND_MM))
    schreiber.setResolution(_AUFLOESUNG)
    schreiber.setTitle(f"{projekt.name} – Quelltext")
    if name:
        schreiber.setCreator(name)

    dokument = dokument_erzeugen(projekt, jetzt)
    flaeche = schreiber.pageLayout().paintRectPixels(_AUFLOESUNG)
    kopfhoehe = _kopfhoehe()
    seite = QSizeF(flaeche.width(), flaeche.height() - kopfhoehe)
    dokument.setPageSize(seite)
    koepfe = seitenkoepfe(projekt, dokument, jetzt, name)

    maler = QPainter(schreiber)
    try:
        for index, (links, rechts) in enumerate(koepfe):
            if index:
                schreiber.newPage()
            _kopfzeile_zeichnen(maler, seite.width(), links, rechts)
            maler.save()
            maler.translate(0, kopfhoehe - index * seite.height())
            ausschnitt = QRectF(
                0, index * seite.height(), seite.width(), seite.height()
            )
            maler.setClipRect(ausschnitt)
            kontext = QAbstractTextDocumentLayout.PaintContext()
            kontext.clip = ausschnitt
            dokument.documentLayout().draw(maler, kontext)
            maler.restore()
    finally:
        maler.end()
    return ziel
