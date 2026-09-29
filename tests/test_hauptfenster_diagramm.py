"""Tests für die Diagramm-Verdrahtung im Hauptfenster (M9, Schritt 1):
Explorer-Gruppe „Diagramme“, Doppelklick öffnet ein eigenes Fenster,
„Datei → Neues Diagramm …“ legt eine `.pdiag` an. Headless.

Projekte werden in `tmp_path` erzeugt statt aus `beispielprojekte/`
benutzt - hier wird tatsächlich geschrieben (AGENTS.md).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ide.diagramm import DiagrammFenster, diagramm_erzeugen
from ide.project import projekt_erzeugen
from ide.shell.explorer import PFAD_ROLLE


def _projekt_mit_diagramm(tmp_path: Path) -> tuple[Path, Path]:
    projekt = projekt_erzeugen("gui", tmp_path / "Testprojekt", "Testprojekt")
    diagramm_pfad = projekt.diagramm_ordner / "ampel_klassen.pdiag"
    diagramm_pfad.parent.mkdir(parents=True, exist_ok=True)
    diagramm_erzeugen("class", diagramm_pfad, "ampel_klassen")
    return projekt.ordner, diagramm_pfad


def test_explorer_zeigt_diagramme_in_eigener_gruppe(tmp_path: Path, hauptfenster_bauen) -> None:
    projekt_ordner, _ = _projekt_mit_diagramm(tmp_path)
    fenster = hauptfenster_bauen()

    fenster.projekt_oeffnen(projekt_ordner)

    gruppe = fenster.explorer.diagramme_gruppe
    assert gruppe.text(0) == "Diagramme"
    assert [gruppe.child(i).text(0) for i in range(gruppe.childCount())] == ["ampel_klassen"]


def test_projekt_ohne_diagramme_zeigt_leere_gruppe(tmp_path: Path, hauptfenster_bauen) -> None:
    projekt = projekt_erzeugen("gui", tmp_path / "Leer", "Leer")
    fenster = hauptfenster_bauen()

    fenster.projekt_oeffnen(projekt.ordner)

    assert fenster.explorer.diagramme_gruppe.childCount() == 0


def test_doppelklick_auf_ein_diagramm_oeffnet_ein_eigenes_fenster(
    tmp_path: Path, hauptfenster_bauen
) -> None:
    projekt_ordner, diagramm_pfad = _projekt_mit_diagramm(tmp_path)
    fenster = hauptfenster_bauen()
    fenster.projekt_oeffnen(projekt_ordner)
    eintrag = fenster.explorer.diagramme_gruppe.child(0)

    fenster._bei_explorer_doppelklick(eintrag, 0)

    diagramm_fenster = fenster._offene_diagramme[str(diagramm_pfad)]
    assert isinstance(diagramm_fenster, DiagrammFenster)
    # kein Tab im Hauptfenster - eigenes Fenster (Abschnitt 13.1)
    assert fenster.editor_tabs.count() == 0
    assert eintrag.data(0, PFAD_ROLLE) == str(diagramm_pfad)


def test_zweites_oeffnen_holt_dasselbe_fenster_nach_vorne(
    tmp_path: Path, hauptfenster_bauen
) -> None:
    _, diagramm_pfad = _projekt_mit_diagramm(tmp_path)
    fenster = hauptfenster_bauen()

    erstes = fenster.diagramm_oeffnen(diagramm_pfad)
    zweites = fenster.diagramm_oeffnen(diagramm_pfad)

    assert erstes is zweites
    assert len(fenster._offene_diagramme) == 1


def test_neues_diagramm_legt_datei_an_und_oeffnet_sie(
    tmp_path: Path, monkeypatch, hauptfenster_bauen
) -> None:
    from PySide6.QtWidgets import QInputDialog

    projekt = projekt_erzeugen("gui", tmp_path / "Neu", "Neu")
    fenster = hauptfenster_bauen()
    fenster.projekt_oeffnen(projekt.ordner)

    monkeypatch.setattr(QInputDialog, "getItem", lambda *a, **k: ("Struktogramm", True))
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("ampel_zeichnen", True))

    fenster._neues_diagramm_aktion()

    erwartet = projekt.diagramm_ordner / "ampel_zeichnen.pdiag"
    assert erwartet.exists()
    assert str(erwartet) in fenster._offene_diagramme
    assert fenster._offene_diagramme[str(erwartet)].diagramm.typ == "struktogramm"
    # erscheint sofort im Explorer, ohne das Projekt neu zu öffnen
    gruppe = fenster.explorer.diagramme_gruppe
    assert [gruppe.child(i).text(0) for i in range(gruppe.childCount())] == ["ampel_zeichnen"]


def test_neues_diagramm_ohne_projekt_zeigt_hinweis(hauptfenster) -> None:

    hauptfenster._neues_diagramm_aktion()

    meldung = hauptfenster.statusBar().currentMessage()
    assert meldung.startswith("Kein Projekt offen.")
    assert "Projekt → Projekt öffnen …" in meldung


def test_neues_diagramm_mit_vorhandenem_namen_zeigt_hinweis(
    tmp_path: Path, monkeypatch, hauptfenster_bauen
) -> None:
    from PySide6.QtWidgets import QInputDialog

    projekt_ordner, _ = _projekt_mit_diagramm(tmp_path)
    fenster = hauptfenster_bauen()
    fenster.projekt_oeffnen(projekt_ordner)

    monkeypatch.setattr(QInputDialog, "getItem", lambda *a, **k: ("Klassendiagramm", True))
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("ampel_klassen", True))

    fenster._neues_diagramm_aktion()

    assert "gibt es schon" in fenster.statusBar().currentMessage()


@pytest.mark.parametrize(
    "name", ["..\\..\\ausserhalb", "ampel:neu", "wozu?"]
)
def test_neues_diagramm_lehnt_einen_unbrauchbaren_namen_ab(
    tmp_path: Path, monkeypatch, hauptfenster_bauen, name: str
) -> None:
    # Punkt 232: „Umbenennen …“ prüfte diese Fälle schon, das Anlegen
    # nicht.
    from PySide6.QtWidgets import QInputDialog, QMessageBox

    projekt = projekt_erzeugen("gui", tmp_path / "Neu", "Neu")
    fenster = hauptfenster_bauen()
    fenster.projekt_oeffnen(projekt.ordner)
    meldungen: list[str] = []
    monkeypatch.setattr(
        QMessageBox, "warning",
        staticmethod(lambda _eltern, _titel, text: meldungen.append(text)),
    )
    monkeypatch.setattr(QInputDialog, "getItem", lambda *a, **k: ("Struktogramm", True))
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: (name, True))
    vorher = set(tmp_path.rglob("*.pdiag"))

    fenster._neues_diagramm_aktion()

    assert set(tmp_path.rglob("*.pdiag")) == vorher
    assert fenster._offene_diagramme == {}
    assert len(meldungen) == 1
    assert "taugt nicht als Dateiname" in meldungen[0]


def test_datei_menue_hat_den_eintrag_neues_diagramm(hauptfenster) -> None:

    titel = {aktion.text() for aktion in hauptfenster.menue("Datei").actions()}

    assert "Neues Diagramm …" in titel
