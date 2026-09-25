"""Eine gebaute Fassung kommt als GitHub-Release ins Repository.

Nachgebildet werden `git` und `gh`; kein Test spricht mit GitHub.
Geprüft wird, was schiefgehen könnte, ohne dass es jemand merkt: ein
Tag, das auf einen anderen Stand umgebogen wird, eine Fassung aus
nicht eingechecktem Code, eine Beschreibung ohne Prüfsummen.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tools import veroeffentlichen as v


class _Git:
    """Ein nachgebildetes Repository mit Tags, offenen Dateien und
    einem Protokoll der Befehle."""

    def __init__(self) -> None:
        self.kopf = "a" * 40
        self.tags: dict[str, str] = {}
        self.offen: list[str] = []
        self.befehle: list[list[str]] = []

    def __call__(self, *argumente: str) -> subprocess.CompletedProcess[str]:
        self.befehle.append(list(argumente))
        ausgabe, code = "", 0
        if argumente[0] == "status":
            ausgabe = "".join(f" M {datei}\n" for datei in self.offen)
        elif argumente[0] == "rev-parse":
            ziel = argumente[-1].removesuffix("^{commit}")
            if ziel == "HEAD":
                ausgabe = self.kopf
            elif ziel in self.tags:
                ausgabe = self.tags[ziel]
            elif len(ziel) >= 7 and all(z in "0123456789abcdef" for z in ziel):
                ausgabe = ziel.ljust(40, "0")
            else:
                code = 1
        elif argumente[0] == "tag":
            self.tags[argumente[2]] = argumente[3]
        elif argumente[0] == "commit":
            self.offen = []
            self.kopf = "b" * 40
        return subprocess.CompletedProcess(list(argumente), code, ausgabe + "\n", "")


@pytest.fixture
def git(monkeypatch: pytest.MonkeyPatch) -> _Git:
    nachbau = _Git()
    monkeypatch.setattr(v, "_git", nachbau)
    return nachbau


@pytest.fixture
def gh(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> list[list[str]]:
    """`gh`, angemeldet; merkt sich jeden Aufruf. Ein Release gibt es
    noch nicht."""
    aufrufe: list[list[str]] = []
    monkeypatch.setattr(v, "gh_finden", lambda: tmp_path / "gh.exe")

    def ausfuehren(befehl: list[str]) -> subprocess.CompletedProcess[str]:
        aufrufe.append(befehl[1:])
        code = 1 if befehl[1:3] == ["release", "view"] else 0
        return subprocess.CompletedProcess(befehl, code, "", "")

    monkeypatch.setattr(v, "_ausfuehren", ausfuehren)
    return aufrufe


@pytest.fixture
def gebaut(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[Path, Path]:
    setup = tmp_path / "Natter-Setup.exe"
    setup.write_bytes(b"MZ setup")
    archiv = tmp_path / "Natter-0.3.2-Setup.zip"
    archiv.write_bytes(b"PK zip")
    monkeypatch.setattr(v, "_SETUP", setup)
    monkeypatch.setattr(v, "zip_pfad", lambda _version: archiv)
    return setup, archiv


# --------------------------------------------- Vorbedingungen


def test_ohne_gh_wird_frueh_abgebrochen(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(v, "gh_finden", lambda: None)

    with pytest.raises(v.VeroeffentlichungFehler, match="winget install GitHub.cli"):
        v.vorbedingungen_pruefen()


def test_nicht_eingecheckte_arbeit_verhindert_das_veroeffentlichen(
    git: _Git, gh: list[list[str]]
) -> None:
    """Eine Fassung, deren Stand in keinem Commit steht, ließe sich
    später nicht wiederfinden."""
    git.offen = ["ide/shell/hauptfenster.py"]

    with pytest.raises(v.VeroeffentlichungFehler, match="hauptfenster.py"):
        v.vorbedingungen_pruefen()


def test_die_versionsaenderung_des_baus_darf_offen_sein(
    git: _Git, gh: list[list[str]]
) -> None:
    """Schritt 2 des Baus ändert diese Dateien; eingecheckt werden sie
    beim Veröffentlichen."""
    git.offen = ["pyproject.toml", "tools/natter.iss", "ide/main.py", "uv.lock"]

    v.vorbedingungen_pruefen()


# --------------------------------------------- Ablauf


def test_version_wird_eingecheckt_markiert_und_hochgeladen(
    git: _Git, gh: list[list[str]], gebaut: tuple[Path, Path]
) -> None:
    git.offen = ["pyproject.toml", "ide/main.py"]

    adresse = v.veroeffentlichen("0.3.2", melden=lambda _t: None)

    assert ["commit", "-m", "Version 0.3.2"] in git.befehle
    assert git.tags["v0.3.2"] == "b" * 40
    assert ["push", "origin", "main"] in git.befehle
    assert ["push", "origin", "v0.3.2"] in git.befehle
    erstellen = next(a for a in gh if a[:2] == ["release", "create"])
    assert str(gebaut[1]) in erstellen and str(gebaut[0]) in erstellen
    assert adresse.endswith("/releases/tag/v0.3.2")


def test_mit_stand_wird_genau_dieser_markiert(
    git: _Git, gh: list[list[str]], gebaut: tuple[Path, Path]
) -> None:
    """Wurde nach dem Bau weitergearbeitet, soll das Tag auf den Stand
    zeigen, aus dem die Dateien stammen - nicht auf einen späteren."""
    v.veroeffentlichen("0.3.2", commit="268de88", melden=lambda _t: None)

    assert git.tags["v0.3.2"].startswith("268de88")
    assert not any(b[0] == "commit" for b in git.befehle)


def test_eine_vergebene_nummer_wird_nicht_umgebogen(
    git: _Git, gh: list[list[str]], gebaut: tuple[Path, Path]
) -> None:
    git.tags["v0.3.2"] = "c" * 40

    with pytest.raises(v.SchonVeroeffentlicht):
        v.veroeffentlichen("0.3.2", melden=lambda _t: None)

    assert git.tags["v0.3.2"] == "c" * 40
    assert not any(b[0] == "push" for b in git.befehle)


def test_ein_abgebrochenes_hochladen_wird_wiederholt(
    git: _Git, gh: list[list[str]], gebaut: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Dasselbe Tag auf demselben Stand, das Release gibt es schon: die
    Dateien werden ersetzt, statt dass der Lauf scheitert."""
    git.tags["v0.3.2"] = git.kopf
    aufrufe: list[list[str]] = []
    def ausfuehren(befehl: list[str]) -> subprocess.CompletedProcess[str]:
        aufrufe.append(befehl[1:])
        return subprocess.CompletedProcess(befehl, 0, "", "")

    monkeypatch.setattr(v, "_ausfuehren", ausfuehren)

    v.veroeffentlichen("0.3.2", melden=lambda _t: None)

    hochladen = next(a for a in aufrufe if a[:2] == ["release", "upload"])
    assert "--clobber" in hochladen


def test_ohne_gebaute_dateien_wird_nichts_angefasst(
    git: _Git, gh: list[list[str]], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(v, "_SETUP", tmp_path / "fehlt.exe")
    monkeypatch.setattr(v, "zip_pfad", lambda _version: tmp_path / "fehlt.zip")

    with pytest.raises(v.VeroeffentlichungFehler, match="fehlt"):
        v.veroeffentlichen("0.3.2", melden=lambda _t: None)

    assert git.befehle == []


# --------------------------------------------- Die Beschreibung


def test_die_beschreibung_erklaert_den_weg_unter_windows() -> None:
    text = v.beschreibung("0.3.2")

    assert "Natter-0.3.2-Setup.zip" in text
    assert "Zulassen" in text
    assert "ZUERST-LESEN.txt" in text


def test_die_beschreibung_bleibt_ohne_pruefsummen() -> None:
    """Eine Tabelle mit 64-stelligen Zeichenketten überfordert, wer nur
    herunterladen will - so der Einwand beim ersten Release. GitHub
    zeigt die Prüfsumme ohnehin an jeder Datei."""
    text = v.beschreibung("0.3.2")

    assert "SHA-256" not in text
    assert "Get-FileHash" not in text


def test_lehrkraefte_steht_nicht_im_namen() -> None:
    assert "ehrkr" not in v.zip_pfad("0.3.2").name
    assert "ehrkr" not in v.beschreibung("0.3.2")
