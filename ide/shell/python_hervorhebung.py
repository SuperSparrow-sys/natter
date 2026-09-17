"""Python-Syntax-Hervorhebung für den Quelltexteditor (Abschnitt 7.5).

Regelbasiert (keine echte Grammatik, kein Jedi) – reicht für den
Schulunterricht; eine echte Spracherkennung über Monaco/Jedi ist ein
eigener, späterer Schritt (siehe `prototypes/s2`, `docs/PLAN.md`).
Farben angelehnt an VS Codes Standard-Theme „Light+“, damit Schüler, die
VS Code aus dem Unterricht kennen, dieselbe Farbsprache wiedererkennen
(Schlüsselwörter blau, Zeichenketten rotbraun, Kommentare grün,
Funktionsnamen/eingebaute Funktionen bräunlich).
"""

from __future__ import annotations

import keyword

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat

# Häufig im Unterricht verwendete eingebaute Funktionen (Abschnitt 12,
# u. a. print/input aus den Konsolenübungen) – keine vollständige Liste
# aller `builtins`, nur die im Kursmaterial tatsächlich relevanten.
_BUILTINS = {
    "print",
    "len",
    "range",
    "input",
    "open",
    "str",
    "int",
    "float",
    "bool",
    "list",
    "dict",
    "set",
    "tuple",
    "type",
    "isinstance",
    "issubclass",
    "super",
    "enumerate",
    "zip",
    "map",
    "filter",
    "sorted",
    "reversed",
    "sum",
    "min",
    "max",
    "abs",
    "round",
    "any",
    "all",
    "iter",
    "next",
    "repr",
    "format",
    "id",
    "hasattr",
    "getattr",
    "setattr",
    "delattr",
    "staticmethod",
    "classmethod",
    "property",
    "callable",
    "vars",
    "dir",
    "object",
}


def _format(farbe: str, *, fett: bool = False, kursiv: bool = False) -> QTextCharFormat:
    zeichenformat = QTextCharFormat()
    zeichenformat.setForeground(QColor(farbe))
    if fett:
        zeichenformat.setFontWeight(QFont.Weight.Bold)
    if kursiv:
        zeichenformat.setFontItalic(True)
    return zeichenformat


_KEYWORD_FORMAT = _format("#0000ff")
_BUILTIN_FORMAT = _format("#795e26")
_STRING_FORMAT = _format("#a31515")
_COMMENT_FORMAT = _format("#008000", kursiv=True)
_NUMBER_FORMAT = _format("#098658")
_DEF_NAME_FORMAT = _format("#795e26", fett=True)
_DECORATOR_FORMAT = _format("#af00db")
_SELF_FORMAT = _format("#001080")


class PythonHervorhebung(QSyntaxHighlighter):
    _KEYWORD_MUSTER = QRegularExpression(r"\b(" + "|".join(sorted(keyword.kwlist)) + r")\b")
    _BUILTIN_MUSTER = QRegularExpression(r"\b(" + "|".join(sorted(_BUILTINS)) + r")\b")
    _SELF_MUSTER = QRegularExpression(r"\b(self|cls)\b")
    _ZAHL_MUSTER = QRegularExpression(r"\b\d+\.?\d*\b")
    _DECORATOR_MUSTER = QRegularExpression(r"@\w+")
    _DEF_NAME_MUSTER = QRegularExpression(r"\b(?:def|class)\s+(\w+)")
    _KOMMENTAR_MUSTER = QRegularExpression(r"#[^\n]*")
    _STRING_MUSTER = QRegularExpression(
        r"(\"[^\"\\\n]*(?:\\.[^\"\\\n]*)*\")|('[^'\\\n]*(?:\\.[^'\\\n]*)*')"
    )
    _DREIFACH_ANFUEHRUNG = QRegularExpression(r"(\"\"\"|''')")

    def highlightBlock(self, text: str) -> None:
        for muster, zeichenformat in (
            (self._KEYWORD_MUSTER, _KEYWORD_FORMAT),
            (self._BUILTIN_MUSTER, _BUILTIN_FORMAT),
            (self._SELF_MUSTER, _SELF_FORMAT),
            (self._ZAHL_MUSTER, _NUMBER_FORMAT),
            (self._DECORATOR_MUSTER, _DECORATOR_FORMAT),
        ):
            self._alle_treffer_formatieren(text, muster, zeichenformat)

        treffer_iterator = self._DEF_NAME_MUSTER.globalMatch(text)
        while treffer_iterator.hasNext():
            treffer = treffer_iterator.next()
            self.setFormat(treffer.capturedStart(1), treffer.capturedLength(1), _DEF_NAME_FORMAT)

        # Zeichenketten/Kommentare zuletzt: überschreiben Wortfarben, die
        # zufällig innerhalb einer Zeichenkette/eines Kommentars liegen
        # (z. B. "if" im String "if du das liest").
        self._alle_treffer_formatieren(text, self._STRING_MUSTER, _STRING_FORMAT)
        kommentar_treffer = self._KOMMENTAR_MUSTER.match(text)
        if kommentar_treffer.hasMatch():
            self.setFormat(
                kommentar_treffer.capturedStart(),
                kommentar_treffer.capturedLength(),
                _COMMENT_FORMAT,
            )

        self._dreifach_zeichenketten_verarbeiten(text)

    def _alle_treffer_formatieren(
        self, text: str, muster: QRegularExpression, zeichenformat: QTextCharFormat
    ) -> None:
        treffer_iterator = muster.globalMatch(text)
        while treffer_iterator.hasNext():
            treffer = treffer_iterator.next()
            self.setFormat(treffer.capturedStart(), treffer.capturedLength(), zeichenformat)

    def _dreifach_zeichenketten_verarbeiten(self, text: str) -> None:
        """`\"\"\"`/`'''`-Zeichenketten über mehrere Zeilen hinweg, nach
        dem Standardmuster aus der Qt-Dokumentation (`previousBlockState`/
        `setCurrentBlockState`).

        Setzt sich eine Zeichenkette aus der vorherigen Zeile fort
        (`fortsetzung`), muss die Suche nach dem schließenden `\"\"\"` ab
        Position 0 beginnen - sonst würde ein schließendes `\"\"\"` direkt
        am Zeilenanfang übersehen (die sonst übliche Verschiebung um 3
        Zeichen gilt nur für ein frisch in dieser Zeile gefundenes
        öffnendes `\"\"\"`, das sonst sich selbst als Ende erkennen würde)."""
        self.setCurrentBlockState(0)

        fortsetzung = self.previousBlockState() == 1
        if fortsetzung:
            start_index = 0
        else:
            treffer = self._DREIFACH_ANFUEHRUNG.match(text)
            start_index = treffer.capturedStart() if treffer.hasMatch() else -1

        while start_index >= 0:
            such_beginn = start_index if fortsetzung else start_index + 3
            end_treffer = self._DREIFACH_ANFUEHRUNG.match(text, such_beginn)
            if end_treffer.hasMatch():
                laenge = end_treffer.capturedEnd() - start_index
            else:
                self.setCurrentBlockState(1)
                laenge = len(text) - start_index
            self.setFormat(start_index, laenge, _STRING_FORMAT)
            fortsetzung = False
            naechster_treffer = self._DREIFACH_ANFUEHRUNG.match(text, start_index + laenge)
            start_index = naechster_treffer.capturedStart() if naechster_treffer.hasMatch() else -1
