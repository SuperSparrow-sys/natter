"""Was aus `beispielprojekte/` und den anderen Datenordnern in die
Auslieferung kommt (Punkt 231).

Bis 0.3.6 kopierte der Bau alles aus dem Arbeitsbaum des
Baurechners, auch eine `konten.sqlite` aus einem Probelauf und
`__pycache__`. Die Tests legen dafür ein eigenes Git-Repository in
`tmp_path` an; das Repository von Natter bleibt unberührt.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tools import auslieferung_bauen as bau
from tools import ide_paketieren as paket


def _git(ordner: Path, *argumente: str) -> None:
    subprocess.run(
        [
            "git", "-c", "user.name=Probe", "-c", "user.email=probe@example.invalid",
            "-c", "commit.gpgsign=false", *argumente,
        ],
        cwd=ordner,
        check=True,
        capture_output=True,
    )


def _legen(ordner: Path, pfad: str, inhalt: bytes = b"x") -> None:
    ziel = ordner / pfad
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_bytes(inhalt)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Ein Repository mit einem eingecheckten Beispiel und daneben
    dem, was ein Probelauf hinterlässt."""
    wurzel = tmp_path / "repo"
    wurzel.mkdir()
    _git(wurzel, "init", "-q")
    _legen(wurzel, ".gitignore", b"__pycache__/\n*.sqlite\n")
    _legen(wurzel, "beispielprojekte/06_Konto/u_main.py", b"print(1)\n")
    _legen(wurzel, "beispielprojekte/06_Konto/daten/start.csv", b"a;b\n")
    _legen(wurzel, "design/tokens.json", b"{}")
    _git(wurzel, "add", "-A")
    _git(wurzel, "commit", "-q", "-m", "Probe")
    # Was ein Probelauf hinterlässt: ignoriert, aber vorhanden.
    _legen(wurzel, "beispielprojekte/06_Konto/konten.sqlite", b"SQLite")
    _legen(
        wurzel,
        "beispielprojekte/06_Konto/__pycache__/u_main.cpython-313.pyc",
        b"pyc",
    )
    return wurzel


def _dateien(ordner: Path) -> set[str]:
    return {
        p.relative_to(ordner).as_posix() for p in ordner.rglob("*") if p.is_file()
    }


def test_nur_eingecheckte_dateien_kommen_mit(repo: Path, tmp_path: Path) -> None:
    ziel = tmp_path / "ziel"

    paket.eingecheckt_kopieren(repo / "beispielprojekte", ziel, repo)

    assert _dateien(ziel) == {
        "06_Konto/u_main.py",
        "06_Konto/daten/start.csv",
    }


def test_ohne_git_fallen_datenbank_und_pycache_trotzdem_weg(
    tmp_path: Path,
) -> None:
    quelle = tmp_path / "ohne_git" / "beispielprojekte"
    _legen(quelle, "06_Konto/u_main.py")
    _legen(quelle, "06_Konto/konten.sqlite")
    _legen(quelle, "06_Konto/__pycache__/u_main.cpython-313.pyc")
    ziel = tmp_path / "ziel"

    paket.eingecheckt_kopieren(quelle, ziel, tmp_path / "ohne_git")

    assert _dateien(ziel) == {"06_Konto/u_main.py"}


def test_der_kopierschritt_laesst_sqlite_und_pycache_weg(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Der Schritt, den der Bau wirklich ausführt."""
    monkeypatch.setattr(paket, "_PROJEKT_WURZEL", repo)
    for name, ordner in (
        ("_DESIGN_ORDNER", "design"),
        ("_SCHEMAS_ORDNER", "design"),
        ("_TEMPLATES_ORDNER", "design"),
        ("_BEISPIEL_ORDNER", "beispielprojekte"),
    ):
        monkeypatch.setattr(paket, name, repo / ordner)
    _legen(repo, "docs/erste_schritte.md")
    _legen(repo, "docs/komponenten.md")
    _legen(repo, "docs/handbuch.md")
    monkeypatch.setattr(paket, "_DOCS_ORDNER", repo / "docs")
    python = tmp_path / "dist" / "python" / "python.exe"

    paket._datenordner_kopieren(python)

    beispiele = python.parent / "Lib" / "site-packages" / "beispielprojekte"
    inhalt = _dateien(beispiele)
    assert "06_Konto/u_main.py" in inhalt
    assert not [n for n in inhalt if n.endswith(".sqlite")]
    assert not [n for n in inhalt if "__pycache__" in n]


def test_schritt_1_meldet_ignorierte_dateien_in_den_datenordnern(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(bau, "_PROJEKT_WURZEL", repo)

    gefunden = bau._ignorierte_datendateien_melden()

    assert "beispielprojekte/06_Konto/konten.sqlite" in gefunden
    assert "ignorierte Datei" in capsys.readouterr().out
