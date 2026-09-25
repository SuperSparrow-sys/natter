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
from ide.shell.hauptfenster import HauptFenster


def test_pakete_anzeigen_zeigt_installierte_pakete(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "ide.shell.hauptfenster.installierte_pakete",
        lambda: [Paket("pytest", "8.0.0"), Paket("ruff", "0.8.1")],
    )
    fenster = HauptFenster()
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
 hintergrund_abwarten
) -> None:
    aufgerufen = []
    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("requests", True)))
    monkeypatch.setattr(
        "ide.shell.hauptfenster.paket_installieren", lambda name: aufgerufen.append(name)
    )
    fenster = HauptFenster()

    fenster._paket_installieren_aktion()
    hintergrund_abwarten(fenster)

    assert aufgerufen == ["requests"]
    assert fenster.statusBar().currentMessage() == "requests installiert."


def test_paket_installieren_abgebrochen_installiert_nichts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    aufgerufen = []
    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("", False)))
    monkeypatch.setattr(
        "ide.shell.hauptfenster.paket_installieren", lambda name: aufgerufen.append(name)
    )
    fenster = HauptFenster()

    fenster._paket_installieren_aktion()

    assert aufgerufen == []


def test_paket_installieren_bei_fehler_zeigt_meldung(
    monkeypatch: pytest.MonkeyPatch,
    hintergrund_abwarten,
) -> None:
    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("kaputt", True)))

    def fake_installieren(name: str) -> str:
        raise PaketFehler("No matching distribution found for kaputt")

    monkeypatch.setattr("ide.shell.hauptfenster.paket_installieren", fake_installieren)
    fenster = HauptFenster()

    fenster._paket_installieren_aktion()
    hintergrund_abwarten(fenster)

    assert "fehlgeschlagen" in fenster.statusBar().currentMessage()


def test_paketliste_exportieren_schreibt_an_den_gewaehlten_pfad(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
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
    fenster = HauptFenster()

    fenster._paketliste_exportieren_aktion()

    assert aufgerufen == [str(ziel)]
    assert str(ziel) in fenster.statusBar().currentMessage()
