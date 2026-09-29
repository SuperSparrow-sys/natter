"""Tests für die IDE-Verdrahtung der Paketverwaltung (Abschnitt 7.2).
Siehe Arbeitspaket M7, Schritt 3. `pip` selbst ist bereits in
tests/test_env_pakete.py gemockt getestet - hier nur die Verdrahtung.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QInputDialog, QTableWidget

from ide.env import Paket, PaketFehler


def test_pakete_anzeigen_zeigt_installierte_pakete(
    monkeypatch: pytest.MonkeyPatch, hauptfenster_bauen
) -> None:
    monkeypatch.setattr(
        "ide.shell.hauptfenster.installierte_pakete",
        lambda: [Paket("pytest", "8.0.0"), Paket("ruff", "0.8.1")],
    )
    fenster = hauptfenster_bauen()
    inhalt: dict[str, object] = {}

    def dialog_lesen() -> None:
        dialog = QApplication.activeModalWidget()
        tabelle = dialog.findChild(QTableWidget)
        inhalt["zeilen"] = tabelle.rowCount()
        inhalt["erste_zelle"] = tabelle.item(0, 0).text()
        dialog.close()

    QTimer.singleShot(0, dialog_lesen)
    fenster._pakete_anzeigen_aktion()

    assert inhalt["zeilen"] == 2
    assert inhalt["erste_zelle"] == "pytest"


def test_paket_installieren_ruft_installation_mit_eingegebenem_namen_auf(
    monkeypatch: pytest.MonkeyPatch,
 hintergrund_abwarten, hauptfenster_bauen
) -> None:
    aufgerufen = []
    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("requests", True)))
    monkeypatch.setattr(
        "ide.shell.hauptfenster.paket_installieren", lambda name: aufgerufen.append(name)
    )
    fenster = hauptfenster_bauen()

    fenster._paket_installieren_aktion()
    hintergrund_abwarten(fenster)

    assert aufgerufen == ["requests"]
    assert fenster.statusBar().currentMessage() == "requests installiert."


def test_paket_installieren_abgebrochen_installiert_nichts(
    monkeypatch: pytest.MonkeyPatch, hauptfenster_bauen,
) -> None:
    aufgerufen = []
    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("", False)))
    monkeypatch.setattr(
        "ide.shell.hauptfenster.paket_installieren", lambda name: aufgerufen.append(name)
    )
    fenster = hauptfenster_bauen()

    fenster._paket_installieren_aktion()

    assert aufgerufen == []


def test_paket_installieren_bei_fehler_zeigt_meldung(
    monkeypatch: pytest.MonkeyPatch,
    hintergrund_abwarten, hauptfenster_bauen,
) -> None:
    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("kaputt", True)))

    def fake_installieren(name: str) -> str:
        raise PaketFehler(
            "Keine Verbindung zum Paketverzeichnis.",
            "ERROR: No matching distribution found for kaputt",
        )

    monkeypatch.setattr("ide.shell.hauptfenster.paket_installieren", fake_installieren)
    fenster = hauptfenster_bauen()

    fenster._paket_installieren_aktion()
    hintergrund_abwarten(fenster)

    status = fenster.statusBar().currentMessage()
    assert "fehlgeschlagen" in status
    assert "Keine Verbindung zum Paketverzeichnis" in status
    # Die Ausgabe von pip steht nur im Panel „Meldungen“ (Punkt 424).
    assert "No matching distribution" not in status
    assert "PaketFehler" not in status
    eintraege = [
        fenster.meldungen_liste.item(i).text()
        for i in range(fenster.meldungen_liste.count())
    ]
    assert "ERROR: No matching distribution found for kaputt" in eintraege


def test_paketliste_exportieren_schreibt_an_den_gewaehlten_pfad(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hauptfenster_bauen
) -> None:
    ziel = tmp_path / "requirements.txt"
    monkeypatch.setattr(
        "ide.shell.hauptfenster.QFileDialog.getSaveFileName",
        staticmethod(lambda *a, **k: (str(ziel), "Text (*.txt)")),
    )
    aufgerufen = []
    monkeypatch.setattr(
        "ide.shell.hauptfenster.paketliste_exportieren", lambda pfad: aufgerufen.append(pfad)
    )
    fenster = hauptfenster_bauen()

    fenster._paketliste_exportieren_aktion()

    assert aufgerufen == [str(ziel)]
    assert str(ziel) in fenster.statusBar().currentMessage()
