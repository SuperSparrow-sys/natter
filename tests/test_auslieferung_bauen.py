"""Der Bauweg zur fertigen `Natter-Setup.exe` (`tools/auslieferung_bauen.py`).

Geprüft wird hier nicht der Bau selbst - der dauert eine halbe Stunde
und braucht Inno Setup, ein Zertifikat und 21 MB Download. Geprüft wird
das, was zwischen den Schritten passiert, denn genau dort sind im
 die beiden Fehler entstanden, die es überhaupt zu diesem
Skript kommen ließen: ein Installer aus einem veralteten `dist\\Natter`
und eine Auslieferung mit Paketversionen, gegen die nie ein Test lief
(siehe `docs/arbeitspakete/M13.md`).

Die Versionsnummer steht an zwei Stellen - `pyproject.toml` bestimmt,
was `pip` in die Auslieferung legt, `tools/natter.iss` das, was Windows
in „Apps & Features" anzeigt. Laufen sie auseinander, trägt das Update
eine Nummer, die es so nie gegeben hat; deshalb steht der Abgleich
hier.

Alle Tests arbeiten auf Kopien in `tmp_path`: `_version_setzen`
schreibt wirklich in die Dateien, und ein Testlauf darf die
eingecheckte `pyproject.toml` nicht anfassen.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tools import auslieferung_bauen as bau

PYPROJECT = '[project]\nname = "natter"\nversion = "0.1.0"\nrequires-python = ">=3.13"\n'
ISS = '#define MyAppName "Natter"\n#define MyAppVersion "0.1.0"\n[Setup]\n'


@pytest.fixture
def dateien(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    """`pyproject.toml` und `natter.iss` als Wegwerf-Kopien."""
    pyproject = tmp_path / "pyproject.toml"
    iss = tmp_path / "natter.iss"
    pyproject.write_text(PYPROJECT, encoding="utf-8")
    iss.write_text(ISS, encoding="utf-8")
    monkeypatch.setattr(bau, "_PYPROJECT", pyproject)
    monkeypatch.setattr(bau, "_ISS", iss)
    return pyproject, iss


def test_die_version_wird_an_beiden_stellen_gesetzt(dateien: tuple[Path, Path]) -> None:
    pyproject, iss = dateien

    bau._version_setzen("0.2.0")

    assert 'version = "0.2.0"' in pyproject.read_text(encoding="utf-8")
    assert '#define MyAppVersion "0.2.0"' in iss.read_text(encoding="utf-8")
    # Der Rest der Dateien bleibt unangetastet.
    assert 'name = "natter"' in pyproject.read_text(encoding="utf-8")
    assert "[Setup]" in iss.read_text(encoding="utf-8")


@pytest.mark.parametrize("unsinn", ["0.2", "v0.2.0", "0.2.0-beta", "zwei"])
def test_eine_unbrauchbare_versionsnummer_wird_abgelehnt(
    unsinn: str, dateien: tuple[Path, Path]
) -> None:
    """Inno Setup nimmt fast alles als `AppVersion` an und vergleicht es
    dann als Zeichenkette. Was nicht `1.2.3` ist, faellt hier auf."""
    with pytest.raises(bau.BauFehler, match="Format"):
        bau._version_setzen(unsinn)

    # Nichts halb geschrieben.
    assert dateien[0].read_text(encoding="utf-8") == PYPROJECT
    assert dateien[1].read_text(encoding="utf-8") == ISS


def test_auseinanderlaufende_versionen_brechen_den_bau_ab(
    dateien: tuple[Path, Path],
) -> None:
    """Der Fall, den es zu verhindern gilt: `pip` legt 0.2.0 in die
    Auslieferung, Windows zeigt 0.1.0 an."""
    dateien[1].write_text(ISS.replace("0.1.0", "0.3.0"), encoding="utf-8")

    with pytest.raises(bau.BauFehler, match="auseinander"):
        bau._versionen_abgleichen(None)


def test_gleiche_versionen_gehen_durch(dateien: tuple[Path, Path]) -> None:
    assert bau._versionen_abgleichen(None) == "0.1.0"


def test_mit_angabe_werden_beide_dateien_nachgezogen(dateien: tuple[Path, Path]) -> None:
    assert bau._versionen_abgleichen("1.0.0") == "1.0.0"
    assert bau._version_aus_pyproject() == "1.0.0"
    assert bau._version_aus_iss() == "1.0.0"


def test_die_echten_dateien_sind_einig() -> None:
    """Ohne Kopie, gegen den eingecheckten Stand: beide Versionsnummern
    muessen jetzt schon uebereinstimmen, nicht erst beim naechsten Bau."""
    assert bau._version_aus_pyproject() == bau._version_aus_iss()


def test_ohne_inno_setup_kommt_eine_brauchbare_meldung(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Inno Setup ist die einzige Voraussetzung, die nicht mit `uv sync`
    kommt - wer sie nicht hat, soll lesen, wo er sie bekommt."""
    monkeypatch.setattr(bau.shutil, "which", lambda _: None)
    monkeypatch.setattr(bau, "_ISCC_ORTE", ())

    with pytest.raises(bau.BauFehler, match="jrsoftware"):
        bau._iscc_finden()


def test_die_rauchprobe_meldet_eine_kaputte_auslieferung(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Schritt 6 ist die Stelle, an der eine Auslieferung auffaellt, die
    alle Tests bestanden hat. Sie muss abbrechen, nicht warnen."""

    class Fehlschlag:
        returncode = 1
        stdout = "FEHLER pandas: DLL load failed while importing join\n"
        stderr = ""

    monkeypatch.setattr(bau.subprocess, "run", lambda *a, **k: Fehlschlag())

    with pytest.raises(bau.BauFehler, match="Rauchprobe"):
        bau._rauchprobe(tmp_path / "python.exe")


def test_die_rauchprobe_prueft_die_gebaute_python(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Und nicht die des Entwicklungsbaums - dort lief beim
    pandas-Fehler ja alles."""
    gerufen: list[list[str]] = []

    class Erfolg:
        returncode = 0
        stdout = "pandas 3.0.5\nRauchprobe bestanden\n"
        stderr = ""

    def merken(befehl, **kwargs):  # noqa: ANN001, ANN202
        gerufen.append([str(teil) for teil in befehl])
        return Erfolg()

    monkeypatch.setattr(bau.subprocess, "run", merken)
    python = tmp_path / "dist" / "Natter" / "python" / "python.exe"

    bau._rauchprobe(python)

    assert gerufen[0][0] == str(python)
    assert "import pandas" in gerufen[0][2]


def test_die_rauchprobe_sieht_jede_pandas_bibliothek_an() -> None:
    """Blockiert wurden fuenf von vierzehn - eine
 Probe, die nur `import pandas` macht, haette drei davon nicht
 bemerkt, weil pandas sie erst spaeter nachlaedt."""
    for teil in ("algos", "byteswap", "groupby", "join", "parsers"):
        assert f'"{teil}"' in bau._RAUCHPROBE


def test_ein_kaputtes_manifest_bricht_den_bau_ab(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Eine Abweichung hier hiesse beim Schueler: Manipulationswarnung
    beim ersten Start."""
    from ide.integritaet import PruefErgebnis

    monkeypatch.setattr(
        bau,
        "manifest_pruefen",
        lambda *a, **k: PruefErgebnis(signatur_gueltig=True, veraendert=["Natter.exe"]),
    )

    with pytest.raises(bau.BauFehler, match="Natter.exe"):
        bau._manifest_gegenpruefen(tmp_path)


def test_ein_fehlendes_manifest_ist_nur_eine_warnung(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Ohne privaten Schluessel schreibt `ide_paketieren` gar kein
    Manifest - ein Bau auf einem fremden Rechner soll daran nicht
    scheitern."""
    from ide.integritaet import ManifestFehler

    def fehlt(*a, **k):  # noqa: ANN002, ANN003, ANN202
        raise ManifestFehler("manifest.json fehlt")

    monkeypatch.setattr(bau, "manifest_pruefen", fehlt)

    bau._manifest_gegenpruefen(tmp_path)

    assert "Warnung" in capsys.readouterr().out


def test_ein_alter_installer_bleibt_nicht_liegen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sonst sieht die Datei vom vorigen Bau nach dem Ergebnis dieses
    Baus aus - genau der Fehler, den es zu verhindern gilt."""
    installer = tmp_path / "Natter-Setup.exe"
    installer.write_bytes(b"alter Stand")
    monkeypatch.setattr(bau, "_INSTALLER", installer)
    monkeypatch.setattr(bau, "_iscc_finden", lambda: Path("ISCC.exe"))
    monkeypatch.setattr(bau, "_laufen_lassen", lambda *a, **k: "Successful compile")

    with pytest.raises(bau.BauFehler, match="fehlt"):
        bau._installer_bauen()

    assert not installer.exists()


def test_nur_installer_ohne_gebauten_ordner_bricht_ab(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(bau, "_AUSGABE", tmp_path / "gibtsnicht")

    with pytest.raises(bau.BauFehler, match="--nur-installer"):
        bau.auslieferung_bauen(nur_installer=True)


def test_version_und_nur_installer_schliessen_einander_aus(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Die neue Nummer kaeme sonst nur in den Installer: Windows zeigte
    0.2.0 an, `pip list` in der Installation weiterhin 0.1.0."""
    assert bau.main(["--version", "0.2.0", "--nur-installer"]) == 1
    assert "schließen einander aus" in capsys.readouterr().err
