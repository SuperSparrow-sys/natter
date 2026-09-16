"""Tests für die Paketverwaltung (Abschnitt 7.2, 18). Siehe
docs/arbeitspakete/M7.md, Schritt 3. `subprocess.run` wird gemockt -
echte `pip`-Aufrufe (Netzwerk/Installation) gehören nicht in die
automatisierte Testsuite.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from ide.env import PaketFehler, installierte_pakete, paket_installieren, paketliste_exportieren


def _ergebnis(
    *, stdout: str = "", stderr: str = "", returncode: int = 0
) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


def test_installierte_pakete_parst_echte_pip_list_json_ausgabe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pip_ausgabe = '[{"name": "pytest", "version": "8.0.0"}, {"name": "ruff", "version": "0.8.1"}]'
    monkeypatch.setattr(
        "ide.env.pakete.subprocess.run", lambda *a, **k: _ergebnis(stdout=pip_ausgabe)
    )

    pakete = installierte_pakete()

    assert pakete[0].name == "pytest"
    assert pakete[0].version == "8.0.0"
    assert pakete[1].name == "ruff"


def test_paket_installieren_ruft_pip_install_mit_dem_richtigen_namen_auf(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    aufgerufen = []

    def fake_run(befehl, **kwargs):
        aufgerufen.append(befehl)
        return _ergebnis(stdout="Successfully installed requests-2.31.0")

    monkeypatch.setattr("ide.env.pakete.subprocess.run", fake_run)

    ausgabe = paket_installieren("requests")

    assert aufgerufen[0][-2:] == ["install", "requests"]
    assert "Successfully installed" in ausgabe


def test_paket_installieren_bei_fehler_loest_paketfehler_aus(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "ide.env.pakete.subprocess.run",
        lambda *a, **k: _ergebnis(
            returncode=1, stderr="ERROR: No matching distribution found for nicht_vorhanden_xyz"
        ),
    )

    with pytest.raises(PaketFehler, match="No matching distribution"):
        paket_installieren("nicht_vorhanden_xyz")


def test_paketliste_exportieren_schreibt_pip_freeze_ausgabe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pip_ausgabe = "pandas==2.2.0\nnumpy==1.26.0\n"
    monkeypatch.setattr(
        "ide.env.pakete.subprocess.run", lambda *a, **k: _ergebnis(stdout=pip_ausgabe)
    )
    ziel = tmp_path / "requirements.txt"

    paketliste_exportieren(ziel)

    assert ziel.read_text(encoding="utf-8") == pip_ausgabe
