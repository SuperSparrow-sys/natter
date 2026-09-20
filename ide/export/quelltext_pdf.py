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

Dass `QTextDocument.print_()` die Formate des `QSyntaxHighlighter`
mitnimmt, ist nicht selbstverständlich - sie hängen am Layout des
Blocks und nicht am Zeichenformat des Dokuments, und `toHtml()`
verliert sie. Beim Drucken zeichnet dasselbe Layout, deshalb trägt
der Weg.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QMarginsF
from PySide6.QtGui import (
    QColor,
    QFont,
    QPageSize,
    QPdfWriter,
    QTextBlockFormat,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
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

        inhalt = datei.read_text(encoding="utf-8")
        _code_einfuegen(cursor, inhalt)
        erste = False

    _MitNummern(dokument, ueberschriften).rehighlight()
    return dokument


def _code_einfuegen(cursor: QTextCursor, quelltext: str) -> None:
    """Die Zeilen einer Datei, jede als eigener Block."""
    # Keine hängende Einrückung für den umgebrochenen Rest. Sie sah
    # gut aus, kostete aber rund fünf Zeichen Breite in jeder Zeile -
    # und dann brachen erst recht Zeilen um, die sonst gepasst
    # hätten. Als Fortsetzung ist der Rest ohnehin zu erkennen: ihm
    # fehlt die Zeilennummer.
    zeilenformat = QTextBlockFormat()

    code = QTextCharFormat()
    code.setFontFamilies([CODE_SCHRIFT])
    code.setFontPointSize(CODE_GROESSE)

    for zeile in _nummeriert(quelltext):
        cursor.insertBlock()
        cursor.setBlockFormat(zeilenformat)
        cursor.insertText(zeile, code)


def quelltext_als_pdf(
    projekt: Projekt, ziel: Path, jetzt: date | None = None
) -> Path:
    """Schreibt den Quelltext des Projekts nach `ziel` und gibt den
    Pfad zurück."""
    ziel = Path(ziel)
    ziel.parent.mkdir(parents=True, exist_ok=True)

    schreiber = QPdfWriter(str(ziel))
    schreiber.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    schreiber.setPageMargins(QMarginsF(_RAND_MM, _RAND_MM, _RAND_MM, _RAND_MM))
    schreiber.setResolution(_AUFLOESUNG)
    schreiber.setTitle(f"{projekt.name} – Quelltext")

    dokument = dokument_erzeugen(projekt, jetzt)
    flaeche = schreiber.pageLayout().paintRectPixels(_AUFLOESUNG)
    dokument.setPageSize(flaeche.size().toSizeF())
    dokument.print_(schreiber)
    return ziel
