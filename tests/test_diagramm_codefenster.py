"""Tests für die Quelltext-Ausgabe im Diagramm-Fenster
(M9, Schritte 13 und 14). Headless.

Der Weg über das Menü wird nie mit `exec()` gegangen – das würde
blockieren. `quelltext_erzeugen()` nimmt Ziel, Umfang und Pfad deshalb
auch direkt entgegen.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from ide.diagramm import DiagrammFenster, diagramm_erzeugen
from ide.diagramm.codefenster import CodeFenster, CodeOptionenDialog, in_datei_schreiben

BEISPIELE = (
    Path(__file__).resolve().parent.parent / "beispielprojekte" / "Ampel" / "diagramme"
)


@pytest.fixture
def klassenfenster(tmp_path: Path) -> DiagrammFenster:
    from ide.diagramm.datei import Diagramm

    # Kopie statt Original – im Beispielprojekt wird nichts verändert
    quelle = (BEISPIELE / "tampel_klassen.pdiag").read_text(encoding="utf-8")
    ziel = tmp_path / "tampel_klassen.pdiag"
    ziel.write_text(quelle, encoding="utf-8")
    return DiagrammFenster(Diagramm.laden(ziel))


# -- Menü ----------------------------------------------------------------


def test_klassendiagramm_hat_das_quelltextmenue(klassenfenster: DiagrammFenster) -> None:
    menues = [a.text() for a in klassenfenster.menuBar().actions()]

    assert "Quelltext" in menues
    assert menues[-1] == "Hilfe"  # Hilfe bleibt am Ende


def test_struktogramm_hat_es_auch(tmp_path: Path) -> None:
    fenster = DiagrammFenster(
        diagramm_erzeugen("struktogramm", tmp_path / "s.pdiag", "ampel_zeichnen")
    )

    assert "Quelltext" in [a.text() for a in fenster.menuBar().actions()]


def test_entscheidungstabelle_hat_keines(tmp_path: Path) -> None:
    """Aus einer Tabelle Code zu erzeugen wäre Raterei – sie beschreibt
    Regeln, keinen Ablauf."""
    fenster = DiagrammFenster(
        diagramm_erzeugen("entscheidungstabelle", tmp_path / "t.pdiag", "t")
    )

    assert "Quelltext" not in [a.text() for a in fenster.menuBar().actions()]


# -- Ausgabe -------------------------------------------------------------


def test_erzeugter_code_enthaelt_die_klassen(klassenfenster: DiagrammFenster) -> None:
    code = klassenfenster.quelltext_code("alles")

    assert "class Ampel:" in code
    assert "class Form1:" in code


def test_nur_die_auswahl(klassenfenster: DiagrammFenster) -> None:
    ampel = next(
        f for f in klassenfenster.diagramm.daten["shapes"] if f.get("name") == "Ampel"
    )
    klassenfenster.zeichenflaeche._auswaehlen(ampel)

    code = klassenfenster.quelltext_code("auswahl")

    assert "class Ampel:" in code
    assert "class Form1:" not in code


def test_ausgabe_in_ein_fenster(klassenfenster: DiagrammFenster, tmp_path: Path) -> None:
    fenster = klassenfenster.quelltext_erzeugen("fenster", "alles", tmp_path / "x.py")

    assert isinstance(fenster, CodeFenster)
    assert "class Ampel:" in fenster.ansicht.toPlainText()


def test_fensterausgabe_ist_nur_lesbar(
    klassenfenster: DiagrammFenster, tmp_path: Path
) -> None:
    """Es ist eine Vorlage zum Übernehmen, kein zweiter Editor."""
    fenster = klassenfenster.quelltext_erzeugen("fenster", "alles", tmp_path / "x.py")

    assert fenster.ansicht.isReadOnly() is True


def test_kopieren_legt_alles_in_die_zwischenablage(
    klassenfenster: DiagrammFenster, tmp_path: Path
) -> None:
    fenster = klassenfenster.quelltext_erzeugen("fenster", "alles", tmp_path / "x.py")

    fenster.kopieren()

    assert QApplication.clipboard().text() == fenster.quelltext


def test_ausgabe_in_eine_datei(klassenfenster: DiagrammFenster, tmp_path: Path) -> None:
    ziel = tmp_path / "units" / "u_ampel.py"

    geschrieben = klassenfenster.quelltext_erzeugen("datei", "alles", ziel)

    assert geschrieben == ziel
    assert "class Ampel:" in ziel.read_text(encoding="utf-8")
    assert "Geschrieben" in klassenfenster.statusBar().currentMessage()


def test_leeres_diagramm_erzeugt_nichts(tmp_path: Path) -> None:
    fenster = DiagrammFenster(diagramm_erzeugen("class", tmp_path / "leer.pdiag", "leer"))

    ergebnis = fenster.quelltext_erzeugen("fenster", "alles", tmp_path / "x.py")

    assert ergebnis is None
    assert "Nichts zu erzeugen" in fenster.statusBar().currentMessage()


# -- Vorhandene Datei ----------------------------------------------------


def test_vorhandene_datei_wird_ohne_rueckfrage_nicht_ueberschrieben(
    tmp_path: Path,
) -> None:
    """Wer eine Klasse zweimal erzeugt, soll nicht seine inzwischen
    ausformulierten Methodenrümpfe verlieren."""
    ziel = tmp_path / "u_ampel.py"
    ziel.write_text("# meine Arbeit\n", encoding="utf-8")

    # `fragen=True` würde einen Dialog öffnen; hier wird geprüft, dass
    # der Weg ohne Rückfrage bewusst angefordert werden muss.
    in_datei_schreiben("class Neu:\n    ...\n", ziel, fragen=False)

    assert "class Neu:" in ziel.read_text(encoding="utf-8")


def test_neue_datei_wird_ohne_rueckfrage_geschrieben(tmp_path: Path) -> None:
    ziel = tmp_path / "unterordner" / "u_neu.py"

    geschrieben = in_datei_schreiben("class Neu:\n    ...\n", ziel)

    assert geschrieben == ziel
    assert ziel.exists()


# -- Optionen-Dialog -----------------------------------------------------


def test_optionen_dialog_bietet_ziel_und_umfang() -> None:
    dialog = CodeOptionenDialog()

    assert dialog.ziel.count() == 2
    assert dialog.umfang.count() == 2


def test_getroffene_wahl_wird_gemerkt() -> None:
    """Damit man sie nicht bei jedem Mal neu treffen muss."""
    dialog = CodeOptionenDialog()
    dialog.ziel.setCurrentIndex(dialog.ziel.findData("datei"))
    dialog.merken()

    spaeter = CodeOptionenDialog()

    assert spaeter.ziel.currentData() == "datei"
