"""Der Bauweg zur fertigen `Natter-Setup.exe` (`tools/auslieferung_bauen.py`).

Geprüft wird hier nicht der Bau selbst - der dauert eine halbe Stunde
und braucht Inno Setup, ein Zertifikat und 21 MB Download. Geprüft wird
das, was zwischen den Schritten passiert, denn genau dort sind die
beiden Fehler entstanden, die es überhaupt zu diesem Skript kommen
ließen: ein Installer aus einem veralteten `dist\\Natter` und eine
Auslieferung mit Paketversionen, gegen die nie ein Test lief (siehe
`docs/arbeitspakete/M13.md`).

Die Versionsnummer steht an drei Stellen: `pyproject.toml` bestimmt,
was `pip` in die Auslieferung legt, `tools/natter.iss` das, was
Windows in „Apps & Features" anzeigt, und `ide/main.py` das, was beim
Start auf dem Ladebild steht. Laufen sie auseinander, trägt das
Update eine Nummer, die es so nie gegeben hat; bei 0.3.0 war es genau
so, und aufgefallen ist es erst in der fertigen Installation.

Alle Tests arbeiten auf Kopien: `_version_setzen` schreibt wirklich in
die Dateien, und ein Testlauf darf die eingecheckten nicht anfassen.
Dafür sorgt der Riegel `_echte_dateien_geschuetzt` von sich aus.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tools import auslieferung_bauen as bau

PYPROJECT = '[project]\nname = "natter"\nversion = "0.1.0"\nrequires-python = ">=3.13"\n'
ISS = '#define MyAppName "Natter"\n#define MyAppVersion "0.1.0"\n[Setup]\n'
MAIN = 'VERSION = "0.1.0"\n\n\ndef main() -> int:\n    return 0\n'

#: Die eingecheckten Pfade, festgehalten bevor der Riegel unten sie
#: auf einen Wegwerf-Ordner umlenkt.
_ECHT_PYPROJECT = bau._PYPROJECT
_ECHT_ISS = bau._ISS
_ECHT_MAIN = bau._MAIN


@pytest.fixture(autouse=True)
def _echte_dateien_geschuetzt(tmp_path_factory, monkeypatch: pytest.MonkeyPatch) -> None:
    """Kein Test schreibt in die eingecheckten Dateien.

    `_version_setzen()` schreibt wirklich, und die Tests dazu arbeiten
    auf Kopien - solange sie die `dateien`-Fixture benutzen. Beim
    Erweitern um `ide/main.py` lief einmal ein Testlauf dazwischen,
    bei dem das Skript die dritte Datei schon kannte und die Fixture
    noch nicht: er setzte die eingecheckte `ide/main.py` auf 1.0.0.

    Dieser Riegel lenkt alle drei Pfade von vornherein auf einen
    Wegwerf-Ordner um. Wer Kopien mit Inhalt braucht, nimmt weiter
    `dateien` - die überschreibt die Pfade dann mit ihren eigenen.
    """
    ordner = tmp_path_factory.mktemp("versionen")
    for name, dateiname, inhalt in (
        ("_PYPROJECT", "pyproject.toml", PYPROJECT),
        ("_ISS", "natter.iss", ISS),
        ("_MAIN", "main.py", MAIN),
    ):
        # Mit Inhalt und nicht nur als Pfad: ein Test, der den ganzen
        # Lauf antreibt, kommt sonst schon an Schritt 2 nicht vorbei
        # und scheitert an etwas anderem als an seiner eigenen Frage.
        pfad = ordner / dateiname
        pfad.write_text(inhalt, encoding="utf-8")
        monkeypatch.setattr(bau, name, pfad)

    # Protokoll, Schrittzeiten und Teststempel: ein Test, der den Lauf
    # antreibt, schriebe sie sonst nach `dist/` und `build/` - und ein
    # Teststempel dort ließe den nächsten echten Bau glauben, die
    # Tests seien schon grün gewesen.
    monkeypatch.setattr(bau, "_BAU_CACHE", ordner / "bau-cache")
    monkeypatch.setattr(bau, "_TEST_STEMPEL", ordner / "bau-cache" / "tests.json")
    monkeypatch.setattr(bau, "_PROTOKOLL", ordner / "auslieferung.log")


@pytest.fixture
def echte_pfade(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hebt den Riegel für die Tests auf, die ausdrücklich den
    eingecheckten Stand lesen - sie schreiben nicht."""
    monkeypatch.setattr(bau, "_PYPROJECT", _ECHT_PYPROJECT)
    monkeypatch.setattr(bau, "_ISS", _ECHT_ISS)
    monkeypatch.setattr(bau, "_MAIN", _ECHT_MAIN)


@pytest.fixture
def dateien(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path, Path]:
    """Die drei Dateien mit einer Versionsnummer, als Wegwerf-Kopien."""
    pyproject = tmp_path / "pyproject.toml"
    iss = tmp_path / "natter.iss"
    main = tmp_path / "main.py"
    pyproject.write_text(PYPROJECT, encoding="utf-8")
    iss.write_text(ISS, encoding="utf-8")
    main.write_text(MAIN, encoding="utf-8")
    monkeypatch.setattr(bau, "_PYPROJECT", pyproject)
    monkeypatch.setattr(bau, "_ISS", iss)
    monkeypatch.setattr(bau, "_MAIN", main)
    return pyproject, iss, main


def test_die_version_wird_an_allen_drei_stellen_gesetzt(
    dateien: tuple[Path, Path, Path],
) -> None:
    pyproject, iss, main = dateien

    bau._version_setzen("0.2.0")

    assert 'version = "0.2.0"' in pyproject.read_text(encoding="utf-8")
    assert '#define MyAppVersion "0.2.0"' in iss.read_text(encoding="utf-8")
    assert 'VERSION = "0.2.0"' in main.read_text(encoding="utf-8")
    # Der Rest der Dateien bleibt unangetastet.
    assert 'name = "natter"' in pyproject.read_text(encoding="utf-8")
    assert "[Setup]" in iss.read_text(encoding="utf-8")
    assert "def main() -> int:" in main.read_text(encoding="utf-8")


@pytest.mark.parametrize("unsinn", ["0.2", "v0.2.0", "0.2.0-beta", "zwei"])
def test_eine_unbrauchbare_versionsnummer_wird_abgelehnt(
    unsinn: str, dateien: tuple[Path, Path, Path]
) -> None:
    """Inno Setup nimmt fast alles als `AppVersion` an und vergleicht es
    dann als Zeichenkette. Was nicht `1.2.3` ist, faellt hier auf."""
    with pytest.raises(bau.BauFehler, match="Format"):
        bau._version_setzen(unsinn)

    # Nichts halb geschrieben.
    assert dateien[0].read_text(encoding="utf-8") == PYPROJECT
    assert dateien[1].read_text(encoding="utf-8") == ISS
    assert dateien[2].read_text(encoding="utf-8") == MAIN


def test_auseinanderlaufende_versionen_brechen_den_bau_ab(
    dateien: tuple[Path, Path, Path],
) -> None:
    """Der Fall, den es zu verhindern gilt: `pip` legt 0.2.0 in die
    Auslieferung, Windows zeigt 0.1.0 an."""
    dateien[1].write_text(ISS.replace("0.1.0", "0.3.0"), encoding="utf-8")

    with pytest.raises(bau.BauFehler, match="auseinander"):
        bau._versionen_abgleichen(None)


def test_gleiche_versionen_gehen_durch(dateien: tuple[Path, Path, Path]) -> None:
    assert bau._versionen_abgleichen(None) == "0.1.0"


def test_eine_vergessene_stelle_bricht_den_bau_ab(
    dateien: tuple[Path, Path, Path],
) -> None:
    """Der Fall, der beim Bau von 0.3.0 durchgerutscht ist: die
    Auslieferung war als 0.3.0 registriert und begrüßte den Benutzer
    mit 0.2.1, weil `ide/main.py` nicht mitgezogen und auch nicht
    abgeglichen wurde."""
    dateien[2].write_text(MAIN.replace("0.1.0", "0.2.1"), encoding="utf-8")

    with pytest.raises(bau.BauFehler, match="auseinander"):
        bau._versionen_abgleichen(None)


def test_mit_angabe_werden_alle_dateien_nachgezogen(
    dateien: tuple[Path, Path, Path],
) -> None:
    assert bau._versionen_abgleichen("1.0.0") == "1.0.0"
    assert bau._version_aus_pyproject() == "1.0.0"
    assert bau._version_aus_iss() == "1.0.0"
    assert bau._version_aus_main() == "1.0.0"


def test_die_echten_dateien_sind_einig(echte_pfade: None) -> None:
    """Ohne Kopie, gegen den eingecheckten Stand: alle drei
    Versionsnummern müssen jetzt schon übereinstimmen, nicht erst beim
    nächsten Bau.

    Die dritte Stelle kam nach dem Bau von 0.3.0 dazu. Bis dahin
    verglich der Test nur `pyproject.toml` und `natter.iss`, und die
    Nummer, die beim Start auf dem Ladebild steht, blieb auf 0.2.1.
    """
    assert bau._version_aus_pyproject() == bau._version_aus_iss()
    assert bau._version_aus_pyproject() == bau._version_aus_main()


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
 Probe, die nur `import pandas` macht, hätte drei davon nicht
 bemerkt, weil pandas sie erst später nachlaedt."""
    for teil in ("algos", "byteswap", "groupby", "join", "parsers"):
        assert f'"{teil}"' in bau._RAUCHPROBE


def test_ein_kaputtes_manifest_bricht_den_bau_ab(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Eine Abweichung hier hiesse beim Schüler: Manipulationswarnung
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
    """Ohne privaten Schlüssel schreibt `ide_paketieren` gar kein
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


def test_das_gate_prueft_dieselben_endungen_wie_das_signierskript() -> None:
    """Liefen die beiden auseinander, pruefte Schritt 10 etwas
    anderes, als der Bau signiert hat - und genau dazwischen sind die
    beiden letzten Auslieferungsfehler entstanden."""
    wurzel = Path(__file__).resolve().parent.parent
    skript = (wurzel / "tools" / "signieren" / "alles_signieren.ps1").read_text(
        encoding="utf-8"
    )
    zeile = next(z for z in skript.splitlines() if z.startswith("$ENDUNGEN"))
    im_skript = {
        teil.strip().strip('"').lstrip("*")
        for teil in zeile.split("@(")[1].rstrip(")").split(",")
    }

    assert im_skript == set(bau._SIGNIERTE_ENDUNGEN)


def test_das_gate_filtert_nicht_ueber_include() -> None:
    """`-Include` wird zusammen mit `-LiteralPath` von PowerShell ohne
    Meldung fallengelassen. Der erste Lauf dieses Gates meldete
    deshalb 29341 Luecken, angefuehrt von manifest.json und den
    Lizenztexten."""
    import inspect

    quelle = inspect.getsource(bau._luecken_in_den_signaturen)
    code = [z for z in quelle.splitlines() if not z.lstrip().startswith("#")]

    assert any("-LiteralPath" in z for z in code)
    assert any("Where-Object" in z for z in code)
    assert not any("-Include" in z for z in code)
