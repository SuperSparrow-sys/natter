"""Wo „Projekt öffnen …“ und „Öffnen …“ beginnen (Punkt 408).

Ohne Startordner zeigt der Dialog den Arbeitsordner des Prozesses.
Den setzt der Startmenü-Eintrag auf den Programmordner von Natter, und
die installierte Fassung 0.4.0 zeigte beim ersten „Projekt öffnen …“
die Ordner `Lizenzen`, `python` und `starter` statt der Projekte.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from PySide6.QtWidgets import QFileDialog

import ide.pfade
from ide.project import projekt_erzeugen


@pytest.mark.parametrize(
    ("dialog", "gewaehlt"),
    [
        ("_projekt_oeffnen_dialog", "Rechnen/Rechnen.natter"),
        ("_datei_oeffnen_dialog", "notiz.txt"),
    ],
)
def test_oeffnen_dialog_beginnt_bei_den_projekten(
    hauptfenster,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    dialog: str,
    gewaehlt: str,
):
    # Der Arbeitsordner steht wie beim Start aus dem Startmenü im
    # Programmordner. Ein Dialog ohne Startordner landete dort.
    programmordner = tmp_path / "Programs" / "Natter"
    programmordner.mkdir(parents=True)
    monkeypatch.chdir(programmordner)
    natter = ide.pfade.natter_ordner()
    natter.mkdir(parents=True)
    ablage = tmp_path / "Ablage"
    projekt = projekt_erzeugen("console", ablage / "Rechnen", "Rechnen")
    (ablage / "notiz.txt").write_text("Notiz", encoding="utf-8")

    gefragt: list[str] = []
    antwort = {"pfad": ""}

    def dialog_ersatz(_eltern, _titel, ordner="", *_a, **_k):
        gefragt.append(ordner)
        return antwort["pfad"], ""

    monkeypatch.setattr(QFileDialog, "getOpenFileName", dialog_ersatz)
    oeffnen = getattr(hauptfenster, dialog)

    # Ohne Projekt und ohne gemerkten Ordner: `natter_ordner()`.
    oeffnen()
    assert gefragt[-1] and os.path.samefile(gefragt[-1], natter)

    # Mit offenem Projekt: dessen Ordner.
    assert hauptfenster.projekt_oeffnen(projekt.ordner / "Rechnen.natter")
    oeffnen()
    assert os.path.samefile(gefragt[-1], projekt.ordner)
    assert hauptfenster.projekt_schliessen()

    # Nach einer Wahl im Dialog und ohne Projekt: dort, wo gewählt
    # wurde - beim Projekt der Ordner, in dem die Projekte liegen.
    antwort["pfad"] = str(ablage / gewaehlt)
    oeffnen()
    antwort["pfad"] = ""
    if hauptfenster.projekt is not None:
        assert hauptfenster.projekt_schliessen()
    oeffnen()
    assert os.path.samefile(gefragt[-1], ablage)
