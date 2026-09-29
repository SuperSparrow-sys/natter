"""Eine `.md`-Datei wird gesetzt angezeigt, nicht als Rohtext
(Abschnitt 11.6).

Bis landete jede `.md` im Quelltexteditor. Wer die
`README.md` eines Beispielprojekts anklickte, bekam `## Überschrift`,
`fett` und Tabellen aus Strichen zu sehen - in einem Fenster mit
Zeilennummern und Syntaxhervorhebung. Für die vier eingebauten
Hilfeseiten war das seit M11 gelöst, für eine selbst geöffnete Datei
nicht.

Geprüft wird deshalb nicht, dass ein Widget entsteht, sondern dass die
Auszeichnung wirklich verschwunden ist: keine Rauten, keine
Sternchen, keine Striche mehr im angezeigten Text.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QUrl

from ide.shell.hauptfenster import HauptFenster
from ide.shell.quelltexteditor import QuelltextEditor
from ide.viewers import MarkdownAnsicht, ueberschrift_lesen

BEISPIEL = """# Obstsortierer

Ein **wichtiger** Satz mit `code` darin.

## Zutaten

- Äpfel
- Birnen

| Sorte | Preis |
|---|---|
| Apfel | 1,20 |
"""


@pytest.fixture
def datei(tmp_path: Path) -> Path:
    pfad = tmp_path / "README.md"
    pfad.write_text(BEISPIEL, encoding="utf-8")
    return pfad


def test_die_auszeichnung_ist_verschwunden(datei: Path, qtbot) -> None:
    """Der eigentliche Punkt: kein `#`, kein `**`, keine Tabellenstriche
    mehr im angezeigten Text."""
    ansicht = MarkdownAnsicht(datei)
    qtbot.addWidget(ansicht)

    text = ansicht.text()

    assert "Obstsortierer" in text
    assert "wichtiger" in text
    assert "#" not in text
    assert "**" not in text
    assert "|" not in text
    assert "- Äpfel" not in text


def test_die_tabelle_bleibt_eine_tabelle(datei: Path, qtbot) -> None:
    """Gesetzt heißt nicht „Striche entfernt": die Zeilen der Tabelle
    müssen im Dokument als Tabelle stehen, sonst stünde alles
    hintereinander."""
    ansicht = MarkdownAnsicht(datei)
    qtbot.addWidget(ansicht)

    html = ansicht.ansicht.document().toHtml()

    assert "<table" in html
    assert "Apfel" in html


def test_code_stellen_bekommen_eine_vorhandene_schriftart(datei: Path, qtbot) -> None:
    """Die Falle aus M12: Qt setzt Code-Stellen auf die Gattungsfamilie
    „monospace", die es unter Windows nicht gibt - aus `u_main.py` wurde
    „u_m⌐H h_desig⌐h py"."""
    ansicht = MarkdownAnsicht(datei)
    qtbot.addWidget(ansicht)

    assert "monospace" not in ansicht.ansicht.document().toHtml()


def test_die_ansicht_laedt_nach_einer_aenderung_neu(datei: Path, qtbot) -> None:
    """Wer im Editor schreibt und zurückwechselt, soll das Ergebnis
    sehen."""
    ansicht = MarkdownAnsicht(datei)
    qtbot.addWidget(ansicht)
    assert "Kiwi" not in ansicht.text()

    datei.write_text(BEISPIEL + "\n- Kiwi\n", encoding="utf-8")
    # `QFileSystemWatcher` braucht eine laufende Ereignisschleife; der
    # Test ruft den Weg deshalb direkt auf, statt auf das Signal zu
    # warten - geprüft wird das Neuladen, nicht Qts Dateiüberwachung.
    ansicht._neu_laden()

    assert "Kiwi" in ansicht.text()


def test_eine_datei_in_windows_codepage_bleibt_lesbar(tmp_path: Path, qtbot) -> None:
    """Eine von Hand angelegte Datei kann cp1252 sein. Lieber mit
    falschen Umlauten anzeigen als den Reiter leer lassen."""
    pfad = tmp_path / "alt.md"
    pfad.write_bytes("# Übung\n\nGrüße".encode("cp1252"))

    ansicht = MarkdownAnsicht(pfad)
    qtbot.addWidget(ansicht)

    assert "bung" in ansicht.text()


# --------------------------------------------------------------- Verweise


def test_ein_verweis_auf_eine_nachbardatei_geht_in_natter_auf(
    datei: Path, qtbot
) -> None:
    """Sonst führte er ins Leere oder - schlimmer - an Windows vorbei in
    ein fremdes Programm."""
    nachbar = datei.parent / "u_main.py"
    nachbar.write_text("print('hallo')\n", encoding="utf-8")
    ansicht = MarkdownAnsicht(datei)
    qtbot.addWidget(ansicht)

    with qtbot.waitSignal(ansicht.datei_angefordert) as gefangen:
        ansicht._verweis_geklickt(QUrl("u_main.py"))

    assert gefangen.args[0] == nachbar


def test_ein_verweis_ins_internet_geht_an_den_browser(
    datei: Path, qtbot, monkeypatch: pytest.MonkeyPatch
) -> None:
    gerufen: list[str] = []
    monkeypatch.setattr(
        "ide.viewers.markdown_ansicht.open_url", lambda adresse: gerufen.append(adresse)
    )
    ansicht = MarkdownAnsicht(datei)
    qtbot.addWidget(ansicht)

    ansicht._verweis_geklickt(QUrl("https://example.org/hilfe"))

    assert gerufen == ["https://example.org/hilfe"]


def test_ein_verweis_ins_leere_stuerzt_nicht_ab(datei: Path, qtbot) -> None:
    """Ohne Hauptfenster gibt es keine Statusleiste - und trotzdem darf
    nichts passieren."""
    ansicht = MarkdownAnsicht(datei)
    qtbot.addWidget(ansicht)

    ansicht._verweis_geklickt(QUrl("gibtsnicht.md"))


# --------------------------------------------------------------- Im Fenster


def test_oeffnen_zeigt_markdown_gesetzt_statt_im_editor(datei: Path, qtbot) -> None:
    """Der Weg, den der Nutzer geht: Datei öffnen."""
    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    fenster.oeffnen(datei)

    widget = fenster.editor_tabs.currentWidget()
    assert isinstance(widget, MarkdownAnsicht)
    assert not isinstance(widget, QuelltextEditor)


def test_der_reiter_traegt_die_ueberschrift(datei: Path, qtbot) -> None:
    """Zwei Reiter mit der Aufschrift „README.md" wären nicht
    auseinanderzuhalten."""
    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    fenster.oeffnen(datei)

    assert fenster.editor_tabs.tabText(fenster.editor_tabs.currentIndex()) == "Obstsortierer"


def test_ohne_ueberschrift_bleibt_der_dateiname(tmp_path: Path, qtbot) -> None:
    pfad = tmp_path / "notizen.md"
    pfad.write_text("Nur Text, keine Überschrift.\n", encoding="utf-8")
    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    fenster.oeffnen(pfad)

    assert fenster.editor_tabs.tabText(fenster.editor_tabs.currentIndex()) == "notizen.md"


def test_quelltext_bearbeiten_oeffnet_wirklich_den_editor(datei: Path, qtbot) -> None:
    """Der Fehler, der dabei beinahe entstanden wäre: `datei_oeffnen`
    fand den Betrachter über denselben Pfad und holte ihn nur wieder
    nach vorn - der Knopf hätte nichts getan."""
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    fenster.oeffnen(datei)
    ansicht = fenster.editor_tabs.currentWidget()

    ansicht._bearbeiten_knopf.click()

    editor = fenster.editor_tabs.currentWidget()
    assert isinstance(editor, QuelltextEditor)
    assert editor.toPlainText() == BEISPIEL
    assert fenster.editor_tabs.count() == 2


def test_ein_zweites_oeffnen_macht_keinen_zweiten_reiter(datei: Path, qtbot) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    fenster.oeffnen(datei)
    fenster.oeffnen(datei)

    assert fenster.editor_tabs.count() == 1


def test_eine_md_datei_neben_einem_offenen_editor_wird_trotzdem_gesetzt(
    datei: Path, qtbot
) -> None:
    """Wer sie im Editor offen hat und aus dem Explorer anklickt, will
    sie gesetzt sehen."""
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    fenster.datei_oeffnen(datei)

    fenster.oeffnen(datei)

    assert isinstance(fenster.editor_tabs.currentWidget(), MarkdownAnsicht)


def test_eine_py_datei_geht_weiter_in_den_editor(tmp_path: Path, qtbot) -> None:
    """Die Unterscheidung darf nichts anderes verschoben haben."""
    pfad = tmp_path / "u_main.py"
    pfad.write_text("print('hallo')\n", encoding="utf-8")
    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    fenster.oeffnen(pfad)

    assert isinstance(fenster.editor_tabs.currentWidget(), QuelltextEditor)


# --------------------------------------------------------------- Überschrift


@pytest.mark.parametrize(
    ("text", "erwartet"),
    [
        ("# Titel\n\nText", "Titel"),
        ("Vorspann\n\n# Titel", "Titel"),
        ("## Nur zweite Ebene", None),
        ("Kein Titel", None),
        ("#\n", None),
        ("#kein Leerzeichen", None),
    ],
)
def test_ueberschrift_lesen(text: str, erwartet: str | None) -> None:
    assert ueberschrift_lesen(text) == erwartet


def test_eine_ueberschrift_ganz_unten_zaehlt_nicht() -> None:
    """Sonst müsste für den Reitertitel jede Datei ganz gelesen
    werden."""
    assert ueberschrift_lesen("\n" * 50 + "# Spät") is None
