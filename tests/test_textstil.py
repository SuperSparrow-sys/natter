"""Natters Texte sprechen niemanden direkt an.

Weder „du" noch „Sie" - in Meldungen, Hilfeseiten, Projektvorlagen und
auf den Textseiten des Installers. Formuliert wird unpersönlich, wie
in deutscher Software üblich: „Die Datei lässt sich nicht öffnen",
„Zum Fortfahren die Bedingungen annehmen".

Was dieser Test bewusst nicht anfasst: die Ausgaben der
Beispielprogramme. `input("Wie heißt du? ")` ist das Programm einer
Schülerin, das mit seinem Benutzer spricht - nicht Natter, das mit der
Schülerin spricht. Ein Begrüßungsprogramm, das „Wie ist der Name?"
fragt, wäre gestelzt und pädagogisch falsch.

Dazu die zweite Regel: Kommentare und Docstrings tragen keine
Markdown-Hervorhebung. `**so**` schreibt niemand in Quelltext; es war
das deutlichste Zeichen dafür, dass ein Text nicht von Hand entstanden
ist.
"""

from __future__ import annotations

import io
import re
import tokenize
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent

DU_FORMEN = re.compile(
    r"\b(du|dir|dich|dein|deine|deinen|deinem|deines|deiner|Du|Dir|Dich|Dein|Deine)\b"
)

#: „Sie" nur mitten im Satz. Am Satzanfang ist es das gewöhnliche
#: „sie", nur groß geschrieben („Die Beispiele … Sie sind keine
#: Sammlung"), und das ist keine Anrede. Davor muss deshalb ein
#: Buchstabe oder ein Komma stehen - kein Punkt, keine Klammer, kein
#: Zeilenanfang.
SIE_FORMEN = re.compile(r"(?<=[a-zäöüß,]) (Sie|Ihnen|Ihre|Ihren|Ihrem|Ihres|Ihrer)\b")

#: Dateien, die jemand liest und die deshalb der Regel unterliegen.
TEXTDATEIEN = [
    *sorted((WURZEL / "templates").rglob("*.template")),
    WURZEL / "tools" / "lizenz_vorlagen" / "INSTALLER_LIZENZ.txt",
    WURZEL / "tools" / "lizenz_vorlagen" / "INSTALLER_HINWEIS.txt",
    WURZEL / "docs" / "erste_schritte.md",
    WURZEL / "docs" / "umstieg_pascal_python.md",
    WURZEL / "docs" / "komponenten.md",
]


def _lesen(pfad: Path) -> str:
    return pfad.read_text(encoding="utf-8-sig")


@pytest.mark.parametrize("pfad", TEXTDATEIEN, ids=lambda p: p.name)
def test_kein_du_in_den_texten(pfad: Path) -> None:
    treffer = [
        f"Zeile {nummer}: {zeile.strip()}"
        for nummer, zeile in enumerate(_lesen(pfad).splitlines(), 1)
        if DU_FORMEN.search(zeile)
    ]
    assert not treffer, f"{pfad.name} spricht direkt an:\n" + "\n".join(treffer[:5])


@pytest.mark.parametrize("pfad", TEXTDATEIEN, ids=lambda p: p.name)
def test_kein_sie_in_den_texten(pfad: Path) -> None:
    treffer = [
        f"Zeile {nummer}: {zeile.strip()}"
        for nummer, zeile in enumerate(_lesen(pfad).splitlines(), 1)
        if SIE_FORMEN.search(zeile)
    ]
    assert not treffer, f"{pfad.name} siezt:\n" + "\n".join(treffer[:5])


def test_die_liste_der_textdateien_stimmt() -> None:
    """Sonst prüfte der Test oben stillschweigend nichts."""
    assert len(TEXTDATEIEN) >= 8
    for pfad in TEXTDATEIEN:
        assert pfad.is_file(), pfad


# --------------------------------------------------- Quelltext der IDE


def _python_dateien() -> list[Path]:
    dateien = []
    for teil in ("ide", "pcl"):
        for pfad in sorted((WURZEL / teil).rglob("*.py")):
            if "__pycache__" not in pfad.parts:
                dateien.append(pfad)
    return dateien


ALLE_PYTHON = _python_dateien()


def _kommentare_und_docstrings(pfad: Path) -> list[tuple[int, str]]:
    quelle = pfad.read_text(encoding="utf-8")
    stuecke = []
    vorheriger = tokenize.INDENT
    for marke in tokenize.generate_tokens(io.StringIO(quelle).readline):
        ist_docstring = marke.type == tokenize.STRING and vorheriger in (
            tokenize.INDENT,
            tokenize.NEWLINE,
            tokenize.NL,
            tokenize.DEDENT,
            tokenize.ENCODING,
        )
        if marke.type == tokenize.COMMENT or ist_docstring:
            stuecke.append((marke.start[0], marke.string))
        if marke.type not in (tokenize.COMMENT, tokenize.NL):
            vorheriger = marke.type
    return stuecke


def test_keine_markdown_hervorhebung_in_kommentaren() -> None:
    """`**so**` in einem Python-Kommentar schreibt kein Mensch."""
    fett = re.compile(r"\*\*(?!\s)[^*\n]+?(?<!\s)\*\*")
    treffer = []
    for pfad in ALLE_PYTHON:
        for nummer, text in _kommentare_und_docstrings(pfad):
            if fett.search(text):
                treffer.append(f"{pfad.relative_to(WURZEL)}:{nummer}")
    assert not treffer, "Markdown-Fettschrift im Quelltext:\n" + "\n".join(treffer[:10])


def test_keine_datumsetiketten_in_kommentaren() -> None:
    """„Nutzer-Feedback September 2026:" vor jeder Begründung war das
    zweite Erkennungszeichen. Die Begründung bleibt, das Etikett
    nicht."""
    etikett = re.compile(r"Nutzer-(Feedback|Wunsch|Vorgabe|Auftrag|Meldung)")
    treffer = []
    for pfad in ALLE_PYTHON:
        for nummer, text in _kommentare_und_docstrings(pfad):
            if etikett.search(text):
                treffer.append(f"{pfad.relative_to(WURZEL)}:{nummer}")
    assert not treffer, "Zuschreibungs-Etikett im Quelltext:\n" + "\n".join(treffer[:10])


def test_die_meldungen_der_ide_sprechen_niemanden_an() -> None:
    """Nur die Anrede mit „du": ein „Sie" liesse sich von einem
    gewöhnlichen „sie" am Satzanfang nicht zuverlässig unterscheiden."""
    treffer = []
    for pfad in ALLE_PYTHON:
        quelle = pfad.read_text(encoding="utf-8")
        for marke in tokenize.generate_tokens(io.StringIO(quelle).readline):
            if marke.type != tokenize.STRING:
                continue
            # Nur Texte, die wie ein Satz aussehen - kein Bezeichner,
            # kein Muster, kein Pfad.
            inhalt = marke.string
            if " " not in inhalt or len(inhalt) < 12:
                continue
            if DU_FORMEN.search(inhalt):
                treffer.append(f"{pfad.relative_to(WURZEL)}:{marke.start[0]}: {inhalt[:70]}")
    assert not treffer, "Direkte Anrede in einem Text:\n" + "\n".join(treffer[:10])
