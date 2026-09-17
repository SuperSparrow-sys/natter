"""Tests für den PyInstaller-Export (Abschnitt 16, 17; M8 Schritt 4).
Nutzt ein `subprocess.run`-Double statt eines echten PyInstaller-Baus
(dauert real 15-40s, siehe `docs/arbeitspakete/M8.md` für den einmaligen
echten Bau/Lauf zur Abnahme). Prüft die Kommandozusammenstellung, den
Umgang mit `export`-Einstellungen aus der `.natter`-Datei und das aus
Sicht des Aufrufers sichtbare Ergebnis bei Erfolg/Fehler.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from ide.export import exe_exportieren
from ide.project import Projekt


def _projekt(tmp_path: Path, export_optionen: dict | None = None) -> Projekt:
    ordner = tmp_path / "MeinProjekt"
    ordner.mkdir()
    (ordner / "main.py").write_text("print('hallo')\n", encoding="utf-8")
    daten = {
        "format": "natter-project/1",
        "name": "MeinProjekt",
        "type": "console",
        "main": "main.py",
    }
    if export_optionen is not None:
        daten["export"] = export_optionen
    return Projekt(ordner=ordner, daten=daten)


class _ErgebnisAttrappe:
    def __init__(self, returncode: int = 0, stdout: str = "ok\n", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_bindet_den_design_ordner_ein_damit_pcl_theme_tokens_findet(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ohne `--add-data` stürzt jede exportierte Exe beim Start ab, weil
    `pcl.theme` `design/tokens.json` zur Laufzeit lädt statt es zu
    importieren (real mit einem echten PyInstaller-Bau gefunden, siehe
    `docs/arbeitspakete/M8.md`)."""
    projekt = _projekt(tmp_path)
    aufrufe = []

    def gefaelschtes_run(befehl, **kwargs):
        aufrufe.append(befehl)
        (projekt.ordner / "dist" / "MeinProjekt").mkdir(parents=True)
        return _ErgebnisAttrappe()

    monkeypatch.setattr("ide.export.exporter.subprocess.run", gefaelschtes_run)

    exe_exportieren(projekt)

    befehl = aufrufe[0]
    assert "--add-data" in befehl
    add_data_wert = befehl[befehl.index("--add-data") + 1]
    assert add_data_wert.endswith("design")
    assert "tokens.json" not in add_data_wert  # der ganze Ordner, nicht nur die Datei


def test_baut_ordner_variante_ohne_windowed_fuer_konsolenprojekt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    projekt = _projekt(tmp_path)
    aufrufe = []

    def gefaelschtes_run(befehl, **kwargs):
        aufrufe.append(befehl)
        (projekt.ordner / "dist" / "MeinProjekt").mkdir(parents=True)
        return _ErgebnisAttrappe()

    monkeypatch.setattr(subprocess, "run", gefaelschtes_run)

    ergebnis = exe_exportieren(projekt)

    assert ergebnis.erfolgreich is True
    befehl = aufrufe[0]
    assert "--windowed" not in befehl
    assert "MeinProjekt" in befehl
    assert str(projekt.haupt_datei) in befehl


def test_gui_projekt_baut_mit_windowed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    projekt = _projekt(tmp_path, {"target": "folder"})
    projekt.daten["type"] = "gui"
    aufrufe = []

    def gefaelschtes_run(befehl, **kwargs):
        aufrufe.append(befehl)
        (projekt.ordner / "dist" / "MeinProjekt").mkdir(parents=True)
        return _ErgebnisAttrappe()

    monkeypatch.setattr("ide.export.exporter.subprocess.run", gefaelschtes_run)

    exe_exportieren(projekt)

    assert "--windowed" in aufrufe[0]


def test_fehlgeschlagener_build_liefert_kein_ausgabeverzeichnis(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    projekt = _projekt(tmp_path)

    monkeypatch.setattr(
        "ide.export.exporter.subprocess.run",
        lambda *a, **k: _ErgebnisAttrappe(returncode=1, stdout="", stderr="Fehler: xyz"),
    )

    ergebnis = exe_exportieren(projekt)

    assert ergebnis.erfolgreich is False
    assert ergebnis.ausgabe_pfad is None
    assert "Fehler" in ergebnis.protokoll


def test_target_zip_erzeugt_eine_zip_datei_statt_eines_ordners(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    projekt = _projekt(tmp_path, {"target": "zip"})

    def gefaelschtes_run(befehl, **kwargs):
        ausgabe = projekt.ordner / "dist" / "MeinProjekt"
        ausgabe.mkdir(parents=True)
        (ausgabe / "MeinProjekt.exe").write_text("", encoding="utf-8")
        return _ErgebnisAttrappe()

    monkeypatch.setattr("ide.export.exporter.subprocess.run", gefaelschtes_run)

    ergebnis = exe_exportieren(projekt)

    assert ergebnis.erfolgreich is True
    assert ergebnis.ausgabe_pfad.suffix == ".zip"
    assert ergebnis.ausgabe_pfad.exists()


def test_target_folder_laesst_ordner_wie_er_ist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    projekt = _projekt(tmp_path, {"target": "folder"})

    def gefaelschtes_run(befehl, **kwargs):
        ausgabe = projekt.ordner / "dist" / "MeinProjekt"
        ausgabe.mkdir(parents=True)
        (ausgabe / "MeinProjekt.exe").write_text("", encoding="utf-8")
        return _ErgebnisAttrappe()

    monkeypatch.setattr("ide.export.exporter.subprocess.run", gefaelschtes_run)

    ergebnis = exe_exportieren(projekt)

    assert ergebnis.erfolgreich is True
    assert ergebnis.ausgabe_pfad.is_dir()
    assert (ergebnis.ausgabe_pfad / "MeinProjekt.exe").exists()


def test_include_data_dir_kopiert_den_daten_ordner_mit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    projekt = _projekt(tmp_path, {"target": "folder", "include_data_dir": True})
    (projekt.ordner / "daten").mkdir()
    (projekt.ordner / "daten" / "werte.csv").write_text("a,b\n1,2\n", encoding="utf-8")

    def gefaelschtes_run(befehl, **kwargs):
        (projekt.ordner / "dist" / "MeinProjekt").mkdir(parents=True)
        return _ErgebnisAttrappe()

    monkeypatch.setattr("ide.export.exporter.subprocess.run", gefaelschtes_run)

    ergebnis = exe_exportieren(projekt)

    assert (ergebnis.ausgabe_pfad / "daten" / "werte.csv").exists()


def test_icon_wird_als_pyinstaller_option_uebergeben(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    projekt = _projekt(tmp_path, {"target": "folder", "icon": "symbol.ico"})
    aufrufe = []

    def gefaelschtes_run(befehl, **kwargs):
        aufrufe.append(befehl)
        (projekt.ordner / "dist" / "MeinProjekt").mkdir(parents=True)
        return _ErgebnisAttrappe()

    monkeypatch.setattr("ide.export.exporter.subprocess.run", gefaelschtes_run)

    exe_exportieren(projekt)

    befehl = aufrufe[0]
    assert "--icon" in befehl
    assert str(projekt.ordner / "symbol.ico") in befehl


def test_zwischenstaende_werden_nach_dem_bau_entfernt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    projekt = _projekt(tmp_path, {"target": "folder"})

    def gefaelschtes_run(befehl, **kwargs):
        (projekt.ordner / "dist" / "MeinProjekt").mkdir(parents=True)
        (projekt.ordner / "_pyinstaller_build").mkdir()
        (projekt.ordner / "_pyinstaller_spec").mkdir()
        return _ErgebnisAttrappe()

    monkeypatch.setattr("ide.export.exporter.subprocess.run", gefaelschtes_run)

    exe_exportieren(projekt)

    assert not (projekt.ordner / "_pyinstaller_build").exists()
    assert not (projekt.ordner / "_pyinstaller_spec").exists()
