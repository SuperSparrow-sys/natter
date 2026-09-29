"""Der Bauweg zur fertigen `Natter-Setup.exe` (`tools/auslieferung_bauen.py`).

Geprüft wird hier nicht der Bau selbst - der dauert eine halbe Stunde
und braucht Inno Setup, ein Zertifikat und 21 MB Download. Geprüft wird
das, was zwischen den Schritten passiert, denn genau dort sind die
beiden Fehler entstanden, die es überhaupt zu diesem Skript kommen
ließen: ein Installer aus einem veralteten `dist\\Natter` und eine
Auslieferung mit Paketversionen, gegen die nie ein Test lief (siehe
Arbeitspaket M13).

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

    # Kein Test stellt etwas auf GitHub. Die Vorprüfung fragte sonst die
    # echte `gh`-Anmeldung und den echten Arbeitsbaum ab, und ein Test,
    # der bis Schritt 12 käme, würde pushen.
    def nicht_veroeffentlichen(*_a, **_k):  # noqa: ANN202
        raise AssertionError("Ein Test hat versucht, auf GitHub zu veröffentlichen.")

    monkeypatch.setattr(bau, "vorbedingungen_pruefen", lambda: None)
    monkeypatch.setattr(bau, "veroeffentlichen", nicht_veroeffentlichen)


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


def _manifest_fehlt(monkeypatch: pytest.MonkeyPatch) -> None:
    from ide.integritaet import ManifestFehler

    def fehlt(*a, **k):  # noqa: ANN002, ANN003, ANN202
        raise ManifestFehler("manifest.json fehlt")

    monkeypatch.setattr(bau, "manifest_pruefen", fehlt)


def test_ein_fehlendes_manifest_bricht_den_bau_ab(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Punkt 274: eine Installation ohne Manifest meldet bei jedem
    Start, sie sei verändert worden, und rät zu einer Neuinstallation,
    die nichts ändert."""
    _manifest_fehlt(monkeypatch)

    with pytest.raises(bau.BauFehler, match="manifest.json fehlt"):
        bau._manifest_gegenpruefen(tmp_path)


def test_ohne_signatur_ist_ein_fehlendes_manifest_nur_eine_warnung(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _manifest_fehlt(monkeypatch)

    bau._manifest_gegenpruefen(tmp_path, ohne_signatur=True)

    assert "Warnung" in capsys.readouterr().out


def test_ein_fehlender_manifest_schluessel_bricht_vor_dem_bau_ab(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Und zwar in Schritt 1, nicht erst nach Tests und Bau."""
    monkeypatch.setattr(bau, "MANIFEST_SCHLUESSEL", tmp_path / "fehlt.pem")
    monkeypatch.setattr(bau, "_arbeitsbaum_ansehen", lambda: None)
    monkeypatch.setattr(bau, "_ruff_pruefen", lambda: None)

    def nicht_bauen(**_k):  # noqa: ANN003, ANN202
        raise AssertionError("dist\\Natter wurde trotzdem gebaut.")

    monkeypatch.setattr(bau, "paketieren", nicht_bauen)

    with pytest.raises(bau.BauFehler, match="fehlt.pem"):
        bau.auslieferung_bauen(
            mit_tests=False, veroeffentlichen_=False, live=False
        )


def test_ide_paketieren_schreibt_ohne_schluessel_kein_stilles_nichts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tools import ide_paketieren

    monkeypatch.setattr(
        ide_paketieren, "MANIFEST_SCHLUESSEL", tmp_path / "fehlt.pem"
    )

    with pytest.raises(RuntimeError, match="fehlt.pem"):
        ide_paketieren._manifest_schreiben(tmp_path)


def _powershell_nachgebildet(
    monkeypatch: pytest.MonkeyPatch, *, returncode: int = 0, stdout: str = "",
    stderr: str = "",
) -> None:
    import subprocess

    monkeypatch.setattr(
        bau.subprocess,
        "run",
        lambda befehl, **_k: subprocess.CompletedProcess(
            befehl, returncode, stdout=stdout, stderr=stderr
        ),
    )


def test_ein_fehlschlag_beim_signieren_des_installers_bricht_ab(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _powershell_nachgebildet(
        monkeypatch, returncode=1, stderr="Kein Zertifikat gefunden."
    )

    with pytest.raises(bau.BauFehler, match="Kein Zertifikat"):
        bau._installer_signieren(tmp_path / "Natter-Setup.exe")


def test_ein_unsignierter_installer_bricht_schritt_10_ab(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _powershell_nachgebildet(
        monkeypatch,
        stdout="Natter.exe|Valid\nNatter-Setup.exe|NotSigned\n",
    )

    with pytest.raises(bau.BauFehler, match="Natter-Setup.exe"):
        bau._signaturen_pruefen(
            [tmp_path / "Natter.exe", tmp_path / "Natter-Setup.exe"]
        )


def test_ohne_auskunft_von_windows_gilt_der_installer_als_unsigniert(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _powershell_nachgebildet(monkeypatch, stdout="Natter.exe|Valid\n")

    with pytest.raises(bau.BauFehler, match="Natter-Setup.exe"):
        bau._signaturen_pruefen(
            [tmp_path / "Natter.exe", tmp_path / "Natter-Setup.exe"]
        )


def test_gueltige_signaturen_gehen_durch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _powershell_nachgebildet(
        monkeypatch, stdout="Natter.exe|Valid\nNatter-Setup.exe|Valid\n"
    )

    bau._signaturen_pruefen(
        [tmp_path / "Natter.exe", tmp_path / "Natter-Setup.exe"]
    )


def test_ohne_signatur_wird_nichts_veroeffentlicht(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Der Schalter für den Probebau lässt die Warnungen durch; dafür
    bleibt die Auslieferung lokal. Die Fixture oben lässt jeden
    Versuch zu veröffentlichen scheitern."""
    installer = tmp_path / "Natter-Setup.exe"
    installer.write_bytes(b"MZ")
    for name in (
        "_arbeitsbaum_ansehen", "_ruff_pruefen", "_tests_laufen_lassen",
        "_rauchprobe", "_manifest_gegenpruefen", "_installer_signieren",
        "_signaturen_pruefen", "_alle_signaturen_pruefen", "_paket_packen",
        "_manifest_schluessel_pruefen", "_starterversion_pruefen",
    ):
        monkeypatch.setattr(bau, name, lambda *_a, **_k: None)
    monkeypatch.setattr(bau, "paketieren", lambda **_k: tmp_path)
    monkeypatch.setattr(bau, "_installer_bauen", lambda: installer)

    assert bau.main(["--ohne-signatur", "--ohne-balken"]) == 0


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


# -- Vorlagen des Exe-Exports bleiben unsigniert (Punkt 34) ------------


def test_signierskript_und_bau_nehmen_dieselben_vorlagen_aus() -> None:
    """Die Ausnahme für die PyInstaller-Vorlagen steht im Bau, im
    Signierskript und in Schritt 10. Liefen sie auseinander, würde eine
    Vorlage signiert und jede exportierte Exe unsignierbar."""
    from tools.ide_paketieren import NICHT_SIGNIERT

    wurzel = Path(__file__).resolve().parent.parent
    skript = (wurzel / "tools" / "signieren" / "alles_signieren.ps1").read_text(
        encoding="utf-8"
    )
    zeile = next(z for z in skript.splitlines() if z.startswith("$AUSGENOMMEN"))

    assert zeile.split("=", 1)[1].strip().strip('"') == NICHT_SIGNIERT


def test_der_bau_zaehlt_die_vorlagen_nicht_zu_den_binaerdateien(
    tmp_path: Path,
) -> None:
    from tools.ide_paketieren import _binaerdateien

    vorlage = tmp_path / "Lib" / "site-packages" / "PyInstaller" / "bootloader"
    (vorlage / "Windows-64bit-intel").mkdir(parents=True)
    (vorlage / "Windows-64bit-intel" / "runw.exe").write_bytes(b"MZ")
    (tmp_path / "Natter.exe").write_bytes(b"MZ")

    assert [p.name for p in _binaerdateien(tmp_path)] == ["Natter.exe"]


def _signierte_kopie(ziel: Path) -> list[str]:
    """Kopiert eine Datei mit eingebetteter gültiger Signatur nach
    `ziel`. Leer zurück heißt: gefunden; sonst je Kandidat, was
    PowerShell über seine Kopie gesagt hat.

    Nicht jede signierte Windows-Datei taugt dafür: auf dem
    GitHub-Runner (Windows Server) ist `notepad.exe` nur über einen
    Katalog signiert, und die Kopie gilt dann als unsigniert. Deshalb
    wird die Kopie selbst geprüft und notfalls die nächste Datei
    versucht. Bis zum 26.09. meldete der Runner bei allen drei
    damaligen Kandidaten etwas anderes als `Valid`, ohne dass der
    Grund im Protokoll stand (Punkt 46); deshalb steht er jetzt in
    der Begründung fürs Überspringen.
    """
    import glob
    import shutil
    import subprocess

    kandidaten = [
        Path(r"C:\Windows\System32\notepad.exe"),
        Path(r"C:\Program Files\PowerShell\7\pwsh.exe"),
        *(Path(p) for p in (shutil.which("git"), shutil.which("pwsh")) if p),
        Path(r"C:\Program Files\dotnet\dotnet.exe"),
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        *(Path(p) for p in sorted(glob.glob(
            r"C:\hostedtoolcache\windows\Python\3.*\x64\python.exe"))),
    ]
    befunde = []
    for quelle in kandidaten:
        if not quelle.is_file():
            continue
        shutil.copy(quelle, ziel)
        lauf = subprocess.run(
            [
                "powershell", "-NoProfile", "-Command",
                f"$s = Get-AuthenticodeSignature -LiteralPath '{ziel}'; "
                "Write-Output \"$($s.Status)|$($s.StatusMessage)\"",
            ],
            capture_output=True,
            encoding="oem",
            errors="replace",
            timeout=60,
            check=False,
            env=bau.powershell_umgebung(),
        )
        status = lauf.stdout.strip()
        if status.startswith("Valid|"):
            return []
        fehler = lauf.stderr.strip().replace("\n", " ")[:300]
        befunde.append(f"{quelle.name}: {status} {fehler}".strip())
    return befunde or ["kein Kandidat vorhanden"]


def test_schritt_10_meldet_eine_signierte_vorlage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mit echtem PowerShell: eine signierte Vorlage bricht ab, eine
    unsignierte Vorlage nicht, eine unsignierte Datei sonst schon."""
    monkeypatch.setattr(bau, "_anzeige", _StummeAnzeige())
    vorlagen = tmp_path / "PyInstaller" / "bootloader" / "Windows-64bit-intel"
    vorlagen.mkdir(parents=True)
    befunde = _signierte_kopie(vorlagen / "run.exe")
    if befunde:
        pytest.skip("keine Datei mit eingebetteter Signatur gefunden: "
                    + "; ".join(befunde))
    (vorlagen / "runw.exe").write_bytes(b"MZ unsigniert")
    (tmp_path / "Lib.dll").write_bytes(b"MZ unsigniert")

    luecken = bau._luecken_in_den_signaturen(tmp_path)

    assert any(p.endswith("run.exe (Vorlage für den Exe-Export, muss unsigniert bleiben)")
               for p in luecken)
    assert any(p.endswith("Lib.dll") for p in luecken)
    assert not any("runw.exe" in p for p in luecken)


class _StummeAnzeige:
    def stand(self, *_a, **_k) -> None:
        pass


def test_ruff_prueft_nichts_unter_build() -> None:
    """Schritt 3 ruft `ruff check .`; unter build/ liegen Zwischenstände
    und Auswertungen mit Kopien von Schülerprojekten. Der erste
    Bauversuch zu 0.3.3 brach daran ab (Punkt 32)."""
    import subprocess
    import sys

    wurzel = Path(__file__).resolve().parent.parent
    ergebnis = subprocess.run(
        [sys.executable, "-m", "ruff", "check", ".", "--show-files"],
        cwd=wurzel, capture_output=True, text=True, timeout=120,
    )
    dateien = [z for z in ergebnis.stdout.splitlines() if z.strip()]

    assert dateien, "ruff hat keine Dateien genannt"
    unter_build = [d for d in dateien if Path(d).relative_to(wurzel).parts[0] == "build"]
    assert unter_build == []


def test_entwicklungsbaum_und_auslieferung_haben_dieselbe_python() -> None:
    """Punkt 33: ausgeliefert wurde 3.13.15, getestet mit 3.13.14 -
    `uv.lock` legt die Patch-Version von Python nicht fest. Jetzt steht
    sie in `.python-version` (uv und die CI lesen sie) und muss zu der
    Fassung passen, die der Bau herunterlädt."""
    from tools.python_beschaffen import PYTHON_FASSUNG

    wurzel = Path(__file__).resolve().parent.parent
    festgelegt = (wurzel / ".python-version").read_text(encoding="utf-8").strip()

    assert PYTHON_FASSUNG.split("-")[1] == festgelegt


def test_entwicklungs_python_kommt_aus_uvs_verwaltung() -> None:
    """Punkt 52: `.venv` war mit einer Python aus einem Zwischenordner
    angelegt, der später geräumt wurde; danach fehlte `ctypes.wintypes`,
    und kein Test lief mehr. uv nimmt die Python jetzt nur aus der
    eigenen Verwaltung."""
    import tomllib

    wurzel = Path(__file__).resolve().parent.parent
    daten = tomllib.loads((wurzel / "pyproject.toml").read_text(encoding="utf-8"))

    assert daten["tool"]["uv"]["python-preference"] == "only-managed"


def _starter_nachbilden(ordner: Path, *, mit_ordner: bool = True) -> None:
    """Was PyInstaller mit `--onedir` ablegt, im Kleinen."""
    ordner.mkdir(parents=True)
    (ordner / "Natter.exe").write_bytes(b"MZ")
    if mit_ordner:
        (ordner / "starter").mkdir()
        (ordner / "starter" / "python313.dll").write_bytes(b"MZ")
        (ordner / "starter" / "base_library.zip").write_bytes(b"PK")


def _starterbau_umlenken(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> object:
    from tools import ide_paketieren as paket

    monkeypatch.setattr(paket, "_DIST_ORDNER", tmp_path / "dist")
    monkeypatch.setattr(paket, "_AUSGABE", tmp_path / "dist" / "Natter")
    monkeypatch.setattr(paket, "_BUILD_ORDNER", tmp_path / "build")
    monkeypatch.setattr(paket, "_SPEC_ORDNER", tmp_path / "spec")
    (tmp_path / "dist" / "Natter").mkdir(parents=True)
    return paket


@pytest.mark.parametrize("mit_ordner", [True, False])
def test_der_starter_wird_als_ordner_gebaut(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mit_ordner: bool
) -> None:
    """Punkt 399: als einzelne Datei entpackte sich `Natter.exe` bei
    jedem Start nach `%TEMP%\\_MEI…`, und nach einem harten Beenden
    blieben dort je rund 18 MB liegen. Als Ordner gebaut kommen
    `Natter.exe` und der Ordner `starter` in den Programmordner;
    fehlt der Ordner, bricht der Bau ab, statt eine Natter.exe
    auszuliefern, die nicht startet."""
    from ide.integritaet.manifest import STARTER_ORDNER

    paket = _starterbau_umlenken(tmp_path, monkeypatch)
    gesehen: list[list[str]] = []

    def pyinstaller(befehl, _melder, **_k):  # noqa: ANN001, ANN202
        gesehen.append(befehl)
        _starter_nachbilden(
            tmp_path / "dist" / "_starter" / "Natter", mit_ordner=mit_ordner
        )
        return 0, ""

    monkeypatch.setattr(paket, "ausfuehren", pyinstaller)

    if not mit_ordner:
        with pytest.raises(RuntimeError, match=STARTER_ORDNER):
            paket._starter_bauen()
        return
    paket._starter_bauen()

    befehl = gesehen[0]
    assert "--onedir" in befehl
    assert "--onefile" not in befehl
    assert befehl[befehl.index("--contents-directory") + 1] == STARTER_ORDNER
    ausgabe = tmp_path / "dist" / "Natter"
    assert (ausgabe / "Natter.exe").is_file()
    assert (ausgabe / STARTER_ORDNER / "python313.dll").is_file()
    assert not (tmp_path / "dist" / "_starter").exists()
    # Schritt 6 sieht im gebauten Ordner nach demselben Namen.
    assert f'"{STARTER_ORDNER}"' in bau._RAUCHPROBE


def test_der_starter_bekommt_die_versionsnummer_aus_pyproject(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Punkt 359: `Natter.exe` trug keine Versionsangabe, weil der
    Starter ohne `--version-file` gebaut wurde. Eine Softwareverteilung
    fand damit keine Dateiversion für ihre Erkennungsregel. Geprüft an
    einer Attrappe statt PyInstaller: der Aufruf muss die Datei nennen,
    und sie muss die Nummer aus `pyproject.toml` tragen."""
    from tools import ide_paketieren as paket

    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(PYPROJECT.replace("0.1.0", "0.7.3"), encoding="utf-8")
    monkeypatch.setattr(paket, "_PYPROJECT", pyproject)
    monkeypatch.setattr(paket, "_DIST_ORDNER", tmp_path / "dist")
    monkeypatch.setattr(paket, "_AUSGABE", tmp_path / "dist" / "Natter")
    monkeypatch.setattr(paket, "_BUILD_ORDNER", tmp_path / "build")
    monkeypatch.setattr(paket, "_SPEC_ORDNER", tmp_path / "spec")
    (tmp_path / "dist" / "Natter").mkdir(parents=True)
    gesehen: dict[str, object] = {}

    def pyinstaller(befehl, _melder, **_k):  # noqa: ANN001, ANN202
        gesehen["befehl"] = befehl
        datei = Path(befehl[befehl.index("--version-file") + 1])
        gesehen["inhalt"] = datei.read_text(encoding="utf-8")
        _starter_nachbilden(tmp_path / "dist" / "_starter" / "Natter")
        return 0, ""

    monkeypatch.setattr(paket, "ausfuehren", pyinstaller)

    paket._starter_bauen()

    assert "--version-file" in gesehen["befehl"]
    inhalt = str(gesehen["inhalt"])
    assert "filevers=(0, 7, 3, 0)" in inhalt
    assert "StringStruct('FileVersion', '0.7.3')" in inhalt
    assert "StringStruct('ProductVersion', '0.7.3')" in inhalt
    assert (tmp_path / "dist" / "Natter" / "Natter.exe").exists()

    # So, wie PyInstaller die Datei liest.
    versioninfo = pytest.importorskip("PyInstaller.utils.win32.versioninfo")
    datei = tmp_path / "gelesen.txt"
    datei.write_text(inhalt, encoding="utf-8")
    info = versioninfo.load_version_info_from_text_file(str(datei))
    assert info.ffi.fileVersionMS == (0 << 16) | 7
    assert info.ffi.fileVersionLS == (3 << 16) | 0


def test_die_dateiversion_wird_nach_dem_bau_geprueft(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Punkt 359, zweite Hälfte: Schritt 5 liest die Dateiversion der
    gebauten `Natter.exe` so, wie Windows sie zeigt, und bricht bei
    einer fehlenden oder falschen ab."""
    import sys

    python = bau.dateiversion(Path(sys.executable))
    assert python is not None
    assert python.startswith(f"{sys.version_info.major}.{sys.version_info.minor}.")

    ohne = tmp_path / "Natter.exe"
    ohne.write_bytes(b"MZ")
    assert bau.dateiversion(ohne) is None
    with pytest.raises(bau.BauFehler, match="keine"):
        bau._starterversion_pruefen(ohne, "0.4.0")

    monkeypatch.setattr(bau, "dateiversion", lambda _p: "0.3.6")
    with pytest.raises(bau.BauFehler, match="0.3.6"):
        bau._starterversion_pruefen(ohne, "0.4.0")
    monkeypatch.setattr(bau, "dateiversion", lambda _p: "0.4.0")
    bau._starterversion_pruefen(ohne, "0.4.0")


def test_agents_md_nennt_jede_datei_mit_versionsnummer() -> None:
    """AGENTS.md nannte zwei Stellen, das Skript setzt drei
    (Punkt 135). Die Liste hier steht gleichlautend im Kopf des
    Skripts, Schritt 2."""
    from pathlib import Path

    wurzel = Path(__file__).resolve().parent.parent
    text = (wurzel / "AGENTS.md").read_text(encoding="utf-8")
    abschnitt = text.split("## Auslieferung", 1)[1].split("\n## ", 1)[0]
    skript = (wurzel / "tools" / "auslieferung_bauen.py").read_text(encoding="utf-8")
    for datei in ("pyproject.toml", "tools/natter.iss", "ide/main.py"):
        assert f"`{datei}`" in skript
        assert f"`{datei}`" in abschnitt
