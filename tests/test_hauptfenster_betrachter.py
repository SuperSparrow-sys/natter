"""Tests für die IDE-Verdrahtung der Betrachter (Abschnitt 11.3-11.5):
Doppelklick im Explorer auf eine `.csv`-/Bild-/`.html`-Datei öffnet den
passenden Betrachter-Tab statt des Quelltexteditors. Siehe
Arbeitspaket M5, Schritt 7.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtGui import QColor, QPixmap, QTextDocument
from PySide6.QtWidgets import QTreeWidgetItem

from ide.shell.explorer import PFAD_ROLLE
from ide.viewers import BildVorschau, CsvAnsicht, HtmlVorschau, MarkdownAnsicht


def _eintrag(pfad: Path) -> QTreeWidgetItem:
    eintrag = QTreeWidgetItem([pfad.name])
    eintrag.setData(0, PFAD_ROLLE, str(pfad))
    return eintrag


def test_doppelklick_auf_csv_oeffnet_die_csv_ansicht(tmp_path: Path, hauptfenster_bauen) -> None:
    datei = tmp_path / "schueler.csv"
    datei.write_text("name,punkte\nAnna,12\n", encoding="utf-8")
    fenster = hauptfenster_bauen()

    fenster._bei_explorer_doppelklick(_eintrag(datei), 0)

    aktiv = fenster.editor_tabs.currentWidget()
    assert isinstance(aktiv, CsvAnsicht)


def test_doppelklick_auf_bild_oeffnet_die_bildvorschau(tmp_path: Path, hauptfenster_bauen) -> None:
    datei = tmp_path / "bild.png"
    pixmap = QPixmap(10, 10)
    pixmap.fill(QColor("blue"))
    pixmap.save(str(datei), "PNG")
    fenster = hauptfenster_bauen()

    fenster._bei_explorer_doppelklick(_eintrag(datei), 0)

    aktiv = fenster.editor_tabs.currentWidget()
    assert isinstance(aktiv, BildVorschau)


def test_doppelklick_auf_html_oeffnet_die_html_vorschau(tmp_path: Path, hauptfenster_bauen) -> None:
    datei = tmp_path / "seite.html"
    datei.write_text("<h1>Highscore</h1>", encoding="utf-8")
    fenster = hauptfenster_bauen()

    fenster._bei_explorer_doppelklick(_eintrag(datei), 0)

    aktiv = fenster.editor_tabs.currentWidget()
    assert isinstance(aktiv, HtmlVorschau)


def test_doppelklick_auf_dieselbe_datei_aktiviert_nur_den_vorhandenen_tab(
    tmp_path: Path, hauptfenster_bauen,
) -> None:
    datei = tmp_path / "schueler.csv"
    datei.write_text("name,punkte\nAnna,12\n", encoding="utf-8")
    fenster = hauptfenster_bauen()

    fenster._bei_explorer_doppelklick(_eintrag(datei), 0)
    erster_tab_anzahl = fenster.editor_tabs.count()
    fenster._bei_explorer_doppelklick(_eintrag(datei), 0)

    assert fenster.editor_tabs.count() == erster_tab_anzahl

@pytest.mark.parametrize("art", ["html", "md"])
def test_unterseite_im_projekt_reicht_bis_zum_projektordner(
    art: str, tmp_path: Path, hauptfenster_bauen
) -> None:
    """Punkt 382: eine Unterseite `seiten/kontakt.<art>` zeigt das Logo
    aus `../bilder/`, und der Verweis auf `../index.<art>` öffnet die
    Startseite, weil die Grenze der Projektordner ist. Ein Verweis aus
    dem Projektordner hinaus wird weiter abgewiesen, auch wenn die
    Datei dort existiert."""
    projekt = tmp_path / "website"
    (projekt / "seiten").mkdir(parents=True)
    (projekt / "bilder").mkdir()
    (projekt / "main.py").write_text("print('hallo')\n", encoding="utf-8")
    (projekt / "website.natter").write_text(
        json.dumps(
            {
                "format": "natter-project/1",
                "name": "Website",
                "type": "console",
                "main": "main.py",
            }
        ),
        encoding="utf-8",
    )
    logo = projekt / "bilder" / "logo.png"
    pixmap = QPixmap(8, 8)
    pixmap.fill(QColor("green"))
    assert pixmap.save(str(logo), "PNG")
    (tmp_path / f"draussen.{art}").write_text("Fremd", encoding="utf-8")
    if art == "html":
        (projekt / "index.html").write_text(
            "<h1>Startseite</h1>", encoding="utf-8"
        )
        unterseite = projekt / "seiten" / "kontakt.html"
        unterseite.write_text(
            '<h1>Kontakt</h1><img src="../bilder/logo.png">'
            '<a href="../index.html">Zur Startseite</a>',
            encoding="utf-8",
        )
    else:
        (projekt / "index.md").write_text(
            "# Startseite\n", encoding="utf-8"
        )
        unterseite = projekt / "seiten" / "kontakt.md"
        unterseite.write_text(
            "# Kontakt\n\n![Logo](../bilder/logo.png)\n\n"
            "[Zur Startseite](../index.md)\n",
            encoding="utf-8",
        )
    fenster = hauptfenster_bauen()
    fenster.projekt_oeffnen(projekt / "website.natter")

    fenster.oeffnen(unterseite)
    ansicht = fenster.editor_tabs.currentWidget()
    browser = ansicht.browser if art == "html" else ansicht.ansicht
    bildart = QTextDocument.ResourceType.ImageResource
    bild = browser.document().resource(
        bildart, QUrl.fromLocalFile(str(logo))
    )
    leer = getattr(bild, "isNull", None)
    geladen = bild is not None and (
        not leer() if leer is not None else bool(bild)
    )
    assert geladen, "das Logo fehlt"

    ansicht._verweis_geklickt(QUrl(f"../../draussen.{art}"))
    assert "außerhalb" in fenster.statusBar().currentMessage()
    assert fenster.editor_tabs.currentWidget() is ansicht
    assert "Fremd" not in browser.toPlainText()

    ansicht._verweis_geklickt(QUrl(f"../index.{art}"))
    if art == "html":
        assert "Startseite" in browser.toPlainText()
    else:
        startseite = fenster.editor_tabs.currentWidget()
        assert isinstance(startseite, MarkdownAnsicht)
        assert startseite.pfad == projekt / "index.md"


def test_doppelklick_auf_datenbank_und_pdf(
    tmp_path: Path, hauptfenster_bauen, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Punkt 560: eine `.sqlite` verbindet das Panel „Datenbank“, eine
    PDF geht an das Programm, das Windows dafür vorsieht - beides
    endete in „keine Textdatei“."""
    import sqlite3

    datenbank = tmp_path / "konten.sqlite"
    with sqlite3.connect(datenbank) as verbindung:
        verbindung.execute("CREATE TABLE konto (nr INTEGER)")
    verbindung.close()
    pdf = tmp_path / "aufgabe.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    fenster = hauptfenster_bauen()
    uebergeben: list[Path] = []
    monkeypatch.setattr(fenster, "_mit_windows_oeffnen", uebergeben.append)

    fenster._bei_explorer_doppelklick(_eintrag(datenbank), 0)
    fenster._bei_explorer_doppelklick(_eintrag(pdf), 0)

    panel = fenster.datenbank_panel
    assert panel.verbindung is not None
    assert Path(panel.verbindung.database_name) == datenbank
    assert uebergeben == [pdf]
    assert fenster.editor_tabs.count() == 0 or not any(
        "aufgabe" in fenster.editor_tabs.tabText(i)
        for i in range(fenster.editor_tabs.count())
    )
    panel.trennen()
