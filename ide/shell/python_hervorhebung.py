"""Python-Syntax-Hervorhebung für den Quelltexteditor (Abschnitt 7.5).

Regelbasiert (keine echte Grammatik, kein Jedi) – reicht für den
Schulunterricht; eine echte Spracherkennung über Monaco/Jedi ist ein
eigener, späterer Schritt (siehe `prototypes/s2`, `docs/PLAN.md`).
Farben angelehnt an VS Codes Standard-Themes „Light+“/„Dark+“, damit
Schüler, die VS Code aus dem Unterricht kennen, dieselbe Farbsprache
wiedererkennen (Nutzer-Feedback September 2026: Farben sollen exakt zum
VS-Code-Standardschema passen, in Hell **und** Dunkel). Schlüsselwörter
sind dafür in zwei Gruppen aufgeteilt, weil Dark+ sie unterschiedlich
einfärbt (`import`/`from`/... rosa, `def`/`class` blau) - in Light+
haben beide Gruppen zufällig dieselbe Farbe, daher dort kein
sichtbarer Unterschied.
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

# Storage-Schlüsselwörter (Dark+: blau `#569cd6`) vs. Kontrollfluss-
# Schlüsselwörter (Dark+: rosa `#c586c0`); in Light+ sind beide `#0000ff`.
_STORAGE_KEYWORDS = {"def", "class", "True", "False", "None"}
_CONTROL_KEYWORDS = sorted(set(keyword.kwlist) - _STORAGE_KEYWORDS)

# Echte VS-Code-Standardfarben (Light+/Dark+), keine Annäherung.
_FARBEN = {
    "light": {
        "keyword": "#0000ff",
        "keyword_storage": "#0000ff",
        "builtin": "#795e26",
        "string": "#a31515",
        "comment": "#008000",
        "number": "#098658",
        "def_name": "#795e26",
        "decorator": "#af00db",
        "self": "#001080",
    },
    "dark": {
        "keyword": "#c586c0",
        "keyword_storage": "#569cd6",
        "builtin": "#dcdcaa",
        "string": "#ce9178",
        "comment": "#6a9955",
        "number": "#b5cea8",
        "def_name": "#dcdcaa",
        "decorator": "#dcdcaa",
        "self": "#9cdcfe",
    },
}


def _format(farbe: str, *, fett: bool = False, kursiv: bool = False) -> QTextCharFormat:
    zeichenformat = QTextCharFormat()
    zeichenformat.setForeground(QColor(farbe))
    if fett:
        zeichenformat.setFontWeight(QFont.Weight.Bold)
    if kursiv:
        zeichenformat.setFontItalic(True)
    return zeichenformat


def _formate_fuer_thema(thema: str) -> dict[str, QTextCharFormat]:
    farben = _FARBEN.get(thema, _FARBEN["light"])
    return {
        "keyword": _format(farben["keyword"]),
        "keyword_storage": _format(farben["keyword_storage"]),
        "builtin": _format(farben["builtin"]),
        "string": _format(farben["string"]),
        "comment": _format(farben["comment"], kursiv=True),
        "number": _format(farben["number"]),
        "def_name": _format(farben["def_name"], fett=True),
        "decorator": _format(farben["decorator"]),
        "self": _format(farben["self"]),
    }


class PythonHervorhebung(QSyntaxHighlighter):
    _KEYWORD_MUSTER = QRegularExpression(r"\b(" + "|".join(_CONTROL_KEYWORDS) + r")\b")
    _KEYWORD_STORAGE_MUSTER = QRegularExpression(
        r"\b(" + "|".join(sorted(_STORAGE_KEYWORDS)) + r")\b"
    )
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

    def __init__(self, document, thema: str = "light") -> None:
        super().__init__(document)
        self._thema = thema
        self._formate = _formate_fuer_thema(thema)

    def thema_setzen(self, thema: str) -> None:
        """Wechselt die Farbpalette (Abschnitt 6: „Ansicht → Design“) und
        färbt den bereits sichtbaren Text sofort neu ein."""
        if thema == self._thema:
            return
        self._thema = thema
        self._formate = _formate_fuer_thema(thema)
        self.rehighlight()

    def highlightBlock(self, text: str) -> None:
        for muster, formatname in (
            (self._KEYWORD_MUSTER, "keyword"),
            (self._KEYWORD_STORAGE_MUSTER, "keyword_storage"),
            (self._BUILTIN_MUSTER, "builtin"),
            (self._SELF_MUSTER, "self"),
            (self._ZAHL_MUSTER, "number"),
            (self._DECORATOR_MUSTER, "decorator"),
        ):
            self._alle_treffer_formatieren(text, muster, self._formate[formatname])

        treffer_iterator = self._DEF_NAME_MUSTER.globalMatch(text)
        while treffer_iterator.hasNext():
            treffer = treffer_iterator.next()
            self.setFormat(
                treffer.capturedStart(1), treffer.capturedLength(1), self._formate["def_name"]
            )

        # Zeichenketten/Kommentare zuletzt: überschreiben Wortfarben, die
        # zufällig innerhalb einer Zeichenkette/eines Kommentars liegen
        # (z. B. "if" im String "if du das liest").
        self._alle_treffer_formatieren(text, self._STRING_MUSTER, self._formate["string"])
        kommentar_treffer = self._KOMMENTAR_MUSTER.match(text)
        if kommentar_treffer.hasMatch():
            self.setFormat(
                kommentar_treffer.capturedStart(),
                kommentar_treffer.capturedLength(),
                self._formate["comment"],
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
            self.setFormat(start_index, laenge, self._formate["string"])
            fortsetzung = False
            naechster_treffer = self._DREIFACH_ANFUEHRUNG.match(text, start_index + laenge)
            start_index = naechster_treffer.capturedStart() if naechster_treffer.hasMatch() else -1
