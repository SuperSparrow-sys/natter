"""Tests für die Python-Syntax-Hervorhebung (Abschnitt 7.5). Headless.
Prüft die zugewiesene Zeichenfarbe an bestimmten Textpositionen gegen
ein echtes `QTextDocument` (kein Mock, echtes Qt-Highlighting).
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QFont, QTextDocument

from ide.shell.python_hervorhebung import PythonHervorhebung


def _dokument(text: str, thema: str = "light") -> QTextDocument:
    dokument = QTextDocument()
    dokument.setPlainText(text)
    hervorhebung = PythonHervorhebung(dokument, thema)
    hervorhebung.rehighlight()
    return dokument


@dataclass(frozen=True)
class _Format:
    farbe: str
    fett: bool
    kursiv: bool


_STANDARD_FORMAT = _Format(farbe="#000000", fett=False, kursiv=False)


def _format_bei(dokument: QTextDocument, index: int) -> _Format:
    # Der Syntax-Highlighter legt seine Formatierung als zusätzliche
    # Formatierung im QTextLayout des Blocks ab, nicht im charFormat()
    # des Dokuments selbst (das bliebe ohne Highlighter beim Standard-
    # Zeichenformat) - deshalb hier direkt im Layout nachsehen. Die
    # eigentlichen Werte werden sofort in ein einfaches Python-Objekt
    # kopiert, weil die von `formats()` gelieferten `QTextCharFormat`-
    # Objekte nur so lange gültig bleiben, wie die Ergebnisliste selbst.
    block = dokument.findBlock(index)
    offset = index - block.position()
    for bereich in block.layout().formats():
        if bereich.start <= offset < bereich.start + bereich.length:
            zeichenformat = bereich.format
            return _Format(
                farbe=zeichenformat.foreground().color().name(),
                fett=zeichenformat.fontWeight() == QFont.Weight.Bold,
                kursiv=zeichenformat.fontItalic(),
            )
    return _STANDARD_FORMAT


def test_schluesselwort_ist_blau() -> None:
    dokument = _dokument("def f():\n    pass\n")
    formatierung = _format_bei(dokument, 0)  # "d" von "def"
    assert formatierung.farbe == "#0000ff"


def test_zeichenkette_ist_rotbraun() -> None:
    dokument = _dokument('x = "hallo"\n')
    formatierung = _format_bei(dokument, 5)  # "h" von "hallo"
    assert formatierung.farbe == "#a31515"


def test_kommentar_ist_gruen_und_kursiv() -> None:
    dokument = _dokument("x = 1  # ein Kommentar\n")
    formatierung = _format_bei(dokument, 9)  # innerhalb des Kommentars
    assert formatierung.farbe == "#008000"
    assert formatierung.kursiv is True


def test_print_als_eingebaute_funktion_ist_braun() -> None:
    dokument = _dokument('print("hallo")\n')
    formatierung = _format_bei(dokument, 0)  # "p" von "print"
    assert formatierung.farbe == "#795e26"


def test_zahl_ist_gruenlich() -> None:
    dokument = _dokument("x = 42\n")
    formatierung = _format_bei(dokument, 4)  # "4" von "42"
    assert formatierung.farbe == "#098658"


def test_funktionsname_nach_def_ist_fett() -> None:
    dokument = _dokument("def meine_funktion():\n    pass\n")
    formatierung = _format_bei(dokument, 4)  # "m" von "meine_funktion"
    assert formatierung.farbe == "#795e26"
    assert formatierung.fett is True


def test_self_ist_gesondert_eingefaerbt() -> None:
    text = "class X:\n    def f(self):\n        self.x = 1\n"
    dokument = _dokument(text)
    index = text.rindex("self")  # "self" in "self.x", nicht im Parameter
    formatierung = _format_bei(dokument, index)
    assert formatierung.farbe == "#001080"


def test_schluesselwort_innerhalb_einer_zeichenkette_wird_nicht_als_schluesselwort_gefaerbt() -> (
    None
):
    dokument = _dokument('x = "if das hier steht"\n')
    formatierung = _format_bei(dokument, 5)  # "i" von "if" INNERHALB der Zeichenkette
    assert formatierung.farbe == "#a31515"


def test_mehrzeilige_zeichenkette_wird_auf_beiden_zeilen_erkannt() -> None:
    dokument = _dokument('x = """erste\nzweite"""\n')
    erste_zeile_format = _format_bei(dokument, 6)  # "e" von "erste" (Zeile 1)
    zweite_block = dokument.findBlockByNumber(1)
    zweite_zeile_format = _format_bei(dokument, zweite_block.position() + 1)  # "z" von "zweite"
    assert erste_zeile_format.farbe == "#a31515"
    assert zweite_zeile_format.farbe == "#a31515"


def test_raute_innerhalb_einer_zeichenkette_ist_kein_kommentarbeginn() -> None:
    # Real per Nutzer-Screenshot gefunden: `_FARBE_AUS = "#000000"` wurde
    # ab dem "#" grün/kursiv (Kommentarfarbe) statt rotbraun eingefärbt.
    text = '_FARBE_AUS = "#000000"\n'
    dokument = _dokument(text)
    index = text.index("#000000")
    formatierung = _format_bei(dokument, index)
    assert formatierung.farbe == "#a31515"
    assert formatierung.kursiv is False


def test_echter_kommentar_nach_einer_zeichenkette_bleibt_ein_kommentar() -> None:
    text = 'x = "#000000"  # das ist eine Farbe\n'
    dokument = _dokument(text)
    index = text.index("# das")
    formatierung = _format_bei(dokument, index)
    assert formatierung.farbe == "#008000"
    assert formatierung.kursiv is True


# -- Dunkles Design (VS Code "Dark+", gemeldet) -----


def test_dark_control_schluesselwort_ist_rosa() -> None:
    dokument = _dokument('from x import y\n', thema="dark")
    formatierung = _format_bei(dokument, 0)  # "f" von "from"
    assert formatierung.farbe == "#c586c0"


def test_dark_def_schluesselwort_ist_blau() -> None:
    dokument = _dokument("def f():\n    pass\n", thema="dark")
    formatierung = _format_bei(dokument, 0)  # "d" von "def"
    assert formatierung.farbe == "#569cd6"


def test_dark_zeichenkette_ist_orange() -> None:
    dokument = _dokument('x = "hallo"\n', thema="dark")
    formatierung = _format_bei(dokument, 5)
    assert formatierung.farbe == "#ce9178"


def test_dark_kommentar_ist_gruen_und_kursiv() -> None:
    dokument = _dokument("x = 1  # ein Kommentar\n", thema="dark")
    formatierung = _format_bei(dokument, 9)
    assert formatierung.farbe == "#6a9955"
    assert formatierung.kursiv is True


def test_dark_zahl_hat_helles_gruen() -> None:
    dokument = _dokument("x = 42\n", thema="dark")
    formatierung = _format_bei(dokument, 4)
    assert formatierung.farbe == "#b5cea8"


def test_dark_self_ist_hellblau() -> None:
    text = "class X:\n    def f(self):\n        self.x = 1\n"
    dokument = _dokument(text, thema="dark")
    index = text.rindex("self")
    formatierung = _format_bei(dokument, index)
    assert formatierung.farbe == "#9cdcfe"


def test_thema_wechseln_faerbt_sofort_neu_ein() -> None:
    dokument = QTextDocument()
    dokument.setPlainText("def f():\n    pass\n")
    hervorhebung = PythonHervorhebung(dokument, "light")
    hervorhebung.rehighlight()
    assert _format_bei(dokument, 0).farbe == "#0000ff"

    hervorhebung.thema_setzen("dark")

    assert _format_bei(dokument, 0).farbe == "#569cd6"
