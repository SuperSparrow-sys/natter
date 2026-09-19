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
    original = Path(__file__).resolve().parent.parent / "beispielprojekte" / "04_CookieKlicker"
    ziel = tmp_path / "04_CookieKlicker"
    shutil.copytree(original, ziel)
    return ziel


def test_ohne_offenes_projekt_zeigt_hinweis() -> None:
    fenster = HauptFenster()
    fenster._als_exe_exportieren_aktion()
    meldung = fenster.statusBar().currentMessage()
    assert meldung.startswith("Kein Projekt offen.")
    assert "Projekt → Öffnen" in meldung


def test_erfolgreicher_export_meldet_den_ausgabepfad(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fenster = HauptFenster()
    fenster.projekt_oeffnen(_projekt_kopie(tmp_path) / "04_CookieKlicker.natter")
    ausgabe = tmp_path / "dist" / "04_CookieKlicker.exe"
    ausgabe.parent.mkdir(parents=True)
    ausgabe.write_bytes(b"MZ")

    monkeypatch.setattr(
        "ide.shell.hauptfenster.exe_exportieren",
        lambda projekt, **_: ExportErgebnis(True, ausgabe, "ok"),
    )
    monkeypatch.setattr("ide.shell.hauptfenster.sys.platform", "nicht-win32")

    fenster._als_exe_exportieren_aktion()

    assert str(ausgabe) in fenster.statusBar().currentMessage()


def test_fehlgeschlagener_export_zeigt_protokoll_in_meldungen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fenster = HauptFenster()
    fenster.projekt_oeffnen(_projekt_kopie(tmp_path) / "04_CookieKlicker.natter")

    monkeypatch.setattr(
        "ide.shell.hauptfenster.exe_exportieren",
        lambda projekt, **_: ExportErgebnis(False, None, "PyInstaller-Fehler: xyz"),
    )

    fenster._als_exe_exportieren_aktion()

    texte = [fenster.meldungen_liste.item(i).text() for i in range(fenster.meldungen_liste.count())]
    assert any("PyInstaller-Fehler" in t for t in texte)
    assert "fehlgeschlagen" in fenster.statusBar().currentMessage()


def test_ein_ladebalken_laeuft_in_der_untersten_zeile_mit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Nutzer-Vorgabe September 2026: „wenn ich ein Programm als Exe
    exportiere soll unten ein Ladebalken sein in der untersten Zeile".

    Ein Export dauert eine halbe bis eine Minute, und die Oberfläche
    steht dabei still - ohne Balken sieht das nach einem Absturz aus.
    """
    fenster = HauptFenster()
    fenster.projekt_oeffnen(_projekt_kopie(tmp_path) / "04_CookieKlicker.natter")
    ausgabe = tmp_path / "dist" / "04_CookieKlicker.exe"
    ausgabe.parent.mkdir(parents=True)
    ausgabe.write_bytes(b"MZ")

    staende: list[int] = []

    def gefaelschter_export(projekt, fortschritt=None, **_):
        # So ruft der echte Exporter zurück, während PyInstaller läuft.
        for prozent, text in ((5, "gestartet"), (55, "gesucht"), (100, "fertig")):
            fortschritt(prozent, text)
            staende.append(fenster._fortschritt_balken.value())
        return ExportErgebnis(True, ausgabe, "ok")

    monkeypatch.setattr("ide.shell.hauptfenster.exe_exportieren", gefaelschter_export)
    monkeypatch.setattr("ide.shell.hauptfenster.sys.platform", "nicht-win32")

    fenster._als_exe_exportieren_aktion()

    assert staende == [5, 55, 100]
    # Danach verschwindet er wieder: ein dauerhaft sichtbarer Balken in
    # der Statuszeile sieht nach einem hängenden Programm aus.
    assert fenster._fortschritt_balken.isHidden()
