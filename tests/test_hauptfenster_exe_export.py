"""Tests für „Projekt → Als Exe exportieren …“ (Abschnitt 16, 17;
M8 Schritt 4). Nutzt ein Double für `exe_exportieren`, damit der Test
nicht 15-40 Sekunden auf einen echten PyInstaller-Bau wartet (siehe
`tests/test_exporter.py` für die Export-Logik selbst und
`docs/arbeitspakete/M8.md` für die einmalige echte Abnahme).
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from ide.export.exporter import ExportErgebnis
from ide.shell.hauptfenster import HauptFenster


def _projekt_kopie(tmp_path: Path) -> Path:
    original = Path(__file__).resolve().parent.parent / "beispielprojekte" / "Ampel"
    ziel = tmp_path / "Ampel"
    shutil.copytree(original, ziel)
    return ziel


def test_ohne_offenes_projekt_zeigt_hinweis() -> None:
    fenster = HauptFenster()
    fenster._als_exe_exportieren_aktion()
    assert fenster.statusBar().currentMessage() == "Kein Projekt offen."


def test_erfolgreicher_export_meldet_den_ausgabepfad(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fenster = HauptFenster()
    fenster.projekt_oeffnen(_projekt_kopie(tmp_path) / "ampel.natter")
    ausgabe = tmp_path / "dist" / "Ampel"
    ausgabe.mkdir(parents=True)

    monkeypatch.setattr(
        "ide.shell.hauptfenster.exe_exportieren",
        lambda projekt: ExportErgebnis(True, ausgabe, "ok"),
    )
    monkeypatch.setattr("ide.shell.hauptfenster.sys.platform", "nicht-win32")

    fenster._als_exe_exportieren_aktion()

    assert str(ausgabe) in fenster.statusBar().currentMessage()


def test_fehlgeschlagener_export_zeigt_protokoll_in_meldungen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fenster = HauptFenster()
    fenster.projekt_oeffnen(_projekt_kopie(tmp_path) / "ampel.natter")

    monkeypatch.setattr(
        "ide.shell.hauptfenster.exe_exportieren",
        lambda projekt: ExportErgebnis(False, None, "PyInstaller-Fehler: xyz"),
    )

    fenster._als_exe_exportieren_aktion()

    texte = [fenster.meldungen_liste.item(i).text() for i in range(fenster.meldungen_liste.count())]
    assert any("PyInstaller-Fehler" in t for t in texte)
    assert "fehlgeschlagen" in fenster.statusBar().currentMessage()
