"""Update-Verhalten des Installers (Punkte 26, 28, 30).

Den Installer selbst baut der Auslieferungsbau; hier wird geprüft, was
sich ohne Bau prüfen lässt: das Hilfsskript für nachinstallierte
Pakete, die Einstellungen in tools/natter.iss und dass die
unpersönlichen Texte jede Anrede aus German.isl abdecken.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

from tools.installer_pakete_merken import nachinstallierte

WURZEL = Path(__file__).resolve().parent.parent
ISS = WURZEL / "tools" / "natter.iss"
TEXTE = WURZEL / "tools" / "installer_texte.isl"
GERMAN_ISL = Path(r"C:\Program Files (x86)\Inno Setup 6\Languages\German.isl")


def _paket(site: Path, name: str) -> None:
    info = site / f"{name}-1.0.dist-info"
    info.mkdir(parents=True)
    (info / "METADATA").write_text(
        f"Metadata-Version: 2.1\nName: {name}\nVersion: 1.0\n", encoding="utf-8"
    )


@pytest.fixture
def alte_python(tmp_path: Path) -> Path:
    python = tmp_path / "python"
    site = python / "Lib" / "site-packages"
    for name in ("numpy", "PySide6_Essentials", "natter", "pip", "cowsay", "Requests"):
        _paket(site, name)
    (python / "requirements-auslieferung.txt").write_text(
        "# erzeugt von uv\n"
        "numpy==2.5.3 \\\n    --hash=sha256:abc\n"
        "pyside6-essentials==6.11.2 ; sys_platform == 'win32'\n",
        encoding="utf-8",
    )
    return python


def test_nachinstallierte_pakete_werden_erkannt(alte_python: Path) -> None:
    assert nachinstallierte(alte_python) == ["cowsay", "Requests"]


def test_ohne_liste_der_mitgelieferten_wird_nichts_geraten(alte_python: Path) -> None:
    (alte_python / "requirements-auslieferung.txt").unlink()

    assert nachinstallierte(alte_python) is None


def test_das_skript_schreibt_die_liste(alte_python: Path, tmp_path: Path) -> None:
    ziel = tmp_path / "appdata" / "pakete_vor_update.txt"
    skript = WURZEL / "tools" / "installer_pakete_merken.py"

    subprocess.run([sys.executable, str(skript), str(ziel), str(alte_python)],
                   check=True, timeout=60)

    assert ziel.read_text(encoding="utf-8").split() == ["cowsay", "Requests"]


def test_das_setup_ersetzt_die_mitgelieferte_python_vollstaendig() -> None:
    """Punkt 28: nur Natters eigene Ordner zu leeren, ließ die
    Qt-Module unter GPL und eine alte natter-dist-info liegen."""
    text = ISS.read_text(encoding="utf-8-sig")
    abschnitt = text.split("[InstallDelete]")[1].split("\n[")[0]

    assert re.search(r'Type: filesandordirs; Name: "\{app\}\\python"\s*$', abschnitt, re.M)


def test_das_setup_erkennt_ein_update() -> None:
    """Punkt 26: vorhandene Fassung nennen, Ordnerseiten überspringen,
    Pakete merken und wieder installieren, keine ältere über eine
    neuere."""
    text = ISS.read_text(encoding="utf-8-sig")

    assert "DisableDirPage=auto" in text
    assert "DisableProgramGroupPage=auto" in text
    assert "CloseApplications=yes" in text
    assert "installer_pakete_merken.py" in text
    assert "DisplayVersion" in text
    assert "wird auf" in text and "aktualisiert" in text


def test_nur_deutsch_ohne_sprachauswahl() -> None:
    """Punkt 30: Natter ist deutsch; die Frage nach der Setup-Sprache
    entfällt."""
    text = ISS.read_text(encoding="utf-8-sig")
    sprachen = text.split("[Languages]")[1].split("\n[")[0]
    eintraege = [z for z in sprachen.splitlines() if z.startswith("Name:")]

    assert len(eintraege) == 1
    assert "installer_texte.isl" in eintraege[0]


@pytest.mark.skipif(not GERMAN_ISL.exists(), reason="Inno Setup nicht installiert")
def test_jede_anrede_aus_german_isl_ist_ueberschrieben() -> None:
    """Punkt 30: 64 Meldungen in German.isl sprechen mit „Sie“ oder
    „Ihr“ an. Jede davon braucht eine Fassung in installer_texte.isl,
    und die darf selbst niemanden ansprechen."""
    anrede = re.compile(r"\b(Sie|Ihr|Ihre|Ihrem|Ihren|Ihrer|Ihnen)\b")

    def meldungen(pfad: Path) -> dict[str, str]:
        ergebnis = {}
        for zeile in pfad.read_text(encoding="utf-8-sig").splitlines():
            if "=" in zeile and not zeile.startswith((";", "[")):
                name, wert = zeile.split("=", 1)
                ergebnis[name.strip()] = wert
        return ergebnis

    original = meldungen(GERMAN_ISL)
    eigene = meldungen(TEXTE)
    mit_anrede = {n for n, w in original.items() if anrede.search(w)}

    assert mit_anrede, "German.isl nicht gelesen"
    assert sorted(mit_anrede - set(eigene)) == []
    assert {n: w for n, w in eigene.items() if anrede.search(w)} == {}
