"""Die Hilfeseiten sind gesetzt und nicht nur angezeigt.

Punkt 17 der offenen Punkte. Ein längeres Dokument lief über die
ganze Fensterbreite, die Zeilen standen dicht übereinander, und in den
Tabellen klebten die Einträge an den Rahmen. Betroffen waren beide
Wege, denn sie benutzen dieselbe Klasse: die Hilfeseiten unter
„Hilfe" und jede `.md`, die jemand öffnet.

Der Hebel ist ein Umweg über HTML: `setDefaultStyleSheet()` wirkt nur
beim Einlesen von HTML, und `setMarkdown()` geht daran vorbei.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtGui import QColor, QPalette

from ide.viewers.hilfe_ansicht import (
    HOECHSTBREITE,
    ZEILENABSTAND,
    HilfeAnsicht,
    stilvorlage,
)

WURZEL = Path(__file__).resolve().parent.parent

BEISPIEL = """# Überschrift

Ein Absatz mit `code` darin.

| Spalte | Bedeutung |
|---|---|
| `caption` | Was dasteht |

```python
def f():
    pass
```
"""


@pytest.fixture
def ansicht(qtbot) -> HilfeAnsicht:
    a = HilfeAnsicht()
    qtbot.addWidget(a)
    return a


def _fragmente(ansicht: HilfeAnsicht):
    """Alle Textstücke des Dokuments mit ihrem Block."""
    dokument = ansicht.document()
    block = dokument.begin()
    while block.isValid():
        teil = block.begin()
        while not teil.atEnd():
            stueck = teil.fragment()
            if stueck.isValid():
                yield block, stueck
            teil += 1
        block = block.next()


# ----------------------------------------------- Die Vorlage selbst


def test_die_vorlage_setzt_den_zeilenabstand() -> None:
    assert f"line-height: {ZEILENABSTAND}%" in stilvorlage(False, "Consolas")


def test_im_dunklen_thema_ist_die_schrift_kraeftiger() -> None:
    """Helle Schrift auf dunklem Grund wirkt dünner als dieselbe
    Schrift umgekehrt. 500 gleicht das aus, ohne fett zu wirken."""
    assert "font-weight: 500" in stilvorlage(True, "Consolas")
    assert "font-weight: 400" in stilvorlage(False, "Consolas")


def test_die_vorlage_schreibt_keine_textfarbe_fest() -> None:
    """Die Farbe kommt vom Thema der IDE. Eine Vorlage, die sie
    festschriebe, sähe im jeweils anderen Thema falsch aus."""
    for dunkel in (True, False):
        vorlage = stilvorlage(dunkel, "Consolas")
        for zeile in vorlage.splitlines():
            if "color:" in zeile and "background-color:" not in zeile:
                pytest.fail(f"Die Vorlage setzt eine Textfarbe: {zeile.strip()}")


def test_die_tabellen_bekommen_einen_rahmen_und_luft() -> None:
    vorlage = stilvorlage(False, "Consolas")

    assert "border-collapse: collapse" in vorlage
    assert "padding:" in vorlage


def test_die_codeschrift_steht_in_der_vorlage() -> None:
    assert "font-family: Courier New" in stilvorlage(False, "Courier New")


# ----------------------------------------------- Was im Bild ankommt


def test_der_umweg_ueber_html_erhaelt_alles(ansicht: HilfeAnsicht) -> None:
    """Ein Verlust dabei wäre schlimmer als das alte Aussehen."""
    ansicht.markdown_setzen(BEISPIEL)
    text = ansicht.toPlainText()

    assert "Überschrift" in text
    assert "Was dasteht" in text, "Die Tabelle ist verloren gegangen."
    assert "def f():" in text, "Der Codeblock ist verloren gegangen."


def test_der_codeblock_wird_abgesetzt(ansicht: HilfeAnsicht) -> None:
    """Ohne Fläche steht er mitten im Fließtext. In der
    Komponenten-Referenz ist eine Markdown-Tabelle absichtlich als
    Text gesetzt - ohne Absetzung sieht das aus wie eine Tabelle,
    deren Formatierung fehlt."""
    ansicht.markdown_setzen(BEISPIEL)

    flaechen = {
        block.blockFormat().background().color().name()
        for block, stueck in _fragmente(ansicht)
        if "def f():" in stueck.text()
    }

    assert flaechen and flaechen != {"#000000"}, (
        "Der Codeblock hat keine eigene Fläche."
    )


def test_der_zeilenabstand_steht_im_dokument(ansicht: HilfeAnsicht) -> None:
    """Der Punkt, um den es ging: mit `setMarkdown()` blieb alles bei
    Qts Vorgabe, und die Zeilen klebten aufeinander. Geprüft wird
    das fertige Dokument und nicht die Vorlage - dass eine Zeile im
    Stylesheet steht, heißt nicht, dass Qt sie annimmt."""
    ansicht.markdown_setzen(BEISPIEL)

    abstaende = {
        block.blockFormat().lineHeight()
        for block, stueck in _fragmente(ansicht)
        if "Ein Absatz" in stueck.text()
    }

    assert abstaende, "Der Absatz wurde nicht gefunden."
    assert abstaende == {float(ZEILENABSTAND)}, (
        f"Zeilenabstand {abstaende} statt {ZEILENABSTAND} % - die Vorlage "
        f"greift nicht."
    )


def test_code_bekommt_eine_schrift_die_es_gibt(ansicht: HilfeAnsicht) -> None:
    """Qt setzt beim Umwandeln von Markdown die Gattungsfamilie
    „monospace", die es unter Windows nicht gibt."""
    ansicht.markdown_setzen(BEISPIEL)

    offen = [
        stueck.text()
        for _block, stueck in _fragmente(ansicht)
        if "monospace" in (stueck.charFormat().fontFamilies() or [])
    ]

    assert not offen, f"Noch auf „monospace“: {offen[:3]}"


@pytest.mark.parametrize(
    "seite", ["erste_schritte.md", "komponenten.md", "fuer_lehrkraefte.md"]
)
def test_auch_die_langen_seiten_bleiben_sauber(
    ansicht: HilfeAnsicht, seite: str
) -> None:
    """Der Fund, der den alten Umweg gerettet hat: in einer langen
    Seite schreibt Qt die Familie als Inline-Angabe, und die gewinnt
    gegen die Vorlage. Ohne den Nachbesserer blieben in
    `komponenten.md` 673 Stellen auf „monospace"."""
    ansicht.markdown_setzen((WURZEL / "docs" / seite).read_text(encoding="utf-8"))

    offen = sum(
        1
        for _block, stueck in _fragmente(ansicht)
        if "monospace" in (stueck.charFormat().fontFamilies() or [])
    )

    assert offen == 0, f"{seite}: {offen} Stellen blieben auf „monospace“"


# ----------------------------------------------- Die Textbreite


def test_ein_breites_fenster_bekommt_raender(ansicht: HilfeAnsicht) -> None:
    """Bei 200 Zeichen je Zeile findet niemand mehr den nächsten
    Zeilenanfang."""
    ansicht.resize(HOECHSTBREITE + 400, 600)
    ansicht.markdown_setzen(BEISPIEL)

    assert ansicht.viewport().width() <= HOECHSTBREITE + 4


def test_ein_schmales_fenster_bekommt_keine(ansicht: HilfeAnsicht) -> None:
    """Sonst bliebe in einem schmalen Reiter nichts mehr übrig."""
    ansicht.resize(400, 600)
    ansicht.markdown_setzen(BEISPIEL)

    assert ansicht.viewport().width() > 300


def test_die_breite_wandert_beim_vergroessern_mit(ansicht: HilfeAnsicht) -> None:
    """Der Riegel gegen die Endlosschleife darf die Anpassung nicht
    ganz abschalten: `setViewportMargins()` löst selbst ein
    `resizeEvent` aus, deshalb wird mit der Breite des Widgets
    gerechnet und der letzte Wert verglichen."""
    ansicht.resize(400, 600)
    ansicht.markdown_setzen(BEISPIEL)
    schmal = ansicht.viewport().width()

    ansicht.resize(HOECHSTBREITE + 600, 600)

    assert ansicht.viewport().width() <= HOECHSTBREITE + 4
    assert ansicht.viewport().width() > schmal - 400


def test_das_thema_wird_aus_der_eigenen_farbe_gelesen(ansicht: HilfeAnsicht) -> None:
    """Die Ansicht kennt die Einstellungen der IDE nicht - ihre Farbe
    hat sie von dort ohnehin schon."""
    palette = QPalette(ansicht.palette())
    palette.setColor(QPalette.ColorRole.Base, QColor("#1e1e1e"))
    ansicht.setPalette(palette)

    assert ansicht._ist_dunkel() is True

    palette.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
    ansicht.setPalette(palette)

    assert ansicht._ist_dunkel() is False
