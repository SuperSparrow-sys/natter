"""Eine aus dem Diagramm erzeugte Klasse landet im Editor.

Punkt 10 der offenen Punkte. Vorher schrieb „Speichern unter …" die
Datei, und danach passierte nichts: `speichern_unter()` gab den Pfad
zurück, aber niemand öffnete ihn. Die Schülerin musste ihre eben
erzeugte Klasse selbst im Projekt-Explorer suchen — und am
20. September landete sie sogar in einem eigens angelegten, sonst
leeren Ordner, weil der Dialog in gar keinem Ordner begann.

Der Weg ist bewusst über ein Signal gebaut und nicht über eine
Referenz: der Diagramm-Editor ist ein eigenes Fenster und soll das
Hauptfenster nicht kennen müssen. Dasselbe Muster benutzt der
Projekt-Explorer für `umbenennen_angefordert`.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from ide.diagramm.codefenster import CodeFenster
from ide.shell.hauptfenster import HauptFenster

BEISPIEL = Path(__file__).resolve().parent.parent / "beispielprojekte" / "06_Kontoverwaltung"


def _projekt_kopie(tmp_path: Path) -> Path:
    ziel = tmp_path / "06_Kontoverwaltung"
    shutil.copytree(BEISPIEL, ziel)
    return ziel / "06_Kontoverwaltung.natter"


# ------------------------------------------- Das Fenster meldet sich


def test_das_codefenster_beginnt_im_vorgeschlagenen_ordner(tmp_path: Path, qtbot) -> None:
    fenster = CodeFenster("x = 1\n", "Quelltext", vorschlag=tmp_path / "u_konto.py")
    qtbot.addWidget(fenster)

    assert fenster.vorschlag == tmp_path / "u_konto.py"


def test_das_codefenster_meldet_die_geschriebene_datei(tmp_path: Path, qtbot) -> None:
    fenster = CodeFenster("x = 1\n", "Quelltext", vorschlag=tmp_path / "u_neu.py")
    qtbot.addWidget(fenster)
    gemeldet: list[Path] = []
    fenster.datei_geschrieben.connect(gemeldet.append)

    ergebnis = fenster.speichern_unter(tmp_path / "u_neu.py")

    assert ergebnis == tmp_path / "u_neu.py"
    assert ergebnis.read_text(encoding="utf-8") == "x = 1\n"
    assert gemeldet == [tmp_path / "u_neu.py"]


def test_eine_vorhandene_datei_wird_nicht_still_ueberschrieben(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, qtbot
) -> None:
    """Wer eine Klasse zweimal erzeugt, soll seine inzwischen
    ausformulierten Methodenrümpfe nicht verlieren."""
    from PySide6.QtWidgets import QMessageBox

    ziel = tmp_path / "u_konto.py"
    ziel.write_text("# meine Arbeit\n", encoding="utf-8")
    fenster = CodeFenster("x = 1\n", "Quelltext", vorschlag=ziel)
    qtbot.addWidget(fenster)
    gefragt: list[bool] = []

    def antwort(*_a, **_k):
        gefragt.append(True)
        return QMessageBox.StandardButton.Cancel

    monkeypatch.setattr(QMessageBox, "question", staticmethod(antwort))

    assert fenster.speichern_unter(ziel) is None
    assert gefragt, "Es wurde nicht nachgefragt"
    assert ziel.read_text(encoding="utf-8") == "# meine Arbeit\n"


# --------------------------------------- Das Hauptfenster nimmt sie an


def test_die_datei_steht_danach_im_explorer(tmp_path: Path, qtbot) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    projektdatei = _projekt_kopie(tmp_path)
    fenster.projekt_oeffnen(projektdatei)
    neu = projektdatei.parent / "u_konto_klassen.py"
    neu.write_text("class Konto:\n    pass\n", encoding="utf-8")

    fenster._erzeugte_datei_uebernehmen(neu)

    gezeigt = [
        fenster.explorer.units_gruppe.child(i).text(0)
        for i in range(fenster.explorer.units_gruppe.childCount())
    ]
    assert "u_konto_klassen.py" in gezeigt


def test_die_datei_ist_danach_als_reiter_offen(tmp_path: Path, qtbot) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    projektdatei = _projekt_kopie(tmp_path)
    fenster.projekt_oeffnen(projektdatei)
    neu = projektdatei.parent / "u_konto_klassen.py"
    neu.write_text("class Konto:\n    pass\n", encoding="utf-8")

    fenster._erzeugte_datei_uebernehmen(neu)

    titel = [fenster.editor_tabs.tabText(i) for i in range(fenster.editor_tabs.count())]
    assert "u_konto_klassen.py" in titel


def test_eine_datei_ausserhalb_des_projekts_kommt_nur_in_den_reiter(
    tmp_path: Path, qtbot
) -> None:
    """Der Explorer zeigt das Projekt und nicht irgendeinen Ordner."""
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    projektdatei = _projekt_kopie(tmp_path)
    fenster.projekt_oeffnen(projektdatei)
    draussen = tmp_path / "woanders.py"
    draussen.write_text("x = 1\n", encoding="utf-8")

    fenster._erzeugte_datei_uebernehmen(draussen)

    gezeigt = [
        fenster.explorer.units_gruppe.child(i).text(0)
        for i in range(fenster.explorer.units_gruppe.childCount())
    ]
    titel = [fenster.editor_tabs.tabText(i) for i in range(fenster.editor_tabs.count())]
    assert "woanders.py" not in gezeigt
    assert "woanders.py" in titel


def test_das_diagrammfenster_ist_angeschlossen(tmp_path: Path, qtbot) -> None:
    """Die Kette vom Diagramm-Editor bis zum Editor-Reiter."""
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    projektdatei = _projekt_kopie(tmp_path)
    fenster.projekt_oeffnen(projektdatei)
    diagramm = projektdatei.parent / "diagramme" / "konto_klassen.pdiag"

    diagrammfenster = fenster.diagramm_oeffnen(diagramm)
    neu = projektdatei.parent / "u_aus_dem_diagramm.py"
    neu.write_text("class Konto:\n    pass\n", encoding="utf-8")

    diagrammfenster.datei_geschrieben.emit(neu)

    titel = [fenster.editor_tabs.tabText(i) for i in range(fenster.editor_tabs.count())]
    assert "u_aus_dem_diagramm.py" in titel
